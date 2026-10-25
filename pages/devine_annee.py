"""« Devine l'année » : quiz à partir d'un texte d'éphéméride sans année, score selon l'écart."""
import re

from .common import embed, page_shell

META = {
    "slug": "devine-annee",
    "title": "Devine l'année",
    "description": "Un texte d'archive d'Air France, sans aucune date : en quelle année cela s'est-il passé ? Cinq manches, des points selon l'écart.",
    "order": 14,
}

YEAR = re.compile(r"(?<!\d)(1[89]\d\d|20[0-3]\d)(?!\d)")
HINT = re.compile(r"anniversaire|centenaire|cinquantenaire|bicentenaire|il y a \d+ ans|\b\d+\s*ans\s+(plus tôt|après|auparavant)", re.I)
MAXLEN = 900


def prepare(data):
    """Un texte = [id, année, texte, titre, résumé, intérêt]. Intérêt ≥ 4, aucune année dans le texte ni le titre,
    pas d'allusion à un anniversaire (qui trahirait l'époque), texte de longueur raisonnable."""
    rows = []
    for rec in data.records():
        if rec["interest"] < 4:
            continue
        text = data.text(rec["id"]).replace("\r\n", "\n").replace("\r", "\n")
        if YEAR.search(text) or YEAR.search(rec["title"]) or HINT.search(text) or len(text) > MAXLEN or len(text) < 80:
            continue
        rows.append([rec["id"], int(rec["date"][:4]), text, rec["title"], rec["summary"], rec["interest"]])
    return {"rows": rows}


BODY = """
<style>
.bar { display:flex; justify-content:space-between; flex-wrap:wrap; gap:10px; color:var(--muted); font-size:14px; margin-bottom:12px; }
.bar b { color:var(--ink); }
.txt { font-size:16.5px; line-height:1.6; white-space:pre-wrap; margin:0 0 16px; }
.guess { display:flex; flex-wrap:wrap; gap:14px; align-items:center; }
.guess input[type=range] { flex:1 1 320px; accent-color:var(--accent); }
.guess .big { font-size:28px; font-weight:700; color:var(--accent); min-width:70px; }
button.go { font:inherit; padding:7px 18px; border:0; border-radius:6px; background:var(--accent); color:var(--bg); cursor:pointer; font-weight:600; }
button.go:hover { opacity:.9; }
.res { margin-top:16px; padding-top:14px; border-top:1px solid var(--line); }
.res .pts { font-size:22px; font-weight:700; } .res .ans { color:var(--accent2); font-weight:700; }
.scale { position:relative; height:34px; margin:14px 0 4px; }
.scale .ln { position:absolute; left:0; right:0; top:16px; height:2px; background:var(--line); }
.scale .pin { position:absolute; top:6px; width:12px; height:22px; margin-left:-6px; border-radius:3px; }
.scale .pin.g { background:var(--accent); } .scale .pin.t { background:var(--accent2); }
.scale .lab { position:absolute; top:-8px; font-size:11px; transform:translateX(-50%); white-space:nowrap; }
.hist { display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
.hist span { border:1px solid var(--line); border-radius:8px; padding:2px 10px; font-size:13px; }
.note { color:var(--muted); font-size:12.5px; margin-top:14px; }
.hidden { display:none; }
</style>
<div class="card" id="game">
  <div class="bar"><span>Manche <b id="rn">1</b> / <b id="rt">5</b></span><span>Score : <b id="sc">0</b></span></div>
  <p class="txt" id="txt"></p>
  <div class="guess" id="guess">
    <span class="big" id="gy"></span>
    <input type="range" id="sl" aria-label="Année proposée">
    <button class="go" id="ok">Valider</button>
  </div>
  <div class="res hidden" id="res"></div>
</div>
<p class="note" id="note"></p>
"""

SCRIPT = r"""
const D = __DATA__;
const ENT = { "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;" };
const esc = s => String(s).replace(/[&<>"]/g, c => ENT[c]);
const $ = id => document.getElementById(id);
const ROUNDS = 5, MIN = 1900, MAX = 2022;
const points = gap => Math.round(1000 * Math.exp(-gap / 12));   // 0 an : 1000 · 5 ans : 659 · 20 ans : 189 · 50 ans : 16
let order, round, score, cur, answered, hist;

$("sl").min = MIN; $("sl").max = MAX; $("sl").step = 1;
$("sl").addEventListener("input", () => { $("gy").textContent = $("sl").value; });
$("note").textContent = `${D.rows.length} textes d'intérêt ≥ 4 dont ni le titre ni le corps ne contiennent d'année (ni allusion à un anniversaire). ` +
  `Barème : 1000 points pour l'année exacte, 659 à 5 ans d'écart, 189 à 20 ans, moins de 20 au-delà de 50 ans. ` +
  `L'année est celle de la date de l'éphéméride, pas toujours celle de l'événement (commémorations, rétrospectives).`;

function shuffle(a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }

function newGame() {
  // tirage réparti sur les époques : une manche par tranche de rang d'année, pour ne pas tomber 5 fois dans les années 2000
  const sorted = D.rows.slice().sort((a, b) => a[1] - b[1]);
  const per = sorted.length / ROUNDS;
  order = shuffle(Array.from({ length: ROUNDS }, (_, i) => sorted[Math.floor(i * per + Math.random() * per)]));
  round = 0; score = 0; hist = [];
  show();
}

function show() {
  cur = order[round]; answered = false;
  $("rn").textContent = round + 1; $("rt").textContent = ROUNDS; $("sc").textContent = score;
  $("txt").textContent = cur[2];
  $("sl").value = 1960; $("gy").textContent = 1960;
  $("guess").classList.remove("hidden"); $("res").classList.add("hidden");
}

function scale(g, t) {
  const pos = y => ((y - MIN) / (MAX - MIN) * 100).toFixed(2) + "%";
  return `<div class="scale"><div class="ln"></div>
    <div class="pin g" style="left:${pos(g)}"></div><div class="lab" style="left:${pos(g)};color:var(--accent)">${g}</div>
    <div class="pin t" style="left:${pos(t)};opacity:.9"></div><div class="lab" style="left:${pos(t)};top:30px;color:var(--accent2)">${t}</div></div>`;
}

function validate() {
  if (answered) return;
  answered = true;
  const g = +$("sl").value, t = cur[1], gap = Math.abs(g - t), p = points(gap);
  score += p; hist.push([g, t, p]);
  $("sc").textContent = score;
  const last = round === ROUNDS - 1;
  $("guess").classList.add("hidden");
  $("res").classList.remove("hidden");
  $("res").innerHTML = `<div><span class="pts">+${p} points</span> — vous : ${g}, réponse : <span class="ans">${t}</span> (${gap === 0 ? "exact !" : "écart de " + gap + " an" + (gap > 1 ? "s" : "")})</div>
    ${scale(g, t)}<h3 style="margin:22px 0 4px">${esc(cur[3])}</h3><p style="margin:0 0 14px;color:var(--muted)">${esc(cur[4])}</p>
    <button class="go" id="next">${last ? "Voir le résultat" : "Manche suivante"}</button>`;
  $("next").addEventListener("click", () => { if (last) end(); else { round++; show(); } });
}

function end() {
  $("txt").textContent = "";
  $("res").innerHTML = `<div class="pts">Score final : ${score} / ${ROUNDS * 1000}</div>
    <div class="hist">${hist.map((h, i) => `<span>${i + 1}. ${h[0]} → <b>${h[1]}</b> (+${h[2]})</span>`).join("")}</div>
    <p style="margin:14px 0"><button class="go" id="again">Rejouer</button></p>`;
  $("again").addEventListener("click", newGame);
}

$("ok").addEventListener("click", validate);
newGame();
"""


def build(data):
    return page_shell(
        META["title"],
        "Un texte d'archive d'Air France, sans aucune année. À vous de la deviner : plus vous êtes proche, plus vous marquez de points.",
        BODY,
        script=SCRIPT.replace("__DATA__", embed(prepare(data))),
    )
