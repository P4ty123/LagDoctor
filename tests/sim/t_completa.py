import os as _os, sys as _sys  # collaudo simulato: Windows finto (mock) + codice di LagDoctor
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_sys.path.insert(0, _os.path.abspath(_os.path.join(_HERE, "..", "..")))
_sys.path.insert(0, _os.path.join(_HERE, "mock"))
exec(open("audit_tweaks.py").read().split("SKIP = {")[0])
import winreg as WR
# Voce gia' applicata con una versione vecchia (solo TcpAckFrequency e TCPNoDelay): la versione nuova aggiunge
# TcpDelAckTicks da sola all'avvio, salvando il valore di prima; Annulla rimette tutto com'era.
IF = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
k = IF + r"\{11111111-AAAA}"
WR.DB[("HKLM", k.lower())] = {"DhcpIPAddress": ("192.168.1.10", 1)}
st = T.load_state()
st["nagle"] = {"backup": {"reg": [["HKLM", k, "TcpAckFrequency", None, None], ["HKLM", k, "TCPNoDelay", None, None]]},
               "nome": "Disattiva algoritmo di Nagle"}
T.save_state(st)
for n in ("TcpAckFrequency", "TCPNoDelay"):
    T.reg_write("HKLM", k, n, T.DWORD, 1)
print("prima:", T.BY_ID["nagle"].status(), WR.DB[("HKLM", k.lower())])
assert T.BY_ID["nagle"].status() is False  # manca TcpDelAckTicks
assert T.complete_applied() == ["nagle"]
assert T.reg_read("HKLM", k, "TcpDelAckTicks")[0] == 0 and T.BY_ID["nagle"].status() is True
assert T.complete_applied() == []  # la seconda volta non fa niente
T.revert_one("nagle")
vals = WR.DB[("HKLM", k.lower())]
print("dopo Annulla:", vals)
assert set(vals) == {"DhcpIPAddress"}, vals
print("TUTTO OK")
