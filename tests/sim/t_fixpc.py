"""Fix PC: catalogo coerente (id unici, campi presenti, comandi non vuoti) ed esecuzione simulata dei passi."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lagdoctor import fixpc as F  # noqa: E402

cat = F.catalog()
ids = [f["id"] for c in cat["cats"] for f in c["fx"]]
assert len(ids) == len(set(ids)) == len(F.BY_ID), "id duplicati"
assert len(cat["cats"]) >= 10 and len(ids) >= 50
for f in F.BY_ID.values():
    assert f["t"] and f["q"] and f["d"] and f["steps"], f["id"]
    for st in f["steps"]:
        assert st["sh"] in ("cmd", "ps", "py") and st["c"].strip(), f["id"]
        if st["sh"] == "py":
            assert st["fn"] in ("explorer_kill", "explorer_start", "open_wlanreport", "open_battery", "launch_mdsched"), st["fn"]
    assert not (f["ro"] and f["w"]), "un controllo in sola lettura non deve avere avvisi: %s" % f["id"]
# i passi che riavviano i servizi devono girare anche se un passo prima fallisce
for fid in ("wu.ripristina-windows-update", "altro.sblocca-la-coda-di-stampa", "ui.ricostruisci-la-cache-delle-icone"):
    assert F.BY_ID[fid]["steps"][-1]["always"], fid

# esecuzione: il passo 2 fallisce -> si ferma, ma il passo "always" gira lo stesso
seq = []


def fake_popen(step):
    seq.append(step["c"])
    code = 5 if step["c"] == "B" else 0
    p = subprocess.Popen(["bash", "-c", "printf 'riga %s\\r\\n10%%%%\\r100%%%%\\r\\n'; exit %d" % (step["c"], code)],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p, F._decoder("utf-8")


F._popen = fake_popen
F.BY_ID["t"] = {"id": "t", "t": "prova", "r": False, "ro": False, "res": None,
                "steps": [F.cmd("A"), F.cmd("B"), F.cmd("C"), F.cmd("D", always=True)]}
r = F.run("t")
assert seq == ["A", "B", "D"], seq
assert not r["ok"] and "\"B\"" in r["res"], r
assert "100%" in r["out"] and "10%" not in r["out"].replace("100%", ""), r["out"]
seq.clear()
F.BY_ID["t"]["steps"] = [F.cmd("A"), F.cmd("B", soft=True), F.cmd("C")]
r = F.run("t")
assert seq == ["A", "B", "C"] and r["ok"], (seq, r)
print("OK fix pc: %d fix in %d categorie" % (len(ids), len(cat["cats"])))

# console nascosta: riga finale col codice di uscita
from lagdoctor import conrun as C  # noqa: E402
scr = "Verifica 100% completata.\n\nProtezione risorse di Windows non ha rilevato violazioni.\n" + C.MARK + "0\n"
assert C._exit_code(scr) == 0 and C.MARK not in C._clean(scr) and C._clean(scr).endswith("violazioni.")
assert C._exit_code("in corso 45%") is None
assert C._exit_code("x\n" + C.MARK + "-2146498529") == -2146498529
print("OK console nascosta")

# SFC: ogni messaggio (inglese e italiano) deve dare l'esito giusto
casi = [("Windows Resource Protection did not find any integrity violations.", True),
        ("Protezione risorse di Windows non ha rilevato violazioni di integrità.", True),
        ("Windows Resource Protection found integrity violations.", False),
        ("Protezione risorse di Windows ha rilevato violazioni di integrità.", False),
        ("Windows Resource Protection found corrupt files and successfully repaired them.", True),
        ("Protezione risorse di Windows ha rilevato file danneggiati e li ha ripristinati correttamente.", True),
        ("Windows Resource Protection found corrupt files but was unable to fix some of them.", False),
        ("Windows Resource Protection could not perform the requested operation.", False)]
for testo, atteso in casi:
    good, msg = F._sfc("Verification 100% complete.\n" + testo)
    assert good is atteso, (testo, good, msg)
print("OK esiti di SFC")
