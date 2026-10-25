"""Prix des billets : les `figures` de type tarif (francs puis euros), par ligne et par année."""
import re
import unicodedata

from .common import embed, page_shell

META = {
    "slug": "prix-billets",
    "title": "Prix des billets",
    "description": "Les tarifs cités dans les éphémérides, en francs puis en euros, ligne par ligne et année par année (de Toulouse-Rabat en 1919 à Paris-New York en 2010).",
    "order": 11,
}

EURO_PER_NF = 6.55957  # 1 € = 6,55957 nouveaux francs (parité fixe de 1999)
OLD_FRANC_LAST_YEAR = 1959  # réforme du 1er janvier 1960 : 1 nouveau franc = 100 anciens francs
CURRENCIES = {"francs": "franc", "nouveaux francs": "franc", "euros": "euro"}

# Lignes (couples de lieux) : alias de noms, normalisés vers un nom d'affichage.
ALIASES = {  # clés sans accent ni casse (voir `norm`)
    "la reunion": "Réunion", "reunion": "Réunion", "rio de janeiro": "Rio de Janeiro", "rio": "Rio de Janeiro",
    "orly": "Paris", "hong-kong": "Hong Kong", "hong kong": "Hong Kong", "sao paulo": "São Paulo",
    "fort-de-france": "Fort-de-France", "st tropez": "Saint-Tropez", "pointe-a-pitre": "Pointe-à-Pitre",
    "etats-unis": "États-Unis", "seoul": "Séoul", "dusseldorf": "Düsseldorf", "ancone": "Ancône",
    "beijing": "Pékin", "pekin": "Pékin", "le caire": "Le Caire", "tokyo": "Tokyo", "saigon": "Saïgon",
}
# Extrémités qui ne sont pas des lieux de vol ou qui ne désignent pas une ligne précise.
NOT_A_LINE = re.compile(r"wagons-lits|\bcar\b|invalides|berline|wi-fi|timbre|navette|abonnement|menu|château|siège|"
                        r"province|lunettes|assistance|minitours|aéroflorales|entretien", re.I)
NOT_A_FARE = re.compile(r"action|achat|rachat|d'appel|propriété|prix unitaire|prix minimum$|prix maximum$|prix du grand|coffret|"
                        r"carte cadeau|tee-shirt|t-shirt|mariniere|livre|loyer|assurance|enregistrement|fret|colis|consigne|"
                        r"kit de voyage|avion de noël|prix annuel|prix moyen des billets ryanair|service saphir|menus?\b|château|prix d'un a\d|"
                        r"\b(19|20)\d\d$",
                        re.I)


def norm(text):
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def place_names(records):
    """Noms de lieux (villes, pays) connus par les enregistrements, pour reconnaître les extrémités d'une ligne."""
    names = set()
    for r in records:
        for p in r["places"]:
            names.add(p["name"])
        for route in r["routes"]:
            for c in route["cities"]:
                names.add(c["name"])
    names |= {"France", "Corse", "Antilles", "Europe", "Afrique du Nord", "Réunion", "La Réunion", "Orly", "Paris",
              "Hong-Kong", "Etats-Unis", "Province britannique", "Rio", "St Tropez", "Saïgon", "Irlande", "Djibouti", "Maroc"}
    return {n for n in names if len(n) >= 3}


def find_places(label, lexicon):
    """Lieux cités dans le libellé, dans l'ordre, par plus longue correspondance (jamais à l'intérieur d'un mot)."""
    text = norm(label)
    found = []
    for name in sorted(lexicon, key=len, reverse=True):
        key = norm(name)
        for m in re.finditer(r"(?<![\w])" + re.escape(key) + r"(?![\w])", text):
            if not any(a < m.end() and m.start() < b for a, b, _ in found):
                found.append((m.start(), m.end(), name))
    found.sort()
    out = []
    for _, _, name in found:
        name = ALIASES.get(norm(name), name)
        if name not in out:
            out.append(name)
    return out


def trip_type(label):
    low = label.lower()
    if re.search(r"retour|\bar\b|a/r|aller-retour", low):
        return "aller-retour"
    if re.search(r"simple|\(aller\)", low):
        return "aller simple"
    return "non précisé"


def euros(value, currency, year):
    """Montant nominal converti en euros (aucune correction de l'inflation)."""
    if currency == "euro":
        return value
    new_francs = value / 100 if year <= OLD_FRANC_LAST_YEAR else value
    return new_francs / EURO_PER_NF


def category(label, is_line):
    low = label.lower()
    if is_line:
        return "Ligne"
    if re.search(r"abonnement|carte", low):
        return "Carte"
    if re.search(r"bagage|siège|pass |wi-fi|assistance|voiture|moto|menu", low):
        return "Option"
    if re.search(r"forfait|jours|circuit|golf|pêche|périodes|week-end", low):
        return "Forfait"
    if re.search(r"classe|economy|business|affaires|économique|jeune", low):
        return "Classe"
    return "Autre"


def collect(data):
    records = data.records()
    lexicon = place_names(records)
    rows = []
    for r in records:
        for f in r["figures"]:
            unit = str(f["unit"]).strip().lower()
            label = f["label"].replace("&eacute;", "é").strip()
            if unit not in CURRENCIES or not re.match(r"(tarif|prix)\b", label.lower()) or NOT_A_FARE.search(label):
                continue
            currency = CURRENCIES[unit]
            year = f["year"] or int(r["date"][:4])
            if abs(year - int(r["date"][:4])) > 3:
                year = int(r["date"][:4])
            if currency == "euro" and year < 1999:
                continue  # unité manifestement fausse (texte 4067 : « 200 euros » en 1971)
            places = [] if NOT_A_LINE.search(label) else find_places(re.sub(r"\(.*?\)", "", label), lexicon)
            places = [p for p in places if p not in ("Province britannique",)]
            if places[:1] == ["France"] and len(places) >= 3:
                places = places[1:]  # « Intra-France Paris-Marseille »
            line = None
            if len(places) >= 2 and not (len(places) >= 3 and places[0] != "Paris"):  # « Jeunes New York, Boston, Washington » : pas une ligne
                a, b = places[0], places[1]
                if "Europe" not in (a, b) and "Afrique du Nord" not in (a, b):
                    line = [a, b]
            rows.append({
                "id": r["id"], "date": r["date"], "year": year, "label": label, "value": f["value"],
                "unit": currency, "eur": euros(f["value"], currency, year), "line": line,
                "trip": trip_type(label) if line else None, "cat": category(label, bool(line)),
                "title": r["title"], "interest": r["interest"],
            })
    # les mêmes tarifs répétés par plusieurs textes ne comptent qu'une fois
    seen, unique = set(), []
    for row in rows:
        key = (line_key(row["line"]) if row["line"] else row["label"], row["trip"], row["value"], row["year"])
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def line_key(line):
    # Paris est toujours en premier ; sinon ordre alphabétique pour que A-B et B-A soient la même ligne
    a, b = line
    rank = {"Paris": 0, "France": 1}
    if (rank.get(b, 9), b) < (rank.get(a, 9), a):
        a, b = b, a
    return f"{a} – {b}"


def build(data):
    rows = collect(data)
    for row in rows:
        row["eur"] = round(row["eur"], 2)
        row["lk"] = line_key(row["line"]) if row["line"] else None
        del row["line"]
    texts = {}
    for row in rows:
        texts[row["id"]] = data.text(row["id"])
    payload = {"rows": rows, "texts": texts, "rate": EURO_PER_NF}
    body = """
<style>
.row { display:flex; gap:16px; flex-wrap:wrap; align-items:flex-start; }
.side { flex:0 0 270px; max-height:560px; overflow:auto; }
.main { flex:1 1 560px; min-width:0; }
.chip { display:flex; gap:6px; align-items:center; padding:3px 4px; border-radius:6px; cursor:pointer; font-size:13px; }
.chip:hover { background:var(--bg); } .chip .n { margin-left:auto; color:var(--muted); font-size:12px; }
.chip i { width:10px; height:10px; border-radius:50%; flex:none; border:1px solid var(--line); }
.tools { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:10px; align-items:center; font-size:13px; color:var(--muted); }
select, input[type=search] { background:var(--card); color:var(--ink); border:1px solid var(--line); border-radius:6px; padding:5px 8px; font:inherit; }
svg text { fill:var(--muted); font-size:11px; } svg .grid line { stroke:var(--line); } svg .domain { stroke:var(--line); }
table { border-collapse:collapse; width:100%; font-size:13px; } th, td { text-align:left; padding:5px 8px; border-bottom:1px solid var(--line); vertical-align:top; }
th { cursor:pointer; position:sticky; top:0; background:var(--card); } td.num { text-align:right; white-space:nowrap; }
.tablewrap { max-height:520px; overflow:auto; }
#tip { position:fixed; pointer-events:none; background:var(--card); border:1px solid var(--line); border-radius:8px; padding:6px 10px; font-size:12px; display:none; max-width:320px; box-shadow:0 2px 10px #0003; z-index:9; }
.note { color:var(--muted); font-size:13px; max-width:90ch; } .stats { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px; }
.stat { padding:10px 16px; } .stat b { display:block; font-size:22px; } .stat span { color:var(--muted); font-size:12px; }
#source { margin-top:12px; font-size:13px; white-space:pre-wrap; max-height:260px; overflow:auto; } .hl { background:#ffd54a55; }
h2 { font-size:18px; margin:28px 0 8px; }
</style>
<div class="stats" id="stats"></div>
<p class="note" id="method"></p>
<h2>Une ligne, des années</h2>
<div class="row">
  <div class="card side" id="lines"></div>
  <div class="card main">
    <div class="tools">
      <label>Voyage <select id="trip"><option value="all">tous</option><option value="aller-retour">aller-retour</option><option value="aller simple">aller simple</option></select></label>
      <label>Échelle <select id="scale"><option value="log">logarithmique</option><option value="linear">linéaire</option></select></label>
      <span>Cliquer une ligne dans la liste pour l'ajouter ou la retirer.</span>
    </div>
    <svg id="chart" width="100%" height="420"></svg>
    <div id="source" class="card" style="display:none"></div>
  </div>
</div>
<h2>Tous les tarifs de ligne</h2>
<div class="card"><svg id="scatter" width="100%" height="360"></svg></div>
<h2>Tous les tarifs relevés</h2>
<div class="tools"><input type="search" id="q" placeholder="Rechercher (libellé, texte)…"><label>Catégorie <select id="cat"><option value="">toutes</option></select></label><span id="count"></span></div>
<div class="card tablewrap"><table id="table"><thead><tr>
<th data-k="year">Année</th><th data-k="label">Libellé</th><th data-k="value">Montant d'origine</th><th data-k="eur">En euros (nominal)</th><th data-k="cat">Type</th></tr></thead><tbody></tbody></table></div>
<div id="tip"></div>
"""
    script = "const D=" + embed(payload) + ";\n" + SCRIPT
    return page_shell(
        META["title"],
        "Ce que coûtait un billet Air France : tous les tarifs cités dans les éphémérides, ramenés en euros pour être comparés. "
        "Les montants sont <b>nominaux</b> (non corrigés de l'inflation) : un billet à 6 400 F en 1952 n'est pas comparable à un billet à 100 € aujourd'hui.",
        body,
        head_extra='<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>',
        script=script,
    )


SCRIPT = r"""
const fmtE = v => (v < 10 ? v.toFixed(2) : Math.round(v).toLocaleString('fr-FR')).replace('.', ',') + ' €';
const fmtO = r => r.value.toLocaleString('fr-FR') + (r.unit === 'euro' ? ' €' : (r.year <= 1959 ? ' F (anciens)' : ' F'));
const esc = s => String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const rows = D.rows;
const lineRows = rows.filter(r => r.lk);
const tip = document.getElementById('tip');
function showTip(ev, html) { tip.style.display = 'block'; tip.innerHTML = html; tip.style.left = Math.min(ev.clientX + 12, innerWidth - 340) + 'px'; tip.style.top = (ev.clientY + 12) + 'px'; }
function hideTip() { tip.style.display = 'none'; }
const palette = ['#2a6fdb', '#e3001b', '#1a9e6b', '#e08a00', '#8a4fd1', '#0e9ab5', '#c2417a', '#7a8a00'];

// --- bandeau
const years = rows.map(r => r.year);
const lineSet = new Set(lineRows.map(r => r.lk));
document.getElementById('stats').innerHTML = [
  [rows.length, 'tarifs relevés'], [lineRows.length, 'tarifs de ligne'], [lineSet.size, 'lignes distinctes'],
  [d3.min(years) + '–' + d3.max(years), 'années couvertes'],
].map(([a, b]) => `<div class="card stat"><b>${a}</b><span>${b}</span></div>`).join('');
document.getElementById('method').innerHTML =
  `Francs → euros : avant 1960, les montants sont en anciens francs (÷ 100 pour obtenir des nouveaux francs) ; ensuite 1 € = ${D.rate.toString().replace('.', ',')} F. ` +
  `Seuls les libellés commençant par « tarif » ou « prix » sont retenus (cotation d'actions, prix d'achat d'avions, menus et vins sont écartés) ; ` +
  `les montants en dollars ne sont pas convertis. Une ligne = les deux premiers lieux du libellé, sans distinguer le sens ; une cellule « non précisé » peut être un aller simple ou un aller-retour.`;

// --- liste des lignes
const byLine = d3.group(lineRows, r => r.lk);
const lineList = Array.from(byLine, ([k, v]) => ({k, n: v.length, years: new Set(v.map(r => r.year)).size}))
  .sort((a, b) => b.years - a.years || b.n - a.n || a.k.localeCompare(b.k, 'fr'));
let selected = ['Paris – Londres', 'Paris – New York', 'Paris – Alger', 'Paris – Marseille'].filter(k => byLine.has(k));
if (!selected.length) selected = lineList.slice(0, 3).map(l => l.k);
const colorOf = k => { const i = selected.indexOf(k); return i < 0 ? 'transparent' : palette[i % palette.length]; };
function renderLines() {
  const box = document.getElementById('lines');
  box.innerHTML = '<div class="note" style="margin-bottom:6px">Lignes triées par nombre d\'années documentées</div>' +
    lineList.map(l => `<div class="chip" data-k="${esc(l.k)}"><i style="background:${colorOf(l.k)}"></i>${esc(l.k)}<span class="n">${l.years} an${l.years > 1 ? 's' : ''}</span></div>`).join('');
  box.querySelectorAll('.chip').forEach(el => el.onclick = () => {
    const k = el.dataset.k, i = selected.indexOf(k);
    if (i >= 0) selected.splice(i, 1); else if (selected.length < palette.length) selected.push(k);
    renderLines(); drawChart();
  });
}

// --- graphique par ligne
const shapes = {'aller-retour': d3.symbolCircle, 'aller simple': d3.symbolTriangle, 'non précisé': d3.symbolSquare};
function showSource(r) {
  const el = document.getElementById('source'); el.style.display = 'block';
  const text = D.texts[r.id] || '';
  el.innerHTML = `<b>${esc(r.label)} : ${esc(fmtO(r))} (≈ ${fmtE(r.eur)})</b> · ${esc(r.date)} · ${esc(r.title)}<br><br>` + esc(text);
}
function axes(svg, x, y, W, H, m, scale) {
  const yAxis = d3.axisLeft(y).ticks(scale === 'log' ? 6 : 8, scale === 'log' ? '~s' : null).tickFormat(v => v.toLocaleString('fr-FR') + ' €');
  svg.append('g').attr('class', 'grid').attr('transform', `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(6).tickSize(-(W - m.l - m.r)).tickFormat('')).select('.domain').remove();
  svg.append('g').attr('transform', `translate(0,${H - m.b})`).call(d3.axisBottom(x).tickFormat(d3.format('d')).ticks(12));
  svg.append('g').attr('transform', `translate(${m.l},0)`).call(yAxis);
}
function drawChart() {
  const svg = d3.select('#chart'); svg.selectAll('*').remove();
  const W = document.getElementById('chart').clientWidth || 700, H = 420, m = {l: 64, r: 16, t: 14, b: 30};
  const trip = document.getElementById('trip').value, scale = document.getElementById('scale').value;
  const pts = lineRows.filter(r => selected.includes(r.lk) && (trip === 'all' || r.trip === trip));
  if (!pts.length) { svg.append('text').attr('x', 20).attr('y', 40).text('Aucun tarif pour cette sélection.'); return; }
  const x = d3.scaleLinear().domain(d3.extent(pts, r => r.year)).nice().range([m.l, W - m.r]);
  if (x.domain()[0] === x.domain()[1]) x.domain([x.domain()[0] - 1, x.domain()[1] + 1]);
  const ext = d3.extent(pts, r => r.eur);
  const y = (scale === 'log' ? d3.scaleLog().domain([ext[0] / 1.3, ext[1] * 1.3]) : d3.scaleLinear().domain([0, ext[1] * 1.1])).range([H - m.b, m.t]);
  axes(svg, x, y, W, H, m, scale);
  for (const k of selected) {
    const p = pts.filter(r => r.lk === k).sort((a, b) => a.year - b.year);
    if (!p.length) continue;
    // une valeur par année (médiane) pour tracer la courbe ; tous les points restent affichés
    const med = Array.from(d3.group(p, r => r.year), ([yr, v]) => [yr, d3.median(v, r => r.eur)]).sort((a, b) => a[0] - b[0]);
    svg.append('path').datum(med).attr('fill', 'none').attr('stroke', colorOf(k)).attr('stroke-width', 1.6).attr('stroke-opacity', .6)
      .attr('d', d3.line().x(d => x(d[0])).y(d => y(d[1])));
    svg.selectAll(null).data(p).enter().append('path').attr('transform', r => `translate(${x(r.year)},${y(r.eur)})`)
      .attr('d', r => d3.symbol().type(shapes[r.trip] || d3.symbolCircle).size(70)()).attr('fill', colorOf(k)).attr('stroke', 'var(--card)').style('cursor', 'pointer')
      .on('mousemove', (ev, r) => showTip(ev, `<b>${esc(r.lk)}</b> · ${r.year}<br>${esc(r.label)}<br>${esc(fmtO(r))} ≈ <b>${fmtE(r.eur)}</b> (${r.trip})`))
      .on('mouseleave', hideTip).on('click', (ev, r) => showSource(r));
  }
  const leg = svg.append('g').attr('transform', `translate(${m.l + 8},${m.t + 4})`);
  [['aller-retour', 'aller-retour'], ['aller simple', 'aller simple'], ['non précisé', 'non précisé']].forEach(([t, l], i) => {
    leg.append('path').attr('transform', `translate(${i * 110},0)`).attr('d', d3.symbol().type(shapes[t]).size(60)()).attr('fill', 'var(--muted)');
    leg.append('text').attr('x', i * 110 + 10).attr('y', 4).text(l);
  });
}

// --- nuage de tous les tarifs de ligne
function drawScatter() {
  const svg = d3.select('#scatter'); svg.selectAll('*').remove();
  const W = document.getElementById('scatter').clientWidth || 900, H = 360, m = {l: 64, r: 16, t: 14, b: 30};
  const x = d3.scaleLinear().domain([1915, 2022]).range([m.l, W - m.r]);
  const y = d3.scaleLog().domain([d3.min(lineRows, r => r.eur) / 1.3, d3.max(lineRows, r => r.eur) * 1.3]).range([H - m.b, m.t]);
  axes(svg, x, y, W, H, m, 'log');
  svg.selectAll('circle').data(lineRows).enter().append('circle').attr('cx', r => x(r.year)).attr('cy', r => y(r.eur)).attr('r', 4)
    .attr('fill', r => r.unit === 'euro' ? 'var(--accent2)' : 'var(--accent)').attr('fill-opacity', .55).attr('stroke', 'var(--card)')
    .on('mousemove', (ev, r) => showTip(ev, `<b>${esc(r.lk)}</b> · ${r.year}<br>${esc(r.label)}<br>${esc(fmtO(r))} ≈ <b>${fmtE(r.eur)}</b>`))
    .on('mouseleave', hideTip)
    .on('click', (ev, r) => { if (!selected.includes(r.lk) && selected.length < palette.length) selected.push(r.lk); renderLines(); drawChart(); showSource(r); });
  const leg = svg.append('g').attr('transform', `translate(${m.l + 8},${m.t + 4})`);
  [['var(--accent)', 'en francs'], ['var(--accent2)', 'en euros']].forEach(([c, l], i) => {
    leg.append('circle').attr('cx', i * 90).attr('r', 4).attr('fill', c); leg.append('text').attr('x', i * 90 + 8).attr('y', 4).text(l);
  });
}

// --- tableau
const cats = Array.from(new Set(rows.map(r => r.cat))).sort();
document.getElementById('cat').innerHTML += cats.map(c => `<option>${c}</option>`).join('');
let sortKey = 'year', sortDir = 1;
function renderTable() {
  const q = document.getElementById('q').value.toLowerCase().trim(), cat = document.getElementById('cat').value;
  const list = rows.filter(r => (!cat || r.cat === cat) && (!q || (r.label + ' ' + r.title).toLowerCase().includes(q)))
    .sort((a, b) => (typeof a[sortKey] === 'string' ? a[sortKey].localeCompare(b[sortKey], 'fr') : a[sortKey] - b[sortKey]) * sortDir || a.id - b.id);
  document.getElementById('count').textContent = list.length + ' tarif' + (list.length > 1 ? 's' : '');
  document.querySelector('#table tbody').innerHTML = list.map(r =>
    `<tr><td>${r.year}</td><td title="${esc(r.title)}">${esc(r.label)}</td><td class="num">${esc(fmtO(r))}</td><td class="num">${fmtE(r.eur)}</td><td>${r.cat}</td></tr>`).join('');
}
document.querySelectorAll('#table th').forEach(th => th.onclick = () => { sortDir = sortKey === th.dataset.k ? -sortDir : 1; sortKey = th.dataset.k; renderTable(); });
['q', 'cat'].forEach(id => document.getElementById(id).oninput = renderTable);
['trip', 'scale'].forEach(id => document.getElementById(id).onchange = drawChart);
window.addEventListener('resize', () => { drawChart(); drawScatter(); });
renderLines(); drawChart(); drawScatter(); renderTable();
"""
