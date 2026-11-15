"""Quali programmi aperti sono giochi (per Analizza gioco e per "Aggiungi un gioco").

Un programma e' un gioco se:
  1. e' uno dei giochi installati che LagDoctor conosce (gli stessi della game mode: Steam, Epic, GOG, Xbox, Ubisoft,
     EA, Battle.net, Riot, Minecraft... e quelli aggiunti a mano), oppure
  2. il suo eseguibile e' in una cartella di giochi (steamapps, Epic Games, XboxGames, Riot Games...), oppure
  3. ha una finestra a schermo intero (anche "finestra senza bordi") e disegna con la scheda video (DirectX,
     Vulkan, OpenGL), e non e' un browser, un lettore video, Discord o un altro programma noto.
Tutti gli altri programmi aperti vanno in "others" (si vedono solo con "Mostra tutti i programmi aperti").
"""
import ctypes
import os
import re

import psutil

from . import capture, gameicons, gamemode
from . import games as G
from .main import GAME_HINTS, NOT_GAMES

NON_GAME_APPS = {
    "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe", "vivaldi.exe", "iexplore.exe", "arc.exe",
    "discord.exe", "spotify.exe", "vlc.exe", "mpc-hc.exe", "mpc-hc64.exe", "mpc-be64.exe", "potplayermini64.exe",
    "potplayermini.exe", "wmplayer.exe", "video.ui.exe", "microsoft.media.player.exe", "obs64.exe", "obs32.exe",
    "explorer.exe", "applicationframehost.exe", "shellexperiencehost.exe", "searchhost.exe", "textinputhost.exe",
    "startmenuexperiencehost.exe", "lockapp.exe", "powerpnt.exe", "winword.exe", "excel.exe", "outlook.exe",
    "teams.exe", "ms-teams.exe", "zoom.exe", "code.exe", "devenv.exe", "msedgewebview2.exe", "whatsapp.exe",
    "telegram.exe", "netflix.exe", "nvidia overlay.exe", "nvcontainer.exe", "gamebar.exe", "xboxpcapp.exe",
    "lagdoctor.exe", "lagdoctorhelper.exe", "python.exe", "pythonw.exe", "photos.exe", "acrobat.exe", "acrord32.exe",
    "notepad.exe", "mspaint.exe", "streamlabs obs.exe", "medal.exe", "overwolf.exe", "steelseriesgg.exe",
    "rtss.exe", "msiafterburner.exe", "taskmgr.exe", "mmc.exe", "cmd.exe", "powershell.exe", "windowsterminal.exe",
}
GPU_DLLS = ("d3d9.dll", "d3d11.dll", "d3d12.dll", "vulkan-1.dll", "opengl32.dll", "d3d10.dll", "d3d8.dll")


def fullscreen_pids():
    """pid dei programmi con una finestra visibile grande come un intero monitor."""
    if os.name != "nt":
        return set()
    from ctypes import wintypes as W
    u32 = ctypes.WinDLL("user32", use_last_error=True)

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", W.DWORD), ("rcMonitor", W.RECT), ("rcWork", W.RECT), ("dwFlags", W.DWORD)]
    u32.MonitorFromWindow.restype = W.HMONITOR
    u32.MonitorFromWindow.argtypes = [W.HWND, W.DWORD]
    u32.GetMonitorInfoW.argtypes = [W.HMONITOR, ctypes.POINTER(MONITORINFO)]
    u32.GetWindowRect.argtypes = [W.HWND, ctypes.POINTER(W.RECT)]
    u32.GetWindowThreadProcessId.argtypes = [W.HWND, ctypes.POINTER(W.DWORD)]
    u32.IsWindowVisible.argtypes = [W.HWND]
    u32.IsIconic.argtypes = [W.HWND]

    class WINDOWPLACEMENT(ctypes.Structure):
        _fields_ = [("length", W.UINT), ("flags", W.UINT), ("showCmd", W.UINT), ("ptMinPosition", W.POINT),
                    ("ptMaxPosition", W.POINT), ("rcNormalPosition", W.RECT)]
    u32.GetWindowPlacement.argtypes = [W.HWND, ctypes.POINTER(WINDOWPLACEMENT)]
    found = set()

    @ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    def cb(hwnd, _lp):
        try:
            if not u32.IsWindowVisible(hwnd):
                return True
            r = W.RECT()
            if not u32.GetWindowRect(hwnd, ctypes.byref(r)):
                return True
            mon = u32.MonitorFromWindow(hwnd, 2)  # il monitor piu' vicino
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(mi)
            if not mon or not u32.GetMonitorInfoW(mon, ctypes.byref(mi)):
                return True
            m = mi.rcMonitor
            if (m.right - m.left) < 640:
                return True
            if u32.IsIconic(hwnd):
                # ridotta a icona (es. il gioco a schermo intero dopo Alt+Tab): conta la sua posizione normale
                wp = WINDOWPLACEMENT()
                wp.length = ctypes.sizeof(wp)
                if not u32.GetWindowPlacement(hwnd, ctypes.byref(wp)):
                    return True
                r = wp.rcNormalPosition
                m = W.RECT(0, 0, u32.GetSystemMetrics(0), u32.GetSystemMetrics(1))  # monitor principale
            # la finestra copre tutto il monitor (a schermo intero o "finestra senza bordi")
            covers = r.left <= m.left and r.top <= m.top and r.right >= m.right and r.bottom >= m.bottom
            if covers:
                pid = W.DWORD()
                u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                found.add(pid.value)
        except Exception:
            pass
        return True
    u32.EnumWindows(cb, 0)
    return found


def uses_gpu(p):
    try:
        names = {os.path.basename(m.path).lower() for m in p.memory_maps(grouped=True)}
    except (psutil.Error, OSError):
        return True  # non leggibile (es. protetto da anti-cheat): per i programmi a schermo intero va bene lo stesso
    return any(d in names for d in GPU_DLLS)


def _pretty(exe_name):
    stem = re.sub(r"\.exe$", "", exe_name or "", flags=re.I)
    stem = re.sub(r"[-_](win64|win32|x64|shipping|dx11|dx12|vulkan)\b", "", stem, flags=re.I)
    return stem.replace("_", " ").strip() or exe_name


def _library():
    try:
        c = gamemode.load_config()
        lib = c.get("games") or []
        if not lib:
            lib = G.detect()
        return lib
    except Exception:
        return []


def candidates():
    """{"items": giochi aperti, "others": altri programmi grandi}"""
    lib = _library()
    fs = fullscreen_pids()
    windir = os.path.normcase(os.environ.get("WINDIR", r"C:\Windows"))
    me = os.getpid()
    by_game, others = {}, []
    for p in psutil.process_iter(["pid", "name", "exe", "memory_info"]):
        try:
            pid, name = p.info["pid"], (p.info["name"] or "")
            low = name.lower()
            if pid == me or not name or low in NOT_GAMES or low in capture.IGNORE_PROCS:
                continue
            exe = p.info["exe"] or ""
            mem = p.info["memory_info"].rss / 2**20 if p.info["memory_info"] else 0
            item = {"pid": pid, "name": name, "exe": exe, "mem": round(mem)}
            game = None
            for g in lib:
                if G.matches(g, name, exe, lambda: " ".join(p.cmdline())):
                    game = g
                    break
            if game:
                item.update(game_id=game["id"], game=game["name"], source=game.get("source"), kind="lib")
            elif exe and any(h in exe.lower() for h in GAME_HINTS) and not G.NOT_GAME_EXE.search(low) and mem > 150:
                item.update(game_id=gameicons.exe_key(exe), game=_pretty(name), source=None, kind="folder")
            elif pid in fs and low not in NON_GAME_APPS and not os.path.normcase(exe).startswith(windir) and uses_gpu(p):
                item.update(game_id=gameicons.exe_key(exe) if exe else None, game=_pretty(name), source=None, kind="fullscreen")
            else:
                if mem > 300:
                    others.append(item)
                continue
            k = item["game_id"] or str(pid)
            if k not in by_game or by_game[k]["mem"] < mem:  # un gioco con piu' processi: quello che usa piu' RAM
                by_game[k] = item
        except psutil.Error:
            continue
    items = sorted(by_game.values(), key=lambda i: (i["kind"] != "lib", -i["mem"]))
    for i in items:
        i["icon"] = bool(i.get("game_id")) and gameicons.have(i["game_id"])
    missing = [{"id": i["game_id"], "name": i["game"], "exe": i["exe"]} for i in items
               if i.get("game_id") and not i["icon"] and i["exe"]]
    for i in items:  # per i giochi della libreria l'icona viene dal gioco, non dal processo
        if i["kind"] == "lib":
            g = next((g for g in lib if g["id"] == i["game_id"]), None)
            if g:
                missing = [m for m in missing if m["id"] != i["game_id"]] + ([g] if not i["icon"] else [])
    pending = gameicons.ensure(missing) if missing else False
    others.sort(key=lambda i: -i["mem"])
    return {"items": items, "others": others[:20], "icons_pending": pending}
