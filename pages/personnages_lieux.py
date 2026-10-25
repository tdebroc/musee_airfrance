"""Personnages et lieux : index des personnes (rôle, période, textes) et des lieux (carte + liste, noms historiques)."""
import re
import unicodedata
from collections import Counter, defaultdict

from .common import embed, page_shell

META = {
    "slug": "personnages-lieux",
    "title": "Personnages et lieux",
    "description": "Qui et où : l'index des personnes citées (dirigeants, navigants, politiques…) et des lieux, avec carte, périodes et noms historiques.",
    "order": 3,
}

CIVILITY = re.compile(r"^(?:m\.|mm\.|mme|mlle|monsieur|madame|mademoiselle|dr|pr)\s+", re.I)
KINDS = {"dirigeant": "dirigeant", "navigant": "navigant", "personnalite": "personnalité", "politique": "politique",
         "personnel": "personnel", "autre": "autre"}


def plain(s):
    s = "".join(ch for ch in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(ch) != "Mn")
    return re.sub(r"[\s\-–’']+", " ", s).strip()


def clean_name(name):
    return CIVILITY.sub("", name.strip()).strip()


def prepare_people(data):
    mentions = []   # (clé, nom propre, rôle, kind, date, id)
    for rec in data.records():
        for p in rec["people"]:
            name = clean_name(p["name"])
            if len(plain(name)) < 3:
                continue
            mentions.append((plain(name), name, (p.get("role") or "").strip(), p.get("kind") or "autre", rec["date"], rec["id"]))

    # Les noms réduits à un patronyme (« Lesieux ») rejoignent le nom complet s'il est unique.
    by_last = defaultdict(set)
    for key, *_ in mentions:
        if " " in key:
            by_last[key.split()[-1]].add(key)
    merged = {}
    for key, *_ in mentions:
        if " " not in key and len(by_last.get(key, ())) == 1:
            merged[key] = next(iter(by_last[key]))

    groups = defaultdict(list)
    for m in mentions:
        groups[merged.get(m[0], m[0])].append(m)

    people = []
    for key, ms in groups.items():
        dates = {m[5]: m[4] for m in ms}
        ids = sorted(dates, key=lambda i: (dates[i], i))
        names = Counter(m[1] for m in ms if plain(m[1]) == key) or Counter(m[1] for m in ms)
        kinds = Counter(m[3] for m in ms if m[3] != "autre") or Counter(m[3] for m in ms)
        roles = Counter(m[2] for m in ms if m[2])
        people.append({
            "n": names.most_common(1)[0][0],
            "k": kinds.most_common(1)[0][0],
            "r": [r for r, _ in roles.most_common(3)],
            "a": min(dates.values()), "z": max(dates.values()),
            "t": [[dates[i], i] for i in ids],
        })
    people.sort(key=lambda p: (-len(p["t"]), p["n"]))
    return people


def prepare_places(data):
    groups = defaultdict(lambda: {"names": Counter(), "coords": Counter(), "hist": Counter(), "ids": {}, "country": Counter()})
    for rec in data.records():
        for p in rec["places"]:
            if p.get("lat") is None or p.get("lon") is None or not p.get("name"):
                continue
            g = groups[(plain(p["name"]), plain(p.get("country") or ""))]
            g["names"][p["name"]] += 1
            g["coords"][(round(p["lat"], 1), round(p["lon"], 1))] += 1
            g["country"][p.get("country") or ""] += 1
            g["ids"][rec["id"]] = rec["date"]
            h = (p.get("historical_name") or "").strip()
            if h and plain(h) != plain(p["name"]):
                g["hist"][h] += 1
    places = []
    for (key, _), g in groups.items():
        lat, lon = g["coords"].most_common(1)[0][0]
        ids = sorted(g["ids"], key=lambda i: (g["ids"][i], i))
        places.append({
            "n": g["names"].most_common(1)[0][0], "c": g["country"].most_common(1)[0][0],
            "la": lat, "lo": lon,
            "h": [h for h, _ in g["hist"].most_common(4)],
            "a": min(g["ids"].values()), "z": max(g["ids"].values()),
            "t": [[g["ids"][i], i] for i in ids],
        })
    places.sort(key=lambda p: (-len(p["t"]), p["n"]))
    return places


def prepare(data):
    people, places = prepare_people(data), prepare_places(data)
    used = {i for p in people + places for _, i in p["t"]}
    titles = {str(i): data.enriched[i]["title"] for i in used}
    return {"people": people, "places": places, "titles": titles, "kinds": KINDS}


BODY = """
<div class="tabs"><button id="tabP" class="on">Personnes</button><button id="tabL">Lieux</button></div>
<div class="card ctl">
  <label>Recherche <input id="q" type="search" placeholder="Mermoz, Dakar…"></label>
  <label id="kindWrap">Type <select id="kind"></select></label>
  <label>Textes min. <input id="minK" type="range" min="1" max="30" value="2"><b id="minKv">2</b></label>
  <span id="count" class="muted"></span>
</div>
<div class="split">
  <div class="card" id="mapCard" style="display:none"><svg id="map" style="width:100%;height:auto"></svg></div>
  <div class="card list"><ul id="list"></ul><button id="more" style="display:none">Afficher plus</button></div>
  <div class="card" id="detail"><p class="muted">Cliquez sur un nom pour lire ses textes.</p></div>
</div>
<style>
.tabs { display:flex; gap:8px; margin-bottom:12px; }
.tabs button, #more { padding:7px 16px; border:1px solid var(--line); background:var(--card); color:var(--ink); border-radius:8px; cursor:pointer; font:inherit; }
.tabs button.on { background:var(--accent); color:var(--card); border-color:var(--accent); }
.ctl { display:flex; flex-wrap:wrap; gap:18px; align-items:center; }
.ctl input[type=search], .ctl select { padding:5px 8px; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--ink); font:inherit; }
.muted { color:var(--muted); font-size:13px; }
.split { display:grid; grid-template-columns:minmax(300px,1fr) minmax(300px,1fr); gap:14px; margin-top:14px; align-items:start; }
#mapCard { grid-column:1 / -1; }
.list ul { list-style:none; margin:0; padding:0; max-height:560px; overflow:auto; }
.list li { padding:6px 4px; border-bottom:1px solid var(--line); cursor:pointer; display:flex; justify-content:space-between; gap:10px; }
.list li:hover, .list li.sel { background:var(--bg); }
.list li small { color:var(--muted); display:block; }
.list li .num { color:var(--muted); font-variant-numeric:tabular-nums; white-space:nowrap; }
#detail ul { list-style:none; margin:8px 0 0; padding:0; max-height:480px; overflow:auto; }
#detail li { padding:3px 0; border-bottom:1px solid var(--line); font-size:13px; }
#detail li b { display:inline-block; width:84px; color:var(--muted); font-weight:500; }
#detail h2 { margin:0 0 2px; font-size:19px; }
.land { fill:var(--line); } .sphere { fill:var(--card); stroke:var(--line); } .dot { fill:var(--accent); fill-opacity:.5; stroke:var(--accent); cursor:pointer; }
.dot.sel { fill:var(--accent2); stroke:var(--accent2); fill-opacity:.8; }
@media (max-width:800px) { .split { grid-template-columns:1fr; } }
</style>
"""

SCRIPT = r"""
const D = __DATA__;
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const plain = s => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
D.people.forEach(p => p.s = plain(p.n + " " + p.r.join(" ")));
D.places.forEach(p => p.s = plain(p.n + " " + p.h.join(" ") + " " + p.c));
let mode = "P", shown = 80, selected = null;
const $ = id => document.getElementById(id);

const kindSel = $("kind");
kindSel.innerHTML = '<option value="">tous</option>' + Object.entries(D.kinds).map(([k, v]) => `<option value="${k}">${v}</option>`).join("");

// Carte
const W = 1000, H = 480;
const svg = d3.select("#map").attr("viewBox", `0 0 ${W} ${H}`);
const proj = d3.geoEqualEarth().fitExtent([[8, 8], [W - 8, H - 8]], { type: "Sphere" });
const path = d3.geoPath(proj);
svg.append("path").attr("class", "sphere").attr("d", path({ type: "Sphere" }));
const gLand = svg.append("g"), gDots = svg.append("g");
fetch("https://cdn.jsdelivr.net/npm/world-atlas@2/land-110m.json").then(r => r.json()).then(topo => {
  const [kx, ky] = topo.transform.scale, [tx, ty] = topo.transform.translate;
  const decoded = topo.arcs.map(a => { let x = 0, y = 0; return a.map(([dx, dy]) => [(x += dx) * kx + tx, (y += dy) * ky + ty]); });
  const ring = idx => idx.flatMap(i => i >= 0 ? decoded[i] : decoded[~i].slice().reverse());
  const polys = [];
  for (const g of topo.objects.land.geometries) {
    if (g.type === "Polygon") polys.push(g.arcs.map(ring));
    else if (g.type === "MultiPolygon") g.arcs.forEach(p => polys.push(p.map(ring)));
  }
  gLand.append("path").attr("class", "land").attr("d", path({ type: "MultiPolygon", coordinates: polys }));
}).catch(() => {});
const rad = d3.scaleSqrt().domain([1, 1800]).range([2, 16]);

function items() {
  const q = plain($("q").value.trim()), minK = +$("minK").value, kind = kindSel.value;
  const src = mode === "P" ? D.people : D.places;
  return src.filter(p => p.t.length >= minK && (!q || p.s.includes(q)) && (mode === "L" || !kind || p.k === kind));
}

function render() {
  const all = items();
  $("minKv").textContent = $("minK").value;
  $("count").textContent = all.length + (mode === "P" ? " personne" : " lieu") + (all.length > 1 ? "s" : "");
  $("kindWrap").style.display = mode === "P" ? "" : "none";
  $("mapCard").style.display = mode === "L" ? "" : "none";
  const rows = all.slice(0, shown);
  $("list").innerHTML = rows.map((p, i) => {
    const sub = mode === "P" ? (D.kinds[p.k] || p.k) + (p.r[0] ? " · " + p.r[0] : "")
                             : (p.c || "") + (p.h.length ? " · aussi : " + p.h.slice(0, 2).join(", ") : "");
    return `<li data-i="${i}" class="${p === selected ? "sel" : ""}"><span><b>${esc(p.n)}</b><small>${esc(sub)}</small></span><span class="num">${p.t.length} · ${p.a.slice(0, 4)}–${p.z.slice(0, 4)}</span></li>`;
  }).join("") || '<li class="muted">Aucun résultat.</li>';
  $("more").style.display = all.length > shown ? "" : "none";
  $("more").textContent = `Afficher plus (${all.length - shown} restants)`;
  $("list").querySelectorAll("li[data-i]").forEach(li => li.addEventListener("click", () => select(rows[+li.dataset.i])));
  if (mode === "L") {
    gDots.selectAll("circle").data(all, d => d.n + d.c + d.la + d.lo).join("circle").attr("class", d => "dot" + (d === selected ? " sel" : ""))
      .attr("cx", d => proj([d.lo, d.la])[0]).attr("cy", d => proj([d.lo, d.la])[1]).attr("r", d => rad(d.t.length))
      .on("click", (e, d) => select(d)).selectAll("title").data(d => [d]).join("title").text(d => `${d.n} · ${d.t.length} texte(s)`);
  }
}

function select(p) {
  selected = p;
  const el = $("detail");
  const meta = mode === "P"
    ? `${esc(D.kinds[p.k] || p.k)}${p.r.length ? " · " + p.r.map(esc).join(" ; ") : ""}`
    : `${esc(p.c || "")}${p.h.length ? " · variantes employées dans les textes (aéroports, anciens noms…) : " + p.h.map(esc).join(", ") : ""}`;
  el.innerHTML = `<h2>${esc(p.n)}</h2><div class="muted">${meta}<br>${p.t.length} texte(s) · cité de ${p.a.slice(0, 4)} à ${p.z.slice(0, 4)}</div><ul>` +
    p.t.map(([d, id]) => `<li><b>${d}</b>${esc(D.titles[id] || "")}</li>`).join("") + "</ul>";
  render();
}

function setMode(m) {
  mode = m; shown = 80; selected = null;
  $("tabP").classList.toggle("on", m === "P"); $("tabL").classList.toggle("on", m === "L");
  $("q").placeholder = m === "P" ? "Mermoz, Spinetta…" : "Saïgon, Dakar…";
  $("minK").value = m === "P" ? 2 : 3;
  $("detail").innerHTML = '<p class="muted">Cliquez sur un nom pour lire ses textes.</p>';
  render();
}
$("tabP").onclick = () => setMode("P"); $("tabL").onclick = () => setMode("L");
$("more").onclick = () => { shown += 120; render(); };
["q", "minK", "kind"].forEach(id => $(id).addEventListener("input", () => { shown = 80; render(); }));
setMode("P");
"""


def build(data):
    payload = prepare(data)
    script = SCRIPT.replace("__DATA__", embed(payload))
    lead = (f"{len(payload['people'])} personnes et {len(payload['places'])} lieux repérés dans les textes. "
            "Les noms sont regroupés (« M. Lesieux » = « Louis Lesieux ») ; la période est celle des textes qui les citent, "
            "pas forcément celle de leur vie ou de leur rôle.")
    head = '<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>'
    return page_shell(META["title"], lead, BODY, head_extra=head, script=script)
