"""Effetti visivi con SystemParametersInfo e registro simulati."""
import os as _os, sys as _sys  # collaudo simulato: Windows finto (mock) + codice di LagDoctor
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.abspath(_os.path.join(_HERE, "..", "..")))
_sys.path.insert(0, _os.path.join(_HERE, "mock"))

import ctypes
import sys

import winreg  # mock
from lagdoctor import tweaks as T

# stato di Windows: tutto acceso (Windows appena installato)
SPI_STATE = {s: True for _n, _g, s, _m in T.VisualFxTweak.SPI}
STATE = {"min": True, "font": True}


class FakeU32:
    def __init__(self):
        self.SystemParametersInfoW = self

    def __call__(self, action, ui, pv, flags):
        for _n, g, s, m in T.VisualFxTweak.SPI:
            if action == g:
                pv._obj.value = int(SPI_STATE[s])
                return 1
            if action == s:
                SPI_STATE[s] = bool(ui) if m == "ui" else bool(pv.value)
                return 1
        if action == 0x0048:
            pv._obj.iMinAnimate = int(STATE["min"])
            return 1
        if action == 0x0049:
            STATE["min"] = bool(pv._obj.iMinAnimate)
            return 1
        return 0


T.VisualFxTweak._u32 = lambda self: (ctypes, FakeU32())
winreg.DB[("HKCU", r"control panel\desktop")] = {"UserPreferencesMask": (bytes.fromhex("9e1e078012000000"), 3)}
t = T.BY_ID["visual_fx"]
print("prima:", t.status())
assert t.status() is False
b = t.apply()
print("dopo applica:", t.status(), "| tutte le caselle spente:", not any(SPI_STATE.values()), "| minimizza:", STATE["min"])
assert t.status() is True and not any(SPI_STATE.values()) and STATE["min"] is False
assert T.reg_read("HKCU", T.VisualFxTweak.ADV, "IconsOnly")[0] == 0  # anteprime restano
assert T.reg_read("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects", "VisualFXSetting")[0] == 3
t.revert(b)
print("dopo annulla:", t.status(), "| caselle di nuovo accese:", all(SPI_STATE.values()), "| UPM:",
      T.reg_read("HKCU", r"Control Panel\Desktop", "UserPreferencesMask")[0].hex())
assert all(SPI_STATE.values()) and STATE["min"] is True
assert T.reg_read("HKCU", T.VisualFxTweak.ADV, "ListviewShadow")[0] is None
# vecchia versione (solo registro) applicata in passato: Annulla deve funzionare lo stesso
old = {"reg": [["HKCU", r"Software\Microsoft\Windows\DWM", "EnableAeroPeek", None, None]]}
T.reg_write("HKCU", r"Software\Microsoft\Windows\DWM", "EnableAeroPeek", 4, 0)
t.revert(old)
assert T.reg_read("HKCU", r"Software\Microsoft\Windows\DWM", "EnableAeroPeek")[0] is None
print("annulla di una versione precedente: ok")
print("TUTTO OK")
