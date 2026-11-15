"""Overlay: spegnimento e ripristino con file e processi finti (Linux)."""
import os as _os, sys as _sys  # collaudo simulato: Windows finto (mock) + codice di LagDoctor
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.abspath(_os.path.join(_HERE, "..", "..")))
_sys.path.insert(0, _os.path.join(_HERE, "mock"))

import os
import shutil
import subprocess
import sys
import tempfile
import time

S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "mock"))
W = tempfile.mkdtemp()
os.environ.update({"ProgramFiles": W + "/pf", "ProgramFiles(x86)": W + "/pf86", "LOCALAPPDATA": W + "/local",
                   "LAGDOCTOR_DATA": W + "/data"})
os.makedirs(W + "/data")
import winreg  # mock
from lagdoctor import tweaks as T, overlays as O

T.init(W + "/data")

# ---------------- Steam: due account, uno senza la chiave e senza blocco system
st = W + "/pf86/Steam/userdata"
os.makedirs(st + "/1/config"); os.makedirs(st + "/2/config")
A = '"UserLocalConfigStore"\r\n{\r\n\t"system"\r\n\t{\r\n\t\t"EnableGameOverlay"\t\t"1"\r\n\t\t"Other"\t\t"x"\r\n\t}\r\n}\r\n'
B = '"UserLocalConfigStore"\n{\n\t"friends"\n\t{\n\t}\n}\n'
open(st + "/1/config/localconfig.vdf", "w", newline="").write(A)
open(st + "/2/config/localconfig.vdf", "w", newline="").write(B)
assert O.steam_overlay_enabled() in (True,)
r = T.apply_one("ov_steam"); print("steam:", r)
a2 = open(st + "/1/config/localconfig.vdf", newline="").read(); b2 = open(st + "/2/config/localconfig.vdf", newline="").read()
assert '"EnableGameOverlay"\t\t"0"' in a2 and "\r\n" in a2 and '"Other"' in a2, a2
assert '"system"' in b2 and '"EnableGameOverlay"\t\t"0"' in b2, b2
os.utime(st + "/2/config/localconfig.vdf", (time.time() - 100, time.time() - 100))
assert T.BY_ID["ov_steam"].status() is True
T.revert_one("ov_steam")
assert open(st + "/1/config/localconfig.vdf", newline="").read() == A
assert "EnableGameOverlay" not in open(st + "/2/config/localconfig.vdf").read()
print("steam ripristinato: ok")

# ---------------- EA
ea = W + "/local/Electronic Arts/EA Desktop"; os.makedirs(ea); os.makedirs(W + "/pf/Electronic Arts/EA Desktop")
open(ea + "/user_123.ini", "w").write("user.downloadinplace=true\n")
assert O.ea_overlay_enabled() is True
T.apply_one("ov_ea"); assert "user.igoenabled=0" in open(ea + "/user_123.ini").read()
assert T.BY_ID["ov_ea"].status() is True
T.revert_one("ov_ea"); assert open(ea + "/user_123.ini").read() == "user.downloadinplace=true\n"
print("EA: ok")

# ---------------- Ubisoft
ub = W + "/local/Ubisoft Game Launcher"; os.makedirs(ub); os.makedirs(W + "/pf86/Ubisoft/Ubisoft Game Launcher")
U = "language: it-IT\noverlay:\n  enabled: true\n  fps_enabled: false\nmisc:\n  x: 1\n"
open(ub + "/settings.yml", "w").write(U)
assert T.BY_ID["ov_ubisoft"].status() is False
T.apply_one("ov_ubisoft"); assert "  enabled: false\n  fps_enabled" in open(ub + "/settings.yml").read()
assert T.BY_ID["ov_ubisoft"].status() is True
T.revert_one("ov_ubisoft"); assert open(ub + "/settings.yml").read() == U
print("Ubisoft: ok")

# ---------------- RivaTuner: processo + avvio con Windows
os.makedirs(W + "/pf86/RivaTuner Statistics Server"); open(W + "/pf86/RivaTuner Statistics Server/RTSS.exe", "w").close()
shutil.copy("/bin/sleep", W + "/rtss.exe")
p = subprocess.Popen([W + "/rtss.exe", "300"])
winreg.DB[("HKCU", r"software\microsoft\windows\currentversion\run")] = {"RTSS": ('"C:\\RTSS\\RTSS.exe" /s', 1)}
time.sleep(0.5)
assert T.BY_ID["ov_rtss"].status() is False
T.apply_one("ov_rtss"); p.wait(5)
assert T.BY_ID["ov_rtss"].status() is True
assert [i for i in T.startup_items() if i["name"] == "RTSS"][0]["enabled"] is False
assert "rtss.exe" in O.blocked_processes()
T.revert_one("ov_rtss")
assert [i for i in T.startup_items() if i["name"] == "RTSS"][0]["enabled"] is True
assert "rtss.exe" not in O.blocked_processes()
print("RivaTuner: ok")
print("TUTTO OK")
