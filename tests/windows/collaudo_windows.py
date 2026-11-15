"""Collaudo di LagDoctor su un Windows VERO (il computer usa e getta di GitHub, a ogni versione; uscita 1 = la
versione non viene pubblicata). Va eseguito come amministratore. Puo' essere eseguito anche a mano su un PC di prova:
cambia davvero le impostazioni, ma ogni voce viene annullata subito dopo.

1. Ogni ottimizzazione "sicura": stato -> Applica -> risulta attiva (o "serve il riavvio") -> Annulla -> lo stato e i
   valori (registro, servizio, piano energetico, bcdedit) tornano ESATTAMENTE come prima.
2. Le voci rischiose, di rete e quelle che dipendono da hardware assente: solo lettura dello stato (deve rispondere
   True / False / non verificabile, senza errori).
3. Tutti i comandi PowerShell di LagDoctor: controllo della sintassi (senza eseguirli).
4. Funzioni: processi all'avvio (lettura, spegni / riaccendi un servizio e un'attivita' di prova), manutenzione
   della game mode (sospesa e rimessa), Esplora risorse (AutoRestartShell), timer, processori, verifica completa.

    python tests/windows/collaudo_windows.py [cartella-risultati]
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, ROOT)
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "collaudo")
os.makedirs(OUT, exist_ok=True)
os.environ["LAGDOCTOR_DATA"] = tempfile.mkdtemp(prefix="ld-collaudo-")

from lagdoctor import tweaks as T  # noqa: E402  (carica anche extra_tweaks, virt_tweak, overlays)
from lagdoctor import extra_tweaks as XT  # noqa: E402

T.init(os.environ["LAGDOCTOR_DATA"])
RIGHE, FALLITI = [], []
CREATE_NO_WINDOW = 0x08000000


def esito(gruppo, nome, ok, dettaglio=""):
    """ok: True = passato, False = FALLITO, None = non applicabile su questo PC."""
    tag = {True: "OK", False: "FALLITO", None: "n/a"}[ok]
    RIGHE.append("%-8s %-22s %s%s" % (tag, gruppo, nome, (" - " + dettaglio) if dettaglio else ""))
    print(RIGHE[-1], flush=True)
    if ok is False:
        FALLITI.append("%s / %s: %s" % (gruppo, nome, dettaglio))


# ====================================================================== 1-2. ottimizzazioni
# voci che sul computer di GitHub NON si applicano (si controlla solo che lo stato si legga):
SOLO_LETTURA_CAT = {"Rete"}  # schede di rete e DNS: toccarle puo' staccare il computer di prova dalla rete
SOLO_LETTURA_IDS = {
    "app_onedrive",       # winget: scarica da internet
    "defender_excl",      # chiede una cartella
    "myth_dns",           # DNS delle schede di rete
    "myth_pagefile_off",  # toglie il file di paging al computer di prova
}


def snapshot(t):
    """I valori di Windows che la voce tocca, per controllare che Annulla li rimetta uguali."""
    s = {}
    try:
        if isinstance(t, T.RegTweak):
            for h, p, n, _typ, _v in t.values() or []:
                s["%s\\%s\\%s" % (h, p, n)] = repr(T.reg_read(h, p, n)[0])
        if isinstance(t, T.ServiceTweak):
            s["servizio %s" % t.service] = repr(T.reg_read("HKLM", T.ServiceTweak.KEY + "\\" + t.service, "Start")[0])
        if isinstance(t, T.PowerSettingTweak):
            for st in (t.setting,) + tuple(t.extra):
                s["powercfg %s" % st] = repr(T._powercfg_query(t.sub, st))
        if isinstance(t, (T.PowerPlanTweak, XT.PowerOverlayTweak)) or isinstance(t, T.PowerSettingTweak):
            s["piano attivo"] = T._active_scheme()
        if isinstance(t, T.BcdTweak):
            code, out = T.run(["bcdedit", "/enum", "{current}"])
            s["bcdedit %s" % t.option] = next((l.split()[-1] for l in out.splitlines()
                                               if l.split() and l.split()[0].lower() == t.option), None)
    except Exception as e:
        s["errore lettura"] = str(e)
    return s


def collauda_voce(t):
    gruppo = "Ottimizzazioni"
    nome = "%s (%s)" % (t.name, t.id)
    try:
        s0 = t.status()
    except Exception as e:
        return esito(gruppo, nome, False, "errore leggendo lo stato: %s" % e)
    if s0 not in (True, False, None):
        return esito(gruppo, nome, False, "stato non valido: %r" % (s0,))
    rischiosa = t.risk >= 2
    if (rischiosa or t.cat in SOLO_LETTURA_CAT or t.id in SOLO_LETTURA_IDS or t.vendor or t.kind == "overlay"
            or isinstance(t, (XT.AppxTweak, T.DefenderExclusionTweak))):
        return esito(gruppo, nome, True if s0 is not None else None,
                     "solo lettura dello stato: %s" % {True: "attiva", False: "non attiva", None: "non verificabile"}[s0])
    if s0 is None:
        return esito(gruppo, nome, None, "non verificabile su questo computer: non applicata")
    prima = snapshot(t)
    try:
        msg = T.apply_one(t.id)
    except Exception as e:
        txt = str(e)
        if "non disponibile" in txt or "non presente" in txt:
            return esito(gruppo, nome, None, "non disponibile su questo computer: %s" % txt[:120])
        T.load_state().get(t.id) and T.revert_one(t.id)
        return esito(gruppo, nome, False, "Applica: %s" % txt[:200])
    s1 = t.status()
    problemi = []
    if s1 is not True and not (t.reboot and s1 is False):
        problemi.append("dopo Applica risulta %r (atteso attiva)" % (s1,))
    try:
        T.revert_one(t.id)
    except Exception as e:
        problemi.append("Annulla: %s" % str(e)[:150])
    s2 = t.status()
    dopo = snapshot(t)
    if s2 != s0:
        problemi.append("dopo Annulla risulta %r (prima era %r)" % (s2, s0))
    diff = [k for k in set(prima) | set(dopo) if prima.get(k) != dopo.get(k)]
    if diff:
        problemi.append("Annulla non rimette com'era: " + "; ".join("%s %s -> %s" % (k, prima.get(k), dopo.get(k))
                                                                   for k in diff[:3]))
    if problemi:
        return esito(gruppo, nome, False, " | ".join(problemi))
    esito(gruppo, nome, True, "%s%s" % (msg, " (attiva dopo il riavvio)" if s1 is False else ""))


# ====================================================================== 3. sintassi PowerShell
def sintassi_powershell():
    from lagdoctor import autostart
    pezzi = []
    for t in T.BY_ID.values():
        for attr in ("on", "off", "check"):
            v = getattr(t, attr, None)
            if isinstance(v, str) and v.strip():
                pezzi.append(("%s.%s" % (t.id, attr), v))
    pezzi.append(("autostart.PS_TASKS", autostart.PS_TASKS))
    from lagdoctor import fixpc
    for f in fixpc.BY_ID.values():
        for i, st in enumerate(f["steps"]):
            if st["sh"] == "ps":
                pezzi.append(("fixpc.%s.%d" % (f["id"], i), st["c"]))
    script = os.path.join(OUT, "sintassi.ps1")
    files = []
    for i, (nome, codice) in enumerate(pezzi):
        f = os.path.join(OUT, "ps_%03d.ps1" % i)
        with open(f, "w", encoding="utf-8-sig") as fh:
            fh.write(codice)
        files.append((nome, f))
    with open(script, "w", encoding="utf-8-sig") as fh:
        fh.write("foreach ($f in $args) { $e = $null; $null = [System.Management.Automation.Language.Parser]::ParseFile("
                 "$f, [ref]$null, [ref]$e); if ($e) { 'ERR|' + $f + '|' + ($e | Select-Object -First 1).Message } "
                 "else { 'OK|' + $f } }")
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script] + [f for _n, f in files],
                       capture_output=True, text=True, timeout=300, creationflags=CREATE_NO_WINDOW)
    res = {}
    for line in r.stdout.splitlines():
        parts = line.strip().split("|", 2)
        if len(parts) >= 2:
            res[os.path.normcase(parts[1])] = parts[2] if parts[0] == "ERR" else None
    for nome, f in files:
        k = os.path.normcase(f)
        if k not in res:
            esito("Sintassi PowerShell", nome, False, "non controllata (%s)" % (r.stderr.strip()[-150:] or "?"))
        elif res[k]:
            esito("Sintassi PowerShell", nome, False, res[k])
    esito("Sintassi PowerShell", "%d comandi controllati" % len(files),
          not any(f.startswith("Sintassi PowerShell") for f in FALLITI))


# ====================================================================== 4. funzioni
def prova(nome):
    def deco(fn):
        def run():
            try:
                r = fn()
                esito("Funzioni", nome, True if r is None else r[0], "" if r is None else r[1])
            except AssertionError as e:
                esito("Funzioni", nome, False, str(e) or "controllo non superato")
            except Exception as e:
                esito("Funzioni", nome, False, "%s: %s" % (type(e).__name__, str(e)[:200]))
                traceback.print_exc()
        return run
    return deco


@prova("Processi all'avvio: lettura di servizi e attivita' pianificate")
def f_autostart_lettura():
    from lagdoctor import autostart
    r = autostart.list_items(include_windows=True)
    svc = [i for i in r["items"] if i["kind"] == "svc"]
    task = [i for i in r["items"] if i["kind"] == "task"]
    assert not r["error"], r["error"]
    assert len(svc) >= 20 and len(task) >= 5, "letti %d servizi e %d attivita'" % (len(svc), len(task))
    return True, "%d servizi, %d attivita'" % (len(svc), len(task))


@prova("Processi all'avvio: spegni e riaccendi un servizio di prova")
def f_autostart_servizio():
    from lagdoctor import autostart
    nome = "LagDoctorCollaudo"
    T.run(["sc", "create", nome, "binPath=", r"C:\Windows\System32\svchost.exe -k LagDoctorCollaudo", "start=", "delayed-auto"])
    try:
        prima = (T.reg_read("HKLM", r"SYSTEM\CurrentControlSet\Services\%s" % nome, "Start")[0],
                 T.reg_read("HKLM", r"SYSTEM\CurrentControlSet\Services\%s" % nome, "DelayedAutostart")[0])
        assert prima[0] == 2, "servizio di prova non creato (%r)" % (prima,)
        autostart.set_enabled("svc", nome, False)
        assert T.reg_read("HKLM", r"SYSTEM\CurrentControlSet\Services\%s" % nome, "Start")[0] == 4, "non disattivato"
        autostart.set_enabled("svc", nome, True)
        dopo = (T.reg_read("HKLM", r"SYSTEM\CurrentControlSet\Services\%s" % nome, "Start")[0],
                T.reg_read("HKLM", r"SYSTEM\CurrentControlSet\Services\%s" % nome, "DelayedAutostart")[0])
        assert dopo == prima, "dopo la riaccensione %r, prima %r" % (dopo, prima)
    finally:
        T.run(["sc", "delete", nome])


@prova("Processi all'avvio: spegni e riaccendi un'attivita' pianificata di prova")
def f_autostart_attivita():
    from lagdoctor import autostart
    nome = "\\LagDoctorCollaudo"
    T.run(["schtasks", "/Create", "/TN", nome, "/TR", r"C:\Windows\System32\cmd.exe /c exit", "/SC", "ONLOGON", "/F"])
    try:
        stato = lambda: T.ps("(Get-ScheduledTask -TaskPath '\\' -TaskName 'LagDoctorCollaudo').State")[1].strip()
        assert stato() == "Ready", "attivita' di prova non creata (%s)" % stato()
        autostart.set_enabled("task", nome, False)
        assert stato() == "Disabled", "non disattivata (%s)" % stato()
        autostart.set_enabled("task", nome, True)
        assert stato() == "Ready", "non riattivata (%s)" % stato()
    finally:
        T.run(["schtasks", "/Delete", "/TN", nome, "/F"])


@prova("Game mode: manutenzione di Windows sospesa e rimessa com'era")
def f_manutenzione():
    from lagdoctor import gamemode as G
    def stati():
        lst = ",".join("'%s'" % t.replace("'", "''") for t in G.MAINT_TASKS)
        out = T.ps("foreach ($p in @(%s)) { $i = $p.LastIndexOf('\\'); $t = Get-ScheduledTask -TaskPath "
                   "$p.Substring(0, $i + 1) -TaskName $p.Substring($i + 1) -ErrorAction SilentlyContinue; "
                   "if ($t) { $p + '=' + $t.State } }" % lst, timeout=120)[1]
        return dict(l.strip().split("=", 1) for l in out.splitlines() if "=" in l)
    prima = stati()
    reg0 = T.reg_read("HKLM", G.MAINT_KEY, "MaintenanceDisabled")[0]
    e = G.Engine()
    e.j = {"bg": {}, "services": [], "qos": [], "restart": []}
    e._pause_maintenance()
    durante = stati()
    sospese = [p for p in e.j.get("maint_tasks", []) if durante.get(p) == "Disabled"]
    assert len(sospese) == len(e.j.get("maint_tasks", [])), "sospese %d su %d" % (len(sospese), len(e.j.get("maint_tasks", [])))
    assert T.reg_read("HKLM", G.MAINT_KEY, "MaintenanceDisabled")[0] == 1, "Manutenzione automatica non sospesa"
    e.deactivate("collaudo")
    dopo = stati()
    diff = [p for p in prima if prima[p] != dopo.get(p)]
    assert not diff, "non rimesse com'erano: %s" % diff[:3]
    assert T.reg_read("HKLM", G.MAINT_KEY, "MaintenanceDisabled")[0] == reg0, "Manutenzione automatica non rimessa"
    return True, "%d attivita' sospese e rimesse, %d presenti" % (len(sospese), len(prima))


@prova("Game mode: riavvio automatico di Esplora risorse sospeso e rimesso")
def f_autorestart():
    from lagdoctor import gamemode as G
    v0 = T.reg_read("HKLM", G.WINLOGON_KEY, "AutoRestartShell")[0]
    prev = G._autorestart_shell(0)
    assert T.reg_read("HKLM", G.WINLOGON_KEY, "AutoRestartShell")[0] == 0
    G._autorestart_shell(restore=prev)
    assert T.reg_read("HKLM", G.WINLOGON_KEY, "AutoRestartShell")[0] == v0, "valore non rimesso"
    m0 = G._minimized_arrange()
    G._minimized_arrange(m0)
    return True, "AutoRestartShell %r, disposizione finestre ridotte %r" % (v0, m0)


@prova("Timer di sistema leggibile")
def f_timer():
    v = XT.timer_now_ms()
    assert v is not None and 0.4 <= v <= 16, "timer %r" % v
    return True, "%.3f ms" % v


@prova("Processore: struttura, affinita', modalita' efficienza, schede video")
def f_cpu():
    from lagdoctor import cputopo, gamemode as G
    d, e = cputopo.decide(), cputopo.eco_decide()
    assert d.get("kind") and e.get("why"), (d, e)
    return True, "%s, %s | efficienza: %s | GPU: %s" % (d.get("cpu"), d.get("kind"), e.get("apply"), G.gpu_names())


@prova("Verifica completa: tutte le voci controllate senza errori")
def f_verifica():
    from lagdoctor import verifica
    st = {t.id: t.status() for t in T.for_vendor(None)}
    rows = verifica.check_tweaks(st, None) + verifica.check_other()
    assert rows and all(r["res"] in ("ok", "ko", "reboot", "off", "unk", "manual") for r in rows)
    ko = [r["name"] for r in rows if r["res"] == "ko"]
    assert not ko, "risultano problemi senza aver applicato niente: %s" % ko[:5]
    return True, "%d righe" % len(rows)


@prova("Icone dei giochi: estratte dal file .exe (PNG con trasparenza)")
def f_icone():
    import struct
    from lagdoctor import gameicons
    win = os.environ.get("WINDIR", r"C:\Windows")
    prove = [("t-notepad", os.path.join(win, "System32", "notepad.exe")), ("t-explorer", os.path.join(win, "explorer.exe"))]
    for gid, _e in prove:
        try:
            os.remove(gameicons.path_for(gid))
        except OSError:
            pass
    ok = gameicons.extract(prove, timeout=180)
    assert set(ok) == {g for g, _e in prove}, "icone non estratte: %s" % sorted({g for g, _e in prove} - set(ok))
    info = []
    for gid, _e in prove:
        data = open(gameicons.path_for(gid), "rb").read()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", "non e' un PNG"
        w, h, depth, ctype = struct.unpack(">IIBB", data[16:26])
        assert w >= 32 and h >= 32 and ctype == 6, "PNG %dx%d tipo %d (serve RGBA)" % (w, h, ctype)
        info.append("%s %dx%d" % (gid, w, h))
    # eseguibile principale di una cartella: deve scegliere quello "vero", non uninstall/crash
    d = os.path.join(OUT, "giocofinto")
    os.makedirs(os.path.join(d, "bin"), exist_ok=True)
    for name, size in (("unins000.exe", 5), ("CrashReporter.exe", 9), ("bin/GiocoFinto-Win64-Shipping.exe", 3), ("Launcher.exe", 8)):
        with open(os.path.join(d, name), "wb") as f:
            f.write(b"\0" * size * 2**20)
    exe = gameicons.find_exe({"id": "x", "name": "Gioco Finto", "dir": d})
    assert exe and exe.endswith("GiocoFinto-Win64-Shipping.exe"), "scelto %s" % exe
    return True, ", ".join(info) + ", eseguibile del gioco scelto bene"


@prova("Riconoscimento dei giochi aperti (Analizza gioco)")
def f_giochi_aperti():
    import subprocess as sp
    from lagdoctor import gamedetect
    fs = gamedetect.fullscreen_pids()
    p = sp.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        r = gamedetect.candidates()
        assert set(r) >= {"items", "others", "icons_pending"}
        nomi = [i["name"].lower() for i in r["items"]]
        assert not any(n in gamedetect.NON_GAME_APPS for n in nomi), "programmi non giochi tra i giochi: %s" % nomi
        assert all(i.get("kind") in ("lib", "folder", "fullscreen") for i in r["items"])
    finally:
        p.kill()
    return True, "%d giochi, %d altri programmi, %d finestre a schermo intero" % (len(r["items"]), len(r["others"]), len(fs))


def fixpc_veri():
    """Fix PC: esegue davvero i fix sicuri (non tolgono Internet e non riavviano) e controlla che riescano.
    Come nell'exe di LagDoctor (che non ha console), l'uscita dei comandi viene letta dallo schermo di una console
    nascosta: si controlla che succeda davvero e che la percentuale di SFC arrivi fluida."""
    import ctypes
    import re
    from lagdoctor import conrun, fixpc
    ctypes.WinDLL("kernel32").FreeConsole()  # l'exe di LagDoctor non ha console: qui la si toglie per fare lo stesso
    esito("Fix PC", "lettura dalla console nascosta disponibile", conrun.available())
    for f in fixpc.BY_ID.values():
        if not f["ci"]:
            continue
        try:
            r = fixpc.run(f["id"])
            ultima = (r["out"].strip().splitlines() or [""])[-1][:120]
            shell = [m for m, st in zip(r["modes"], [x for x in f["steps"] if x["sh"] != "py"])]
            ok = r["ok"] and all(m == "console" for m in shell)
            esito("Fix PC", f["t"], ok, "%s s, %s | %s | %s" % (r["secs"], ",".join(r["modes"]), r["res"], ultima))
            if not ok:
                print(r["out"][-1500:], file=sys.stderr)
        except Exception as e:
            esito("Fix PC", f["t"], False, "%s: %s" % (type(e).__name__, str(e)[:200]))
            traceback.print_exc()
    # comandi con barra di avanzamento (non riparano niente): percentuale fluida ed esito chiaro
    prove = [("SFC (sfc /verifyonly)", "sfc /verifyonly", "sfc", 15, "sfc"),
             ("DISM ScanHealth", "DISM /Online /Cleanup-Image /ScanHealth", "dism_check", 5, "a posto"),
             ("Controllo disco (chkdsk C: /scan)", "chkdsk C: /scan", "chk_scan", 3, "non ha errori"),
             ("Ottimizza dischi (defrag /C /O /U)", "defrag /C /O /U", None, 0, None)]  # sul disco virtuale non c'e' niente da fare
    for nome, comando, res, minimo, atteso in prove:
        fixpc.BY_ID["_p"] = {"id": "_p", "t": nome, "r": False, "ro": True, "res": res,
                             "steps": [fixpc.cmd(comando, soft=res is not None)]}
        viste = []

        def live(text, viste=viste):
            m = re.findall(r"(\d{1,3})(?:[.,]\d)?\s*(?:%|percent)", text)
            if m and (not viste or viste[-1] != int(m[-1])):
                viste.append(int(m[-1]))
        try:
            r = fixpc.run("_p", live=live)
            if atteso == "sfc":  # l'esito deve corrispondere a quello che SFC ha scritto davvero
                trovati = "found integrity violations" in r["out"] or "corrupt files" in r["out"]
                pulito = "did not find any integrity violations" in r["out"]
                giusto = (trovati and "danneggiati" in r["res"] and not r["ok"]) or (pulito and "a posto" in r["res"] and r["ok"])
                ok = giusto and len(set(viste)) >= minimo and r["modes"] == ["console"]
            else:
                ok = r["ok"] and len(set(viste)) >= minimo and (atteso is None or atteso in r["res"]) and r["modes"] == ["console"]
            esito("Fix PC", "%s: percentuale fluida ed esito chiaro" % nome, ok,
                  "%s s, %d percentuali diverse (%s), esito: %s" % (r["secs"], len(set(viste)), viste[:5] + ["..."] + viste[-3:], r["res"]))
            print("----- %s -----\n%s\n" % (nome, r["out"][-1200:]), file=sys.stderr)
        except Exception as e:
            esito("Fix PC", "%s: percentuale fluida ed esito chiaro" % nome, False, "%s: %s" % (type(e).__name__, str(e)[:200]))
            traceback.print_exc()


def main():
    t0 = time.time()
    print("Collaudo su Windows vero - LagDoctor", file=sys.stderr)
    for t in sorted(T.for_vendor(None), key=lambda x: (T.CAT_ORDER.index(x.cat) if x.cat in T.CAT_ORDER else 99, x.id)):
        collauda_voce(t)
    sintassi_powershell()
    for f in (f_autostart_lettura, f_autostart_servizio, f_autostart_attivita, f_manutenzione, f_autorestart, f_timer,
              f_cpu, f_verifica, f_icone, f_giochi_aperti):
        f()
    fixpc_veri()  # per ultimo: toglie la console a questo processo, come nell'exe di LagDoctor
    rimaste = T.applied_by_us()
    if rimaste:  # nessuna voce deve restare applicata alla fine
        esito("Pulizia", "voci rimaste applicate", False, ", ".join(rimaste))
        for tid in rimaste:
            try:
                T.revert_one(tid)
            except Exception:
                pass
    ok = sum(1 for r in RIGHE if r.startswith("OK"))
    na = sum(1 for r in RIGHE if r.startswith("n/a"))
    riepilogo = "\n%d controlli: %d OK, %d FALLITI, %d non applicabili su questo computer (%.0f s)" % (
        len(RIGHE), ok, len(FALLITI), na, time.time() - t0)
    with open(os.path.join(OUT, "collaudo-windows.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(RIGHE) + "\n" + riepilogo + "\n")
        if FALLITI:
            f.write("\nFALLITI:\n" + "\n".join(FALLITI) + "\n")
    print(riepilogo)
    if FALLITI:
        print("\nFALLITI:\n" + "\n".join(FALLITI))
    return 1 if FALLITI else 0


if __name__ == "__main__":
    sys.exit(main())
