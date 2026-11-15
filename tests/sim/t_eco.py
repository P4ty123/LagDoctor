import os as _os, sys as _sys  # collaudo simulato: Windows finto (mock) + codice di LagDoctor
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.abspath(_os.path.join(_HERE, "..", "..")))
_sys.path.insert(0, _os.path.join(_HERE, "mock"))
import sys
src = open("t_cputopo.py").read().split("CASES = [")[0].replace('', "")
exec(src)
from lagdoctor import cputopo as C
cases = [
    ("AMD Ryzen 7 9800X3D 8-Core Processor", ryzen(1, 8, [96]), False, False),
    ("AMD Ryzen 7 9800X3D 8-Core Processor", ryzen(1, 8, [96]), True, True),     # stesso chip su portatile
    ("AMD Ryzen 9 7950X3D 16-Core Processor", ryzen(2, 8, [96, 32]), False, False),
    ("13th Gen Intel(R) Core(TM) i7-13700K", intel(8, 8), False, True),
    ("13th Gen Intel(R) Core(TM) i5-13600K", intel(6, 8), False, True),
    ("Intel(R) Core(TM) i7-9700K", ryzen(1, 8, [12]), False, False),
    ("AMD Ryzen AI 9 HX 370", ryzen(2, 4, [16, 8]), False, True),  # Zen 5 + Zen 5c (cache diversa)
]
ok = 0
for name, raw, batt, want in cases:
    r = C.eco_decide(C.parse(raw), name, battery=batt)
    good = r["apply"] == want
    ok += good
    print("OK " if good else "NO ", name[:42].ljust(42), "batteria" if batt else "fisso   ", r["apply"], r["why"][:70])
print("corretti %d/%d" % (ok, len(cases)))
sys.exit(0 if ok == len(cases) else 1)
