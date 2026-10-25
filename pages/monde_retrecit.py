"""Le monde rétrécit : durées de trajet citées dans les textes, par liaison, au fil des décennies."""
import math

from .common import embed, page_shell

META = {
    "slug": "monde-retrecit",
    "title": "Le monde rétrécit",
    "description": "Du Breguet 14 au Boeing 777 et au Concorde : les durées de trajet citées dans les textes, liaison par liaison, et la vitesse moyenne qui en découle.",
    "order": 6,
}

# Durées aberrantes ou hors sujet, écartées à la main (id du texte, raison).
EXCLUDED = {
    6742: "liaison maritime (bateau rapide), pas un vol",
    8689: "projet de vol Tokyo-Haneda : 50 h est une erreur d'extraction",
    10346: "anniversaire des 60 ans : 24 h est une durée symbolique, pas celle du vol",
}
ALIASES = {"Roissy-en-France": "Paris"}


def km(a, b):
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b["lon"] - a["lon"]) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def prepare(data):
    """Un trajet = [id, année, date, ville A, ville B, durée h, km, km/h, action, appareil, titre] ; les itinéraires à escales vont à part (+ itinéraire en 12e)."""
    legs, multi, seen = [], [], set()
    for rec in data.records():
        for r in rec["routes"]:
            hours = r.get("duration_hours")
            cities = r["cities"]
            if not hours or hours <= 0 or rec["id"] in EXCLUDED or len(cities) < 2:
                continue
            if any(c.get("lat") is None or c.get("lon") is None for c in cities):
                continue
            names = [ALIASES.get(c["name"], c["name"]) for c in cities]
            key = (rec["id"], tuple(names), hours)
            if key in seen:
                continue
            seen.add(key)
            dist = sum(km(a, b) for a, b in zip(cities, cities[1:]))
            if dist < 50:  # quasi-même point : durée inexploitable
                continue
            row = [rec["id"], int(rec["date"][:4]), rec["date"], names[0], names[-1], hours, round(dist), round(dist / hours), r["action"], r.get("aircraft") or "", rec["title"]]
            if len(cities) == 2:
                legs.append(row)
            else:
                # la durée citée peut ne couvrir qu'une étape : pas de vitesse pour les escales
                multi.append(row[:7] + [None] + row[8:] + [" → ".join(names)])
    return {"legs": legs, "multi": multi, "excluded": [[k, v] for k, v in EXCLUDED.items()]}


BODY = """
<style>
.ctl { display:flex; flex-wrap:wrap; gap:16px; align-items:center; margin-bottom:12px; color:var(--muted); font-size:13px; }
.ctl select, .ctl input[type=text] { background:var(--card); color:var(--ink); border:1px solid var(--line); border-radius:6px; padding:4px 8px; font:inherit; }
.panel { margin-bottom:16px; } .panel h2 { margin:0 0 2px; font-size:16px; } .panel .sub { color:var(--muted); font-size:12.5px; margin:0 0 6px; }
svg text { fill:var(--muted); font-size:11px; } svg .axis path, svg .axis line { stroke:var(--line); } svg .grid line { stroke:var(--line); stroke-opacity:.5; }
.line { fill:none; stroke-width:1.6; } .dim { opacity:.12; } .pt { cursor:pointer; }
table { border-collapse:collapse; width:100%; font-size:13px; } th, td { text-align:right; padding:4px 8px; border-bottom:1px solid var(--line); }
th:nth-child(-n+2), td:nth-child(-n+2) { text-align:left; } th { color:var(--muted); font-weight:600; position:sticky; top:0; background:var(--card); }
.scroll { max-height:420px; overflow:auto; }
.big { font-size:15px; color:var(--ink); } .note { color:var(--muted); font-size:12.5px; margin-top:10px; }
.tag { font-size:11px; padding:0 6px; border-radius:8px; border:1px solid var(--line); color:var(--muted); }
</style>
<div class="card panel"><h2>La durée de quelques liaisons depuis 1930</h2>
<p class="sub">Chaque ligne relie les durées citées pour une même liaison (échelle logarithmique : une division par deux a toujours la même hauteur). Choisissez une liaison, ou survolez une ligne, pour la mettre en avant.</p>
<div class="ctl"><label>Liaison <select id="sel"></select></label><span id="gain" class="big"></span></div>
<svg id="dur" width="100%"></svg></div>
<div class="card panel"><h2>Vitesse moyenne de bout en bout</h2>
<p class="sub">Distance orthodromique divisée par la durée citée (escales et attentes comprises). Un point = un trajet, le rayon grandit avec la distance, les vols d'essai sont en creux ; la courbe rouge donne la médiane par décennie.</p>
<svg id="spd" width="100%"></svg></div>
<div class="card panel"><h2>Toutes les durées citées</h2>
<p class="sub">Par ordre chronologique. Cliquez sur un en-tête pour trier ; survolez une ligne pour lire le titre du texte.</p>
<div class="ctl"><label>Filtre <input type="text" id="q" placeholder="ville, appareil…"></label><label><input type="checkbox" id="withMulti"> inclure les itinéraires à escales (distance = somme des étapes ; sans vitesse, la durée citée ne couvre pas toujours tout l'itinéraire)</label><span id="cnt"></span></div>
<div class="scroll"><table id="tab"></table></div></div>
<p class="note" id="note"></p>
"""

SCRIPT = r"""
const D = __DATA__;
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" }[c]));
const fmtH = h => { if (h >= 48) return (h / 24).toFixed(1).replace(".", ",") + " j"; let hh = Math.floor(h), mm = Math.round((h - hh) * 60); if (mm === 60) { hh++; mm = 0; } return hh ? hh + " h" + (mm ? String(mm).padStart(2, "0") : "") : mm + " min"; };
const nf = new Intl.NumberFormat("fr-FR");
const COLS = ["#3b82f6", "#e3001b", "#2f9e8f", "#e3a008", "#a855f7", "#f97316", "#14b8a6", "#ec4899", "#84cc16", "#64748b", "#0ea5e9", "#d946ef"];
const [I_ID, I_Y, I_DATE, I_A, I_B, I_H, I_KM, I_V, I_ACT, I_AC, I_T, I_ITI] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11];
const pairLabel = r => r[I_B] === "Paris" ? "Paris–" + r[I_A] : r[I_A] === "Paris" ? "Paris–" + r[I_B] : [r[I_A], r[I_B]].sort((a, b) => a.localeCompare(b, "fr")).join("–");

// liaisons citées à au moins 2 années différentes, les plus documentées d'abord
const byPair = d3.group(D.legs, pairLabel);
const pairs = [...byPair].map(([k, v]) => [k, v.slice().sort((a, b) => a[I_DATE] < b[I_DATE] ? -1 : 1)])
  .filter(([, v]) => new Set(v.map(r => r[I_Y])).size >= 2).sort((a, b) => b[1].length - a[1].length || (a[0] < b[0] ? -1 : 1));
const color = new Map(pairs.map(([k], i) => [k, COLS[i % COLS.length]]));
let current = pairs.some(p => p[0] === "Paris–New York") ? "Paris–New York" : (pairs[0] ? pairs[0][0] : null);

const sel = document.getElementById("sel");
sel.innerHTML = '<option value="">(toutes)</option>' + pairs.map(([k, v]) => `<option value="${esc(k)}">${esc(k)} (${v.length})</option>`).join("");
sel.value = current || "";
sel.onchange = () => { current = sel.value || null; drawDur(); };

const M = { l:56, r:20, t:10, b:24 };
function setup(id, H) { const svg = d3.select("#" + id), W = svg.node().clientWidth || 900; svg.attr("viewBox", `0 0 ${W} ${H}`).attr("height", H).selectAll("*").remove(); return [svg, W, H]; }

function drawDur() {
  const [svg, W, H] = setup("dur", 340);
  const pts = pairs.flatMap(([, v]) => v);
  if (!pts.length) { svg.append("text").attr("x", 10).attr("y", 30).text("Pas assez de liaisons citées à plusieurs dates."); return; }
  const ext = d3.extent(pts, r => r[I_Y]);
  const x = d3.scaleLinear([ext[0] - 1, ext[1] + 1], [M.l, W - M.r]);
  const y = d3.scaleLog([Math.min(0.5, d3.min(pts, r => r[I_H])), d3.max(pts, r => r[I_H]) * 1.15], [H - M.b, M.t]);
  const ticks = [0.5, 1, 2, 4, 8, 16, 32, 64, 128, 256].filter(t => t >= y.domain()[0] && t <= y.domain()[1]);
  svg.append("g").attr("class", "grid").selectAll("line").data(ticks).join("line").attr("x1", M.l).attr("x2", W - M.r).attr("y1", y).attr("y2", y);
  svg.append("g").attr("class", "axis").attr("transform", `translate(${M.l},0)`).call(d3.axisLeft(y).tickValues(ticks).tickFormat(fmtH));
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - M.b})`).call(d3.axisBottom(x).ticks(10).tickFormat(d3.format("d")));
  const line = d3.line().x(r => x(r[I_Y])).y(r => y(r[I_H]));
  for (const [k, v] of pairs) {
    const g = svg.append("g").attr("data-k", k).classed("dim", !!current && current !== k)
      .on("mouseenter", () => { if (!current) hover(k); }).on("mouseleave", () => { if (!current) hover(null); });
    g.append("path").attr("class", "line").attr("d", line(v)).attr("stroke", color.get(k));
    g.selectAll("circle").data(v).join("circle").attr("class", "pt").attr("cx", r => x(r[I_Y])).attr("cy", r => y(r[I_H])).attr("r", 3.6).attr("fill", color.get(k))
      .append("title").text(r => `${k} · ${r[I_DATE]} · ${fmtH(r[I_H])}${r[I_AC] ? " · " + r[I_AC] : ""}\n${r[I_T]}`);
    if (current === k || (!current && v.length >= 3)) {
      const last = v[v.length - 1];
      g.append("text").attr("x", x(last[I_Y]) + 6).attr("y", y(last[I_H]) + 4).style("fill", color.get(k)).text(k);
    }
  }
  const p = pairs.find(q => q[0] === current);
  const gain = document.getElementById("gain");
  if (p) {
    const a = p[1][0], b = p[1][p[1].length - 1];
    gain.textContent = `${current} : ${fmtH(a[I_H])} en ${a[I_Y]} → ${fmtH(b[I_H])} en ${b[I_Y]}` + (a[I_H] > b[I_H] ? ` (${(a[I_H] / b[I_H]).toFixed(1).replace(".", ",")} fois plus rapide)` : "");
  } else gain.textContent = "";
}
function hover(k) { d3.selectAll("#dur g[data-k]").classed("dim", function () { return !!k && this.dataset.k !== k; }); }

function drawSpd() {
  const [svg, W, H] = setup("spd", 300);
  const pts = D.legs;
  const x = d3.scaleLinear([1925, 2025], [M.l, W - M.r]), y = d3.scaleLog([15, d3.max(pts, r => r[I_V]) * 1.2], [H - M.b, M.t]);
  const r = d3.scaleSqrt([0, d3.max(pts, p => p[I_KM])], [2, 9]);
  const ticks = [20, 50, 100, 200, 500, 1000, 1500].filter(t => t <= y.domain()[1]);
  svg.append("g").attr("class", "grid").selectAll("line").data(ticks).join("line").attr("x1", M.l).attr("x2", W - M.r).attr("y1", y).attr("y2", y);
  svg.append("g").attr("class", "axis").attr("transform", `translate(${M.l},0)`).call(d3.axisLeft(y).tickValues(ticks).tickFormat(d => d + " km/h"));
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - M.b})`).call(d3.axisBottom(x).ticks(10).tickFormat(d3.format("d")));
  svg.append("g").selectAll("circle").data(pts).join("circle").attr("class", "pt").attr("cx", p => x(p[I_Y])).attr("cy", p => y(p[I_V])).attr("r", p => r(p[I_KM]))
    .attr("fill", p => p[I_ACT] === "vol_essai" ? "none" : "var(--accent)").attr("fill-opacity", .45).attr("stroke", "var(--accent)").attr("stroke-width", 1.2)
    .append("title").text(p => `${pairLabel(p)} · ${p[I_DATE]}\n${nf.format(p[I_KM])} km en ${fmtH(p[I_H])} = ${nf.format(p[I_V])} km/h${p[I_AC] ? "\n" + p[I_AC] : ""}`);
  const dec = d3.rollups(pts, v => d3.median(v, p => p[I_V]), p => Math.floor(p[I_Y] / 10) * 10).sort((a, b) => a[0] - b[0]);
  svg.append("path").attr("fill", "none").attr("stroke", "var(--accent2)").attr("stroke-width", 2).attr("d", d3.line().x(d => x(d[0] + 5)).y(d => y(d[1])).curve(d3.curveMonotoneX)(dec));
  svg.append("g").selectAll("text").data(dec).join("text").attr("x", d => x(d[0] + 5)).attr("y", d => y(d[1]) - 8).attr("text-anchor", "middle").style("fill", "var(--accent2)").text(d => nf.format(Math.round(d[1])));
}

let sortKey = I_DATE, sortDir = 1;
const HEAD = [["Date", I_DATE], ["Liaison", I_A], ["Durée", I_H], ["Distance", I_KM], ["Vitesse", I_V], ["Appareil", I_AC]];
function drawTab() {
  const q = document.getElementById("q").value.trim().toLowerCase(), multi = document.getElementById("withMulti").checked;
  let rows = D.legs.concat(multi ? D.multi : []);
  if (q) rows = rows.filter(r => (r[I_A] + " " + r[I_B] + " " + r[I_AC] + " " + (r[I_ITI] || "") + " " + r[I_T]).toLowerCase().includes(q));
  rows = rows.slice().sort((a, b) => (a[sortKey] < b[sortKey] ? -1 : a[sortKey] > b[sortKey] ? 1 : 0) * sortDir || (a[I_DATE] < b[I_DATE] ? -1 : 1));
  document.getElementById("cnt").textContent = `${rows.length} trajets`;
  document.getElementById("tab").innerHTML = "<tr>" + HEAD.map(([t, k]) => `<th data-k="${k}" style="cursor:pointer">${t}${k === sortKey ? (sortDir > 0 ? " ▲" : " ▼") : ""}</th>`).join("") + "</tr>" +
    rows.map(r => `<tr title="${esc(r[I_T])}"><td>${r[I_DATE]}</td><td>${esc(r[I_ITI] || pairLabel(r))}${r[I_ACT] === "vol_essai" ? ' <span class="tag">essai</span>' : ""}${r[I_ITI] ? ' <span class="tag">escales</span>' : ""}</td><td>${fmtH(r[I_H])}</td><td>${nf.format(r[I_KM])} km</td><td>${r[I_V] == null ? "—" : nf.format(r[I_V]) + " km/h"}</td><td>${esc(r[I_AC])}</td></tr>`).join("");
  document.querySelectorAll("#tab th").forEach(th => th.onclick = () => { const k = +th.dataset.k; sortDir = k === sortKey ? -sortDir : 1; sortKey = k; drawTab(); });
}
document.getElementById("q").oninput = drawTab;
document.getElementById("withMulti").onchange = drawTab;
document.getElementById("note").innerHTML = `Matière : ${D.legs.length} trajets directs et ${D.multi.length} itinéraires à escales avec une durée citée, sur plus de 10 000 textes : c'est peu, la plupart des textes ne donnent pas la durée. Les durées sont celles de l'annonce (parfois escales comprises), pas des mesures ; les vitesses sont de bout en bout. Écartés à la main : ` + D.excluded.map(([i, w]) => `texte ${i} (${esc(w)})`).join(" ; ") + ".";
addEventListener("resize", () => { drawDur(); drawSpd(); });
drawDur(); drawSpd(); drawTab();
"""


def build(data):
    script = SCRIPT.replace("__DATA__", embed(prepare(data)))
    return page_shell(
        META["title"],
        "Combien de temps fallait-il pour rejoindre Dakar, New York ou Tokyo ? Les durées de trajet citées dans les éphémérides, de l'Aéropostale au Concorde.",
        BODY,
        head_extra='<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>',
        script=script,
    )
