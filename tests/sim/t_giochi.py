"""Analizza gioco: riconoscimento dei giochi aperti (struttura) e loghi dei giochi famosi."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lagdoctor import gamedetect, gameicons  # noqa: E402

r = gamedetect.candidates()
assert set(r) >= {"items", "others", "icons_pending"}, r.keys()
assert all(i["name"].lower() not in gamedetect.NON_GAME_APPS for i in r["items"])
assert gameicons.key("steam:730") == "steam-730" and gameicons.key("../../x") == "x"
assert ".." not in gameicons.path_for("../../etc/passwd").replace(gameicons.DIR, "")

js = open(os.path.join(os.path.dirname(__file__), "..", "..", "lagdoctor", "ui", "gamelogos.js"), encoding="utf-8").read()
paths = json.loads(re.search(r"GAME_LOGO_PATHS = (\{.*?\});", js).group(1))
rows = json.loads(re.search(r"GAME_LOGOS = (\[.*?\]);", js, re.S).group(1))
assert len(rows) >= 140 and all(r[1] in paths for r in rows)


def logo(name):
    n = " " + re.sub(r"[^a-z0-9]+", " ", name.lower()).strip() + " "
    for ws, slug, *_ in rows:
        if any(" " + w + " " in n for w in ws):
            return slug
    return None


casi = {"Counter-Strike 2": "counterstrike", "Grand Theft Auto V": "rockstargames", "Cyberpunk 2077": "cdprojekt",
        "Call of Duty: Black Ops 6": "activision", "Assassin's Creed Valhalla": "ubisoft", "Apex Legends": "ea",
        "Tom Clancy's Rainbow Six Siege": "ubisoft", "Genshin Impact": "mihoyo", "Notepad": None, "Annotazioni": None}
for nome, atteso in casi.items():
    assert logo(nome) == atteso, (nome, logo(nome), atteso)
print("OK giochi: %d loghi, riconoscimento ok" % len(rows))
