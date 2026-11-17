"""Nome di ogni voce come "cosa" (non come azione) e verso dell'interruttore.

L'interruttore di ogni voce dice se quella cosa e' ATTIVA sul PC:
    pol = +1  applicare la voce ACCENDE la cosa   (es. "TRIM degli SSD": applicata = TRIM acceso)
    pol = -1  applicare la voce SPEGNE la cosa    (es. "Core parking": applicata = core parking spento)
tech = nome tecnico o dettagli (prima erano tra parentesi nel nome): si vedono nella finestra dei dettagli.
short = frase breve sotto il nome, che descrive la cosa (per le voci con pol -1; le altre usano tweak_short).
"""

N = {}


def n(tid, label, pol, tech=None, short=None):
    N[tid] = {"label": label, "pol": pol, "tech": tech, "short": short}


# ------------------------------------------------------------------ CORREZIONI
n("fix_hpet", "HPET forzato", -1, "useplatformclock", "Timer vecchio forzato da un 'ottimizzatore': peggiora FPS e stutter.")
n("fix_pagefile", "File di paging", 1)
n("fix_autotuning", "TCP Auto-Tuning", 1)
n("fix_largecache", "Cache di sistema grande", -1, "LargeSystemCache", "Modalita' server: toglie RAM ai programmi.")
n("fix_clearpagefile", "Svuotamento del file di paging allo spegnimento", -1, "ClearPageFileAtShutdown",
  "Rende lo spegnimento molto lento e non aiuta i giochi.")
n("fix_powersaver", "Piano 'Risparmio energia'", -1, None, "Limita CPU e GPU: su un PC da gioco toglie prestazioni.")
n("fix_hags_off_40", "HAGS", 1, "Pianificazione GPU con accelerazione hardware")
for _id, _l, _t in [("wuauserv", "Windows Update", "wuauserv"), ("bits", "BITS", "Servizio trasferimento intelligente in background"),
                    ("audiosrv", "Audio di Windows", "Audiosrv"), ("audioendpointbuilder", "Generatore endpoint audio", "AudioEndpointBuilder"),
                    ("gamingservices", "Gaming Services", "Xbox / Game Pass"), ("xblauthmanager", "Xbox Live Auth Manager", "XblAuthManager"),
                    ("dnscache", "Client DNS", "Dnscache"), ("mpssvc", "Windows Firewall", "mpssvc"),
                    ("schedule", "Utilita' di pianificazione", "Schedule"), ("themes", "Temi", "Themes")]:
    n("fix_svc_" + _id, "Servizio " + _l, 1, "nome del servizio: " + _t)
n("fix_trim", "TRIM degli SSD", 1)

# ------------------------------------------------------------------ DRIVER NVIDIA
n("nvfix_vsync_half", "V-Sync a mezza frequenza", -1, None, "Il driver forza il V-Sync a 1/2, 1/3 o 1/4 della frequenza del monitor.")
n("nvfix_fpscap_low", "Limite FPS globale basso", -1, None, "Il driver limita tutti i giochi molto sotto la frequenza del monitor.")
n("nvfix_minpower", "Gestione energia 'consumo minimo'", -1, "Prediligi consumo minimo", "Tiene la scheda video a frequenze basse anche nei giochi.")
n("nvfix_shadercache", "Cache shader", 1)
n("nvfix_vrr_blocked", "Blocco di G-SYNC", -1, "profilo globale", "G-SYNC bloccato per tutte le app: non funziona in nessun gioco.")
n("nvfix_fxaa", "FXAA forzato", -1, None, "Il driver forza l'FXAA su tutti i giochi: sfoca testi e interfaccia.")
n("nvfix_thread", "Ottimizzazione thread", 1)
n("nvfix_prerender", "Troppi frame pre-renderizzati", -1, None, "Il driver prepara troppi frame in anticipo: piu' input lag.")
n("nv_lowlat_on", "Modalita' bassa latenza", 1)
n("nv_shadercache_unlimited", "Cache shader illimitata", 1)
n("nv_refresh_highest", "Frequenza piu' alta disponibile", 1)
n("nv_power_max", "Prestazioni massime della scheda video", 1, "Gestione energia: prediligi prestazioni massime (globale)")
n("nv_gsync_windowed", "G-SYNC in finestra e senza bordi", 1)
n("nv_vsync_on", "V-Sync del driver", 1, "da usare insieme a G-SYNC")
n("nv_fps_cap", "Limite FPS 3 sotto la frequenza del monitor", 1)
n("nv_texture_perf", "Filtro texture veloce", 1, "Filtro texture - Qualita': Prestazioni elevate")

# ------------------------------------------------------------------ DRIVER AMD
n("amdfix_chill", "Radeon Chill", -1, None, "Fa variare gli FPS di continuo: causa micro-stutter.")
n("amdfix_esync", "Enhanced Sync", -1, None, "Con FreeSync e' una causa nota di stutter.")
n("amdfix_vsync_always", "V-Sync forzato sempre", -1, None, "Aggiunge input lag in tutti i giochi.")
n("amdfix_frtc_low", "Limite FPS globale basso", -1, None, "Adrenalin limita tutti i giochi molto sotto la frequenza del monitor.")
n("amdfix_mlaa", "Antialiasing morfologico forzato", -1, "MLAA", "Sfoca l'immagine e costa FPS.")
n("amd_antilag_on", "Radeon Anti-Lag", 1)
n("amd_boost_off", "Radeon Boost", -1, None, "Abbassa la risoluzione nei movimenti veloci per avere piu' FPS.")
n("amd_afmf_off", "AMD Fluid Motion Frames", -1, "AFMF", "Il driver genera frame intermedi: piu' FPS ma piu' latenza.")
n("amd_fps_cap", "Limite FPS 3 sotto la frequenza del monitor", 1, "FRTC")

# ------------------------------------------------------------------ GIOCO
n("game_mode", "Modalita' Gioco di Windows", 1)
n("windowed_opt", "Ottimizzazioni per giochi in finestra", 1)
n("hags", "HAGS", 1, "Pianificazione GPU con accelerazione hardware")
n("fso_off", "Ottimizzazioni schermo intero", -1, "FSO, globale", "Windows gestisce lo schermo intero dei giochi come una finestra senza bordi.")
n("mmcss_games", "Priorita' alta ai giochi MMCSS", 1)
n("pcie_aspm", "Risparmio energetico PCI Express", -1, "ASPM", "Scheda video e SSD vanno in risparmio sul bus: puo' causare micro-scatti.")
n("vrr_opt", "Frequenza variabile di Windows", 1, "VRR")

# ------------------------------------------------------------------ OVERLAYS
n("game_dvr", "Registrazione Xbox Game Bar", -1, "Game DVR", "Registra il gioco in sottofondo: causa nota di micro-scatti.")
n("mpo_off", "MPO", -1, "Multiplane Overlay", "Con alcuni driver causa sfarfallii e scatti nei giochi senza bordi.")
n("mpo_full", "MPO anche nel driver", -1, "Multiplane Overlay completo", "Da spegnere solo se la versione normale non basta.")
n("gamedvr_policy", "Game DVR di sistema", -1, "criterio per tutti gli utenti", "Permette all'app Xbox di riattivare la registrazione.")
n("gamebar_shortcut", "Game Bar con Win+G e tasto Xbox", -1, None, "Si apre per sbaglio in partita, soprattutto con i controller.")
n("ov_steam", "Steam", -1, None, "Il menu Maiusc+Tab dentro i giochi.")
n("ov_nvidia", "NVIDIA", -1, "NVIDIA App / GeForce Experience", "L'overlay Alt+Z con statistiche e Instant Replay.")
n("ov_amd", "AMD Software", -1, "Adrenalin", "L'overlay con metriche, registrazione e replay.")
n("ov_intel", "Intel", -1, "Intel Graphics Software / Arc Control", "L'overlay della scheda video Intel.")
n("ov_discord", "Discord", -1, None, "Chi sta parlando e le notifiche sopra il gioco.")
n("ov_rtss", "RivaTuner", -1, "RivaTuner Statistics Server, l'overlay di MSI Afterburner", "FPS e temperature sopra il gioco.")
n("ov_overwolf", "Overwolf", -1, "Outplayed, Porofessor e altre app", "App che si disegnano sopra i giochi.")
n("ov_ea", "App EA", -1, None, "Il menu Maiusc+F1 dei giochi EA.")
n("ov_ubisoft", "Ubisoft Connect", -1, None, "Il menu Maiusc+F2 dei giochi Ubisoft.")
n("ov_gog", "GOG Galaxy", -1, None, "Il menu Maiusc+Tab dei giochi GOG.")

# ------------------------------------------------------------------ CPU ED ENERGIA
n("plan_ultimate", "Piano 'Prestazioni eccellenti'", 1, "Ultimate Performance")
n("core_parking", "Core parking", -1, None, "Windows mette a riposo i core che non servono.")
n("power_throttling", "Power Throttling", -1, None, "Windows rallenta i programmi in background per risparmiare energia.")
n("usb_suspend", "Sospensione selettiva USB", -1, None, "Mette in risparmio mouse, tastiera e cuffie USB: puo' causare micro-blocchi.")
n("prio_sep", "Win32PrioritySeparation 26", 1, "valore esadecimale")
n("sys_resp", "SystemResponsiveness 10", 1)
n("dynamic_tick", "Dynamic tick", -1, None, "Il timer di sistema scatta solo quando serve, per risparmiare energia.")
n("prio_sep_2a", "Win32PrioritySeparation 2A", 1, "valore esadecimale")
n("boost_aggr", "Boost processore aggressivo", 1, "Modalita' boost processore: Aggressiva")
n("min_cpu_100", "Stato minimo processore al 100%", 1)
n("idle_off", "Idle della CPU", -1, "C-states", "La CPU va a riposo quando non lavora.")
n("timer_res", "Timer Resolution 0,5 ms", 1, "GlobalTimerResolutionRequests, automatico, parte con Windows")

# ------------------------------------------------------------------ MEMORIA E DISCO
n("mem_compress", "Compressione della memoria", -1, None, "Windows comprime la RAM: un po' di lavoro in piu' per la CPU.")
n("sysmain", "SysMain", -1, "Superfetch", "Windows precarica in RAM i programmi che usi spesso.")
n("wsearch", "Indicizzazione di Windows Search", -1, None, "Windows indicizza i file in background per la ricerca.")
n("hibernation", "Ibernazione e avvio rapido", -1, None, "Windows non riparte da zero a ogni accensione.")
n("defender_excl", "Esclusione dei giochi da Defender", 1)
n("paging_exec", "DisablePagingExecutive", 1)
n("prefetch_off", "Prefetcher", -1, None, "Windows prepara in anticipo i file dei programmi che usi spesso.")
n("svchost_split", "Meno processi svchost", 1, "SvcHostSplitThresholdInKB")
n("ntfs_lastaccess", "Data di ultimo accesso NTFS", -1, None, "Windows scrive sul disco l'ora di accesso a ogni file letto.")
n("ntfs_83", "Nomi file corti 8.3", -1, None, "Windows crea i nomi tipo PROGRA~1 per ogni file.")
n("storage_sense_off", "Sensore memoria", -1, None, "Pulizie automatiche del disco, anche mentre giochi.")
n("maintenance_off", "Manutenzione automatica", -1, None, "Scansioni e ottimizzazioni giornaliere di Windows.")

# ------------------------------------------------------------------ RETE
n("delivery_opt", "Condivisione aggiornamenti P2P", -1, "Ottimizzazione recapito", "Windows usa la tua connessione per inviare aggiornamenti ad altri PC.")
n("nic_power", "Risparmio energetico della scheda di rete", -1, None, "Puo' causare picchi di ping, soprattutto con il Wi-Fi.")
n("nagle", "Algoritmo di Nagle", -1, "TcpAckFrequency, TCPNoDelay, TcpDelAckTicks", "Windows raggruppa i piccoli pacchetti TCP e aspetta prima di confermarli.")
n("net_throttle", "Network Throttling", -1, "NetworkThrottlingIndex", "Limita i pacchetti di rete mentre riproduci audio o video.")
n("nic_intmod", "Interrupt Moderation", -1, None, "La scheda di rete raggruppa i pacchetti prima di avvisare la CPU.")
n("nic_eee", "Energy Efficient Ethernet", -1, None, "Il cavo di rete va in risparmio tra un pacchetto e l'altro.")
n("nic_flow", "Flow Control", -1, None, "La scheda di rete mette in pausa l'invio quando il router e' sotto carico.")
n("ipv4_pref", "Preferenza per IPv4", 1)
n("teredo_off", "Teredo", -1, "tunnel IPv6", "Tunnel IPv6 usato da alcuni giochi Game Pass per il multiplayer.")
n("nic_lso", "Large Send Offload", -1, None, "La scheda di rete divide da sola i pacchetti grandi.")

# ------------------------------------------------------------------ INTERFACCIA E INPUT
n("mouse_accel", "Accelerazione del mouse", -1, None, "Il puntatore va piu' lontano se muovi il mouse veloce: mira meno costante.")
n("bg_apps", "App dello Store in background", -1, None, "Le app dello Store restano attive in background.")
n("transparency", "Effetti di trasparenza", -1, None, "Trasparenze di menu e barre sul desktop.")
n("diagtrack", "Telemetria", -1, "servizio DiagTrack", "Invio di dati diagnostici a Microsoft in background.")
n("visual_fx", "Animazioni e ombre di Windows", -1, "Effetti visivi: testo smussato e anteprime restano",
  "Animazioni, ombre, dissolvenze e scorrimento fluido di Windows.")
n("menu_delay", "Ritardo dei menu", -1, "MenuShowDelay", "I menu di Windows aspettano un attimo prima di aprirsi.")
n("sticky_keys", "Scorciatoia Tasti permanenti", -1, None, "Premere Shift 5 volte apre una finestra che ti butta fuori dal gioco.")
n("keyboard_fast", "Ripetizione tastiera rapida", 1)
n("wait_kill_svc", "Spegnimento rapido", 1, "WaitToKillServiceTimeout = 2000")
n("startup_delay", "Ritardo dei programmi all'avvio", -1, None, "Windows aspetta qualche secondo prima di avviare i programmi.")
n("notifications_off", "Notifiche popup", -1, None, "Popup di Windows e delle app sopra il gioco.")
n("widgets_off", "Widget", -1, "notizie e meteo", "Il pannello Widget scarica notizie in background.")
n("edge_bg_off", "Edge in background", -1, None, "Edge si precarica all'avvio e resta in memoria.")
n("recall_off", "Recall", -1, "analisi AI degli screenshot", "Sui PC Copilot+ salva e analizza screenshot continui.")
n("telemetry_policy", "Raccolta dati e pubblicita'", -1, "criteri", "Cronologia attivita', ID pubblicitario e app suggerite.")
n("wersvc", "Segnalazione errori Windows", -1, None, "Dopo un crash Windows raccoglie e invia il rapporto.")
n("spooler", "Spooler di stampa", -1, None, "Il servizio di stampa: spegnilo solo se non hai una stampante.")
n("access_keys", "Scorciatoie Filtro tasti e Tasti di alternanza", -1, None, "Finestre di accessibilita' che si aprono durante il gioco.")
n("copilot_off", "Copilot", -1, None, "Copilot resta pronto in background.")
n("start_web_off", "Risultati web nel menu Start", -1, "Bing", "La ricerca del menu Start interroga anche Bing.")
n("wu_active_hours", "Ore attive di Windows Update", 1, "10:00 - 02:00")
n("usb_notify_off", "Notifiche USB", -1, None, "Popup quando un dispositivo USB ha un problema.")
n("metered_drivers", "App dei dispositivi automatiche", -1, None, "Windows installa da solo i programmi di mouse, tastiere e cuffie.")
n("mouse_pointer_6", "Velocita' puntatore neutra", 1, "6 su 11")

# ------------------------------------------------------------------ SICUREZZA (PERICOLOSE)
n("mitigations_off", "Protezioni Spectre e Meltdown", -1, None, "Proteggono da attacchi che leggono la memoria. Meglio tenerle accese.")
n("defender_rt_off", "Protezione in tempo reale di Defender", -1, None, "Defender controlla i file mentre vengono aperti. Meglio tenerla accesa.")
n("wu_auto_off", "Aggiornamenti automatici di Windows", -1, None, "Windows scarica e installa gli aggiornamenti da solo.")
n("bitlocker_off", "BitLocker", -1, "disco di sistema", "Il disco di sistema e' cifrato: i tuoi file sono protetti se il PC viene rubato.")
n("uac_dimmed_off", "Oscuramento dello schermo UAC", -1, None, "Le richieste di amministratore oscurano lo schermo: i giochi possono uscire.")
n("virt_off", "Virtualizzazione", -1, "VBS, Isolamento core, Hyper-V", "Integrita' della memoria, VBS e Hyper-V: protezioni che costano un po' di FPS.")

# ------------------------------------------------------------------ DEBLOAT
for _id, _l, _t in [("app_bing", "Meteo, Notizie, Sport e Finanza", "app di Bing"),
                    ("app_solitaire", "Microsoft Solitaire Collection", None),
                    ("app_candy", "Giochi e app sponsorizzate", "Candy Crush, TikTok, Spotify..."),
                    ("app_clipchamp", "Clipchamp", None),
                    ("app_officehub", "App promozionale di Microsoft 365", "non tocca Office se lo hai installato"),
                    ("app_getstarted", "Suggerimenti", "Get Started"),
                    ("app_feedback", "Hub di Feedback", None),
                    ("app_maps", "Mappe", None),
                    ("app_todo", "Microsoft To Do", None),
                    ("app_powerautomate", "Power Automate", None),
                    ("app_devhome", "Dev Home", None),
                    ("app_mixedreality", "Realta' mista e 3D Viewer", None),
                    ("app_teams", "Microsoft Teams personale", None),
                    ("app_skype_people", "Skype, Contatti e vecchia Posta", None),
                    ("app_family", "Microsoft Family", None),
                    ("app_journal_sway", "Journal, Sway, OneNote e Power BI", None),
                    ("app_zunevideo", "Film e TV", None),
                    ("app_xboxold", "Xbox Console Companion", "la vecchia app Xbox"),
                    ("app_pcmanager", "Microsoft PC Manager e AI Hub", None),
                    ("app_cortana", "Cortana", None),
                    ("app_alarms_recorder", "Sveglie e Registratore di suoni", None),
                    ("app_stickynotes", "Sticky Notes", None),
                    ("app_outlook_new", "Nuovo Outlook", None),
                    ("app_phonelink", "Collegamento al telefono", None),
                    ("app_onedrive", "OneDrive", None)]:
    n(_id, _l, -1, _t)  # frase breve: la descrizione dell'app


def get(tid):
    return N.get(tid)


# frasi brevi delle voci che accendono qualcosa, scritte come descrizione della cosa (non come azione)
for _id, _short in [
        ("fix_pagefile", "La 'RAM di riserva' su disco: senza, i giochi vanno in crash quando la RAM finisce."),
        ("fix_autotuning", "Adatta la rete alla velocita' della tua connessione."),
        ("fix_svc_wuauserv", "Serve ad aggiornare driver, giochi Game Pass e DirectX."),
        ("fix_svc_bits", "Serve a Windows Update, all'app Xbox e a Epic."),
        ("fix_svc_audiosrv", "Senza questo servizio il PC non ha audio."),
        ("fix_svc_audioendpointbuilder", "Serve all'audio di Windows."),
        ("fix_svc_gamingservices", "Senza, i giochi Game Pass non partono."),
        ("fix_svc_xblauthmanager", "Serve per l'accesso Xbox nei giochi Game Pass."),
        ("fix_svc_dnscache", "Ricorda gli indirizzi dei siti: senza, ogni connessione parte piu' lenta."),
        ("fix_svc_mpssvc", "Alcuni giochi e anti-cheat non partono senza firewall."),
        ("fix_svc_schedule", "Serve a molti launcher e ai driver NVIDIA e AMD."),
        ("fix_svc_themes", "L'aspetto di Windows: spento non aiuta i giochi."),
        ("fix_trim", "Tiene l'SSD veloce nel tempo."),
        ("nvfix_shadercache", "Il driver salva gli shader compilati: meno stutter."),
        ("nvfix_thread", "Il driver distribuisce il lavoro su piu' core: serve ai giochi OpenGL."),
        ("nv_vsync_on", "Insieme a G-SYNC elimina il tearing rimasto."),
        ("nv_fps_cap", "Tiene G-SYNC sempre attivo e la latenza bassa."),
        ("amd_fps_cap", "Tiene FreeSync sempre attivo e la latenza bassa."),
        ("mmcss_games", "Vale per i giochi che si registrano al servizio multimediale di Windows."),
        ("mouse_pointer_6", "Il movimento del mouse non viene moltiplicato.")]:
    N[_id]["short"] = _short


def label(t):
    """nome breve della voce (o quello vecchio se manca)."""
    return (N.get(t.id) or {}).get("label") or t.name


def verbo(t):
    """'accesa' o 'spenta': cosa succede alla cosa quando LagDoctor applica la voce."""
    return "accesa" if (N.get(t.id) or {}).get("pol", 1) > 0 else "spenta"
