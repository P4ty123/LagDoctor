"""Testi brevi di ogni voce.

    short = la frase sotto il nome della voce (molto breve)
    sum   = la sintesi in grassetto in cima ai dettagli: cosa fa e quando conviene davvero
La spiegazione completa e i possibili problemi restano in tweak_docs.py.
"""

S = {}


def s(tid, short, sm):
    S[tid] = {"short": short, "sum": sm}


# ------------------------------------------------------------------ CORREZIONI
s("fix_hpet", "Toglie il timer HPET forzato, che peggiora FPS e stutter.",
  "Riporta Windows al timer normale: con l'HPET forzato aumentano latenza e scatti. Da correggere sempre, non ha controindicazioni.")
s("fix_pagefile", "Riattiva il file di paging, senza cui i giochi vanno in crash.",
  "Senza file di paging, quando la RAM finisce i giochi si chiudono invece di rallentare un attimo. Riattivarlo e' sempre consigliato, anche con 32 GB.")
s("fix_autotuning", "Riporta la velocita' piena di download.",
  "Il vecchio 'tweak di rete' che lo spegne rallenta download e aggiornamenti senza abbassare il ping. Riattivarlo non ha controindicazioni.")
s("fix_largecache", "Ridà ai programmi la RAM tolta dalla cache.",
  "Con la cache in modalita' server Windows toglie RAM ai giochi. Il valore 0 e' quello normale dei PC di casa.")
s("fix_clearpagefile", "Spegnimento di nuovo veloce.",
  "Svuotare il file di paging a ogni spegnimento lo rende molto lento e non aiuta i giochi: e' un residuo di vecchie guide.")
s("fix_powersaver", "Esce dal piano che limita CPU e GPU.",
  "Con 'Risparmio energia' la CPU non arriva alle frequenze massime: su un PC da gioco toglie prestazioni ovunque.")
s("fix_hags_off_40", "Serve alle RTX 40/50 per Frame Generation.",
  "Sulle RTX 40 e 50 HAGS e' necessario per DLSS Frame Generation e di solito riduce un po' la latenza.")
for _id, _n, _why in [("wuauserv", "Windows Update", "senza, non si aggiornano driver, giochi Game Pass e DirectX"),
                      ("bits", "BITS", "serve a Windows Update, all'app Xbox e a Epic"),
                      ("audiosrv", "Audio di Windows", "senza, il PC non ha audio"),
                      ("audioendpointbuilder", "Generatore endpoint audio", "serve all'audio di Windows"),
                      ("gamingservices", "Gaming Services", "senza, i giochi Game Pass non partono"),
                      ("xblauthmanager", "Xbox Live Auth Manager", "serve per l'accesso Xbox nei giochi Game Pass"),
                      ("dnscache", "Client DNS", "senza, ogni connessione parte piu' lenta"),
                      ("mpssvc", "Windows Firewall", "alcuni giochi e anti-cheat non partono senza"),
                      ("schedule", "Utilita' di pianificazione", "serve a molti launcher e ai driver NVIDIA e AMD"),
                      ("themes", "Temi", "spento rompe l'aspetto di Windows senza aiutare i giochi")]:
    s("fix_svc_" + _id, "Riattiva il servizio %s." % _n,
      "Il servizio e' stato spento, di solito da uno script 'debloat': %s. Riattivarlo non costa prestazioni." % _why)
s("fix_trim", "Riattiva il TRIM: l'SSD non rallenta col tempo.",
  "Senza TRIM l'SSD diventa piu' lento e si consuma di piu'. Va sempre tenuto attivo.")

# ------------------------------------------------------------------ DRIVER NVIDIA
s("nvfix_vsync_half", "Toglie il V-Sync a meta' della frequenza del monitor.",
  "Con il V-Sync a 1/2 o 1/3 un monitor da 165 Hz mostra al massimo 82 o 55 FPS e tutto sembra lento. Da correggere.")
s("nvfix_fpscap_low", "Toglie un limite FPS troppo basso per tutti i giochi.",
  "Un limite molto sotto la frequenza del monitor toglie fluidita' in ogni gioco. Da correggere.")
s("nvfix_minpower", "La scheda video non resta piu' a frequenze basse.",
  "'Prediligi consumo minimo' tiene la GPU bassa anche nei giochi: meno FPS. Da correggere.")
s("nvfix_shadercache", "Riattiva la cache degli shader: meno stutter.",
  "Senza cache i giochi ricompilano gli shader ogni volta e scattano nei primi minuti e in ogni zona nuova. Da correggere.")
s("nvfix_vrr_blocked", "Sblocca G-SYNC in tutti i giochi.",
  "Se e' bloccato nel profilo globale, G-SYNC non funziona in nessun gioco anche se e' acceso. Da correggere.")
s("nvfix_fxaa", "Toglie l'FXAA forzato che sfoca l'immagine.",
  "Forzato su tutti i giochi sfoca testi e interfaccia e si somma all'antialiasing del gioco. Da correggere.")
s("nvfix_thread", "Riattiva l'ottimizzazione thread del driver.",
  "Spenta, i giochi OpenGL come Minecraft Java e gli emulatori perdono FPS. Da correggere.")
s("nvfix_prerender", "Meno frame preparati in anticipo: meno input lag.",
  "Con troppi frame in coda ogni comando arriva sullo schermo in ritardo. Da correggere.")
s("nv_lowlat_on", "Meno input lag quando la scheda video e' al massimo.",
  "Il driver prepara un solo frame in anticipo. Utile nei giochi senza NVIDIA Reflex; se il gioco ha Reflex, usa quello.")
s("nv_shadercache_unlimited", "Cache degli shader senza limite.",
  "Con molti giochi installati la cache non si riempie mai e gli shader non vengono ricompilati: meno stutter. Consigliata.")
s("nv_refresh_highest", "I giochi usano sempre la frequenza massima del monitor.",
  "Evita che i giochi vecchi partano a 60 Hz su un monitor piu' veloce. Nessuna controindicazione.")
s("nv_power_max", "La scheda video resta sempre a frequenze alte.",
  "Evita i cali momentanei nei giochi leggeri, ma la GPU consuma e scalda di piu' anche sul desktop.")
s("nv_gsync_windowed", "G-SYNC anche nei giochi in finestra o senza bordi.",
  "Molti giochi moderni usano la finestra senza bordi: cosi' anche loro hanno la frequenza variabile.")
s("nv_vsync_on", "V-Sync del driver acceso, da usare insieme a G-SYNC.",
  "Con G-SYNC e un limite FPS sotto la frequenza elimina il tearing rimasto senza aggiungere latenza. Spegni il V-Sync dentro i giochi.")
s("nv_fps_cap", "Limite FPS 3 sotto la frequenza del monitor.",
  "Tiene G-SYNC sempre attivo ed evita la latenza del V-Sync quando gli FPS toccano il massimo. Consigliato con G-SYNC.")
s("nv_texture_perf", "Filtro delle texture piu' veloce, qualita' quasi uguale.",
  "Qualche FPS in piu' nei giochi pesanti sulle texture; la differenza di qualita' si vede appena.")

# ------------------------------------------------------------------ DRIVER AMD
s("amdfix_chill", "Spegne Radeon Chill, che fa variare gli FPS.",
  "Chill cambia gli FPS di continuo e causa micro-stutter: non e' pensato come limitatore. Da correggere.")
s("amdfix_esync", "Spegne Enhanced Sync, causa nota di stutter.",
  "Con FreeSync non serve ed e' una causa segnalata di scatti e sfarfallii. Da correggere.")
s("amdfix_vsync_always", "Il V-Sync non e' piu' forzato in tutti i giochi.",
  "Forzato sempre aggiunge input lag ovunque: meglio lasciar decidere al gioco. Da correggere.")
s("amdfix_frtc_low", "Toglie un limite FPS troppo basso per tutti i giochi.",
  "Un limite molto sotto la frequenza del monitor toglie fluidita' in ogni gioco. Da correggere.")
s("amdfix_mlaa", "Toglie l'antialiasing forzato che sfoca l'immagine.",
  "L'MLAA forzato sfoca testi e interfaccia e costa FPS in tutti i giochi. Da correggere.")
s("amd_antilag_on", "Meno input lag quando la scheda video e' al massimo.",
  "Radeon Anti-Lag riduce il ritardo dei comandi quando la GPU e' al limite. Consigliato nei giochi competitivi.")
s("amd_boost_off", "Immagine sempre nitida, anche nei movimenti veloci.",
  "Radeon Boost abbassa la risoluzione quando muovi la visuale: piu' FPS ma immagine meno nitida. Spegnilo se la preferisci pulita.")
s("amd_afmf_off", "Niente frame generati dal driver: meno latenza.",
  "AFMF aumenta gli FPS mostrati ma aggiunge latenza. Nei giochi competitivi conta di piu' la reattivita'.")
s("amd_fps_cap", "Limite FPS 3 sotto la frequenza del monitor.",
  "Tiene FreeSync sempre attivo e riduce consumi e latenza da V-Sync. Consigliato con FreeSync.")

# ------------------------------------------------------------------ GIOCO
s("game_mode", "Windows da' la precedenza al gioco.",
  "La Modalita' Gioco di Windows rimanda aggiornamenti e installazioni di driver mentre giochi. Consigliata, e' attiva di base.")
s("windowed_opt", "Meno latenza nei giochi in finestra o senza bordi.",
  "I giochi DirectX 10 e 11 in finestra usano il metodo moderno di Windows: meno latenza, frame piu' regolari e VRR. Consigliata.")
s("hags", "La scheda video gestisce da sola la coda dei frame.",
  "Serve per DLSS Frame Generation e spesso riduce un po' la latenza, ma in alcuni giochi peggiora: provala con il test Prima/Dopo.")
s("fso_off", "Forza il vero schermo intero esclusivo.",
  "Utile solo in alcuni giochi vecchi; puo' rompere Auto HDR e rallentare l'Alt+Tab. Effetto molto variabile.")
s("mmcss_games", "Priorita' alta ai giochi che usano MMCSS.",
  "Alza la priorita' solo dei pochi giochi che si registrano al servizio multimediale di Windows: spesso non cambia niente.")
s("pcie_aspm", "Scheda video e SSD non vanno in risparmio sul bus PCIe.",
  "Correzione nota per micro-scatti quando il carico cambia all'improvviso. Consuma un po' di piu' a riposo.")
s("vrr_opt", "G-SYNC e FreeSync anche nei giochi DirectX 11.",
  "Meno tearing e scatti quando gli FPS scendono sotto la frequenza del monitor. Consigliata se hai un monitor G-SYNC o FreeSync.")

# ------------------------------------------------------------------ OVERLAYS
s("game_dvr", "Windows smette di registrare il gioco in sottofondo.",
  "La registrazione continua della Xbox Game Bar usa scheda video e disco: e' una causa nota di micro-scatti. Consigliata.")
s("mpo_off", "Corregge sfarfallii e scatti nei giochi senza bordi.",
  "Serve solo se hai sfarfallii, schermi neri o scatti in finestra senza bordi, soprattutto con piu' monitor. Senza questi problemi non serve.")
s("mpo_full", "Spegne l'MPO del tutto, anche nel driver.",
  "Da usare solo se la versione normale non ha risolto sfarfallii o scatti.")
s("gamedvr_policy", "Blocca la registrazione della Game Bar per tutti.",
  "Come la voce normale, ma l'app Xbox non puo' piu' riattivarla dopo un aggiornamento.")
s("gamebar_shortcut", "Win+G e il tasto Xbox non aprono piu' la Game Bar.",
  "Evita che la Game Bar si apra per sbaglio in partita, cosa che con i controller succede spesso.")
s("ov_steam", "Il menu Maiusc+Tab di Steam dentro i giochi.",
  "Ogni overlay disegna sopra ogni frame: spegnilo se non lo usi, in alcuni giochi causa micro-scatti.")
s("ov_nvidia", "L'overlay Alt+Z di NVIDIA.",
  "Resta agganciato al gioco e, con Instant Replay, registra di continuo. Spegnilo se non ti serve.")
s("ov_amd", "L'overlay di AMD Software.",
  "Il replay istantaneo registra di continuo e l'overlay si aggancia a ogni gioco. Spegnilo se non ti serve.")
s("ov_intel", "L'overlay della scheda video Intel.",
  "Si aggancia al gioco e la registrazione usa la scheda video. Spegnilo se non ti serve.")
s("ov_discord", "L'overlay di Discord dentro i giochi.",
  "E' uno degli overlay piu' indicati come causa di micro-scatti e conflitti. Spegnilo se non lo usi.")
s("ov_rtss", "L'overlay di RivaTuner (MSI Afterburner).",
  "Finche' e' aperto si aggancia a tutti i programmi 3D. Tienilo solo se usi davvero i suoi grafici.")
s("ov_overwolf", "Le app Overwolf sopra i giochi.",
  "Sono basate su un browser: usano CPU e memoria e si agganciano al gioco. Spegnile se non ti servono.")
s("ov_ea", "Il menu Maiusc+F1 dei giochi EA.",
  "Un livello in piu' sopra il gioco: spegnilo se non lo usi.")
s("ov_ubisoft", "Il menu Maiusc+F2 dei giochi Ubisoft.",
  "Un livello in piu' sopra il gioco: spegnilo se non lo usi.")
s("ov_gog", "Il menu Maiusc+Tab dei giochi GOG.",
  "Un livello in piu' sopra il gioco: spegnilo se non lo usi.")

# ------------------------------------------------------------------ CPU ED ENERGIA
s("plan_ultimate", "Il piano energetico piu' spinto di Windows.",
  "La CPU resta sempre pronta: latenza minima quando arriva il carico. Consuma e scalda di piu' anche a riposo.")
s("core_parking", "Tutti i core del processore restano sempre attivi.",
  "Evita il ritardo di riattivazione dei core. Aiuta soprattutto sui portatili e sugli Intel ibridi meno recenti.")
s("power_throttling", "Windows non rallenta piu' i programmi in background.",
  "Discord, OBS o la musica non vengono frenati per risparmiare energia mentre giochi.")
s("usb_suspend", "Mouse, tastiera e cuffie USB non vanno in risparmio.",
  "Evita micro-blocchi del mouse e audio che si interrompe. Consigliata, soprattutto sui portatili.")
s("prio_sep", "Piu' tempo di CPU alla finestra in primo piano.",
  "Tweak molto diffuso, ma su Windows 11 i benefici non sono dimostrati. Si esclude con la variante 2A.")
s("sys_resp", "Meno CPU riservata alle attivita' di sottofondo.",
  "Vale solo per i programmi registrati al servizio multimediale di Windows: di solito non cambia niente.")
s("dynamic_tick", "Il timer di sistema scatta sempre.",
  "Alcuni riportano una latenza piu' costante, ma gli effetti misurati sono minimi e a volte negativi.")
s("prio_sep_2a", "Massimo tempo di CPU al gioco in primo piano.",
  "Variante preferita dalle community competitive, ma i benefici sono solo aneddotici. Si esclude con la variante 26.")
s("boost_aggr", "La CPU sale subito al massimo quando serve.",
  "Riduce il ritardo di risalita della frequenza. Sui desktop spesso e' gia' cosi'.")
s("min_cpu_100", "La CPU non scende mai di frequenza.",
  "Nessun ritardo di risalita, ma piu' calore e consumi. Sui Ryzen moderni il guadagno e' minimo.")
s("idle_off", "La CPU non va mai a riposo.",
  "Latenza minima per setup competitivi estremi, ma la CPU sembra sempre al 100% e scalda molto. Solo per chi sa cosa fa.")
s("timer_res", "Timer di sistema a 0,5 ms, sempre attivo.",
  "Limitatori di FPS e attese brevi piu' precisi e frame piu' regolari. Uno dei tweak piu' famosi; consuma un po' di piu' a riposo.")

# ------------------------------------------------------------------ MEMORIA E DISCO
s("mem_compress", "Windows non comprime piu' la RAM.",
  "Risparmia un po' di lavoro alla CPU. Ha senso solo con 32 GB di RAM o piu'.")
s("sysmain", "Windows smette di precaricare i programmi in RAM.",
  "Meno attivita' del disco in background. Su SSD il beneficio e' minimo.")
s("wsearch", "Niente indicizzazione dei file in background.",
  "Il disco lavora meno mentre giochi, ma la ricerca nel menu Start e in Esplora file diventa piu' lenta.")
s("hibernation", "Windows riparte da zero a ogni accensione.",
  "Libera spazio su disco quanto la RAM e toglie l'avvio rapido: utile se dopo giorni di uso il PC scatta di piu'.")
s("defender_excl", "Defender non controlla i file dei giochi.",
  "Caricamenti piu' veloci e meno stutter mentre il gioco carica i file. Il resto del PC resta protetto. Consigliata.")
s("paging_exec", "Driver e kernel restano sempre in RAM.",
  "In teoria evita ricaricamenti dal disco; benefici mai misurati. Innocua con 16 GB o piu'.")
s("prefetch_off", "Windows non prepara piu' i programmi in anticipo.",
  "Tweak dei tempi di Windows XP: sugli SSD non cambia nulla e i programmi possono aprirsi piu' lentamente.")
s("svchost_split", "Meno processi svchost in Gestione attivita'.",
  "Raggruppa i servizi di Windows: meno processi e un po' meno RAM, ma nessun effetto dimostrato sugli FPS.")
s("ntfs_lastaccess", "Meno scritture inutili sul disco.",
  "Windows non segna l'ora di accesso a ogni file letto: utile quando un gioco legge migliaia di file.")
s("ntfs_83", "Non crea piu' i nomi corti dei file (PROGRA~1).",
  "Piccolo risparmio nelle cartelle con moltissimi file; qualche vecchio installer potrebbe non funzionare.")
s("storage_sense_off", "Niente pulizie automatiche del disco.",
  "Evita che la pulizia di Windows parta mentre giochi.")
s("maintenance_off", "Windows non fa piu' la manutenzione giornaliera.",
  "Evita attivita' in background, ma di solito parte solo con il PC inattivo. La game mode la mette gia' in pausa durante il gioco.")

# ------------------------------------------------------------------ RETE
s("delivery_opt", "La tua connessione non invia aggiornamenti ad altri PC.",
  "Windows non usa la tua rete per condividere aggiornamenti su Internet mentre giochi. Nessuna controindicazione.")
s("nic_power", "La scheda di rete non va in risparmio.",
  "Evita picchi di ping e brevi disconnessioni, soprattutto con il Wi-Fi.")
s("nagle", "Fa partire subito i piccoli pacchetti di rete TCP.",
  "Fa partire e confermare subito i piccoli pacchetti di rete. Serve solo nei giochi che usano TCP, come alcuni MMO e giochi vecchi: "
  "negli sparatutto, in Dota 2 e in League of Legends non cambia niente.")
s("net_throttle", "Toglie il limite ai pacchetti di rete durante audio e video.",
  "In un test pubblicato e' stato l'unico tweak di rete ad abbassare il ping, in un solo gioco. Negli altri non cambia nulla.")
s("nic_intmod", "La scheda di rete avvisa subito la CPU per ogni pacchetto.",
  "Latenza di rete piu' bassa in cambio di un po' piu' di lavoro per la CPU. Indicata da Microsoft e Intel per la latenza minima.")
s("nic_eee", "Il cavo di rete non va in risparmio energetico.",
  "Evita micro-disconnessioni e picchi di ping che alcuni driver causano con il risparmio energetico.")
s("nic_flow", "La scheda di rete non mette in pausa l'invio.",
  "Consigliata da molte guide, ma l'effetto non e' mai stato misurato.")
s("ipv4_pref", "Le connessioni usano IPv4 quando possibile.",
  "Utile solo se il tuo IPv6 e' instabile o passa da un tunnel lento; altrimenti non cambia niente.")
s("teredo_off", "Spegne il tunnel IPv6 Teredo.",
  "Toglie un adattatore virtuale inutile, ma alcuni giochi Game Pass lo usano per il multiplayer: se hai problemi di NAT, annulla.")
s("nic_lso", "La CPU divide da sola i pacchetti grandi.",
  "Aiuta con alcuni driver economici che causano picchi di ping; con i driver buoni conviene lasciarlo acceso.")

# ------------------------------------------------------------------ INTERFACCIA E INPUT
s("mouse_accel", "La mira dipende solo da quanto muovi il mouse.",
  "Senza accelerazione la memoria muscolare resta costante: fondamentale negli sparatutto. Consigliata.")
s("bg_apps", "Le app dello Store non girano in background.",
  "Meno processi e notifiche mentre giochi.")
s("transparency", "Niente trasparenze sul desktop.",
  "Il compositore di Windows lavora un po' meno; dentro i giochi a schermo intero non cambia niente.")
s("diagtrack", "Ferma l'invio di dati diagnostici a Microsoft.",
  "Meno attivita' e traffico di rete in background.")
s("visual_fx", "Windows senza animazioni ne' ombre.",
  "Finestre e menu si aprono all'istante e il PC sembra piu' scattante, soprattutto se e' poco potente. Dentro i giochi non cambia niente.")
s("menu_delay", "I menu di Windows si aprono subito.",
  "Solo estetico: nessun effetto sui giochi.")
s("sticky_keys", "Premere Shift 5 volte non apre piu' i Tasti permanenti.",
  "Nei giochi Shift si preme spesso, e quella finestra ti butta fuori dalla partita. Consigliata.")
s("keyboard_fast", "I tasti tenuti premuti si ripetono piu' in fretta.",
  "Ritardo minimo e ripetizione veloce, comoda nei menu e quando scrivi.")
s("wait_kill_svc", "Spegnimento e riavvio piu' rapidi.",
  "Windows aspetta al massimo 2 secondi invece di 5 i servizi lenti a chiudersi.")
s("startup_delay", "I programmi all'avvio partono subito.",
  "Il desktop e' pronto qualche secondo prima.")
s("notifications_off", "Niente popup di notifica sopra il gioco.",
  "Blocca le notifiche di Windows e delle app. La Modalita' Gioco ne blocca gia' molte.")
s("widgets_off", "Il pannello Widget non scarica notizie in background.",
  "Un processo web in meno sempre attivo.")
s("edge_bg_off", "Edge non resta aperto in background.",
  "Libera RAM e CPU se non usi Edge mentre giochi.")
s("recall_off", "Spegne Recall, l'analisi AI degli screenshot.",
  "Conta solo sui PC Copilot+: niente catture e analisi in background. Sugli altri PC non fa nulla.")
s("telemetry_policy", "Raccolta dati e pubblicita' di Windows al minimo.",
  "Meno attivita' in background e meno app suggerite; effetto piccolo sulle prestazioni.")
s("wersvc", "Windows non crea piu' i rapporti dopo un crash.",
  "Dopo un crash non perde tempo a raccogliere e inviare il rapporto.")
s("spooler", "Spegne il servizio di stampa.",
  "Da usare SOLO se non hai una stampante: dopo non potrai stampare.")
s("access_keys", "Niente finestre di accessibilita' durante il gioco.",
  "Tenere premuto Shift destro o Bloc Num non apre piu' Filtro tasti e Tasti di alternanza in partita.")
s("copilot_off", "Copilot non resta pronto in background.",
  "Un componente in meno attivo mentre giochi.")
s("start_web_off", "La ricerca del menu Start non usa piu' Bing.",
  "Ricerca piu' veloce, solo sul PC, senza processi web in background.")
s("wu_active_hours", "Niente riavvii per aggiornamenti tra le 10 e le 2.",
  "Evita riavvii e avvisi di riavvio durante le sessioni di gioco serali.")
s("usb_notify_off", "Niente popup per i problemi dei dispositivi USB.",
  "Nessuna notifica sopra il gioco se un dispositivo USB ha un problema momentaneo.")
s("metered_drivers", "Windows non installa da solo le app delle periferiche.",
  "Evita software di mouse e tastiere che restano in background; alcuni causano stutter.")
s("mouse_pointer_6", "Velocita' del puntatore al valore neutro (6/11).",
  "Il movimento del mouse non viene moltiplicato: utile nei giochi che non usano il 'raw input'.")

# ------------------------------------------------------------------ SICUREZZA (PERICOLOSE)
s("mitigations_off", "Spegne le protezioni Spectre e Meltdown.",
  "Guadagno quasi nullo sui processori recenti, qualche % solo sugli Intel fino alla 9a generazione. Il PC diventa attaccabile anche da siti web: sconsigliata.")
s("defender_rt_off", "Defender smette di controllare i file aperti.",
  "Pericolosa: per i giochi basta escludere le loro cartelle, che e' molto piu' sicuro.")
s("wu_auto_off", "Windows non si aggiorna piu' da solo.",
  "Niente download durante le partite, ma dovrai aggiornare a mano: senza aggiornamenti il PC resta scoperto.")
s("bitlocker_off", "Decritta il disco di sistema.",
  "Toglie un piccolo costo su letture e scritture, ma chi prende il PC o il disco puo' leggere i tuoi file. Ci vogliono da minuti a ore.")
s("uac_dimmed_off", "Le richieste di amministratore non oscurano lo schermo.",
  "Evita che i giochi a schermo intero escano o si riducano a icona. La richiesta di conferma resta.")
s("virt_off", "Spegne Integrita' della memoria, VBS e Hyper-V.",
  "Puo' valere fino al 5-10% di FPS in alcuni giochi, ma toglie protezioni importanti e blocca macchine virtuali e Sandbox.")

# ------------------------------------------------------------------ DEBLOAT
for _id, _short in [("app_bing", "Toglie Meteo, Notizie, Sport e Finanza."),
                    ("app_solitaire", "Toglie il solitario con pubblicita'."),
                    ("app_candy", "Toglie giochi e app sponsorizzate."),
                    ("app_clipchamp", "Toglie l'editor video Clipchamp."),
                    ("app_officehub", "Toglie l'app che pubblicizza Microsoft 365."),
                    ("app_getstarted", "Toglie l'app dei suggerimenti."),
                    ("app_feedback", "Toglie l'Hub di Feedback."),
                    ("app_maps", "Toglie l'app Mappe."),
                    ("app_todo", "Toglie Microsoft To Do."),
                    ("app_powerautomate", "Toglie Power Automate."),
                    ("app_devhome", "Toglie Dev Home."),
                    ("app_mixedreality", "Toglie Realta' mista e 3D Viewer."),
                    ("app_teams", "Toglie Teams personale, che parte con Windows."),
                    ("app_skype_people", "Toglie Skype, Contatti e la vecchia Posta."),
                    ("app_family", "Toglie Microsoft Family."),
                    ("app_journal_sway", "Toglie Journal, Sway, OneNote e Power BI."),
                    ("app_zunevideo", "Toglie il vecchio Film e TV."),
                    ("app_xboxold", "Toglie la vecchia Xbox Console Companion."),
                    ("app_pcmanager", "Toglie PC Manager e AI Hub."),
                    ("app_cortana", "Toglie Cortana."),
                    ("app_alarms_recorder", "Toglie Sveglie e Registratore di suoni."),
                    ("app_stickynotes", "Toglie Sticky Notes."),
                    ("app_outlook_new", "Toglie il nuovo Outlook gratuito."),
                    ("app_phonelink", "Toglie Collegamento al telefono.")]:
    s(_id, _short, "App preinstallata che di solito non serve: toglierla riduce processi e aggiornamenti in background. "
                   "Gli FPS non cambiano molto. Si puo' reinstallare dal Microsoft Store.")
s("app_teams", "Toglie Teams personale, che parte con Windows.",
  "Teams personale parte con Windows e resta in memoria: toglierlo libera RAM e CPU. Si puo' reinstallare quando vuoi.")
s("app_family", "Toglie Microsoft Family.",
  "Serve solo per il controllo genitori: tienila se la usi per gli account dei figli.")
s("app_onedrive", "Disinstalla OneDrive.",
  "Durante la sincronizzazione usa disco, rete e CPU e puo' causare stutter. Toglilo solo se non usi OneDrive per i tuoi file.")


def get(tid):
    return S.get(tid)
