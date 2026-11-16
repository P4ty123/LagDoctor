"""Attivita' recenti mostrate nella Panoramica (game mode, backup, ottimizzazioni, analisi, Fix PC).

Ogni voce: {"t": ora, "kind": tipo, "text": testo (i nomi tra «» vengono mostrati in grassetto), "link": pagina}.
Scritto sia da LagDoctor sia dal processo della game mode: ogni scrittura rilegge il file.
"""
import json
import os
import threading
import time

from . import paths

FILE = paths.data("attivita.json")
_LOCK = threading.Lock()
MAX = 60


def _load():
    try:
        with open(FILE, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except (OSError, ValueError):
        return []


def add(kind, text, link=None):
    try:
        with _LOCK:
            items = _load()
            items.append({"t": time.time(), "kind": kind, "text": text, "link": link})
            tmp = FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(items[-MAX:], f, ensure_ascii=False)
            os.replace(tmp, FILE)
    except Exception:
        pass  # le attivita' sono solo informative: un errore qui non deve bloccare niente


def recent(n=5):
    return list(reversed(_load()[-n:]))


def durata(secondi):
    m = int(secondi // 60)
    if m < 60:
        return "%d min" % max(1, m)
    return "%d h %02d min" % (m // 60, m % 60) if m % 60 else "%d h" % (m // 60)
