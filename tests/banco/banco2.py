"""Banco di prova: game mode con programmi in background a 'Inferiore al normale' (attuale) o a 'Bassa'."""
import json, os, shutil, statistics, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT); sys.path.insert(0, HERE)
import banco as B  # noqa: E402
from lagdoctor import gamemode as GM, games, paths  # noqa: E402
import psutil  # noqa: E402

CLASSES = {"inferiore": 0x4000, "bassa": 0x40}


def set_class(name):
    c = GM.load_config(); c["opts"]["bg_class"] = CLASSES[name]; GM.save_config(c)


def musica_read(path):
    try:
        n, g, w = open(path).read().split()
        return int(n), int(g), float(w)
    except Exception:
        return 0, 0, 0.0


def main():
    B.compile_exe(os.path.join(HERE, "FakeGame.cs"), B.GAME_ON)
    dist = r"C:\Temp\Disturbo\BrowserSim.exe"; B.compile_exe(os.path.join(HERE, "Disturbo.cs"), dist)
    mus = r"C:\Temp\Musica\MusicaSim.exe"; B.compile_exe(os.path.join(HERE, "Musica.cs"), mus)
    os.makedirs(paths.DATA_DIR, exist_ok=True)
    c = GM.load_config(); c["enabled"] = True
    c["games"] = [dict(games.manual(B.GAME_ON), on=True, priority="high", anticheat=False)]; GM.save_config(c)
    set_class("inferiore")
    daemon = subprocess.Popen(paths.gui_cmd("--gamemode"), cwd=ROOT); time.sleep(8)
    cores = os.cpu_count()
    dist_p = [subprocess.Popen([dist]) for _ in range(cores)]
    res = {k: [] for k in CLASSES}
    try:
        order = []
        for i in range(4):
            order += [("inferiore", i), ("bassa", i)] if i % 2 == 0 else [("bassa", i), ("inferiore", i)]
        for cls, i in order:
            set_class(cls); time.sleep(6)  # la game mode rilegge le opzioni
            mfile = os.path.join(B.OUT, "musica_%s_%d.txt" % (cls, i))
            m = subprocess.Popen([mus, mfile])
            time.sleep(2)
            r = B.run_game(B.GAME_ON, cls, i, True)
            # stato della musica durante la partita misurata
            n, g, w = musica_read(mfile)
            m.kill()
            prios = {}
            r["musica_glitch"], r["musica_worst"] = g, w
            res[cls].append(r)
            print("%-9s giro %d: %6.1f FPS, 1%% low %6.1f, 0,1%% low %6.1f, peggior frame %5.1f ms | musica: %d pezzi in "
                  "ritardo su %d, ritardo peggiore %.0f ms  (%s)" % (cls, i, r["fps"], r["low1"], r["low01"], r["max_ms"],
                                                                     g, n, w, r["note"]), flush=True)
    finally:
        for p in dist_p:
            p.kill()
        c = GM.load_config(); c["enabled"] = False; GM.save_config(c); time.sleep(8)
        daemon.kill()
    print()
    for cls, name in (("inferiore", "Inferiore al normale (attuale)"), ("bassa", "Bassa")):
        L = res[cls]; m = lambda k: statistics.mean(x[k] for x in L)
        print("%-32s %.1f FPS medi, 1%% low %.1f, 0,1%% low %.1f, peggior frame %.1f ms | musica in ritardo %.0f volte, "
              "ritardo peggiore %.0f ms" % (name, m("fps"), m("low1"), m("low01"), m("max_ms"), m("musica_glitch"),
                                            m("musica_worst")))
    json.dump(res, open(os.path.join(B.OUT, "risultati2.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
