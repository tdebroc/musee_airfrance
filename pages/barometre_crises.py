"""Baromètre des crises : intensité par année des textes de guerre/crise, grèves et sécurité/sûreté (hors ton positif)."""
from .common import embed, page_shell

META = {
    "slug": "barometre-crises",
    "title": "Baromètre des crises",
    "description": "Année par année, l'intensité des crises chez Air France : guerres et crises, grèves, sécurité et sûreté, pondérée par l'intérêt des textes, avec les événements marquants.",
    "order": 13,
}

CRISIS = ["guerre_crise", "greve_social", "securite_surete"]  # ordre = priorité pour le classement d'un texte multi-catégories
TONES = {"positif": "p", "neutre": "n", "negatif": "m"}


def prepare(data):
    """Texte = [id, date, titre, groupe, ton, intérêt, morts] ; groupe = 1re catégorie de crise, ou 'negatif' (ton négatif hors crise)."""
    events, per_year = [], {}
    for rec in data.records():
        year = rec["date"][:4]
        per_year[year] = per_year.get(year, 0) + 1
        group = next((c for c in CRISIS if c in rec["categories"]), None)
        if group and rec["tone"] == "positif":
            continue  # certifications, exercices réussis… : pas une crise
        if not group and rec["tone"] == "negatif":
            group = "negatif"
        if group:
            events.append([rec["id"], rec["date"], rec["title"], group, TONES.get(rec["tone"], "n"), rec["interest"], rec["casualties"]])
    return {"events": events, "perYear": per_year, "crisis": CRISIS}


BODY = """
<style>
.ctl { display:flex; flex-wrap:wrap; gap:16px; align-items:center; margin-bottom:12px; color:var(--muted); font-size:13px; }
.ctl label { display:flex; gap:6px; align-items:center; cursor:pointer; }
.panel h2 { margin:0 0 2px; font-size:16px; } .panel .sub { color:var(--muted); font-size:12.5px; margin:0 0 6px; }
svg text { fill:var(--muted); font-size:11px; } svg .axis path, svg .axis line { stroke:var(--line); }
.bar { cursor:pointer; } .bar:hover { opacity:.8; } .sel { stroke:var(--ink); stroke-width:1.5; fill:none; }
.legend { display:flex; flex-wrap:wrap; gap:14px; font-size:12.5px; color:var(--muted); margin:4px 0 0; }
.legend i { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:5px; vertical-align:-1px; }
.cols { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:16px; } @media (max-width:900px) { .cols { grid-template-columns:1fr; } }
ul.ev { list-style:none; margin:0; padding:0; max-height:460px; overflow:auto; } ul.ev li { padding:6px 0; border-bottom:1px solid var(--line); font-size:13px; }
ul.ev li.click { cursor:pointer; } ul.ev li.click:hover { background:var(--bg); }
.tag { display:inline-block; font-size:11px; padding:0 6px; border-radius:8px; border:1px solid var(--line); color:var(--muted); margin-right:4px; }
.tone-p { color:#1a7f4b; } .tone-m { color:var(--accent2); } .tone-n { color:var(--muted); }
.note { color:var(--muted); font-size:12.5px; margin-top:10px; }
</style>
<div class="ctl">
  <label><input type="radio" name="mode" value="w" checked> Intensité (somme des intérêts)</label>
  <label><input type="radio" name="mode" value="n"> Nombre de textes</label>
  <label><input type="radio" name="mode" value="pct"> Part des textes de l'année (%)</label>
  <label><input type="checkbox" id="neg"> Ajouter les textes de ton négatif d'autres catégories</label>
</div>
<div class="card panel"><h2>Intensité des crises par année</h2><p class="sub">Les points sombres marquent les années avec un texte d'intérêt 5 (événement marquant). Cliquez sur une année pour lire ses textes.</p>
<svg id="chart" width="100%"></svg><div class="legend" id="lg"></div></div>
<div class="cols">
  <div class="card"><h2 style="margin:0 0 8px;font-size:16px" id="evtitle">Textes de l'année</h2><ul class="ev" id="evlist"><li>Cliquez sur une barre.</li></ul></div>
  <div class="card"><h2 style="margin:0 0 8px;font-size:16px">Événements marquants (intérêt 5)</h2><ul class="ev" id="top"></ul></div>
</div>
<p class="note">Un texte compte pour une seule crise (priorité : guerre/crise, puis grève, puis sécurité/sûreté). Les textes de ton positif de ces catégories (certifications, exercices réussis…) sont écartés. L'intensité somme les notes d'intérêt (1 à 5) des textes : une année riche en petits textes peut égaler une année à un seul grand événement. Les commémorations (AF447, Concorde, Entebbe) comptent à leur date de rappel, pas à celle du drame. Les années sans texte sont des lacunes des éphémérides, pas des années calmes ; le volume de textes augmente aussi après 1990.</p>
"""

SCRIPT = r"""
const D = __DATA__;
const COL = { guerre_crise:"#e3a008", greve_social:"#a855f7", securite_surete:"#e3001b", negatif:"#8a8f98" };
const LAB = { guerre_crise:"Guerres et crises", greve_social:"Grèves et conflits sociaux", securite_surete:"Sécurité et sûreté", negatif:"Autres textes négatifs" };
const TONE = { p:"positif", n:"neutre", m:"négatif" };
const Y0 = 1908, Y1 = 2022, years = d3.range(Y0, Y1 + 1), M = { l:44, r:12, t:10, b:22 };
let mode = "w", withNeg = false, selected = null;
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[c]));
const keys = () => withNeg ? [...D.crisis, "negatif"] : D.crisis;
const kept = () => D.events.filter(e => withNeg || e[3] !== "negatif");

function series() {
  const ks = keys(), rows = new Map(years.map(y => [y, { y, total:0, top:0 }]));
  for (const e of kept()) {
    const row = rows.get(+e[1].slice(0, 4));
    if (!row) continue;
    row[e[3]] = (row[e[3]] || 0) + (mode === "w" ? e[5] : 1);
    if (e[5] >= 5) row.top++;
  }
  for (const row of rows.values()) {
    const all = D.perYear[row.y] || 0;
    for (const k of ks) { const v = row[k] || 0; row[k] = mode === "pct" ? (all ? 100 * v / all : 0) : v; }
    row.total = d3.sum(ks, k => row[k]);
  }
  return [...rows.values()];
}

function draw() {
  const svg = d3.select("#chart"), W = svg.node().clientWidth || 900, H = 280, ks = keys();
  svg.attr("viewBox", `0 0 ${W} ${H}`).attr("height", H).selectAll("*").remove();
  const rows = series(), x = d3.scaleBand().domain(years).range([M.l, W - M.r]).padding(0.12);
  const y = d3.scaleLinear([0, (d3.max(rows, r => r.total) || 1) * 1.08], [H - M.b, M.t]).nice();
  svg.append("g").attr("class", "axis").attr("transform", `translate(${M.l},0)`).call(d3.axisLeft(y).ticks(5).tickFormat(d => mode === "pct" ? d + " %" : d));
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - M.b})`).call(d3.axisBottom(x).tickValues(years.filter(v => v % 10 === 0)).tickSizeOuter(0));
  const fmt = v => mode === "pct" ? d3.format(".1f")(v) + " %" : v;
  const g = svg.append("g");
  for (const layer of d3.stack().keys(ks)(rows)) {
    g.selectAll(null).data(layer).join("rect").attr("class", "bar").attr("fill", COL[layer.key])
      .attr("x", d => x(d.data.y)).attr("width", x.bandwidth()).attr("y", d => y(d[1])).attr("height", d => Math.max(0, y(d[0]) - y(d[1])))
      .append("title").text(d => `${d.data.y} · ${LAB[layer.key]} : ${fmt(d.data[layer.key])}`);
  }
  svg.append("g").selectAll("circle").data(rows.filter(r => r.top > 0)).join("circle")
    .attr("cx", r => x(r.y) + x.bandwidth() / 2).attr("cy", r => y(r.total) - 5).attr("r", 2.6).attr("fill", "var(--ink)")
    .append("title").text(r => `${r.y} : ${r.top} événement(s) marquant(s)`);
  svg.append("g").selectAll("rect").data(years).join("rect").attr("x", v => x(v) - 1).attr("width", x.bandwidth() + 2).attr("y", M.t).attr("height", H - M.b - M.t)
    .attr("fill", "transparent").style("cursor", "pointer").on("click", (_, v) => select(v));
  const sel = svg.append("rect").attr("class", "sel").attr("id", "sel").attr("display", "none");
  svg.node().__x = x; svg.node().__H = H;
  if (selected != null) sel.attr("display", null).attr("x", x(selected) - 1).attr("width", x.bandwidth() + 2).attr("y", M.t).attr("height", H - M.b - M.t);
}

function item(e, click) {
  return `<li${click ? ` class="click" data-y="${e[1].slice(0, 4)}"` : ""}><span class="tag" style="border-color:${COL[e[3]]}">${LAB[e[3]]}</span><b>${esc(e[2])}</b>
    <div class="tone-${e[4]}">${e[1]} · ton ${TONE[e[4]]} · intérêt ${e[5]}${e[6] ? ` · ${e[6]} morts` : ""}</div></li>`;
}

function select(yr) {
  selected = yr; draw();
  const evs = kept().filter(e => +e[1].slice(0, 4) === yr).sort((a, b) => b[5] - a[5] || (a[1] < b[1] ? -1 : 1));
  d3.select("#evtitle").text(`Textes de ${yr} (${evs.length})`);
  d3.select("#evlist").html(evs.length ? evs.map(e => item(e, false)).join("") : "<li>Aucun texte de crise cette année-là.</li>");
}

function drawTop() {
  const evs = kept().filter(e => e[5] >= 5).sort((a, b) => a[1] < b[1] ? -1 : 1);
  d3.select("#top").html(evs.map(e => item(e, true)).join(""));
  document.querySelectorAll("#top li.click").forEach(li => li.addEventListener("click", () => select(+li.dataset.y)));
}

function render() {
  draw(); drawTop();
  d3.select("#lg").html(keys().map(k => `<span><i style="background:${COL[k]}"></i>${LAB[k]}</span>`).join(""));
  if (selected != null) select(selected);
}
document.querySelectorAll("input[name=mode]").forEach(i => i.addEventListener("change", () => { mode = i.value; render(); }));
document.getElementById("neg").addEventListener("change", e => { withNeg = e.target.checked; render(); });
addEventListener("resize", draw);
render();
"""


def build(data):
    script = SCRIPT.replace("__DATA__", embed(prepare(data)))
    return page_shell(
        META["title"],
        "Quelles années ont été les plus difficiles pour Air France ? Guerres et crises, grèves, sécurité et sûreté, pondérées par l'intérêt des textes, avec les événements marquants.",
        BODY,
        head_extra='<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>',
        script=script,
    )
