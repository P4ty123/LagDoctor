"""Panoramica: attivita' recenti (ordine, limite, durate) e dati in piu' (disco, ecc.)."""
import os
import sys
import tempfile

os.environ["LAGDOCTOR_DATA"] = tempfile.mkdtemp()
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lagdoctor import activity as A  # noqa: E402

for i in range(70):
    A.add("tweaks", "voce %d" % i, "tweaks")
r = A.recent(5)
assert [x["text"] for x in r] == ["voce 69", "voce 68", "voce 67", "voce 66", "voce 65"], r
assert len(A._load()) == A.MAX
assert A.durata(30) == "1 min" and A.durata(42 * 60) == "42 min" and A.durata(102 * 60) == "1 h 42 min" and A.durata(120 * 60) == "2 h"
from lagdoctor import server as S  # noqa: E402
h = S.home_json()
assert set(h) >= {"activity", "windows", "last_backup", "disk"} and h["disk"]["total_gb"] > 0, h
print("OK attivita' recenti e dati della Panoramica")
