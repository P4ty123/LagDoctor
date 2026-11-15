"""Fix PC: comandi veri di Windows per sistemare i problemi piu' comuni, divisi per categoria.

Ogni fix e' una lista di passi. Ogni passo e' un comando cmd o PowerShell (mostrato all'utente cosi' come viene
eseguito) oppure un'azione interna di LagDoctor (es. riaprire Esplora risorse come utente normale).
L'uscita dei comandi viene letta mentre girano e mostrata nell'interfaccia.
"""
import base64
import codecs
import os
import queue
import re
import subprocess
import threading
import time

from . import conrun, paths

CREATE_NO_WINDOW = 0x08000000
USB_SUSPEND = "2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226"
APPX_REG = ("ForEach-Object { try { Add-AppxPackage -DisableDevelopmentMode -Register \"$($_.InstallLocation)\\AppXManifest.xml\" "
            "-ErrorAction Stop; 'OK: ' + $_.Name } catch { 'Saltata: ' + $_.Name } }")


def cmd(c, soft=False, enc=None, timeout=1800, always=False):
    """always: gira anche se un passo prima e' fallito (serve a rimettere le cose a posto)."""
    return {"sh": "cmd", "c": c, "soft": soft, "enc": enc, "timeout": timeout, "always": always}


def ps(c, soft=False, timeout=1800, always=False):
    return {"sh": "ps", "c": c, "soft": soft, "timeout": timeout, "always": always}


def act(name, c, soft=False, always=False):
    """azione interna: c e' la descrizione mostrata."""
    return {"sh": "py", "fn": name, "c": c, "soft": soft, "always": always}


def fix(t, q, steps, d="pochi secondi", r=False, w=None, ro=False, best=False, ci=False, res=None, kw=""):
    return {"t": t, "q": q, "steps": steps, "d": d, "r": r, "w": w, "ro": ro, "best": best, "ci": ci, "res": res, "kw": kw}


EXPLORER_KILL = act("explorer_kill", "taskkill /f /im explorer.exe")
EXPLORER_START = act("explorer_start", "start explorer.exe", always=True)

CATS = [
    ("rete", "Rete e Internet", [
        fix("Svuota la cache DNS", "Alcuni siti non si aprono o si aprono quelli vecchi dopo un cambio di DNS.",
            [cmd("ipconfig /flushdns")], ci=True, kw="internet siti dns"),
        fix("Rinnova l'indirizzo IP", "\"Nessun accesso a Internet\", indirizzo 169.254.x.x o rete che non prende l'IP dal router.",
            [cmd("ipconfig /release", soft=True), cmd("ipconfig /renew")], d="10-30 secondi", res="ip",
            kw="internet ip router wifi cavo"),
        fix("Ripristina Winsock", "Internet non va in nessun programma dopo una VPN, un antivirus o un programma di rete disinstallato male.",
            [cmd("netsh winsock reset")], r=True, kw="internet vpn"),
        fix("Ripristina TCP/IP", "Connessione instabile o che non si collega anche con il cavo, dopo aver provato Winsock.",
            [cmd("netsh int ip reset", soft=True), cmd("netsh int ipv6 reset", soft=True)], r=True, kw="internet connessione"),
        fix("Riavvia le schede di rete", "Wi-Fi o cavo bloccati senza dover riavviare il PC.",
            [ps("Get-NetAdapter -Physical | Where-Object Status -ne 'Disabled' | Restart-NetAdapter -Confirm:$false; "
                "Start-Sleep 3; Get-NetAdapter -Physical | Format-Table Name, Status, LinkSpeed -AutoSize")],
            d="10 secondi", kw="wifi cavo ethernet internet"),
        fix("Svuota cache ARP e NetBIOS", "Dispositivi della rete di casa (stampanti, NAS, altri PC) non raggiungibili.",
            [cmd("arp -d *", soft=True), cmd("nbtstat -R", soft=True), cmd("nbtstat -RR", soft=True)], ci=True,
            kw="rete locale nas stampante"),
        fix("DNS automatici", "Hai messo DNS a mano e ora qualcosa non va: torna ai DNS del router.",
            [ps("Get-NetAdapter | Set-DnsClientServerAddress -ResetServerAddresses; ipconfig /flushdns")], kw="dns internet"),
        fix("Togli il proxy", "Browser o Store dicono \"impossibile connettersi al proxy\".",
            [cmd("netsh winhttp reset proxy"),
             cmd("reg add \"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings\" /v ProxyEnable /t REG_DWORD /d 0 /f")],
            kw="proxy browser internet store"),
        fix("Ripristina il firewall di Windows", "Programmi o giochi online bloccati da regole del firewall sbagliate.",
            [cmd("netsh advfirewall reset")],
            w="Cancella anche le regole aggiunte dai programmi: alcuni giochi chiederanno di nuovo il permesso.",
            kw="firewall giochi online bloccato"),
        fix("Reimposta completamente la rete", "Ultima spiaggia quando nient'altro funziona (come Impostazioni > Rete > Reimposta rete).",
            [cmd("netcfg -d")], r=True, d="1 minuto",
            w="Reinstalla tutte le schede di rete e cancella VPN e schede virtuali: le password Wi-Fi restano.",
            kw="internet reset rete wifi"),
        fix("Prova la connessione", "Capire se il problema e' la rete, il DNS o il sito.",
            [cmd("ping -n 4 1.1.1.1", soft=True), cmd("nslookup www.google.com", soft=True)], ro=True, d="10 secondi",
            ci=True, kw="internet ping lag"),
        fix("Rapporto Wi-Fi", "Wi-Fi che si disconnette: crea un rapporto con tutte le disconnessioni degli ultimi 3 giorni e lo apre.",
            [cmd("netsh wlan show wlanreport"),
             act("open_wlanreport", "start %ProgramData%\\Microsoft\\Windows\\WlanReport\\wlan-report-latest.html")],
            ro=True, d="10 secondi", kw="wifi disconnette"),
    ]),
    ("bt", "Bluetooth", [
        fix("Riavvia i servizi Bluetooth", "Il Bluetooth non trova dispositivi o l'interruttore e' sparito.",
            [ps("Restart-Service bthserv -Force"),
             ps("Get-Service BluetoothUserService_* | Restart-Service -Force", soft=True),
             ps("Get-Service BTAGService -ErrorAction SilentlyContinue | Restart-Service -Force", soft=True)],
            d="10 secondi", kw="bluetooth cuffie controller"),
        fix("Riavvia la scheda Bluetooth", "Cuffie, controller o mouse non si collegano piu' finche' non riavvii il PC.",
            [ps("Get-PnpDevice -Class Bluetooth -Status OK | Where-Object InstanceId -match '^(USB|PCI)' | "
                "ForEach-Object { $_.FriendlyName; pnputil /restart-device \"$($_.InstanceId)\" }")],
            d="15 secondi", kw="bluetooth cuffie controller mouse"),
        fix("Niente risparmio energetico sulle USB", "Cuffie, mouse o controller Bluetooth che si scollegano da soli (la scheda Bluetooth e' quasi sempre su USB).",
            [cmd("powercfg /setacvalueindex SCHEME_CURRENT " + USB_SUSPEND + " 0"),
             cmd("powercfg /setdcvalueindex SCHEME_CURRENT " + USB_SUSPEND + " 0"),
             cmd("powercfg /setactive SCHEME_CURRENT")], kw="bluetooth usb scollega"),
        fix("Cerca di nuovo i dispositivi", "Scheda Bluetooth sparita da Gestione dispositivi.",
            [cmd("pnputil /scan-devices")], kw="bluetooth sparito"),
    ]),
    ("dischi", "Dischi", [
        fix("Controllo veloce del disco", "Errori di lettura, file che non si aprono: controlla il disco C senza riavviare.",
            [cmd("chkdsk C: /scan", soft=True)], ro=True, res="chk_scan", d="1-5 minuti", kw="disco errori chkdsk"),
        fix("Ripara il disco al riavvio", "Il controllo veloce ha trovato errori: li ripara al prossimo avvio.",
            [cmd("echo Y | chkdsk C: /f /r", soft=True)], r=True, res="chk_fr", d="10-60 minuti",
            w="Al riavvio il controllo puo' durare da 10 minuti a un'ora: non spegnere il PC.", kw="disco errori chkdsk"),
        fix("Ripara gli errori del volume", "Ripara subito gli errori trovati dal controllo veloce, senza il controllo lungo.",
            [ps("Repair-Volume -DriveLetter C -SpotFix")], d="1 minuto", kw="disco errori"),
        fix("Ottimizza tutti i dischi", "SSD piu' lento del solito o disco pieno di frammenti: TRIM sugli SSD, deframmentazione sugli HDD.",
            [cmd("defrag /C /O /U")], d="1-20 minuti", kw="ssd hdd lento deframmenta trim"),
        fix("Attiva il TRIM", "SSD che rallenta col tempo: il TRIM deve essere attivo.",
            [cmd("fsutil behavior set DisableDeleteNotify 0")], ci=True, kw="ssd trim lento"),
        fix("Salute dei dischi", "Mostra stato, temperatura, usura ed errori di ogni disco.",
            [ps("Get-PhysicalDisk | Sort-Object DeviceId | Format-Table FriendlyName, MediaType, @{n='GB';e={[math]::Round($_.Size/1GB)}}, HealthStatus -AutoSize"),
             ps("Get-PhysicalDisk | Sort-Object DeviceId | ForEach-Object { $r = $_ | Get-StorageReliabilityCounter; "
                "[pscustomobject]@{Disco=$_.FriendlyName; Temperatura=$r.Temperature; 'Usura %'=$r.Wear; "
                "'Errori lettura'=$r.ReadErrorsUncorrected; 'Ore accensione'=$r.PowerOnHours} } | Format-Table -AutoSize", soft=True)],
            ro=True, ci=True, kw="disco ssd salute temperatura usura smart"),
    ]),
    ("sys", "File di Windows", [
        fix("Riparazione completa di Windows", "Schermate blu, errori strani, programmi di sistema che non si aprono. Fa tutto in ordine: DISM e poi SFC.",
            [cmd("DISM /Online /Cleanup-Image /RestoreHealth"), cmd("sfc /scannow", enc="utf-16-le", soft=True)], d="15-30 minuti", res="full",
            best=True, kw="schermata blu errori dism sfc riparare corrotto"),
        fix("Controllo rapido dell'immagine (DISM)", "Verifica se Windows risulta gia' segnato come danneggiato.",
            [cmd("DISM /Online /Cleanup-Image /CheckHealth", soft=True)], ro=True, ci=True, res="dism_check", kw="dism corrotto"),
        fix("Controllo approfondito dell'immagine (DISM)", "Cerca danni nei file di Windows senza riparare.",
            [cmd("DISM /Online /Cleanup-Image /ScanHealth", soft=True)], ro=True, res="dism_check", d="5-10 minuti", kw="dism corrotto"),
        fix("Ripara l'immagine di Windows (DISM)", "Scarica da Windows Update i file di sistema danneggiati e li sostituisce.",
            [cmd("DISM /Online /Cleanup-Image /RestoreHealth", soft=True)], d="10-20 minuti", res="dism_restore", kw="dism riparare"),
        fix("Controllo file di sistema (SFC)", "Ripara i file di sistema usando la copia locale.",
            [cmd("sfc /scannow", enc="utf-16-le", soft=True)], d="5-15 minuti", res="sfc", kw="sfc riparare"),
    ]),
    ("wu", "Windows Update", [
        fix("Ripristina Windows Update", "Aggiornamenti bloccati, errori 0x800..., download fermo allo 0%.",
            [cmd("net stop wuauserv", soft=True), cmd("net stop cryptSvc", soft=True), cmd("net stop bits", soft=True),
             cmd("net stop msiserver", soft=True),
             cmd("ren %windir%\\SoftwareDistribution SoftwareDistribution.old-{ts}"),
             cmd("ren %windir%\\System32\\catroot2 catroot2.old-{ts}", soft=True),
             cmd("net start wuauserv", soft=True, always=True), cmd("net start cryptSvc", soft=True, always=True), cmd("net start bits", soft=True, always=True),
             cmd("net start msiserver", soft=True, always=True)],
            d="1 minuto", best=True, kw="aggiornamenti bloccati errore update"),
        fix("Svuota i download degli aggiornamenti", "Un aggiornamento fallisce sempre allo stesso punto.",
            [cmd("net stop wuauserv", soft=True), cmd("net stop bits", soft=True),
             cmd("del /f /s /q %windir%\\SoftwareDistribution\\Download\\*", soft=True),
             cmd("net start wuauserv", soft=True, always=True), cmd("net start bits", soft=True, always=True)], d="30 secondi", kw="aggiornamenti update"),
        fix("Riavvia i servizi di aggiornamento", "Windows Update resta su \"Ricerca aggiornamenti\" all'infinito.",
            [ps("Restart-Service wuauserv, bits -Force"), ps("Restart-Service UsoSvc -Force", soft=True)],
            d="10 secondi", kw="aggiornamenti update bloccato"),
        fix("Cerca aggiornamenti adesso", "Avvia subito la ricerca di aggiornamenti.",
            [cmd("UsoClient StartInteractiveScan")], kw="aggiornamenti update"),
    ]),
    ("audio", "Audio", [
        fix("Riavvia i servizi audio", "Nessun suono, icona del volume con la X, audio che gracchia.",
            [ps("Restart-Service AudioEndpointBuilder -Force"), ps("Start-Service Audiosrv")], d="10 secondi",
            kw="audio suono volume cuffie casse"),
        fix("Riavvia le schede audio", "Cuffie o casse non rilevate, audio sparito dopo lo standby.",
            [ps("Get-PnpDevice -Class MEDIA -Status OK | ForEach-Object { $_.FriendlyName; pnputil /restart-device \"$($_.InstanceId)\" }")],
            d="15 secondi", kw="audio suono cuffie casse"),
    ]),
    ("ui", "Desktop e menu Start", [
        fix("Riavvia Esplora risorse", "Barra delle applicazioni bloccata, desktop che non risponde.",
            [EXPLORER_KILL, EXPLORER_START], kw="barra applicazioni desktop explorer bloccato"),
        fix("Ricostruisci la cache delle icone", "Icone bianche, sbagliate o che non si aggiornano.",
            [EXPLORER_KILL,
             cmd("del /a /f /q \"%localappdata%\\IconCache.db\" \"%localappdata%\\Microsoft\\Windows\\Explorer\\iconcache*\"", soft=True),
             EXPLORER_START], kw="icone bianche"),
        fix("Ricostruisci le miniature", "Anteprime di foto e video nere o sbagliate.",
            [EXPLORER_KILL, cmd("del /a /f /q \"%localappdata%\\Microsoft\\Windows\\Explorer\\thumbcache_*.db\"", soft=True),
             EXPLORER_START], kw="anteprime foto miniature"),
        fix("Ripara menu Start e ricerca", "Il menu Start non si apre o la ricerca non scrive.",
            [ps("Get-AppxPackage -AllUsers Microsoft.Windows.StartMenuExperienceHost, MicrosoftWindows.Client.CBS, Microsoft.Windows.ShellExperienceHost | " + APPX_REG),
             ps("Stop-Process -Name StartMenuExperienceHost, SearchHost -Force -ErrorAction SilentlyContinue", soft=True)],
            d="30 secondi", kw="menu start ricerca"),
        fix("Ricostruisci l'indice di ricerca", "La ricerca non trova file o programmi che ci sono.",
            [cmd("reg add \"HKLM\\SOFTWARE\\Microsoft\\Windows Search\" /v SetupCompletedSuccessfully /t REG_DWORD /d 0 /f"),
             ps("Restart-Service WSearch -Force")], d="pochi secondi (l'indice si ricrea in background)", kw="ricerca file"),
        fix("Ricostruisci la cache dei caratteri", "Scritte con caratteri strani o quadratini.",
            [cmd("net stop FontCache", soft=True),
             cmd("del /f /q %windir%\\ServiceProfiles\\LocalService\\AppData\\Local\\FontCache\\*", soft=True),
             cmd("net start FontCache", soft=True, always=True)], ci=True, kw="caratteri font scritte"),
    ]),
    ("app", "Store e app", [
        fix("Svuota la cache dello Store", "Microsoft Store che non apre, download bloccati.",
            [cmd("wsreset.exe", timeout=180)], d="30 secondi", kw="store microsoft download"),
        fix("Reinstalla il Microsoft Store", "Lo Store si chiude subito o non c'e' piu'.",
            [ps("Get-AppxPackage -AllUsers Microsoft.WindowsStore | " + APPX_REG)], d="30 secondi", kw="store microsoft"),
        fix("Ripara le app di Windows", "Calcolatrice, Foto, Impostazioni o altre app che non si aprono.",
            [ps("Get-AppxPackage -AllUsers | Where-Object { $_.InstallLocation -and -not $_.IsFramework } | " + APPX_REG)],
            w="Ci mette qualche minuto e alcune app vengono saltate: e' normale.", d="3-10 minuti",
            kw="app calcolatrice foto impostazioni"),
        fix("Ripara Gaming Services (Xbox)", "Giochi del Game Pass che non si installano o non partono.",
            [ps("Get-AppxPackage -AllUsers *GamingServices* | Remove-AppxPackage -AllUsers", soft=True),
             ps("Start-Process 'ms-windows-store://pdp/?productid=9MWPM2CQNLHN'")],
            w="Disinstalla Gaming Services e apre lo Store per reinstallarlo (premi Installa): i giochi restano.",
            d="2 minuti", kw="xbox game pass giochi"),
    ]),
    ("dev", "Dispositivi e driver", [
        fix("Dispositivi con problemi", "Elenca i dispositivi con errori (il triangolo giallo di Gestione dispositivi).",
            [ps("$d = Get-PnpDevice -PresentOnly | Where-Object Status -eq 'Error'; "
                "if ($d) { $d | Format-Table Class, FriendlyName, Status -AutoSize } else { 'Nessun dispositivo con errori.' }")],
            ro=True, ci=True, kw="driver dispositivi errore triangolo"),
        fix("Cerca di nuovo l'hardware", "Un dispositivo collegato non viene visto.",
            [cmd("pnputil /scan-devices")], ci=True, kw="dispositivo usb non visto"),
        fix("Niente risparmio energetico sulle USB", "Mouse, tastiere, controller o chiavette USB che si scollegano da soli.",
            [cmd("powercfg /setacvalueindex SCHEME_CURRENT " + USB_SUSPEND + " 0"),
             cmd("powercfg /setdcvalueindex SCHEME_CURRENT " + USB_SUSPEND + " 0"),
             cmd("powercfg /setactive SCHEME_CURRENT")], kw="usb mouse tastiera controller scollega"),
        fix("Ripara WMI", "Gestione attivita' o altri programmi non leggono temperature, GPU o informazioni del PC.",
            [cmd("winmgmt /verifyrepository", soft=True), cmd("winmgmt /salvagerepository")], d="30 secondi",
            kw="wmi informazioni temperature"),
        fix("Ultimi spegnimenti improvvisi", "Il PC si riavvia o si spegne da solo: mostra quando e' successo e se c'e' stata una schermata blu.",
            [ps("$e = Get-WinEvent -FilterHashtable @{LogName='System'; Id=41,1001,6008} -MaxEvents 15 -ErrorAction SilentlyContinue; "
                "if ($e) { $e | Format-Table TimeCreated, Id, @{n='Messaggio';e={($_.Message -split \"`n\")[0]}} -AutoSize -Wrap } "
                "else { 'Nessuno spegnimento improvviso registrato.' }")],
            ro=True, ci=True, kw="riavvio spegne schermata blu crash"),
    ]),
    ("altro", "Avvio, ora e stampanti", [
        fix("Disattiva l'avvio rapido", "Problemi che spariscono solo con \"Riavvia\" e non con \"Arresta\", periferiche non viste all'accensione.",
            [cmd("reg add \"HKLM\\SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Power\" /v HiberbootEnabled /t REG_DWORD /d 0 /f")],
            kw="avvio rapido accensione"),
        fix("Test della memoria RAM", "Schermate blu casuali: apre il test della RAM di Windows (scegli \"Riavvia ora\").",
            [act("launch_mdsched", "mdsched.exe")], r=True, d="15-30 minuti al riavvio", kw="ram memoria schermata blu"),
        fix("Sincronizza l'orologio", "Ora sbagliata, errori dei certificati nei siti, launcher che non si collegano.",
            [cmd("net start w32time", soft=True), cmd("w32tm /resync /force")], kw="ora orologio data certificati"),
        fix("Sblocca la coda di stampa", "Stampa bloccata che non si cancella.",
            [cmd("net stop spooler", soft=True), cmd("del /f /q %windir%\\System32\\spool\\PRINTERS\\*", soft=True),
             cmd("net start spooler", always=True)], ci=True, kw="stampante stampa"),
        fix("Rapporto della batteria", "Portatile: capacita' reale della batteria e quanto si e' consumata.",
            [cmd("powercfg /batteryreport /output \"{reports}\\batteria.html\""), act("open_battery", "start batteria.html")],
            ro=True, kw="batteria portatile"),
    ]),
]


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


BY_ID = {}
for _cid, _cn, _fx in CATS:
    for _f in _fx:
        _f["id"] = _cid + "." + _slug(_f["t"])
        _f["cat"] = _cid
        BY_ID[_f["id"]] = _f


def _shown(c):
    return c.replace("{ts}", "<data e ora>").replace("{reports}", paths.REPORTS)


def catalog():
    return {"cats": [{"id": cid, "n": n, "fx": [{k: f[k] for k in ("id", "t", "q", "d", "r", "w", "ro", "best", "kw")}
                                                  | {"c": [_shown(s["c"]) for s in f["steps"]]} for f in fx]}
                     for cid, n, fx in CATS]}


# ======================================================================= esecuzione
def _expand(c):
    return c.replace("{ts}", time.strftime("%Y%m%d%H%M%S")).replace("{reports}", paths.REPORTS)


def _decoder(enc):
    if enc:
        return codecs.getincrementaldecoder(enc)(errors="replace")
    try:
        return codecs.getincrementaldecoder("oem" if os.name == "nt" else "utf-8")(errors="replace")
    except LookupError:
        return codecs.getincrementaldecoder("cp850")(errors="replace")


class Output:
    """testo dei comandi: \\r riscrive la riga corrente (barre di avanzamento di DISM, sfc, chkdsk)."""

    def __init__(self):
        self.lines = [""]
        self.pending_cr = False
        self.modes = []  # per ogni comando: letto dalla console o dalla pipe

    def feed(self, text):
        for ch in text.replace("\x00", ""):
            if self.pending_cr:
                self.pending_cr = False
                if ch != "\n":
                    self.lines[-1] = ""
            if ch == "\r":
                self.pending_cr = True
            elif ch == "\n":
                self.lines.append("")
            else:
                self.lines[-1] += ch
        if len(self.lines) > 1500:
            self.lines = self.lines[-1000:]

    def set_live(self, start, text):
        """sostituisce tutto da start in poi con lo schermo attuale della console."""
        self.lines = self.lines[:start] + text.split("\n") + [""]
        self.pending_cr = False

    def line(self, s):
        if self.lines[-1]:
            self.lines.append("")
        self.lines[-1] = s
        self.lines.append("")

    def text(self, n=400):
        out, blank = [], False
        for l in self.lines[-n:]:  # niente righe vuote di fila
            l = l.rstrip()
            if not l:
                if blank or not out:
                    continue
                blank = True
            else:
                blank = False
            out.append(l)
        return "\n".join(out).strip("\n")


def _ps_script(c, width):
    return ("$ProgressPreference='SilentlyContinue'; $ErrorActionPreference='Continue'; $global:LASTEXITCODE=0; $n=0; "
            "& { " + c + " } *>&1 | ForEach-Object { if ($_ -is [System.Management.Automation.ErrorRecord]) { $n++; "
            "'ERRORE: ' + $_.Exception.Message } else { $_ } } | Out-String -Width %d -Stream; "
            "if ($n) { exit 1 } elseif ($LASTEXITCODE) { exit $LASTEXITCODE }" % width)


def _cmdline(step, width):
    c = _expand(step["c"])
    if step["sh"] == "ps":
        script = _ps_script(c, width)
        if width != conrun.WIDTH - 5:  # pipe: l'uscita di PowerShell arriva in UTF-8
            script = "[Console]::OutputEncoding=[Text.Encoding]::UTF8; " + script
        enc = base64.b64encode(script.encode("utf-16-le")).decode()
        return "powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -EncodedCommand " + enc
    return c if width == conrun.WIDTH - 5 else "cmd /d /c " + c  # in console il comando gira gia' dentro cmd


def _popen(step):
    args = _cmdline(step, 160)
    dec = _decoder("utf-8") if step["sh"] == "ps" else _decoder(step.get("enc"))
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0)
    return p, dec


def _action(name):
    if name == "explorer_kill":
        subprocess.run("taskkill /f /im explorer.exe", shell=True, capture_output=True, creationflags=CREATE_NO_WINDOW)
        time.sleep(1.0)
        return 0, "Esplora risorse chiuso."
    if name == "explorer_start":
        import psutil
        from .gamemode import launch_as_user
        if any((p.info["name"] or "").lower() == "explorer.exe" for p in psutil.process_iter(["name"])):
            return 0, "Esplora risorse e' gia' aperto."
        exe = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "explorer.exe")
        ok = launch_as_user(exe, fast=True) or launch_as_user(exe)
        if not ok:
            subprocess.Popen([exe], creationflags=CREATE_NO_WINDOW)
        return 0, "Esplora risorse riaperto."
    if name == "open_wlanreport":
        f = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), r"Microsoft\Windows\WlanReport\wlan-report-latest.html")
        if not os.path.exists(f):
            return 1, "Rapporto non trovato (il PC ha il Wi-Fi?)."
        os.startfile(f)
        return 0, "Rapporto aperto nel browser: " + f
    if name == "open_battery":
        f = os.path.join(paths.REPORTS, "batteria.html")
        if not os.path.exists(f):
            return 1, "Rapporto non creato: questo PC non ha una batteria."
        os.startfile(f)
        return 0, "Rapporto aperto nel browser: " + f
    if name == "launch_mdsched":
        subprocess.Popen(["mdsched.exe"])
        return 0, "Si e' aperta la finestra del test della RAM: scegli \"Riavvia ora e verifica la presenza di problemi\"."
    raise ValueError("azione sconosciuta: %s" % name)


def _has(text, *frags):
    t = text.lower()
    return any(x in t for x in frags)


def _code(c):
    return "0x%08X" % (c & 0xFFFFFFFF) if isinstance(c, int) and (c < 0 or c > 0xFFFF) else str(c)


DISM_ERR = {0x800F081F: "DISM non trova i file per riparare: controlla la connessione a Internet e che Windows Update funzioni.",
            0x800F0906: "DISM non riesce a scaricare i file per riparare: controlla la connessione a Internet.",
            0x800F0907: "DISM non riesce a scaricare i file per riparare: un criterio di gruppo lo impedisce.",
            0x800F0954: "DISM non riesce a usare Windows Update (WSUS o criteri aziendali).",
            0x800F0950: "DISM non trova i file per riparare.",
            740: "serve LagDoctor avviato come amministratore.",
            5: "accesso negato: serve LagDoctor avviato come amministratore."}


def _sfc_cbs(since):
    """esito di SFC letto dal suo registro (CBS.log, in inglese su ogni Windows): serve se il messaggio non si legge."""
    f = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), r"Logs\CBS\CBS.log")
    try:
        with open(f, "rb") as fh:
            fh.seek(0, 2)
            fh.seek(max(0, fh.tell() - 8 * 1024 * 1024))
            data = fh.read().decode("utf-8", "replace")
    except OSError:
        return None
    t0 = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(since - 5))
    sr = [l for l in data.splitlines() if "[SR]" in l and l[:19] >= t0]
    if not sr:
        return None
    if any("Cannot repair member file" in l for l in sr):
        return False, ("SFC ha trovato file danneggiati ma non e' riuscito a ripararli tutti: esegui \"Ripara l'immagine "
                       "di Windows (DISM)\", riavvia e poi esegui di nuovo SFC.")
    if any("Repaired file" in l or "Repairing corrupted file" in l for l in sr):
        return True, "SFC ha trovato file danneggiati e li ha riparati tutti. Riavvia il PC per completare."
    if any("Verify complete" in l for l in sr):
        if any("Cannot verify component files" in l or "corrupt" in l.lower() for l in sr):
            return False, "SFC ha trovato file danneggiati: esegui \"Riparazione completa di Windows\"."
        return True, "SFC non ha trovato nessun file danneggiato: i file di sistema di Windows sono a posto."
    return None


def _sfc(out, since=None):
    if _has(out, "non ha rilevato violazioni", "did not find any integrity violations"):
        return True, "SFC non ha trovato nessun file danneggiato: i file di sistema di Windows sono a posto."
    if _has(out, "li ha ripristinati", "successfully repaired"):
        return True, "SFC ha trovato file danneggiati e li ha riparati tutti. Riavvia il PC per completare."
    if _has(out, "correggerne alcuni", "unable to fix some"):
        return False, ("SFC ha trovato file danneggiati ma non e' riuscito a ripararli tutti: esegui \"Ripara l'immagine "
                       "di Windows (DISM)\", riavvia e poi esegui di nuovo SFC.")
    if _has(out, "riparazione del sistema in sospeso", "repair pending"):
        return False, "C'e' una riparazione di Windows in sospeso: riavvia il PC e poi esegui di nuovo SFC."
    if _has(out, "eseguire l'operazione richiesta", "could not perform the requested operation"):
        return False, "SFC non e' riuscito a fare il controllo: riavvia il PC e riprova (se succede ancora, prova in modalita' provvisoria)."
    r = _sfc_cbs(since) if since else None
    return r if r else (None, "SFC ha finito, ma non riesco a leggere il suo esito: guarda il messaggio qui sopra.")


def _dism(out, code, restore):
    if code not in (0, 3010):
        msg = DISM_ERR.get(code & 0xFFFFFFFF if isinstance(code, int) else code)
        return False, "DISM non e' riuscito (errore %s)%s" % (_code(code), ": " + msg if msg else ": leggi il messaggio qui sopra.")
    if restore:
        return True, "DISM ha completato la riparazione: l'immagine di Windows e' a posto."
    if _has(out, "not repairable", "non e' ripristinabile", "non è ripristinabile", "non riparabile"):
        return False, "DISM dice che l'immagine di Windows e' danneggiata e NON si puo' riparare: serve reinstallare Windows mantenendo i file."
    if _has(out, "repairable", "ripristinabile", "riparabile"):
        return False, "DISM ha trovato file di Windows danneggiati che si possono riparare: esegui \"Ripara l'immagine di Windows (DISM)\"."
    return True, "DISM non ha trovato nessun danneggiamento: l'immagine di Windows e' a posto."


def _summary(f, ok, failed, out, codes=(), since=None):
    """frase finale mostrata sotto il fix. Ritorna (ok, testo): alcuni comandi finiscono senza errori ma trovano problemi."""
    kind = f.get("res")
    last = codes[-1] if codes else None
    if kind == "sfc":
        good, msg = _sfc(out, since)
        return (ok if good is None else good), msg
    if kind == "full":
        if len(codes) < 2:  # DISM fallito: SFC non e' partito
            return False, _dism(out, codes[0] if codes else -1, True)[1] + " SFC non e' stato eseguito."
        good, msg = _sfc(out, since)
        return (ok if good is None else good), "DISM ha completato la riparazione. " + msg
    if kind in ("dism_check", "dism_restore"):
        return _dism(out, last if last is not None else -1, kind == "dism_restore")
    if kind == "chk_scan":
        if last == 0 or _has(out, "found no problems", "non ha rilevato problemi"):
            return True, "Il disco C non ha errori."
        return False, ("Il controllo ha trovato errori sul disco C: esegui \"Ripara gli errori del volume\" "
                       "o \"Ripara il disco al riavvio\".")
    if kind == "chk_fr":
        if _has(out, "next time", "successivo riavvio", "prossimo riavvio"):
            return True, "Riparazione programmata: al prossimo riavvio Windows controlla e ripara il disco (puo' durare fino a un'ora)."
        return False, "Non sono riuscito a programmare la riparazione del disco: leggi il messaggio qui sopra."
    if not ok:
        c = failed[1]
        hint = DISM_ERR.get(c) if c in (5, 740) else None
        return False, "Il comando \"%s\" non e' riuscito (codice %s): %s" % (failed[0], _code(c), hint or "leggi il messaggio qui sopra.")
    if kind == "ip":
        ips = [ip for ip in re.findall(r"IPv4[^:\n]*:\s*([\d.]+)", out) if not ip.startswith("169.254.")]
        if ips:
            return True, "Nuovo indirizzo %s ricevuto dal router." % ips[-1]
        return False, "Il router non ha dato un indirizzo valido: controlla cavo o Wi-Fi."
    if f["ro"]:
        return True, "Controllo completato, il risultato e' qui sopra."
    if f["r"]:
        return True, "Fatto. Riavvia il PC per completare."
    return True, "Fatto."


def _run_step(step, out, push, stop):
    if conrun.available():
        start = len(out.lines) - 1 if out.lines[-1] == "" else len(out.lines)

        def screen(text):
            out.set_live(start, text)
            push()
        try:
            out.modes.append("console")
            code, text = conrun.run(_cmdline(step, conrun.WIDTH - 5), screen, stop=stop, timeout=step.get("timeout", 1800))
            out.set_live(start, text)
            return code
        except conrun.Failed as e:
            out.modes[-1] = "pipe (%s)" % e  # console non utilizzabile: uso la pipe
            return _run_pipe(step, out, push, stop)
    out.modes.append("pipe")
    return _run_pipe(step, out, push, stop)


def _run_pipe(step, out, push, stop):
    try:
        p, dec = _popen(step)
    except OSError as e:
        out.line("Non riesco ad avviare il comando: %s" % e)
        return -1
    q = queue.Queue()

    def reader():
        fd = p.stdout.fileno()
        while True:
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                chunk = b""
            q.put(chunk)
            if not chunk:
                return
    threading.Thread(target=reader, daemon=True).start()
    end = time.time() + step.get("timeout", 1800)
    last = 0
    while True:
        try:
            chunk = q.get(timeout=0.25)
        except queue.Empty:
            chunk = None
        if chunk == b"":
            break
        if chunk:
            out.feed(dec.decode(chunk))
            if time.time() - last > 0.25:
                push()
                last = time.time()
        halt = "Interrotto." if stop is not None and stop.is_set() else "Tempo scaduto." if time.time() > end else None
        if halt:
            _kill_tree(p.pid)
            out.line(halt)
            break
    out.feed(dec.decode(b"", final=True))
    try:
        return p.wait(timeout=10)
    except subprocess.TimeoutExpired:
        return -1


def _kill_tree(pid):
    try:
        import psutil
        pr = psutil.Process(pid)
        for c in pr.children(recursive=True):
            c.kill()
        pr.kill()
    except Exception:
        pass


def run(fid, job=None, live=None):
    """Esegue un fix. live(text) riceve l'uscita mentre i comandi girano. Ritorna un dizionario con l'esito."""
    f = BY_ID[fid]
    out = Output()
    stop = job.stop if job is not None else None
    failed = None
    codes = []
    t0 = time.time()

    def push():
        if live:
            live(out.text())
    for step in f["steps"]:
        if failed is not None and not step.get("always"):
            continue  # dopo un errore girano solo i passi che rimettono le cose a posto (es. riavvio dei servizi)
        out.line("> " + _expand(step["c"]))
        push()
        if step["sh"] == "py":
            try:
                code, msg = _action(step["fn"])
            except Exception as e:
                code, msg = 1, "Errore: %s" % e
            out.line(msg)
        else:
            code = _run_step(step, out, push, stop)
        push()
        codes.append(code)
        if code not in (0, 3010) and not step.get("soft") and failed is None:
            failed = (step["c"], code)
        if stop is not None and stop.is_set() and failed is None:
            failed = (step["c"], "interrotto")
    text = out.text(1000)
    ok = failed is None
    ok, res = _summary(f, ok, failed, text, codes, t0)
    return {"id": fid, "ok": ok, "out": text, "res": res, "reboot": bool(f["r"] and ok), "modes": out.modes,
            "secs": round(time.time() - t0, 1)}
