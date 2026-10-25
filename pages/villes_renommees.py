"""Villes renommées : vrais changements de nom de villes (Saïgon → Hô Chi Minh-Ville), avec carte, date et emploi dans les textes.

Les `historical_name` de enriched.jsonl sont trop bruités (aéroports, abréviations, variantes d'orthographe) pour servir
directement : la liste des renommages est donc curée à la main (CITIES). Les textes sont ensuite relus pour voir
quand l'ancien et le nouveau nom sont réellement employés ; les coordonnées viennent des lieux enrichis.
"""
import re
import unicodedata
from collections import Counter

from .common import embed, page_shell

META = {
    "slug": "villes-renommees",
    "title": "Villes renommées",
    "description": "Saïgon, Fort-Lamy, Léopoldville, Bombay… les villes qui ont changé de nom, quand les textes ont basculé du vieux nom au nouveau.",
    "order": 9,
}

KINDS = {"renommage": "changement de nom", "translit": "changement de transcription"}

# (anciens noms, nouveaux noms, pays actuel, année du changement ou None, année approximative ?, nature, note)
# L'année est une connaissance historique extérieure aux textes ; None = date incertaine ou graduelle.
CITIES = [
    (["Saïgon", "Saigon"], ["Hô Chi Minh-Ville", "Ho Chi Minh-Ville"], "Viêt Nam", 1976, False, "renommage", "Réunification du Viêt Nam ; Saïgon est resté d'usage courant."),
    (["Fort-Lamy"], ["N'Djamena", "N'Djaména"], "Tchad", 1973, False, "renommage", ""),
    (["Fort-Archambault"], ["Sarh"], "Tchad", 1972, False, "renommage", ""),
    (["Bône"], ["Annaba"], "Algérie", 1962, True, "renommage", "Indépendance de l'Algérie."),
    (["Philippeville"], ["Skikda"], "Algérie", 1962, True, "renommage", "Indépendance de l'Algérie."),
    (["Colomb-Béchar", "Clomb-Béchar"],["Béchar", "Bechar"], "Algérie", 1962, True, "renommage", "Indépendance de l'Algérie."),
    (["Orléansville"], ["El Asnam", "Chlef"], "Algérie", 1962, True, "renommage", "El Asnam en 1962, Chlef depuis 1981."),
    (["Bougie"], ["Béjaïa", "Bejaia"], "Algérie", None, True, "renommage", "Arabisation après l'indépendance."),
    (["Port-Lyautey"], ["Kénitra", "Kenitra"], "Maroc", 1956, True, "renommage", "Indépendance du Maroc."),
    (["Cap Juby", "Cap-Juby"], ["Tarfaya"], "Maroc", 1958, False, "renommage", "Rétrocession par l'Espagne au Maroc."),
    (["Villa Cisneros"], ["Dakhla"], "Sahara occidental", 1976, True, "renommage", "Départ de l'Espagne."),
    (["Port-Étienne"], ["Nouadhibou"], "Mauritanie", 1970, True, "renommage", ""),
    (["Fort-Gouraud"], ["Fdérik", "Fderik"], "Mauritanie", None, True, "renommage", "Rebaptisée après l'indépendance."),
    (["Bathurst"], ["Banjul"], "Gambie", 1973, False, "renommage", ""),
    (["Léopoldville"], ["Kinshasa"], "R. D. du Congo", 1966, False, "renommage", "Campagne de « recours à l'authenticité » du Congo."),
    (["Élisabethville"], ["Lubumbashi"], "R. D. du Congo", 1966, False, "renommage", ""),
    (["Coquilhatville"], ["Mbandaka"], "R. D. du Congo", 1966, False, "renommage", ""),
    (["Stanleyville"], ["Kisangani"], "R. D. du Congo", 1966, False, "renommage", ""),
    (["Luluabourg"], ["Kananga"], "R. D. du Congo", 1966, False, "renommage", ""),
    (["Port-Francqui"], ["Ilebo"], "R. D. du Congo", 1966, False, "renommage", ""),
    (["Broken Hill"], ["Kabwe"], "Zambie", 1966, False, "renommage", ""),
    (["Salisbury"], ["Harare"], "Zimbabwe", 1982, False, "renommage", "Capitale de la Rhodésie, desservie par l'UAT."),
    (["Lourenço Marques"], ["Maputo"], "Mozambique", 1976, False, "renommage", ""),
    (["Tananarive"], ["Antananarivo"], "Madagascar", None, True, "renommage", "Nom malgache complet, adopté progressivement en français."),
    (["Tamatave"], ["Toamasina"], "Madagascar", None, True, "renommage", ""),
    (["Majunga"], ["Mahajanga"], "Madagascar", None, True, "renommage", ""),
    (["Diego-Suarez", "Diégo-Suarez"], ["Antsiranana"], "Madagascar", None, True, "renommage", ""),
    (["Tuléar"], ["Toliara"], "Madagascar", None, True, "renommage", ""),
    (["Fort-Dauphin"], ["Tôlanaro", "Taolagnaro"], "Madagascar", None, True, "renommage", ""),
    (["Tourane"], ["Da Nang", "Danang"], "Viêt Nam", None, True, "renommage", "Rebaptisée Đà Nẵng dans les années 1950."),
    (["Batavia"], ["Jakarta", "Djakarta"], "Indonésie", 1949, True, "renommage", "Indépendance de l'Indonésie (Jakarta sous l'occupation japonaise dès 1942)."),
    (["Rangoon", "Rangoun"], ["Yangon"], "Myanmar", 1989, False, "renommage", ""),
    (["Calcutta"], ["Kolkata"], "Inde", 2001, False, "renommage", ""),
    (["Bombay"], ["Mumbai"], "Inde", 1995, False, "renommage", ""),
    (["Madras"], ["Chennai"], "Inde", 1996, False, "renommage", ""),
    (["Bangalore"], ["Bengaluru", "Bengalore"], "Inde", 2014, False, "renommage", ""),
    (["Allahabad"], ["Prayagraj"], "Inde", 2018, False, "renommage", ""),
    (["Constantinople"], ["Istanbul"], "Turquie", 1930, False, "renommage", "Loi postale turque de 1930 ; Istanbul était déjà le nom usuel."),
    (["Angora"], ["Ankara"], "Turquie", 1930, False, "renommage", ""),
    (["Léningrad"], ["Saint-Pétersbourg"], "Russie", 1991, False, "renommage", "Pétrograd entre 1914 et 1924."),
    (["Lydda"], ["Lod"], "Israël", 1948, True, "renommage", "Lod est le nom hébreu de la ville de l'aéroport de Tel-Aviv."),
    (["Pékin"], ["Beijing"], "Chine", None, True, "translit", "Passage à la transcription pinyin : même ville, autre graphie."),
    (["Canton"], ["Guangzhou"], "Chine", None, True, "translit", "Passage à la transcription pinyin ; « Canton » reste très employé après l'ouverture de la ligne (2004)."),
]


def fold(text):
    """Sans accents, ponctuation de mots en espaces, sans changer la longueur (positions alignées sur l'original)."""
    out = []
    for ch in text:
        if ch in "-–’' \n\t\r":
            out.append(" ")
            continue
        base = unicodedata.normalize("NFD", ch)[0]
        out.append(base if len(base) == 1 else ch)
    return "".join(out)


def pattern(names):
    alts = sorted((re.escape(fold(n)).replace(r"\ ", " +") for n in names), key=len, reverse=True)
    return re.compile(r"(?<![A-Za-z])(?:" + "|".join(alts) + r")(?![A-Za-z])")


def plain(s):
    return re.sub(r"[^a-z0-9]", "", fold(s).lower())


def excerpt(text, start, end):
    a, b = max(0, start - 70), min(len(text), end + 70)
    return ("…" if a else "") + re.sub(r"\s+", " ", text[a:b]).strip() + ("…" if b < len(text) else "")


def coordinates(data):
    """Position la plus fréquente par nom (lieux et villes de lignes), via le nom courant ou l'ancien nom employé."""
    seen = {}
    for rec in data.records():
        places = list(rec["places"]) + [c for r in rec["routes"] for c in r["cities"]]
        for p in places:
            if p.get("lat") is None or p.get("lon") is None:
                continue
            for name in (p.get("name"), p.get("historical_name")):
                if name:
                    seen.setdefault(plain(name), Counter())[(round(p["lat"], 2), round(p["lon"], 2))] += 1
    return seen


def prepare(data):
    coords = coordinates(data)
    texts = {i: data.text(i) for i in data.raw}
    folded = {i: fold(t) for i, t in texts.items()}
    dates = {i: data.raw[i]["field_date_value"][:10] for i in texts}
    cities = []
    for olds, news, country, year, approx, kind, note in CITIES:
        old_re, new_re = pattern(olds), pattern(news)
        hits = []
        for i, f in folded.items():
            masked = f
            old_found = None
            for m in old_re.finditer(f):
                old_found = old_found or m
                masked = masked[:m.start()] + " " * (m.end() - m.start()) + masked[m.end():]
            new_found = next(new_re.finditer(masked), None)
            if old_found:
                hits.append((dates[i], i, "o", excerpt(texts[i], old_found.start(), old_found.end())))
            if new_found:
                hits.append((dates[i], i, "n", excerpt(texts[i], new_found.start(), new_found.end())))
        if not hits:
            continue
        hits.sort()
        position = None
        for name in news + olds:
            counter = coords.get(plain(name))
            if counter:
                position = counter.most_common(1)[0][0]
                break
        old_dates = [h[0] for h in hits if h[2] == "o"]
        new_dates = [h[0] for h in hits if h[2] == "n"]
        cities.append({
            "o": olds[0], "n": news[0], "c": country, "y": year, "ap": approx, "k": kind, "note": note,
            "la": position[0] if position else None, "lo": position[1] if position else None,
            "t": [[d, i, f, e] for d, i, f, e in hits],
            "oa": old_dates[0][:4] if old_dates else None, "oz": old_dates[-1][:4] if old_dates else None,
            "na": new_dates[0][:4] if new_dates else None,
        })
    cities.sort(key=lambda c: (c["y"] is None, c["y"] or 0, c["o"]))
    titles = {i: data.enriched[i]["title"] for c in cities for _, i, _, _ in c["t"] if i in data.enriched}
    return {"cities": cities, "titles": titles, "kinds": KINDS}


BODY = """
<div class="card" id="chartCard">
  <div class="ctl">
    <label>Nature <select id="kind"></select></label>
    <label>Tri <select id="sort"><option value="y">année du changement</option><option value="n">nombre de textes</option><option value="o">ordre alphabétique</option></select></label>
    <span class="muted" id="count"></span>
  </div>
  <p class="legend"><span class="sw o"></span>texte employant l'ancien nom <span class="sw n"></span>texte employant le nouveau nom <span class="sw c"></span>année du changement (connaissance historique, hors textes). Cliquez une ligne pour lire les textes.</p>
  <svg id="chart" width="100%"></svg>
</div>
<div class="split">
  <div class="card" id="detail"><p class="muted">Cliquez une ville dans la frise.</p></div>
  <div class="card"><svg id="map" width="100%"></svg></div>
</div>
<p class="muted note">La liste est curée à la main : les « noms historiques » de l'enrichissement mélangent de vrais anciens noms avec des aéroports (Orly, Roissy), des abréviations (CDG, Rio) et des variantes d'orthographe (Francfort, Fort de France), écartés ici. Les emplois sont relevés dans le texte brut des éphémérides ; l'année du changement vient de l'histoire, pas des textes. Les textes postérieurs au changement qui emploient encore l'ancien nom sont souvent des rétrospectives.</p>
<style>
.ctl { display:flex; flex-wrap:wrap; gap:18px; align-items:center; }
.ctl select { padding:5px 8px; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--ink); font:inherit; }
.muted { color:var(--muted); font-size:13px; }
.legend { color:var(--muted); font-size:13px; margin:8px 0; }
.sw { display:inline-block; width:10px; height:10px; border-radius:50%; margin:0 5px 0 12px; vertical-align:middle; }
.sw.o { background:#8a8f98; } .sw.n { background:var(--accent); } .sw.c { background:var(--accent2); border-radius:0; width:3px; height:12px; }
.split { display:grid; grid-template-columns:minmax(300px,1fr) minmax(300px,1fr); gap:14px; margin-top:14px; align-items:start; }
#detail h2 { margin:0 0 2px; font-size:20px; }
#detail ul { list-style:none; margin:10px 0 0; padding:0; max-height:520px; overflow:auto; }
#detail li { padding:6px 0; border-bottom:1px solid var(--line); font-size:13px; }
#detail li b { display:inline-block; width:84px; color:var(--muted); font-weight:500; }
#detail li q { display:block; margin-left:84px; color:var(--muted); quotes:none; }
.tag { font-size:11px; padding:0 6px; border:1px solid var(--line); border-radius:8px; }
.row { cursor:pointer; } .row:hover rect.bg, .row.sel rect.bg { fill:var(--bg); }
.row text { fill:var(--ink); font-size:12px; } .row text.dim { fill:var(--muted); }
.od { fill:#8a8f98; fill-opacity:.75; } .nd { fill:var(--accent); fill-opacity:.8; } .cy { stroke:var(--accent2); stroke-width:2.5; }
.axis text { fill:var(--muted); font-size:11px; } .axis line, .axis path { stroke:var(--line); }
.land { fill:var(--line); } .sphere { fill:var(--card); stroke:var(--line); }
.pt { fill:var(--accent); fill-opacity:.55; stroke:var(--accent); cursor:pointer; } .pt.sel { fill:var(--accent2); stroke:var(--accent2); fill-opacity:.9; }
.note { margin-top:14px; max-width:90ch; }
@media (max-width:800px) { .split { grid-template-columns:1fr; } }
</style>
"""

SCRIPT = r"""
const D = __DATA__;
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const $ = id => document.getElementById(id);
D.cities.forEach(c => { c.nt = new Set(c.t.map(x => x[1])).size; });
let selected = null;

$("kind").innerHTML = '<option value="">toutes</option>' + Object.entries(D.kinds).map(([k, v]) => `<option value="${k}">${v}</option>`).join("");

// Carte
const MW = 600, MH = 330;
const msvg = d3.select("#map").attr("viewBox", `0 0 ${MW} ${MH}`);
const proj = d3.geoEqualEarth().fitExtent([[6, 6], [MW - 6, MH - 6]], { type: "Sphere" });
const mpath = d3.geoPath(proj);
msvg.append("path").attr("class", "sphere").attr("d", mpath({ type: "Sphere" }));
const gLand = msvg.append("g"), gPts = msvg.append("g");
fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/land-110m.json").then(r => r.json()).then(topo => {
  const [kx, ky] = topo.transform.scale, [tx, ty] = topo.transform.translate;
  const decoded = topo.arcs.map(a => { let x = 0, y = 0; return a.map(([dx, dy]) => [(x += dx) * kx + tx, (y += dy) * ky + ty]); });
  const ring = idx => idx.flatMap(i => i >= 0 ? decoded[i] : decoded[~i].slice().reverse());
  const polys = [];
  for (const g of topo.objects.land.geometries) {
    if (g.type === "Polygon") polys.push(g.arcs.map(ring));
    else if (g.type === "MultiPolygon") g.arcs.forEach(p => polys.push(p.map(ring)));
  }
  gLand.append("path").attr("class", "land").attr("d", mpath({ type: "MultiPolygon", coordinates: polys }));
}).catch(() => {});

// Frise
const ROW = 22, M = { l: 300, r: 20, t: 24, b: 8 }, CW = 1000;
const x = d3.scaleLinear().domain([1910, 2024]).range([M.l, CW - M.r]);
const chart = d3.select("#chart");

function list() {
  const kind = $("kind").value, by = $("sort").value;
  const rows = D.cities.filter(c => !kind || c.k === kind);
  if (by === "n") rows.sort((a, b) => b.nt - a.nt);
  else if (by === "o") rows.sort((a, b) => a.o.localeCompare(b.o, "fr"));
  return rows;
}

function render() {
  const rows = list();
  $("count").textContent = rows.length + " ville" + (rows.length > 1 ? "s" : "") + " · " + rows.reduce((s, c) => s + c.nt, 0) + " mentions de textes";
  const H = M.t + rows.length * ROW + M.b;
  chart.attr("viewBox", `0 0 ${CW} ${H}`).attr("height", null);
  chart.selectAll("*").remove();
  chart.append("g").attr("class", "axis").attr("transform", `translate(0,${M.t - 6})`)
    .call(d3.axisTop(x).tickFormat(d3.format("d")).ticks(12).tickSize(-(H - M.t + 6)));
  const g = chart.selectAll("g.row").data(rows).join("g").attr("class", d => "row" + (d === selected ? " sel" : ""))
    .attr("transform", (d, i) => `translate(0,${M.t + i * ROW})`).on("click", (e, d) => select(d));
  g.append("rect").attr("class", "bg").attr("x", 0).attr("y", 0).attr("width", CW).attr("height", ROW).attr("fill", "transparent");
  g.append("text").attr("x", 6).attr("y", 15).text(d => `${d.o} → ${d.n}`);
  g.append("text").attr("class", "dim").attr("x", M.l - 8).attr("y", 15).attr("text-anchor", "end").text(d => d.y ? (d.ap ? "~" : "") + d.y : "date ?");
  g.filter(d => d.y).append("line").attr("class", "cy").attr("x1", d => x(d.y)).attr("x2", d => x(d.y)).attr("y1", 2).attr("y2", ROW - 2);
  g.each(function (d) {
    d3.select(this).selectAll("circle").data(d.t).join("circle").attr("class", t => t[2] === "o" ? "od" : "nd")
      .attr("cx", t => x(+t[0].slice(0, 4) + (+t[0].slice(5, 7) - 1) / 12)).attr("cy", t => t[2] === "o" ? 8 : 15).attr("r", 2.6)
      .append("title").text(t => `${t[0]} · ${t[2] === "o" ? d.o : d.n} · ${D.titles[t[1]] || ""}`);
  });
  gPts.selectAll("circle").data(rows.filter(c => c.la !== null), d => d.o).join("circle")
    .attr("class", d => "pt" + (d === selected ? " sel" : "")).attr("cx", d => proj([d.lo, d.la])[0]).attr("cy", d => proj([d.lo, d.la])[1])
    .attr("r", d => d === selected ? 7 : 4).on("click", (e, d) => select(d))
    .append("title").text(d => `${d.o} → ${d.n}`);
}

function select(c) {
  selected = c;
  const olds = c.t.filter(t => t[2] === "o"), news = c.t.filter(t => t[2] === "n");
  const late = c.y ? olds.filter(t => +t[0].slice(0, 4) > c.y).length : null;
  const bits = [
    `ancien nom dans ${olds.length} texte(s)` + (olds.length ? ` (${c.oa}–${c.oz})` : ""),
    `nouveau nom dans ${news.length} texte(s)` + (news.length ? ` (dès ${c.na})` : ""),
  ];
  if (late) bits.push(`${late} texte(s) emploient encore l'ancien nom après ${c.y}`);
  const when = c.y ? `${c.ap ? "vers " : "en "}${c.y}` : "date incertaine ou progressive";
  $("detail").innerHTML = `<h2>${esc(c.o)} → ${esc(c.n)}</h2>
    <div class="muted">${esc(c.c)} · <span class="tag">${esc(D.kinds[c.k])}</span> · changement ${when}<br>${bits.join(" · ")}${c.note ? "<br>" + esc(c.note) : ""}</div>
    <ul>${c.t.map(t => `<li><b>${t[0]}</b>${esc(D.titles[t[1]] || "")} <span class="tag">${t[2] === "o" ? "ancien nom" : "nouveau nom"}</span><q>${esc(t[3])}</q></li>`).join("")}</ul>`;
  render();
}

$("kind").onchange = render; $("sort").onchange = render;
render();
select(D.cities.find(c => c.o === "Saïgon") || D.cities[0]);
"""


def build(data):
    payload = prepare(data)
    script = SCRIPT.replace("__DATA__", embed(payload))
    n = len(payload["cities"])
    mentions = sum(len({t[1] for t in c["t"]}) for c in payload["cities"])
    lead = (f"{n} villes aux noms changés, relevées dans {mentions} mentions de textes. Pour chacune : la date du changement, "
            "et les textes qui emploient l'ancien nom, le nouveau, ou encore l'ancien bien après le changement.")
    head = '<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>'
    return page_shell(META["title"], lead, BODY, head_extra=head, script=script)
