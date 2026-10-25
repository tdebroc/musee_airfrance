"""Carte animée du réseau : lignes ouvertes / fermées au fil des années, d'après les `routes` enrichies."""
from html import unescape

from .common import embed, page_shell

META = {
    "slug": "carte-reseau",
    "title": "Carte animée du réseau",
    "description": "Les lignes ouvertes, suspendues et fermées d'Air France et de ses ancêtres, année après année, sur un planisphère.",
    "order": 1,
}

OPEN = "o"      # ouverture / reprise : la ligne existe
CLOSE = "f"     # suspension / fermeture : la ligne n'existe plus
CODES = {"ouverture": OPEN, "reprise": OPEN, "suspension": CLOSE, "fermeture": CLOSE}
NEAR = 3.0      # deux villes de même nom à moins de 3° sont la même ville (Saint-Louis FR / SN sinon)


def prepare(data):
    """Villes dédupliquées + segments avec leurs événements datés. Renvoie un dict prêt à être inliné."""
    cities, index, by_name = [], {}, {}

    def city_id(c):
        name = unescape(c["name"]).strip()
        for i in by_name.get(name, []):
            if abs(cities[i][1] - c["lat"]) < NEAR and abs(cities[i][2] - c["lon"]) < NEAR:
                return i
        cities.append([name, round(c["lat"], 2), round(c["lon"], 2)])
        by_name.setdefault(name, []).append(len(cities) - 1)
        return len(cities) - 1

    segments, titles = {}, {}
    n_test = 0
    for rec in data.records():
        for route in rec["routes"]:
            code = CODES.get(route["action"])
            if code is None:
                n_test += route["action"] == "vol_essai"
                continue
            ids = [city_id(c) for c in route["cities"]]
            for a, b in zip(ids, ids[1:]):
                if a == b:
                    continue
                key = (min(a, b), max(a, b))
                segments.setdefault(key, []).append([rec["date"], code, rec["id"]])
                titles[rec["id"]] = rec["title"]
    seg_list = [[a, b, evs] for (a, b), evs in segments.items()]
    used = {c for a, b, _ in seg_list for c in (a, b)}
    remap = {old: new for new, old in enumerate(sorted(used))}
    return {
        "cities": [cities[i] for i in sorted(used)],
        "segments": [[remap[a], remap[b], evs] for a, b, evs in seg_list],
        "titles": {str(k): v for k, v in titles.items()},
        "tests": n_test,
    }


SCRIPT = r"""
const D = __DATA__;
const dark = () => matchMedia("(prefers-color-scheme: dark)").matches;
const Y0 = 1908, Y1 = 2022;

// État d'une ligne au 31 décembre de l'année y : dernier événement ouverture/reprise (o) ou suspension/fermeture (f).
function stateAt(seg, y) {
  let last = null, lastDate = null, openedIn = false, closedIn = false;
  for (const [d, c] of seg[2]) {
    const ey = +d.slice(0, 4);
    if (ey > y) break;
    last = c; lastDate = d;
    if (ey === y) { if (c === "o") openedIn = true; else closedIn = true; }
  }
  return { open: last === "o", openedIn, closedIn, seen: last !== null };
}
D.segments.forEach(s => s[2].sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));

const years = d3.range(Y0, Y1 + 1);
const counts = years.map(y => {
  let open = 0, o = 0, f = 0;
  for (const s of D.segments) { const st = stateAt(s, y); open += st.open; o += st.openedIn; f += st.closedIn; }
  return { y, open, o, f };
});

const W = 1000, H = 520;
const svg = d3.select("#map").attr("viewBox", `0 0 ${W} ${H}`);
const proj = d3.geoEqualEarth().fitExtent([[8, 8], [W - 8, H - 8]], { type: "Sphere" });
const path = d3.geoPath(proj);
svg.append("path").attr("class", "sphere").attr("d", path({ type: "Sphere" }));
svg.append("path").attr("class", "grat").attr("d", path(d3.geoGraticule10()));
const gLand = svg.append("g"), gLines = svg.append("g"), gDots = svg.append("g");

// Fond de carte : world-atlas via jsdelivr (même CDN que D3) ; sans réseau, la carte reste lisible grâce aux villes.
fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/land-110m.json").then(r => r.json()).then(topo => {
  const arcs = topo.arcs, [kx, ky] = topo.transform.scale, [tx, ty] = topo.transform.translate;
  const decoded = arcs.map(a => { let x = 0, y = 0; return a.map(([dx, dy]) => [(x += dx) * kx + tx, (y += dy) * ky + ty]); });
  const ring = idx => idx.flatMap(i => i >= 0 ? decoded[i] : decoded[~i].slice().reverse());
  const polys = [];
  for (const g of topo.objects.land.geometries) {
    if (g.type === "Polygon") polys.push(g.arcs.map(ring));
    else if (g.type === "MultiPolygon") g.arcs.forEach(p => polys.push(p.map(ring)));
  }
  gLand.append("path").attr("class", "land").attr("d", path({ type: "MultiPolygon", coordinates: polys }));
}).catch(() => {});

const P = D.cities.map(c => proj([c[2], c[1]]));
const arc = s => {
  const a = D.cities[s[0]], b = D.cities[s[1]];
  return path({ type: "LineString", coordinates: [[a[2], a[1]], [b[2], b[1]]] });
};
const arcs = D.segments.map(arc);

const slider = document.getElementById("year"), label = document.getElementById("ylabel");
slider.min = Y0; slider.max = Y1;
const tip = document.getElementById("events");

function draw(y) {
  label.textContent = y;
  const rows = D.segments.map((s, i) => ({ i, s, st: stateAt(s, y) }));
  const shown = rows.filter(r => r.st.open || r.st.closedIn);
  gLines.selectAll("path").data(shown, r => r.i).join("path")
    .attr("d", r => arcs[r.i])
    .attr("class", r => "ln " + (r.st.closedIn && !r.st.open ? "closed" : r.st.openedIn ? "new" : "old"));
  const cityOpen = new Set(shown.flatMap(r => [r.s[0], r.s[1]]));
  gDots.selectAll("circle").data([...cityOpen], d => d).join("circle")
    .attr("cx", d => P[d][0]).attr("cy", d => P[d][1]).attr("r", 1.8).attr("class", "dot");
  const c = counts[y - Y0];
  document.getElementById("stat").innerHTML =
    `<b>${c.open}</b> lignes ouvertes · <span class="n">+${c.o} ouvertures/reprises</span> · <span class="c">${c.f} suspensions/fermetures</span> cette année`;
  d3.select("#cursor").attr("x1", sx(y)).attr("x2", sx(y));
  // événements de l'année, les plus récents d'abord dans l'ordre du calendrier
  const evs = [];
  for (const s of D.segments) for (const [d, code, id] of s[2]) if (+d.slice(0, 4) === y)
    evs.push({ d, code, id, a: D.cities[s[0]][0], b: D.cities[s[1]][0] });
  evs.sort((p, q) => p.d < q.d ? -1 : 1);
  tip.innerHTML = evs.length ? evs.slice(0, 60).map(e =>
    `<li class="${e.code}"><time>${e.d.slice(5).split("-").reverse().join("/")}</time> ${e.code === "o" ? "ouverture" : "fermeture"} ${e.a} – ${e.b}
     <small>${D.titles[e.id] || ""}</small></li>`).join("") + (evs.length > 60 ? `<li class="more">… et ${evs.length - 60} autres</li>` : "")
    : `<li class="more">Aucun événement de ligne daté de ${y} dans les textes.</li>`;
}

// Courbe : lignes ouvertes par année (cumul des événements)
const SW = 1000, SH = 90;
const sx = d3.scaleLinear([Y0, Y1], [30, SW - 10]), sy = d3.scaleLinear([0, d3.max(counts, c => c.open)], [SH - 18, 6]);
const spark = d3.select("#spark").attr("viewBox", `0 0 ${SW} ${SH}`);
spark.append("path").datum(counts).attr("class", "area")
  .attr("d", d3.area().x(c => sx(c.y)).y0(sy(0)).y1(c => sy(c.open)));
spark.append("g").attr("transform", `translate(0,${SH - 18})`).attr("class", "ax")
  .call(d3.axisBottom(sx).tickFormat(d3.format("d")).ticks(12).tickSize(3));
spark.append("g").attr("transform", "translate(30,0)").attr("class", "ax")
  .call(d3.axisLeft(sy).ticks(3).tickSize(3));
spark.append("line").attr("id", "cursor").attr("y1", 0).attr("y2", SH - 18).attr("class", "cursor");
spark.append("rect").attr("x", 30).attr("y", 0).attr("width", SW - 40).attr("height", SH - 18).attr("fill", "transparent")
  .on("click", ev => setYear(Math.round(sx.invert(d3.pointer(ev)[0]))));

let timer = null;
function setYear(y) { y = Math.max(Y0, Math.min(Y1, y)); slider.value = y; draw(y); }
function toggle() {
  const b = document.getElementById("play");
  if (timer) { clearInterval(timer); timer = null; b.textContent = "▶ Lecture"; return; }
  if (+slider.value >= Y1) slider.value = Y0;
  b.textContent = "⏸ Pause";
  timer = setInterval(() => { const y = +slider.value + 1; if (y > Y1) { toggle(); return; } setYear(y); }, 350);
}
document.getElementById("play").onclick = toggle;
slider.oninput = () => { if (timer) toggle(); setYear(+slider.value); };
setYear(1950);
"""

BODY = """
<div class="card">
  <div class="bar"><button id="play">▶ Lecture</button><input id="year" type="range" step="1" value="1950"><span id="ylabel" class="yl"></span></div>
  <p id="stat" class="stat"></p>
  <svg id="map" role="img" aria-label="Planisphère des lignes ouvertes"></svg>
  <p class="legend"><i class="k old"></i>ligne ouverte <i class="k new"></i>ouverte cette année <i class="k closed"></i>suspendue ou fermée cette année</p>
  <svg id="spark" role="img" aria-label="Nombre de lignes ouvertes par année"></svg>
  <p class="note">Courbe : lignes ouvertes selon les textes. Cliquer dessus pour changer d'année.</p>
</div>
<div class="card" style="margin-top:16px"><h2>Événements de l'année</h2><ul id="events"></ul></div>
<p class="note">Une ligne est comptée ouverte dès qu'un texte en annonce l'ouverture ou la reprise, jusqu'à une suspension ou une fermeture citée : les fermetures étant rarement mentionnées, le nombre de lignes ouvertes croît mécaniquement et surestime le réseau réel. Les lignes à escales sont décomposées en tronçons. Les vols d'essai (%TESTS%) ne sont pas comptés. Le fond de carte est chargé depuis jsdelivr ; hors ligne, seuls les villes et les tracés s'affichent.</p>
"""

HEAD = """<script src="https://cdn.jsdelivr.net/npm/d3@7"></script><style>
.bar { display:flex; gap:14px; align-items:center; } .bar input { flex:1; } .yl { font:600 28px/1 system-ui; min-width:3.2em; text-align:right; }
button { font:inherit; padding:6px 14px; border:1px solid var(--line); border-radius:8px; background:var(--card); color:var(--ink); cursor:pointer; }
button:hover { border-color:var(--accent); }
.stat { margin:10px 0 4px; color:var(--muted); } .stat b { color:var(--ink); font-size:18px; } .stat .n { color:#d95926; } .stat .c { color:#8a8f98; }
svg { width:100%; height:auto; display:block; }
.sphere { fill:color-mix(in srgb, var(--accent) 6%, var(--card)); stroke:var(--line); } .grat { fill:none; stroke:var(--line); stroke-width:.4; }
.land { fill:color-mix(in srgb, var(--muted) 22%, var(--card)); stroke:var(--line); stroke-width:.4; }
.ln { fill:none; stroke-linecap:round; } .ln.old { stroke:#2a78d6; stroke-width:.9; opacity:.45; }
.ln.new { stroke:#eb6834; stroke-width:1.8; opacity:1; } .ln.closed { stroke:#8a8f98; stroke-width:1.4; stroke-dasharray:4 3; opacity:.9; }
@media (prefers-color-scheme: dark) { .ln.old { stroke:#5a9bec; } .ln.new { stroke:#ff8a57; } }
.dot { fill:var(--ink); opacity:.55; }
.legend { color:var(--muted); font-size:13px; margin:6px 0 10px; } .k { display:inline-block; width:18px; height:0; border-top:2px solid; margin:0 6px 3px 12px; vertical-align:middle; }
.k.old { border-color:#2a78d6; opacity:.6; } .k.new { border-color:#eb6834; } .k.closed { border-color:#8a8f98; border-top-style:dashed; }
.area { fill:color-mix(in srgb, var(--accent) 25%, transparent); stroke:var(--accent); } .cursor { stroke:var(--accent2); stroke-width:1.5; }
.ax text { fill:var(--muted); font-size:10px; } .ax path, .ax line { stroke:var(--line); }
#events { list-style:none; margin:0; padding:0; columns:2 380px; font-size:14px; } #events li { padding:3px 0; break-inside:avoid; }
#events time { color:var(--muted); font-variant-numeric:tabular-nums; margin-right:4px; } #events small { display:block; color:var(--muted); }
#events li.f { color:var(--muted); } #events li.more { color:var(--muted); font-style:italic; }
h2 { font-size:17px; margin:0 0 8px; } .note { color:var(--muted); font-size:13px; max-width:90ch; }
</style>"""


def build(data):
    prepared = prepare(data)
    body = BODY.replace("%TESTS%", str(prepared["tests"]))
    script = SCRIPT.replace("__DATA__", embed(prepared))
    return page_shell(
        META["title"],
        "Chaque trait est une ligne citée par les éphémérides ; faites défiler les années de 1908 à 2022 pour voir le réseau se déployer.",
        body, head_extra=HEAD, script=script,
    )
