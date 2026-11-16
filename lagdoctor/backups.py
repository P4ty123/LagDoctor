"""Backups: i punti di ripristino di Windows creati da LagDoctor e le modifiche di LagDoctor annullabili.

I punti di ripristino di LagDoctor hanno la descrizione che inizia con "LagDoctor" (es. "LagDoctor: prima di
applicare 5 modifiche", "LagDoctor: creato da te"). Quelli creati da Windows o da altri programmi non compaiono.
"""
import ctypes
import json
import os
import re

from . import tweaks

PREFIX = "LagDoctor"

PS_LIST = r'''
$ErrorActionPreference = 'Stop'
$r = @(Get-ComputerRestorePoint | Where-Object { $_.Description -like 'LagDoctor*' } | ForEach-Object {
  [pscustomobject]@{ seq = [int]$_.SequenceNumber; desc = [string]$_.Description;
                     time = ([Management.ManagementDateTimeConverter]::ToDateTime($_.CreationTime)).ToString('s') } })
ConvertTo-Json -InputObject $r -Compress
'''


_CACHE = {"t": 0, "v": None}


def forget_cache():
    _CACHE["v"] = None


def restore_points(cached=False):
    """[{seq, time (ISO), note}], dal piu' recente. Solleva RuntimeError se Windows non risponde.
    cached: per la Panoramica, riusa la lettura degli ultimi 10 minuti (leggere i punti di ripristino e' lento)."""
    import time
    if cached and _CACHE["v"] is not None and time.time() - _CACHE["t"] < 600:
        return _CACHE["v"]
    code, out = tweaks.ps(PS_LIST, timeout=90)
    m = re.search(r"\[.*\]", out or "", re.S)
    if code != 0 or not m:
        raise RuntimeError((out or "").strip()[-300:] or "Ripristino configurazione di sistema non disponibile")
    items = []
    for p in json.loads(m.group(0)):
        desc = p.get("desc") or ""
        note = desc[len(PREFIX):].lstrip(" :-") or "creato da LagDoctor"
        items.append({"seq": int(p["seq"]), "time": p.get("time"), "note": note})
    items.sort(key=lambda i: i["time"] or "", reverse=True)
    import time
    _CACHE.update(t=time.time(), v=items)
    return items


def create(note="creato da te"):
    return tweaks.create_restore_point("%s: %s" % (PREFIX, note))


def _is_ours(seq):
    return any(p["seq"] == int(seq) for p in restore_points())


def delete(seq):
    """Elimina un punto di ripristino di LagDoctor (API di Windows SRRemoveRestorePoint)."""
    if not _is_ours(seq):
        raise ValueError("Backup non trovato.")
    r = ctypes.WinDLL("srclient").SRRemoveRestorePoint(ctypes.c_ulong(int(seq)))
    if r != 0:
        raise RuntimeError("Windows non ha eliminato il backup (errore %d)." % r)
    return "Backup eliminato."


def restore(seq):
    """Riporta Windows al punto di ripristino: Windows riavvia il PC da solo."""
    if not _is_ours(seq):
        raise ValueError("Backup non trovato.")
    code, out = tweaks.ps("Restore-Computer -RestorePoint %d -Confirm:$false" % int(seq), timeout=120)
    if code != 0:
        raise RuntimeError((out or "").strip()[-300:] or "Ripristino non avviato.")
    return "Ripristino avviato: il PC si riavvia."


def changes():
    """Le modifiche di LagDoctor ancora attive, con la data in cui sono state applicate."""
    out = []
    for tid, item in tweaks.load_state().items():
        if tid.startswith("_") or not isinstance(item, dict):
            continue
        t = tweaks.BY_ID.get(tid)
        out.append({"id": tid, "name": t.name if t else item.get("nome") or tid, "cat": t.cat if t else "",
                    "time": item.get("data"), "known": bool(t)})
    out.sort(key=lambda c: c["time"] or "", reverse=True)
    return out
