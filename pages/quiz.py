"""« Le Grand Quiz » : 5 questions, 5 façons de répondre, jusqu'à 5 000 points par question, classement."""
from .common import embed, page_shell
from .quiz_data import all_questions

META = {
    "slug": "quiz",
    "title": "Le Grand Quiz",
    "description": "Cinq questions, cinq façons de répondre : cliquer sur la carte, placer une année, estimer un chiffre, remettre dans l'ordre, deviner un mot. Plus vite, plus de points (5 000 max), avec classement.",
    "order": 16,
}

HEAD = """<script src="https://cdn.jsdelivr.net/npm/d3@7"></script><style>
.hidden { display:none !important; }
.muted { color:var(--muted); }
button { font:inherit; cursor:pointer; }
button.go { padding:8px 20px; border:0; border-radius:6px; background:var(--accent); color:var(--bg); font-weight:600; }
button.go:disabled { opacity:.4; cursor:default; }
button.alt { padding:7px 14px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--ink); }
button.alt:hover { border-color:var(--accent); }
input[type=text], input[type=number] { font:inherit; padding:8px 10px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--ink); }
.levels { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:12px; margin:14px 0; }
.lvl { text-align:left; padding:14px; border:2px solid var(--line); border-radius:10px; background:var(--card); color:var(--ink); }
.lvl:hover { border-color:var(--accent); }
.lvl.on { border-color:var(--accent); box-shadow:0 0 0 3px color-mix(in srgb, var(--accent) 25%, transparent); }
.lvl b { font-size:18px; display:block; } .lvl span { display:block; color:var(--muted); font-size:13px; margin-top:4px; }
.rules { color:var(--muted); font-size:13.5px; margin:8px 0 0; padding-left:18px; }
.who { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin:12px 0; }
.bar { display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px; font-size:14px; color:var(--muted); margin-bottom:8px; }
.bar b { color:var(--ink); }
.chip { display:inline-block; padding:1px 10px; border-radius:99px; background:color-mix(in srgb, var(--accent) 14%, transparent); color:var(--accent); font-weight:600; font-size:13px; }
.timer { height:8px; border-radius:4px; background:var(--line); overflow:hidden; }
.timer i { display:block; height:100%; width:100%; background:var(--accent); transition:none; }
.timer i.low { background:var(--accent2); }
.pot { font-size:13px; color:var(--muted); margin:4px 0 12px; text-align:right; }
.ask { font-size:19px; margin:6px 0 12px; line-height:1.4; }
.txt { font-size:16.5px; line-height:1.6; white-space:pre-wrap; margin:0 0 14px; padding:12px 14px; border-left:3px solid var(--accent); background:color-mix(in srgb, var(--accent) 6%, transparent); }
.row { display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
.mapwrap { position:relative; border:1px solid var(--line); border-radius:8px; overflow:hidden; background:color-mix(in srgb, var(--accent) 8%, var(--card)); }
.mapwrap svg { display:block; width:100%; height:auto; cursor:crosshair; touch-action:none; }
.mapbtns { position:absolute; top:8px; right:8px; display:flex; flex-direction:column; gap:4px; }
.mapbtns button { width:30px; height:30px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--ink); }
.land { fill:color-mix(in srgb, var(--muted) 24%, var(--card)); stroke:var(--card); stroke-width:.6; vector-effect:non-scaling-stroke; }
.sphere { fill:none; } .grat { fill:none; stroke:var(--line); stroke-width:.4; vector-effect:non-scaling-stroke; }
.pin { fill:var(--accent); stroke:#fff; } .truth { fill:var(--accent2); stroke:#fff; } .link { stroke:var(--accent2); fill:none; stroke-dasharray:5 4; vector-effect:non-scaling-stroke; stroke-width:2; }
.yearbig { font-size:34px; font-weight:700; color:var(--accent); min-width:90px; }
input[type=range] { flex:1 1 320px; accent-color:var(--accent); }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:10px; margin-bottom:12px; }
.ocard { position:relative; text-align:left; padding:12px 12px 12px 44px; border:2px solid var(--line); border-radius:8px; background:var(--card); color:var(--ink); min-height:64px; }
.ocard:hover { border-color:var(--accent); }
.ocard .n { position:absolute; left:10px; top:50%; transform:translateY(-50%); width:26px; height:26px; border-radius:50%; background:var(--line); color:var(--muted); display:grid; place-items:center; font-weight:700; }
.ocard.picked { border-color:var(--accent); } .ocard.picked .n { background:var(--accent); color:var(--bg); }
.ocard.ok { border-color:#2e9e5b; } .ocard.ko { border-color:var(--accent2); }
.ocard small { display:block; color:var(--muted); margin-top:2px; }
.shake { animation:shake .3s; } @keyframes shake { 25% { transform:translateX(-6px); } 75% { transform:translateX(6px); } }
.reveal { margin-top:16px; padding:14px; border-radius:8px; background:color-mix(in srgb, var(--accent) 7%, transparent); }
.reveal .pts { font-size:30px; font-weight:800; color:var(--accent); }
.reveal .det { color:var(--muted); font-size:13.5px; margin:2px 0 8px; }
.reveal .src { font-size:13px; color:var(--muted); margin:8px 0; border-left:3px solid var(--line); padding-left:10px; white-space:pre-wrap; }
.reveal .good { color:var(--accent2); font-weight:700; }
.final { font-size:46px; font-weight:800; color:var(--accent); line-height:1.1; }
table.t { border-collapse:collapse; width:100%; font-size:14px; }
table.t th, table.t td { text-align:left; padding:6px 10px; border-bottom:1px solid var(--line); }
table.t td.n, table.t th.n { text-align:right; font-variant-numeric:tabular-nums; }
table.t tr.me { background:color-mix(in srgb, var(--accent) 14%, transparent); font-weight:600; }
.tabs { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px; }
.tabs button { padding:5px 14px; border:1px solid var(--line); border-radius:99px; background:var(--card); color:var(--ink); }
.tabs button.on { background:var(--accent); color:var(--bg); border-color:var(--accent); }
.board { margin-top:20px; }
.note { color:var(--muted); font-size:12.5px; margin-top:10px; }
</style>"""

BODY = """
<div class="card" id="start">
  <p class="ask" style="margin-top:0">Choisis ton niveau, puis réponds à <b>5 questions</b> tirées des éphémérides d'Air France.</p>
  <div class="levels" id="levels"></div>
  <div class="who"><label for="pseudo">Ton pseudo</label><input type="text" id="pseudo" maxlength="20" placeholder="Anonyme" autocomplete="nickname">
    <button class="go" id="play">Jouer</button></div>
  <ul class="rules">
    <li><b>5 000 points maximum par question</b> : points = précision × rapidité. Répondre tout de suite garde 100 % des points, attendre le temps imparti n'en garde que la moitié.</li>
    <li>Les 5 questions utilisent <b>5 modes de réponse différents</b> : clic sur la carte, curseur sur une frise, estimation d'un chiffre, remise en ordre chronologique, mot à deviner.</li>
    <li>Toutes les réponses viennent des textes des éphémérides, cités après chaque question.</li>
  </ul>
</div>

<div class="card hidden" id="game">
  <div class="bar"><span>Question <b id="qn">1</b> / 5 · <span class="chip" id="qmode"></span> · <span id="qlevel"></span></span><span>Score : <b id="score">0</b></span></div>
  <div class="timer"><i id="tbar"></i></div>
  <div class="pot" id="pot"></div>

  <div id="p-carte" class="panel hidden">
    <p class="ask">Où se trouve <b id="c-name"></b> <span class="muted" id="c-country"></span> ?</p>
    <div class="mapwrap"><svg id="map"></svg>
      <div class="mapbtns"><button id="zin" title="Zoom +">+</button><button id="zout" title="Zoom −">−</button><button id="zreset" title="Vue d'ensemble">⌂</button></div></div>
    <div class="row" style="margin-top:10px"><button class="go" id="c-ok" disabled>Valider</button>
      <span class="muted" id="c-help">Clique sur la carte (molette ou boutons pour zoomer, glisser pour déplacer). Plus tu es proche, plus tu gagnes de points.</span></div>
  </div>

  <div id="p-annee" class="panel hidden">
    <p class="ask">En quelle année cela s'est-il passé ?</p>
    <p class="txt" id="y-text"></p>
    <div class="row"><span class="yearbig" id="y-val"></span><input type="range" id="y-sl" aria-label="Année proposée" min="1905" max="2022" step="1"><button class="go" id="y-ok">Valider</button></div>
  </div>

  <div id="p-nombre" class="panel hidden">
    <p class="ask" id="n-prompt"></p>
    <div class="row"><input type="text" inputmode="decimal" id="n-in" placeholder="Ta valeur" autocomplete="off" style="width:180px"><b id="n-unit"></b><button class="go" id="n-ok">Valider</button></div>
    <p class="muted" id="n-msg" style="min-height:1.4em;margin:8px 0 0"></p>
  </div>

  <div id="p-ordre" class="panel hidden">
    <p class="ask">Remets ces événements dans l'ordre chronologique : clique du <b>plus ancien</b> au <b>plus récent</b>.</p>
    <div class="cards" id="o-cards"></div>
    <div class="row"><button class="go" id="o-ok" disabled>Valider</button><button class="alt" id="o-reset">Recommencer</button></div>
  </div>

  <div id="p-texte" class="panel hidden">
    <p class="ask" id="t-prompt"></p>
    <p class="txt" id="t-text"></p>
    <div class="row"><input type="text" id="t-in" placeholder="Ta réponse" autocomplete="off" style="width:240px"><button class="go" id="t-ok">Valider</button>
      <button class="alt" id="t-hint">Indice (−25 %)</button><button class="alt" id="t-skip">Je passe</button></div>
    <p class="muted" id="t-msg" style="min-height:1.4em;margin:8px 0 0"></p>
  </div>

  <div class="reveal hidden" id="reveal">
    <div class="pts" id="r-pts"></div><div class="det" id="r-det"></div>
    <div id="r-ans"></div><div class="src" id="r-src"></div>
    <button class="go" id="next">Question suivante</button>
  </div>
</div>

<div class="card hidden" id="end">
  <p class="muted" style="margin:0">Partie terminée · niveau <b id="e-level"></b></p>
  <div class="final"><span id="e-score"></span> <span style="font-size:20px;font-weight:600">/ 25 000</span></div>
  <p id="e-rank" class="ask"></p>
  <table class="t" id="e-table"></table>
  <div class="row" style="margin-top:14px"><button class="go" id="again">Rejouer</button><button class="alt" id="menu">Changer de niveau</button></div>
</div>

<div class="card board" id="boardcard">
  <h2 style="margin:0 0 10px;font-size:20px">Classement</h2>
  <div class="tabs" id="tabs"></div>
  <table class="t" id="board"></table>
  <div class="row" style="margin-top:12px"><button class="alt" id="export">Exporter</button><button class="alt" id="import">Importer</button>
    <button class="alt" id="clear">Effacer</button><input type="file" id="file" accept="application/json" class="hidden"></div>
  <p class="note">Le classement est enregistré dans ce navigateur (le site est statique, sans serveur) : pour comparer vos scores, exportez-le et importez celui des autres, les parties sont fusionnées.</p>
</div>
"""

SCRIPT = r"""
const Q = __DATA__;
const $ = id => document.getElementById(id);
const MODES = {
  carte:  { label: "Carte",       T: 40 }, annee: { label: "Frise",       T: 45 },
  nombre: { label: "Estimation",  T: 50 }, ordre: { label: "Chronologie", T: 60 },
  texte:  { label: "Devinette",   T: 60 },
};
const LEVELS = {
  facile:    { label: "Facile",    text: "Villes et événements célèbres, tolérance large." },
  moyen:     { label: "Moyen",     text: "Histoire de la compagnie : il faut avoir de bonnes notions." },
  difficile: { label: "Difficile", text: "Archives pointues, tolérance serrée." },
};
const SCALE = {
  carte:  { facile: 2500, moyen: 1500, difficile: 800 },    // km : 37 % des points à cette distance
  annee:  { facile: 12, moyen: 8, difficile: 5 },           // années
  nombre: { facile: 0.6, moyen: 0.4, difficile: 0.45 },     // écart logarithmique
};
const MAXPTS = 5000, SEEN_KEY = "musee-af-quiz-vus", BOARD_KEY = "musee-af-quiz-classement", NAME_KEY = "musee-af-quiz-pseudo";

// --- stockage (localStorage, avec repli mémoire si indisponible) ---
const mem = {};
const store = {
  get(k, d) { try { const v = localStorage.getItem(k); return v === null ? (k in mem ? mem[k] : d) : JSON.parse(v); } catch (e) { return k in mem ? mem[k] : d; } },
  set(k, v) { mem[k] = v; try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
};

// --- état ---
const S = { level: "facile", qs: [], i: 0, total: 0, results: [], cur: null, t0: 0, raf: 0, lastEntry: null };
const shuffle = a => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
const fmt = n => Math.round(n).toLocaleString("fr-FR");
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const dateFr = iso => new Date(iso + "T12:00:00").toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
const fold = s => s.toLowerCase().replace(/[’]/g, "'").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, " ").trim();

// --- écran de départ ---
function bestOf(level) {
  const scores = store.get(BOARD_KEY, []).filter(e => e.level === level).map(e => e.score);
  return scores.length ? Math.max(...scores) : null;
}
function renderLevels() {
  $("levels").innerHTML = Object.entries(LEVELS).map(([k, v]) => {
    const best = bestOf(k);
    return `<button class="lvl ${k === S.level ? "on" : ""}" data-l="${k}"><b>${v.label}</b><span>${v.text}</span><span>${best === null ? "Pas encore joué" : "Meilleur score : " + fmt(best)}</span></button>`;
  }).join("");
  document.querySelectorAll(".lvl").forEach(b => b.onclick = () => { S.level = b.dataset.l; renderLevels(); boardTab = S.level; renderBoard(); });
}
$("pseudo").value = store.get(NAME_KEY, "");

function pickQuestions(level) {
  const seen = new Set(store.get(SEEN_KEY, []));
  const picked = shuffle(Object.keys(MODES)).map(mode => {
    const pool = Q.filter(q => q.mode === mode && q.level === level);
    let fresh = pool.filter(q => !seen.has(q.id));
    if (!fresh.length) { pool.forEach(q => seen.delete(q.id)); fresh = pool; }
    const q = fresh[Math.floor(Math.random() * fresh.length)];
    seen.add(q.id);
    return q;
  });
  store.set(SEEN_KEY, [...seen]);
  return picked;
}

function startGame() {
  store.set(NAME_KEY, $("pseudo").value.trim());
  Object.assign(S, { qs: pickQuestions(S.level), i: 0, total: 0, results: [], lastEntry: null });
  $("start").classList.add("hidden"); $("end").classList.add("hidden"); $("game").classList.remove("hidden");
  $("score").textContent = "0";
  showQuestion();
}
$("play").onclick = startGame;
$("again").onclick = startGame;
$("menu").onclick = () => { $("end").classList.add("hidden"); $("start").classList.remove("hidden"); renderLevels(); };

// --- minuteur et points ---
const mult = el => 1 - 0.5 * Math.min(1, el / S.cur.T);
function tick() {
  const el = (performance.now() - S.t0) / 1000, left = Math.max(0, 1 - el / S.cur.T);
  $("tbar").style.width = (left * 100) + "%";
  $("tbar").classList.toggle("low", left < 0.25);
  $("pot").textContent = `Jusqu'à ${fmt(MAXPTS * mult(el))} points si tu réponds maintenant · ${Math.ceil(S.cur.T - el)} s`;
  if (el >= S.cur.T) { S.cur.timeUp(); return; }
  S.raf = requestAnimationFrame(tick);
}
function finish(acc, view) {
  cancelAnimationFrame(S.raf);
  const el = Math.min((performance.now() - S.t0) / 1000, S.cur.T), m = mult(el);
  const pts = acc > 0 ? Math.round(MAXPTS * Math.min(1, acc) * m) : 0;
  S.total += pts;
  S.results.push({ mode: S.cur.q.mode, pts, acc, secs: el });
  $("score").textContent = fmt(S.total);
  $("tbar").style.width = "0%"; $("pot").textContent = "";
  $("r-pts").textContent = `+${fmt(pts)} points`;
  $("r-det").textContent = `Précision ${Math.round(Math.min(1, acc) * 100)} % × rapidité ×${m.toFixed(2)} (${el.toFixed(1)} s)`;
  $("r-ans").innerHTML = view.answer;
  const q = S.cur.q;
  $("r-src").textContent = view.src || (q.title ? `Éphéméride du ${dateFr(q.date)} : ${q.title}` : "");
  $("r-src").classList.toggle("hidden", !$("r-src").textContent);
  $("next").textContent = S.i === 4 ? "Voir le résultat" : "Question suivante";
  $("reveal").classList.remove("hidden");
  $("next").focus({ preventScroll: true });
  S.cur.locked = true;
}
$("next").onclick = () => { S.i++; S.i >= 5 ? endGame() : showQuestion(); };

function showQuestion() {
  const q = S.qs[S.i];
  document.querySelectorAll(".panel").forEach(p => p.classList.add("hidden"));
  $("reveal").classList.add("hidden");
  $("qn").textContent = S.i + 1;
  $("qmode").textContent = MODES[q.mode].label;
  $("qlevel").textContent = LEVELS[q.level].label;
  $("p-" + q.mode).classList.remove("hidden");
  S.cur = { q, T: MODES[q.mode].T, locked: false };
  SETUP[q.mode](q);
  S.t0 = performance.now();
  S.raf = requestAnimationFrame(tick);
  $("game").scrollIntoView({ block: "nearest" });
}

// --- mode carte ---
const MW = 1000, MH = 520;
const svg = d3.select("#map").attr("viewBox", `0 0 ${MW} ${MH}`);
const proj = d3.geoEqualEarth().fitExtent([[6, 6], [MW - 6, MH - 6]], { type: "Sphere" });
const gpath = d3.geoPath(proj);
const root = svg.append("g");
root.append("path").attr("class", "sphere").attr("d", gpath({ type: "Sphere" }));
root.append("path").attr("class", "grat").attr("d", gpath(d3.geoGraticule10()));
const gLand = root.append("g"), gMarks = root.append("g");
const zoom = d3.zoom().scaleExtent([1, 14]).translateExtent([[0, 0], [MW, MH]]).on("zoom", e => {
  root.attr("transform", e.transform);
  gMarks.selectAll("circle").attr("r", function () { return this.dataset.r / e.transform.k; }).attr("stroke-width", 1.5 / e.transform.k);
});
svg.call(zoom).on("dblclick.zoom", null);
$("zin").onclick = () => svg.transition().duration(250).call(zoom.scaleBy, 1.8);
$("zout").onclick = () => svg.transition().duration(250).call(zoom.scaleBy, 1 / 1.8);
$("zreset").onclick = () => svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity);
fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json").then(r => r.json()).then(topo => {
  const [kx, ky] = topo.transform.scale, [tx, ty] = topo.transform.translate;
  const decoded = topo.arcs.map(a => { let x = 0, y = 0; return a.map(([dx, dy]) => [(x += dx) * kx + tx, (y += dy) * ky + ty]); });
  const ring = idx => idx.flatMap(i => i >= 0 ? decoded[i] : decoded[~i].slice().reverse());
  const polys = [];
  for (const g of topo.objects.countries.geometries) {
    if (g.type === "Polygon") polys.push(g.arcs.map(ring));
    else if (g.type === "MultiPolygon") g.arcs.forEach(p => polys.push(p.map(ring)));
  }
  gLand.append("path").attr("class", "land").attr("d", gpath({ type: "MultiPolygon", coordinates: polys }));
}).catch(() => { $("c-help").textContent = "Fond de carte indisponible (hors ligne) : seules les graticules sont tracées, le jeu reste jouable."; });

const km = (a, b) => d3.geoDistance(a, b) * 6371;
function mark(ll, cls, r) {
  const [x, y] = proj(ll);
  return gMarks.append("circle").attr("class", cls).attr("cx", x).attr("cy", y).attr("data-r", r).attr("r", r).attr("stroke-width", 1.5);
}
function fitTo(lls) {
  const pts = lls.map(proj), xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  const dx = Math.max(...xs) - Math.min(...xs), dy = Math.max(...ys) - Math.min(...ys);
  const k = Math.max(1, Math.min(8, 0.6 * Math.min(MW / Math.max(dx, 1), MH / Math.max(dy, 1))));
  const cx = (Math.max(...xs) + Math.min(...xs)) / 2, cy = (Math.max(...ys) + Math.min(...ys)) / 2;
  svg.transition().duration(800).call(zoom.transform, d3.zoomIdentity.translate(MW / 2 - k * cx, MH / 2 - k * cy).scale(k));
}
function setupCarte(q) {
  gMarks.selectAll("*").remove();
  svg.interrupt().call(zoom.transform, d3.zoomIdentity);
  $("c-name").textContent = q.label; $("c-country").textContent = `(${q.country})`;
  const st = S.cur; st.guess = null; $("c-ok").disabled = true;
  const submit = () => {
    if (st.locked) return;
    if (!st.guess) { finish(0, { answer: `Tu n'as pas placé de repère. <span class="good">${esc(q.label)}</span> était ici.` }); revealTarget(null); return; }
    const d = km(st.guess, [q.lon, q.lat]), acc = d < 25 ? 1 : Math.exp(-d / SCALE.carte[q.level]);
    revealTarget(st.guess);
    finish(acc, { answer: `Tu étais à <span class="good">${fmt(d)} km</span> de ${esc(q.label)}.`, src: q.fact ? `Dans les éphémérides (${dateFr(q.fact[0])}) : ${q.fact[1]}` : "" });
  };
  const revealTarget = g => { mark([q.lon, q.lat], "truth", 8); if (g) { gMarks.insert("path", ":first-child").attr("class", "link").attr("d", gpath({ type: "LineString", coordinates: [g, [q.lon, q.lat]] })); fitTo([g, [q.lon, q.lat]]); } else fitTo([[q.lon, q.lat]]); };
  svg.on("click", e => {
    if (st.locked) return;
    const [x, y] = d3.pointer(e, root.node()), ll = proj.invert([x, y]);
    if (!ll || isNaN(ll[0]) || Math.hypot(proj(ll)[0] - x, proj(ll)[1] - y) > 1.5) return;  // en dehors du globe
    gMarks.selectAll(".pin").remove();
    const k = d3.zoomTransform(svg.node()).k;
    mark(ll, "pin", 7).attr("r", 7 / k);
    st.guess = ll; $("c-ok").disabled = false;
  });
  $("c-ok").onclick = submit;
  st.timeUp = submit;
}

// --- mode année ---
function setupAnnee(q) {
  const sl = $("y-sl"), st = S.cur;
  $("y-text").textContent = q.text;
  sl.value = 1960; $("y-val").textContent = sl.value;
  sl.oninput = () => $("y-val").textContent = sl.value;
  const submit = () => {
    if (st.locked) return;
    const guess = +sl.value, gap = Math.abs(guess - q.year), acc = gap === 0 ? 1 : Math.exp(-gap / SCALE.annee[q.level]);
    const span = 2022 - 1905, pos = y => ((y - 1905) / span * 100).toFixed(1);
    sl.disabled = true;
    finish(acc, { answer: `C'était en <span class="good">${q.year}</span>${gap ? ` : tu as proposé ${guess}, soit ${gap} an${gap > 1 ? "s" : ""} d'écart` : " : en plein dans le mille !"}.
      <div style="position:relative;height:34px;margin:10px 0 0"><div style="position:absolute;left:0;right:0;top:16px;height:2px;background:var(--line)"></div>
      <div title="Ta réponse" style="position:absolute;left:${pos(guess)}%;top:6px;width:12px;height:22px;margin-left:-6px;border-radius:3px;background:var(--accent)"></div>
      <div title="Réponse" style="position:absolute;left:${pos(q.year)}%;top:6px;width:12px;height:22px;margin-left:-6px;border-radius:3px;background:var(--accent2)"></div></div>` });
  };
  sl.disabled = false;
  $("y-ok").onclick = submit;
  st.timeUp = submit;
}

// --- mode nombre ---
function parseNumber(raw) {
  let s = raw.trim().replace(/[\s  ]/g, "");
  if (/^\d{1,3}(\.\d{3})+$/.test(s)) s = s.replace(/\./g, "");   // 1.075.000
  s = s.replace(",", ".");
  return /^\d+(\.\d+)?$/.test(s) ? parseFloat(s) : NaN;
}
function setupNombre(q) {
  const inp = $("n-in"), st = S.cur;
  $("n-prompt").textContent = q.prompt; $("n-unit").textContent = q.unit; $("n-msg").textContent = "";
  inp.value = ""; inp.disabled = false; inp.focus();
  const submit = force => {
    if (st.locked) return;
    const v = parseNumber(inp.value);
    if (isNaN(v) || v <= 0) {
      if (!force) { $("n-msg").textContent = "Entre un nombre strictement positif (ex. 1 075 000 ou 11,5)."; inp.classList.remove("shake"); void inp.offsetWidth; inp.classList.add("shake"); return; }
      finish(0, { answer: `Pas de réponse. La valeur était <span class="good">${fmt(q.answer)} ${esc(q.unit)}</span>.`, src: q.source }); return;
    }
    const off = Math.abs(Math.log(v / q.answer)), acc = off < 0.01 ? 1 : Math.exp(-off / SCALE.nombre[q.level]);
    inp.disabled = true;
    finish(acc, { answer: `Réponse : <span class="good">${fmt(q.answer)} ${esc(q.unit)}</span> · tu as dit ${fmt(v)} (${v > q.answer ? "+" : "−"}${Math.round(Math.abs(v - q.answer) / q.answer * 100)} %).`,
      src: `Éphéméride du ${dateFr(q.date)} : ${q.source}` });
  };
  $("n-ok").onclick = () => submit(false);
  inp.onkeydown = e => { if (e.key === "Enter") submit(false); };
  st.timeUp = () => submit(true);
}

// --- mode ordre ---
function setupOrdre(q) {
  const st = S.cur, items = shuffle(q.items.map((it, i) => ({ ...it, rank: i })));   // rank = vrai rang
  st.picked = [];
  const box = $("o-cards");
  const draw = () => {
    box.innerHTML = items.map((it, i) => `<button class="ocard ${st.picked.includes(i) ? "picked" : ""}" data-i="${i}"><span class="n">${st.picked.includes(i) ? st.picked.indexOf(i) + 1 : ""}</span>${esc(it.title)}</button>`).join("");
    box.querySelectorAll(".ocard").forEach(b => b.onclick = () => {
      if (st.locked) return;
      const i = +b.dataset.i, at = st.picked.indexOf(i);
      if (at >= 0) st.picked.splice(at, 1); else st.picked.push(i);
      draw();
    });
    $("o-ok").disabled = st.picked.length < 4;
  };
  const submit = () => {
    if (st.locked) return;
    const ranks = st.picked.map(i => items[i].rank);
    let good = 0;
    for (let a = 0; a < ranks.length; a++) for (let b = a + 1; b < ranks.length; b++) if (ranks[a] < ranks[b]) good++;
    const acc = Math.pow(good / 6, 2);
    box.innerHTML = q.items.map((it, r) => {
      const idx = items.findIndex(x => x.rank === r), mine = st.picked.indexOf(idx);
      return `<div class="ocard ${mine === r ? "ok" : "ko"}"><span class="n">${r + 1}</span>${esc(it.title)}<small>${it.year}${mine < 0 ? " · non classé" : mine === r ? " · bien placé" : ` · tu l'avais mis ${mine + 1}ᵉ`}</small></div>`;
    }).join("");
    $("o-ok").disabled = true;
    finish(acc, { answer: `<span class="good">${good} paire${good > 1 ? "s" : ""} sur 6</span> dans le bon ordre.`, src: "Dates tirées des éphémérides correspondantes." });
  };
  $("o-reset").onclick = () => { if (!st.locked) { st.picked = []; draw(); } };
  $("o-ok").onclick = submit;
  st.timeUp = submit;
  draw();
}

// --- mode texte ---
function lev(a, b) {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++)
    d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return d[a.length][b.length];
}
function matches(guess, aliases) {
  const g = fold(guess);
  if (!g) return false;
  return aliases.some(al => {
    const a = fold(al);
    if (g === a || (" " + g + " ").includes(" " + a + " ")) return true;
    const tol = a.length >= 9 ? 2 : a.length >= 5 ? 1 : 0;
    return tol > 0 && lev(g, a) <= tol;
  });
}
function setupTexte(q) {
  const inp = $("t-in"), st = S.cur;
  st.wrong = 0; st.hint = false;
  $("t-prompt").textContent = q.prompt; $("t-text").textContent = q.masked; $("t-msg").textContent = "";
  inp.value = ""; inp.disabled = false; inp.focus();
  $("t-hint").disabled = false;
  const end = (ok, forced) => {
    inp.disabled = true; $("t-hint").disabled = true;
    const acc = ok ? Math.max(0.2, 1 - 0.15 * st.wrong - (st.hint ? 0.25 : 0)) : 0;
    finish(acc, { answer: ok ? `Bravo : <span class="good">${esc(q.answer)}</span>${st.wrong ? ` (${st.wrong} essai${st.wrong > 1 ? "s" : ""} raté${st.wrong > 1 ? "s" : ""})` : ""}.`
      : `${forced ? "Temps écoulé" : "Dommage"} : c'était <span class="good">${esc(q.answer)}</span>.`, src: `Éphéméride du ${dateFr(q.date)} :\n${q.full}` });
  };
  const submit = () => {
    if (st.locked) return;
    if (matches(inp.value, q.aliases)) return end(true);
    if (!inp.value.trim()) return;
    st.wrong++;
    $("t-msg").textContent = `Non, ce n'est pas « ${inp.value.trim()} » (−15 % des points possibles). Réessaie.`;
    inp.value = ""; inp.classList.remove("shake"); void inp.offsetWidth; inp.classList.add("shake");
  };
  $("t-ok").onclick = submit;
  inp.onkeydown = e => { if (e.key === "Enter") submit(); };
  $("t-hint").onclick = () => {
    if (st.locked || st.hint) return;
    st.hint = true; $("t-hint").disabled = true;
    const a = q.answer.replace(/[^\p{L}\p{N}]/gu, "");
    $("t-msg").textContent = `Indice : ${a.length} caractères, ça commence par « ${q.answer[0]} ».`;
  };
  $("t-skip").onclick = () => { if (!st.locked) end(false, false); };
  st.timeUp = () => end(false, true);
}
const SETUP = { carte: setupCarte, annee: setupAnnee, nombre: setupNombre, ordre: setupOrdre, texte: setupTexte };

// --- fin de partie et classement ---
let boardTab = "tous";
function endGame() {
  $("game").classList.add("hidden"); $("end").classList.remove("hidden");
  const name = store.get(NAME_KEY, "") || "Anonyme";
  const entry = { name, level: S.level, score: S.total, date: new Date().toISOString(), id: Math.random().toString(36).slice(2) };
  const board = store.get(BOARD_KEY, []); board.push(entry); store.set(BOARD_KEY, board);
  S.lastEntry = entry.id;
  const same = board.filter(e => e.level === S.level).sort((a, b) => b.score - a.score);
  $("e-level").textContent = LEVELS[S.level].label;
  $("e-score").textContent = fmt(S.total);
  $("e-rank").textContent = `${name} : n° ${same.findIndex(e => e.id === entry.id) + 1} sur ${same.length} au classement ${LEVELS[S.level].label.toLowerCase()}.`;
  $("e-table").innerHTML = "<tr><th>Mode</th><th class='n'>Temps</th><th class='n'>Précision</th><th class='n'>Points</th></tr>" +
    S.results.map(r => `<tr><td>${MODES[r.mode].label}</td><td class="n">${r.secs.toFixed(1)} s</td><td class="n">${Math.round(Math.min(1, r.acc) * 100)} %</td><td class="n">${fmt(r.pts)}</td></tr>`).join("");
  boardTab = S.level; renderBoard();
}
function renderBoard() {
  const tabs = [["tous", "Tous niveaux"], ...Object.entries(LEVELS).map(([k, v]) => [k, v.label])];
  $("tabs").innerHTML = tabs.map(([k, l]) => `<button class="${k === boardTab ? "on" : ""}" data-k="${k}">${l}</button>`).join("");
  $("tabs").querySelectorAll("button").forEach(b => b.onclick = () => { boardTab = b.dataset.k; renderBoard(); });
  const rows = store.get(BOARD_KEY, []).filter(e => boardTab === "tous" || e.level === boardTab).sort((a, b) => b.score - a.score || a.date.localeCompare(b.date)).slice(0, 10);
  $("board").innerHTML = rows.length
    ? "<tr><th class='n'>#</th><th>Joueur</th><th>Niveau</th><th>Date</th><th class='n'>Score</th></tr>" +
      rows.map((e, i) => `<tr class="${e.id === S.lastEntry ? "me" : ""}"><td class="n">${i + 1}</td><td>${esc(e.name)}</td><td>${LEVELS[e.level].label}</td><td>${new Date(e.date).toLocaleDateString("fr-FR")}</td><td class="n">${fmt(e.score)}</td></tr>`).join("")
    : "<tr><td class='muted'>Aucune partie pour l'instant : à toi de jouer !</td></tr>";
}
$("export").onclick = () => {
  const url = URL.createObjectURL(new Blob([JSON.stringify(store.get(BOARD_KEY, []), null, 1)], { type: "application/json" }));
  Object.assign(document.createElement("a"), { href: url, download: "classement-quiz-air-france.json" }).click();
  URL.revokeObjectURL(url);
};
$("import").onclick = () => $("file").click();
$("file").onchange = async () => {
  try {
    const incoming = JSON.parse(await $("file").files[0].text());
    const board = store.get(BOARD_KEY, []), ids = new Set(board.map(e => e.id));
    for (const e of incoming) if (e && e.id && !ids.has(e.id) && LEVELS[e.level] && Number.isFinite(e.score) && e.name) board.push({ id: String(e.id), name: String(e.name).slice(0, 20), level: e.level, score: e.score, date: String(e.date) });
    store.set(BOARD_KEY, board); renderBoard(); renderLevels();
  } catch (err) { alert("Fichier de classement illisible."); }
  $("file").value = "";
};
$("clear").onclick = () => { if (confirm("Effacer tout le classement de ce navigateur ?")) { store.set(BOARD_KEY, []); renderBoard(); renderLevels(); } };

renderLevels(); renderBoard();
"""


def build(data):
    questions = all_questions(data)
    return page_shell(
        META["title"],
        f"{len(questions)} questions tirées des éphémérides, trois niveaux, cinq façons de répondre. Plus tu réponds vite, plus tu marques : jusqu'à 5 000 points par question.",
        BODY,
        head_extra=HEAD,
        script=SCRIPT.replace("__DATA__", embed(questions)),
    )
