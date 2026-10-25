"""« Demande au musée » : recherche plein texte côté navigateur dans titres, résumés, personnes, lieux, compagnies, avions."""
import re

from .common import embed, page_shell

META = {
    "slug": "demande-musee",
    "title": "Demande au musée",
    "description": "Une question, un nom, un lieu, un avion : recherche instantanée dans les 10 000 éphémérides, tolérante aux accents, sans serveur ni IA.",
    "order": 15,
}

TITLE = {"accident_incident": "Accident", "commercial_produit": "Commercial", "communication_culture": "Communication",
         "direction_nomination": "Direction", "entreprise_capital": "Entreprise", "environnement": "Environnement",
         "fermeture_ligne": "Fermeture de ligne", "flotte": "Flotte", "greve_social": "Grève / social",
         "guerre_crise": "Guerre / crise", "infrastructure_aeroport": "Aéroport", "ouverture_ligne": "Ouverture de ligne",
         "premier_vol": "Premier vol", "record": "Record", "resultats_trafic": "Résultats / trafic",
         "securite_surete": "Sécurité / sûreté", "service_bord_equipage": "Service à bord", "technique_maintenance": "Technique",
         "autre": "Autre"}


def names(items, key="name"):
    seen, out = set(), []
    for item in items or []:
        value = (item.get(key) if isinstance(item, dict) else item) or ""
        value = re.sub(r"\s+", " ", value).strip()
        if value and value.lower() not in seen:
            seen.add(value.lower())
            out.append(value)
    return out


def prepare(data):
    """Une ligne = [id, date, titre, résumé, intérêt, [catégories], personnes, lieux, compagnies, avions]."""
    cats = sorted(TITLE)
    rows = []
    for rec in data.records():
        rows.append([
            rec["id"], rec["date"], rec["title"], rec["summary"], rec["interest"],
            [cats.index(c) for c in rec["categories"] if c in TITLE],
            names(rec["people"]), names(rec["places"]), names(rec["companies"], None),
            names(rec["aircraft"], "model"),
        ])
    return {"rows": rows, "cats": [[c, TITLE[c]] for c in cats]}


BODY = """
<style>
.q { display:flex; gap:10px; flex-wrap:wrap; }
.q input[type=search] { flex:1 1 380px; font:inherit; font-size:17px; padding:10px 14px; border:1px solid var(--line); border-radius:8px; background:var(--card); color:var(--ink); }
.filters { display:flex; gap:14px; flex-wrap:wrap; align-items:center; margin:12px 0; color:var(--muted); font-size:13.5px; }
.filters select, .filters input[type=number] { font:inherit; padding:4px 6px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--ink); }
.filters input[type=number] { width:76px; }
.ex { font-size:13.5px; color:var(--muted); margin:4px 0 12px; }
.ex a { cursor:pointer; margin-right:12px; }
#count { margin:6px 0 10px; color:var(--muted); font-size:14px; }
.hit { padding:12px 2px; border-bottom:1px solid var(--line); }
.hit h3 { margin:0 0 2px; font-size:16px; } .hit h3 .y { color:var(--accent2); margin-right:8px; font-variant-numeric:tabular-nums; }
.hit p { margin:2px 0 6px; } .hit .meta { font-size:12.5px; color:var(--muted); }
.tag { display:inline-block; border:1px solid var(--line); border-radius:10px; padding:0 8px; margin:0 4px 2px 0; font-size:12px; cursor:pointer; }
.tag:hover { border-color:var(--accent); }
.stars { color:var(--accent2); letter-spacing:1px; }
mark { background:rgba(255,200,0,.35); color:inherit; border-radius:2px; }
button.more { font:inherit; margin:16px 0; padding:7px 18px; border:0; border-radius:6px; background:var(--accent); color:var(--bg); cursor:pointer; font-weight:600; }
.note { color:var(--muted); font-size:12.5px; margin-top:14px; }
</style>
<div class="card">
  <div class="q"><input type="search" id="q" placeholder="Concorde, Mermoz, grève 1968, Saïgon, premier vol New York…" autofocus aria-label="Recherche"></div>
  <div class="ex" id="ex"></div>
  <div class="filters">
    <label>Catégorie <select id="cat"><option value="">toutes</option></select></label>
    <label>De <input type="number" id="y0" min="1900" max="2030" placeholder="1900"></label>
    <label>à <input type="number" id="y1" min="1900" max="2030" placeholder="2022"></label>
    <label>Intérêt ≥ <select id="mi"><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option></select></label>
    <label>Tri <select id="sort"><option value="rel">pertinence</option><option value="asc">date croissante</option><option value="desc">date décroissante</option></select></label>
  </div>
  <div id="count"></div>
  <div id="out"></div>
  <button class="more" id="more" hidden>Afficher la suite</button>
</div>
<p class="note">Recherche dans le titre, le résumé, les personnes, lieux, compagnies et avions cités de chaque éphéméride (le texte intégral n'est pas dans la page).
Tous les mots doivent être présents (début de mot accepté : « conc » trouve Concorde) ; accents et majuscules sont ignorés ; un nombre à 4 chiffres cherche aussi l'année.
Tout se passe dans votre navigateur : aucune requête, aucun modèle de langage.</p>
"""

SCRIPT = r"""
const D = __DATA__;
const $ = id => document.getElementById(id);
const ENT = { "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" };
const esc = s => String(s).replace(/[&<>"]/g, c => ENT[c]);
// normalisation caractère par caractère : la longueur est conservée, on peut donc surligner sur le texte d'origine
const norm = s => Array.from(String(s), c => (c.toLowerCase().normalize("NFD")[0] || c)).join("")
  .replace(/[’'`\-–—_/.,;:()«»"]/g, " ");
const PAGE = 30;
const STOP = new Set(["le","la","les","l","de","du","des","d","un","une","et","en","au","aux","a","qui","que","quand","quel","quelle","quels","quelles","est","sont","ce","cette","dans","sur","pour","par","il","y","a","se","s","qu","ou"]);

const rows = D.rows.map(r => ({
  id: r[0], date: r[1], year: +r[1].slice(0, 4), title: r[2], summary: r[3], interest: r[4], cats: r[5],
  people: r[6], places: r[7], companies: r[8], aircraft: r[9],
  nt: norm(r[2]), ns: norm(r[3]),
  nk: norm([...r[6], ...r[7], ...r[8], ...r[9]].join(" | ")),
}));
D.cats.forEach(([k, label], i) => { const o = document.createElement("option"); o.value = i; o.textContent = label; $("cat").appendChild(o); });

const examples = ["Concorde", "Mermoz", "grève 1968", "Saïgon", "Boeing 747 retrait", "Entebbe", "Tananarive", "nouvelle livrée"];
$("ex").innerHTML = "Essayer : " + examples.map(e => `<a data-q="${esc(e)}">${esc(e)}</a>`).join("");
$("ex").addEventListener("click", e => { const q = e.target.dataset && e.target.dataset.q; if (q) { $("q").value = q; run(); } });

// les mots d'un champ normalisé, pour le test « début de mot »
const hasWord = (field, t) => field.startsWith(t) || field.includes(" " + t);

let results = [], shown = 0, terms = [];

function parse(q) {
  const all = norm(q).split(/\s+/).filter(Boolean);
  const kept = all.filter(t => !STOP.has(t));
  return kept.length ? kept : all;
}

function score(r) {
  let total = 0;
  for (const t of terms) {
    let s = 0;
    if (hasWord(r.nt, t)) s += 6;
    if (hasWord(r.nk, t)) s += 5;
    if (hasWord(r.ns, t)) s += 2;
    if (/^\d{4}$/.test(t) && r.year === +t) s += 4;
    if (!s) return 0;
    total += s;
  }
  // bonus : phrase exacte dans le titre ou le résumé, et intérêt
  const phrase = terms.join(" ");
  if (terms.length > 1 && (r.nt.includes(phrase) || r.ns.includes(phrase))) total += 6;
  return total + r.interest * 0.5;
}

function run() {
  const q = $("q").value.trim();
  terms = parse(q);
  const cat = $("cat").value, y0 = +$("y0").value || 0, y1 = +$("y1").value || 9999, mi = +$("mi").value, sort = $("sort").value;
  const ok = r => r.interest >= mi && r.year >= y0 && r.year <= y1 && (cat === "" || r.cats.includes(+cat));
  if (!terms.length) {
    results = [];
    const any = rows.filter(ok);
    $("count").textContent = any.length ? `${any.length} éphémérides correspondent aux filtres — tapez un mot pour chercher.` : "Aucune éphéméride pour ces filtres.";
    if (cat !== "" || y0 || y1 !== 9999 || mi > 1) results = any.map(r => [r, r.interest]);
    else { $("out").innerHTML = ""; $("more").hidden = true; return; }
  } else {
    results = [];
    for (const r of rows) if (ok(r)) { const s = score(r); if (s > 0) results.push([r, s]); }
  }
  if (sort === "rel") results.sort((a, b) => b[1] - a[1] || b[0].interest - a[0].interest || a[0].date.localeCompare(b[0].date));
  else results.sort((a, b) => (sort === "asc" ? 1 : -1) * a[0].date.localeCompare(b[0].date) || a[0].id - b[0].id);
  if (terms.length) $("count").textContent = results.length ? `${results.length} résultat${results.length > 1 ? "s" : ""}` : "Aucun résultat. Essayez moins de mots, ou un début de mot.";
  shown = 0; $("out").innerHTML = ""; more();
}

function hl(text) {
  if (!terms.length) return esc(text);
  const n = norm(text), mark = new Array(text.length).fill(false);
  for (const t of terms) {
    if (/^\d$/.test(t)) continue;
    let i = 0;
    while ((i = n.indexOf(t, i)) !== -1) {
      if (i === 0 || n[i - 1] === " ") { const e = n.indexOf(" ", i); const end = e === -1 ? n.length : e; for (let k = i; k < Math.min(end, i + t.length); k++) mark[k] = true; }
      i += t.length;
    }
  }
  const chars = Array.from(text);
  // text et n ont la même longueur en unités UTF-16 sauf paires de substitution ; Array.from garde l'alignement sur les points de code
  let out = "", open = false, idx = 0;
  for (const c of chars) {
    const m = mark[idx]; idx += c.length;
    if (m && !open) { out += "<mark>"; open = true; } else if (!m && open) { out += "</mark>"; open = false; }
    out += esc(c);
  }
  return out + (open ? "</mark>" : "");
}

function more() {
  const slice = results.slice(shown, shown + PAGE);
  $("out").insertAdjacentHTML("beforeend", slice.map(([r]) => {
    const ents = [...r.people.slice(0, 4), ...r.places.slice(0, 4), ...r.aircraft.slice(0, 3)];
    const tags = r.cats.map(c => `<span class="tag" data-cat="${c}">${esc(D.cats[c][1])}</span>`).join("");
    return `<div class="hit"><h3><span class="y">${esc(r.date.split("-").reverse().join("/"))}</span>${hl(r.title)}</h3>
      <p>${hl(r.summary)}</p>
      <div class="meta"><span class="stars" title="Intérêt ${r.interest}/5">${"★".repeat(r.interest)}${"☆".repeat(5 - r.interest)}</span> ${tags}
      ${ents.length ? " · " + esc(ents.join(", ")) : ""} · n° ${r.id}</div></div>`;
  }).join(""));
  shown += slice.length;
  $("more").hidden = shown >= results.length;
}

$("more").addEventListener("click", more);
$("out").addEventListener("click", e => { const c = e.target.dataset && e.target.dataset.cat; if (c !== undefined) { $("cat").value = c; run(); } });
let timer;
$("q").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(run, 120); });
["cat", "y0", "y1", "mi", "sort"].forEach(id => $(id).addEventListener("change", run));
run();
"""


def build(data):
    return page_shell(
        META["title"],
        "Posez votre question au musée : un nom, un lieu, un avion, une année. La recherche se fait dans votre navigateur, sans IA ni serveur.",
        BODY,
        script=SCRIPT.replace("__DATA__", embed(prepare(data))),
    )
