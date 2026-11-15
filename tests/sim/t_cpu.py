"""Utilizzo CPU della Panoramica: se il contatore '% Processor Utility' di Windows si guasta (100% a riposo, visto
su un mini PC Intel N95) si usa il tempo di CPU vero."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ.setdefault("LAGDOCTOR_DATA", tempfile.mkdtemp())
from lagdoctor import server as S  # noqa: E402


class Q:
    ok = True

    def __init__(self, util, t):
        self.v = {"util": util, "time": t}

    def collect(self):
        return self.v


def prova(util, t, ref):
    S._CPU.update(q=Q(util, t), times=None, hist=[])
    S._cpu_times_util = lambda: ref
    return S._cpu_util_locked()


assert prova(100.0, 2.0, 3.0) == 3.0          # contatore guasto: 100% a riposo -> tempo di CPU
assert prova(130.0, 60.0, 60.0) == 100.0      # turbo: utilita' sopra il tempo, ma credibile
assert prova(35.0, 20.0, 22.0) == 35.0        # normale
assert prova(80.0, 30.0, None) == 80.0        # senza riferimento: il contatore
print("OK utilizzo CPU")
