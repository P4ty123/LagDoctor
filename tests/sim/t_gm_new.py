import os as _os, sys as _sys  # collaudo simulato: Windows finto (mock) + codice di LagDoctor
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.abspath(_os.path.join(_HERE, "..", "..")))
_sys.path.insert(0, _os.path.join(_HERE, "mock"))
import os, sys, tempfile
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "mock"))
os.environ["LAGDOCTOR_DATA"] = tempfile.mkdtemp()
import winreg
from lagdoctor import gamemode as G
calls = []
def fake_ps(cmd, timeout=120):
    calls.append(cmd)
    if "Disable-ScheduledTask" in cmd:
        return 0, "DIS:" + G.MAINT_TASKS[0] + "\nDIS:" + G.MAINT_TASKS[8] + "\nERR:" + G.MAINT_TASKS[9] + "\nFINE"
    return 0, ""
G._ps = fake_ps
e = G.Engine(); e.j = {"bg": {}, "services": [], "qos": []}
e._pause_maintenance()
print(e.actions[-1])
assert e.j["maint_tasks"] == [G.MAINT_TASKS[0], G.MAINT_TASKS[8]]
assert winreg.DB[("HKLM", G.MAINT_KEY.lower())]["MaintenanceDisabled"][0] == 1 and e.j["maint_prev"] == "assente"
# il journal e' salvato: dopo un crash recover() ripristina
j = G._load(G.JOURNAL, None); assert j["maint_tasks"]
e2 = G.Engine(); e2.deactivate("prova")
en = [c for c in calls if "Enable-ScheduledTask" in c][0]
assert G.MAINT_TASKS[0].replace("'", "''") in en and G.MAINT_TASKS[9] not in en
assert "MaintenanceDisabled" not in winreg.DB[("HKLM", G.MAINT_KEY.lower())]
print("manutenzione: sospese e ripristinate (anche dopo un crash): ok")
# scheda video preferita
exe = r"C:\Games\Gioco\gioco.exe"; exe2 = r"C:\Games\Altro\altro.exe"
winreg.DB[("HKCU", G.GPU_PREF_KEY.lower())] = {exe2: ("GpuPreference=1;", 1)}
assert G.gpu_pref_set(exe) is True and G.gpu_pref_set(exe2) is False
assert winreg.DB[("HKCU", G.GPU_PREF_KEY.lower())][exe][0] == "GpuPreference=2;"
assert G.gpu_pref_clear() == 1
assert exe not in winreg.DB[("HKCU", G.GPU_PREF_KEY.lower())] and exe2 in winreg.DB[("HKCU", G.GPU_PREF_KEY.lower())]
print("scheda video: impostata solo dove non c'era una scelta, tolta solo la sua: ok")
# memoria standby: solo quando la RAM libera e' poca
G._memlists = lambda: (5000, 9000); G._purge_standby = lambda: True
e.j = {"bg": {}}; e._purge_t = 0; e.standby_check(); assert not e.j.get("purges")
G._memlists = lambda: (600, 3000); e.standby_check(); assert e.j["purges"] == 1
e.standby_check(); assert e.j["purges"] == 1  # non piu' di una volta al minuto
print("standby: solo con poca RAM libera, max 1/minuto: ok")
print("TUTTO OK")
