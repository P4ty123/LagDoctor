"use strict";
/* LagDoctor - interfaccia. Nessuna libreria esterna: funziona offline. */

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const main = () => $("#main");
const S = { rec: null, state: null, catalog: null, page: "home", filter: "fix", sel: new Set(), open: new Set(), recCtx: null, lastScan: null, lastRecord: null, sensorTimer: null, sensorHist: [] };

async function api(path, body) {
  const opt = { headers: { "X-Token": window.LD_TOKEN } };
  if (body !== undefined) { opt.method = "POST"; opt.headers["Content-Type"] = "application/json"; opt.body = JSON.stringify(body); }
  const r = await fetch(path, opt);
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || ("Errore " + r.status));
  return j;
}
function toast(msg, ms = 3500) { const t = $("#toast"); t.textContent = msg; t.hidden = false; clearTimeout(t._h); t._h = setTimeout(() => (t.hidden = true), ms); }
function modal(html) { $("#modal").classList.remove("soft"); $("#modal-card").className = "modal-card"; $("#modal-card").innerHTML = html; $("#modal").hidden = false; return $("#modal-card"); }
function closeModal() { $("#modal").hidden = true; }
const reportUrl = (f) => "/report?f=" + encodeURIComponent(f) + "&t=" + encodeURIComponent(window.LD_TOKEN);
const base = (p) => String(p || "").split(/[\\/]/).pop();
/* icone (tratto, 24x24) */
const ICP = {
  scan: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  arrow: '<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>',
  chev: '<path d="m9 6 6 6-6 6"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-2.6-6.4L21 8"/><path d="M21 3v5h-5"/>',
  rec: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3" fill="currentColor"/>',
  cmp: '<path d="M8 3 4 7l4 4"/><path d="M4 7h16"/><path d="m16 21 4-4-4-4"/><path d="M20 17H4"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13"/><path d="M3 6h.01M3 12h.01M3 18h.01"/>',
  fps: '<path d="M3 3v18h18"/><path d="m7 15 4-4 3 3 5-6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  bolt: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
  gpu: '<rect x="2" y="7" width="20" height="10" rx="2"/><circle cx="8" cy="12" r="2"/><circle cx="16" cy="12" r="2"/>',
  low: '<path d="M3 3v18h18"/><path d="m7 9 4 4 3-3 5 6"/>',
  report: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
  trash: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/>',
};
const ic = (k) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICP[k]}</svg>`;
/* pulsante nel nuovo stile: icona + testo (+ freccia) */
const actBtn = (attrs, icon, label, cls = "", chev = true) =>
  `<button class="act ${cls}" ${attrs}><span class="ic">${ic(icon)}</span><span>${label}</span>${chev ? `<span class="chev">${ic("chev")}</span>` : ""}</button>`;
const fmt = (v, d = 0) => (v === null || v === undefined || isNaN(v)) ? "–" : Number(v).toFixed(d);

/* job: avvia e aspetta, aggiornando un elenco di messaggi */
async function runJob(start, onUpdate) {
  let job = await start;
  while (job.status === "running") {
    await new Promise((r) => setTimeout(r, job.kind === "record" ? 800 : job.kind === "fixpc" ? 350 : 600));
    job = await api("/api/job?id=" + job.id);
    onUpdate && onUpdate(job);
  }
  if (job.status === "error") throw new Error(job.error);
  return job;
}
function logList(el, msgs) { el.innerHTML = msgs.map((m) => "<li>" + esc(m) + "</li>").join(""); el.scrollTop = el.scrollHeight; }

/* ------------------------------------------------------------------ navigazione */
/* animazioni: la scheda vecchia scompare, la nuova entra dal basso (niente animazioni se Windows le ha spente) */
/* finestra senza bordo (WebView2): la barra del titolo la disegna LagDoctor */
const FRAMELESS = !!window.pywebview || /[?&]frameless=1/.test(location.search);
if (FRAMELESS) document.body.classList.add("frameless");
const winApi = (a, ...args) => (window.pywebview && window.pywebview.api && window.pywebview.api[a] ? window.pywebview.api[a](...args) : Promise.resolve());
$("#tb-min").onclick = () => winApi("minimize");
$("#tb-max").onclick = () => winApi("toggle_maximize").then(() => setTimeout(syncMax, 80));
$("#tb-close").onclick = () => winApi("close");
/* trascinare: la barra in alto e il logo (classe pywebview-drag-region, lo fa pywebview). Doppio clic = ingrandisci */
[$("#tb-drag"), $(".brand")].forEach((el) => el.addEventListener("dblclick", () => { if (FRAMELESS) winApi("toggle_maximize"); }));
/* ridimensionare dai bordi: la finestra segue il mouse (un comando alla volta, per non intasarla) */
$$("#rz i").forEach((el) => el.addEventListener("mousedown", async (e) => {
  if (e.button !== 0 || !FRAMELESS) return;
  e.preventDefault();
  const edge = el.dataset.e, sx = e.screenX, sy = e.screenY;
  const size = await winApi("get_size");
  if (!size) return;
  let busy = false, last = null;
  const send = async () => {
    if (busy || !last) return;
    busy = true; const [w, h] = last; last = null;
    await winApi("resize_to", w, h, edge).catch(() => {});
    busy = false; send();
  };
  const move = (ev) => {
    const dx = ev.screenX - sx, dy = ev.screenY - sy;
    const w = size[0] + (edge.includes("left") ? -dx : edge.includes("right") ? dx : 0);
    const h = size[1] + (edge.includes("top") ? -dy : edge.includes("bottom") ? dy : 0);
    last = [w, h]; send();
  };
  const up = () => { window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up); document.body.classList.remove("resizing"); };
  document.body.classList.add("resizing");
  window.addEventListener("mousemove", move); window.addEventListener("mouseup", up);
}));
/* finestra ingrandita: niente bordi per ridimensionare */
const syncMax = () => winApi("is_maximized").then((m) => { document.body.classList.toggle("maxed", m === true); $("#tb-max").title = m ? "Ripristina" : "Ingrandisci"; }).catch(() => {});
if (FRAMELESS) { window.addEventListener("resize", () => setTimeout(syncMax, 60)); window.addEventListener("pywebviewready", syncMax); }
/* animazioni: decide solo l'interruttore in Impostazioni (S.noAnim). Non seguono "Effetti di animazione" di
   Windows: molti lo spengono per le prestazioni (anche le ottimizzazioni degli effetti visivi) e le animazioni
   di LagDoctor sparirebbero anche con l'interruttore acceso. */
const noAnim = () => !!S.noAnim;
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
/* con una barra fissa dentro (.bar) solo dissolvenza: lo spostamento la farebbe saltare */
const animCls = (el) => (el === main() || el.querySelector(".bar") || el.classList.contains("bar")) ? "fade" : "";
function animOut(els) { els.forEach((el) => { el.classList.remove("sw-in"); el.classList.add("sw-out"); const c = animCls(el); if (c) el.classList.add(c); }); }
function animIn(els) {
  if (noAnim()) return;
  els.forEach((el, i) => {
    el.classList.remove("sw-out", "sw-in");
    const c = animCls(el); el.classList.toggle("fade", !!c);
    void el.offsetWidth;  /* riparte l'animazione */
    el.style.animationDelay = Math.min(i, 6) * 40 + "ms";
    el.classList.add("sw-in");
  });
}
/* il contenuto sotto la barra delle sotto-schede (Analizza gioco, Avvio automatico) */
function belowTabs() {
  const kids = [...main().children], i = kids.findIndex((k) => k.matches(".rg-head, .tabs2"));
  return i >= 0 ? kids.slice(i + 1) : kids;
}
/* aspetta che la pagina nuova sia disegnata (non che abbia finito di caricare tutto) */
function rendered(old, promise) {
  return Promise.race([promise, new Promise((res) => {
    const mo = new MutationObserver(() => { if (main().firstElementChild !== old) { mo.disconnect(); res(); } });
    mo.observe(main(), { childList: true }); setTimeout(() => { mo.disconnect(); res(); }, 30000);
  })]);
}
/* sotto-schede di Ottimizzazioni: categoria o filtro */
async function swapTweaks(change) {
  const list = $("#tw-list");
  if (!noAnim() && list) { animOut([list]); await wait(110); }
  change(); renderTweaks();
  if ($("#tw-list")) { $("#tw-list").classList.remove("sw-out"); animIn([$("#tw-list")]); }
}

/* "exp" e "sessions" sono schede dentro "Analizza gioco". opt.sub = cambio di sotto-scheda, opt.quiet = senza animazione */
async function go(page, opt = {}) {
  if (page === "exp" || page === "sessions") { S.recTab = page; page = "record"; }
  const tok = S.navTok = (S.navTok || 0) + 1;
  const anim = !noAnim() && !opt.quiet && S.page !== undefined && main().firstElementChild;
  const sub = anim && opt.sub;
  if (anim) {
    animOut(sub ? belowTabs() : [main()]);
    await wait(sub ? 120 : 150);
    if (tok !== S.navTok) return;  /* nel frattempo e' stata scelta un'altra scheda */
  }
  S.page = page;
  const navPage = page === "scan" || page === "verifica" ? "home" : page;  /* pagine aperte dalla Panoramica */
  $$("#nav a").forEach((a) => a.classList.toggle("active", a.dataset.page === navPage));
  clearInterval(S.sensorTimer);
  main().scrollTop = 0;
  refreshState().catch(() => {});
  const old = main().firstElementChild;
  const fn = page === "record" ? ({ rec: record, exp, sessions })[S.recTab || "rec"]
    : ({ home, scan, tweaks: tweaksPage, driver, startup, gamemode: gamemodePage, verifica: verificaPage, fixpc: fixpcPage, pulitore: pulitorePage, backups: backupsPage })[page];
  const p = Promise.resolve().then(fn).catch((e) => { main().classList.remove("sw-out", "fade"); throw e; });
  if (!anim) return p;
  const pp = p.catch(() => {});
  await rendered(old, pp);
  if (tok !== S.navTok) return;
  /* pagine che prima mostrano "Leggo..." (Driver video, Ottimizzazioni): l'animazione parte sul contenuto vero.
     Il caricamento resta nascosto se dura poco; se dura di piu' compare in dissolvenza. */
  const ld = main().children.length === 1 && main().firstElementChild.classList.contains("loading") ? main().firstElementChild : null;
  if (ld) {
    const show = setTimeout(() => { if (tok === S.navTok && main().firstElementChild === ld) { main().classList.remove("sw-out", "fade"); animIn([ld]); } }, 450);
    await rendered(ld, pp);
    clearTimeout(show);
    if (tok !== S.navTok) return;
  }
  main().classList.remove("sw-out", "fade");
  animIn(sub ? belowTabs() : [...main().children]);
}
$$("#nav a").forEach((a) => a.addEventListener("click", () => { if (a.dataset.page === S.page && a.dataset.page !== "record") return; if (a.dataset.page === "record") S.recTab = "rec"; go(a.dataset.page); }));

function recTabs(active) {
  const exp = S.state && S.state.experiment ? ' <span class="pill warn">in corso</span>' : "";
  return `<div class="rtabs" id="rec-tabs">
    <a data-t="rec" class="${active === "rec" ? "on" : ""}">${ic("rec")}Registra</a>
    <a data-t="exp" class="${active === "exp" ? "on" : ""}">${ic("cmp")}Prima / Dopo${exp}</a>
    <a data-t="sessions" class="${active === "sessions" ? "on" : ""}">${ic("list")}Sessioni</a></div>`;
}
/* intestazione comune delle pagine di Analizza gioco */
function recHead(tab, sub) {
  return `<div class="rg-head"><div><h1>Analizza gioco</h1><p class="sub">${sub}</p></div>${recTabs(tab)}</div>`;
}
const REC_SUB = "Registra una partita: LagDoctor misura ogni frame e ti dice cosa causa scatti e lag.";
function bindRecTabs() {
  $$("#rec-tabs a").forEach((a) => a.addEventListener("click", () => { if (a.classList.contains("on")) return; S.recTab = a.dataset.t; go("record", { sub: true }); }));
}

async function refreshState() {
  S.state = await api("/api/state");
  S.noAnim = S.state.animations === false;
  if (S.state.version) $("#app-ver").textContent = "v" + S.state.version;
  const gmNav = $("#nav-gm"); if (gmNav && S.state.gm) gmNav.hidden = !S.state.gm.active;
  $("#nav-exp").hidden = !S.state.experiment;
  const rb = S.state.reboot || [], bar = $("#reboot-bar");
  bar.hidden = !rb.length;
  if (rb.length) {
    bar.innerHTML = `<b>Riavvia Windows</b><span class="grow mut">${rb.length} modifiche funzionano solo dopo il riavvio: ${rb.slice(0, 4).map(esc).join(", ")}${rb.length > 4 ? "..." : ""}</span><button class="sm" id="reboot-now">Riavvia ora</button>`;
    $("#reboot-now").onclick = () => {
      const m = modal(`<h2>Riavviare il PC?</h2><p>Salva il tuo lavoro: Windows si riavvia tra 15 secondi.</p>
        <div class="row" style="justify-content:flex-end"><button class="ghost" id="m-cancel">Non ora</button><button id="m-ok">Riavvia</button></div>`);
      $("#m-cancel", m).onclick = closeModal;
      $("#m-ok", m).onclick = async () => { await api("/api/reboot", {}); m.innerHTML = "<h2>Riavvio tra 15 secondi...</h2>"; };
    };
  }
}
async function loadCatalog(force) {
  if (!S.catalog || force) S.catalog = await api("/api/catalog");
  const n = toFix().length;
  $("#nav-fix").hidden = !n; $("#nav-fix").textContent = n;
  return S.catalog;
}

/* ------------------------------------------------------------------ problemi */
const SEV = { 3: ["ALTA", "b-bad"], 2: ["MEDIA", "b-warn"], 1: ["BASSA", "b-acc"] };
function probHtml(list) {
  if (!list || !list.length) return '<div class="empty">Nessun problema trovato.</div>';
  return list.slice().sort((a, b) => b.gravita - a.gravita).map((p, i) => `
    <div class="prob s${p.gravita}">
      <div class="prob-h"><span class="badge ${SEV[p.gravita][1]}">${SEV[p.gravita][0]}</span><b class="grow">${esc(p.titolo)}</b>
      ${p.auto_fix ? `<button class="sm" data-fix='${esc(JSON.stringify(p.auto_fix))}'>Correggi</button>` : ""}</div>
      <p>${esc(p.spiegazione)}</p><p class="fix"><b>Come risolvere:</b> ${esc(p.soluzione)}</p>
    </div>`).join("");
}
function bindFixButtons(root) {
  $$("[data-fix]", root).forEach((b) => b.addEventListener("click", async () => {
    b.disabled = true;
    try { const r = await api("/api/fix", { fix: JSON.parse(b.dataset.fix) }); toast(r.msg); b.textContent = "Fatto"; }
    catch (e) { toast("Errore: " + e.message); b.disabled = false; }
  }));
}

/* ------------------------------------------------------------------ PANORAMICA */
const SEV_TXT = { 3: ["ALTA", "s3"], 2: ["MEDIA", "s2"], 1: ["BASSA", "s1"] };
/* punteggio indicativo: 100 meno le impostazioni che tolgono prestazioni e i problemi trovati */
function pcScore(fixN, probs) {
  let s = 100 - Math.min(fixN * 4, 40);
  (probs || []).forEach((p) => { s -= p.gravita >= 3 ? 10 : p.gravita === 2 ? 5 : 2; });
  return Math.max(5, Math.min(100, Math.round(s)));
}
function scoreText(score, fixN, probs) {
  const hi = (probs || []).filter((p) => p.gravita >= 3).length;
  const title = score >= 85 ? "PC in ottima forma" : score >= 65 ? "PC in buona forma" : score >= 45 ? "Qualcosa da sistemare" : "Ci sono diversi problemi";
  const parts = [];
  parts.push(fixN ? `${fixN} impostazion${fixN === 1 ? "e ti toglie" : "i ti tolgono"} prestazioni.` : "Nessuna impostazione dannosa attiva.");
  parts.push(hi ? `${hi} problem${hi === 1 ? "a importante" : "i importanti"} nel controllo rapido.` : (probs || []).length ? `${probs.length} consigli nel controllo rapido.` : "Nessun problema trovato.");
  return { title, text: parts.join("<br>") };
}
function quickHtml(list) {
  if (!list || !list.length) return '<div class="mut" style="padding:8px 0">Nessun problema trovato.</div>';
  return list.slice().sort((a, b) => b.gravita - a.gravita).map((p) => `
    <div class="prob"><div class="prob-h"><span class="sev ${SEV_TXT[p.gravita][1]}">${SEV_TXT[p.gravita][0]}</span><b class="grow" style="font-weight:500">${esc(p.titolo)}</b>
      ${p.auto_fix ? `<button class="sm" data-fix='${esc(JSON.stringify(p.auto_fix))}'>Correggi</button>` : ""}</div>
      <details style="margin:0"><summary style="margin:6px 0 0;font-size:12.5px">Perche' e come risolvere</summary>
      <p class="mut" style="font-size:13px;margin:6px 0 0">${esc(p.spiegazione)}</p><p class="fix" style="font-size:13px">${esc(p.soluzione)}</p></details>
    </div>`).join("");
}
/* icone della Panoramica */
const HI = {
  cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5" rx="1"/><path d="M9 2.5V6M15 2.5V6M9 18v3.5M15 18v3.5M2.5 9H6M2.5 15H6M18 9h3.5M18 15h3.5"/>',
  gpu: '<rect x="2" y="6" width="20" height="11" rx="2"/><circle cx="9" cy="11.5" r="2.8"/><path d="M15 9.5h4M15 13.5h4M5 17v2"/>',
  ram: '<rect x="2.5" y="7" width="19" height="10" rx="1.5"/><path d="M6 17v3M10 17v3M14 17v3M18 17v3"/><rect x="6" y="10" width="4" height="4" rx=".5"/><rect x="14" y="10" width="4" height="4" rx=".5"/>',
  temp: '<path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0z"/><path d="M12 9v7"/>',
  disk: '<rect x="3" y="13" width="18" height="7" rx="2"/><path d="M5 13l2.5-8h9l2.5 8"/><path d="M7 16.5h.01M10.5 16.5h.01"/>',
  win: '<rect x="3" y="3" width="8" height="8" rx="1"/><rect x="13" y="3" width="8" height="8" rx="1"/><rect x="3" y="13" width="8" height="8" rx="1"/><rect x="13" y="13" width="8" height="8" rx="1"/>',
  play: '<path d="M8 5v14l11-7z"/>', scan: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  wrench: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 7.9l-6.9 6.9a2.1 2.1 0 0 1-3-3l6.9-6.9a6 6 0 0 1 7.9-7.9z"/>',
  arch: '<rect x="3" y="4" width="18" height="5" rx="1"/><path d="M5 9v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9"/><path d="M10 13h4"/>',
  rec: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/>', check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  warn: '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17h.01"/>', power: '<path d="M12 3v9"/><path d="M6.3 6.3a8 8 0 1 0 11.4 0"/>',
  tune: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
};
const hsv = (k) => `<svg viewBox="0 0 24 24">${HI[k]}</svg>`;
const ACT_IC = { gamemode: ["play", "#2ee59d"], backup: ["arch", "#00d4ff"], tweaks: ["tune", "#a78bfa"], analisi: ["rec", "#ff5c7a"], fixpc: ["wrench", "#ff8a5c"] };
function quando(t) {
  const d = new Date(t * 1000), now = new Date();
  const hm = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  const day = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diff = Math.round((day(now) - day(d)) / 86400000);
  return diff === 0 ? "oggi, " + hm : diff === 1 ? "ieri, " + hm : `${d.getDate()} ${MESI[d.getMonth()]}`;
}
function heroGmHtml(gm) {
  if (!gm) return "";
  let st, k, t, sub;
  if (!gm.enabled) { st = "off"; k = "Spenta"; t = "Spenta"; sub = "Accendila: si attiva da sola quando apri un gioco"; }
  else if (!gm.running) { st = "warn"; t = "Non in esecuzione"; sub = "Apri la pagina Game mode per riavviarla"; }
  else if (gm.active) { st = "on"; t = esc((gm.games || []).join(", ")); sub = "Attiva: il PC lavora per il gioco"; }
  else { st = "ready"; t = "Pronta"; sub = `Si attiva da sola quando apri uno dei tuoi ${gm.n_games} giochi`; }
  return `<div class="hm-gm ${st}"><div class="hm-gmh" data-go="gamemode"><span class="dot"></span>Game mode</div><b data-go="gamemode">${t}</b><small>${sub}</small>
    ${gm.active ? '<a class="hm-ver" id="home-gm-ver">Verifica ottimizzazioni</a>' : ""}
    <button class="hm-pw" id="home-gm-pw" title="${gm.enabled ? "Spegni la game mode" : "Accendi la game mode"}">${hsv("power")}</button></div>`;
}
async function home() {
  await refreshState(); await loadCatalog();
  const si = S.state.sysinfo || {}, g = si.gpu || {};
  const fixN = toFix().length, probs = S.state.problems || [];
  const score = pcScore(fixN, probs), st = scoreText(score, fixN, probs);
  const H = S.homeData || {};
  const ok = !fixN && !probs.some((p) => p.gravita >= 2);
  const sub = [st.text.replace(/<br>/g, " ").replace(/\.\s*$/, ""), `${S.state.applied} ottimizzazion${S.state.applied === 1 ? "e" : "i"} di LagDoctor attive`,
    H.last_backup ? "ultimo backup " + dataIt(H.last_backup).replace(/^(\d+ \w+) \d{4},/, "$1,") : ""].filter(Boolean).join(" · ");
  const hw = (ic, col, k, v) => v ? `<div class="hm-hw"><span class="ci" style="color:${col}">${hsv(ic)}</span><span class="k">${k}</span><b>${esc(v)}</b></div>` : "";
  main().innerHTML = `<h1>Panoramica</h1>
    ${S.state.experiment ? `<div class="banner"><b>Test prima/dopo in corso</b> su ${esc(S.state.experiment.gioco)}: quando sei pronto registra la partita DOPO. <button class="sm" data-go="exp">Vai</button></div>` : ""}
    ${!S.state.admin ? '<div class="banner">LagDoctor non ha i permessi di amministratore: avvialo di nuovo e rispondi Si.</div>' : ""}
    <div class="hm-hero ${S.booting ? "" : ok ? "good" : score >= 45 ? "mid" : "low"}">
      ${S.booting ? `<div class="hm-boot">${bootCardHtml()}</div>` : `
      <div class="hm-ring"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="52" class="bg"/><circle cx="60" cy="60" r="52" class="fg" stroke-dasharray="326.7" stroke-dashoffset="${(326.7 * (1 - score / 100)).toFixed(1)}"/></svg><div><b>${score}</b><small>su 100</small></div></div>
      <div class="hm-hs"><div class="hm-k">${hsv(ok ? "check" : "warn")}${ok ? "Tutto a posto" : "Da sistemare"}</div>
        <div class="hm-t1">${st.title}</div><div class="hm-s">${sub}</div>
        <div class="hm-btns">${fixN ? `<button data-go="tweaks">${hsv("tune")}Correggi ora</button>` : ""}<button class="${fixN ? "ghost" : ""}" data-go="scan">${hsv("scan")}Scansione completa</button>
          ${fixN ? "" : `<button class="ghost" data-go="record">${hsv("rec")}Analizza un gioco</button>`}</div></div>`}
      ${heroGmHtml(S.state.gm)}
    </div>
    ${probs.length && !S.booting ? `<div class="hm-sec"><h2>Da sistemare</h2>${probs.length > 3 ? `<a class="hm-more" id="hm-more">${S.homeAllProbs ? "Mostra meno" : `Mostra tutti (${probs.length})`}</a>` : ""}</div>
      <div class="hm-probs">${quickHtml(S.homeAllProbs ? probs : probs.slice().sort((a, b) => b.gravita - a.gravita).slice(0, 3))}</div>` : ""}
    <div class="hm-sec"><h2>Adesso</h2><span class="mut">ultimi 60 secondi</span></div>
    <div class="hm-ms" id="home-sensors"></div>
    <div class="hm-cols">
      <div><div class="hm-sec"><h2>Il tuo PC</h2></div>
        ${hw("cpu", "#7c5cff", "Processore", si.cpu || "?")}
        ${hw("gpu", g.vendor === "amd" ? "#ff5c5c" : g.vendor === "nvidia" ? "#76b900" : "#38bdf8", "Scheda video", (g.name || "?") + (g.vram_mb && !g.integrated ? " · " + Math.round(g.vram_mb / 1024) + " GB" : ""))}
        ${hw("ram", "#ffb547", "RAM", si.ram || "?")}
        ${hw("disk", "#a78bfa", "Disco di sistema", H.disk ? `${H.disk.drive} · ${H.disk.total_gb} GB · ${H.disk.free_gb} GB liberi` : "")}
        ${hw("win", "#38bdf8", "Windows", H.windows || "")}
      </div>
      <div><div class="hm-sec"><h2>Attivita' recenti</h2></div><div id="home-act">${actHtml(H.activity)}</div></div>
    </div>`;
  $$("[data-go]").forEach((b) => b.addEventListener("click", () => { if (b.dataset.go === "tweaks") { S.filter = "fix"; S.twCat = ""; } if (b.dataset.go === "record") S.recTab = "rec"; go(b.dataset.go); }));
  bindFixButtons(main());
  bindActs();
  const more = $("#hm-more"); if (more) more.onclick = () => { S.homeAllProbs = !S.homeAllProbs; home(); };
  const hv = $("#home-gm-ver"); if (hv) { S.gmGames = ((S.state.gm || {}).games || []).join(", "); hv.onclick = gmVerifyDialog; }
  const pw = $("#home-gm-pw");
  if (pw) pw.onclick = async () => {
    const on = (S.state.gm || {}).enabled; pw.disabled = true;
    if (on) toast("Spengo la game mode e rimetto tutto com'era...");
    try { const x = await api("/api/gamemode", { action: on ? "disable" : "enable" }); toast((x && x.msg) || (on ? "Game mode spenta" : "Game mode accesa")); }
    catch (e) { toast("Errore: " + e.message); }
    if (S.page === "home") home();
  };
  startSensors($("#home-sensors"));
  /* dati in piu' (attivita', backup, disco, Windows): arrivano dopo, senza rallentare l'apertura della pagina */
  if (!S.homeLoading) {
    S.homeLoading = true;
    api("/api/home").then((d) => {
      const changed = JSON.stringify(d) !== JSON.stringify(S.homeData || {});
      S.homeData = d; S.homeLoading = false;
      if (changed && S.page === "home" && $("#home-sensors") && $("#modal").hidden) home();
    }).catch(() => { S.homeLoading = false; });
  }
}
function actHtml(list) {
  if (!list) return '<div class="mut" style="padding:8px 0">...</div>';
  if (!list.length) return '<div class="mut" style="padding:8px 0">Ancora niente: qui compariranno partite con la game mode, backup, modifiche e analisi.</div>';
  return list.map((a, i) => {
    const ic = ACT_IC[a.kind] || ["check", "#94a3b8"];
    const txt = esc(a.text).replace(/«(.*?)»/g, "<b>$1</b>");
    return `<div class="hm-a ${a.link ? "link" : ""}" data-act="${i}"><span class="hm-ti" style="color:${ic[1]};background:${ic[1]}1f">${hsv(ic[0])}</span><div class="grow">${txt}</div><small>${quando(a.t)}</small></div>`;
  }).join("");
}
function bindActs() {
  const list = (S.homeData || {}).activity || [];
  $$("#home-act [data-act]").forEach((el) => el.onclick = () => {
    const a = list[Number(el.dataset.act)]; if (!a || !a.link) return;
    if (a.link === "record") S.recTab = "sessions";
    if (a.link === "tweaks") { S.filter = "all"; S.twCat = ""; }
    go(a.link);
  });
}

/* sensori della Panoramica: valore, dettaglio e grafico degli ultimi 60 secondi */
const SENSOR_MAIN = [
  ["cpu_util", "cpu", "#7c5cff", "Processore", "s", (d) => fmt(d.cpu_util) + "%", (d) => d.cpu_ghz ? fmt(d.cpu_ghz, 1).replace(".", ",") + " GHz" : "", 100],
  ["gpu_util", "gpu", "#00d4ff", "Scheda video", "g", (d) => fmt(d.gpu_util) + "%",
    (d) => [d.gpu_clock != null ? fmt(d.gpu_clock) + " MHz" : "", d.gpu_power != null ? fmt(d.gpu_power) + " W" : ""].filter(Boolean).join(" · "), 100],
  ["gpu_temp", "temp", "#2ee59d", "Temperatura GPU", "g", (d) => fmt(d.gpu_temp) + " °C", (d) => d.gpu_hotspot != null ? "hotspot " + fmt(d.gpu_hotspot) + " °C" : "", 95],
  ["ram_pct", "ram", "#ffb547", "Memoria", "s", (d) => fmt(d.ram_pct) + "%", (d) => `${fmt(d.ram_used, 1).replace(".", ",")} GB su ${fmt(d.ram_total, 0)} GB`, 100],
];
function sparkSvg(pts, col, max) {
  const w = 220, h = 44, n = 60;
  if (!pts.length) return "";
  const xs = (i) => ((i + n - pts.length) / (n - 1)) * w;
  const ys = (v) => h - 3 - Math.max(0, Math.min(1, v / max)) * (h - 8);
  const line = pts.map((v, i) => `${xs(i).toFixed(1)},${ys(v).toFixed(1)}`).join(" ");
  const id = "sg" + col.slice(1);
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><defs><linearGradient id="${id}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${col}" stop-opacity=".35"/><stop offset="1" stop-color="${col}" stop-opacity="0"/></linearGradient></defs>
    <polygon points="${xs(0).toFixed(1)},${h} ${line} ${w},${h}" fill="url(#${id})"/><polyline points="${line}" fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round" vector-effect="non-scaling-stroke"/></svg>`;
}
function startSensors(box) {
  S.sensHist = S.sensHist || {};
  box.innerHTML = SENSOR_MAIN.map(([k, ic, col, label]) => `<div class="hm-m"><div class="hm-mh"><span class="ci" style="color:${col}">${hsv(ic)}</span>${label}</div>
    <div class="hm-v" id="s-${k}">–</div><div class="hm-sub" id="n-${k}">&nbsp;</div><div class="hm-sp" id="g-${k}">${sparkSvg(S.sensHist[k] || [], col, SENSOR_MAIN.find((x) => x[0] === k)[7])}</div></div>`).join("");
  const flags = document.createElement("div"); flags.className = "sens-flags"; box.after(flags);
  const tick = async () => {
    if (!document.body.contains(box)) return clearInterval(S.sensorTimer);
    try {
      const r = await api("/api/sensors");
      const gd = r.available ? (r.data || {}) : {}, sd = r.sys || {};
      SENSOR_MAIN.forEach(([k, , col, , src, val, note, max]) => {
        const d = src === "g" ? gd : sd, el = $("#s-" + k), n = $("#n-" + k), gr = $("#g-" + k);
        if (!el) return;
        const v = d[k];
        el.innerHTML = v == null ? "–" : val(d);
        n.innerHTML = v == null ? (src === "g" && !r.available && k === "gpu_util" ? "sensori non leggibili" : "&nbsp;") : (esc(note(d)) || "&nbsp;");
        if (v != null) { const h = (S.sensHist[k] = (S.sensHist[k] || []).concat([v]).slice(-60)); gr.innerHTML = sparkSvg(h, col, k === "gpu_temp" ? Math.max(max, ...h) : max); }
      });
      flags.innerHTML = (gd.thr_thermal ? '<span class="badge b-bad">GPU: throttling termico</span>' : "") + (gd.thr_power ? '<span class="badge b-warn">GPU al limite di potenza</span>' : "");
    } catch (e) { /* ignora */ }
  };
  clearInterval(S.sensorTimer); tick(); S.sensorTimer = setInterval(tick, 1000);
}

/* ------------------------------------------------------------------ SCANSIONE */
function scan() {
  const r = S.lastScan;
  main().innerHTML = `
    <button class="ghost sm" id="back-home" style="margin-bottom:14px">← Panoramica</button>
    <h1>Scansione completa</h1><p class="sub">Hardware, Windows, driver, dischi, rete, errori degli ultimi 30 giorni e lo stato di ogni impostazione. Richiede 1-2 minuti.</p>
    ${bootCardHtml()}
    <div class="row"><button id="go-scan" ${S.booting ? 'disabled title="Aspetta la fine della scansione delle impostazioni"' : ""}>${r ? "Ripeti scansione" : "Avvia scansione"}</button>${r ? `<button class="ghost" id="open-rep">Apri il report completo</button>` : ""}</div>
    <ul class="log" id="scan-log"></ul><div id="scan-out"></div>`;
  $("#back-home").onclick = () => go("home");
  $("#go-scan").onclick = async () => {
    $("#go-scan").disabled = true; $("#scan-out").innerHTML = '<div class="spinner"></div>';
    try {
      const job = await runJob(api("/api/scan", {}), (j) => logList($("#scan-log"), j.messages));
      S.lastScan = job.result; await loadCatalog(true); scan();
    } catch (e) { toast("Errore: " + e.message); $("#go-scan").disabled = false; $("#scan-out").innerHTML = ""; }
  };
  if (!r) return;
  $("#open-rep").onclick = () => window.open(reportUrl(r.report), "_blank");
  const s = r.summary, er = s.errors || {};
  const disp = (s.displays || []).map((d) => `${d.width}x${d.height} @ ${d.hz} Hz (max ${d.max_hz})`).join("<br>") || "?";
  const disks = (s.disks || []).map((d) => `${esc(d.name)} · ${esc(d.health)}${d.temp ? " · " + d.temp + "°C" : ""}`).join("<br>") || "?";
  const net = (s.net || []).map((n) => `${esc(n.InterfaceDescription)} · ${esc(n.LinkSpeed)}`).join("<br>") || "?";
  const fixN = toFix().length, avail = notActive().length;
  $("#scan-out").innerHTML = `
    <div class="grid">
      <div class="card kpi"><small>Windows</small><b>${esc(s.windows)}</b><span class="mut">acceso da ${fmt(s.uptime_h)} ore</span></div>
      <div class="card kpi"><small>Processore</small><b>${esc(s.cpu)}</b></div>
      <div class="card kpi"><small>Scheda video</small><b>${esc(s.gpu)}</b><span class="mut">${s.vram || "?"} MB</span></div>
      <div class="card kpi"><small>RAM</small><b>${esc(s.ram)}</b></div>
      <div class="card kpi"><small>Schermi</small><b style="font-size:13px">${disp}</b></div>
      <div class="card kpi"><small>Dischi</small><b style="font-size:13px">${disks}</b></div>
      <div class="card kpi"><small>Rete</small><b style="font-size:13px">${net}</b></div>
      <div class="card kpi"><small>Errori 30 giorni</small><b style="font-size:13px">Hardware ${er.ev_whea ?? "?"} · Driver video ${er.ev_tdr ?? "?"}<br>Schermate blu ${er.ev_bsod ?? "?"} · Spegnimenti ${er.ev_kp41 ?? "?"}</b></div>
      <div class="card kpi"><small>Software</small><b style="font-size:13px">${s.apps} programmi · ${s.startup} all'avvio · ${s.services} servizi</b></div>
    </div>
    <h2>Impostazioni</h2>
    <div class="grid">
      <div class="card"><b style="font-size:24px;color:${fixN ? "var(--bad)" : "var(--ok)"}">${fixN}</b><p class="mut">impostazioni attuali che ti tolgono prestazioni</p><button id="to-fix" ${fixN ? "" : "disabled"}>Correggi</button></div>
      <div class="card"><b style="font-size:24px">${avail}</b><p class="mut">ottimizzazioni non ancora attive</p><button class="ghost" id="to-avail">Scegli</button></div>
      <div class="card"><b style="font-size:24px">${s.startup}</b><p class="mut">programmi che partono con Windows</p><button class="ghost" data-go2="startup">Gestisci</button></div>
    </div>
    <h2>Problemi trovati (${r.problems.length})</h2>${probHtml(r.problems)}`;
  $("#to-fix").onclick = () => { S.filter = "fix"; S.twCat = ""; go("tweaks"); };
  $("#to-avail").onclick = () => { S.filter = "off"; S.twCat = ""; go("tweaks"); };
  $$("[data-go2]").forEach((b) => (b.onclick = () => go(b.dataset.go2)));
  bindFixButtons($("#scan-out"));
}

/* ------------------------------------------------------------------ OTTIMIZZAZIONI */
const EFF = { alta: 0, media: 1, bassa: 2, comfort: 3, dubbia: 4, sconsigliata: 5 };
const tws = () => (S.catalog ? S.catalog.tweaks : []);
/* voci che l'utente ha deciso di ignorare: compaiono solo in "Ignorate" e non contano nel punteggio */
const twsActive = () => tws().filter((t) => !t.ignored);
const ignoredList = () => tws().filter((t) => t.ignored);
/* attiva = gia' impostata (da Windows, da te o da LagDoctor) */
const isOn = (t) => t.applied || t.status === true;
function toFix() {
  const list = twsActive().filter((t) => !t.applied && (
    (t.status === false && ((t.kind === "fix" && t.recommended !== false) || t.harm_if_off)) ||
    (t.kind === "myth" && t.status === true)));
  /* mito attivo + sua correzione = stesso problema: tengo solo il mito (che si disattiva) */
  const mythGroups = new Set(list.filter((t) => t.kind === "myth" && t.group).map((t) => t.group));
  return list.filter((t) => t.kind === "myth" || !(t.group && mythGroups.has(t.group)));
}
function notActive() {
  const fx = new Set(toFix().map((t) => t.id)), groups = new Set(toFix().map((t) => t.group).filter(Boolean));
  return twsActive().filter((t) => !fx.has(t.id) && !isOn(t) && t.kind !== "fix" && t.kind !== "myth" && !t.manual && !(t.group && groups.has(t.group)));
}
function statusBadge(t) {
  if (t.applied) return t.kind === "myth" ? '<span class="badge b-bad">attivata da LagDoctor</span>' : `<span class="badge b-acc">${(t.pol || 1) > 0 ? "accesa" : "spenta"} da LagDoctor</span>`;
  if (S.booting && t.status == null) return '<span class="badge">in lettura...</span>';
  if (t.kind === "myth") return t.status === true ? '<span class="badge b-bad">ATTIVA: da disattivare</span>' : t.status === false ? '<span class="badge b-ok">disattivata</span>' : '<span class="badge">non verificabile</span>';
  if (t.status === true) { const w = (t.pol || 1) > 0 ? "gia' accesa" : "gia' spenta"; return t.note ? `<span class="badge b-ok" title="${esc(t.note)}">${w} (altro programma)</span>` : `<span class="badge b-ok">${w}</span>`; }
  if (t.status === false) return t.kind === "fix" || t.harm_if_off ? '<span class="badge b-bad">da correggere</span>' : "";
  if (S.booting && t.status == null) return '<span class="badge">in lettura...</span>';
  if (t.note) return '<span class="badge">' + esc(t.note) + '</span>';
  return '<span class="badge">non verificabile</span>';
}
const riskCls = ["b-ok", "b-acc", "b-warn", "b-bad"];
const effCls = { alta: "b-ok", media: "b-ok", bassa: "", comfort: "", dubbia: "b-warn", sconsigliata: "b-bad" };
/* si puo' spuntare solo cio' che non e' gia' attivo */
const selectable = (t) => t.kind === "overlay" ? (!t.ignored && !t.manual && !t.applied && (!isOn(t) || (t.running && t.running.length > 0)))
  : !isOn(t) && !t.ignored && !t.manual;
const OV_CAT = "Overlays";

/* icone delle categorie di Ottimizzazioni: [colore, disegno] */
const CAT_IC = {
  "": ["#a0a8c8", '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/>'],
  "Correzioni (impostazioni che tolgono prestazioni)": ["#38bdf8", '<path d="M3 12h4l2-5 4 10 2-5h6"/>'],
  "CPU ed energia": ["#ffb547", '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>'],
  "Memoria e disco": ["#a78bfa", '<rect x="2.5" y="7" width="19" height="10" rx="1.5"/><path d="M6 17v3M10 17v3M14 17v3M18 17v3"/><rect x="6" y="10" width="4" height="4" rx=".5"/><rect x="14" y="10" width="4" height="4" rx=".5"/>'],
  "Rete": ["#00d4ff", '<path d="M2 8.5a15 15 0 0 1 20 0"/><path d="M5 12a10 10 0 0 1 14 0"/><path d="M8.5 15.5a5 5 0 0 1 7 0"/><circle cx="12" cy="19" r="1"/>'],
  "Gioco": ["#2ee59d", '<path d="M6 8h12a4 4 0 0 1 4 4v1.5a3.5 3.5 0 0 1-6.3 2.1L14.5 14h-5l-1.2 1.6A3.5 3.5 0 0 1 2 13.5V12a4 4 0 0 1 4-4z"/><path d="M7 10.5v3M5.5 12h3M16 11h.01M18 13h.01"/>'],
  "Interfaccia e input": ["#7c5cff", '<rect x="6" y="3" width="12" height="18" rx="6"/><path d="M12 7v4"/>'],
  "Debloat (app preinstallate)": ["#ff8a5c", '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>'],
  "Sicurezza (PERICOLOSE)": ["#ff5c7a", '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z"/><path d="M12 8v5M12 16h.01"/>'],
  "Overlays": ["#f472b6", '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>'],
  "Driver NVIDIA": ["#76b900", '<rect x="2" y="6" width="20" height="11" rx="2"/><circle cx="9" cy="11.5" r="2.8"/><path d="M15 9.5h4M15 13.5h4M5 17v2"/>'],
  "Driver AMD": ["#ff5c5c", '<rect x="2" y="6" width="20" height="11" rx="2"/><circle cx="9" cy="11.5" r="2.8"/><path d="M15 9.5h4M15 13.5h4M5 17v2"/>'],
};
const catIcon = (k) => { const i = CAT_IC[k]; return i ? `<span class="ci" style="color:${i[0]}"><svg viewBox="0 0 24 24">${i[1]}</svg></span>` : ""; };
/* nomi delle categorie senza le parentesi (la spiegazione e' nelle voci) */
const CAT_NAMES = { "Correzioni (impostazioni che tolgono prestazioni)": "Correzioni", "Sicurezza (PERICOLOSE)": "Sicurezza", "Debloat (app preinstallate)": "App preinstallate" };
const catName = (c) => CAT_NAMES[c] || c;
async function tweaksPage() {
  main().innerHTML = '<div class="loading"><div class="spinner"></div><p>Carico le impostazioni...</p></div>';
  await loadCatalog();
  if (!S.catalog.checked) {
    await runJob(api("/api/check", {})).catch(() => {});
    await loadCatalog(true);
  }
  if (S.catFilter) { S.twCat = S.catFilter; S.catFilter = null; }
  if (S.twCat === undefined) S.twCat = "";
  S.ovLoaded = false; S.ovLive = null;
  main().innerHTML = `
    <div class="row opt-head"><div><h1 style="margin-bottom:4px">Ottimizzazioni</h1><p class="sub" id="opt-sub" style="margin:0"></p></div><span class="grow"></span>
      <div class="seg" id="filters">
        <a data-f="fix">Da correggere</a><a data-f="all">Tutte</a><a data-f="rec">Consigliate</a><a data-f="off">Non applicate</a><a data-f="on">Applicate</a><a data-f="ign">Ignorate</a>
      </div></div>
    <div class="opt-wrap"><div class="cats" id="cats"></div>
      <div class="panel">
        <div class="row" style="align-items:flex-start"><div><h2 id="pan-t"></h2><div class="mut" id="pan-s" style="font-size:13px"></div></div><span class="grow"></span>
          <input type="search" id="q" placeholder="Cerca..." style="width:190px"></div>
        <div class="row opt-tools">
          <button class="ghost sm" id="sel-rec">Seleziona consigliate</button>
          <button class="ghost sm" id="sel-none">Deseleziona</button>
          <span class="grow"></span>
          <button class="ghost sm" id="recheck">Ricontrolla stato</button>
        </div>
        <div id="tw-list"></div>
        <details style="margin-top:18px"><summary>Da fare a mano: impostazioni utili che nessun programma puo' cambiare dall'esterno (${S.catalog.manual.length})</summary>
          ${S.catalog.manual.map((m) => `<div class="card" style="margin-bottom:6px"><b>${esc(m.name)}</b><p style="margin:4px 0">${esc(m.how)}</p><span class="mut" style="font-size:12px">Fonte: ${esc(m.source)}</span></div>`).join("")}
        </details>
      </div></div>
    <div class="bar"><span id="sel-count" class="grow mut">Nessuna voce selezionata</span>
      <button class="ghost" id="undo-btn">Annulla modifiche...</button><button id="apply-btn" disabled>Applica</button></div>`;
  $$("#filters a").forEach((c) => c.addEventListener("click", () => {
    if (S.filter === c.dataset.f) return;
    swapTweaks(() => {
      S.filter = c.dataset.f;
      if (S.twCat && !filtered().some((t) => t.cat === S.twCat)) S.twCat = "";  /* categoria vuota con questo filtro: mostro tutto */
    });
  }));
  $("#q").addEventListener("input", renderTweaks);
  $("#sel-rec").onclick = () => { visible().forEach((t) => { if (t.kind !== "myth" && (t.recommended || t.kind === "fix" || t.harm_if_off) && selectable(t)) S.sel.add(t.id); }); renderTweaks(); };
  $("#sel-none").onclick = () => { S.sel.clear(); renderTweaks(); };
  $("#recheck").onclick = async () => { $("#recheck").disabled = true; toast("Ricontrollo lo stato di tutte le impostazioni..."); await runJob(api("/api/check", {})).catch((e) => toast(e.message)); await loadCatalog(true); tweaksPage(); };
  $("#apply-btn").onclick = applySelected;
  $("#undo-btn").onclick = undoDialog;
  renderTweaks();
}
/* voci che passano il filtro in alto e la ricerca (senza guardare la categoria) */
function filtered() {
  const q = ($("#q")?.value || "").toLowerCase();
  const fx = new Set(toFix().map((t) => t.id)), na = new Set(notActive().map((t) => t.id));
  return tws().filter((t) => {
    if (S.filter === "ign") { if (!t.ignored) return false; }
    else if (t.ignored) return false;
    if (S.filter === "fix" && !fx.has(t.id)) return false;
    if (S.filter === "off" && !na.has(t.id)) return false;
    if (S.filter === "rec" && !(t.recommended && !isOn(t)) && !fx.has(t.id)) return false;
    if (S.filter === "on" && !(isOn(t) && t.kind !== "myth")) return false;
    if (S.filter === "myth" && t.kind !== "myth") return false;
    if (q && !(t.name + " " + (t.label || "") + " " + (t.tech || "") + " " + t.desc).toLowerCase().includes(q)) return false;
    return true;
  });
}
function visible() {
  return filtered().filter((t) => !S.twCat || t.cat === S.twCat);
}
/* dettagli di una voce: finestrella sopra la pagina (che si scurisce un po') */
function docModal(t) {
  if (!t) return;
  const d = t.doc || { cosa: t.desc, perche: "", problemi: "" };
  const myth = t.kind === "myth";
  const body = [d.cosa, d.perche].filter((x) => x && x !== t.sum).join(" ");
  const prob = d.problemi && !/^nessuno/i.test(d.problemi.trim()) ? d.problemi : "";
  const m = modal(`<div class="hd"><div style="flex:1"><h2>${esc(t.label || t.name)}</h2>${t.tech ? `<div class="tech">${esc(t.tech)}</div>` : ""}</div><button class="x" id="m-close" title="Chiudi">&times;</button></div>
    <p class="sum">${esc(t.sum || t.desc || "")}</p>
    ${body ? `<p>${esc(body)}</p>` : ""}
    ${t.how_ld ? `<p><b>Se lo spegni da LagDoctor:</b> ${esc(t.how_ld)}</p>` : ""}
    ${t.how ? `<p><b>${t.manual ? "Come spegnerlo" : "Oppure dal programma"}:</b> ${esc(t.how)}</p>` : ""}
    ${prob ? `<p class="warn"><b>${myth ? "Perche' e' meglio lasciarla disattivata" : "Possibili problemi"}:</b> ${esc(prob)}</p>` : ""}
    ${t.warning && t.cat !== OV_CAT ? `<p class="warn"><b>Attenzione:</b> ${esc(t.warning)}</p>` : ""}`);
  m.classList.add("doc3"); $("#modal").classList.add("soft");
  $("#m-close", m).onclick = closeModal;
}
function docHtml(t) {
  const d = t.doc || { cosa: t.desc, perche: "", problemi: "" };
  const myth = t.kind === "myth";
  /* Overlays: la descrizione breve non sta sotto il nome ma qui, in cima ai dettagli */
  const lead = t.cat === OV_CAT && t.desc && t.desc !== d.cosa ? `<p class="lead">${esc(t.desc)}</p>` : "";
  return `<div class="more doc">${lead}
    <div><h4>${myth ? "Cosa fa" : "A cosa serve questa impostazione"}</h4><p>${esc(d.cosa)}</p></div>
    <div><h4 class="ok">${myth ? "Quando potrebbe aiutare" : "Perche' cambiarla"}</h4><p>${esc(d.perche || t.desc)}</p></div>
    <div><h4 class="bad">${myth ? "Perche' e' meglio lasciarla disattivata" : "Possibili problemi"}</h4><p>${esc(d.problemi || "Nessuno noto.")}</p></div>
    ${t.how_ld ? `<div class="how"><h4>Se lo spegni da LagDoctor</h4><p>${esc(t.how_ld)}</p></div>` : ""}
    ${t.how ? `<div class="how"><h4>${t.manual ? "Come spegnerlo" : "Oppure dal programma"}</h4><p>${esc(t.how)}</p></div>` : ""}
    ${t.warning && t.cat !== OV_CAT ? `<div class="w">Attenzione: ${esc(t.warning)}</div>` : ""}
    <div class="mut src">Efficacia ${esc(t.efficacy)} · rischio ${esc(t.risk_label)}${t.reboot ? " · serve il riavvio" : ""}${t.source ? " · fonte: " + esc(t.source) : ""}</div>
  </div>`;
}
function actionHtml(t) {
  if (t.ignored) return `<button class="ghost sm" data-unign="${t.id}" title="Torna tra ${t.recommended === true ? "le consigliate" : "le altre voci"}">Non ignorare</button>`;
  if (t.needs_path && t.applied && t.status === false) return `<button class="ghost sm" data-addpath="${t.id}" title="Alcuni giochi non sono ancora esclusi (es. installati dopo o su un altro disco)">Aggiungi cartelle</button>`;
  return !t.applied && (!isOn(t) || t.kind === "myth") ? `<button class="ghost sm ign-btn" data-ign="${t.id}" title="Non mostrarla piu' tra quelle da fare: non conta nel punteggio">Ignora</button>` : "";
}
async function setIgnored(id, ignore) {
  const t = tws().find((x) => x.id === id);
  try {
    await api("/api/ignore", { id, ignore });
    if (t) t.ignored = ignore;
    S.sel.delete(id);
    toast(ignore ? "Ignorata: la trovi in \"Ignorate\"" : (t && t.recommended === true ? "Rimessa tra le consigliate" : "Rimessa tra le voci normali"));
    const n = toFix().length; $("#nav-fix").hidden = !n; $("#nav-fix").textContent = n;
    refreshState().catch(() => {});
    renderTweaks();
  } catch (e) { toast("Errore: " + e.message); }
}
/* pallini dell'effetto e rischio colorato */
const EFF_DOTS = { alta: 3, media: 2, bassa: 1, comfort: 1, dubbia: 0, sconsigliata: 0 };
const EFF_WORD = { alta: "effetto alto", media: "effetto medio", bassa: "effetto basso", comfort: "comodita'", dubbia: "effetto dubbio", sconsigliata: "sconsigliata" };
const RISK_CLS = ["s", "m", "r", "p"];
function dotsHtml(t) {
  const n = EFF_DOTS[t.efficacy] ?? 0;
  const lab = t.efficacy === "dubbia" ? "dubbio" : t.efficacy === "sconsigliata" ? "sconsigl." : t.efficacy === "comfort" ? "comodita'" : "effetto";
  return `<span class="dots" title="${EFF_WORD[t.efficacy] || esc(t.efficacy)}">${[0, 1, 2].map((k) => `<i${k < n ? ' class="f"' : ""}></i>`).join("")}<em>${lab}</em></span>`;
}
function stateHtml(t) {
  if (t.kind === "overlay") {
    if (S.sel.has(t.id)) return '<span class="badge b-acc">da spegnere</span>';
    if (t.applied && !(t.running && t.running.length)) return '<span class="badge b-ok" title="LagDoctor lo tiene spento anche dopo il riavvio">spento da LagDoctor</span>';
    if (S.booting && t.status == null) return '<span class="badge">in lettura...</span>';
    if (t.running && t.running.length) return '<span class="badge b-warn" title="in esecuzione adesso">attivo ora</span>';
    if (t.status === false) return '<span class="badge b-warn">acceso</span>';
    if (t.status === true) return '<span class="badge b-ok">spento</span>';
    return '<span class="badge" title="LagDoctor non riesce a leggere questa impostazione">da controllare</span>';
  }
  if (S.sel.has(t.id)) return `<span class="badge b-acc">${(t.pol || 1) > 0 ? "da accendere" : "da spegnere"}</span>`;
  if (t.applied || t.kind === "myth" || t.status === true) return statusBadge(t);
  if (S.booting && t.status == null) return '<span class="badge">in lettura...</span>';
  if (t.status === false && (t.kind === "fix" || t.harm_if_off) && !t.ignored) return '<span class="badge b-bad">da correggere</span>';
  if (t.recommended === true && !t.ignored) return `<span class="badge b-acc">${(t.pol || 1) > 0 ? "meglio accesa" : "meglio spenta"}</span>`;
  if (t.status == null) return statusBadge(t);
  return "";
}
function switchHtml(t) {
  if (t.manual) return `<button class="ghost sm how-btn" data-how="${t.id}" title="Si spegne dal programma: ti dico dove">Come spegnerlo</button>`;
  if (t.kind === "overlay") return ovSwitchHtml(t);
  const applied = isOn(t) || S.sel.has(t.id), on = (t.pol || 1) > 0 ? applied : !applied;  /* acceso = la cosa e' attiva sul PC */
  let tip = "", dis = false;
  if (t.ignored) { dis = true; tip = "Voce ignorata"; }
  else if (t.applied) tip = t.kind === "myth" ? "Disattiva" : "Annulla la modifica di LagDoctor";
  else if (t.kind === "myth" && t.status === true) tip = "Disattiva";
  else if (isOn(t)) { dis = true; tip = "Gia' cosi' (impostata da Windows o da un altro programma)"; }
  else if (t.kind === "overlay") tip = S.sel.has(t.id) ? "Verra' spento quando premi Applica" : "Accendi per spegnere questo overlay (poi premi Applica)";
  else tip = S.sel.has(t.id) ? "Cambiata: premi Applica in basso" : ((t.pol || 1) > 0 ? "Accendi e premi Applica" : "Spegni e premi Applica");
  return `<label class="switch${S.sel.has(t.id) ? " pend" : ""}" title="${tip}"><input type="checkbox" data-sw="${t.id}" ${on ? "checked" : ""} ${dis ? "disabled" : ""}><span></span></label>`;
}
/* overlay: l'interruttore mostra l'OVERLAY (acceso = l'overlay e' acceso). Spegnendolo lo si seleziona per Applica. */
/* spento da LagDoctor = resta spento (lo tiene spento il guardiano anche se per un attimo si riapre) */
const ovOn = (t) => !t.applied && (!isOn(t) || (t.running && t.running.length > 0));
/* interruttore ACCESO = overlay SPENTO (come le altre ottimizzazioni: acceso = ottimizzazione attiva),
   chiunque l'abbia spento (LagDoctor o tu dal programma). Overlay acceso = interruttore spento, sempre libero. */
function ovSwitchHtml(t) {
  const pend = S.sel.has(t.id), on = ovOn(t) && !pend;  /* acceso = l'overlay e' attivo */
  let tip, dis = false;
  if (t.ignored) { dis = true; tip = "Voce ignorata"; }
  else if (pend) tip = "Verra' spento quando premi Applica (riaccendi l'interruttore per annullare)";
  else if (t.applied) tip = "Overlay spento da LagDoctor (resta spento): accendi l'interruttore per riaccenderlo";
  else if (!ovOn(t)) tip = "Overlay spento dal suo programma";
  else tip = "Overlay acceso: spegni l'interruttore e premi Applica per spegnerlo";
  return `<label class="switch${pend ? " pend" : ""}" title="${tip}"><input type="checkbox" data-sw="${t.id}" ${on ? "checked" : ""} ${dis ? "disabled" : ""}><span></span></label>`;
}
function rowHtml(t) {
  return `<div class="tw2 ${S.sel.has(t.id) ? "sel" : ""}" data-id="${t.id}">
    <div class="tx name"><b>${esc(t.label || t.name)}</b><div>${esc(t.short || t.desc || (t.doc && t.doc.cosa) || "")} ${actionHtml(t)}</div></div>
    <div class="right"><span class="stc">${stateHtml(t)}</span>${dotsHtml(t)}<span class="risk ${RISK_CLS[t.risk] || "m"}">${esc(t.risk_label)}</span>${switchHtml(t)}</div>
  </div>`;
}
function renderTweaks() {
  $$("#filters a").forEach((c) => c.classList.toggle("on", c.dataset.f === S.filter));
  [...S.sel].forEach((id) => { const t = tws().find((x) => x.id === id); if (!t || !selectable(t)) S.sel.delete(id); });
  const all = tws(), act = twsActive(), fx = new Set(toFix().map((t) => t.id)), fl = filtered();
  const order = [...new Set(all.map((t) => t.cat))];
  if (S.twCat && !order.includes(S.twCat)) S.twCat = "";
  const nOn = act.filter((t) => isOn(t) && t.kind !== "myth").length, nTot = act.filter((t) => t.kind !== "myth" || isOn(t)).length;
  $("#opt-sub").textContent = `${nOn} applicate su ${nTot}` + (fx.size ? ` · ${fx.size} da correggere` : "");
  const counts = { fix: fx.size, ign: ignoredList().length };
  $$("#filters a").forEach((c) => { const n = counts[c.dataset.f]; c.innerHTML = c.textContent.replace(/ \d+$/, "") + (n ? ` <small>${n}</small>` : ""); });
  /* categorie a sinistra */
  const catRow = (key, label, items) => {
    const tot = items.filter((t) => t.kind !== "myth" || isOn(t)).length || items.length;
    const on = items.filter((t) => isOn(t) && t.kind !== "myth").length;
    const myth = items.length && items.every((t) => t.kind === "myth");
    const warn = items.some((t) => fx.has(t.id));
    const n = key ? fl.filter((t) => t.cat === key).length : fl.length;
    const cnt = myth ? `${items.filter((t) => isOn(t)).length} attive` : `${on}/${tot}`;
    const pct = myth ? 0 : Math.round(100 * on / Math.max(tot, 1));
    return `<div class="cat ${S.twCat === key ? "on" : ""} ${n ? "" : "empty"}" data-cat="${esc(key)}"><div class="r">${warn ? '<span class="warn" title="ci sono voci da correggere"></span>' : ""}${catIcon(key)}<b>${esc(label)}</b><span class="c">${cnt}</span></div>
      <div class="p"><i style="width:${pct}%"></i></div></div>`;
  };
  $("#cats").innerHTML = catRow("", "Tutte le categorie", act) + order.map((c) => catRow(c, catName(c), act.filter((t) => t.cat === c))).join("");
  $$("#cats .cat").forEach((el) => el.addEventListener("click", () => { if (S.twCat === el.dataset.cat) return; if (el.dataset.cat === OV_CAT && S.twCat !== OV_CAT) S.ovLoaded = false; swapTweaks(() => { S.twCat = el.dataset.cat; }); }));
  /* pannello a destra */
  const list = visible();
  const fname = { fix: "da correggere", all: "", rec: "consigliate", off: "non attive", on: "attive", ign: "ignorate", myth: "non affidabili" }[S.filter] || "";
  $("#pan-t").textContent = S.twCat ? catName(S.twCat) : "Tutte le categorie";
  const scope = act.filter((t) => !S.twCat || t.cat === S.twCat);
  const sTot = scope.filter((t) => t.kind !== "myth" || isOn(t)).length;
  const allMyth = scope.length && scope.every((t) => t.kind === "myth");
  const ovs = S.twCat === OV_CAT ? scope.filter((t) => t.kind === "overlay") : [];
  if (ovs.length) {
    const acc = ovs.filter((t) => !t.applied && (t.status === false || (t.running && t.running.length))).length;
    const off = ovs.filter((t) => t.applied || (t.status === true && !(t.running && t.running.length))).length, unk = ovs.length - acc - off;
    $("#pan-s").textContent = `Overlay installati: ${acc} ${acc === 1 ? "acceso" : "accesi"}, ${off} ${off === 1 ? "spento" : "spenti"}` +
      (unk ? `, ${unk} da controllare` : "") + (fname ? ` · ${list.length} ${fname}` : "");
  } else $("#pan-s").textContent = (allMyth ? `${scope.length} voci · ${scope.filter(isOn).length} attive sul tuo PC` : `${scope.filter((t) => isOn(t) && t.kind !== "myth").length} applicate su ${sTot}`) + (fname ? ` · ${list.length} ${fname}` : "") +
    (S.twCat === "Sicurezza" ? " · voci pericolose: chiedono una conferma prima di essere applicate" : "");
  const groups = {};
  /* overlay: prima quelli che girano adesso, poi accesi, da controllare, spenti; poi le voci di Windows */
  const ovRank = (t) => t.kind !== "overlay" ? 4 : (t.running && t.running.length) ? 0 : t.status === false ? 1 : t.status == null ? 2 : 3;
  list.slice().sort((a, b) => (a.cat === OV_CAT && b.cat === OV_CAT ? ovRank(a) - ovRank(b) : 0) ||
    (b.recommended === true) - (a.recommended === true) || (EFF[a.efficacy] - EFF[b.efficacy]) || a.risk - b.risk)
    .forEach((t) => (groups[t.cat] = groups[t.cat] || []).push(t));
  const ignNote = S.filter === "ign" ? `<div class="myth-note" style="background:rgba(255,255,255,.04);border-color:var(--line2)">Voci che hai deciso di ignorare: non compaiono tra quelle da correggere o consigliate e <b>non contano nel punteggio</b> del PC. Con <b>Non ignorare</b> tornano al loro posto.</div>` : "";
  const multi = !S.twCat;
  const ovBox = S.twCat === OV_CAT ? overlayBox() : "";
  $("#tw-list").innerHTML = ovBox + ignNote + (list.length ? order.filter((c) => groups[c]).map((c) => `
    <div class="tw-group">${multi ? `<h3>${esc(catName(c))}</h3>` : ""}
    ${groups[c].map(rowHtml).join("")}
    </div>`).join("") : `<div class="empty">${S.filter === "ign" ? "Nessuna voce ignorata." : S.filter === "fix" ? "Niente da correggere qui." : "Nessuna voce con questi filtri."}</div>`);
  $$("#tw-list .tw2[data-id]").forEach((row) => {
    const id = row.dataset.id;
    $(".name", row).addEventListener("click", () => docModal(tws().find((x) => x.id === id)));
  });
  $$("[data-sw]").forEach((cb) => cb.addEventListener("change", (e) => {
    const id = cb.dataset.sw, t = tws().find((x) => x.id === id);
    if (!t) return;
    /* l'interruttore mostra la cosa (acceso = attiva): "applicata" e' il contrario per le voci che spengono qualcosa */
    const pol = t.kind === "overlay" ? -1 : (t.pol || 1);
    Object.defineProperty(e, "applied", { value: pol > 0 ? e.target.checked : !e.target.checked });
    const keep = (applied) => { e.target.checked = pol > 0 ? applied : !applied; };
    if (t.kind === "overlay") {
      if (S.sel.has(id)) S.sel.delete(id);                                   // annullo la selezione
      else if (t.applied) { keep(true); return revertIds([id]); }  // riaccendo l'overlay (come prima)
      else if (ovOn(t) && !t.ignored && !t.manual) S.sel.add(id);             // da spegnere con Applica
      else { keep(true); toast("Questo overlay e' gia' spento: l'hai spento dal suo programma. Per riaccenderlo usa il programma; se lo riaccendi, qui l'interruttore torna spento e potrai rispegnerlo da LagDoctor.", 7000); }
      return renderTweaks();
    }
    if (t.applied) { keep(true); return revertIds([id]); }
    if (t.kind === "myth" && t.status === true) { keep(true); return forceOff(id); }
    if (!selectable(t)) { keep(isOn(t)); return; }
    e.applied ? S.sel.add(id) : S.sel.delete(id);
    renderTweaks();
  }));
  $$("[data-how]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); docModal(tws().find((x) => x.id === b.dataset.how)); }));
  $$("[data-undo]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); revertIds([b.dataset.undo]); }));
  $$("[data-off]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); forceOff(b.dataset.off); }));
  $$("[data-ign]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); setIgnored(b.dataset.ign, true); }));
  $$("[data-addpath]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); applySelected([b.dataset.addpath]); }));
  $$("[data-unign]").forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); setIgnored(b.dataset.unign, false); }));
  if (S.twCat === OV_CAT) { const rb = $("#ov-refresh"); if (rb) rb.onclick = () => loadOverlays(true); if (!S.ovLoaded) loadOverlays(false); }
  const n = S.sel.size;
  $("#sel-count").textContent = n ? n + (n === 1 ? " voce selezionata" : " voci selezionate") + ": premi Applica (clicca sul nome di una voce per leggere cosa fa)"
    : "Interruttore acceso = attivo, spento = disattivato. Cambia gli interruttori e premi Applica. Clicca su una voce per leggere cosa fa.";
  $("#apply-btn").disabled = !n;
}
/* overlay: cosa gira adesso (si aggiorna ogni volta che apri la categoria) */
function overlayBox() {
  const live = S.ovLive;
  const body = live == null ? '<span class="mut">Controllo i programmi aperti...</span>'
    : live.length ? live.map((o) => `<span class="badge b-warn" title="${esc(o.process)}">${esc(o.name)}</span>`).join(" ")
    : '<span class="badge b-ok">nessun overlay in esecuzione</span>';
  return `<div class="ov-live"><div><b>Overlay attivi adesso</b><div class="mut" style="font-size:12.5px;margin-top:2px">Programmi che in questo momento si agganciano ai giochi. Sotto trovi tutti gli overlay installati e dove spegnerli.</div></div>
    <div class="ov-chips">${body}</div><button class="ghost sm" id="ov-refresh">Aggiorna</button></div>`;
}
async function loadOverlays(manual) {
  S.ovLoaded = true;
  try {
    const r = await api("/api/overlays");
    S.ovLive = r.live || [];
    tws().forEach((t) => { const x = r.items && r.items[t.id]; if (x) { t.status = x.status; t.note = x.note; t.running = x.running; } });
    if (manual) toast(S.ovLive.length ? `${S.ovLive.length} overlay in esecuzione` : "Nessun overlay in esecuzione");
  } catch (e) { S.ovLive = []; if (manual) toast("Errore: " + e.message); }
  if (S.page === "tweaks") renderTweaks();
}
async function forceOff(id) {
  try {
    const r = await api("/api/force_off", { id });
    toast(r.msg, 5000);
    await loadCatalog(true); await refreshState();
    if (S.page === "tweaks") renderTweaks();
  } catch (e) { toast("Errore: " + e.message); }
}

async function applySelected(ids, after) {
  ids = Array.isArray(ids) ? ids : [...S.sel];
  const sel = ids.map((id) => tws().find((t) => t.id === id)).filter(Boolean);
  const risky = sel.filter((t) => t.risk >= 2), needsPath = sel.some((t) => t.needs_path);
  const groups = {}; sel.forEach((t) => { if (t.group) (groups[t.group] = groups[t.group] || []).push(t); });
  const dup = Object.values(groups).filter((g) => g.length > 1);
  let libs = [];
  if (needsPath) {
    toast("Cerco i giochi su tutti i dischi (anche quelli senza launcher)...", 15000);
    try { libs = (await api("/api/defender_folders")).items || []; } catch (e) { libs = []; }
    $("#toast").hidden = true;
  }
  const srcName = { steam: "Steam", epic: "Epic", gog: "GOG", xbox: "Xbox", ubisoft: "Ubisoft", pc: "launcher", disco: "trovato sul disco" };
  const libHtml = libs.map((l, i) => `<label class="def-lib"><input type="checkbox" class="def-cb" data-i="${i}" ${l.excluded ? "checked disabled" : "checked"}>
      <span><b>${esc(l.path)}</b> <span class="mut">${l.drive ? "disco " + esc(l.drive) + " · " : ""}${l.games.length} ${l.games.length === 1 ? "gioco" : "giochi"}${(l.sources || []).length ? " · " + l.sources.map((s) => srcName[s] || s).join(", ") : ""}${l.excluded ? " · gia' esclusa" : ""}</span><br>
      <span class="mut" style="font-size:12px">${esc(l.games.slice(0, 6).join(", "))}${l.games.length > 6 ? ", ..." : ""}</span></span></label>`).join("");
  const m = modal(`
    <h2>Applico ${sel.length} modifiche</h2>
    <p class="mut">Prima creo un punto di ripristino di Windows. Ogni modifica si potra' annullare.</p>
    <ul>${sel.map((t) => `<li>${esc(t.label || t.name)}: <b>${t.kind === "overlay" || (t.pol || 1) < 0 ? "si spegne" : "si accende"}</b> <span class="badge ${riskCls[t.risk]}">${t.risk_label}</span></li>`).join("")}</ul>
    ${sel.some((t) => t.closes) ? `<div class="banner"><b>Programmi che verranno chiusi</b><p>Per cambiare l'impostazione dell'overlay LagDoctor chiude: <b>${[...new Set(sel.filter((t) => t.closes).map((t) => t.closes))].join(", ")}</b>. Se stai giocando o scaricando, finisci prima. Poi riaprili quando vuoi: l'overlay resta spento.</p></div>` : ""}
    ${dup.length ? `<p class="mut">Alternative tra loro: applico solo la prima di: ${dup.map((g) => g.map((t) => esc(t.label || t.name)).join(" / ")).join("; ")}</p>` : ""}
    ${needsPath ? `<div><b>Cartelle dei giochi da escludere da Defender</b>
      <p class="mut" style="margin:4px 0 8px">${libs.length ? "Trovate su tutti i dischi: dai launcher (Steam, Epic, GOG, Xbox, Ubisoft, EA...) e cercando i giochi senza launcher. Togli la spunta a quelle che non vuoi escludere." : "Nessuna cartella di giochi trovata: scrivila qui sotto."}</p>
      ${libHtml}
      <p style="margin-top:8px"><span class="mut">Altre cartelle (facoltativo, separate da ;)</span><br><input type="text" id="def-path" style="width:100%" placeholder="es. D:\\Giochi"></p></div>` : ""}
    ${risky.length ? `<div class="banner"><b>Modifiche rischiose o pericolose</b>${risky.map((t) => `<p><b>${esc(t.label || t.name)}</b>: ${esc(t.warning || "")}</p>`).join("")}
      <p>Scrivi <b>CONFERMO</b> per procedere:</p><input type="text" id="confirm" autocomplete="off"></div>` : ""}
    <div class="row" style="justify-content:flex-end;margin-top:14px"><button class="ghost" id="m-cancel">Annulla</button><button id="m-ok">Applica</button></div>`);
  $("#m-cancel", m).onclick = closeModal;
  $("#m-ok", m).onclick = async () => {
    const body = { ids, confirm: risky.length ? $("#confirm", m).value.trim() : "", defender_paths: needsPath ? [...libs.filter((l, i) => { const cb = $(`.def-cb[data-i="${i}"]`, m); return cb && cb.checked && !cb.disabled; }).map((l) => l.path),
      ...$("#def-path", m).value.split(";").map((p) => p.trim().replace(/^"|"$/g, "")).filter(Boolean)] : [] };
    if (needsPath && !body.defender_paths.length && !libs.some((l) => l.excluded)) { toast("Scegli almeno una cartella da escludere."); return; }
    if (needsPath && !body.defender_paths.length) { toast("Le cartelle spuntate sono gia' tutte escluse: niente da fare."); return; }
    if (risky.length && body.confirm !== "CONFERMO") { toast("Scrivi CONFERMO in maiuscolo per le modifiche rischiose."); return; }
    m.innerHTML = '<h2>Applico le modifiche...</h2><div class="spinner"></div><ul class="log" id="m-log"></ul>';
    try {
      const job = await runJob(api("/api/apply", body), (j) => logList($("#m-log"), j.messages));
      const res = job.result.results;
      S.sel.clear(); await loadCatalog(true);
      const ko = res.filter((r) => !r.ok), okN = res.length - ko.length;
      const title = !ko.length ? `Fatto: ${okN === 1 ? "modifica applicata" : okN + " modifiche applicate"}`
        : !okN ? (ko.length === 1 ? "Modifica NON riuscita" : `Nessuna modifica riuscita (${ko.length})`)
        : `${okN} ${okN === 1 ? "applicata" : "applicate"}, ${ko.length} NON ${ko.length === 1 ? "riuscita" : "riuscite"}`;
      const ic = { ok: ["✔", "var(--ok)"], reboot: ["⟳", "var(--warn)"], unk: ["?", "var(--warn)"], ko: ["✘", "var(--bad)"] };
      const line = (r) => { const [i, c] = ic[r.state || (r.ok ? "ok" : "ko")]; return `<li style="list-style:none;margin-left:-18px"><b style="color:${c}">${i}</b> <b>${esc(r.name)}</b>: <span class="${r.ok ? "mut" : ""}" style="${r.ok ? "" : "color:var(--bad)"}">${esc(r.msg)}</span></li>`; };
      m.innerHTML = `<h2 style="color:${ko.length ? "var(--bad)" : "inherit"}">${title}</h2>
        ${ko.length ? `<div class="banner" style="border-color:var(--bad)"><b>Non riuscite</b><ul style="margin:6px 0 0">${ko.map(line).join("")}</ul></div>` : ""}
        ${okN ? `<ul>${res.filter((r) => r.ok).map(line).join("")}</ul>` : ""}
        ${job.result.reboot ? '<div class="banner"><b>Riavvia Windows</b> per completare: alcune modifiche funzionano solo dopo il riavvio. Te lo ricordo anche in alto finche\' non riavvii.</div>' : ""}
        <div class="row" style="justify-content:flex-end">${job.result.reboot ? '<button class="ghost" id="m-reboot">Riavvia ora</button>' : ""}<button id="m-close">Chiudi</button></div>`;
      refreshState().catch(() => {});
      $("#m-close", m).onclick = () => { closeModal(); after ? after(res) : (S.page === "tweaks" && tweaksPage()); };
      if (job.result.reboot) $("#m-reboot", m).onclick = async () => { await api("/api/reboot", {}); m.innerHTML = "<h2>Windows si riavvia tra 15 secondi...</h2><p>Salva il tuo lavoro.</p>"; };
    } catch (e) { m.innerHTML = `<h2>Errore</h2><p>${esc(e.message)}</p><button id="m-close">Chiudi</button>`; $("#m-close", m).onclick = closeModal; }
  };
}
async function revertIds(ids) {
  const m = modal('<h2>Annullo...</h2><div class="spinner"></div>');
  try {
    const job = await runJob(api("/api/revert", { ids }));
    await loadCatalog(true);
    m.innerHTML = `<h2>Fatto</h2><ul>${job.result.results.map((r) => `<li>${esc(r.name)}: <span class="mut">${esc(r.msg)}</span></li>`).join("")}</ul><button id="m-close">Chiudi</button>`;
    refreshState().catch(() => {});
    $("#m-close", m).onclick = () => { closeModal(); if (S.page === "tweaks") tweaksPage(); };
  } catch (e) { m.innerHTML = `<h2>Errore</h2><p>${esc(e.message)}</p><button id="m-close">Chiudi</button>`; $("#m-close", m).onclick = closeModal; }
}
function undoDialog() {
  const applied = tws().filter((t) => t.applied);
  if (!applied.length) return toast("LagDoctor non ha applicato nessuna modifica.");
  const m = modal(`<h2>Annulla modifiche di LagDoctor</h2>
    ${applied.map((t) => `<label class="list-row"><input type="checkbox" value="${t.id}" checked> ${esc(t.label || t.name)} <span class="mut">· ${(t.pol || 1) > 0 ? "accesa" : "spenta"} da LagDoctor</span></label>`).join("")}
    <div class="row" style="justify-content:flex-end;margin-top:12px"><button class="ghost" id="m-cancel">Chiudi</button><button class="red" id="m-ok">Annulla selezionate</button></div>`);
  $("#m-cancel", m).onclick = closeModal;
  $("#m-ok", m).onclick = () => revertIds($$("input:checked", m).map((i) => i.value));
}

/* ------------------------------------------------------------------ DRIVER VIDEO */
/* Schede in preparazione */
function soonPage(title, sub) {
  main().innerHTML = `<h1>${title}</h1><p class="sub">${sub}</p><div class="empty">In arrivo nei prossimi aggiornamenti.</div>`;
}
function pulitorePage() { soonPage("Pulitore", "Pulizia dei file inutili che occupano spazio sul disco."); }

/* ------------------------------------------------------------------ BACKUPS */
const BK_RP = '<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/><path d="M12 8v4l3 2"/>';
const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];
function dataIt(iso, ora = true) {
  const d = new Date(iso);
  if (isNaN(d)) return iso || "";
  return `${d.getDate()} ${MESI[d.getMonth()]} ${d.getFullYear()}` + (ora ? `, ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}` : "");
}
async function backupsPage() {
  main().innerHTML = '<div class="loading"><div class="spinner"></div><p>Leggo i backup...</p></div>';
  let r;
  try { r = await api("/api/backups"); } catch (e) { main().innerHTML = `<h1>Backups</h1><div class="empty">Errore: ${esc(e.message)}</div>`; return; }
  if (S.page !== "backups") return;
  const tile = (inner, col) => `<span class="bk-ic" style="color:${col};background:${col}1f">${inner}</span>`;
  main().innerHTML = `<div class="bk-head"><h1>Backups</h1><button class="ghost" id="bk-new">+ Crea backup adesso</button></div>
    ${r.error && !r.points.length ? `<div class="empty">Non riesco a leggere i backup di Windows: ${esc(r.error)}</div>`
      : r.points.length ? r.points.map((p) => `<div class="bk-row">${tile(`<svg viewBox="0 0 24 24">${BK_RP}</svg>`, "#00d4ff")}
        <div class="grow"><b>${esc(dataIt(p.time))}</b><small>${esc(p.note)}</small></div>
        <div class="btns"><button class="ghost" data-rp="${p.seq}">Ripristina</button><button class="ghost del" data-rpdel="${p.seq}">Elimina</button></div></div>`).join("")
      : '<div class="empty">Nessun backup.</div>'}
    <div class="bk-sec"><h2>Modifiche di LagDoctor</h2><span class="grow"></span>${r.changes.length ? '<button class="ghost sm" id="bk-undoall">Annulla tutte</button>' : ""}</div>
    ${r.changes.length ? r.changes.map((c) => {
      const ic = CAT_IC[c.cat] || ["#a78bfa", '<rect x="6" y="6" width="12" height="12" rx="2"/>'];
      return `<div class="bk-row">${tile(`<svg viewBox="0 0 24 24">${ic[1]}</svg>`, ic[0])}
        <div class="grow"><b>${esc(c.name)}</b><small>${esc(c.cat)}${c.time ? " · applicata il " + esc(dataIt(c.time, false)) : ""}</small></div>
        <div class="btns"><button class="ghost" data-undo1="${esc(c.id)}">Annulla modifica</button></div></div>`; }).join("")
      : '<div class="empty">Nessuna modifica di LagDoctor attiva.</div>'}`;
  const when = (seq) => dataIt((r.points.find((p) => p.seq === Number(seq)) || {}).time);
  const ask = (title, text, okLabel, fn) => {
    const m = modal(`<h2>${title}</h2><p>${text}</p><div class="row" style="justify-content:flex-end"><button class="ghost" id="m-cancel">Annulla</button><button id="m-ok">${okLabel}</button></div>`);
    $("#m-cancel", m).onclick = closeModal;
    $("#m-ok", m).onclick = async () => { $("#m-ok", m).disabled = true; $("#m-cancel", m).disabled = true; await fn(m); };
  };
  $("#bk-new").onclick = async () => {
    const b = $("#bk-new"); b.disabled = true; b.textContent = "Creo il backup...";
    try { await runJob(api("/api/backups/create", {})); toast("Backup creato"); }
    catch (e) { toast("Errore: " + e.message, 7000); }
    if (S.page === "backups") backupsPage();
  };
  $$("[data-rp]").forEach((b) => b.onclick = () => ask("Ripristinare questo backup?",
    `Windows torna com'era il <b>${esc(when(b.dataset.rp))}</b>: impostazioni, registro, driver e programmi. I tuoi file personali (foto, documenti, salvataggi) non vengono toccati.<br><br><b>Il PC si riavvia subito</b> e ci mette qualche minuto: salva quello che stai facendo.`,
    "Ripristina e riavvia", async (m) => {
      try { await api("/api/backups/restore", { seq: Number(b.dataset.rp) }); m.innerHTML = "<h2>Ripristino avviato</h2><p>Il PC si sta riavviando...</p>"; }
      catch (e) { closeModal(); toast("Errore: " + e.message, 8000); }
    }));
  $$("[data-rpdel]").forEach((b) => b.onclick = () => ask("Eliminare questo backup?",
    `Il backup del <b>${esc(when(b.dataset.rpdel))}</b> verra' cancellato e non si potra' piu' usare.`, "Elimina", async () => {
      try { const x = await api("/api/backups/delete", { seq: Number(b.dataset.rpdel) }); toast(x.msg || "Backup eliminato"); }
      catch (e) { toast("Errore: " + e.message, 8000); }
      closeModal(); backupsPage();
    }));
  const undo = async (ids) => {
    try { await runJob(api("/api/revert", { ids })); toast(ids.length === 1 ? "Modifica annullata" : "Modifiche annullate"); }
    catch (e) { toast("Errore: " + e.message, 7000); }
    S.catalog = null; closeModal(); if (S.page === "backups") backupsPage();
  };
  $$("[data-undo1]").forEach((b) => b.onclick = () => { b.disabled = true; b.textContent = "Annullo..."; undo([b.dataset.undo1]); });
  const all = $("#bk-undoall");
  if (all) all.onclick = () => ask("Annullare tutte le modifiche?", `LagDoctor rimette com'erano tutte le ${r.changes.length} modifiche. Alcune valgono dal prossimo riavvio.`,
    "Annulla tutte", () => undo(r.changes.filter((c) => c.known).map((c) => c.id)));
}

/* ------------------------------------------------------------------ Fix PC */
const FX_IC = {
  rete: ["#00d4ff", '<path d="M2 8.5a15 15 0 0 1 20 0"/><path d="M5 12a10 10 0 0 1 14 0"/><path d="M8.5 15.5a5 5 0 0 1 7 0"/><circle cx="12" cy="19" r="1"/>'],
  bt: ["#4d8dff", '<path d="M7 7l10 10-5 4V3l5 4L7 17"/>'],
  dischi: ["#a78bfa", '<rect x="3" y="13" width="18" height="7" rx="2"/><path d="M5 13l2.5-8h9l2.5 8"/><path d="M7 16.5h.01M10.5 16.5h.01"/>'],
  sys: ["#2ee59d", '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>'],
  wu: ["#38bdf8", '<path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/><path d="M12 8v6M9.5 11.5L12 14l2.5-2.5"/>'],
  audio: ["#f472b6", '<path d="M4 9v6h4l5 4V5L8 9z"/><path d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12"/>'],
  ui: ["#7c5cff", '<rect x="2.5" y="4" width="19" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>'],
  app: ["#ffb547", '<path d="M5 8h14l-1 12H6z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/>'],
  dev: ["#ff8a5c", '<path d="M9 2v5M15 2v5"/><path d="M6 7h12v4a6 6 0 0 1-12 0z"/><path d="M12 17v5"/>'],
  altro: ["#94a3b8", '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'],
};
const fxIcon = (id) => { const i = FX_IC[id] || ["#8b90a8", '<circle cx="12" cy="12" r="4"/>']; return `<span class="ci" style="color:${i[0]}"><svg viewBox="0 0 24 24">${i[1]}</svg></span>`; };
async function fixpcPage() {
  if (!S.fx) {
    main().innerHTML = '<div class="loading"><div class="spinner"></div><p>Carico i comandi...</p></div>';
    S.fx = await api("/api/fixpc");
    S.fxRes = S.fxRes || {}; S.fxOpen = S.fxOpen || new Set();
  }
  S.fxCat = S.fxCat || S.fx.cats[0].id;
  main().innerHTML = `<h1>Fix PC</h1><p class="sub">Comandi veri di Windows per sistemare i problemi piu' comuni. Scegli la categoria, leggi a cosa serve e premi Esegui: vedi il risultato qui sotto.</p>
    <input class="fx-search" id="fx-q" type="search" placeholder="Cerca un problema (es. wifi, cuffie, schermata blu, aggiornamenti)...">
    <div class="fx-wrap"><div class="fx-cats" id="fx-cats"></div><div id="fx-body"></div></div>`;
  $("#fx-q").addEventListener("input", renderFix);
  renderFix();
}
function renderFix() {
  const q = ($("#fx-q")?.value || "").trim().toLowerCase();
  const running = S.fxRunning;
  $("#fx-cats").innerHTML = S.fx.cats.map((c) => `<a class="fx-cat ${!q && c.id === S.fxCat ? "on" : ""}" data-c="${c.id}">${fxIcon(c.id)}<span class="n">${esc(c.n)}</span><small>${c.fx.length}</small></a>`).join("");
  $$("#fx-cats a").forEach((a) => a.addEventListener("click", () => { S.fxCat = a.dataset.c; $("#fx-q").value = ""; renderFix(); main().scrollTop = 0; }));
  const card = (f) => {
    const b = [f.best ? '<span class="badge b-acc">CONSIGLIATO</span>' : "", f.ro ? '<span class="badge b-ok">SOLO CONTROLLO</span>' : "",
      f.r ? '<span class="badge b-warn">RIAVVIO</span>' : "", f.w ? '<span class="badge b-bad">ATTENZIONE</span>' : "",
      `<span class="badge">${esc(f.d)}</span>`].join("");
    const open = S.fxOpen.has(f.id), res = S.fxRes[f.id], me = running === f.id;
    return `<div class="fx" data-id="${f.id}"><div class="fx-top"><div class="fx-main"><div class="fx-t">${esc(f.t)}${b}</div><p class="fx-q">${esc(f.q)}</p>
      ${f.w ? `<p class="fx-warn">${esc(f.w)}</p>` : ""}</div>
      <div class="fx-btns"><button class="ghost fx-cmd">${open ? "Nascondi comandi" : "Comandi"}</button>
        ${me ? '<button class="ghost fx-stop">Interrompi</button>' : `<button class="fx-go" ${running ? "disabled" : ""}>${res ? "Esegui di nuovo" : "Esegui"}</button>`}</div></div>
      ${open ? `<div class="fx-code">${f.c.map((x) => '<span class="fxp">&gt; </span>' + esc(x)).join("\n")}</div>` : ""}
      ${me || res ? `<div class="fx-out">${esc(me ? (S.fxLive || "Avvio...") : res.out)}</div>` : ""}
      ${me ? '<p class="fx-res run"><span class="spinner sm"></span>In corso...</p>' : res ? `<p class="fx-res ${res.ok ? "ok" : "bad"}"><b>${res.ok ? "&#10004;" : "&#10006;"}</b>${esc(res.res)}</p>` : ""}</div>`;
  };
  let html;
  if (q) {
    const hits = S.fx.cats.map((c) => [c, c.fx.filter((f) => (f.t + " " + f.q + " " + f.kw + " " + c.n).toLowerCase().includes(q))]).filter(([, l]) => l.length);
    html = hits.length ? hits.map(([c, l]) => `<div class="fx-head">${fxIcon(c.id)}<h2>${esc(c.n)}</h2></div><div class="fx-list">${l.map(card).join("")}</div>`).join("")
      : '<div class="empty">Nessun fix trovato: prova con un\'altra parola.</div>';
  } else {
    const c = S.fx.cats.find((x) => x.id === S.fxCat) || S.fx.cats[0];
    html = `<div class="fx-head">${fxIcon(c.id)}<h2>${esc(c.n)}</h2></div><div class="fx-list">${c.fx.map(card).join("")}</div>`;
  }
  $("#fx-body").innerHTML = html;
  $$("#fx-body .fx").forEach((el) => {
    const id = el.dataset.id;
    $(".fx-cmd", el).onclick = () => { S.fxOpen.has(id) ? S.fxOpen.delete(id) : S.fxOpen.add(id); renderFix(); };
    const go = $(".fx-go", el); if (go) go.onclick = () => fixAsk(id);
    const st = $(".fx-stop", el); if (st) st.onclick = () => S.fxJob && api("/api/stop", { id: S.fxJob }).catch(() => {});
  });
  const o = $("#fx-body .fx-out"); if (o && running) o.scrollTop = o.scrollHeight;
}
function fxFind(id) { for (const c of S.fx.cats) for (const f of c.fx) if (f.id === id) return f; }
function fixAsk(id) {
  const f = fxFind(id);
  if (!f.w && !f.r) return fixRun(id);
  const m = modal(`<h2>${esc(f.t)}</h2>${f.w ? `<p>${esc(f.w)}</p>` : ""}${f.r ? "<p>Alla fine servira' un riavvio del PC per completare.</p>" : ""}
    <div class="fx-code" style="margin:0 0 16px">${f.c.map((x) => '<span class="fxp">&gt; </span>' + esc(x)).join("\n")}</div>
    <div class="row" style="justify-content:flex-end"><button class="ghost" id="m-cancel">Annulla</button><button id="m-ok">Esegui</button></div>`);
  $("#m-cancel", m).onclick = closeModal;
  $("#m-ok", m).onclick = () => { closeModal(); fixRun(id); };
}
async function fixRun(id) {
  if (S.fxRunning) return;
  S.fxRunning = id; S.fxLive = ""; delete S.fxRes[id];
  const here = () => S.page === "fixpc" && $("#fx-body");
  if (here()) renderFix();
  try {
    const job = await runJob(api("/api/fixpc/run", { id }).then((j) => { S.fxJob = j.id; return j; }), (j) => {
      S.fxLive = (j.live && j.live.out) || "";
      const o = here() && $(`#fx-body .fx[data-id="${CSS.escape(id)}"] .fx-out`);
      if (o) { const end = o.scrollTop + o.clientHeight >= o.scrollHeight - 30; o.textContent = S.fxLive || "Avvio..."; if (end) o.scrollTop = o.scrollHeight; }
    });
    S.fxRes[id] = job.result;
  } catch (e) {
    S.fxRes[id] = { ok: false, out: S.fxLive || "", res: "Errore: " + e.message };
  }
  S.fxRunning = null; S.fxJob = null;
  const r = S.fxRes[id];
  toast((r.ok ? "Finito: " : "Attenzione: ") + fxFind(id).t);
  if (here()) renderFix();
}

async function driver() {
  main().innerHTML = '<div class="loading"><div class="spinner"></div><p>Leggo le impostazioni del driver video...</p></div>';
  let r;
  try { r = await api("/api/driver"); } catch (e) { r = { ok: false, error: e.message }; }
  await loadCatalog();
  const cat = r.vendor === "nvidia" ? "Driver NVIDIA" : r.vendor === "amd" ? "Driver AMD" : null;
  const items = cat ? tws().filter((t) => t.cat === cat) : [];
  const linked = new Set((r.problems || []).map((p) => p.fix_id).filter(Boolean));
  const fix = items.filter((t) => !t.applied && t.status !== true && ((t.kind === "fix" && t.status === false) || linked.has(t.id)));
  const lvl = { ok: ["OK", "b-ok"], info: ["DA SAPERE", "b-acc"], bad: ["PROBLEMA", "b-bad"] };
  main().innerHTML = `<h1>Driver video${r.panel ? " – " + esc(r.panel) : ""}</h1>
    <p class="sub">Impostazioni globali lette direttamente dal driver${r.raw && r.raw.gpu ? " (" + esc(r.raw.gpu) + ")" : ""}. Valgono per tutti i giochi, salvo i profili dei singoli giochi.</p>
    ${!r.ok ? `<div class="prob s2"><b>Non riesco a leggere le impostazioni del driver</b><p>${esc(r.error || "")}</p>
      <p class="fix">Assicurati di avere il driver ufficiale ${r.vendor === "amd" ? "AMD Software Adrenalin aggiornato" : "NVIDIA aggiornato"} e di aver avviato LagDoctor come amministratore.</p></div>` : `
    <div class="row" style="margin-bottom:12px"><button id="drv-fix" ${fix.length ? "" : "disabled"}>${fix.length ? "Correggi " + fix.length + " problemi" : "Nessun problema da correggere"}</button>
      <button class="ghost" id="drv-all">Tutte le ottimizzazioni del driver (${items.length})</button><button class="ghost" id="drv-reload">Rileggi</button></div>
    <p class="mut" style="font-size:13px;margin:0 0 6px">Clicca su un'impostazione per leggere a cosa serve, il valore consigliato e i possibili problemi.</p>
    <table class="drv"><tr><th>Impostazione</th><th>Valore attuale</th><th>Giudizio</th><th>Nota</th></tr>
      ${r.rows.map((x, i) => `<tr class="drv-row" data-i="${i}"><td><b>${esc(x.name)}</b> <span class="info-hint">▾ dettagli</span></td><td><b>${esc(x.value)}</b></td><td><span class="badge ${lvl[x.level][1]}">${lvl[x.level][0]}</span></td><td class="mut" style="font-size:13px">${esc(x.note || "")}</td></tr>
        <tr class="drv-doc" data-i="${i}" hidden><td colspan="4">${x.doc ? `<div class="doc">
          <div><h4>A cosa serve</h4><p>${esc(x.doc.cosa)}</p></div>
          <div><h4 class="ok">Valore consigliato e perche'</h4><p>${esc(x.doc.perche)}</p></div>
          <div><h4 class="bad">Possibili problemi</h4><p>${esc(x.doc.problemi)}</p></div></div>` : '<span class="mut">Nessuna spiegazione disponibile.</span>'}</td></tr>`).join("")}
    </table>
    <h2>Problemi trovati</h2>${probHtml(r.problems)}`}
    <details><summary>Cosa non si puo' leggere</summary><div class="card mut">
      ${r.vendor === "amd" ? "Adrenalin: la dimensione della cache shader, Smart Access Memory e i profili dei singoli giochi non sono esposti da AMD; FreeSync si controlla in Adrenalin > Schermo."
        : "NVIDIA: vengono lette le impostazioni globali. I profili dei singoli giochi possono cambiarle: controllali in Pannello NVIDIA > Gestisci impostazioni 3D > Impostazioni programma. 'Ultra' della modalita' bassa latenza si puo' leggere ma va impostato dal Pannello."}
    </div></details>`;
  if (!r.ok) return;
  $("#drv-reload").onclick = driver;
  $$(".drv-row").forEach((tr) => tr.addEventListener("click", () => {
    const d = $(`.drv-doc[data-i="${tr.dataset.i}"]`);
    d.hidden = !d.hidden;
    $(".info-hint", tr).textContent = d.hidden ? "▾ dettagli" : "▴ chiudi";
  }));
  $("#drv-all").onclick = () => { S.filter = "all"; S.catFilter = cat; go("tweaks"); };
  $("#drv-fix").onclick = () => applySelected(fix.map((t) => t.id), () => driver());
}

/* ------------------------------------------------------------------ AVVIO AUTOMATICO */
async function startup() {
  S.stTab = S.stTab || "prog";
  main().innerHTML = `<h1>Avvio automatico</h1><p class="sub">Cosa parte con Windows e resta in background mentre giochi.</p>
    <div class="tabs2"><a data-st="prog" class="${S.stTab === "prog" ? "on" : ""}">Programmi<small id="st-n-prog"></small></a>
      <a data-st="proc" class="${S.stTab === "proc" ? "on" : ""}">Processi in background<small id="st-n-proc"></small></a></div>
    <div id="st-body"><div class="loading"><div class="spinner"></div><p>Leggo cosa parte con Windows...</p></div></div>`;
  $$("[data-st]").forEach((a) => a.onclick = () => { if (S.stTab === a.dataset.st) return; S.stTab = a.dataset.st; go("startup", { sub: true }); });
  if (S.stTab === "prog") return startupPrograms();
  return startupProcesses();
}
const runTxt = (it) => it.running ? `<b>in esecuzione</b>${it.mb ? " · " + it.mb + " MB" : ""}` : "fermo";
async function startupPrograms() {
  const r = await api("/api/startup");
  const bad = new Set(r.bad);
  $("#st-n-prog").textContent = r.items.length;
  animIn([$("#st-body")]);
  $("#st-body").innerHTML = `<div class="tools"><input type="search" id="st-q" placeholder="Cerca..." style="width:220px"><span class="grow"></span><span class="mut" style="font-size:12px">Interruttore acceso = parte con Windows</span></div>
    <div id="st-list"></div>`;
  const draw = () => {
    const q = ($("#st-q").value || "").toLowerCase();
    const list = r.items.map((it, i) => [it, i]).filter(([it]) => !q || (it.name + " " + it.cmd).toLowerCase().includes(q));
    $("#st-list").innerHTML = list.length ? list.map(([it, i]) => {
      const isBad = bad.has((it.exe || "").toLowerCase()), sec = /securityhealth/i.test(it.name);
      return `<div class="pr"><label class="switch"><input type="checkbox" data-i="${i}" ${it.enabled ? "checked" : ""}><span></span></label>
        <div class="tx"><b>${esc(it.name)}</b> ${isBad ? '<span class="badge b-warn">noto per causare scatti</span>' : ""}${sec ? '<span class="badge b-ok">sicurezza: lascialo attivo</span>' : ""}<div class="sub2" title="${esc(it.cmd)}">${esc(it.exe || "")}</div></div>
        <div class="meta"><span class="src">${it.hive === "HKCU" ? "solo il tuo utente" : "tutti gli utenti"}</span></div><div class="run">${runTxt(it)}</div></div>`;
    }).join("") : '<div class="empty">Nessun programma all\'avvio trovato.</div>';
    $$("#st-list [data-i]").forEach((c) => c.addEventListener("change", async () => {
      const it = r.items[c.dataset.i];
      try { await api("/api/startup", { hive: it.hive, name: it.name, enabled: c.checked }); it.enabled = c.checked; toast((c.checked ? "Attivato: " : "Disattivato: ") + it.name); }
      catch (e) { toast("Errore: " + e.message); c.checked = !c.checked; }
    }));
  };
  $("#st-q").addEventListener("input", draw);
  draw();
}
async function startupProcesses() {
  let r;
  try { r = await api("/api/autostart" + (S.stAll ? "?all=1" : "")); }
  catch (e) { $("#st-body").innerHTML = `<div class="empty">Errore: ${esc(e.message)}</div>`; return; }
  $("#st-n-proc").textContent = r.items.filter((x) => x.group !== "win").length;
  animIn([$("#st-body")]);
  $("#st-body").innerHTML = `<div class="note"><b>Servizi e attivita' pianificate</b> che non si vedono in Gestione attivita' &gt; Avvio. Spegnendo l'interruttore LagDoctor <b>toglie l'avvio automatico</b> (servizio Disattivato, attivita' disattivata): se e' aperto viene fermato <b>una volta sola</b> e non ripartira', senza chiusure continue. Riaccendi l'interruttore per rimettere tutto com'era (anche con "Ripristina tutto").</div>
    <div class="tools"><input type="search" id="st-q" placeholder="Cerca..." style="width:220px"><label class="chk"><input type="checkbox" id="st-all" ${S.stAll ? "checked" : ""}> Mostra anche i componenti di Windows</label>
      <span class="grow"></span><span class="mut" style="font-size:12px">Interruttore acceso = parte con Windows</span></div>
    ${r.error ? `<div class="empty" style="text-align:left">${r.items.length ? "Letto solo in parte" : "Non riesco a leggere servizi e attivita'"}: ${esc(r.error)}</div>` : ""}
    <div id="st-list"></div>`;
  const draw = () => {
    const q = ($("#st-q").value || "").toLowerCase();
    const list = r.items.filter((it) => !q || (it.name + " " + it.exe + " " + it.company).toLowerCase().includes(q));
    $("#st-list").innerHTML = r.groups.map((g) => {
      const rows = list.filter((it) => it.group === g.id);
      if (!rows.length) return "";
      return `<div class="grp">${esc(g.name)}</div>` + rows.map((it) => {
        const i = r.items.indexOf(it);
        const badges = it.badges.map((b) => b.startsWith("!") ? `<span class="badge b-warn">${esc(b.slice(1))}</span>` : b === "si puo' disattivare" ? `<span class="badge b-acc">${esc(b)}</span>` : `<span class="badge">${esc(b)}</span>`).join(" ");
        const lock = it.lock ? `<span class="badge b-ok">${esc(it.lock)}</span>` : "";
        return `<div class="pr"><label class="switch" title="${it.lock ? esc(it.lock) : it.on ? "Spegni per non farlo partire con Windows" : "Accendi per rimetterlo com'era"}"><input type="checkbox" data-p="${i}" ${it.on ? "checked" : ""} ${it.lock ? "disabled" : ""}><span></span></label>
          <div class="tx"><b>${esc(it.name)}</b> ${lock}${badges}<div class="sub2" title="${esc(it.desc || it.path)}">${esc(it.exe || "")}${it.company ? " · " + esc(it.company) : ""}</div></div>
          <div class="meta"><span class="src">${esc(it.origin)}</span></div><div class="run">${runTxt(it)}</div></div>`;
      }).join("");
    }).join("") || '<div class="empty">Nessun servizio o attivita\' trovato.</div>';
    $$("#st-list [data-p]").forEach((c) => c.addEventListener("change", async () => {
      const it = r.items[c.dataset.p];
      c.disabled = true;
      try {
        const x = await api("/api/autostart", { kind: it.kind, id: it.id, enabled: c.checked, exe: it.path });
        toast(it.name + ": " + x.msg, 4500);
        startupProcesses();
      } catch (e) { toast("Errore: " + e.message, 6000); c.checked = !c.checked; c.disabled = false; }
    }));
  };
  $("#st-q").addEventListener("input", draw);
  $("#st-all").onchange = (e) => { S.stAll = e.target.checked; $("#st-list").innerHTML = '<div class="loading"><div class="spinner"></div></div>'; startupProcesses(); };
  draw();
}

/* ------------------------------------------------------------------ GAME MODE */
const GM_SRC = { steam: "Steam", epic: "Epic Games", gog: "GOG", xbox: "Xbox / Game Pass", ubisoft: "Ubisoft", pc: "Installato", java: "Java", manuale: "aggiunto da te" };
/* icona di un gioco: logo del gioco (se e' nell'elenco dei famosi) > icona vera dal suo .exe > logo dello studio > lettera */
const OWN_LOGOS = new Set(["counterstrike", "fortnite", "valorant", "leagueoflegends", "dota2", "pubg", "roblox", "fifa", "vrchat", "osu", "fivem"]);
function gameLogo(name) {
  if (typeof GAME_LOGOS === "undefined") return null;
  const n = " " + String(name || "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim() + " ";
  for (const [ws, slug, c1, c2, fg] of GAME_LOGOS) if (ws.some((w) => n.includes(" " + w + " "))) return { slug, c1, c2, fg };
  return null;
}
function gameIco(name, id, hasIcon) {
  const l = gameLogo(name);
  const logo = l && `<span class="gm-ico" style="background:linear-gradient(135deg,${l.c1},${l.c2})"><svg viewBox="0 0 24 24"><path d="${GAME_LOGO_PATHS[l.slug]}" fill="${l.fg}"/></svg></span>`;
  if (l && OWN_LOGOS.has(l.slug)) return logo;
  if (hasIcon && id) return `<span class="gm-ico img"><img alt="" src="/gameicon?id=${encodeURIComponent(id)}&t=${encodeURIComponent(window.LD_TOKEN)}"></span>`;
  if (logo) return logo;
  const cols = ["#7c5cff", "#00d4ff", "#2ee59d", "#ffb547", "#ff8a5c", "#f472b6", "#38bdf8", "#a78bfa"];
  let h = 0; for (const ch of String(name || "?")) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  const c = cols[h % cols.length];
  return `<span class="gm-ico" style="background:${c}1f;color:${c}">${esc(String(name || "?").replace(/^the\s+/i, "").slice(0, 1).toUpperCase())}</span>`;
}
const GM_GROUPS = [
  ["Il gioco", "#2ee59d", '<path d="M6 8h12a4 4 0 0 1 4 4v1.5a3.5 3.5 0 0 1-6.3 2.1L14.5 14h-5l-1.2 1.6A3.5 3.5 0 0 1 2 13.5V12a4 4 0 0 1 4-4z"/><path d="M7 10.5v3M5.5 12h3M16 11h.01M18 13h.01"/>',
    ["priority", "gpu_priority", "affinity", "timer", "qos"]],
  ["Programmi in background", "#ffb547", '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M7 20h10"/><path d="M9 9h6"/>',
    ["bg_priority", "bg_io", "vendor_priority", "eco_bg", "trim_ram", "close_onedrive"]],
  ["Windows", "#38bdf8", '<rect x="3" y="3" width="8" height="8" rx="1"/><rect x="13" y="3" width="8" height="8" rx="1"/><rect x="3" y="13" width="8" height="8" rx="1"/><rect x="13" y="13" width="8" height="8" rx="1"/>',
    ["close_apps", "stop_services", "stop_updates", "maintenance", "close_shell"]],
  ["Memoria, energia e scheda video", "#a78bfa", '<rect x="2.5" y="7" width="19" height="10" rx="1.5"/><path d="M6 17v3M10 17v3M14 17v3M18 17v3"/><rect x="6" y="10" width="4" height="4" rx=".5"/><rect x="14" y="10" width="4" height="4" rx=".5"/>',
    ["standby_purge", "power_plan", "gpu_pref"]],
];
const GM_SHORT = { priority: "Priorita' del gioco", gpu_priority: "Priorita' della scheda video", affinity: "Core del processore scelti da LagDoctor",
  timer: "Timer di sistema a 0,5 ms", qos: "Priorita' di rete al gioco", bg_priority: "Priorita' bassa ai programmi aperti",
  bg_io: "Priorita' bassa a disco e memoria", vendor_priority: "Priorita' bassa ai programmi del produttore", eco_bg: "Modalita' efficienza",
  trim_ram: "Pulizia della loro RAM", close_onedrive: "Pausa di OneDrive", close_apps: "Chiusura dei componenti inutili",
  stop_services: "Stop dei servizi non necessari", stop_updates: "Blocco di aggiornamenti e download", maintenance: "Pausa della manutenzione",
  close_shell: "Chiusura di Esplora risorse", standby_purge: "Svuotamento della memoria in standby",
  power_plan: "Piano 'Prestazioni eccellenti'", gpu_pref: "Scheda video ad alte prestazioni" };
const GM_PW = '<path d="M12 3v9"/><path d="M6.3 6.3a8 8 0 1 0 11.4 0"/>';
const icoSvg = (d) => `<svg viewBox="0 0 24 24">${d}</svg>`;
function gmSince(t) {
  if (!t) return "";
  const m = Math.max(0, Math.round((Date.now() / 1000 - t) / 60));
  return m < 1 ? "da meno di un minuto" : m === 1 ? "da 1 minuto" : m < 60 ? `da ${m} minuti` : `da ${Math.floor(m / 60)} h ${m % 60} min`;
}
async function gamemodePage(scanAgain) {
  let r;
  try { r = await api("/api/gamemode" + (scanAgain ? "?scan=1" : "")); }
  catch (e) { main().innerHTML = `<h1>Game mode</h1><div class="empty">Errore: ${esc(e.message)}</div>`; return; }
  if (S.page !== "gamemode") return;
  S.gmData = r;
  const c = r.config, st = r.status;
  const nOn = c.games.filter((g) => g.on).length, optOn = r.options.filter((o) => c.opts[o.id]).length;
  const icons = new Set(r.icons || []);
  const playing = new Set((st.active ? st.games || [] : []).map((x) => String(x).toLowerCase()));
  let state, k, title, sub;
  if (!c.enabled) { state = "off"; k = "Spenta"; title = "La game mode e' spenta"; sub = "Accendila: parte da sola con Windows e si attiva quando apri uno dei giochi qui sotto."; }
  else if (!st.running) { state = "warn"; k = "Non in esecuzione"; title = "Il programma della game mode non sta girando"; sub = "Spegnila e riaccendila con il tasto qui a sinistra."; }
  else if (st.active) {
    state = "on"; k = "Attiva"; title = esc((st.games || []).join(", ")) + ` <span>${gmSince(st.since)}</span>`;
    sub = "Processore, scheda video e rete danno la precedenza al gioco. Quando lo chiudi, tutto torna com'era.";
  } else { state = "ready"; k = "Pronta"; title = "In attesa di un gioco"; sub = "Si attiva da sola quando apri uno dei giochi accesi qui sotto."; }
  const note = (id) => id === "affinity" ? (r.cpu && r.cpu.apply ? "si usa su questo processore" : "non serve su questo processore")
    : id === "eco_bg" ? (r.eco && r.eco.apply ? "automatica" : "non serve su questo processore")
    : id === "gpu_pref" ? (r.gpus && r.gpus.length >= 2 ? "" : "PC con due schede") : "";
  const byId = Object.fromEntries(r.options.map((o) => [o.id, o]));
  const grouped = new Set(GM_GROUPS.flatMap((g) => g[3]));
  const groups = GM_GROUPS.map((g) => [...g.slice(0, 3), g[3].filter((id) => byId[id])]);
  const rest = r.options.filter((o) => !grouped.has(o.id)).map((o) => o.id);
  if (rest.length) groups.push(["Altro", "#94a3b8", '<circle cx="12" cy="12" r="9"/><path d="M8 12h8"/>', rest]);
  main().innerHTML = `<h1>Game mode</h1><p class="sub">Quando apri un gioco, il PC lavora solo per lui. Quando lo chiudi, tutto torna esattamente com'era.</p>
    <div class="gm-hero ${state}" id="gm-status">
      <button class="gm-power" id="gm-power" title="${c.enabled ? "Spegni la game mode" : "Accendi la game mode"}">${icoSvg(GM_PW)}</button>
      <div class="gm-state"><div class="gm-k">${k}</div><div class="gm-t">${title}</div><div class="gm-s">${sub}</div>
        <div class="gm-links">${st.active ? '<a id="gm-ver-btn">Verifica ottimizzazioni</a>' : ""}${(st.actions || []).length ? `<a id="gm-acts">Cosa ha fatto ${st.active ? "ora" : "l'ultima volta"}</a>` : ""}
          ${c.enabled && !st.active ? `<span>${st.autostart ? "Parte da sola con Windows" : "Avvio con Windows non attivo"}</span>` : ""}</div></div>
      <div class="gm-nums"><div><b>${nOn}</b><small>giochi seguiti</small></div><div><b>${optOn}</b><small>azioni attive</small></div></div>
    </div>
    ${(st.errors || []).length ? `<ul class="gm-err">${st.errors.map((a) => "<li>" + esc(a) + "</li>").join("")}</ul>` : ""}
    <div class="gm-sec"><h2>Giochi</h2><span class="mut gm-cnt">${c.games.length} trovati${r.added ? ` · <b>${r.added} nuovi</b>` : ""}</span><span class="grow"></span>
      <button class="ghost sm" id="gm-scan">${icoSvg(ICP.refresh)}Cerca di nuovo</button><button class="ghost sm" id="gm-add">${icoSvg('<path d="M12 5v14M5 12h14"/>')}Aggiungi</button></div>
    ${c.games.length ? `<div class="gm-games">${c.games.map((g) => {
      const run = playing.has(String(g.name).toLowerCase());
      return `<div class="gm-game ${g.on ? "" : "off"} ${run ? "run" : ""}">${gameIco(g.name, g.id, icons.has(g.id))}
        <div class="grow gm-gname" data-game="${esc(g.id)}" title="Impostazioni del gioco"><b>${esc(g.name)}</b><small>${run ? '<i class="dot"></i>in gioco adesso' : esc(GM_SRC[g.source] || g.source || "")}${g.anticheat ? " · anti-cheat" : ""}</small></div>
        <label class="switch"><input type="checkbox" data-on="${esc(g.id)}" ${g.on ? "checked" : ""}><span></span></label></div>`;
    }).join("")}</div>` : '<div class="empty">Nessun gioco trovato. Usa "Aggiungi" mentre il gioco e\' aperto.</div>'}
    <div class="gm-sec" style="margin-top:30px"><h2>Cosa fa durante il gioco</h2><span class="grow"></span><span class="mut gm-cnt">Clicca su una voce per sapere cosa fa</span></div>
    <div class="gm-groups">${groups.map(([t, col, ic, ids]) => `<div class="gm-group"><div class="gm-gh"><span class="ci" style="color:${col}">${icoSvg(ic)}</span>${t}</div>
      ${ids.map((id) => { const o = byId[id], n = note(id) || (o.default ? "" : "facoltativa");
        return `<div class="gm-row"><label class="switch"><input type="checkbox" data-opt="${id}" ${c.opts[id] ? "checked" : ""}><span></span></label>
          <span class="grow gm-oname" data-optdoc="${id}">${esc(GM_SHORT[id] || o.name)}</span>${n ? `<small>${esc(n)}</small>` : ""}</div>`; }).join("")}</div>`).join("")}</div>
    <p class="mut" style="font-size:12px;margin-top:22px">Le modifiche valgono dalla prossima apertura del gioco. Niente priorita' "In tempo reale": puo' bloccare mouse, tastiera e audio.</p>`;

  const post = async (body, msg) => {
    try { const x = await api("/api/gamemode", body); if (x && x.msg) toast(x.msg); else if (msg) toast(msg); }
    catch (e) { toast("Errore: " + e.message); }
    gamemodePage();
  };
  $("#gm-power").onclick = () => {
    $("#gm-power").disabled = true;
    if (c.enabled) { toast("Spengo la game mode e rimetto tutto com'era..."); post({ action: "disable" }); }
    else post({ action: "enable" }, "Game mode accesa");
  };
  $("#gm-scan").onclick = () => { $("#gm-scan").disabled = true; toast("Cerco i giochi installati..."); gamemodePage(true); };
  $("#gm-add").onclick = gmAdd;
  $$("[data-on]").forEach((x) => x.onchange = () => post({ action: "game", id: x.dataset.on, on: x.checked }));
  $$("[data-opt]").forEach((x) => x.onchange = () => post({ action: "opt", id: x.dataset.opt, value: x.checked }));
  $$("[data-optdoc]").forEach((x) => x.onclick = () => gmOptDialog(byId[x.dataset.optdoc], r));
  $$("[data-game]").forEach((x) => x.onclick = () => gmGameDialog(c.games.find((g) => g.id === x.dataset.game), r, post));
  const acts = $("#gm-acts"); if (acts) acts.onclick = () => { const m = modal(`<h2>Cosa ha fatto la game mode</h2><ul class="gm-actlist">${st.actions.map((a) => "<li>" + esc(a) + "</li>").join("")}</ul><div class="row" style="justify-content:flex-end"><button class="ghost" id="m-close">Chiudi</button></div>`); $("#m-close", m).onclick = closeModal; };
  $$(".gm-ico img").forEach((im) => im.onerror = () => { const sp = im.parentNode; sp.classList.remove("img"); sp.textContent = "?"; });
  const nav = $("#nav-gm"); if (nav) nav.hidden = !st.active;
  S.gmGames = (st.games || []).join(", ");
  const vb = $("#gm-ver-btn"); if (vb) vb.onclick = gmVerifyDialog;
  clearInterval(S.sensorTimer);
  let waitIcons = r.icons_pending ? 6 : 0;
  S.sensorTimer = setInterval(async () => {
    if (S.page !== "gamemode" || !$("#gm-status")) return clearInterval(S.sensorTimer);
    if (!$("#modal").hidden) return;  /* non ridisegno sotto una finestra aperta */
    try {
      const n = await api("/api/gamemode");
      const newIcons = (n.icons || []).length !== icons.size;
      if (newIcons) waitIcons = 0; else if (waitIcons) waitIcons--;
      if (n.status.active !== st.active || n.status.running !== st.running || newIcons ||
          (n.status.actions || []).length !== (st.actions || []).length) gamemodePage();
    } catch (e) { /* riprova al prossimo giro */ }
  }, 4000);
}
function gmOptDialog(o, r) {
  if (!o) return;
  const box = (html) => `<div class="gm-note">${html}</div>`;
  const cpu = r.cpu && r.cpu.cpu ? " (" + esc(r.cpu.cpu) + ")" : "";
  const extra = o.id === "affinity" ? box(`<b>Il tuo processore${cpu}:</b> ${r.cpu ? (r.cpu.apply ? "<b>affinita' utile</b>, verra' applicata. " : "<b>affinita' non utile</b>, non verra' applicata. ") + esc(r.cpu.why || "") : "non leggibile."}`)
    : o.id === "eco_bg" ? box(`<b>Il tuo processore${cpu}:</b> ${r.eco ? (r.eco.apply ? "<b>modalita' efficienza utile</b>, verra' usata. " : "<b>non serve</b>, resta la priorita' bassa. ") + esc(r.eco.why || "") : "non leggibile."}`)
    : o.id === "gpu_pref" ? box(`<b>Schede video di questo PC:</b> ${r.gpus && r.gpus.length ? esc(r.gpus.join(", ")) : "non leggibili"}. ${r.gpus && r.gpus.length >= 2 ? "<b>Due schede video</b>: l'opzione serve." : "<b>Una sola scheda video</b>: anche accesa non fa niente."}`) : "";
  const m = modal(`<h2>${esc(GM_SHORT[o.id] || o.name)}</h2><p>${esc(o.what)}</p>${extra}<p class="mut" style="font-size:13px"><b>Possibili problemi:</b> ${esc(o.risk)}</p>
    ${o.default ? "" : '<p class="mut" style="font-size:12.5px">Facoltativa: spenta all\'inizio, accendila se ti serve.</p>'}
    <div class="row" style="justify-content:flex-end"><button class="ghost" id="m-close">Chiudi</button></div>`);
  $("#m-close", m).onclick = closeModal;
}
function gmGameDialog(g, r, post) {
  if (!g) return;
  const where = g.match === "java" ? "riconosciuto da Java (javaw.exe) con: " + (g.keywords || []).join(", ") : g.match === "name" ? (g.exe_names || []).join(", ") : g.dir;
  const m = modal(`<div class="row" style="gap:14px;align-items:center;margin-bottom:6px">${gameIco(g.name, g.id, (r.icons || []).includes(g.id))}<div><h2 style="margin:0">${esc(g.name)}</h2><span class="mut" style="font-size:13px">${esc(GM_SRC[g.source] || g.source || "")}</span></div></div>
    <p class="mut" style="font-size:12.5px;word-break:break-all">${esc(where || "")}</p>
    ${g.anticheat ? `<div class="gm-note"><b>Anti-cheat: ${esc(g.anticheat)}.</b> Il processo del gioco e' protetto: LagDoctor non lo tocca. La priorita' la da' Windows stesso all'avvio del gioco (dalla seconda apertura); niente affinita' dei core.</div>` : ""}
    <label class="mut" style="font-size:13px;display:block;margin:14px 0 6px">Priorita' del gioco</label>
    <select id="m-prio">${r.priorities.map((p) => `<option value="${p.id}" ${g.priority === p.id ? "selected" : ""}>${esc(p.name)}</option>`).join("")}</select>
    <div class="row" style="justify-content:space-between;margin-top:20px"><button class="ghost danger-t" id="m-rm">Togli dall'elenco</button><button class="ghost" id="m-close">Chiudi</button></div>`);
  $("#m-close", m).onclick = closeModal;
  $("#m-prio", m).onchange = (e) => { closeModal(); post({ action: "game", id: g.id, priority: e.target.value }, "Priorita' salvata"); };
  $("#m-rm", m).onclick = () => { closeModal(); post({ action: "remove", id: g.id }, "Tolto dall'elenco"); };
}
/* verifica dal vivo delle ottimizzazioni della game mode: pannello a parte, si aggiorna da solo */
function gmVerifyHtml(r) {
  if (!r.active) return '<p class="mut">La game mode non e\' attiva in questo momento: apri un gioco della lista.</p>';
  const ico = (ok) => ok === true ? '<span class="vk ok">✓</span>' : ok === false ? '<span class="vk ko">✗</span>' : '<span class="vk na">•</span>';
  let html = `<div class="row" style="margin-bottom:6px"><b>${r.ok} ok</b>${r.ko ? `<span class="badge b-bad">${r.ko} non applicate</span>` : '<span class="badge b-ok">tutto applicato</span>'}<span class="grow"></span><span class="mut" style="font-size:12px">si aggiorna da solo</span></div>`;
  let last = "";
  r.items.forEach((i) => {
    if (i.group !== last) { html += `<div class="vgroup">${esc(i.group)}</div>`; last = i.group; }
    html += `<div class="vrow">${ico(i.ok)}<span class="grow">${esc(i.name)}</span><span class="mut">${esc(i.detail || "")}</span></div>`;
  });
  return html + '<p class="mut" style="font-size:12px;margin:10px 0 0">✓ applicata e controllata adesso in Windows · ✗ non applicata · • da sapere</p>';
}
async function gmVerifyDialog() {
  const m = modal(`<h2>Ottimizzazioni attive${S.gmGames ? " · " + esc(S.gmGames) : ""}</h2>
    <div id="gm-ver-body"><div class="row" style="gap:10px"><div class="spinner" style="width:20px;height:20px;margin:0"></div><span class="mut">Controllo lo stato reale di Windows...</span></div></div>
    <div class="row" style="justify-content:flex-end;margin-top:14px"><button class="ghost" id="m-close">Chiudi</button></div>`);
  m.classList.add("wide");
  let alive = true;
  $("#m-close", m).onclick = () => { alive = false; m.classList.remove("wide"); closeModal(); };
  const load = async () => {
    if (!alive || $("#modal").hidden || !$("#gm-ver-body")) { alive = false; m.classList.remove("wide"); return; }
    try { const r = await api("/api/gamemode/verify"); const box = $("#gm-ver-body"); if (box) box.innerHTML = gmVerifyHtml(r); } catch (e) { /* riprova */ }
    if (alive) setTimeout(load, 5000);
  };
  load();
}
async function gmAdd() {
  const pr = await api("/api/processes");
  const r = { items: pr.items.concat(pr.others || []) };
  const m = modal(`<h2>Aggiungi un gioco</h2>
    <p class="mut">Apri il gioco, poi sceglilo qui sotto. Oppure scrivi il percorso del file .exe.</p>
    ${r.items.length ? r.items.map((p, i) => `<div class="list-row"><div class="grow"><b>${esc(p.name)}</b> <span class="mut">${p.mem} MB</span><div class="mut" style="font-size:12px;word-break:break-all">${esc(p.exe || "")}</div></div><button data-add="${i}" ${p.exe ? "" : "disabled"}>Aggiungi</button></div>`).join("") : '<div class="empty">Nessun programma grande aperto.</div>'}
    <div style="display:flex;gap:8px;margin-top:10px"><input id="gm-path" placeholder="C:\\Giochi\\gioco.exe" style="flex:1"><button id="gm-path-ok">Aggiungi</button></div>
    <div style="text-align:right;margin-top:12px"><button class="ghost" id="m-close">Chiudi</button></div>`);
  const add = async (exe) => {
    try { await api("/api/gamemode", { action: "add", exe }); toast("Gioco aggiunto"); closeModal(); gamemodePage(); }
    catch (e) { toast("Errore: " + e.message); }
  };
  $$("[data-add]", m).forEach((b) => b.onclick = () => add(r.items[b.dataset.add].exe));
  $("#gm-path-ok", m).onclick = () => add($("#gm-path", m).value.trim());
  $("#m-close", m).onclick = closeModal;
}

/* ------------------------------------------------------------------ ANALIZZA GIOCO */
async function record() {
  const ctx = S.recCtx || {};
  if (S.rec) return recordLive();
  if (S.lastRecord && S.lastRecord.result && !ctx.label) return recordResult(S.lastRecord.result);
  const r = await api("/api/processes");
  const all = r.items.concat(S.recAll ? r.others || [] : []);
  let pick = r.items.length ? r.items[0].pid : null, dur = 300;
  const DURS = [60, 180, 300, 600, 1200];
  const durTxt = (v) => { const m = v / 60; return m + (m === 1 ? " minuto" : " minuti"); };
  const nameOf = (pid) => { const p = all.find((x) => x.pid === pid); return p ? p.game || p.name : "–"; };
  const gb = (m) => m >= 1024 ? (m / 1024).toFixed(1).replace(".", ",") + " GB di RAM" : m + " MB di RAM";
  const row = (p) => `<div class="ag-item pick ${p.pid === pick ? "on" : ""}" data-pid="${p.pid}">${gameIco(p.game || p.name, p.game_id, p.icon)}
    <div class="grow"><b>${esc(p.game || p.name)}</b><small>${p.source ? esc(GM_SRC[p.source] || p.source) + " · " : p.kind === "fullscreen" ? "a schermo intero · " : ""}${esc(p.name)}</small></div>
    <small class="mut">${gb(p.mem)}</small><span class="ag-radio"></span></div>`;
  main().innerHTML = `${recHead("rec", REC_SUB)}
    ${ctx.label ? `<div class="banner"><b>Registrazione ${esc(ctx.label)} per il test Prima / Dopo</b>${ctx.game ? `<br>Usa lo stesso gioco (<b>${esc(ctx.game)}</b>) e, se puoi, la stessa zona e la stessa durata.` : ""}</div>` : ""}
    <div class="ag-steps"><span><i>1</i>Apri il gioco ed entra in partita</span><span class="ln"></span><span><i>2</i>Scegli gioco e durata (torna qui con Alt+Tab)</span><span class="ln"></span><span><i>3</i>Torna a giocare</span></div>
    <div class="ag-grid"><div>
      <div class="gm-sec"><h2>Giochi aperti</h2><span class="grow"></span>${actBtn('id="reload"', "refresh", "Aggiorna", "sm", false)}</div>
      <div id="procs">${r.items.length ? `<div class="ag-list">${r.items.map(row).join("")}</div>`
        : `<div class="ag-empty">${icoSvg(GM_GROUPS[0][2])}<b>Nessun gioco aperto</b><span>Apri il gioco, entra in partita e premi Aggiorna.</span></div>`}
      ${S.recAll ? `<div class="gm-sec" style="margin-top:22px"><h2 style="font-size:15px">Altri programmi aperti</h2></div>${(r.others || []).length ? `<div class="ag-list">${r.others.map(row).join("")}</div>` : '<p class="mut">Nessun altro programma grande aperto.</p>'}` : ""}</div>
      <p class="ag-note">Vengono mostrati solo i giochi: quelli installati sul PC (Steam, Epic, Xbox, Riot, EA, Ubisoft, Battle.net, GOG, Minecraft e quelli aggiunti nella game mode), quelli nelle cartelle dei giochi e i programmi a schermo intero che usano la scheda video per disegnare. Browser, Discord e gli altri programmi non compaiono.
        <a id="rec-all">${S.recAll ? "Mostra solo i giochi" : "Il tuo gioco non c'e'? Mostra tutti i programmi aperti"}</a></p>
    </div><div>
      <div class="gm-sec"><h2>Durata</h2></div>
      <div class="ag-durs" id="durs">${DURS.map((v) => `<a data-d="${v}" class="${v === dur ? "on" : ""}">${v / 60} min</a>`).join("")}</div>
      <button class="big" id="start" style="width:100%;margin-top:18px" ${pick ? "" : "disabled"}><span class="rdot"></span>Avvia registrazione</button>
      <p class="mut tiny" style="margin-top:12px"><span id="rec-sum">${pick ? `Registro <b>${esc(nameOf(pick))}</b> per <b>${durTxt(dur)}</b>. ` : ""}</span>Dopo l'avvio torna nel gioco e gioca normalmente, soprattutto dove senti gli scatti. Alla fine LagDoctor ti mostra le cause e come risolverle.</p>
    </div></div>`;
  bindRecTabs();
  const sum = () => { $("#rec-sum").innerHTML = pick ? `Registro <b>${esc(nameOf(pick))}</b> per <b>${durTxt(dur)}</b>. ` : ""; };
  $("#reload").onclick = record;
  $("#rec-all").onclick = () => { S.recAll = !S.recAll; record(); };
  $$(".gm-ico img").forEach((im) => im.onerror = () => { const sp = im.parentNode; sp.classList.remove("img"); sp.textContent = "?"; });
  $$("#procs .pick").forEach((el) => el.addEventListener("click", () => {
    pick = Number(el.dataset.pid); $$("#procs .pick").forEach((x) => x.classList.toggle("on", x === el));
    sum(); $("#start").disabled = false;
  }));
  $$("#durs a").forEach((el) => el.addEventListener("click", () => {
    dur = Number(el.dataset.d); $$("#durs a").forEach((x) => x.classList.toggle("on", x === el)); sum();
  }));
  if (r.icons_pending && !S.recIconRetry) { S.recIconRetry = true; setTimeout(() => { S.recIconRetry = false; if (S.page === "record" && !S.rec && $("#procs")) record(); }, 5000); }
  $("#start").onclick = async () => {
    try {
      const job = await api("/api/record", { pid: pick, seconds: dur, label: ctx.label || "" });
      pollRecording(job); recordLive();
    } catch (e) { toast("Errore: " + e.message); }
  };
}
/* un solo controllo della registrazione, indipendente dalla pagina aperta */
async function pollRecording(job) {
  S.rec = { job, live: null, messages: [] };
  try {
    const done = await runJob(Promise.resolve(job), (j) => { S.rec.live = j.live; S.rec.messages = j.messages; if (S.page === "record") updateLive(); });
    S.rec = null; S.lastRecord = { result: done.result };
    const ctx = S.recCtx; S.recCtx = null;
    if (ctx && ctx.onDone) { S.lastRecord = null; return ctx.onDone(done.result); }
    if (S.page === "record") recordResult(done.result); else toast("Analisi completata: apri 'Analizza gioco' per vedere il risultato.", 6000);
  } catch (e) {
    S.rec = null; S.recCtx = null; S.lastRecord = null;
    /* passo ad Analizza gioco senza disegnare la pagina: qui sotto mostro l'errore */
    S.navTok = (S.navTok || 0) + 1; S.page = "record"; clearInterval(S.sensorTimer);
    $$("#nav a").forEach((a) => a.classList.toggle("active", a.dataset.page === "record"));
    main().classList.remove("sw-out", "fade");
    main().innerHTML = `<h1>Registrazione non riuscita</h1><div class="prob s3"><p style="white-space:pre-line">${esc(e.message)}</p></div>
      <div class="row"><button id="again">Riprova</button>${/PresentMon/.test(e.message) ? '<button class="ghost" id="pm-page">Apri la pagina di download di PresentMon</button>' : ""}</div>`;
    if ($("#pm-page")) $("#pm-page").onclick = () => window.open("https://github.com/GameTechDev/PresentMon/releases", "_blank");
    $("#again").onclick = record;
  }
}
function updateLive() {
  if (!S.rec || !$("#l-fps")) return;
  logList($("#r-log"), S.rec.messages);
  const l = S.rec.live; if (!l) return;
  $("#l-fps").textContent = fmt(l.fps); $("#l-left").textContent = Math.floor(l.left / 60) + ":" + String(Math.floor(l.left % 60)).padStart(2, "0");
  $("#l-worst").textContent = l.worst ? fmt(l.worst, 1) + " ms" : "–";
  $("#l-gpu").textContent = l.gpu_util != null ? fmt(l.gpu_util) + "%" + (l.gpu_temp != null ? " · " + fmt(l.gpu_temp) + "°" : "") : "–";
  drawFrames($("#cv"), l.frames);
}
function drawFrames(cv, frames) {
  const dpr = window.devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight;
  cv.width = w * dpr; cv.height = h * dpr; const c = cv.getContext("2d"); c.scale(dpr, dpr);
  c.clearRect(0, 0, w, h);
  if (!frames || !frames.length) { c.fillStyle = "#8f98a8"; c.fillText("In attesa dei primi frame... torna nel gioco", 14, 24); return; }
  const sorted = frames.slice().sort((a, b) => a - b), med = sorted[Math.floor(sorted.length / 2)];
  const top = Math.max(med * 3, Math.min(Math.max(...frames) * 1.15, 120), 20);
  c.strokeStyle = "#262c37"; c.fillStyle = "#8f98a8"; c.font = "11px Segoe UI";
  [8.3, 16.7, 33.3, 50, 100].forEach((ms) => { if (ms < top) { const y = h - ms / top * (h - 10); c.beginPath(); c.moveTo(0, y); c.lineTo(w, y); c.stroke(); c.fillText(ms + " ms", 6, y - 3); } });
  c.beginPath(); c.strokeStyle = "#3fbf7f"; c.lineWidth = 1.5;
  frames.forEach((f, i) => { const x = i / (frames.length - 1 || 1) * w, y = h - Math.min(f, top) / top * (h - 10); i ? c.lineTo(x, y) : c.moveTo(x, y); }); c.stroke();
  c.fillStyle = "rgba(229,72,77,.7)";
  frames.forEach((f, i) => { if (f > med * 2 && f - med > 8) { const x = i / (frames.length - 1 || 1) * w; c.fillRect(x - 1.5, 0, 3, h); } });
}
function recordLive() {
  main().innerHTML = `${recHead("rec", REC_SUB)}
    <div class="card live-hero"><span class="rec-dot"></span><div class="grow"><b>Registrazione in corso</b>
      <p class="mut">Torna nel gioco e gioca normalmente, soprattutto dove senti gli scatti. Puoi lasciare questa finestra aperta.</p></div>
      <button class="red" id="stop">Ferma ora e analizza</button></div>
    <div class="stats">
      <div class="stat"><small>${ic("fps")}FPS</small><b id="l-fps">–</b></div>
      <div class="stat"><small>${ic("clock")}Tempo rimasto</small><b id="l-left">–</b></div>
      <div class="stat warn"><small>${ic("bolt")}Frame peggiore</small><b id="l-worst">–</b></div>
      <div class="stat"><small>${ic("gpu")}GPU</small><b id="l-gpu">–</b></div>
    </div>
    <div class="card chart-card"><div class="rg-ph"><h4>Tempo di ogni frame</h4>
      <div class="lg"><span><i style="background:#3fbf7f"></i>frame (piu' piatta = piu' fluido)</span><span><i style="background:#e5484d"></i>stutter</span></div></div>
      <canvas id="cv"></canvas></div>
    <ul class="log" id="r-log"></ul>`;
  bindRecTabs();
  $("#stop").onclick = () => { if (!S.rec) return; api("/api/stop", { id: S.rec.job.id }); $("#stop").disabled = true; $("#stop").textContent = "Fermo e analizzo..."; };
  updateLive();
}
function recordResult(r) {
  const s = r.session;
  const sm = s.stutter_min || 0, grade = sm < 1 ? ["ok", "Fluido"] : sm < 4 ? ["warn", "Qualche scatto"] : ["bad", "Molti scatti"];
  const lowCls = s.fps_medi && s.fps_1low ? (s.fps_1low / s.fps_medi >= 0.7 ? "ok" : s.fps_1low / s.fps_medi >= 0.5 ? "warn" : "bad") : "";
  main().innerHTML = `${recHead("rec", REC_SUB)}
    <div class="card res-hero"><span class="pav">${esc((s.gioco || "?").slice(0, 1).toUpperCase())}</span>
      <div><h2>${esc(s.gioco)}</h2><p>${esc(s.data)} · ${Math.round(s.durata_s / 60)} minuti · sessione #${s.id}</p></div>
      <span class="grade ${grade[0]}">${grade[1]}</span></div>
    <div class="stats">
      <div class="stat"><small>${ic("fps")}FPS medi</small><b>${fmt(s.fps_medi)}</b></div>
      <div class="stat ${lowCls}"><small>${ic("low")}1% low</small><b>${fmt(s.fps_1low)}</b><span>${s.fps_p1 ? "a percentile: " + fmt(s.fps_p1) : ""}</span></div>
      <div class="stat ${lowCls}"><small>${ic("low")}0.1% low</small><b>${fmt(s.fps_01low)}</b><span>${s.fps_p01 ? "a percentile: " + fmt(s.fps_p01) : ""}</span></div>
      <div class="stat ${grade[0]}"><small>${ic("bolt")}Stutter / min</small><b>${fmt(s.stutter_min, 1)}</b></div>
      ${r.breakdown && r.breakdown.gpu_util_avg != null ? `<div class="stat"><small>${ic("gpu")}GPU media</small><b>${fmt(r.breakdown.gpu_util_avg)}%</b></div>` : ""}
    </div>
    <p class="mut" style="font-size:12.5px;margin:-4px 0 12px">1% / 0.1% low = FPS medi dei frame peggiori (metodo severo). "A percentile" = metodo di PresentMon: se e' molto piu' alto, i bassi dipendono da pochi blocchi lunghi (vedi sotto), non da un gioco irregolare.</p>
    ${longHtml(r.breakdown, s)}
    <div class="row">${actBtn('id="rep"', "report", "Apri report con grafico")}${actBtn('id="again"', "rec", "Nuova registrazione")}</div>
    ${breakdownHtml(r.breakdown)}
    <h2>Cause trovate e soluzioni</h2>${probHtml(r.problems)}
    ${factorsHtml(r.factors)}
    ${detailHtml(r.detail)}
    <h2>Altre informazioni</h2><div class="card"><ul>${r.info.map((i) => "<li>" + esc(i) + "</li>").join("")}</ul></div>`;
  $("#rep").onclick = () => window.open(reportUrl(r.report), "_blank");
  $("#again").onclick = () => { S.lastRecord = null; record(); };
  bindRecTabs();
  bindFixButtons(main());
  bindFactors(r);
}
const KIND_COLORS = { dpc: "#e5484d", disk: "#f5a524", paging: "#ff7a45", vram: "#c084fc", background: "#facc15",
  cpu_throttle: "#fb923c", gpu_throttle: "#f97316", shader: "#3e9bff", main_thread: "#22d3ee", gpu_spike: "#a3e635",
  vsync: "#94a3b8", present: "#e879f9", system: "#64748b" };
function breakdownHtml(b) {
  if (!b || !b.kinds || !b.kinds.length) return "";
  const bound = b.bound ? `<div class="bound">
      <div style="width:${b.bound.gpu}%;background:#a3e635" title="GPU"></div><div style="width:${b.bound.cpu}%;background:#22d3ee" title="CPU"></div><div style="width:${b.bound.limitato}%;background:#64748b" title="Limitato"></div></div>
      <p class="mut" style="font-size:13px;margin:4px 0 0">Collo di bottiglia, frame per frame (NON e' l'utilizzo): il limite era la <b style="color:#a3e635">GPU nel ${fmt(b.bound.gpu)}%</b> dei frame, la <b style="color:#22d3ee">CPU nel ${fmt(b.bound.cpu)}%</b>, il <b>V-Sync o un limite FPS nel ${fmt(b.bound.limitato)}%</b>.${b.gpu_util_avg != null ? ` Utilizzo medio della GPU: <b>${fmt(b.gpu_util_avg)}%</b>.` : ""}${b.cap_fps ? ` Limite FPS rilevato: <b>${b.cap_fps} FPS</b> (gioco, driver o V-Sync).` : ""}</p>` : "";
  return `<h2>Di cosa sono fatti gli stutter</h2><div class="card">
    <div class="kbar">${b.kinds.map((k) => `<div title="${esc(k[3])}" style="width:${k[2]}%;background:${KIND_COLORS[k[0]] || "#888"}"></div>`).join("")}</div>
    <div class="klegend">${b.kinds.map((k) => `<div><span style="background:${KIND_COLORS[k[0]] || "#888"}"></span>${esc(k[3])}: <b>${k[1]}</b> (${fmt(k[2])}%)</div>`).join("")}</div>
    ${bound}
    <p class="mut" style="font-size:12.5px;margin:8px 0 0">Ogni stutter e' classificato guardando quale parte del frame si e' allungata (lavoro CPU, lavoro GPU o attesa) e cosa succedeva nel sistema in quel quarto di secondo.</p></div>`;
}
function longHtml(b, s) {
  const L = (b && b.long_frames) || [];
  if (!L.length) return "";
  const share = b.long_share_low;
  return `<div class="card" style="margin-bottom:12px"><b>Blocchi lunghi (frame da 100 ms o piu'): ${s.long_100 || L.length}${s.long_250 ? `, di cui ${s.long_250} oltre 250 ms` : ""}</b>
    <p class="mut" style="font-size:13px;margin:4px 0 8px">${share != null ? `Sono il ${fmt(share)}% dei frame che fanno lo 0.1% low. ` : ""}Guarda i minuti: se corrispondono a salvataggi automatici, apertura della mappa/menu o caricamento di una zona, sono pause del gioco e non stutter durante la guida.</p>
    <div style="display:flex;flex-wrap:wrap;gap:6px">${L.sort((a, c) => a.t - c.t).map((x) => `<span class="badge">${Math.floor(x.t / 60)}:${String(Math.floor(x.t % 60)).padStart(2, "0")} · ${fmt(x.ft)} ms</span>`).join("")}</div></div>`;
}
function detailHtml(d) {
  if (!d || !d.length) return "";
  const cls = { alta: "b-ok", media: "b-acc", bassa: "" };
  return `<details><summary>Gli stutter peggiori, uno per uno (${d.length})</summary><div class="card"><table>
    <tr><th>Momento</th><th>Frame</th><th>Normale</th><th>Causa e prove misurate</th><th>Certezza</th></tr>
    ${d.map((x) => `<tr><td>${Math.floor(x.t / 60)}:${String(Math.floor(x.t % 60)).padStart(2, "0")}</td><td>${fmt(x.ft, 1)} ms</td><td>${fmt(x.med, 1)} ms</td>
      <td><b>${esc(x.label)}</b><div class="mut" style="font-size:12.5px">${esc(x.evidence || "")}${x.detail ? (x.evidence ? " · " : "") + esc(x.detail) : ""}</div></td>
      <td><span class="badge ${cls[x.conf] || ""}">${esc(x.conf)}</span></td></tr>`).join("")}</table></div></details>`;
}
function factorsHtml(f) {
  if (!f || !f.length) return "";
  return `<h2>Impostazioni del tuo PC collegate a questi stutter</h2>
    <p class="mut" style="margin-top:-4px">Controllo fatto sulle impostazioni attuali di Windows, del driver video e delle ottimizzazioni.</p>
    ${f.map((x) => `<div class="fac"><h4>${esc(x.titolo)}</h4>
      ${x.peggiora.length ? `<p style="color:var(--bad);margin:4px 0">Attive ora: PEGGIORANO il problema</p><div class="lst">${x.peggiora.map((i) => `
        <div class="it"><div class="grow"><b>${esc(i.label || i.name)}</b><p>${esc(i.why || "")}</p></div>
        ${i.myth ? `<button class="sm red" data-foff="${i.id}">Disattiva</button>`
          : i.undo ? `<button class="sm red" data-fundo="${i.id}">Annulla</button>`
          : i.kind === "on_bad" ? `<span class="mut" style="font-size:12px;max-width:180px">ottimizzazione attiva che qui peggiora: valuta di toglierla</span>`
          : `<button class="sm" data-fapply="${i.id}" title="${esc(i.name)}">Correggi</button>`}</div>`).join("")}</div>` : ""}
      ${x.aiuta.length ? `<p style="color:var(--ok);margin:10px 0 4px">Non attive: potrebbero AIUTARE</p><div class="lst">${x.aiuta.map((i) => `
        <label class="it"><input type="checkbox" data-fhelp="${i.id}"><div class="grow"><b>${esc(i.name)}</b> <span class="badge">${esc(i.risk)}</span><p>${esc(i.why || "")}</p></div></label>`).join("")}</div>` : ""}
    </div>`).join("")}
    <div class="row"><button class="ghost" id="fac-apply" disabled>Applica le selezionate</button><button class="ghost" id="fac-test" disabled>Provale con il test Prima / Dopo</button></div>`;
}
function bindFactors(r) {
  $$("[data-foff]").forEach((b) => b.addEventListener("click", async () => { b.disabled = true; await forceOff(b.dataset.foff); b.textContent = "Fatto"; }));
  $$("[data-fapply]").forEach((b) => b.addEventListener("click", () => applySelected([b.dataset.fapply], () => toast("Correzione applicata."))));
  $$("[data-fundo]").forEach((b) => b.addEventListener("click", () => revertIds([b.dataset.fundo])));
  const sel = () => [...new Set($$("[data-fhelp]:checked").map((c) => c.dataset.fhelp))];
  $$("[data-fhelp]").forEach((c) => c.addEventListener("change", () => { const n = sel().length; if ($("#fac-apply")) { $("#fac-apply").disabled = !n; $("#fac-test").disabled = !n; } }));
  if ($("#fac-apply")) {
    $("#fac-apply").onclick = () => applySelected(sel(), () => toast("Ottimizzazioni applicate."));
    $("#fac-test").onclick = () => applySelected(sel(), async (res) => {
      const ok = res.filter((x) => x.ok).map((x) => x.id);
      if (!ok.length) return;
      await api("/api/experiment/start", { game: r.session.gioco, before: r.session.id, ids: ok });
      S.recTab = "exp"; go("record");
    });
  }
}

/* ------------------------------------------------------------------ PRIMA / DOPO */
async function exp() {
  await refreshState(); await loadCatalog();
  const e = S.state.experiment;
  if (e) {
    const names = e.modifiche.map((id) => (tws().find((t) => t.id === id) || { name: id }).name);
    main().innerHTML = `${recHead("exp", "Scopri se un'ottimizzazione serve DAVVERO sul tuo PC.")}<h2 style="margin-top:0">Test prima/dopo in corso</h2><p class="sub">Gioco: <b>${esc(e.gioco)}</b> · sessione PRIMA #${e.prima}</p>
      <div class="card"><b>Modifiche in prova</b><ul>${names.map((n) => "<li>" + esc(n) + "</li>").join("")}</ul></div>
      <p class="mut">Se alcune modifiche richiedevano il riavvio, assicurati di aver riavviato il PC.</p>
      <div class="row"><button id="after">Registra la partita DOPO</button><button class="ghost danger" id="cancel">Interrompi il test</button></div>`;
    bindRecTabs();
    $("#after").onclick = () => { S.lastRecord = null; S.recTab = "rec"; S.recCtx = { label: "DOPO", game: e.gioco, onDone: (r) => expResult(e, r) }; go("record"); };
    $("#cancel").onclick = async () => { await api("/api/experiment/end", {}); toast("Test interrotto (le modifiche restano applicate)."); exp(); };
    return;
  }
  const ss = await api("/api/sessions");
  let before = null;
  main().innerHTML = `${recHead("exp", "Scopri se un'ottimizzazione serve DAVVERO sul tuo PC.")}
    <div class="note">Registri una partita, applichi le modifiche, ne registri un'altra e LagDoctor confronta. Consiglio: poche modifiche alla volta, stessa zona e stessa durata.</div>
    <div class="sec"><span>1</span><h2>Partita PRIMA delle modifiche</h2></div>
    <div id="bef">${ss.items.length ? ss.items.slice(0, 8).map((s) => `<div class="list-row pick" data-id="${s.id}"><b class="grow">#${s.id} ${esc(s.gioco)}</b><span class="mut">${esc(s.data)}</span><span>FPS ${fmt(s.fps_medi)} · 1% ${fmt(s.fps_1low)} · stutter/min ${fmt(s.stutter_min, 1)}</span></div>`).join("") : '<div class="empty">Nessuna sessione registrata.</div>'}</div>
    <div class="row" style="margin-top:8px">${actBtn('id="rec-before"', "rec", "Registra adesso la partita PRIMA")}</div>
    <div class="sec"><span>2</span><h2>Modifiche da provare</h2></div><div id="exp-tw"><p class="mut">Scegli prima la partita PRIMA.</p></div>`;
  bindRecTabs();
  $("#rec-before").onclick = () => { S.lastRecord = null; S.recTab = "rec"; S.recCtx = { label: "PRIMA", onDone: () => { toast("Partita PRIMA registrata."); go("exp"); } }; go("record"); };
  $$("#bef .pick").forEach((el) => el.addEventListener("click", () => {
    $$("#bef .pick").forEach((x) => x.classList.toggle("on", x === el));
    before = ss.items.find((s) => s.id === Number(el.dataset.id));
    const cands = toFix().filter((t) => t.kind !== "myth").concat(notActive());
    const chosen = new Set();
    $("#exp-tw").innerHTML = cands.map((t) => `<label class="tw"><input type="checkbox" value="${t.id}"><div><b>${esc(t.name)}</b> ${t.recommended === true ? '<span class="badge b-acc">consigliata</span>' : ""}</div>
      <div class="meta"><span class="badge ${riskCls[t.risk]}">${t.risk_label}</span><span class="badge ${effCls[t.efficacy] || ""}">eff. ${t.efficacy}</span>${t.reboot ? '<span class="badge">riavvio</span>' : ""}</div></label>`).join("")
      + '<div class="bar"><span class="grow mut" id="exp-n">Scegli le modifiche da provare</span><button id="exp-go" disabled>Applica e avvia il test</button></div>';
    $$("#exp-tw input").forEach((c) => c.addEventListener("change", () => { c.checked ? chosen.add(c.value) : chosen.delete(c.value); $("#exp-n").textContent = chosen.size + " modifiche scelte"; $("#exp-go").disabled = !chosen.size; }));
    $("#exp-go").onclick = () => applySelected([...chosen], async (res) => {
      const ok = res.filter((r) => r.ok).map((r) => r.id);
      if (!ok.length) return toast("Nessuna modifica applicata: test non avviato.");
      await api("/api/experiment/start", { game: before.gioco, before: before.id, ids: ok });
      exp();
    });
  }));
}
async function expResult(e, r) {
  S.page = "record"; S.recTab = "exp"; $$("#nav a").forEach((a) => a.classList.toggle("active", a.dataset.page === "record"));
  const c = await api(`/api/compare?a=${e.prima}&b=${r.session.id}`);
  const names = e.modifiche.map((id) => (tws().find((t) => t.id === id) || { name: id }).name);
  main().innerHTML = `${recHead("exp", "Scopri se un'ottimizzazione serve DAVVERO sul tuo PC.")}<h2 style="margin-top:0">Risultato del test</h2><p class="sub">${esc(e.gioco)} · modifiche provate: ${names.map(esc).join(", ")}</p>
    ${compareHtml(c)}
    <div class="row" style="margin-top:16px"><button id="keep">Tieni le modifiche</button><button class="ghost danger" id="undo">Annulla le modifiche provate</button><button class="ghost" id="rep">Report della partita DOPO</button></div>`;
  bindRecTabs();
  $("#keep").onclick = async () => { await api("/api/experiment/end", {}); toast("Modifiche mantenute."); go("home"); };
  $("#undo").onclick = async () => { await api("/api/experiment/end", {}); await revertIds(e.modifiche); };
  $("#rep").onclick = () => window.open(reportUrl(r.report), "_blank");
  refreshState();
}
function compareHtml(c) {
  return `<div class="card"><div class="verdict ${c.verdict.replace(/ /g, "_")}">${esc(c.verdict)}</div><p>${esc(c.why)}</p>
    ${!c.same_game ? '<p class="mut">Attenzione: sono due giochi diversi.</p>' : ""}
    <table><tr><th></th><th>PRIMA</th><th>DOPO</th><th>Differenza</th></tr>
    ${c.rows.map((x) => `<tr><td>${esc(x.label)}</td><td>${fmt(x.a, 1)}</td><td>${fmt(x.b, 1)}</td><td style="color:${Math.abs(x.pct) < 3 ? "var(--mut)" : x.better ? "var(--ok)" : "var(--bad)"}">${x.pct > 0 ? "+" : ""}${fmt(x.pct, 1)}%</td></tr>`).join("")}</table>
    ${c.added.length || c.removed.length ? `<p class="mut">Modifiche diverse tra le due sessioni: ${c.added.map((n) => "+ " + esc(n)).concat(c.removed.map((n) => "− " + esc(n))).join(", ")}</p>` : ""}</div>`;
}

/* ------------------------------------------------------------------ SESSIONI */
async function sessions() {
  const ss = await api("/api/sessions");
  const sel = new Set();
  const exp = S.state && S.state.experiment;
  main().innerHTML = `${recHead("sessions", "Le partite registrate. Seleziona due sessioni per confrontarle, o quelle da eliminare.")}
    ${ss.items.length ? `<div class="sess-tools"><span class="mut">${ss.items.length} ${ss.items.length === 1 ? "sessione" : "sessioni"}</span>
        <label class="chk"><input type="checkbox" id="sel-all"> Seleziona tutte</label><span class="grow"></span>
        ${actBtn('id="del-sel" disabled', "trash", "Elimina selezionate", "sm danger", false)}</div>
      <div class="card stbl"><table><tr><th></th><th>#</th><th>Gioco</th><th>Data</th><th>Tipo</th><th>FPS</th><th>1% low</th><th>Stutter/min</th><th></th></tr>
      ${ss.items.map((s) => `<tr data-row="${s.id}"><td><input type="checkbox" value="${s.id}"></td><td class="mut">${s.id}</td><td><b>${esc(s.gioco)}</b></td><td class="mut">${esc(s.data)}</td><td>${s.etichetta ? `<span class="badge ${s.etichetta === "DOPO" ? "b-ok" : "b-acc"}">${esc(s.etichetta)}</span>` : ""}</td>
      <td><b>${fmt(s.fps_medi)}</b></td><td>${fmt(s.fps_1low)}</td><td>${fmt(s.stutter_min, 1)}</td>
      <td class="row-acts">${s.report ? actBtn(`data-rep="${esc(base(s.report))}"`, "report", "Report", "sm", false) : ""}<button class="del-one" data-del="${s.id}" title="Elimina questa sessione" aria-label="Elimina la sessione ${s.id}">${ic("trash")}</button></td></tr>`).join("")}</table></div>`
      : '<div class="empty">Nessuna sessione: registra una partita dalla scheda Registra.</div>'}
    <div id="cmp"></div>
    <div class="bar"><span class="grow mut" id="cmp-n">Seleziona 2 sessioni per confrontarle (la prima e' il PRIMA)</span><button id="cmp-go" disabled>Confronta</button></div>`;
  bindRecTabs();
  $$("[data-rep]").forEach((b) => (b.onclick = () => window.open(reportUrl(b.dataset.rep), "_blank")));
  const upd = () => {
    const ids = [...sel];
    $("#cmp-go").disabled = ids.length !== 2;
    $("#cmp-n").textContent = ids.length === 2 ? `PRIMA #${Math.min(...ids)} → DOPO #${Math.max(...ids)}`
      : ids.length ? `${ids.length} ${ids.length === 1 ? "sessione selezionata" : "sessioni selezionate"}${ids.length > 2 ? " (per confrontare scegline 2)" : ""}`
      : "Seleziona 2 sessioni per confrontarle (la prima e' il PRIMA)";
    if ($("#del-sel")) { $("#del-sel").disabled = !ids.length; $("#del-sel span:nth-child(2)").textContent = ids.length ? `Elimina selezionate (${ids.length})` : "Elimina selezionate"; }
    if ($("#sel-all")) $("#sel-all").checked = ids.length === ss.items.length;
    $$("tr[data-row]").forEach((r) => r.classList.toggle("on", sel.has(Number(r.dataset.row))));
  };
  $$("td input").forEach((c) => c.addEventListener("change", () => { c.checked ? sel.add(Number(c.value)) : sel.delete(Number(c.value)); upd(); }));
  if ($("#sel-all")) $("#sel-all").onchange = (e) => { $$("td input").forEach((c) => { c.checked = e.target.checked; c.checked ? sel.add(Number(c.value)) : sel.delete(Number(c.value)); }); upd(); };
  const del = (ids) => {
    const list = ss.items.filter((x) => ids.includes(x.id));
    const prot = exp && ids.includes(exp.prima);
    const m = modal(`<h2>Eliminare ${ids.length === 1 ? "la sessione" : ids.length + " sessioni"}?</h2>
      <p>Vengono cancellati anche ${ids.length === 1 ? "il suo report e i dati registrati" : "i loro report e i dati registrati"}. Non si puo' annullare.</p>
      <ul>${list.slice(0, 6).map((x) => `<li>#${x.id} ${esc(x.gioco)} <span class="mut">· ${esc(x.data)}</span></li>`).join("")}${list.length > 6 ? `<li class="mut">e altre ${list.length - 6}...</li>` : ""}</ul>
      ${prot ? `<div class="banner">La sessione #${exp.prima} e' la partita PRIMA del test Prima / Dopo in corso: resta.</div>` : ""}
      <div class="row" style="justify-content:flex-end"><button class="ghost" id="m-cancel">Annulla</button><button class="red" id="m-ok">Elimina</button></div>`);
    $("#m-cancel", m).onclick = closeModal;
    $("#m-ok", m).onclick = async () => {
      $("#m-ok", m).disabled = true;
      try {
        const r = await api("/api/sessions/delete", { ids });
        closeModal();
        const rows = ids.map((i) => $(`tr[data-row="${i}"]`)).filter((x) => x && !(prot && Number(x.dataset.row) === exp.prima));
        if (!noAnim()) { rows.forEach((x) => x.classList.add("row-out")); await wait(260); }
        toast(r.msg);
        if (S.lastRecord && S.lastRecord.result && ids.includes(S.lastRecord.result.session.id)) S.lastRecord = null;
        sessions();
      } catch (e) { toast("Errore: " + e.message); closeModal(); }
    };
  };
  if ($("#del-sel")) $("#del-sel").onclick = () => sel.size && del([...sel]);
  $$("[data-del]").forEach((b) => (b.onclick = () => del([Number(b.dataset.del)])));
  $("#cmp-go").onclick = async () => { const ids = [...sel]; const c = await api(`/api/compare?a=${Math.min(...ids)}&b=${Math.max(...ids)}`); $("#cmp").innerHTML = "<h2>Confronto</h2>" + compareHtml(c); animIn([$("#cmp")]); };
}

/* ------------------------------------------------------------------ azioni globali */
$("#btn-folder").onclick = () => api("/api/open_folder", {}).catch((e) => toast(e.message));
$("#btn-quit").onclick = async () => { await api("/api/quit", {}).catch(() => {}); document.body.innerHTML = '<div class="loading"><p>Chiudo LagDoctor...</p></div>'; };
$("#btn-restore").onclick = () => {
  const m = modal(`<h2>Ripristina tutto</h2><p>Annullo <b>tutte</b> le modifiche fatte da LagDoctor (impostazioni e programmi all'avvio) e riporto i valori originali.</p>
    <div class="row" style="justify-content:flex-end"><button class="ghost" id="m-cancel">Annulla</button><button class="red" id="m-ok">Ripristina</button></div>`);
  $("#m-cancel", m).onclick = closeModal;
  $("#m-ok", m).onclick = async () => {
    m.innerHTML = '<h2>Ripristino...</h2><div class="spinner"></div><ul class="log" id="m-log"></ul>';
    try { await runJob(api("/api/restore_all", {}), (j) => logList($("#m-log"), j.messages)); await loadCatalog(true); m.innerHTML = '<h2>Fatto</h2><p>Se alcune modifiche richiedevano il riavvio, riavvia il PC.</p><button id="m-close">Chiudi</button>'; $("#m-close", m).onclick = () => { closeModal(); go(S.page); }; }
    catch (e) { m.innerHTML = `<h2>Errore</h2><p>${esc(e.message)}</p><button id="m-close">Chiudi</button>`; $("#m-close", m).onclick = closeModal; }
  };
};
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal" && !$(".spinner", $("#modal"))) closeModal(); });

/* ------------------------------------------------------------------ AGGIORNAMENTI */
function showUpdateBar(u) {
  const bar = $("#update-bar");
  $("#nav-upd").hidden = !u.available;
  $("#btn-update").title = u.available ? "Aggiornamento disponibile: LagDoctor " + u.latest : "";
  if (!u.available) { bar.hidden = true; return; }
  bar.hidden = false;
  bar.innerHTML = `<b>Nuova versione: LagDoctor ${esc(u.latest)}</b><span class="grow mut">Hai la ${esc(u.current)}. Le tue modifiche e i backup restano dove sono.</span><button class="sm" id="upd-open">Vedi e aggiorna</button>`;
  $("#upd-open").onclick = () => updateDialog(u);
}
async function checkUpdates(force) {
  try { const u = await api("/api/update" + (force ? "?force=1" : "")); showUpdateBar(u); return u; }
  catch (e) { return { error: e.message }; }
}
async function updateDialog(u) {
  if (!u) {
    const m0 = modal('<h2>Aggiornamenti</h2><div class="spinner"></div><p class="mut" style="text-align:center">Controllo su GitHub...</p>');
    u = await checkUpdates(true);
    if (!m0.isConnected) return;
  }
  const ver = `<p class="mut">Versione installata: <b>${esc(u.current || (S.state && S.state.version) || "?")}</b>${u.latest ? " · ultima pubblicata: <b>" + esc(u.latest) + "</b>" : ""}</p>`;
  let body;
  if (u.error) body = `${ver}<p>Non riesco a controllare gli aggiornamenti: ${esc(u.error)}.</p>`;
  else if (!u.available) body = `${ver}<p>Hai gia' l'ultima versione.</p>`;
  else if (!u.installed) body = `${ver}<p>C'e' una versione nuova. L'aggiornamento automatico funziona nella versione <b>installata</b> (LagDoctor-Setup.exe): scaricala dalla pagina delle versioni e installala una volta, poi gli aggiornamenti saranno automatici.</p>${u.notes ? `<h3>Novita'</h3><div class="notes">${esc(u.notes)}</div>` : ""}`;
  else body = `${ver}<h3>Novita'</h3><div class="notes">${esc(u.notes || "Nessuna descrizione.")}</div><p class="mut" style="font-size:13px">LagDoctor scarica l'installatore, controlla che il file sia integro, si chiude e si riapre aggiornato (circa 1 minuto). Le modifiche applicate, i backup e i report restano. Se la game mode e' accesa viene fermata (ripristinando tutto) e riparte da sola.</p>`;
  const m = modal(`<h2>Aggiornamenti</h2>${body}
    <div class="upd-prog" id="upd-prog" hidden><div class="upd-step" id="upd-step">Avvio...</div>
      <div class="upd-line"><div class="upd-track"><span id="upd-fill"></span></div><b id="upd-pct">0%</b></div></div>
    <div class="row" style="justify-content:flex-end">${!u.installed || u.error || !u.available ? `<button class="ghost" id="upd-page">Pagina delle versioni</button>` : ""}<button class="ghost" id="m-close">Chiudi</button>${u.available && u.installed ? '<button id="upd-go">Aggiorna ora</button>' : ""}</div>`);
  $("#m-close", m).onclick = closeModal;
  const pg = $("#upd-page", m); if (pg) pg.onclick = () => window.open(u.page, "_blank");
  const go = $("#upd-go", m);
  if (go) go.onclick = async () => {
    go.disabled = true; $("#m-close", m).disabled = true; go.textContent = "Aggiorno...";
    try {
      $("#upd-prog", m).hidden = false;
      const job = await runJob(api("/api/update/install", {}), (j) => updProgress(m, j.messages[j.messages.length - 1] || ""));
      updProgress(m, "fatto");
      if (job.result && job.result.restarting) {
        m.innerHTML = '<h2>Installazione in corso...</h2><div class="spinner"></div><p>Questa finestra si chiude ora: LagDoctor si riapre da solo, aggiornato, tra circa un minuto.</p>';
        setTimeout(() => { try { window.close(); } catch (e) { /* ci pensa il programma */ } }, 1500);
      } else { toast(job.result && job.result.msg || "Fatto"); closeModal(); }
    } catch (e) { toast("Aggiornamento non riuscito: " + e.message, 9000); go.disabled = false; $("#m-close", m).disabled = false; go.textContent = "Riprova"; }
  };
}
/* barra di avanzamento dell'aggiornamento: un solo passo alla volta, con la percentuale */
function updProgress(m, msg) {
  let pct = 3, step = "Controllo l'ultima versione...";
  const d = /(\d+)%\s*$/.exec(msg);
  if (/^Scarico/.test(msg)) { const p = d ? +d[1] : 0; pct = 5 + p * 0.85; step = "Scarico LagDoctor " + (/Scarico LagDoctor (\S+)/.exec(msg) || [, ""])[1].replace(/\.\.\.$/, ""); }
  else if (/controllato|installo|Chiudo/i.test(msg)) { pct = 95; step = "File controllato: installo..."; }
  else if (msg === "fatto") { pct = 100; step = "Installazione avviata"; }
  const f = $("#upd-fill", m), t = $("#upd-pct", m), s = $("#upd-step", m);
  if (!f) return;
  f.style.width = Math.round(pct) + "%"; t.textContent = Math.round(pct) + "%"; s.textContent = step;
}
$("#btn-update").onclick = () => updateDialog(null);
/* anche con LagDoctor aperto: ricontrollo ogni 15 minuti */
setInterval(() => checkUpdates(false), 15 * 60 * 1000);

/* ------------------------------------------------------------------ IMPOSTAZIONI */
async function settingsDialog() {
  let s;
  try { s = await api("/api/settings"); } catch (e) { return toast("Errore: " + e.message); }
  const row = (id, title, txt, on, dis) => `<div class="list-row" style="align-items:flex-start">
      <label class="switch"><input type="checkbox" id="${id}" ${on ? "checked" : ""} ${dis ? "disabled" : ""}><span></span></label>
      <div class="grow"><b>${title}</b><div class="mut" style="font-size:13px">${txt}</div></div></div>`;
  const m = modal(`<h2>Impostazioni</h2>
    ${row("set-auto", "Avvia LagDoctor con Windows", "LagDoctor si apre da solo dopo l'accesso a Windows, gia' con i permessi di amministratore (nessuna richiesta di conferma). Usa l'Utilita' di pianificazione di Windows (attivita' 'LagDoctor Avvio').", s.autostart)}
    ${row("set-min", "Ridotto a icona", "All'avvio con Windows LagDoctor parte solo come icona vicino all'orologio, senza aprire la finestra: clicca l'icona quando ti serve.", s.minimized, !s.autostart)}
    <div class="list-row set-delay ${s.autostart ? "" : "off"}" style="align-items:flex-start"><span class="sd-ic">${hsv("temp").replace(HI.temp, '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 2M9 2h6"/>')}</span>
      <div class="grow"><b>Ritardo all'avvio</b><div class="mut" style="font-size:13px">Quanto aspetta LagDoctor dopo l'accesso a Windows prima di partire.</div>
        <div class="sd-row"><input type="range" id="set-delay" min="0" max="60" step="5" value="${s.delay ?? 15}" ${s.autostart ? "" : "disabled"}><b id="set-delay-v"></b></div></div></div>
    ${row("set-newwin", "Finestra senza barra di Edge", "Usa la finestra nuova, con la barra del titolo di LagDoctor al posto di quella grigia di Edge. Se va in errore LagDoctor riprova una volta con la grafica in modalita' software, poi torna da solo alla finestra di Edge. Vale dalla prossima apertura: <b>Esci</b> e riapri LagDoctor." + (s.new_window && s.new_window_failed ? " <b>Ultimo tentativo andato in errore</b>: dettagli in errore-finestra.txt (cartella dei dati)." : ""), s.new_window === true)}
    ${row("set-anim", "Animazioni", "Quando cambi scheda la pagina vecchia scompare e la nuova entra con un'animazione. Spegnile per cambi di scheda istantanei.", s.animations !== false)}
    <p class="mut" style="font-size:12.5px">Chiudendo la finestra con la X, LagDoctor resta acceso tra le icone vicino all'orologio (in basso a destra). Per chiuderlo davvero: tasto destro sull'icona &gt; <b>Esci</b>, oppure il pulsante Esci qui a sinistra.</p>
    ${s.autostart && !s.task ? '<p style="color:#e8a23a;font-size:13px">L\'avvio con Windows non risulta attivo: riattivalo.</p>' : ""}
    <p class="mut" style="font-size:12px">La game mode ha un suo avvio automatico separato (pagina Game mode): funziona anche con LagDoctor chiuso.</p>
    <div class="list-row" style="align-items:center"><div class="grow"><b>Verifica completa</b><div class="mut" style="font-size:13px">Controlla una per una tutte le ottimizzazioni, la game mode e le altre funzioni: per ognuna dice se su questo PC funziona davvero. Solo lettura, non cambia niente.</div></div><button id="set-verify">Apri</button></div>
    <div class="row" style="justify-content:flex-end"><button class="ghost" id="m-close">Chiudi</button></div>`);
  const save = async () => {
    try {
      const r = await api("/api/settings", { autostart: $("#set-auto", m).checked, minimized: $("#set-min", m).checked });
      $("#set-min", m).disabled = !r.autostart; dl.disabled = !r.autostart; $(".set-delay", m).classList.toggle("off", !r.autostart);
      toast(r.autostart ? (r.minimized ? "LagDoctor partira' con Windows, ridotto a icona" : "LagDoctor partira' con Windows") : "Avvio con Windows disattivato");
    } catch (e) { toast("Errore: " + e.message); }
  };
  const dTxt = (v) => Number(v) === 0 ? "subito" : v + " secondi";
  const dl = $("#set-delay", m), dv = $("#set-delay-v", m);
  dv.textContent = dTxt(dl.value);
  dl.oninput = () => { dv.textContent = dTxt(dl.value); };
  dl.onchange = async () => {
    try { const r = await api("/api/settings", { delay: Number(dl.value) }); toast(r.delay ? `LagDoctor partira' ${r.delay} secondi dopo l'accesso a Windows` : "LagDoctor partira' subito all'accesso a Windows"); }
    catch (e) { toast("Errore: " + e.message); }
  };
  $("#set-verify", m).onclick = () => { closeModal(); go("verifica"); };
  $("#set-auto", m).onchange = save;
  $("#set-min", m).onchange = save;
  $("#set-newwin", m).onchange = async (e) => {
    const on = e.target.checked;
    try { await api("/api/settings", { new_window: on }); toast(on ? "Finestra nuova accesa: esci e riapri LagDoctor per usarla" : "Finestra nuova spenta: dalla prossima apertura torna quella di Edge", 6000); }
    catch (err) { e.target.checked = !on; toast("Errore: " + err.message); }
  };
  $("#set-anim", m).onchange = async (e) => {
    const on = e.target.checked;
    try { await api("/api/settings", { animations: on }); S.noAnim = !on; toast(on ? "Animazioni attivate" : "Animazioni disattivate"); }
    catch (err) { e.target.checked = !on; toast("Errore: " + err.message); }
  };
  $("#m-close", m).onclick = closeModal;
}
$("#btn-settings").onclick = settingsDialog;

/* ------------------------------------------------------------------ VERIFICA COMPLETA (strumento di prova) */
const VF_ICON = { ok: ["✔", "var(--ok)"], ko: ["✘", "var(--bad)"], reboot: ["⟳", "var(--warn)"], off: ["○", "var(--mut)"], unk: ["?", "var(--warn)"], manual: ["–", "var(--mut)"] };
async function verificaPage() {
  main().innerHTML = `<h1>Verifica completa</h1>
    <p class="sub">Per ogni ottimizzazione, per la game mode e per le altre funzioni: ✔ funziona su questo PC · ✘ PROBLEMA (applicata ma non attiva) · ⟳ serve il riavvio · ○ non attiva · ? non leggibile. Solo lettura.</p>
    <div id="vf-body"><div class="loading"><div class="spinner"></div><p id="vf-msg">Controllo tutto (1-2 minuti)...</p></div></div>`;
  let job;
  try {
    job = await runJob(api("/api/verifica", {}), (j) => { const el = $("#vf-msg"); if (el && j.messages.length) el.textContent = j.messages[j.messages.length - 1]; });
  } catch (e) { $("#vf-body").innerHTML = `<div class="empty">Errore: ${esc(e.message)}</div>`; return; }
  const r = job.result, s = r.summary;
  S.vfOnly = S.vfOnly || false;
  $("#vf-body").innerHTML = `<div class="row" style="gap:8px;flex-wrap:wrap;margin-bottom:12px">
      <span class="badge b-ok">✔ ${s.ok || 0} funzionano</span><span class="badge b-bad">✘ ${s.ko || 0} problemi</span>
      <span class="badge b-warn">⟳ ${s.reboot || 0} da riavviare</span><span class="badge">○ ${s.off || 0} non attive</span><span class="badge b-warn">? ${s.unk || 0} non leggibili</span>
      <span class="grow"></span><label class="chk mut" style="font-size:13px;display:flex;gap:6px;align-items:center"><input type="checkbox" id="vf-only" ${S.vfOnly ? "checked" : ""}> solo problemi</label>
      <button class="ghost sm" id="vf-copy">Copia risultati</button><button class="sm" id="vf-again">Ricontrolla</button></div>
    ${r.file ? `<p class="mut" style="font-size:12px;margin:0 0 10px">Salvata anche nella Cartella report: ${esc(r.file)}</p>` : ""}
    <div id="vf-list"></div>`;
  const draw = () => {
    let g = null, html = "";
    r.rows.filter((x) => !S.vfOnly || ["ko", "reboot", "unk"].includes(x.res)).forEach((x) => {
      if (x.group !== g) { g = x.group; html += `<div class="grp">${esc(g)}</div>`; }
      const [ic, col] = VF_ICON[x.res] || ["?", "var(--mut)"];
      html += `<div class="vf-row"><span class="vf-ic" style="color:${col}">${ic}</span><div class="grow"><b>${esc(x.name)}</b> <span class="mut">— ${esc(x.msg)}</span>
        ${(x.detail || []).length ? `<div class="vf-det">${x.detail.map(esc).join("<br>")}</div>` : ""}</div></div>`;
    });
    $("#vf-list").innerHTML = html || '<div class="empty">Nessun problema.</div>';
  };
  $("#vf-only").onchange = (e) => { S.vfOnly = e.target.checked; draw(); };
  $("#vf-again").onclick = () => verificaPage();
  $("#vf-copy").onclick = async () => {
    try { await navigator.clipboard.writeText(r.text); toast("Risultati copiati: incollali dove vuoi"); }
    catch (e) { toast("Non riesco a copiare: apri il file nella Cartella report"); }
  };
  draw();
}
/* battito: la versione installata si chiude da sola quando chiudi la finestra */
setInterval(() => { api("/api/ping").catch(() => {}); }, 20000);
window.addEventListener("pagehide", () => { try { navigator.sendBeacon("/api/bye?t=" + encodeURIComponent(window.LD_TOKEN), ""); } catch (e) { /* niente */ } });

/* ------------------------------------------------------------------ avvio */
function bootCardHtml() {
  return S.booting ? `<div class="card boot-card"><div class="spinner"></div><div><b>Scansione di tutte le impostazioni presenti nel sistema...</b><div class="mut" id="boot-msg" style="font-size:13px">${esc(S.bootMsg || "Avvio...")}</div><div class="mut" style="font-size:12px;margin-top:2px">Puoi gia' usare il programma: le pagine si aggiornano da sole quando ha finito.</div></div></div>` : "";
}
function setBooting(on) {
  S.booting = on;
  const sp = $("#nav-scan-spin"); if (sp) sp.hidden = !on;
}
async function backgroundBoot(job) {
  setBooting(true);
  try {
    while (job.status === "running") {
      await new Promise((r) => setTimeout(r, 700));
      job = await api("/api/job?id=" + job.id);
      S.bootMsg = job.messages[job.messages.length - 1];
      const el = $("#boot-msg"); if (el) el.textContent = S.bootMsg || "";
    }
    if (job.status === "error") toast("Errore nella scansione delle impostazioni: " + job.error, 8000);
  } catch (e) { /* il server non risponde: lascio la pagina com'e' */ }
  setBooting(false);
  await loadCatalog(true).catch(() => {});
  /* aggiorno la pagina aperta, se mostra dati della scansione (non se c'e' una finestra aperta) */
  if ($("#modal").hidden && ["home", "scan", "tweaks"].includes(S.page)) go(S.page, { quiet: true });
  toast("Scansione delle impostazioni completata");
}
(async () => {
  try {
    const st = await api("/api/state");
    if (st.sysinfo && !st.booting) { go("home"); setTimeout(() => checkUpdates(false), 1500); return; } /* finestra ricaricata */
    const job = await api("/api/boot", {});
    const st2 = await api("/api/state");
    if (st2.hw_cached || st2.sysinfo) {                           /* avvii successivi: subito l'interfaccia */
      S.bootMsg = job.messages[job.messages.length - 1];
      backgroundBoot(job);
      go("home");
      setTimeout(() => checkUpdates(false), 2000);
      return;
    }
    /* primo avvio: aspetto solo la lettura dell'hardware, poi il resto continua in background */
    let j = job;
    while (j.status === "running") {
      await new Promise((r) => setTimeout(r, 700));
      j = await api("/api/job?id=" + j.id);
      logList($("#boot-log"), j.messages);
      const s3 = await api("/api/state");
      if (s3.hw_cached && j.status === "running") { S.bootMsg = j.messages[j.messages.length - 1]; backgroundBoot(j); break; }
    }
    if (j.status === "error") throw new Error(j.error);
    go("home");
    setTimeout(() => checkUpdates(false), 2000);
  } catch (e) {
    main().innerHTML = `<h1>Errore all'avvio</h1><p>${esc(e.message)}</p><p class="mut">Dettagli nel file errore.txt nella cartella di LagDoctor.</p>`;
  }
})();
