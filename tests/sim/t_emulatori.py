import os as _os, sys as _sys, tempfile  # collaudo simulato: emulatori riconosciuti come giochi (game mode)
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.abspath(_os.path.join(_HERE, "..", "..")))
_sys.path.insert(0, _os.path.join(_HERE, "mock"))
import winreg as WR
tmp = tempfile.mkdtemp()
home, appdata, local = (_os.path.join(tmp, x) for x in ("utente", "roaming", "local"))
for d in (home, appdata, local):
    _os.makedirs(d)
_os.environ.update(USERPROFILE=home, APPDATA=appdata, LOCALAPPDATA=local, ProgramData=_os.path.join(tmp, "pd"),
                   PUBLIC=_os.path.join(tmp, "pub"))
from lagdoctor import games as G  # noqa: E402
G.winreg = WR  # registro finto anche qui (su Linux il modulo non lo importa)

# nessun emulatore
assert G.emulators() == [], G.emulators()
# PCSX2 installato (programma installato con la sua cartella), RPCS3 portatile (solo collegamento sul desktop),
# DuckStation portatile (solo la cartella dei dati in Documenti)
pcsx2 = _os.path.join(tmp, "PCSX2")
_os.makedirs(pcsx2)
open(_os.path.join(pcsx2, "pcsx2-qt.exe"), "w").close()
WR.DB[("HKLM", r"software\microsoft\windows\currentversion\uninstall")] = {}
WR.DB[("HKLM", r"software\microsoft\windows\currentversion\uninstall\pcsx2")] = {
    "DisplayName": ("PCSX2 - PlayStation 2 Emulator", 1), "InstallLocation": (pcsx2, 1)}
_os.makedirs(_os.path.join(home, "Desktop"))
open(_os.path.join(home, "Desktop", "RPCS3.lnk"), "w").close()
_os.makedirs(_os.path.join(home, "Documents", "DuckStation"))
emu = {g["name"]: g for g in G.emulators()}
print("trovati:", sorted(emu))
assert sorted(emu) == ["DuckStation", "PCSX2", "RPCS3"], sorted(emu)
assert emu["PCSX2"]["exe"] == _os.path.join(pcsx2, "pcsx2-qt.exe") and emu["PCSX2"]["source"] == "emulatore"
m = lambda g, n: G.matches(g, n, r"D:\Emulatori\x\\" + n, lambda: "")
assert m(emu["PCSX2"], "pcsx2-qt.exe") and m(emu["PCSX2"], "PCSX2-QT.EXE") and not m(emu["PCSX2"], "rpcs3.exe")
assert m(emu["RPCS3"], "rpcs3.exe") and m(emu["DuckStation"], "duckstation-qt-x64-ReleaseLTCG.exe")
assert any(g["id"] == "emu:pcsx2" for g in G.detect())
print("emulatori: PCSX2 installato, RPCS3 dal collegamento, DuckStation dai dati; riconosciuti dal nome dell'eseguibile")
