import os as _os, sys as _sys  # collaudo simulato: Windows finto (mock) + codice di LagDoctor
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.abspath(_os.path.join(_HERE, "..", "..")))
_sys.path.insert(0, _os.path.join(_HERE, "mock"))
import os, sys, tempfile, shutil, time
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "mock"))
os.environ["LAGDOCTOR_DATA"] = tempfile.mkdtemp()
import winreg
from lagdoctor import gamemode as G
K = ("HKLM", G.WINLOGON_KEY.lower())
winreg.DB[K] = {"AutoRestartShell": (1, 4)}
shutil.copy("/bin/sleep", os.environ["LAGDOCTOR_DATA"] + "/explorer.exe")
pid = os.spawnv(os.P_NOWAIT, os.environ["LAGDOCTOR_DATA"] + "/explorer.exe", ["explorer.exe", "300"]); time.sleep(0.4)
launched = []
G.launch_as_user = lambda exe, args="", fast=False: launched.append(exe) or True
G._ps = lambda *a, **k: (0, "")
e = G.Engine(); e.j = {"bg": {}, "services": [], "qos": [], "restart": []}
e._close_processes({"close_shell": True})
os.waitpid(pid, 0)
assert winreg.DB[K]["AutoRestartShell"][0] == 0 and e.j["shell_restart_prev"] == 1, (winreg.DB[K], e.j)
print("gioco aperto: Esplora risorse chiuso, riapertura automatica di Windows spenta")
# crash a meta' partita: un nuovo Engine legge il diario e ripristina
G.Engine().deactivate("ripristino dopo crash")
assert winreg.DB[K]["AutoRestartShell"][0] == 1 and launched and launched[-1].endswith("explorer.exe")
print("fine partita / dopo crash: riapertura automatica rimessa a 1 ed Esplora risorse riaperto")
winreg.DB[K] = {}
e = G.Engine(); e.j = {"bg": {}, "services": [], "qos": [], "restart": []}
pid = os.spawnv(os.P_NOWAIT, os.environ["LAGDOCTOR_DATA"] + "/explorer.exe", ["explorer.exe", "300"]); time.sleep(0.4)
e._close_processes({"close_shell": True}); os.waitpid(pid, 0); e.deactivate()
assert "AutoRestartShell" not in winreg.DB[K]
print("valore assente prima: tolto di nuovo alla fine")
print("TUTTO OK")
