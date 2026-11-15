"""Genera lagdoctor/ui/gamelogos.js: logo da mostrare accanto ai giochi famosi.

I disegni dei loghi vengono da Simple Icons (https://simpleicons.org, licenza CC0): dove esiste il logo del gioco si
usa quello, altrimenti il logo dello studio o dell'editore che lo ha fatto, su uno sfondo col colore del gioco.
Se il gioco e' installato, LagDoctor preferisce la sua icona vera (presa dal file .exe): questi loghi servono per i
giochi famosi dove l'icona del file non c'e' o non si legge.

    npm pack simple-icons && tar xzf simple-icons-*.tgz
    python tools/make_gamelogos.py package/icons
"""
import json
import os
import re
import sys

# (nome mostrato / parole per riconoscerlo, logo, colore 1, colore 2, colore del disegno)
# le parole sono confrontate col nome del gioco in minuscolo, senza simboli
G = [
    # giochi con il proprio logo
    ("counter strike|cs2|csgo", "counterstrike", "#f0a640", "#c4762a", "#1b1205"),
    ("fortnite", "fortnite", "#8f3cff", "#2fb8ff", "#fff"),
    ("valorant", "valorant", "#ff4655", "#c22c3b", "#fff"),
    ("league of legends", "leagueoflegends", "#0e1f2f", "#091018", "#c8aa6e"),
    ("dota", "dota2", "#c23c2a", "#7a1f12", "#fff"),
    ("pubg|playerunknown", "pubg", "#f4b942", "#d99419", "#1a1405"),
    ("roblox", "roblox", "#e2e2e2", "#9a9a9a", "#111"),
    ("fifa|ea sports fc|ea fc", "fifa", "#326295", "#16365c", "#fff"),
    ("vrchat", "vrchat", "#1a1a1a", "#000", "#fff"),
    ("osu", "osu", "#ff66aa", "#d63d84", "#fff"),
    ("fivem", "fivem", "#f40552", "#a3002f", "#fff"),
    # Rockstar
    ("grand theft auto|gta", "rockstargames", "#2f8f3a", "#14451b", "#fcaf17"),
    ("red dead", "rockstargames", "#b5241b", "#5c0f0a", "#fff"),
    ("max payne", "rockstargames", "#3a3a3a", "#151515", "#fcaf17"),
    ("l a noire|la noire", "rockstargames", "#5a4a32", "#2a2216", "#fcaf17"),
    ("bully", "rockstargames", "#2d5aa8", "#16305e", "#fcaf17"),
    # CD Projekt
    ("cyberpunk", "cdprojekt", "#fcee0a", "#d4c400", "#111"),
    ("witcher", "cdprojekt", "#8b1d1d", "#3f0b0b", "#fff"),
    ("gwent", "cdprojekt", "#6b4f2a", "#33240f", "#fff"),
    # Activision
    ("call of duty|warzone", "activision", "#2b2b2b", "#0d0d0d", "#fff"),
    ("crash bandicoot", "activision", "#f07a1a", "#b54d06", "#fff"),
    ("tony hawk", "activision", "#e63a2a", "#8f1b10", "#fff"),
    ("spyro", "activision", "#7b45c9", "#3f1d7a", "#fff"),
    # Blizzard (Battle.net)
    ("world of warcraft|warcraft", "battledotnet", "#c78c1e", "#5e3e05", "#fff"),
    ("overwatch", "battledotnet", "#f99e1a", "#b9650a", "#fff"),
    ("diablo", "battledotnet", "#a3120c", "#4a0604", "#fff"),
    ("hearthstone", "battledotnet", "#c9842b", "#7a4a12", "#fff"),
    ("starcraft", "battledotnet", "#1c5aa6", "#0b2a52", "#fff"),
    ("heroes of the storm", "battledotnet", "#4a3da8", "#211a5c", "#fff"),
    # Bungie
    ("destiny", "bungie", "#d8d8d8", "#8c8c8c", "#111"),
    ("marathon", "bungie", "#c7f000", "#7a9400", "#111"),
    # HoYoverse / miHoYo
    ("genshin", "mihoyo", "#5aa9e6", "#2c5d8f", "#fff"),
    ("honkai star rail|star rail", "mihoyo", "#3b2f7a", "#16103a", "#fff"),
    ("honkai", "mihoyo", "#d24e8b", "#7a1f4c", "#fff"),
    ("zenless", "mihoyo", "#f7d400", "#b39a00", "#111"),
    # Square Enix
    ("final fantasy", "squareenix", "#1d3f8c", "#0a1d47", "#fff"),
    ("kingdom hearts", "squareenix", "#2c6fd1", "#123a77", "#fff"),
    ("nier", "squareenix", "#d8d0b8", "#8a8370", "#111"),
    ("dragon quest", "squareenix", "#2f86d6", "#164a7c", "#fff"),
    ("octopath", "squareenix", "#b58a3a", "#5e4414", "#fff"),
    ("forspoken", "squareenix", "#4a7d8f", "#1d3c47", "#fff"),
    ("life is strange", "squareenix", "#7aa7c7", "#355b75", "#fff"),
    # Ubisoft
    ("assassin s creed|assassins creed", "ubisoft", "#8a1c1c", "#2d0a0a", "#fff"),
    ("far cry", "ubisoft", "#f28c18", "#9a4b05", "#fff"),
    ("rainbow six|r6", "ubisoft", "#1f2a36", "#0b1017", "#fff"),
    ("the crew", "ubisoft", "#1e78c8", "#0b3c66", "#fff"),
    ("watch dogs", "ubisoft", "#1aa36e", "#0a5236", "#fff"),
    ("ghost recon", "ubisoft", "#56622f", "#262c12", "#fff"),
    ("the division|tom clancy s the division", "ubisoft", "#f26b1d", "#8f3505", "#fff"),
    ("for honor", "ubisoft", "#b02a1d", "#55100a", "#fff"),
    ("anno", "ubisoft", "#c49a3b", "#6b4f14", "#fff"),
    ("trackmania", "ubisoft", "#2bb5d8", "#12607a", "#fff"),
    ("prince of persia", "ubisoft", "#d4a017", "#7a5a05", "#fff"),
    ("avatar frontiers", "ubisoft", "#1aa3a3", "#0a5252", "#fff"),
    ("star wars outlaws", "ubisoft", "#c87a2b", "#6b3c0f", "#fff"),
    ("skull and bones", "ubisoft", "#2f3f4f", "#121a22", "#fff"),
    ("immortals fenyx", "ubisoft", "#3a8fd6", "#17497a", "#fff"),
    ("brawlhalla", "ubisoft", "#e8b22a", "#8c6508", "#fff"),
    ("rayman", "ubisoft", "#8a3fd6", "#45167a", "#fff"),
    ("just dance", "ubisoft", "#ff3fa4", "#a3105c", "#fff"),
    # EA
    ("apex legends", "ea", "#da292a", "#7a0f10", "#fff"),
    ("battlefield", "ea", "#1d2a3a", "#0a1018", "#ff7a00"),
    ("the sims|sims 4|sims 3", "ea", "#3fae2a", "#1c5c10", "#fff"),
    ("need for speed", "ea", "#1d1d1d", "#000", "#41ff00"),
    ("madden", "ea", "#1b3d6d", "#0a1d38", "#fff"),
    ("nhl", "ea", "#3a3a3a", "#111", "#fff"),
    ("ufc", "ea", "#c8102e", "#5c0614", "#fff"),
    ("mass effect", "ea", "#1d3f6e", "#0a1d38", "#fff"),
    ("dragon age", "ea", "#7a1414", "#330707", "#fff"),
    ("star wars jedi|jedi survivor|jedi fallen", "ea", "#3a2a1a", "#120c06", "#ffc500"),
    ("star wars battlefront|star wars squadrons", "ea", "#1a1a1a", "#000", "#ffc500"),
    ("titanfall", "ea", "#3a4a5a", "#141c24", "#fff"),
    ("it takes two|split fiction", "ea", "#d6a52b", "#7a5a0f", "#fff"),
    ("a way out", "ea", "#4a5a6a", "#1c242c", "#fff"),
    ("f1 2|f1 23|f1 24|f1 25|ea sports f1|f1 manager", "ea", "#e10600", "#7a0300", "#fff"),
    ("dirt rally|dirt 5|wrc", "ea", "#f2b705", "#8f6a00", "#111"),
    ("plants vs zombies", "ea", "#5aa02c", "#2a4d12", "#fff"),
    ("dead space", "ea", "#3a3f44", "#121416", "#9fe0ff"),
    ("crysis", "ea", "#3a4a3a", "#141c14", "#fff"),
    ("skate", "ea", "#ffcc00", "#a38200", "#111"),
    ("college football", "ea", "#4a2a0a", "#1c0f02", "#fff"),
    # Valve
    ("half life", "valve", "#f26b1d", "#8f3505", "#fff"),
    ("portal", "valve", "#3a9ad9", "#164a75", "#fff"),
    ("team fortress", "valve", "#b8572a", "#5a2510", "#fff"),
    ("left 4 dead", "valve", "#7a1a1a", "#330a0a", "#fff"),
    ("deadlock", "valve", "#b0a27a", "#5a5238", "#111"),
    ("artifact", "valve", "#3a2a5a", "#160f24", "#fff"),
    # Sega / Atlus
    ("sonic", "sega", "#1f5fd6", "#0b2f7a", "#fff"),
    ("yakuza|like a dragon", "sega", "#b51b1b", "#520707", "#fff"),
    ("persona", "sega", "#e3171b", "#7a0709", "#fff"),
    ("metaphor refantazio", "sega", "#2b5f3a", "#0f2a17", "#fff"),
    ("total war", "sega", "#8a1c1c", "#3a0a0a", "#d4af37"),
    ("football manager", "sega", "#1aa36e", "#0a5236", "#fff"),
    ("company of heroes", "sega", "#5a5a3a", "#24241a", "#fff"),
    ("two point", "sega", "#3fc1d6", "#16687a", "#fff"),
    ("hatsune miku", "sega", "#39c5bb", "#147a73", "#fff"),
    ("alien isolation", "sega", "#2a3a2a", "#0c140c", "#fff"),
    # Konami
    ("metal gear", "konami", "#4a5a3a", "#1c2414", "#fff"),
    ("silent hill", "konami", "#5a5a5a", "#1c1c1c", "#fff"),
    ("efootball|pes 20", "konami", "#1b3fa8", "#0a1d5c", "#fff"),
    ("yu gi oh|yugioh", "konami", "#c79a2b", "#6b4f0f", "#fff"),
    ("castlevania", "konami", "#5a1a3a", "#240a17", "#fff"),
    # Nexon / Embark
    ("the finals", "embark", "#e8e8e8", "#9a9a9a", "#d31f3c"),
    ("arc raiders", "embark", "#2b2b2b", "#0d0d0d", "#ff5a1f"),
    ("maplestory", "nexon", "#ff8a1f", "#a34a05", "#fff"),
    ("the first descendant", "nexon", "#2a4a7a", "#0f1d33", "#fff"),
    ("blue archive", "nexon", "#3fb5ff", "#1660a3", "#fff"),
    ("dave the diver", "nexon", "#1aa3d6", "#0a527a", "#fff"),
    ("mabinogi", "nexon", "#7a5ad6", "#33227a", "#fff"),
    ("dungeon fighter", "nexon", "#a32a1a", "#4d0f07", "#fff"),
    # Riot
    ("teamfight tactics|tft", "riotgames", "#d6a32b", "#7a5a0f", "#fff"),
    ("legends of runeterra|runeterra", "riotgames", "#2b6fd6", "#123a7a", "#fff"),
    ("2xko", "riotgames", "#d6332b", "#7a120f", "#fff"),
    # Epic Games
    ("rocket league", "epicgames", "#0a7cff", "#043f8a", "#fff"),
    ("fall guys", "epicgames", "#ff4fa3", "#a3105c", "#fff"),
    ("unreal tournament", "epicgames", "#2a2a2a", "#0d0d0d", "#fff"),
    # 2K
    ("nba 2k|nba2k", "2k", "#c9082a", "#5c0313", "#fff"),
    ("wwe 2k", "2k", "#1d1d1d", "#000", "#fff"),
    ("civilization", "2k", "#2b5f9e", "#0f2a4a", "#fff"),
    ("borderlands", "2k", "#f2c200", "#8a6e00", "#111"),
    ("bioshock", "2k", "#2b7a8a", "#0f3a42", "#fff"),
    ("xcom", "2k", "#2a4a6a", "#0f1d2c", "#fff"),
    ("mafia", "2k", "#3a2a1a", "#120c06", "#fff"),
    ("pga tour 2k|pga 2k", "2k", "#1a7a3a", "#0a3a1a", "#fff"),
    ("tiny tina", "2k", "#d63fa3", "#7a1660", "#fff"),
    ("top spin", "2k", "#d6d63f", "#7a7a16", "#111"),
    # Paradox
    ("cities skylines", "paradoxinteractive", "#2b9ad6", "#12517a", "#fff"),
    ("stellaris", "paradoxinteractive", "#1a2a5a", "#0a0f24", "#fff"),
    ("hearts of iron", "paradoxinteractive", "#5a4a2a", "#24190a", "#fff"),
    ("crusader kings", "paradoxinteractive", "#8a1a1a", "#3a0a0a", "#d4af37"),
    ("europa universalis", "paradoxinteractive", "#2b4a8a", "#0f1d3a", "#d4af37"),
    ("victoria 3|victoria ii", "paradoxinteractive", "#3a6a3a", "#142a14", "#fff"),
    ("age of wonders", "paradoxinteractive", "#5a2a8a", "#24103a", "#fff"),
    ("prison architect", "paradoxinteractive", "#d6a32b", "#7a5a0f", "#111"),
    # PlayStation (giochi Sony usciti su PC)
    ("god of war", "playstation", "#8a1414", "#3a0707", "#fff"),
    ("spider man|spiderman", "playstation", "#d6222b", "#1d3f8c", "#fff"),
    ("horizon zero dawn|horizon forbidden west", "playstation", "#d6702b", "#7a3a0f", "#fff"),
    ("the last of us", "playstation", "#3a4a2a", "#141c0c", "#fff"),
    ("ghost of tsushima", "playstation", "#c7c7c7", "#7a7a7a", "#8a1414"),
    ("helldivers", "playstation", "#f2d600", "#8a7a00", "#111"),
    ("days gone", "playstation", "#5a3a2a", "#24140c", "#fff"),
    ("ratchet", "playstation", "#f28c18", "#9a4b05", "#fff"),
    ("returnal", "playstation", "#1a3a5a", "#0a1624", "#fff"),
    ("uncharted", "playstation", "#c79a2b", "#6b4f0f", "#fff"),
    ("death stranding", "playstation", "#2a3a4a", "#0c141c", "#fff"),
    ("until dawn", "playstation", "#3a1a1a", "#120808", "#fff"),
    ("stellar blade", "playstation", "#d6c7b0", "#8a7a63", "#111"),
    ("sackboy", "playstation", "#c79a6b", "#6b4f2a", "#fff"),
    ("gran turismo", "playstation", "#1d3f8c", "#0a1d47", "#fff"),
]


def build(icons_dir):
    out = []
    for words, slug, c1, c2, fg in G:
        svg = open(os.path.join(icons_dir, slug + ".svg"), encoding="utf-8").read()
        path = re.search(r'<path d="([^"]+)"', svg).group(1)
        out.append([words.split("|"), slug, c1, c2, fg, path])
    paths = {}
    rows = []
    for words, slug, c1, c2, fg, path in out:  # i disegni uguali una volta sola
        paths[slug] = path
        rows.append([words, slug, c1, c2, fg])
    js = ("/* Loghi dei giochi famosi (generato da tools/make_gamelogos.py, disegni di Simple Icons, CC0).\n"
          "   [parole del nome, logo, colore 1, colore 2, colore del disegno] */\n"
          "const GAME_LOGO_PATHS = " + json.dumps(paths, separators=(",", ":")) + ";\n"
          "const GAME_LOGOS = " + json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + ";\n")
    dest = os.path.join(os.path.dirname(__file__), "..", "lagdoctor", "ui", "gamelogos.js")
    with open(dest, "w", encoding="utf-8", newline="\n") as f:
        f.write(js)
    print("%d giochi, %d disegni, %d KB" % (len(rows), len(paths), len(js) // 1024))


if __name__ == "__main__":
    build(sys.argv[1])
