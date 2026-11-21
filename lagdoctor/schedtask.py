"""Impostazioni delle attivita' dell'Utilita' di pianificazione create da LagDoctor.

schtasks /Create usa le impostazioni normali di Windows, che per un programma che deve restare acceso sono sbagliate:
  - "Avvia solo se il computer e' alimentato da rete elettrica": a batteria (portatili) l'attivita' non parte
  - "Arresta se il computer passa all'alimentazione a batteria": staccando il caricatore Windows la chiude
  - "Arresta l'attivita' se e' in esecuzione da piu' di 3 giorni": dopo 72 ore (PC mai riavviato) la chiude
Qui si tolgono questi tre limiti e, se il programma si chiude con un errore, Windows lo fa ripartire."""
import os
import subprocess

CREATE_NO_WINDOW = 0x08000000

SCRIPT = (
    "$ErrorActionPreference='Stop'; "
    "$t = Get-ScheduledTask -TaskPath '\\' -TaskName '%s'; $s = $t.Settings; "
    "$s.DisallowStartIfOnBatteries = $false; $s.StopIfGoingOnBatteries = $false; $s.ExecutionTimeLimit = 'PT0S'; "
    "%s"
    "Set-ScheduledTask -TaskPath '\\' -TaskName '%s' -Settings $s | Out-Null; 'OK'")
RESTART = "$s.RestartCount = 3; $s.RestartInterval = 'PT1M'; "


def fix(name, restart=True):
    """Da chiamare subito dopo schtasks /Create. Restituisce True se le impostazioni sono state cambiate."""
    if os.name != "nt":
        return False
    cmd = SCRIPT % (name.replace("'", "''"), RESTART if restart else "", name.replace("'", "''"))
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd], capture_output=True,
                           text=True, errors="replace", timeout=60, creationflags=CREATE_NO_WINDOW)
        return r.returncode == 0 and "OK" in r.stdout
    except Exception:
        return False
