"""Icone vere dei giochi: prese dal file .exe del gioco (come quella sul desktop) o dalla cache di Steam.

Le icone vengono salvate in <dati>\\icone\\<id>.png e lette una volta sola. L'estrazione gira in background
(un solo PowerShell per tutti i giochi): finche' non c'e', l'interfaccia mostra il logo o la lettera.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading

from . import paths

DIR = os.path.join(paths.DATA_DIR, "icone")
CREATE_NO_WINDOW = 0x08000000
SKIP_EXE = re.compile(r"crash|unins|setup|install|redist|vc_?redist|dxsetup|directx|easyanticheat|eac|beservice|battleye|"
                      r"report|helper|launcher|bootstrap|updater|update|prereq|cefprocess|webhelper|dotnet|vcredist|"
                      r"ue4prereq|uninst|cleanup|benchmark|config|settings|tool|editor|server|dedicated|touchup", re.I)
_LOCK = threading.Lock()
_BUSY = {"on": False}

PS = r'''
$ErrorActionPreference = 'Stop'
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @"
using System; using System.Drawing; using System.Drawing.Imaging; using System.Runtime.InteropServices;
public static class LdIcon {
  [ComImport, Guid("bcc18b79-ba16-442f-80c4-8a59c30c463b"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
  interface IShellItemImageFactory { [PreserveSig] int GetImage(SIZE size, int flags, out IntPtr phbm); }
  [StructLayout(LayoutKind.Sequential)] struct SIZE { public int cx; public int cy; }
  [DllImport("shell32.dll", CharSet = CharSet.Unicode, PreserveSig = false)]
  static extern void SHCreateItemFromParsingName(string path, IntPtr pbc, [MarshalAs(UnmanagedType.LPStruct)] Guid riid,
                                                 [MarshalAs(UnmanagedType.Interface)] out IShellItemImageFactory ppv);
  [DllImport("gdi32.dll")] static extern bool DeleteObject(IntPtr h);
  public static void Save(string exe, string png, int size) {
    IShellItemImageFactory f;
    SHCreateItemFromParsingName(exe, IntPtr.Zero, typeof(IShellItemImageFactory).GUID, out f);
    SIZE s; s.cx = size; s.cy = size; IntPtr hbm;
    int hr = f.GetImage(s, 0x4 /* solo icona */, out hbm);
    if (hr != 0) Marshal.ThrowExceptionForHR(hr);
    try {
      using (Bitmap b = Image.FromHbitmap(hbm)) {
        BitmapData d = b.LockBits(new Rectangle(0, 0, b.Width, b.Height), ImageLockMode.ReadOnly, b.PixelFormat);
        try {
          using (Bitmap a = new Bitmap(d.Width, d.Height, d.Stride, PixelFormat.Format32bppArgb, d.Scan0))
          using (Bitmap o = new Bitmap(a)) { o.Save(png, ImageFormat.Png); }
        } finally { b.UnlockBits(d); }
      }
    } finally { DeleteObject(hbm); }
  }
}
"@
foreach ($j in (Get-Content -Raw -Encoding UTF8 $args[0] | ConvertFrom-Json)) {
  try { [LdIcon]::Save($j.exe, $j.png, 128); 'OK|' + $j.png }
  catch {
    try { $i = [System.Drawing.Icon]::ExtractAssociatedIcon($j.exe); $i.ToBitmap().Save($j.png, [System.Drawing.Imaging.ImageFormat]::Png); 'OK|' + $j.png }
    catch { 'ERR|' + $j.png + '|' + $_.Exception.Message }
  }
}
'''


def key(gid):
    return re.sub(r"[^a-z0-9_-]+", "-", str(gid).lower()).strip("-")[:80] or "x"


def path_for(gid):
    return os.path.join(DIR, key(gid) + ".png")


def have(gid):
    p = path_for(gid)
    return os.path.isfile(p) and os.path.getsize(p) > 100


def exe_key(exe):
    return "exe-" + hashlib.sha1(os.path.normcase(exe).encode("utf-8", "replace")).hexdigest()[:16]


def _norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def find_exe(game):
    """L'eseguibile principale del gioco: nella sua cartella, il .exe piu' simile al nome e piu' grande."""
    if game.get("exe"):
        return game["exe"] if os.path.isfile(game["exe"]) else None
    d = game.get("dir")
    if not d or not os.path.isdir(d):
        return None
    want = _norm(game.get("name"))
    best, best_score = None, -1
    base_depth = d.rstrip("\\/").count(os.sep)
    n = 0
    for root, dirs, files in os.walk(d):
        if root.count(os.sep) - base_depth >= 4:
            dirs[:] = []
        dirs[:] = [x for x in dirs if not re.search(r"redist|prereq|support|_commonredist|directx|easyanticheat|battleye|"
                                                     r"crash|engine\\binaries\\thirdparty|thirdparty|tools", x, re.I)]
        for f in files:
            if not f.lower().endswith(".exe"):
                continue
            n += 1
            if n > 400:
                break
            stem = f[:-4]
            if SKIP_EXE.search(stem):
                continue
            full = os.path.join(root, f)
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            ns = _norm(stem)
            score = min(size / 2**20, 200)  # i giochi hanno eseguibili grandi
            if ns and want and (ns in want or want in ns):
                score += 300
            elif ns and want and ns[:4] == want[:4]:
                score += 120
            if re.search(r"win64|shipping|x64", stem, re.I):
                score += 40
            if score > best_score:
                best, best_score = full, score
    return best


def _steam_icon(game):
    """icona che Steam ha gia' salvato (piccola, ma e' quella giusta)."""
    if not str(game.get("id", "")).startswith("steam:"):
        return None
    appid = game["id"].split(":", 1)[1]
    try:
        from .games import winreg, _reg
        base = _reg(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath") if winreg else None
    except Exception:
        base = None
    if not base:
        return None
    lc = os.path.join(base, "appcache", "librarycache")
    for p in [os.path.join(lc, appid + "_icon.jpg")] + glob.glob(os.path.join(lc, appid, "*.jpg")):
        b = os.path.basename(p).lower()
        if re.fullmatch(r"[0-9a-f]{40}\.jpg", b) or b.endswith("_icon.jpg"):
            return p
    return None


def extract(items, timeout=120):
    """items: [(id, exe)]. Salva le icone; ritorna gli id riusciti."""
    if os.name != "nt" or not items:
        return []
    os.makedirs(DIR, exist_ok=True)
    jobs = [{"exe": exe, "png": path_for(gid)} for gid, exe in items]
    tmp = tempfile.mkdtemp(prefix="ld-ico-")
    lst, script = os.path.join(tmp, "lista.json"), os.path.join(tmp, "icone.ps1")
    with open(lst, "w", encoding="utf-8") as f:
        json.dump(jobs, f)
    with open(script, "w", encoding="utf-8-sig") as f:
        f.write(PS)
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", script, lst],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                           creationflags=CREATE_NO_WINDOW)
        out = r.stdout
    except (OSError, subprocess.TimeoutExpired):
        out = ""
    finally:
        for p in (lst, script):
            try:
                os.remove(p)
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass
    done = {os.path.normcase(l.split("|")[1]) for l in out.splitlines() if l.startswith("OK|")}
    return [gid for gid, _exe in items if os.path.normcase(path_for(gid)) in done and have(gid)]


def ensure(games, wait=False):
    """Prepara le icone mancanti dei giochi (in background). Ritorna True se ne mancano ancora."""
    bad = failed()
    todo = [g for g in games if g.get("id") and not have(g["id"]) and g["id"] not in bad]
    if not todo or os.name != "nt":
        return False

    def work():
        try:
            items = []
            for g in todo:
                exe = find_exe(g)
                if exe:
                    items.append((g["id"], exe))
                else:
                    st = _steam_icon(g)
                    if st:
                        _copy_jpg(st, g["id"])
            ok = set(extract(items))
            for gid, _e in items:
                if gid not in ok:
                    st = _steam_icon({"id": gid})
                    if st:
                        _copy_jpg(st, gid)
            _mark_failed([g["id"] for g in todo if not have(g["id"])])
        finally:
            _BUSY["on"] = False
    with _LOCK:
        if _BUSY["on"]:
            return True
        _BUSY["on"] = True
    t = threading.Thread(target=work, daemon=True)
    t.start()
    if wait:
        t.join()
    return True


FAILED = os.path.join(DIR, "non_trovate.json")


def _mark_failed(ids):
    """giochi senza icona: non si riprova a ogni apertura della pagina (si riprova con 'Cerca di nuovo')."""
    try:
        old = set(json.load(open(FAILED, encoding="utf-8")))
    except (OSError, ValueError):
        old = set()
    try:
        os.makedirs(DIR, exist_ok=True)
        with open(FAILED, "w", encoding="utf-8") as f:
            json.dump(sorted(old | set(ids)), f)
    except OSError:
        pass


def failed():
    try:
        return set(json.load(open(FAILED, encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def forget_failed():
    try:
        os.remove(FAILED)
    except OSError:
        pass


def _copy_jpg(src, gid):
    """l'icona di Steam e' un jpg: la servo cosi' com'e' (il nome .png non conta per il browser)."""
    try:
        os.makedirs(DIR, exist_ok=True)
        with open(src, "rb") as a, open(path_for(gid), "wb") as b:
            b.write(a.read())
    except OSError:
        pass


def busy():
    return _BUSY["on"]
