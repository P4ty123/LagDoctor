"""Collaudo simulato di LagDoctor (gira su Linux, anche su GitHub a ogni modifica).

Ogni prova usa un Windows finto (registro in mock/winreg.py, powercfg/bcdedit/processi simulati) e controlla la logica
del programma: per ogni ottimizzazione applica -> risulta attiva -> annulla -> tutto come prima; poi game mode,
overlay, guardiano degli overlay, processi all'avvio, Esplora risorse, piani energetici, processori.
Uscita 1 se una prova fallisce.

    python tests/sim/run_all.py
"""
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROVE = [
    ("audit_tweaks.py", "tutte le ottimizzazioni di Windows: applica / verifica / annulla"),
    ("audit_driver.py", "voci dei driver NVIDIA e AMD"),
    ("t_follow.py", "core parking e boost seguono il cambio di piano energetico"),
    ("t_vfx.py", "effetti visivi"),
    ("t_ov.py", "overlay: spegnimento e ripristino (Steam, EA, Ubisoft, RivaTuner)"),
    ("t_guard_ov.py", "guardiano degli overlay"),
    ("t_gamemode.py", "game mode: attivazione, ripristino, crash, spegnimento durante il gioco"),
    ("t_gm_new.py", "game mode: manutenzione, scheda video preferita, memoria standby"),
    ("t_shell.py", "game mode: Esplora risorse chiuso e riaperto"),
    ("t_autostart2.py", "processi in background all'avvio"),
    ("t_cputopo.py", "processori: affinita' dei core"),
    ("t_eco.py", "processori: modalita' efficienza"),
    ("t_fixpc.py", "Fix PC: catalogo dei comandi ed esecuzione"),
]


def main():
    if os.name == "nt":
        print("Il collaudo simulato usa un Windows finto e va eseguito su Linux (su Windows c'e' tests/windows).")
        return 0
    falliti = []
    for nome, cosa in PROVE:
        t0 = time.time()
        env = dict(os.environ, LAGDOCTOR_DATA=tempfile.mkdtemp(prefix="ld-sim-"))
        try:
            r = subprocess.run([sys.executable, nome], cwd=HERE, env=env, capture_output=True, text=True, timeout=600)
            ok, out = r.returncode == 0, (r.stdout + r.stderr)
        except subprocess.TimeoutExpired:
            ok, out = False, "TEMPO SCADUTO"
        print("%s %-18s %5.1fs  %s" % ("OK      " if ok else "FALLITO ", nome, time.time() - t0, cosa))
        if not ok:
            falliti.append(nome)
            print("\n".join("    | " + l for l in out.strip().splitlines()[-25:]))
    # i processi di prova che girano in background (guardiano degli overlay) non devono restare aperti
    subprocess.run(["pkill", "-f", "lagdoctor_gui.py --overlay"], capture_output=True)
    print("\n%d prove, %d fallite%s" % (len(PROVE), len(falliti), (": " + ", ".join(falliti)) if falliti else ""))
    return 1 if falliti else 0


if __name__ == "__main__":
    sys.exit(main())
