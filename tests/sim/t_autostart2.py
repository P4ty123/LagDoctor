import os as _os, sys as _sys  # collaudo simulato: Windows finto (mock) + codice di LagDoctor
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.abspath(_os.path.join(_HERE, "..", "..")))
_sys.path.insert(0, _os.path.join(_HERE, "mock"))
import os, sys, tempfile
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "mock"))
os.environ["LAGDOCTOR_DATA"] = tempfile.mkdtemp()
import winreg
from lagdoctor import autostart as A
A.FILE = os.path.join(os.environ["LAGDOCTOR_DATA"], "avvio_processi.json")
for c in ['"C:\\Program Files\\X\\a b.exe" -k', 'C:\\Windows\\system32\\svchost.exe -k netsvcs -p', 'C:\\P\\x.exe', '"C:\\only"']:
    print(repr(c), "->", A._exe_of(c))
runs = []
A._run = lambda args, timeout=60: (runs.append(args), (0, ""))[1]
winreg.DB[("HKLM", r"system\currentcontrolset\services\adobearmservice")] = {"Start": (2, 4), "DelayedAutostart": (1, 4)}
print(A.set_enabled("svc", "AdobeARMservice", False)); assert runs[-2][-1] == "disabled" and runs[-1][:2] == ["sc", "stop"]
print(A.set_enabled("svc", "AdobeARMservice", True)); assert runs[-2][-1] == "delayed-auto" and runs[-1][:2] == ["sc", "start"]
print(A.set_enabled("task", "\\GoogleUpdaterTaskSystem", False, "/nonexist.exe")); assert ["schtasks", "/Change", "/TN", "\\GoogleUpdaterTaskSystem", "/DISABLE"] in runs
print(A.set_enabled("task", "\\GoogleUpdaterTaskSystem", True)); assert runs[-1][-1] == "/ENABLE"
A._services = lambda: [dict(kind="svc", id="A", name="Adobe Update", exe="C:\\x\\armsvc.exe", company="Adobe", start=2, delayed=0, state="Running", pid=os.getpid(), desc="", inwin=False, mstask=False)]
A._tasks = lambda: ([], "attivita' non lette")
r = A.list_items(); print(len(r["items"]), r["error"], r["items"][0]["running"], r["items"][0]["mb"])
print("TUTTO OK")
