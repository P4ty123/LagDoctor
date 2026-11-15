"""Collaudo automatico di TUTTE le ottimizzazioni su un Windows simulato.

Per ogni voce: la porto nello stato 'non attiva', applico, controllo che risulti attiva, annullo e controllo che il
registro (e lo stato simulato di powercfg / bcdedit / app) torni ESATTAMENTE com'era. Le voci che dipendono da
comandi PowerShell veri (CmdTweak) sono controllate a parte, leggendo i comandi.
"""
import os as _os, sys as _sys  # collaudo simulato: Windows finto (mock) + codice di LagDoctor
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.abspath(_os.path.join(_HERE, "..", "..")))
_sys.path.insert(0, _os.path.join(_HERE, "mock"))

import copy
import os
import re
import sys
import tempfile
import uuid

S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "mock"))
os.environ["LAGDOCTOR_DATA"] = tempfile.mkdtemp()
import winreg  # mock
from lagdoctor import tweaks as T
from lagdoctor import extra_tweaks as XT
from lagdoctor import driver_tweaks as DT  # noqa

T.init(os.environ["LAGDOCTOR_DATA"])
_IF = r"system\currentcontrolset\services\tcpip\parameters\interfaces"
winreg.DB[("HKLM", _IF)] = {}
winreg.DB[("HKLM", _IF + r"\{aaaa-1111}")] = {"DhcpIPAddress": ("192.168.1.20", 1)}
winreg.DB[("HKLM", _IF + r"\{bbbb-2222}")] = {"IPAddress": (["0.0.0.0"], 7)}
BAL = "381b4222-f694-41f0-9685-ff5bb260df2e"
W = {"scheme": BAL, "schemes": {BAL: "Bilanciato", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c": "Prestazioni elevate"},
     "power": {}, "overlay": "00000000-0000-0000-0000-000000000000", "bcd": {},
     "appx": set(), "cmds": []}


def fake_run(args, timeout=60):
    a = [str(x) for x in args]
    W["cmds"].append(" ".join(a))
    if a[0] == "powercfg":
        op = a[1].lower()
        if op == "/getactivescheme":
            return 0, "GUID combinazione per il risparmio di energia: %s  (%s)" % (W["scheme"], W["schemes"][W["scheme"]])
        if op == "/setactive":
            g = a[2].lower()
            if g == "scheme_current":
                return 0, ""
            if g not in W["schemes"]:
                return 1, "Parametri non validi"
            W["scheme"] = g
            return 0, ""
        if op == "/list":
            return 0, "\n".join("GUID combinazione per il risparmio di energia: %s  (%s)" % (g, n) for g, n in W["schemes"].items())
        if op in ("-duplicatescheme", "/duplicatescheme"):
            g = str(uuid.uuid4())
            W["schemes"][g] = "Prestazioni ottimali"
            return 0, "GUID combinazione per il risparmio di energia: %s  (Prestazioni ottimali)" % g
        if op in ("/query", "/qh"):
            k = (W["scheme"], a[3].lower(), a[4].lower())
            ac, dc = W["power"].get(k, (1, 1))
            return 0, ("Indice impostazione alimentazione CA corrente: 0x%08x\n"
                       "Indice impostazione alimentazione CC corrente: 0x%08x" % (ac, dc))
        if op in ("/setacvalueindex", "/setdcvalueindex"):
            k = (W["scheme"], a[3].lower(), a[4].lower())
            ac, dc = W["power"].get(k, (1, 1))
            v = int(a[5])
            W["power"][k] = (v, dc) if op == "/setacvalueindex" else (ac, v)
            return 0, ""
        if op == "/getactiveoverlayscheme":
            return 0, "GUID combinazione per il risparmio di energia attiva: %s" % W["overlay"]
        if op == "/overlaysetactive":
            W["overlay"] = a[2].lower()
            return 0, ""
        return 0, ""
    if a[0] == "bcdedit":
        if a[1] == "/enum":
            lines = ["Caricamento di Windows", "-------------------", "identificatore           {current}"]
            for k, v in W["bcd"].items():
                lines.append("%-24s %s" % (k, {"yes": "S�", "true": "S�"}.get(v.lower(), v)))  # "Si'" rovinato
            return 0, "\n".join(lines)
        if a[1] == "/set":
            W["bcd"][a[3].lower()] = a[4]
            return 0, "Operazione completata."
        if a[1] == "/deletevalue":
            W["bcd"].pop(a[3].lower(), None)
            return 0, "Operazione completata."
    return 0, ""


def fake_ps(cmd, timeout=60):
    W["cmds"].append("PS " + cmd[:80])
    if cmd.strip() == "Get-AppxPackage | ForEach-Object Name":
        return 0, "\n".join(sorted(W["appx"]))
    m = re.match(r"Get-AppxPackage -Name '([^']+)' \| Remove-AppxPackage", cmd)
    if m:
        W["appx"].discard(m.group(1).lower())
        return 0, ""
    m = re.search(r"Get-AppxPackage -AllUsers -Name '([^']+)'", cmd)
    if m:
        W["appx"].add(m.group(1).lower())
        return 0, ""
    return 0, ""


for mod in (T, XT):
    mod.run, mod.ps = fake_run, fake_ps


def snapshot():
    st = copy.deepcopy({k: W[k] for k in ("scheme", "power", "overlay", "bcd", "appx")})
    st["power"] = {k: v for k, v in st["power"].items() if v != (1, 1)}  # (1, 1) = valore predefinito del finto powercfg
    return {k: v for k, v in copy.deepcopy(winreg.DB).items() if v}, st


def make_inactive(t):
    """Porta la voce nello stato 'non attiva' (come un Windows appena installato)."""
    if isinstance(t, T.ServiceTweak):
        cur = {4: 2}.get(t.start, 4)
        T.reg_write("HKLM", T.ServiceTweak.KEY + "\\" + t.service, "Start", 4, cur)
    elif isinstance(t, T.RegTweak) and getattr(t, "active", None) is not None:
        # stato per effetto: provo "assente", poi 0, poi un valore diverso, finche' risulta non attiva
        for mode in ("del", "zero", "plus"):
            for h, p, n, typ, v in t.values():
                if mode == "del":
                    T.reg_delete(h, p, n)
                elif isinstance(v, int):
                    T.reg_write(h, p, n, typ, 0 if mode == "zero" else v + 7)
            if t.status() is False:
                break
    elif isinstance(t, T.RegTweak):
        for h, p, n, typ, v in t.values():
            if isinstance(v, int):
                T.reg_write(h, p, n, typ, v + 7 if v < 1000 else v - 1)
            elif isinstance(v, str):
                T.reg_write(h, p, n, typ, "valore-di-prima")
            else:
                T.reg_delete(h, p, n)
    elif isinstance(t, T.PowerSettingTweak):
        W["power"][(W["scheme"], t.sub.lower(), t.setting.lower())] = (t.value + 1, t.value + 1)
    elif isinstance(t, T.BcdTweak):
        W["bcd"].pop(t.option, None)
    elif isinstance(t, XT.AppxTweak):
        for p in t.packages:
            W["appx"].add(p.lower())
        XT._APPX_CACHE["names"] = None
    elif isinstance(t, XT.PowerOverlayTweak):
        W["scheme"] = BAL
        W["overlay"] = "00000000-0000-0000-0000-000000000000"
    elif type(t).__name__ == "PowerSaverFix":
        W["schemes"]["a1841308-3541-4fab-bc81-f71556f20b4a"] = "Risparmio di energia"
        W["scheme"] = "a1841308-3541-4fab-bc81-f71556f20b4a"
    elif isinstance(t, T.PowerPlanTweak):
        W["scheme"] = BAL


SKIP = {"CmdTweak": "comandi PowerShell veri: controllati leggendo i comandi",
        "NvTweak": "profilo del driver NVIDIA: controllato a parte",
        "AmdTweak": "impostazioni del driver AMD: controllate a parte",
        "OverlayItem": "collaudate a parte (file dei programmi e processi)",
        "TimerResTweak": "collaudato a parte (attivita' + timer reale)",
        "VirtualizationTweak": "funzionalita' di Windows: controllata leggendo i comandi",
        "DefenderExclusionTweak": "chiede la cartella dei giochi: controllata leggendo i comandi",
        "RuntimeRegTweak": "stato letto da Windows mentre gira: controllato leggendo i comandi",
        "VisualFxTweak": "collaudato a parte (t_vfx.py)"}
res = {"ok": [], "ko": [], "skip": []}
for t in sorted(T.BY_ID.values(), key=lambda x: x.id):
    k = type(t).__name__
    if k in SKIP:
        res["skip"].append((t.id, SKIP[k]))
        continue
    try:
        make_inactive(t)
        XT._APPX_CACHE["names"] = None
        s0 = t.status()
        before = snapshot()
        b = t.apply()
        XT._APPX_CACHE["names"] = None
        s1 = t.status()
        t.revert(b)
        XT._APPX_CACHE["names"] = None
        s2 = t.status()
        after = snapshot()
        probs = []
        if s0 is not False:
            probs.append("prima di applicare risulta %r (atteso False)" % s0)
        if s1 is not True:
            probs.append("dopo Applica risulta %r (atteso True)" % s1)
        if s2 is not False:
            probs.append("dopo Annulla risulta %r (atteso False)" % s2)
        if before != after:
            d = [x for x in set(before[0]) | set(after[0]) if before[0].get(x) != after[0].get(x)]
            probs.append("Annulla non rimette tutto com'era: %s %s" % (d[:3], "" if before[1] == after[1] else "(stato powercfg/bcd/app diverso)"))
        (res["ko"] if probs else res["ok"]).append((t.id, "; ".join(probs)))
    except Exception as e:
        res["ko"].append((t.id, "ERRORE %s: %s" % (type(e).__name__, e)))

print("COLLAUDATE: %d   OK: %d   PROBLEMI: %d   controllate a parte: %d" % (
    len(res["ok"]) + len(res["ko"]), len(res["ok"]), len(res["ko"]), len(res["skip"])))
for i, p in res["ko"]:
    print("  PROBLEMA", i, "->", p)
from collections import Counter
print("a parte:", Counter(r for _i, r in res["skip"]))
sys.exit(1 if res["ko"] else 0)
