"""Impostazioni di LagDoctor: avvio con Windows (anche ridotto a icona)."""
import json
import os
import subprocess

from . import paths, schedtask

FILE = paths.data("impostazioni.json")
TASK = "LagDoctor Avvio"
DEFAULTS = {"autostart": False, "minimized": True, "animations": True, "new_window": True, "delay": 15}
MAX_DELAY = 60  # secondi
CREATE_NO_WINDOW = 0x08000000


def _run(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding=("oem" if os.name == "nt" else None), errors="replace", timeout=30, creationflags=CREATE_NO_WINDOW)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return 1, str(e)


def load():
    d = dict(DEFAULTS)
    try:
        with open(FILE, encoding="utf-8") as f:
            d.update(json.load(f))
    except (OSError, ValueError):
        pass
    return d


def save(d):
    os.makedirs(paths.DATA_DIR, exist_ok=True)
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump({k: d[k] for k in DEFAULTS}, f, indent=1)


def startup_cmd(d):
    return paths.gui_cmd("--avvio-windows", *(["--ridotto"] if d.get("minimized") else []))


def delay_of(d):
    """ritardo dell'avvio con Windows in secondi (0 = subito, massimo un minuto)."""
    try:
        return max(0, min(MAX_DELAY, int(d.get("delay", DEFAULTS["delay"]))))
    except (TypeError, ValueError):
        return DEFAULTS["delay"]


def apply(d):
    """Crea o toglie l'avvio con Windows. Usa l'Utilita' di pianificazione (non il registro) perche' LagDoctor
    ha bisogno dei permessi di amministratore: cosi' parte senza la richiesta di conferma di Windows."""
    if d.get("autostart"):
        delay = delay_of(d)
        code, out = _run(["schtasks", "/Create", "/TN", TASK, "/TR", paths.quote(startup_cmd(d)), "/SC", "ONLOGON",
                          "/RL", "HIGHEST", *(["/DELAY", "%04d:%02d" % (delay // 60, delay % 60)] if delay else []), "/F"])
        if code != 0:
            raise RuntimeError("non riesco a creare l'avvio con Windows: " + out[-200:])
        schedtask.fix(TASK, restart=False)  # a batteria deve partire lo stesso; niente limite di 3 giorni
    else:
        _run(["schtasks", "/Delete", "/TN", TASK, "/F"])
    save(d)
    return d


def status():
    d = load()
    d["task"] = _run(["schtasks", "/Query", "/TN", TASK])[0] == 0
    return d


def repair():
    """Dopo l'installazione o un aggiornamento: riscrive l'avvio con il percorso attuale del programma."""
    d = load()
    if d.get("autostart"):
        apply(d)
