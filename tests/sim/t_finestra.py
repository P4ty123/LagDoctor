"""Finestra nuova: prima di aprirla si aspetta che i processi WebView2 della finestra di prima siano chiusi
(riaprirla subito la faceva andare in crash). Qui con processi finti che hanno la stessa cartella dei dati."""
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
os.environ.setdefault("LAGDOCTOR_DATA", tempfile.mkdtemp())
from lagdoctor import server as S  # noqa: E402

names = (os.path.basename(sys.executable).lower(),)
mark = "--user-data-dir=c:\\programdata\\lagdoctor\\strumenti\\finestra-webview2"
# uno si chiude da solo dopo 1 secondo, uno resta appeso
a = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1)", mark])
b = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", mark])
c = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "--altro"])  # non c'entra
time.sleep(0.3)
t0 = time.time()
n = S._wait_webview_leftovers(timeout=2.0, names=names, mark="finestra-webview2")
dt = time.time() - t0
assert n == 2, n
assert a.poll() is not None and b.poll() is not None, "rimasti processi della finestra di prima"
assert c.poll() is None, "chiuso un processo che non c'entra"
assert 1.5 < dt < 6, dt
assert S._wait_webview_leftovers(timeout=2.0, names=names, mark="finestra-webview2") == 0
c.kill()
print("OK finestra: processi rimasti aspettati/chiusi in %.1f s" % dt)
