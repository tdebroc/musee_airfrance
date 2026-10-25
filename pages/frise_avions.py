"""Frise des avions : chaque appareil (famille) avec ses mentions année par année, d'après les `aircraft` enrichis."""
import re
import unicodedata
from collections import Counter, defaultdict

from .common import embed, page_shell

META = {
    "slug": "frise-avions",
    "title": "Frise des avions",
    "description": "Tous les appareils cités dans les éphémérides, du Farman Goliath à l'A350 : première et dernière mention, année par année.",
    "order": 2,
}

# Noms trop vagues pour être un appareil.
GENERIC = {"boeing", "airbus", "air france", "avion leger", "avion de transport", "hydravion", "lockheed", "vickers",
           "tupolev", "potez", "breguet", "farman", "caudron", "latecoere", "spad", "fokker", "bloch", "salmson", "sikorsky",
           "dewoitine", "wibault", "embraer", "atr", "beechcraft", "blériot", "bleriot", "couzinet", "northrop", "sipa",
           "cams", "electra", "pelican", "sommer", "lefort", "monospar", "goeland", "gouland", "general electric ge90",
           "rolls-royce avon", "bristol siddeley olympus", "douglas dc"}

# (motif sur le nom normalisé, nom canonique). Premier motif qui correspond.
ALIASES = [
    (r"caravelle|se ?210$|^se[ .-]?210", "Sud-Aviation Caravelle"),
    (r"concorde", "Concorde"),
    (r"languedoc", "SNCASE Languedoc"),
    (r"armagnac", "SNCASE Armagnac"),
    (r"deux-?ponts|breguet 76[03]|provence", "Bréguet 763 Deux-Ponts"),
    (r"constellation", "Lockheed Constellation"),
    (r"1649|starliner", "Lockheed L-1649 Starliner"),
    (r"electra", "Lockheed Electra"),
    (r"erj|embraer 145|regional jet", "Embraer ERJ 145"),
    (r"e-?jets?$|embraer 190", "Embraer E-Jet"),
    (r"crj|canadair", "Bombardier CRJ"),
    (r"breguet (14|xiv)$", "Breguet XIV"),
    (r"dewoitine d?\.?338", "Dewoitine 338"),
    (r"dewoitine d?\.?333", "Dewoitine 333"),
    (r"dewoitine d?\.?332", "Dewoitine 332"),
    (r"fokker (f[ .-]?)?27", "Fokker F27"),
    (r"fokker (f[ .-]?)?28", "Fokker F28"),
    (r"heron", "de Havilland Heron"),
    (r"catalina", "Consolidated Catalina"),
    (r"liberator|b-24", "Consolidated Liberator"),
    (r"lat[eé]co[eè]re 521|laté 521", "Latécoère 521"),
    (r"goe?land|goëland", "Caudron Goéland"),
    (r"(mcdonnell )?douglas dc[ .-]?10|^dc-10$", "McDonnell Douglas DC-10"),
    (r"(mcdonnell )?douglas dc[ .-]?8|^dc[ .-]?8$", "Douglas DC-8"),
    (r"noratlas|nord 250", "Nord Noratlas"),
    (r"i[lr]?[ao]?u?shin.* il-?14|il-?14", "Iliouchine Il-14"),
    (r"i[lr]?[ao]?u?shin.* il-?18|il-?18", "Iliouchine Il-18"),
    (r"tupolev (tu-)?104|tu-104", "Tupolev Tu-104"),
    (r"guppy", "Aero Spacelines Super Guppy"),
    (r"twin otter|dhc-6", "de Havilland Canada Twin Otter"),
    (r"islander|bn-2", "Britten-Norman Islander"),
    (r"farman.*(goliath|f\.?60)|goliath", "Farman Goliath"),
    (r"jabiru", "Farman Jabiru"),
    (r"boeing 307", "Boeing 307 Stratoliner"),
    (r"stratocruiser|boeing 377", "Boeing 377 Stratocruiser"),
    (r"bristol 170", "Bristol 170 Freighter"),
    (r"salmson 2", "Salmson 2A2"),
    (r"spad s?\.?46", "SPAD 46"),
    (r"spad s?\.?56", "SPAD 56"),
    (r"spad s?\.?33", "SPAD 33"),
    (r"lio?r[eé].*(h[ .-]?13)", "Lioré et Olivier H-13"),
    (r"lio?r[eé].*(h[ .-]?242)|leo (h\.)?242", "Lioré et Olivier LeO H-242"),
    (r"nord[ -]?262", "Nord 262"),
    (r"hurel.dubois", "Hurel-Dubois HD.32"),
    (r"saab 91", "Saab 91 Safir"),
    (r"jodel", "Jodel D.11"),
    (r"caudron g[ .-]?3", "Caudron G.3"),
    (r"caudron g[ .-]?4", "Caudron G.4"),
    (r"atr 42/72", "ATR 42"),
    (r"transall", "Transall C-160"),
    (r"beechcraft (model )?99", "Beechcraft 99"),
    (r"kc-135|c-135", "Boeing C-135"),
    (r"dc[ .-]?9\b", "Douglas DC-9"),
]
ALIASES = [(re.compile(p), name) for p, name in ALIASES]

# Événements : ce qui date vraiment l'appareil (hors simple mention).
LIFE = {"commande": "c", "livraison": "l", "mise_en_service": "s", "premier_vol": "p", "retrait": "r", "accident": "a",
        "record": "k", "exploitation": "e", "mention": "m"}


def plain(s):
    return "".join(ch for ch in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(ch) != "Mn").strip()


def canonical(family):
    """Nom canonique d'une famille, ou None si le nom est trop vague."""
    key = plain(family)
    if key in GENERIC:
        return None
    for pattern, name in ALIASES:
        if pattern.search(key):
            return name
    return family.strip()


def prepare(data):
    fams = defaultdict(lambda: {"ev": [], "man": Counter(), "raw": Counter()})
    titles, dropped = {}, 0
    for rec in data.records():
        seen = set()
        for a in rec["aircraft"]:
            name = canonical(a["family"] or a["model"] or "")
            if name is None:
                dropped += 1
                continue
            f = fams[name]
            f["raw"][a["family"]] += 1
            if a.get("manufacturer"):
                f["man"][a["manufacturer"]] += 1
            ev = LIFE.get(a["event"], "m")
            if (name, ev) in seen:
                continue
            seen.add((name, ev))
            f["ev"].append([rec["date"], ev, rec["id"]])
            titles[rec["id"]] = rec["title"]
    out = []
    for name, f in fams.items():
        evs = f["ev"]
        real = [e for e in evs if e[1] != "m"] or evs
        out.append({
            "n": name,
            "m": f["man"].most_common(1)[0][0] if f["man"] else "",
            "a": min(e[0] for e in real), "z": max(e[0] for e in real),   # première / dernière mention « factuelle »
            "a0": min(e[0] for e in evs), "z0": max(e[0] for e in evs),   # y compris simples mentions
            "ev": evs, "k": len({e[2] for e in evs}),
        })
    out.sort(key=lambda f: (f["a"], f["n"]))
    return {"fams": out, "titles": {str(k): v for k, v in titles.items()}, "dropped": dropped}


BODY = """
<div class="card ctl">
  <label>Recherche <input id="q" type="search" placeholder="Comet, A380, Caravelle…"></label>
  <label>Mentions min. <input id="minK" type="range" min="1" max="40" value="3"><b id="minKv">3</b></label>
  <label>Tri <select id="sort"><option value="a">première mention</option><option value="k">nombre de textes</option><option value="z">dernière mention</option><option value="n">nom</option></select></label>
  <label><input id="withM" type="checkbox"> compter les simples mentions (sans événement daté)</label>
  <span id="count" class="muted"></span>
</div>
<div class="card" style="margin-top:14px;padding:8px 8px 8px 0;overflow-x:auto"><div id="chart"></div></div>
<div class="legend card">
  <span><i class="sw s-e"></i> année avec événement (exploitation, service, livraison…)</span>
  <span><i class="sw s-m"></i> année avec simple mention</span>
  <span><i class="mk">◆</i> commande</span><span><i class="mk">▲</i> mise en service / livraison / 1<sup>er</sup> vol</span>
  <span><i class="mk">■</i> retrait</span><span><i class="mk" style="color:var(--accent2)">✖</i> accident</span>
  <p class="muted">La date est celle de l'éphéméride, pas toujours celle de l'événement : un appareil retiré peut être évoqué bien plus tard (rétrospectives, anniversaires). Les noms vagues (« Boeing », « Airbus ») sont écartés et les variantes d'un même appareil (Caravelle, Concorde, Languedoc…) fusionnées.</p>
</div>
<div id="detail" class="card" style="margin-top:14px;display:none"></div>
<style>
.ctl { display:flex; flex-wrap:wrap; gap:18px; align-items:center; }
.ctl input[type=search] { padding:5px 8px; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--ink); }
.ctl select { padding:4px; background:var(--bg); color:var(--ink); border:1px solid var(--line); border-radius:6px; }
.muted { color:var(--muted); font-size:13px; }
.legend { margin-top:14px; display:flex; flex-wrap:wrap; gap:6px 18px; font-size:13px; }
.legend p { flex-basis:100%; margin:4px 0 0; }
.sw { display:inline-block; width:14px; height:10px; border-radius:2px; margin-right:4px; }
.s-e { background:var(--accent); } .s-m { background:var(--accent); opacity:.3; } .mk { font-style:normal; color:var(--accent); }
#detail ul { margin:6px 0 0; padding:0; list-style:none; max-height:360px; overflow:auto; }
#detail li { padding:3px 0; border-bottom:1px solid var(--line); font-size:13px; }
#detail li b { display:inline-block; width:92px; color:var(--muted); font-weight:500; }
#detail li em { color:var(--muted); font-style:normal; margin-right:6px; }
.row { cursor:pointer; } .row:hover .bg { fill:var(--line); opacity:.5; }
</style>
"""

SCRIPT = r"""
const D = __DATA__;
const EVNAME = {c:"commande", l:"livraison", s:"mise en service", p:"premier vol", r:"retrait", a:"accident", k:"record", e:"exploitation", m:"mention"};
const Y0 = 1905, Y1 = 2023, ROW = 17, LEFT = 230, RIGHT = 20, W = 1100;
const x = d3.scaleLinear().domain([Y0, Y1 + 1]).range([LEFT, W - RIGHT]);
const cell = x(Y0 + 1) - x(Y0);
const yr = d => +d.slice(0, 4);

// Années actives par famille : { année: [événements datés, simples mentions] }
D.fams.forEach(f => {
  f.years = new Map();
  for (const [d, e] of f.ev) {
    const y = yr(d); const c = f.years.get(y) || [0, 0];
    c[e === "m" ? 1 : 0]++; f.years.set(y, c);
  }
});

const svg = d3.select("#chart").append("svg").attr("width", W).style("max-width", "100%").attr("viewBox", [0, 0, W, 100]);
const axisG = svg.append("g");
const body = svg.append("g");
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

function filtered() {
  const q = document.getElementById("q").value.trim().toLowerCase();
  const minK = +document.getElementById("minK").value;
  const withM = document.getElementById("withM").checked;
  const sort = document.getElementById("sort").value;
  let list = D.fams.filter(f => f.k >= minK && (!q || (f.n + " " + f.m).toLowerCase().includes(q)));
  const first = f => withM ? f.a0 : f.a, last = f => withM ? f.z0 : f.z;
  list = list.slice().sort((p, q2) => sort === "k" ? q2.k - p.k : sort === "n" ? p.n.localeCompare(q2.n, "fr")
        : sort === "z" ? (last(p) < last(q2) ? -1 : 1) : (first(p) < first(q2) ? -1 : first(p) > first(q2) ? 1 : p.n.localeCompare(q2.n, "fr")));
  return { list, withM, first, last };
}

function draw() {
  const { list, withM, first, last } = filtered();
  document.getElementById("minKv").textContent = document.getElementById("minK").value;
  document.getElementById("count").textContent = list.length + " appareil" + (list.length > 1 ? "s" : "") + " sur " + D.fams.length;
  const H = 30 + list.length * ROW + 6;
  svg.attr("viewBox", [0, 0, W, H]).style("height", "auto").style("aspect-ratio", W + " / " + H);
  const ink = css("--ink"), muted = css("--muted"), line = css("--line"), acc = css("--accent"), acc2 = css("--accent2");
  axisG.selectAll("*").remove();
  const ticks = d3.range(1910, Y1 + 1, 10);
  axisG.selectAll("text").data(ticks).join("text").attr("x", d => x(d)).attr("y", 14).attr("text-anchor", "middle").attr("fill", muted).attr("font-size", 11).text(d => d);
  axisG.selectAll("line").data(ticks).join("line").attr("x1", d => x(d)).attr("x2", d => x(d)).attr("y1", 20).attr("y2", H).attr("stroke", line);

  const rows = body.selectAll("g.row").data(list, d => d.n).join(
    enter => { const g = enter.append("g").attr("class", "row"); g.append("rect").attr("class", "bg"); g.append("text").attr("class", "lbl"); g.append("g").attr("class", "cells"); g.append("g").attr("class", "mks"); g.append("title"); return g; });
  rows.attr("transform", (d, i) => `translate(0,${26 + i * ROW})`).on("click", (e, d) => detail(d));
  rows.select("rect.bg").attr("x", 0).attr("y", 0).attr("width", W).attr("height", ROW).attr("fill", "transparent");
  rows.select("text.lbl").attr("x", LEFT - 8).attr("y", 12).attr("text-anchor", "end").attr("font-size", 11.5).attr("fill", ink)
      .text(d => d.n.length > 34 ? d.n.slice(0, 33) + "…" : d.n);
  rows.select("title").text(d => `${d.n}${d.m ? " (" + d.m + ")" : ""}\n${d.k} texte(s) · ${first(d).slice(0, 4)}–${last(d).slice(0, 4)}`);
  rows.each(function (d) {
    const g = d3.select(this);
    const cells = [...d.years].filter(([, c]) => c[0] > 0 || withM).map(([y, c]) => ({ y, e: c[0], m: c[1] }));
    g.select("g.cells").selectAll("rect").data(cells).join("rect")
      .attr("x", c => x(c.y)).attr("y", 3).attr("width", Math.max(cell - .4, 1.5)).attr("height", ROW - 6).attr("rx", 1.5)
      .attr("fill", acc).attr("opacity", c => c.e ? Math.min(.45 + .15 * c.e, 1) : .28);
    const marks = [];
    const seen = new Set();
    for (const [dt, e] of d.ev) {
      if (!"clspra".includes(e) || e === "m") continue;
      const sym = e === "c" ? "◆" : e === "r" ? "■" : e === "a" ? "✖" : "▲";
      if (e === "a" || e === "r") { const k = e + yr(dt); if (seen.has(k)) continue; seen.add(k); marks.push({ dt, sym, e }); }
      else if (!seen.has("first" + sym)) { seen.add("first" + sym); marks.push({ dt, sym, e }); }
    }
    g.select("g.mks").selectAll("text").data(marks).join("text")
      .attr("x", m => x(yr(m.dt)) + cell / 2).attr("y", 12).attr("text-anchor", "middle").attr("font-size", 9)
      .attr("fill", m => m.e === "a" ? acc2 : css("--card")).attr("stroke", m => m.e === "a" ? css("--card") : "none").attr("stroke-width", 2.5).attr("paint-order", "stroke").text(m => m.sym);
  });
}

function detail(f) {
  const el = document.getElementById("detail");
  el.style.display = "block";
  const evs = f.ev.slice().sort((a, b) => a[0] < b[0] ? -1 : 1);
  const esc = s => s.replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  el.innerHTML = `<b>${esc(f.n)}</b> <span class="muted">${f.m ? esc(f.m) + " · " : ""}${f.k} textes · ${f.a.slice(0, 4)}–${f.z.slice(0, 4)}</span><ul>` +
    evs.map(([d, e, id]) => `<li><b>${d}</b><em>${EVNAME[e]}</em>${esc(D.titles[id] || "")}</li>`).join("") + "</ul>";
  el.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

["q", "minK", "sort", "withM"].forEach(id => document.getElementById(id).addEventListener("input", draw));
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", draw);
draw();
"""


def build(data):
    payload = prepare(data)
    script = SCRIPT.replace("__DATA__", embed(payload))
    lead = (f"{len(payload['fams'])} appareils distincts repérés dans les textes, de l'avion de la Grande Guerre à l'A350. "
            "Chaque ligne montre les années où l'appareil est cité ; cliquez sur une ligne pour lire les textes.")
    head = '<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>'
    return page_shell(META["title"], lead, BODY, head_extra=head, script=script)
