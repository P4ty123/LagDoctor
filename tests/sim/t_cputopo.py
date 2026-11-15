"""Costruisce i dati binari di GetLogicalProcessorInformationEx per vari processori e controlla la decisione."""
import os as _os, sys as _sys  # collaudo simulato: Windows finto (mock) + codice di LagDoctor
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.abspath(_os.path.join(_HERE, "..", "..")))
_sys.path.insert(0, _os.path.join(_HERE, "mock"))

import struct
import sys

from lagdoctor import cputopo as C


def core(cpus, eff):
    mask = sum(1 << c for c in cpus)
    body = struct.pack("<BB20sH", 1 if len(cpus) > 1 else 0, eff, b"\0" * 20, 1)
    body += struct.pack("<QH6s", mask, 0, b"\0" * 6)
    return struct.pack("<II", 0, 8 + len(body)) + body


def l3(cpus, mb):
    mask = sum(1 << c for c in cpus)
    body = struct.pack("<BBHII18sH", 3, 16, 64, mb * 2**20, 0, b"\0" * 18, 1)
    body += struct.pack("<QH6s", mask, 0, b"\0" * 6)
    return struct.pack("<II", 2, 8 + len(body)) + body


def l2(cpus):
    mask = sum(1 << c for c in cpus)
    body = struct.pack("<BBHII18sH", 2, 8, 64, 1 * 2**20, 0, b"\0" * 18, 1)
    body += struct.pack("<QH6s", mask, 0, b"\0" * 6)
    return struct.pack("<II", 2, 8 + len(body)) + body


def ryzen(ccds, cores_per, l3s):
    raw, cpu = b"", 0
    for i in range(ccds):
        cc = list(range(cpu, cpu + cores_per * 2))
        for k in range(cores_per):
            raw += core([cpu + 2 * k, cpu + 2 * k + 1], 0) + l2([cpu + 2 * k, cpu + 2 * k + 1])
        raw += l3(cc, l3s[i])
        cpu += cores_per * 2
    return raw


def intel(p, e, l3mb=36):
    raw, cpu = b"", 0
    for _ in range(p):
        raw += core([cpu, cpu + 1], 1)
        cpu += 2
    for _ in range(e):
        raw += core([cpu], 0)
        cpu += 1
    raw += l3(list(range(cpu)), l3mb)
    return raw


CASES = [
    ("AMD Ryzen 7 9800X3D 8-Core Processor", ryzen(1, 8, [96]), False, None),
    ("AMD Ryzen 9 7950X3D 16-Core Processor", ryzen(2, 8, [96, 32]), True, list(range(0, 16))),
    ("AMD Ryzen 9 9950X3D 16-Core Processor (cache sul secondo CCD)", ryzen(2, 8, [32, 96]), True, list(range(16, 32))),
    ("AMD Ryzen 9 9950X 16-Core Processor", ryzen(2, 8, [32, 32]), True, list(range(0, 16))),
    ("AMD Ryzen 9 5900X 12-Core Processor", ryzen(2, 6, [32, 32]), True, list(range(0, 12))),
    ("AMD Ryzen AI 9 HX 370 w/ Radeon 890M", ryzen(2, 4, [16, 8]), False, None),
    ("AMD Ryzen 5 7600X 6-Core Processor", ryzen(1, 6, [32]), False, None),
    ("AMD Ryzen 5 5600", ryzen(1, 6, [32]), False, None),
    ("13th Gen Intel(R) Core(TM) i9-13900K", intel(8, 16), True, list(range(0, 16))),
    ("Intel(R) Core(TM) Ultra 9 285K (senza HT)", None, True, None),
    ("12th Gen Intel(R) Core(TM) i5-12400F", intel(6, 0), False, None),
    ("13th Gen Intel(R) Core(TM) i5-13600K", intel(6, 8), False, None),
    ("Intel(R) Core(TM) i7-9700K", intel(8, 0, 12), False, None),
]
ok = 0
for name, raw, want, cpus in CASES:
    if raw is None:  # Core Ultra 200S: 8 core P senza HT + 16 core E
        raw, cpu = b"", 0
        for _ in range(8):
            raw += core([cpu], 1); cpu += 1
        for _ in range(16):
            raw += core([cpu], 0); cpu += 1
        raw += l3(list(range(24)), 36)
        cpus = list(range(8))
    topo = C.parse(raw)
    d = C.decide(topo, name)
    good = d["apply"] == want and (cpus is None or d["cpus"] == cpus)
    ok += good
    print("%-4s %-62s %-6s %s" % ("OK" if good else "ERR", name[:62], d["apply"], (d.get("why") or "")[:110]))
print("corretti: %d/%d" % (ok, len(CASES)))
assert ok == len(CASES)
sys.exit(0 if ok == len(CASES) else 1)
