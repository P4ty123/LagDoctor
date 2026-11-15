"""Esegue un comando in una console nascosta e ne legge lo schermo mentre gira.

Perche': quando l'uscita di un programma va in una pipe, molti comandi di Windows (sfc, DISM, chkdsk, defrag)
la trattengono e la consegnano a blocchi, e le percentuali avanzano a scatti (38% -> 74%). Leggendo direttamente
lo schermo della sua console si vede esattamente quello che si vedrebbe nel Prompt dei comandi, aggiornato in
tempo reale, e senza problemi di codifica (sfc scrive in UTF-16, i comandi cmd nella code page OEM).

Funziona solo se il processo di LagDoctor non ha gia' una console (l'exe con finestra non ce l'ha): altrimenti
available() e' False e si usa la pipe.
"""
import ctypes
import os
import time

if os.name == "nt":
    from ctypes import wintypes as W

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [("cb", W.DWORD), ("lpReserved", W.LPWSTR), ("lpDesktop", W.LPWSTR), ("lpTitle", W.LPWSTR),
                    ("dwX", W.DWORD), ("dwY", W.DWORD), ("dwXSize", W.DWORD), ("dwYSize", W.DWORD),
                    ("dwXCountChars", W.DWORD), ("dwYCountChars", W.DWORD), ("dwFillAttribute", W.DWORD),
                    ("dwFlags", W.DWORD), ("wShowWindow", W.WORD), ("cbReserved2", W.WORD),
                    ("lpReserved2", ctypes.c_void_p), ("hStdInput", W.HANDLE), ("hStdOutput", W.HANDLE),
                    ("hStdError", W.HANDLE)]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [("hProcess", W.HANDLE), ("hThread", W.HANDLE), ("dwProcessId", W.DWORD), ("dwThreadId", W.DWORD)]

    class COORD(ctypes.Structure):
        _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

    class SMALL_RECT(ctypes.Structure):
        _fields_ = [("Left", ctypes.c_short), ("Top", ctypes.c_short), ("Right", ctypes.c_short), ("Bottom", ctypes.c_short)]

    class CSBI(ctypes.Structure):
        _fields_ = [("dwSize", COORD), ("dwCursorPosition", COORD), ("wAttributes", W.WORD),
                    ("srWindow", SMALL_RECT), ("dwMaximumWindowSize", COORD)]

    k32.CreateProcessW.argtypes = [W.LPCWSTR, W.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, W.BOOL, W.DWORD,
                                   ctypes.c_void_p, W.LPCWSTR, ctypes.POINTER(STARTUPINFOW),
                                   ctypes.POINTER(PROCESS_INFORMATION)]
    k32.CreateFileW.restype = W.HANDLE
    k32.CreateFileW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, ctypes.c_void_p, W.DWORD, W.DWORD, W.HANDLE]
    k32.ReadConsoleOutputCharacterW.argtypes = [W.HANDLE, W.LPWSTR, W.DWORD, COORD, ctypes.POINTER(W.DWORD)]
    k32.GetConsoleScreenBufferInfo.argtypes = [W.HANDLE, ctypes.POINTER(CSBI)]
    k32.GetConsoleWindow.restype = W.HWND
    k32.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]
    k32.GetExitCodeProcess.argtypes = [W.HANDLE, ctypes.POINTER(W.DWORD)]
    k32.ResumeThread.argtypes = [W.HANDLE]
    k32.CloseHandle.argtypes = [W.HANDLE]
    k32.AttachConsole.argtypes = [W.DWORD]
    k32.GetConsoleProcessList.argtypes = [ctypes.POINTER(W.DWORD), W.DWORD]

CREATE_NEW_CONSOLE = 0x10
CREATE_SUSPENDED = 0x4
CREATE_UNICODE_ENVIRONMENT = 0x400
STARTF_USESHOWWINDOW = 0x1
STARTF_USECOUNTCHARS = 0x8
SW_HIDE = 0
WIDTH = 200
HEIGHT = 9000
INVALID = ctypes.c_void_p(-1).value


def _has_console():
    buf = (ctypes.c_ulong * 4)()
    return k32.GetConsoleProcessList(buf, 4) > 0


def available():
    if os.name != "nt" or os.environ.get("LAGDOCTOR_NO_CONSOLE_READ"):
        return False
    try:
        return not _has_console()
    except Exception:
        return False


class Failed(Exception):
    """la console non si e' potuta usare: il chiamante usa la pipe (il processo non e' mai partito)."""


def _screen(h):
    info = CSBI()
    if not k32.GetConsoleScreenBufferInfo(h, ctypes.byref(info)):
        return None
    w, last = info.dwSize.X, info.dwCursorPosition.Y
    n = w * (last + 1)
    buf = ctypes.create_unicode_buffer(n + 1)
    got = W.DWORD(0)
    if not k32.ReadConsoleOutputCharacterW(h, buf, n, COORD(0, 0), ctypes.byref(got)):
        return None
    text = buf.value[:got.value] if got.value else ""
    rows = [text[i:i + w].rstrip() for i in range(0, len(text), w)]
    return "\n".join(rows).rstrip()


def run(cmdline, on_text, stop=None, timeout=1800, interval=0.3):
    """Avvia cmdline in una console nascosta; on_text(testo) riceve lo schermo mentre gira.
    Ritorna (codice di uscita, testo finale). Solleva Failed se la console non e' utilizzabile."""
    si = STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    si.dwFlags = STARTF_USESHOWWINDOW | STARTF_USECOUNTCHARS
    si.wShowWindow = SW_HIDE
    si.dwXCountChars, si.dwYCountChars = WIDTH, HEIGHT
    pi = PROCESS_INFORMATION()
    buf = ctypes.create_unicode_buffer(cmdline)
    if not k32.CreateProcessW(None, buf, None, None, False, CREATE_NEW_CONSOLE | CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT,
                              None, None, ctypes.byref(si), ctypes.byref(pi)):
        raise Failed("CreateProcess: errore %d" % ctypes.get_last_error())
    attached = False
    hout = None
    try:
        # ci si aggancia alla sua console PRIMA che parta: cosi' quando finisce lo schermo resta leggibile
        if not k32.AttachConsole(pi.dwProcessId):
            k32.TerminateProcess(pi.hProcess, 1)
            raise Failed("AttachConsole: errore %d" % ctypes.get_last_error())
        attached = True
        hout = k32.CreateFileW("CONOUT$", 0xC0000000, 3, None, 3, 0, None)  # lettura/scrittura, condiviso, esistente
        if not hout or hout == INVALID:
            k32.TerminateProcess(pi.hProcess, 1)
            raise Failed("CONOUT$: errore %d" % ctypes.get_last_error())
        k32.ResumeThread(pi.hThread)
        end = time.time() + timeout
        last = None
        killed = None
        while True:
            done = k32.WaitForSingleObject(pi.hProcess, int(interval * 1000)) == 0
            text = _screen(hout)
            if text is not None and text != last:
                last = text
                on_text(text)
            if done:
                break
            if (stop is not None and stop.is_set()) or time.time() > end:
                killed = "Interrotto." if stop is not None and stop.is_set() else "Tempo scaduto."
                _kill_tree(pi.dwProcessId)
                k32.WaitForSingleObject(pi.hProcess, 5000)
                break
        code = W.DWORD(0)
        k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
        text = _screen(hout)
        if text is None:
            text = last or ""
        if killed:
            text = (text + "\n" + killed).strip()
        return (code.value if not killed else -1), text
    finally:
        if hout and hout != INVALID:
            k32.CloseHandle(hout)
        if attached:
            k32.FreeConsole()
        k32.CloseHandle(pi.hThread)
        k32.CloseHandle(pi.hProcess)


def _kill_tree(pid):
    try:
        import psutil
        pr = psutil.Process(pid)
        for c in pr.children(recursive=True):
            c.kill()
        pr.kill()
    except Exception:
        pass
