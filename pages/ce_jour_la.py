"""« Ce jour-là chez Air France » : les événements d'un jour-mois, toutes années confondues, classés par intérêt."""
import re

from .common import embed, page_shell

META = {
    "slug": "ce-jour-la",
    "title": "Ce jour-là chez Air France",
    "description": "Choisissez un jour du calendrier (par défaut aujourd'hui) : tous les événements d'Air France arrivés ce jour-là, d'année en année, classés par intérêt.",
    "order": 5,
}

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
TONES = {"positif": "p", "neutre": "n", "negatif": "m"}


def explicit_day(text, month, day):
    """Le texte cite-t-il lui-même ce jour (« 1er mars », « 15 mars ») ?"""
    pat = r"\b1(er)?\s+" if day == 1 else r"\b0?%d\s+" % day
    return bool(re.search(pat + MOIS[month - 1], text.lower()))


def prepare(data):
    """Un texte = [id, mmdd, année, titre, résumé, intérêt, ton, catégories, approx].

    approx = 1 quand le jour est probablement un jour par défaut : 1 917 textes sont datés du 1er du mois
    (≈ 280 attendus par jour) et le 15 est lui aussi surreprésenté ; on ne les croit que si le texte cite le jour.
    """
    rows = []
    for rec in data.records():
        d = rec["date"]
        month, day = int(d[5:7]), int(d[8:10])
        approx = int(day in (1, 15) and not explicit_day(data.text(rec["id"]), month, day))
        rows.append([rec["id"], d[5:7] + d[8:10], int(d[:4]), rec["title"], rec["summary"], rec["interest"],
                     TONES.get(rec["tone"], "n"), [c for c in rec["categories"] if c != "autre"], approx])
    return {"rows": rows, "mois": MOIS}


BODY = """
<style>
.ctl { display:flex; flex-wrap:wrap; gap:14px; align-items:center; margin-bottom:14px; font-size:14px; }
.ctl select, .ctl button { font:inherit; padding:5px 10px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--ink); cursor:pointer; }
.ctl label { display:flex; gap:6px; align-items:center; color:var(--muted); }
.sum { color:var(--muted); font-size:13px; margin:0 0 10px; }
.ev { margin-bottom:10px; } .ev h3 { margin:0 0 2px; font-size:15px; } .ev p { margin:4px 0 0; font-size:13.5px; }
.meta { font-size:12.5px; color:var(--muted); display:flex; gap:10px; flex-wrap:wrap; align-items:center; }
.yr { font-weight:700; color:var(--accent); font-size:16px; } .stars { color:#e3a008; letter-spacing:1px; }
.tag { display:inline-block; font-size:11px; padding:0 6px; border-radius:8px; border:1px solid var(--line); }
.tone-p { color:#1a7f4b; } .tone-m { color:var(--accent2); } .tone-n { color:var(--muted); }
.approx { font-size:11.5px; color:var(--muted); font-style:italic; }
details.more > summary { cursor:pointer; color:var(--accent); margin:8px 0; }
.note { color:var(--muted); font-size:12.5px; margin-top:14px; }
</style>
<div class="ctl">
  <label>Jour <select id="day"></select></label>
  <label><select id="month"></select></label>
  <button id="today">Aujourd'hui</button><button id="rand">Un jour au hasard</button>
  <label>Fenêtre <select id="win"><option value="0">ce jour exact</option><option value="3">± 3 jours</option><option value="7">± 7 jours</option></select></label>
  <label>Intérêt <select id="min"><option value="1">tous</option><option value="3">≥ 3</option><option value="4">≥ 4</option></select></label>
</div>
<p class="sum" id="sum"></p>
<div id="out"></div>
<p class="note">Les éphémérides donnent une date complète, mais près de 1 900 textes sont datés du 1er d'un mois (≈ 280 par jour attendus) : le jour y est souvent une valeur par défaut. Ces textes, ainsi que ceux du 15 qui ne citent pas eux-mêmes le jour, sont signalés « jour peut-être approximatif » et rangés à part. Classement : intérêt décroissant (note donnée par le modèle d'enrichissement), puis année.</p>
"""

SCRIPT = r"""
const D = __DATA__;
const ENT = { "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" };
const esc = s => String(s).replace(/[&<>"]/g, c => ENT[c]);
const TONE = { p:"positif", n:"neutre", m:"négatif" };
const $ = id => document.getElementById(id);
const DIM = [31,29,31,30,31,30,31,31,30,31,30,31];
const byKey = new Map();
for (const r of D.rows) { if (!byKey.has(r[1])) byKey.set(r[1], []); byKey.get(r[1]).push(r); }
const key = (m, d) => String(m).padStart(2, "0") + String(d).padStart(2, "0");
const doy = (m, d) => { let n = d; for (let i = 0; i < m - 1; i++) n += DIM[i]; return n; };   // année bissextile : 29 févr. inclus
const fromDoy = n => { n = ((n - 1 + 366) % 366) + 1; let m = 0; while (n > DIM[m]) { n -= DIM[m]; m++; } return [m + 1, n]; };
const label = (m, d) => (d === 1 ? "1er" : d) + " " + D.mois[m - 1];
const plural = (n, w) => n + " " + w + (n > 1 ? "s" : "");

$("month").innerHTML = D.mois.map((n, i) => `<option value="${i + 1}">${n}</option>`).join("");
function fillDays() {
  const m = +$("month").value, cur = +$("day").value || 1;
  $("day").innerHTML = Array.from({ length: DIM[m - 1] }, (_, i) => `<option value="${i + 1}">${i + 1}</option>`).join("");
  $("day").value = Math.min(cur, DIM[m - 1]);
}

function item(r, showDate) {
  const stars = "★".repeat(r[5]) + "☆".repeat(5 - r[5]);
  return `<div class="card ev"><div class="meta"><span class="yr">${r[2]}</span>${showDate ? `<span>${label(+r[1].slice(0, 2), +r[1].slice(2))}</span>` : ""}
    <span class="stars" title="intérêt ${r[5]}/5">${stars}</span><span class="tone-${r[6]}">ton ${TONE[r[6]]}</span>
    ${r[7].map(c => `<span class="tag">${esc(c.replace(/_/g, " "))}</span>`).join("")}${r[8] ? `<span class="approx">jour peut-être approximatif</span>` : ""}</div>
    <h3>${esc(r[3])}</h3><p>${esc(r[4])}</p></div>`;
}

function render() {
  const m = +$("month").value, d = +$("day").value, w = +$("win").value, min = +$("min").value, c = doy(m, d);
  let rows = [];
  for (let k = -w; k <= w; k++) { const [mm, dd] = fromDoy(c + k); rows = rows.concat(byKey.get(key(mm, dd)) || []); }
  rows = rows.filter(r => r[5] >= min);
  const order = (a, b) => b[5] - a[5] || a[2] - b[2];
  const sure = rows.filter(r => !r[8]).sort(order), fuzzy = rows.filter(r => r[8]).sort(order);
  const when = label(m, d) + (w ? ` ± ${w} jours` : "");
  if (sure.length) {
    const ys = sure.map(r => r[2]);
    $("sum").textContent = `${when} : ${plural(sure.length, "événement")} à date sûre, de ${Math.min(...ys)} à ${Math.max(...ys)}${fuzzy.length ? `, plus ${fuzzy.length} au jour incertain` : ""}.`;
  } else {
    $("sum").textContent = `${when} : aucun événement à date sûre${fuzzy.length ? `, ${fuzzy.length} au jour incertain` : ""}.`;
  }
  const showDate = w > 0;
  let html = sure.map(r => item(r, showDate)).join("");
  if (!sure.length && !fuzzy.length) html = `<div class="card">Aucun texte pour ce jour dans les éphémérides (elles ont des lacunes) : essayez une fenêtre plus large.</div>`;
  if (fuzzy.length) html += `<details class="more"${sure.length ? "" : " open"}><summary>${plural(fuzzy.length, "texte")} au jour peut-être approximatif</summary>${fuzzy.map(r => item(r, showDate)).join("")}</details>`;
  $("out").innerHTML = html;
}

function setDate(m, d) { $("month").value = m; fillDays(); $("day").value = d; render(); }
$("month").addEventListener("change", () => { fillDays(); render(); });
for (const id of ["day", "win", "min"]) $(id).addEventListener("change", render);
$("today").addEventListener("click", () => { const t = new Date(); setDate(t.getMonth() + 1, t.getDate()); });
$("rand").addEventListener("click", () => {
  const ks = [...byKey.keys()].filter(k => byKey.get(k).some(r => !r[8] && r[5] >= 3));
  const k = ks[Math.floor(Math.random() * ks.length)]; setDate(+k.slice(0, 2), +k.slice(2));
});
const t = new Date(); setDate(t.getMonth() + 1, t.getDate());
"""


def build(data):
    return page_shell(
        META["title"],
        "Quel événement d'Air France est arrivé un 24 octobre ? Choisissez un jour : les textes des éphémérides de ce jour-là, d'année en année.",
        BODY,
        script=SCRIPT.replace("__DATA__", embed(prepare(data))),
    )
