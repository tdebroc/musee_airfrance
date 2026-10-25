"""Le graphe des personnes : réseau des personnes co-citées, taille = nombre de textes, couleur = kind."""
from collections import Counter
from itertools import combinations

from .common import embed, page_shell
from .personnages_lieux import KINDS, prepare_people

META = {
    "slug": "graphe-personnes",
    "title": "Le graphe des personnes",
    "description": "Qui apparaît avec qui : le réseau des personnes citées dans un même texte, de Mermoz aux dirigeants d'aujourd'hui.",
    "order": 10,
}

MAX_PER_TEXT = 12   # au-delà, le texte est une liste (palmarès, équipage…) et non une vraie co-citation
MIN_TEXTS = 2       # une personne citée une seule fois est écartée du graphe


def prepare(data):
    people = prepare_people(data)   # mêmes noms regroupés que la page personnages-lieux
    in_text = {}
    for i, p in enumerate(people):
        for _, tid in p["t"]:
            in_text.setdefault(tid, set()).add(i)

    pairs, pair_texts = Counter(), {}
    for tid, who in in_text.items():
        who = [i for i in who if len(people[i]["t"]) >= MIN_TEXTS]
        if not 2 <= len(who) <= MAX_PER_TEXT:
            continue
        for a, b in combinations(sorted(who), 2):
            pairs[(a, b)] += 1
            pair_texts.setdefault((a, b), []).append(tid)

    used = sorted({x for e in pairs for x in e}, key=lambda i: (-len(people[i]["t"]), people[i]["n"]))
    index = {old: new for new, old in enumerate(used)}
    nodes = [{"n": people[i]["n"], "k": people[i]["k"], "r": people[i]["r"][:2], "c": len(people[i]["t"]),
              "a": people[i]["a"][:4], "z": people[i]["z"][:4]} for i in used]
    links = [[index[a], index[b], w, sorted(pair_texts[(a, b)])] for (a, b), w in pairs.items()]
    ids = {tid for l in links for tid in l[3]}
    titles = {str(i): [data.enriched[i]["date"], data.enriched[i]["title"]] for i in ids}
    return {"nodes": nodes, "links": links, "titles": titles, "kinds": KINDS,
            "total": len(people), "maxPerText": MAX_PER_TEXT}


BODY = """
<div class="card ctl">
  <label>Recherche <input id="q" type="search" placeholder="Spinetta, Mermoz…"></label>
  <label>Type <select id="kind"></select></label>
  <label>Textes min. <input id="minK" type="range" min="2" max="30" value="4"><b id="minKv">4</b></label>
  <label>Co-citations min. <input id="minW" type="range" min="1" max="8" value="1"><b id="minWv">1</b></label>
  <span id="count" class="muted"></span>
</div>
<div class="split">
  <div class="card"><svg id="g" style="width:100%;height:auto;display:block"></svg><div id="legend" class="muted"></div></div>
  <div class="card" id="detail"><p class="muted">Cliquez sur une personne : ses liens apparaissent, et les textes qui les justifient. Glissez un nœud pour le déplacer, molette pour zoomer.</p></div>
</div>
<style>
.ctl { display:flex; flex-wrap:wrap; gap:18px; align-items:center; }
.ctl input[type=search], .ctl select { padding:5px 8px; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--ink); font:inherit; }
.muted { color:var(--muted); font-size:13px; }
.split { display:grid; grid-template-columns:minmax(0,2fr) minmax(280px,1fr); gap:14px; margin-top:14px; align-items:start; }
.link { stroke:var(--muted); stroke-opacity:.35; } .link.hi { stroke:var(--accent2); stroke-opacity:.9; }
.node { stroke:var(--card); stroke-width:1.2; cursor:pointer; } .node.dim { opacity:.15; } .node.sel { stroke:var(--accent2); stroke-width:3; }
.lab { font-size:11px; fill:var(--ink); pointer-events:none; paint-order:stroke; stroke:var(--card); stroke-width:3px; }
#legend span { display:inline-block; margin:6px 14px 0 0; } #legend i { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:5px; }
#detail h2 { margin:0 0 2px; font-size:19px; } #detail ul { list-style:none; margin:8px 0 0; padding:0; max-height:420px; overflow:auto; }
#detail li { padding:4px 0; border-bottom:1px solid var(--line); font-size:13px; }
#detail li a { cursor:pointer; text-decoration:underline; } #detail li small { color:var(--muted); display:block; }
@media (max-width:900px) { .split { grid-template-columns:1fr; } }
</style>
"""

SCRIPT = r"""
const D = __DATA__;
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const plain = s => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const $ = id => document.getElementById(id);
const COLORS = { dirigeant: "#2a6fdb", navigant: "#e08a00", personnalite: "#9b4fd0", politique: "#d6336c", personnel: "#2f9e6b", autre: "#8a94a6" };
const col = k => COLORS[k] || COLORS.autre;
D.nodes.forEach((n, i) => { n.i = i; n.s = plain(n.n + " " + n.r.join(" ")); });
const links = D.links.map(([s, t, w, ids]) => ({ s, t, w, ids }));

$("kind").innerHTML = '<option value="">tous</option>' + Object.entries(D.kinds).map(([k, v]) => `<option value="${k}">${v}</option>`).join("");
$("legend").innerHTML = Object.entries(D.kinds).map(([k, v]) => `<span><i style="background:${col(k)}"></i>${v}</span>`).join("") +
  `<span>Taille = nombre de textes · épaisseur = nombre de textes communs · textes de plus de ${D.maxPerText} personnes ignorés</span>`;

const W = 1000, H = 700;
const svg = d3.select("#g").attr("viewBox", `0 0 ${W} ${H}`);
const root = svg.append("g");
svg.call(d3.zoom().scaleExtent([0.3, 6]).on("zoom", e => root.attr("transform", e.transform)));
const gL = root.append("g"), gN = root.append("g"), gT = root.append("g");
const rad = d3.scaleSqrt().domain([2, 120]).range([4, 26]).clamp(true);
let sim = null, selected = null, cur = { nodes: [], links: [] };

function filtered() {
  const minK = +$("minK").value, minW = +$("minW").value, kind = $("kind").value;
  const ok = n => n.c >= minK && (!kind || n.k === kind);
  const ls = links.filter(l => l.w >= minW && ok(D.nodes[l.s]) && ok(D.nodes[l.t]));
  const keep = new Set(); ls.forEach(l => { keep.add(l.s); keep.add(l.t); });
  const nodes = D.nodes.filter(n => keep.has(n.i)).map(n => Object.assign({}, n));
  const byI = new Map(nodes.map(n => [n.i, n]));
  return { nodes, links: ls.map(l => ({ source: byI.get(l.s), target: byI.get(l.t), w: l.w, ids: l.ids })) };
}

function neighbors(n) {
  return cur.links.filter(l => l.source === n || l.target === n).map(l => ({ o: l.source === n ? l.target : l.source, w: l.w, ids: l.ids }))
    .sort((a, b) => b.w - a.w || b.o.c - a.o.c);
}

function draw() {
  const q = plain($("q").value.trim());
  $("minKv").textContent = $("minK").value; $("minWv").textContent = $("minW").value;
  cur = filtered();
  $("count").textContent = `${cur.nodes.length} personnes · ${cur.links.length} liens (sur ${D.total} personnes repérées)`;
  if (sim) sim.stop();
  selected = selected && cur.nodes.find(n => n.i === selected.i) || null;
  const lk = gL.selectAll("line").data(cur.links).join("line").attr("class", "link").attr("stroke-width", d => 0.8 + Math.sqrt(d.w) * 0.9);
  const nd = gN.selectAll("circle").data(cur.nodes, d => d.i).join("circle").attr("class", "node")
    .attr("r", d => rad(d.c)).attr("fill", d => col(d.k))
    .on("click", (e, d) => { selected = d; show(); style(); })
    .call(d3.drag().on("start", (e, d) => { if (!e.active) sim.alphaTarget(.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; }).on("end", (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = d.fy = null; }));
  nd.selectAll("title").data(d => [d]).join("title").text(d => `${d.n} · ${d.c} textes`);
  const labelled = new Set(cur.nodes.slice().sort((a, b) => b.c - a.c).slice(0, 25));
  const tx = gT.selectAll("text").data(cur.nodes, d => d.i).join("text").attr("class", "lab").attr("text-anchor", "middle").text(d => d.n);
  function style() {
    const nb = selected ? new Set([selected, ...neighbors(selected).map(x => x.o)]) : null;
    const hit = q ? new Set(cur.nodes.filter(n => n.s.includes(q))) : null;
    nd.attr("class", d => "node" + (d === selected ? " sel" : "") + ((nb && !nb.has(d)) || (hit && !hit.has(d)) ? " dim" : ""));
    lk.attr("class", d => "link" + (selected && (d.source === selected || d.target === selected) ? " hi" : ""));
    tx.style("display", d => (hit ? hit.has(d) : nb ? nb.has(d) : labelled.has(d)) ? null : "none");
  }
  sim = d3.forceSimulation(cur.nodes)
    .force("link", d3.forceLink(cur.links).distance(d => 60 / Math.sqrt(d.w)).strength(0.5))
    .force("charge", d3.forceManyBody().strength(-70))
    .force("collide", d3.forceCollide(d => rad(d.c) + 2))
    .force("x", d3.forceX(W / 2).strength(0.06)).force("y", d3.forceY(H / 2).strength(0.06))
    .on("tick", () => {
      lk.attr("x1", d => d.source.x).attr("y1", d => d.source.y).attr("x2", d => d.target.x).attr("y2", d => d.target.y);
      nd.attr("cx", d => d.x).attr("cy", d => d.y);
      tx.attr("x", d => d.x).attr("y", d => d.y - rad(d.c) - 3);
    });
  draw.style = style; style();
}

function show() {
  const n = selected, el = $("detail");
  if (!n) { return; }
  const nb = neighbors(n);
  const title = id => D.titles[id] || ["", ""];
  el.innerHTML = `<h2>${esc(n.n)}</h2><div class="muted">${esc(D.kinds[n.k] || n.k)}${n.r.length ? " · " + n.r.map(esc).join(" ; ") : ""}<br>${n.c} textes · de ${n.a} à ${n.z}</div>` +
    `<h3 style="font-size:14px;margin:12px 0 0">${nb.length} personne(s) co-citée(s)</h3><ul>` +
    nb.map(x => `<li><a data-i="${x.o.i}">${esc(x.o.n)}</a> <span class="muted">· ${x.w} texte(s) commun(s)</span>` +
      x.ids.slice(0, 3).map(id => `<small>${title(id)[0]} — ${esc(title(id)[1])}</small>`).join("") + "</li>").join("") + "</ul>";
  el.querySelectorAll("a[data-i]").forEach(a => a.onclick = () => { selected = cur.nodes.find(m => m.i === +a.dataset.i); show(); draw.style(); });
}

["minK", "minW", "kind"].forEach(id => $(id).addEventListener("input", draw));
$("q").addEventListener("input", () => draw.style());
draw();
"""


def build(data):
    payload = prepare(data)
    n, e = len(payload["nodes"]), len(payload["links"])
    lead = (f"{n} personnes (citées dans au moins {MIN_TEXTS} textes) reliées par {e} co-citations : deux personnes sont liées "
            f"quand un même texte les nomme. Les textes citant plus de {MAX_PER_TEXT} personnes sont ignorés. "
            "Une co-citation montre qu'on parle des deux ensemble, pas qu'elles se sont rencontrées.")
    head = '<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>'
    return page_shell(META["title"], lead, BODY, head_extra=head, script=SCRIPT.replace("__DATA__", embed(payload)))
