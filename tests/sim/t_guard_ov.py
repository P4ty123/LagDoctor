import os as _os, sys as _sys  # collaudo simulato: Windows finto (mock) + codice di LagDoctor
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.abspath(_os.path.join(_HERE, "..", "..")))
_sys.path.insert(0, _os.path.join(_HERE, "mock"))
import os, shutil, subprocess, sys, tempfile, time
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "mock"))
W = tempfile.mkdtemp()
os.environ.update({"ProgramFiles": W + "/pf", "ProgramFiles(x86)": W + "/pf86", "LOCALAPPDATA": W + "/local", "LAGDOCTOR_DATA": W + "/data"})
os.makedirs(W + "/data")
import winreg
from lagdoctor import tweaks as T, overlays as O
T.init(W + "/data")
calls = []
O._run = lambda a: (calls.append(a[:3]), (0, ""))[1]
O.subprocess.Popen = lambda *a, **k: calls.append(("POPEN", a[0][-1]))
os.makedirs(W + "/pf86/RivaTuner Statistics Server"); open(W + "/pf86/RivaTuner Statistics Server/RTSS.exe", "w").close()
shutil.copy("/bin/sleep", W + "/rtss.exe")
proc = os.spawnv(os.P_NOWAIT, W + "/rtss.exe", [W + "/rtss.exe", "300"]); time.sleep(0.4)
T.apply_one("ov_rtss")
assert ["schtasks", "/Create", "/TN"] in calls and ("POPEN", "--overlay") in calls, calls
os.waitpid(proc, 0)
# si riapre (es. dopo il riavvio): il guardiano lo richiude
proc = os.spawnv(os.P_NOWAIT, W + "/rtss.exe", [W + "/rtss.exe", "300"]); time.sleep(0.4)
assert "rtss.exe" in O.running_names(0)
assert O.guard_once(False) == 1
os.waitpid(proc, 0); assert "rtss.exe" not in O.running_names(0)
print("RTSS riaperto e richiuso: ok")
# EA: l'app riaccende l'overlay -> rimesso
ea = W + "/local/Electronic Arts/EA Desktop"; os.makedirs(ea); os.makedirs(W + "/pf/Electronic Arts/EA Desktop")
open(ea + "/user_1.ini", "w").write("user.x=1\n")
T.apply_one("ov_ea")
open(ea + "/user_1.ini", "w").write("user.x=1\nuser.igoenabled=1\n")
O.guard_once(True)
assert "user.igoenabled=1" in open(ea + "/user_1.ini").read() and "ov_ea" not in T.load_state()
assert T.BY_ID["ov_ea"].status() is False
print("EA riacceso da te nel programma: lasciato acceso e interruttore libero: ok")
T.apply_one("ov_ea"); assert "user.igoenabled=0" in open(ea + "/user_1.ini").read()
calls.clear()
T.revert_one("ov_ea"); assert ["schtasks", "/Delete", "/TN"] not in calls  # resta RTSS
T.revert_one("ov_rtss"); assert ["schtasks", "/Delete", "/TN"] in calls
assert O.guard_once(True) == 0
print("TUTTO OK")
