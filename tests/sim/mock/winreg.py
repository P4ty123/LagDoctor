HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE = "HKCU", "HKLM"
HKEY_USERS = "HKU"
KEY_READ = KEY_WRITE = KEY_WOW64_64KEY = 0
REG_DWORD, REG_SZ = 4, 1
DB = {}
class _K:
    def __init__(s, h, p): s.k = (h, p.lower())
    def __enter__(s): return s
    def __exit__(s, *a): pass
def OpenKey(h, p, *a):
    if (h, p.lower()) not in DB: raise OSError("nokey")
    return _K(h, p)
def CreateKeyEx(h, p, *a):
    DB.setdefault((h, p.lower()), {}); return _K(h, p)
def QueryValueEx(k, n):
    d = DB.get(k.k, {})
    if n not in d: raise OSError("noval")
    return d[n]
def SetValueEx(k, n, r, t, v): DB.setdefault(k.k, {})[n] = (v, t)
def DeleteValue(k, n):
    if n not in DB.get(k.k, {}): raise OSError
    del DB[k.k][n]
def EnumKey(k, i):
    pre = k.k[1] + "\\"
    subs = sorted({p[len(pre):].split("\\")[0] for (h, p) in DB if h == k.k[0] and p.startswith(pre)})
    if i >= len(subs): raise OSError
    return subs[i]
def EnumValue(k, i):
    items = list(DB.get(k.k, {}).items())
    if i >= len(items): raise OSError
    n, (v, t) = items[i]; return n, v, t
