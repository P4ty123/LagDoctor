"""Banco di prova della game mode su Windows (GitHub): finto gioco + programmi in background, senza e con game mode.
Non fa parte del collaudo: si lancia solo dal ramo test/banco-gamemode."""
import json, os, shutil, statistics, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from lagdoctor import gamemode as GM, games, paths  # noqa: E402

OUT = os.path.join(ROOT, "banco"); os.makedirs(OUT, exist_ok=True)
GAME_ON = r"C:\Giochi\Banco\FakeGame.exe"        # registrato nella game mode
GAME_OFF = r"C:\Temp\NonRegistrato\FakeGame.exe"  # stesso programma, cartella non registrata
SECS, WARM, ROUNDS = 40, 10, 4


def compile_exe(src, out, extra=""):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    ps = ("Add-Type -Path '%s' -OutputAssembly '%s' -OutputType ConsoleApplication %s" % (src, out, extra))
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    assert os.path.isfile(out), r.stdout + r.stderr


def stats(path):
    ft = [float(l) for l in open(path) if l.strip()]
    s = sorted(ft); n = len(s)
    med = statistics.median(s)
    p99 = s[min(n - 1, int(n * 0.99))]; p999 = s[min(n - 1, int(n * 0.999))]
    return {"frame": n, "fps": 1000 * n / sum(ft), "low1": 1000 / p99, "low01": 1000 / p999,
            "scatti": sum(1 for f in ft if f > 2 * med), "max_ms": s[-1]}


def status():
    try:
        return json.load(open(GM.STATUS))
    except Exception:
        return {}


def run_game(exe, tag, i, gm):
    csv = os.path.join(OUT, "%s_%d.csv" % (tag, i))
    p = subprocess.Popen([exe, csv, str(SECS), str(WARM)])
    note = ""
    if gm:
        t0 = time.time()
        while time.time() - t0 < 15 and not status().get("active"):
            time.sleep(0.5)
        note = "game mode attiva dopo %.1fs" % (time.time() - t0) if status().get("active") else "GAME MODE NON ATTIVA"
    else:
        time.sleep(3)
        note = "game mode attiva (sbagliato!)" if status().get("active") else "game mode non attiva"
    p.wait()
    if gm:  # aspetto che la game mode rimetta tutto com'era prima del giro dopo
        t0 = time.time()
        while time.time() - t0 < 120 and status().get("active"):
            time.sleep(1)
        time.sleep(3)
    r = stats(csv); r["note"] = note
    return r


def main():
    compile_exe(os.path.join(HERE, "FakeGame.cs"), GAME_ON)
    os.makedirs(os.path.dirname(GAME_OFF), exist_ok=True); shutil.copy(GAME_ON, GAME_OFF)
    dist = os.path.join(r"C:\Temp\Disturbo", "BrowserSim.exe")
    compile_exe(os.path.join(HERE, "Disturbo.cs"), dist)
    cores = os.cpu_count()
    print("Processori logici:", cores)

    c = GM.load_config(); c["enabled"] = True
    g = dict(games.manual(GAME_ON), on=True, priority="high")
    c["games"] = [g]; GM.save_config(c)
    print("Gioco registrato:", g)
    print("Opzioni:", {k: v for k, v in c["opts"].items()})

    res = {"base": [], "off": [], "on": []}
    # riferimento: PC libero, niente in background
    res["base"].append(run_game(GAME_OFF, "base", 0, False))

    daemon = subprocess.Popen(paths.gui_cmd("--gamemode"), cwd=ROOT)
    time.sleep(8)
    dist_p = [subprocess.Popen([dist]) for _ in range(cores)]
    time.sleep(3)
    try:
        order = []
        for i in range(ROUNDS):
            order += [("off", i), ("on", i)] if i % 2 == 0 else [("on", i), ("off", i)]
        for tag, i in order:
            r = run_game(GAME_ON if tag == "on" else GAME_OFF, tag, i, tag == "on")
            res[tag].append(r)
            print("%-4s giro %d: %6.1f FPS medi, 1%% low %6.1f, 0,1%% low %6.1f, scatti %4d, peggior frame %6.1f ms  (%s)"
                  % (tag, i, r["fps"], r["low1"], r["low01"], r["scatti"], r["max_ms"], r["note"]), flush=True)
            if tag == "on":
                st = status()
                for a in (st.get("actions") or [])[:20]:
                    print("        ", a)
    finally:
        for p in dist_p:
            p.kill()
        c = GM.load_config(); c["enabled"] = False; GM.save_config(c)
        time.sleep(8)
        try:
            daemon.kill()
        except Exception:
            pass
    print()
    b = res["base"][0]
    print("RIFERIMENTO (PC libero):  %.1f FPS medi, 1%% low %.1f, 0,1%% low %.1f, scatti %d"
          % (b["fps"], b["low1"], b["low01"], b["scatti"]))
    for tag, name in (("off", "SENZA game mode"), ("on", "CON game mode")):
        L = res[tag]
        m = lambda k: statistics.mean(x[k] for x in L)
        print("%-16s (programmi in background al 100%%): %.1f FPS medi, 1%% low %.1f, 0,1%% low %.1f, scatti %.0f, "
              "peggior frame %.1f ms" % (name, m("fps"), m("low1"), m("low01"), m("scatti"), m("max_ms")))
    json.dump(res, open(os.path.join(OUT, "risultati.json"), "w"), indent=1)
    try:
        shutil.copy(GM.LOG, os.path.join(OUT, "gamemode.log"))
    except Exception:
        pass


if __name__ == "__main__":
    main()
