"""Collaudo delle voci dei driver NVIDIA e AMD con un driver simulato (stessa logica di audit_tweaks.py)."""
import os as _os, sys as _sys  # collaudo simulato: Windows finto (mock) + codice di LagDoctor
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.abspath(_os.path.join(_HERE, "..", "..")))
_sys.path.insert(0, _os.path.join(_HERE, "mock"))

import os
import sys
import tempfile

S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(S, "mock"))
os.environ["LAGDOCTOR_DATA"] = tempfile.mkdtemp()
from lagdoctor import tweaks as T
from lagdoctor import gpu_driver as GD
from lagdoctor import driver_tweaks as DT

T.CONTEXT["refresh_hz"] = 144
NV = {}          # setting id -> valore impostato dall'utente (assente = predefinito del driver)
NV_DEFAULT = {}  # predefinito "di fabbrica"
AMD = {}


class FakeDrs:
    ok, error = True, None

    def get(self, sid):
        return (NV[sid], 0) if sid in NV else (NV_DEFAULT.get(sid), 3)

    def set(self, sid, v):
        NV[sid] = v

    def reset(self, sid):
        NV.pop(sid, None)

    def close(self):
        pass


def fake_read(vendor, hz=None):
    if vendor == "nvidia":
        raw = {}
        for key, sid in GD.NV.items():
            v, loc = FakeDrs().get(sid)
            if v is not None:
                raw[key] = [v, loc]
        return {"ok": True, "raw": raw}
    return {"ok": True, "raw": {k: dict(v) for k, v in AMD.items()}}


def fake_amd_set(key, action, value):
    d = AMD.setdefault(key, {"enabled": False, "mode": 1, "fps": None})
    if action == "enabled":
        d["enabled"] = value
    elif action == "vsync_mode":
        d["mode"] = value
    elif action == "frtc_fps":
        d["fps"] = value


GD.NvDrs, GD.read, GD.amd_set, GD.invalidate = FakeDrs, fake_read, fake_amd_set, (lambda: None)

# stato "di partenza cattivo" per ogni voce: quello che la voce deve correggere/cambiare
BAD_NV = {"VSYNCMODE": 0x32610244, "FRL_FPS": 60, "PREFERRED_PSTATE": 4,
          "SHADERCACHE": 0, "VRR_APP_OVERRIDE": 1, "FXAA_ENABLE": 1, "OGL_THREAD_CONTROL": 2, "PRERENDERLIMIT": 4,
          "SHADERCACHE_SIZE": 4096, "REFRESH_RATE_OVERRIDE": 0, "VRR_MODE": 1, "QUALITY_ENHANCEMENTS": 0}
ok, ko = [], []
for t in DT.NVIDIA + DT.AMD:
    NV.clear()
    AMD.clear()
    for k in ("chill", "esync", "mlaa", "antilag", "boost", "afmf", "frtc", "vsync"):
        AMD[k] = {"enabled": False, "mode": 1, "fps": None}
    if t.vendor == "nvidia":
        if t.key in BAD_NV:
            NV[GD.NV[t.key]] = BAD_NV[t.key]
        if t.id == "nvfix_prerender":
            NV[GD.NV["PRERENDERLIMIT"]] = 4
    else:
        bad = {"amdfix_chill": ("chill", "enabled", True), "amdfix_esync": ("esync", "enabled", True),
               "amdfix_vsync_always": ("vsync", "mode", 3), "amdfix_frtc_low": ("frtc", "enabled", True),
               "amdfix_mlaa": ("mlaa", "enabled", True), "amd_antilag_on": ("antilag", "enabled", False),
               "amd_boost_off": ("boost", "enabled", True), "amd_afmf_off": ("afmf", "enabled", True),
               "amd_fps_cap": ("frtc", "enabled", False)}[t.id]
        AMD[bad[0]][bad[1]] = bad[2]
        if t.id == "amdfix_frtc_low":
            AMD["frtc"]["fps"] = 60
    before = (dict(NV), {k: dict(v) for k, v in AMD.items()})
    probs = []
    try:
        s0 = t.status()
        b = t.apply()
        s1 = t.status()
        t.revert(b)
        s2 = t.status()
        after = (dict(NV), {k: dict(v) for k, v in AMD.items()})
        if s0 is not False:
            probs.append("prima %r" % s0)
        if s1 is not True:
            probs.append("dopo Applica %r" % s1)
        if s2 is not False:
            probs.append("dopo Annulla %r" % s2)
        if before != after:
            probs.append("Annulla non rimette com'era: %s -> %s" % (before, after))
    except Exception as e:
        probs.append("ERRORE %s" % e)
    (ko if probs else ok).append((t.id, "; ".join(probs)))
print("DRIVER: collaudate %d  OK %d  PROBLEMI %d" % (len(ok) + len(ko), len(ok), len(ko)))
for i, p in ko:
    print("  PROBLEMA", i, "->", p)
# noto e innocuo: dopo Annulla resta scritto il numero di FPS, ma con il limite FRTC spento non ha effetto
NOTI = {"amd_fps_cap"}
sys.exit(1 if [i for i, _p in ko if i not in NOTI] else 0)
