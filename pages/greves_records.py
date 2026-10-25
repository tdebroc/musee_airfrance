"""Grèves et accidents face aux records et inaugurations : deux frises par année, d'après les catégories enrichies."""
from .common import embed, page_shell

META = {
    "slug": "greves-records",
    "title": "Grèves et accidents face aux records",
    "description": "Année par année, les textes sur les grèves et les accidents face à ceux sur les records, premiers vols et ouvertures de lignes, avec le ton et le nombre de victimes cité.",
    "order": 4,
}

GOOD = ["record", "premier_vol", "ouverture_ligne"]
BAD = ["greve_social", "accident_incident"]
TONES = {"positif": "p", "neutre": "n", "negatif": "m"}


def prepare(data):
    """Un texte = [id, date, titre, catégories utiles, ton, intérêt, morts] ; seuls les textes d'une des 5 catégories sont gardés."""
    wanted = set(GOOD + BAD)
    events, per_year = [], {}
    for rec in data.records():
        year = rec["date"][:4]
        per_year[year] = per_year.get(year, 0) + 1
        cats = [c for c in rec["categories"] if c in wanted]
        if cats:
            events.append([rec["id"], rec["date"], rec["title"], cats, TONES.get(rec["tone"], "n"), rec["interest"], rec["casualties"]])
    return {"events": events, "perYear": per_year, "good": GOOD, "bad": BAD}


BODY = """
<style>
.ctl { display:flex; flex-wrap:wrap; gap:16px; align-items:center; margin-bottom:12px; color:var(--muted); font-size:13px; }
.ctl label { display:flex; gap:6px; align-items:center; cursor:pointer; }
.panel { margin-bottom:16px; } .panel h2 { margin:0 0 2px; font-size:16px; } .panel .sub { color:var(--muted); font-size:12.5px; margin:0 0 6px; }
svg text { fill:var(--muted); font-size:11px; } svg .axis path, svg .axis line { stroke:var(--line); }
.bar { cursor:pointer; } .bar:hover { opacity:.8; } .sel { stroke:var(--ink); stroke-width:1.5; fill:none; }
.legend { display:flex; flex-wrap:wrap; gap:14px; font-size:12.5px; color:var(--muted); margin:4px 0 0; }
.legend i { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px; }
.cols { display:grid; grid-template-columns:2fr 1fr; gap:16px; } @media (max-width:900px) { .cols { grid-template-columns:1fr; } }
table { border-collapse:collapse; width:100%; font-size:13px; } th, td { text-align:right; padding:4px 8px; border-bottom:1px solid var(--line); }
th:first-child, td:first-child { text-align:left; } th { color:var(--muted); font-weight:600; }
ul.ev { list-style:none; margin:0; padding:0; max-height:420px; overflow:auto; } ul.ev li { padding:6px 0; border-bottom:1px solid var(--line); font-size:13px; }
.tag { display:inline-block; font-size:11px; padding:0 6px; border-radius:8px; border:1px solid var(--line); color:var(--muted); margin-right:4px; }
.tone-p { color:#1a7f4b; } .tone-m { color:var(--accent2); } .tone-n { color:var(--muted); }
.note { color:var(--muted); font-size:12.5px; margin-top:10px; }
</style>
<div class="ctl">
  <label><input type="radio" name="mode" value="n" checked> Nombre de textes</label>
  <label><input type="radio" name="mode" value="pct"> Part des textes de l'année (%)</label>
  <label><input type="checkbox" id="onlyHigh"> Intérêt ≥ 4 seulement</label>
</div>
<div class="card panel"><h2>Records et inaugurations</h2><p class="sub">Records, premiers vols, ouvertures de lignes.</p><svg id="good" width="100%"></svg><div class="legend" id="lg-good"></div></div>
<div class="card panel"><h2>Grèves et accidents</h2><p class="sub">Mouvements sociaux et accidents/incidents. La ligne rouge : plus grand nombre de morts cité par un texte d'accident de l'année.</p><svg id="bad" width="100%"></svg><div class="legend" id="lg-bad"></div></div>
<div class="cols">
  <div class="card"><h2 style="margin:0 0 8px;font-size:16px" id="evtitle">Textes de l'année</h2><ul class="ev" id="evlist"><li>Cliquez sur une barre pour lister les textes de l'année.</li></ul></div>
  <div class="card"><h2 style="margin:0 0 8px;font-size:16px">Par décennie</h2><div id="dec"></div></div>
</div>
<p class="note">Un texte peut relever de plusieurs catégories (il est alors compté dans chacune). Les victimes sont celles citées dans les textes : les commémorations (ex. AF447, 228 morts, rappelé en 2010-2019) répètent le chiffre, d'où le « maximum par année » plutôt qu'une somme. Les années sans texte sont des lacunes des éphémérides, pas forcément des années calmes.</p>
"""

SCRIPT = r"""
const D = __DATA__;
const COL = { record:"#e3a008", premier_vol:"#2f9e8f", ouverture_ligne:"#3b82f6", greve_social:"#a855f7", accident_incident:"#e3001b" };
const LAB = { record:"Records", premier_vol:"Premiers vols", ouverture_ligne:"Ouvertures de lignes", greve_social:"Grèves", accident_incident:"Accidents / incidents" };
const TONE = { p:"positif", n:"neutre", m:"négatif" };
const Y0 = 1908, Y1 = 2022, years = d3.range(Y0, Y1 + 1);
const M = { l:40, r:44, t:8, b:22 };
let mode = "n", onlyHigh = false, selected = null;

const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[c]));
const kept = () => D.events.filter(e => !onlyHigh || e[5] >= 4);

function series(keys) {
  const rows = new Map(years.map(y => [y, { y, total: 0, deaths: 0 }]));
  for (const e of kept()) {
    const y = +e[1].slice(0, 4), row = rows.get(y);
    if (!row) continue;
    for (const c of e[3]) if (keys.includes(c)) {
      row[c] = (row[c] || 0) + 1;
      if (c === "accident_incident" && e[6]) row.deaths = Math.max(row.deaths, e[6]);
    }
  }
  for (const row of rows.values()) {
    const all = D.perYear[row.y] || 0;
    for (const k of keys) { const n = row[k] || 0; row[k] = mode === "pct" ? (all ? 100 * n / all : 0) : n; }
    row.total = d3.sum(keys, k => row[k]);
  }
  return [...rows.values()];
}

function draw(id, keys, withDeaths) {
  const svg = d3.select("#" + id), W = svg.node().clientWidth || 900, H = 190;
  svg.attr("viewBox", `0 0 ${W} ${H}`).attr("height", H).selectAll("*").remove();
  const rows = series(keys);
  const x = d3.scaleBand().domain(years).range([M.l, W - M.r]).padding(0.12);
  const ymax = d3.max(rows, r => r.total) || 1;
  const y = d3.scaleLinear([0, ymax * 1.08], [H - M.b, M.t]).nice();
  svg.append("g").attr("class", "axis").attr("transform", `translate(${M.l},0)`).call(d3.axisLeft(y).ticks(4).tickFormat(d => mode === "pct" ? d + " %" : d));
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - M.b})`).call(d3.axisBottom(x).tickValues(years.filter(v => v % 10 === 0)).tickSizeOuter(0));
  const stack = d3.stack().keys(keys)(rows);
  const g = svg.append("g");
  for (const layer of stack) {
    g.selectAll(null).data(layer).join("rect").attr("class", "bar").attr("fill", COL[layer.key])
      .attr("x", d => x(d.data.y)).attr("width", x.bandwidth()).attr("y", d => y(d[1])).attr("height", d => Math.max(0, y(d[0]) - y(d[1])))
      .append("title").text(d => `${d.data.y} · ${LAB[layer.key]} : ${mode === "pct" ? d3.format(".1f")(d.data[layer.key]) + " %" : d.data[layer.key]}`);
  }
  if (withDeaths) {
    const dmax = d3.max(rows, r => r.deaths) || 1, yd = d3.scaleSqrt([0, dmax], [H - M.b, M.t]);
    const pts = rows.filter(r => r.deaths > 0);
    svg.append("g").selectAll("circle").data(pts).join("circle").attr("cx", d => x(d.y) + x.bandwidth() / 2).attr("cy", d => yd(d.deaths))
      .attr("r", 3.2).attr("fill", "none").attr("stroke", "var(--accent2)").attr("stroke-width", 1.6)
      .append("title").text(d => `${d.y} : jusqu'à ${d.deaths} morts cités`);
    svg.append("text").attr("x", W - M.r + 4).attr("y", M.t + 8).text(dmax + " morts");
  }
  // zones cliquables sur toute la hauteur
  svg.append("g").selectAll("rect").data(years).join("rect").attr("x", v => x(v) - 1).attr("width", x.bandwidth() + 2).attr("y", M.t).attr("height", H - M.b - M.t)
    .attr("fill", "transparent").style("cursor", "pointer").on("click", (_, v) => { selected = v; listYear(v); redrawSel(); });
  svg.append("rect").attr("class", "sel").attr("id", "sel-" + id).attr("display", "none");
  svg.node().__x = x; svg.node().__H = H;
}

function redrawSel() {
  for (const id of ["good", "bad"]) {
    const svg = d3.select("#" + id), r = svg.select("#sel-" + id), x = svg.node().__x;
    if (selected == null || !x) { r.attr("display", "none"); continue; }
    r.attr("display", null).attr("x", x(selected) - 1).attr("width", x.bandwidth() + 2).attr("y", M.t).attr("height", svg.node().__H - M.b - M.t);
  }
}

function listYear(yr) {
  const evs = kept().filter(e => +e[1].slice(0, 4) === yr).sort((a, b) => b[5] - a[5] || (a[1] < b[1] ? -1 : 1));
  d3.select("#evtitle").text(`Textes de ${yr} (${evs.length})`);
  d3.select("#evlist").html(evs.length ? evs.map(e => `<li>${e[3].map(c => `<span class="tag" style="border-color:${COL[c]}">${LAB[c]}</span>`).join("")}<b>${esc(e[2])}</b>
    <div class="tone-${e[4]}">${e[1]} · ton ${TONE[e[4]]} · intérêt ${e[5]}${e[6] ? ` · ${e[6]} morts` : ""}</div></li>`).join("") : "<li>Aucun texte de ces catégories cette année-là.</li>");
}

function decades() {
  const rows = new Map();
  for (const e of kept()) {
    const d = Math.floor(+e[1].slice(0, 4) / 10) * 10, r = rows.get(d) || { good: 0, bad: 0 };
    if (e[3].some(c => D.good.includes(c))) r.good++;
    if (e[3].some(c => D.bad.includes(c))) r.bad++;
    rows.set(d, r);
  }
  const body = [...rows].sort((a, b) => a[0] - b[0]).map(([d, r]) => `<tr><td>${d}s</td><td>${r.good}</td><td>${r.bad}</td><td>${r.bad ? (r.good / r.bad).toFixed(1) : "—"}</td></tr>`).join("");
  d3.select("#dec").html(`<table><tr><th>Décennie</th><th>Records / ouvertures</th><th>Grèves / accidents</th><th>Rapport</th></tr>${body}</table>`);
}

function legend(id, keys) {
  d3.select(id).html(keys.map(k => `<span><i style="background:${COL[k]}"></i>${LAB[k]}</span>`).join("") + (id === "#lg-bad" ? `<span><i style="border:1.6px solid var(--accent2);border-radius:50%;background:none"></i>Morts cités (max/an)</span>` : ""));
}

function render() {
  draw("good", D.good, false); draw("bad", D.bad, true);
  decades(); redrawSel();
  if (selected != null) listYear(selected);
}
legend("#lg-good", D.good); legend("#lg-bad", D.bad);
document.querySelectorAll("input[name=mode]").forEach(i => i.addEventListener("change", () => { mode = i.value; render(); }));
document.getElementById("onlyHigh").addEventListener("change", e => { onlyHigh = e.target.checked; render(); });
addEventListener("resize", render);
render();
"""


def build(data):
    script = SCRIPT.replace("__DATA__", embed(prepare(data)))
    return page_shell(
        META["title"],
        "Les mauvaises nouvelles d'Air France (grèves, accidents) face aux bonnes (records, premiers vols, ouvertures de lignes), année par année. Cliquez sur une année pour lire les textes.",
        BODY,
        head_extra='<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>',
        script=script,
    )
