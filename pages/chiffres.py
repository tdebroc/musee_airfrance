"""Air France en chiffres : passagers, flotte, effectifs, chiffre d'affaires, résultats (séries relevées dans les `figures`)."""
from .common import embed, page_shell

META = {
    "slug": "chiffres",
    "title": "Air France en chiffres",
    "description": "Passagers, flotte, effectifs, chiffre d'affaires et résultats de la compagnie puis du groupe Air France-KLM, tels que les éphémérides les citent (de 1946 à 2020).",
    "order": 12,
}

EURO_PER_FRANC = 1 / 6.55957

# Les `figures` sont trop hétérogènes pour une extraction automatique (trimestres, semestres, filiales, concurrents,
# jalons « 5 millionième passager »...). Les points ci-dessous ont été choisis à la main après lecture des textes :
# annuels, à l'échelle de la compagnie ou du groupe. Chaque entrée est vérifiée à la construction contre enriched.jsonl.
# (métrique, série, id du texte, libellé exact, valeur d'origine, année, périmètre, note)
# valeur d'origine = nombre tel que dans `figures` ; "*" comme libellé = somme des figures de type avion / personnel du texte.
AF, GR = "af", "groupe"
POINTS = [
    # --- passagers
    ("passagers", AF, 1169, "passagers transportés", 1075000, 1952, AF, "année 1952"),
    ("passagers", AF, 1845, "passagers transportés", 2332066, 1956, AF, "année 1956"),
    ("passagers", AF, 3821, "passagers transportés", 4591853, 1968, AF, "année 1968"),
    ("passagers", AF, 7290, "passagers transport&#233;s par Air France", 42900000, 2003, AF, ""),
    ("passagers", AF, 7436, "passagers transportés", 43700000, 2004, AF, "exercice cité dans un texte de partenariat"),
    ("passagers", GR, 10293, "passagers transportés", 70000000, 2006, GR, "chiffre arrondi (« 70 millions par an »)"),
    ("passagers", GR, 7910, "passagers transportés", 74.8, 2008, GR, "exercice 2007-08"),
    ("passagers", GR, 9254, "passagers transportés Groupe", 93400000, 2016, GR, ""),
    ("passagers", GR, 9254, "passagers transportés Groupe", 98700000, 2017, GR, ""),
    ("passagers", GR, 9705, "passagers transportés groupe", 101.4, 2018, GR, "premier passage au-dessus de 100 millions"),
    ("passagers", GR, 10121, "passagers transportés groupe", 104200000, 2019, GR, ""),
    ("passagers", AF, 10121, "passagers transportés Air France", 52600000, 2019, AF, "Air France seule (groupe : 104,2 M)"),
    # --- flotte
    ("flotte", AF, 547, "flotte totale", 88, 1946, AF, "août 1946"),
    ("flotte", AF, 645, "*avions", None, 1947, AF, "somme des 8 types d'avions listés au 31 décembre 1947"),
    ("flotte", AF, 7885, "flotte en exploitation", 393, 2008, AF, "Air France avec ses filiales régionales"),
    ("flotte", AF, 8547, "flotte d'avions en exploitation", 387, 2012, AF, "Air France avec ses filiales régionales"),
    ("flotte", AF, 10185, "flotte totale", 224, 2020, AF, "Air France seule, mai 2020 (pandémie)"),
    ("flotte", GR, 10293, "flotte", 558, 2006, GR, ""),
    ("flotte", GR, 7714, "flotte", 561, 2007, GR, ""),
    ("flotte", GR, 7888, "flotte totale du groupe", 569, 2008, GR, "d'autres textes de 2008-09 citent 622-623 avions"),
    # --- effectifs
    ("effectifs", AF, 645, "*personnel", None, 1947, AF, "personnel au sol (9 580) + navigant (970)"),
    ("effectifs", AF, 5594, "effectif salarié", 39000, 1991, AF, ""),
    ("effectifs", AF, 5991, "effectif inscrit", 42645, 1994, AF, "effectif inscrit (≠ effectif pondéré)"),
    ("effectifs", AF, 6131, "effectif pondéré", 37419, 1994, AF, "moyenne pondérée sur l'exercice"),
    ("effectifs", AF, 6326, "effectif moyen pondéré", 36484, 1996, AF, "moyenne pondérée sur l'exercice"),
    ("effectifs", AF, 6451, "effectif moyen pondéré", 36173, 1997, AF, "moyenne pondérée sur l'exercice"),
    ("effectifs", AF, 8606, "effectif total de référence", 49301, 2011, AF, "salariés sous contrat français"),
    ("effectifs", GR, 7320, "effectifs", 106000, 2004, GR, ""),
    ("effectifs", GR, 10347, "salariés", 100000, 2006, GR, "chiffre arrondi"),
    ("effectifs", GR, 7714, "effectif", 100000, 2007, GR, "chiffre arrondi"),
    ("effectifs", GR, 7888, "salariés du groupe", 103000, 2008, GR, ""),
    ("effectifs", GR, 7909, "effectifs", 104659, 2008, GR, ""),
    ("effectifs", GR, 8090, "Effectifs salariés", 106800, 2009, GR, ""),
    # --- chiffre d'affaires
    ("ca", AF, 6590, "chiffre d'affaires", 60.7, 1998, AF, "exercice 1997-98"),
    ("ca", AF, 6733, "chiffre d'affaires consolidé", 59.7, 1999, AF, "exercice 1998-99"),
    ("ca", AF, 7179, "chiffre d'affaires", 12.69, 2003, AF, "exercice 2002-03"),
    ("ca", AF, 9037, "Chiffre d'affaires", 15.4, 2016, AF, "Air France seule"),
    ("ca", GR, 7577, "chiffre d'affaires en IFRS", 19078, 2005, GR, "exercice 2004-05 (normes IFRS)"),
    ("ca", GR, 7888, "chiffre d'affaires du groupe", 23.07, 2007, GR, "exercice 2006-07"),
    ("ca", GR, 7909, "chiffre d'affaires", 24.11, 2008, GR, "exercice 2007-08"),
    ("ca", GR, 8042, "chiffre d'affaires", 23.97, 2009, GR, "exercice 2008-09"),
    ("ca", GR, 8269, "chiffre d'affaires total", 20.99, 2010, GR, "exercice 2009-10"),
    ("ca", GR, 8540, "chiffre d'affaires total", 24.36, 2011, GR, ""),
    ("ca", GR, 8729, "chiffre d'affaires total", 25.63, 2012, GR, ""),
    ("ca", GR, 8812, "chiffre d'affaires", 25500000000, 2013, GR, ""),
    ("ca", GR, 8812, "chiffre d'affaires", 24900000000, 2014, GR, ""),
    # --- résultats : net
    ("resultat", "net", 6131, "perte nette", -1265, 1994, AF, ""),
    ("resultat", "net", 6451, "résultat net retraité", 211, 1997, AF, "exercice 1996-97"),
    ("resultat", "net", 6590, "bénéfice net", 1.87, 1998, AF, "exercice 1997-98"),
    ("resultat", "net", 6832, "résultat net", 354, 2000, AF, "exercice 1999-2000"),
    ("resultat", "net", 6936, "résultat net consolidé", 421, 2001, AF, "exercice 2000-01"),
    ("resultat", "net", 7065, "résultat net", 153, 2002, AF, "exercice 2001-02"),
    ("resultat", "net", 8043, "résultat net part du Groupe", -814, 2009, GR, "exercice 2008-09 (un autre texte cite −505 M€)"),
    ("resultat", "net", 8269, "résultat net part du groupe annuel", -1.56, 2010, GR, "exercice 2009-10"),
    ("resultat", "net", 8540, "résultat net part du groupe", -809, 2011, GR, ""),
    ("resultat", "net", 8729, "résultat net part du Groupe", -1.19, 2012, GR, ""),
    ("resultat", "net", 8813, "résultat net part du groupe", -1827000000, 2013, GR, ""),
    ("resultat", "net", 8813, "résultat net part du groupe", -198000000, 2014, GR, ""),
    ("resultat", "net", 9767, "résultat net", -153, 2018, AF, "Air France seule"),
    ("resultat", "net", 10158, "résultat net", -141, 2019, AF, "Air France seule"),
    # --- résultats : exploitation
    ("resultat", "expl", 6326, "résultat d'exploitation", 413, 1996, AF, "premier résultat positif depuis 1989"),
    ("resultat", "expl", 7065, "résultat d'exploitation", 235, 2002, AF, "exercice 2001-02"),
    ("resultat", "expl", 7909, "résultat d'exploitation", 1.41, 2008, GR, "exercice 2007-08 (record)"),
    ("resultat", "expl", 8267, "résultat d'exploitation", -1.28, 2010, GR, "exercice 2009-10"),
    ("resultat", "expl", 8540, "résultat d'exploitation", -353, 2011, GR, ""),
    ("resultat", "expl", 8729, "résultat d'exploitation", -300, 2012, GR, ""),
    ("resultat", "expl", 8813, "résultat d'exploitation", 130000000, 2013, GR, ""),
    ("resultat", "expl", 8813, "résultat d'exploitation", -129000000, 2014, GR, ""),
    ("resultat", "expl", 9037, "Résultat d'exploitation", 372, 2016, AF, "Air France seule"),
    ("resultat", "expl", 9767, "résultat d'exploitation", 266, 2018, AF, "Air France seule"),
    ("resultat", "expl", 10158, "résultat d'exploitation", 280, 2019, AF, "Air France seule"),
]

# valeur finale : passagers en millions, argent en millions d'euros (francs convertis au taux fixe de 1999)
MONEY = {
    "euros": 1e-6, "millions d'euros": 1, "milliards d'euros": 1000,
    "francs": 1e-6 * EURO_PER_FRANC, "millions de francs": EURO_PER_FRANC, "milliards de francs": 1000 * EURO_PER_FRANC,
}


def find_figure(record, label, raw, year, metric):
    """Retourne (valeur normalisée, unité d'origine, libellé, valeur d'origine) ; échoue si la figure n'existe pas."""
    figs = record["figures"]
    if label.startswith("*"):
        kind = label[1:]
        if kind == "avions":
            sel = [f for f in figs if f["unit"] == "avions" and f["year"] == year]
        else:
            sel = [f for f in figs if f["label"].startswith("personnel") and f["year"] == year]
        assert sel, (record["id"], label)
        return sum(f["value"] for f in sel), sel[0]["unit"], label, sum(f["value"] for f in sel)
    for f in figs:
        # l'année des figures est parfois le début de l'exercice (2008 pour l'exercice 2008-09 clos en 2009)
        if f["label"] != label or (f["year"] is not None and abs(f["year"] - year) > 1):
            continue
        value = float(f["value"])
        unit = str(f["unit"]).strip().lower()
        # `raw` est soit la valeur d'origine, soit (signe/échelle) la valeur attendue dans l'unité du texte ; on teste les deux
        candidates = {abs(value), value}
        if raw is None or abs(raw) in candidates or raw in candidates:
            return value, unit, f["label"], value
    raise AssertionError((record["id"], label, raw, year, [(f["label"], f["value"], f["year"]) for f in figs]))


def normalise(metric, value, unit, raw_negative):
    if metric == "passagers":
        return value / 1e6 if unit == "passagers" else value
    if metric in ("flotte", "effectifs"):
        return value
    sign = -1 if raw_negative else 1
    if unit == "euros" and abs(value) < 1e5:
        return sign * abs(value)  # erreur d'extraction du texte 9767 : « 266 euros » est en réalité 266 M€
    return sign * abs(value) * MONEY[unit]


def collect(data):
    points = []
    for metric, series, tid, label, raw, year, scope, note in POINTS:
        record = data.enriched[tid]
        value, unit, flabel, orig = find_figure(record, label, raw, year, metric)
        negative = raw is not None and raw < 0
        v = normalise(metric, value, unit, negative)
        points.append({
            "m": metric, "s": series, "scope": scope, "id": tid, "year": year, "v": round(v, 3),
            "label": flabel.replace("&#233;", "é"), "orig": orig, "neg": negative,
            "unit": unit if label[0] != "*" else ("avions" if label == "*avions" else "personnes"),
            "note": note, "title": record["title"], "date": record["date"],
        })
    return points


def build(data):
    points = collect(data)
    texts = {p["id"]: data.text(p["id"]) for p in points}
    payload = {"points": points, "texts": texts}
    body = """
<style>
.tabs { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }
.tabs button { background:var(--card); color:var(--ink); border:1px solid var(--line); border-radius:999px; padding:6px 14px; font:inherit; cursor:pointer; }
.tabs button.on { background:var(--accent); color:#fff; border-color:var(--accent); }
@media (prefers-color-scheme: dark) { .tabs button.on { color:#0e1420; } }
.note { color:var(--muted); font-size:13px; max-width:90ch; }
svg text { fill:var(--muted); font-size:11px; } svg .grid line { stroke:var(--line); } svg .domain { stroke:var(--line); }
#tip { position:fixed; pointer-events:none; background:var(--card); border:1px solid var(--line); border-radius:8px; padding:6px 10px; font-size:12px; display:none; max-width:320px; box-shadow:0 2px 10px #0003; z-index:9; }
table { border-collapse:collapse; width:100%; font-size:13px; } th, td { text-align:left; padding:5px 8px; border-bottom:1px solid var(--line); vertical-align:top; }
td.num { text-align:right; white-space:nowrap; } tbody tr { cursor:pointer; } tbody tr:hover { background:var(--bg); }
#source { margin-top:12px; font-size:13px; white-space:pre-wrap; max-height:260px; overflow:auto; }
h2 { font-size:18px; margin:24px 0 8px; } .legend { display:flex; gap:16px; flex-wrap:wrap; font-size:13px; color:var(--muted); margin:6px 0; }
.legend i { display:inline-block; width:10px; height:10px; margin-right:5px; }
</style>
<div class="tabs" id="tabs"></div>
<p class="note" id="intro"></p>
<div class="card"><div class="legend" id="legend"></div><svg id="chart" width="100%" height="400"></svg>
<div id="source" class="card" style="display:none"></div></div>
<h2>Les relevés</h2>
<div class="card" style="max-height:480px;overflow:auto"><table><thead><tr><th>Année</th><th>Série</th><th>Valeur</th><th>Dans le texte</th><th>Texte</th></tr></thead><tbody id="rows"></tbody></table></div>
<p class="note">Choix des points : les <code>figures</code> des éphémérides mélangent trimestres, semestres, filiales, concurrents et jalons (« 5 millionième passager »). Seuls les chiffres <b>annuels</b>,
à l'échelle de la compagnie ou du groupe, ont été retenus après lecture de leur texte ; les points isolés sont reliés par un trait, ce qui ne dit rien des années intermédiaires.
Francs convertis en euros au taux de 1999 (1 € = 6,55957 F), sans correction de l'inflation. L'année est celle de la clôture de l'exercice quand il est précisé.</p>
<div id="tip"></div>
"""
    script = "const D=" + embed(payload) + ";\n" + SCRIPT
    return page_shell(
        META["title"],
        "Combien de passagers, d'avions, de salariés ? Quel chiffre d'affaires, quel résultat ? Les séries ci-dessous sont reconstituées à partir des seuls chiffres cités dans les éphémérides : "
        "elles sont <b>lacunaires</b>, et le périmètre change en 2004 (Air France seule, puis groupe Air France-KLM).",
        body,
        head_extra='<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>',
        script=script,
    )


SCRIPT = r"""
const METRICS = {
  passagers: {name: 'Passagers', unit: 'millions', fmt: v => v.toLocaleString('fr-FR', {maximumFractionDigits: v < 10 ? 2 : 1}) + ' M',
    series: {af: 'Air France', groupe: 'Groupe Air France-KLM'}, intro: 'Passagers transportés sur l\'année.'},
  flotte: {name: 'Flotte', unit: 'avions', fmt: v => Math.round(v).toLocaleString('fr-FR') + ' avions',
    series: {af: 'Air France', groupe: 'Groupe Air France-KLM'}, intro: 'Nombre d\'avions. Le périmètre varie (avec ou sans filiales régionales) : voir la note de chaque point.'},
  effectifs: {name: 'Effectifs', unit: 'personnes', fmt: v => Math.round(v).toLocaleString('fr-FR') + ' pers.',
    series: {af: 'Air France', groupe: 'Groupe Air France-KLM'}, intro: 'Salariés. « Pondéré » = moyenne de l\'exercice, « inscrit » = effectif à une date.'},
  ca: {name: 'Chiffre d\'affaires', unit: 'M€', fmt: v => Math.round(v).toLocaleString('fr-FR') + ' M€',
    series: {af: 'Air France', groupe: 'Groupe Air France-KLM'}, intro: 'En millions d\'euros nominaux (francs convertis). Pas d\'inflation corrigée.'},
  resultat: {name: 'Résultats', unit: 'M€', fmt: v => Math.round(v).toLocaleString('fr-FR') + ' M€',
    series: {net: 'Résultat net', expl: 'Résultat d\'exploitation'}, intro: 'En millions d\'euros nominaux. Forme du point : cercle = groupe Air France-KLM, losange = Air France seule.'},
};
const COLORS = {af: '#2a6fdb', groupe: '#e3001b', net: '#2a6fdb', expl: '#e08a00'};
const esc = s => String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const tip = document.getElementById('tip');
function showTip(ev, html) { tip.style.display = 'block'; tip.innerHTML = html; tip.style.left = Math.min(ev.clientX + 12, innerWidth - 340) + 'px'; tip.style.top = (ev.clientY + 12) + 'px'; }
function hideTip() { tip.style.display = 'none'; }
let metric = 'passagers';
const fmtOrig = p => (p.neg ? '−' : '') + Math.abs(p.orig).toLocaleString('fr-FR', {maximumFractionDigits: 3}) + ' ' + p.unit + (p.unit === 'euros' && Math.abs(p.orig) < 1e5 ? ' (en réalité M€, erreur d\'extraction)' : '');

function renderTabs() {
  const box = document.getElementById('tabs');
  box.innerHTML = Object.entries(METRICS).map(([k, m]) => `<button data-k="${k}" class="${k === metric ? 'on' : ''}">${m.name}</button>`).join('');
  box.querySelectorAll('button').forEach(b => b.onclick = () => { metric = b.dataset.k; document.getElementById('source').style.display = 'none'; renderAll(); });
}
function tipHtml(p) {
  const M = METRICS[p.m];
  return `<b>${p.year} · ${M.series[p.s]}</b><br>${M.fmt(p.v)}<br>${esc(p.label)} : ${esc(fmtOrig(p))}` + (p.note ? `<br><i>${esc(p.note)}</i>` : '');
}
function showSource(p) {
  const el = document.getElementById('source'); el.style.display = 'block';
  el.innerHTML = `<b>${esc(p.title)}</b> · ${esc(p.date)}<br><i>${esc(p.label)} : ${esc(fmtOrig(p))}${p.note ? ' — ' + esc(p.note) : ''}</i><br><br>` + esc(D.texts[p.id] || '').replace(/<[^>]+>/g, ' ');
}
function drawChart() {
  const M = METRICS[metric], pts = D.points.filter(p => p.m === metric);
  const svg = d3.select('#chart'); svg.selectAll('*').remove();
  const W = document.getElementById('chart').clientWidth || 800, H = 400, m = {l: 74, r: 20, t: 14, b: 30};
  const x = d3.scaleLinear().domain([d3.min(pts, p => p.year) - 1, d3.max(pts, p => p.year) + 1]).range([m.l, W - m.r]);
  const lo = Math.min(0, d3.min(pts, p => p.v)), hi = d3.max(pts, p => p.v);
  const y = d3.scaleLinear().domain([lo, hi + (hi - lo) * 0.06]).nice().range([H - m.b, m.t]);
  svg.append('g').attr('class', 'grid').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(6).tickSize(-(W - m.l - m.r)).tickFormat('')).select('.domain').remove();
  svg.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickFormat(d3.format('d')).ticks(12));
  svg.append('g').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(6).tickFormat(v => v.toLocaleString('fr-FR')));
  svg.append('text').attr('x', 4).attr('y', m.t + 4).text(M.unit);
  if (lo < 0) svg.append('line').attr('x1', m.l).attr('x2', W - m.r).attr('y1', y(0)).attr('y2', y(0)).attr('stroke', 'var(--muted)').attr('stroke-dasharray', '3 3');
  for (const key of Object.keys(M.series)) {
    const sp = pts.filter(p => p.s === key).sort((a, b) => a.year - b.year || a.v - b.v);
    if (!sp.length) continue;
    // une valeur par année pour le trait (la dernière citée), tous les points restent visibles
    const line = Array.from(d3.group(sp, p => p.year), ([yr, v]) => [yr, v[v.length - 1].v]);
    svg.append('path').datum(line).attr('fill', 'none').attr('stroke', COLORS[key]).attr('stroke-width', 1.6).attr('stroke-opacity', .55)
      .attr('d', d3.line().x(d => x(d[0])).y(d => y(d[1])));
    svg.selectAll(null).data(sp).enter().append('path')
      .attr('transform', p => `translate(${x(p.year)},${y(p.v)})`)
      .attr('d', p => d3.symbol().type(p.scope === 'af' && metric === 'resultat' ? d3.symbolDiamond : d3.symbolCircle).size(90)())
      .attr('fill', COLORS[key]).attr('stroke', 'var(--card)').style('cursor', 'pointer')
      .on('mousemove', (ev, p) => showTip(ev, tipHtml(p))).on('mouseleave', hideTip).on('click', (ev, p) => showSource(p));
  }
}
function renderRows() {
  const M = METRICS[metric];
  const pts = D.points.filter(p => p.m === metric).sort((a, b) => a.year - b.year || a.s.localeCompare(b.s));
  document.getElementById('rows').innerHTML = pts.map((p, i) =>
    `<tr data-i="${i}"><td>${p.year}</td><td><span style="color:${COLORS[p.s]}">●</span> ${esc(M.series[p.s])}${metric === 'resultat' ? ' · ' + (p.scope === 'af' ? 'Air France' : 'groupe') : ''}</td>` +
    `<td class="num">${M.fmt(p.v)}</td><td>${esc(p.label)} : ${esc(fmtOrig(p))}${p.note ? '<br><small>' + esc(p.note) + '</small>' : ''}</td><td>${esc(p.title)}</td></tr>`).join('');
  document.querySelectorAll('#rows tr').forEach(tr => tr.onclick = () => { showSource(pts[+tr.dataset.i]); window.scrollTo({top: document.getElementById('chart').getBoundingClientRect().top + scrollY - 20, behavior: 'smooth'}); });
}
function renderAll() {
  const M = METRICS[metric];
  renderTabs();
  document.getElementById('intro').textContent = M.intro;
  document.getElementById('legend').innerHTML = Object.entries(M.series).map(([k, l]) => `<span><i style="background:${COLORS[k]}"></i>${l}</span>`).join('');
  drawChart(); renderRows();
}
window.addEventListener('resize', drawChart);
renderAll();
"""
