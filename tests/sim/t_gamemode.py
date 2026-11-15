"""Test della game mode con processi e Windows simulati."""
import os as _os, sys as _sys  # collaudo simulato: Windows finto (mock) + codice di LagDoctor
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.abspath(_os.path.join(_HERE, "..", "..")))
_sys.path.insert(0, _os.path.join(_HERE, "mock"))

import json
import os
import sys
import tempfile
import time

from lagdoctor import games as G
from lagdoctor import gamemode as GM

tmp = tempfile.mkdtemp()
GM.CONFIG, GM.STATUS, GM.JOURNAL, GM.LOG = [os.path.join(tmp, n) for n in
                                           ("gm.json", "st.json", "j.json", "gm.log")]

# ------------------------------------------------ rilevamento Steam / Epic / riconoscimento processi
steam = os.path.join(tmp, "Steam")
os.makedirs(os.path.join(steam, "steamapps", "common", "FarmingSimulator25"))
os.makedirs(os.path.join(steam, "steamapps", "common", "Steamworks Shared"))
lib2 = os.path.join(tmp, "Lib2")
os.makedirs(os.path.join(lib2, "steamapps", "common", "Hot Wheels Unleashed"))
open(os.path.join(steam, "steamapps", "libraryfolders.vdf"), "w").write(
    '"libraryfolders"\n{\n "0"\n {\n  "path"  "%s"\n }\n "1"\n {\n  "path"  "%s"\n }\n}' % (steam, lib2))
for lib, appid, name, d in [(steam, "2300320", "Farming Simulator 25", "FarmingSimulator25"),
                            (steam, "228980", "Steamworks Common Redistributables", "Steamworks Shared"),
                            (lib2, "1271700", "HOT WHEELS UNLEASHED", "Hot Wheels Unleashed")]:
    open(os.path.join(lib, "steamapps", "appmanifest_%s.acf" % appid), "w").write(
        '"AppState"\n{\n "appid" "%s"\n "name" "%s"\n "installdir" "%s"\n}' % (appid, name, d))
G._reg = lambda root, path, name: steam if name in ("SteamPath", "InstallPath") else None
G.winreg = type("W", (), {"HKEY_CURRENT_USER": 1, "HKEY_LOCAL_MACHINE": 2})
found = G.steam()
print("Steam:", [g["name"] for g in found])
assert sorted(g["name"] for g in found) == ["Farming Simulator 25", "HOT WHEELS UNLEASHED"]
fs = [g for g in found if g["name"].startswith("Farming")][0]
gdir = fs["dir"]
assert G.matches(fs, "FarmingSimulator2025Game.exe", os.path.join(gdir, "x64", "FarmingSimulator2025Game.exe"), None)
assert not G.matches(fs, "UnityCrashHandler64.exe", os.path.join(gdir, "UnityCrashHandler64.exe"), None)
assert not G.matches(fs, "notepad.exe", r"C:\Windows\notepad.exe", None)
mc = dict(match="java", keywords=["minecraft"])
assert G.matches(mc, "javaw.exe", "x", lambda: "javaw -cp ... net.minecraft.client.main.Main")
assert not G.matches(mc, "javaw.exe", "x", lambda: "javaw -jar idea.jar")
m = G.manual(r"C:\Games\Hollow Knight\hollow_knight.exe")
print("manuale:", m)
print("rilevamento ok")


# ------------------------------------------------ processi finti
class FakeProc:
    def __init__(self, pid, name, exe, user="PC\\Luca", prio=0x20, cmd=""):
        self.pid, self._name, self._exe, self._user, self._prio, self._cmd = pid, name, exe, user, prio, cmd
        self.ct = 1000.0 + pid
        self.killed = False
        self.info = {"pid": pid, "name": name, "exe": exe, "username": user}

    def name(self): return self._name
    def exe(self): return self._exe
    def username(self): return self._user
    def create_time(self): return self.ct
    def cmdline(self): return self._cmd.split()
    def kill(self): self.killed = True; PROCS.remove(self)

    def nice(self, v=None):
        if v is None:
            return self._prio
        self._prio = v


game_exe = os.path.join(gdir, "x64", "FarmingSimulator2025Game.exe")
PROCS = [FakeProc(4, "System", None, user=None), FakeProc(100, "explorer.exe", r"C:\Windows\explorer.exe"),
         FakeProc(101, "chrome.exe", "chrome"), FakeProc(102, "Discord.exe", "discord"),
         FakeProc(103, "Widgets.exe", "w"), FakeProc(104, "OneDrive.exe", __file__),
         FakeProc(105, "svchost.exe", "s", user="NT AUTHORITY\\SYSTEM")]
OWN = FakeProc(os.getpid(), "pythonw.exe", "py")


class FakePsutil:
    Error = Exception
    AccessDenied = PermissionError

    @staticmethod
    def process_iter(attrs=None):
        return list(PROCS)

    @staticmethod
    def Process(pid=None):
        if pid is None:
            return OWN
        for p in PROCS:
            if p.pid == pid:
                return p
        raise Exception("no proc")

    @staticmethod
    def pid_exists(pid): return any(p.pid == pid for p in PROCS)

    class _VM:
        available = 10 * 2**30

    @staticmethod
    def virtual_memory(): return FakePsutil._VM


GM.psutil = FakePsutil
CMDS = []
GM._run = lambda a, timeout=60: (CMDS.append(" ".join(a)) or (0, "GUID: 381b4222-f694-41f0-9685-ff5bb260df2e"))


def fake_ps(c, timeout=120):
    CMDS.append("PS " + c[:70])
    if "Stop-Service" in c:
        return 0, "STOP:WSearch\nSTOP:SysMain\nSTOP:wuauserv\nERR:DoSvc\nFINE"
    if "New-NetQosPolicy" in c:
        return 0, "OK"
    return 0, ""


GM._ps = fake_ps
GM._timer = lambda on: CMDS.append("TIMER %s" % on) or True
GM._trim = lambda pid: True
GM._set_gpu_priority = lambda pid, cls: CMDS.append("GPU %d %d" % (pid, cls)) or True
LAUNCHED = []
GM.launch_as_user = lambda exe, args="", fast=False: LAUNCHED.append((exe, args)) or True

cfg = GM.load_config()
cfg["enabled"] = True
cfg["games"] = [dict(fs, on=True, priority="high")]
cfg["opts"]["close_shell"] = True
GM.save_config(cfg)

w = GM.Watcher()
w.tick()
assert not w.engine.active, "attiva senza gioco"
print("senza gioco: in attesa OK")

game = FakeProc(200, "FarmingSimulator2025Game.exe", game_exe)
PROCS.append(game)
w.tick()
e = w.engine
assert e.active
print("azioni:", *e.actions, sep="\n   ")
assert game._prio == 0x80, game._prio
assert [p.name() for p in PROCS if p.name() in ("Widgets.exe", "OneDrive.exe", "explorer.exe")] == []
chrome = [p for p in PROCS if p.name() == "chrome.exe"][0]
discord = [p for p in PROCS if p.name() == "Discord.exe"][0]
svc = [p for p in PROCS if p.name() == "svchost.exe"][0]
assert chrome._prio == 0x4000 and discord._prio == 0x20 and svc._prio == 0x20
j = json.load(open(GM.JOURNAL))
assert j["services"] == ["WSearch", "SysMain", "wuauserv"] and j["explorer"] and j["qos"]
print("gioco avviato: priorita' Alta, chrome abbassato, Discord e servizi di sistema intatti, diario scritto")

# programma aperto DURANTE il gioco
late = FakeProc(300, "msedge.exe", "edge")
PROCS.append(late)
w.tick()
assert late._prio == 0x4000

# gioco chiuso: entro il periodo di tolleranza resta attiva, poi si spegne
PROCS.remove(game)
w.tick()
assert e.active
w.last_seen -= 100
CMDS.clear()
w.tick()
assert not e.active and not os.path.exists(GM.JOURNAL)
assert chrome._prio == 0x20 and late._prio == 0x20
assert any("Start-Service" in c for c in CMDS) and any("Remove-NetQosPolicy" in c for c in CMDS)
assert any("explorer.exe" in x[0] for x in LAUNCHED) and any(x[0] == __file__ for x in LAUNCHED)
assert "TIMER False" in CMDS
print("gioco chiuso: priorita', servizi, QoS, Esplora risorse, OneDrive e timer ripristinati")

# crash: diario rimasto su disco -> ripristino all'avvio
json.dump({"since": 1, "games": ["x"], "services": ["WSearch"], "explorer": False, "restart": [],
           "power_prev": None, "qos": ["LagDoctor-x.exe"], "bg": {}, "timer": False}, open(GM.JOURNAL, "w"))
CMDS.clear()
w2 = GM.Watcher()
assert w2.engine.active
w2.engine.deactivate("test crash")
assert not os.path.exists(GM.JOURNAL) and any("Start-Service" in c for c in CMDS)
print("ripristino dopo crash OK")

# gioco protetto da anti-cheat
def deny(v=None):
    if v is None:
        return 0x20
    raise PermissionError()
g2 = FakeProc(201, "FarmingSimulator2025Game.exe", game_exe)
g2.nice = deny
PROCS.append(g2)
w.tick()
print("anti-cheat:", w.engine.errors)
assert w.engine.errors
PROCS.remove(g2)
w.last_seen -= 100
w.tick()

# GAME MODE SPENTA MENTRE SI GIOCA (programma invisibile chiuso a meta'): un altro processo ripristina dal diario
g3 = FakeProc(202, "FarmingSimulator2025Game.exe", game_exe)
g3.ct = time.time() - 60  # aperto da un minuto (niente attesa anti-cheat)
PROCS.append(g3)
w.tick()
assert w.engine.active and g3._prio == 0x80
j = json.load(open(GM.JOURNAL))
assert "202" in j.get("gproc", {}), j.get("gproc")
CMDS.clear()
GM.Engine().deactivate("game mode spenta, programma invisibile chiuso")  # come recover() dall'interfaccia
assert g3._prio == 0x20 and "GPU 202 2" in CMDS and not os.path.exists(GM.JOURNAL)
assert chrome._prio == 0x20 and any("Start-Service" in c for c in CMDS)
print("spenta durante il gioco + programma chiuso: priorita' e GPU del gioco, sfondo e servizi ripristinati")
w.engine.j = None; w.engine.game_pids.clear()
# GAME MODE SPENTA MENTRE SI GIOCA (caso normale): il ciclo si ferma e ripristina tutto, gioco compreso
w.tick()
assert w.engine.active and g3._prio == 0x80

# spegnimento dalla config: il ciclo termina e ripristina
cfg = GM.load_config(); cfg["enabled"] = False; GM.save_config(cfg)
w.run()
assert g3._prio == 0x20 and not os.path.exists(GM.JOURNAL) and chrome._prio == 0x20
print("spenta durante il gioco: tutto ripristinato, anche la priorita' del gioco ancora aperto")
print("spegnimento OK; stato:", json.load(open(GM.STATUS)))
print("TUTTO OK")
