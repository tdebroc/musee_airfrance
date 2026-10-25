"""La vie d'un avion : le parcours d'un appareil identifié par son immatriculation (commande → livraison → incident → retrait)."""
import re
from collections import Counter, defaultdict

from .common import embed, page_shell

META = {
    "slug": "vie-avion",
    "title": "La vie d'un avion",
    "description": "Suivre un appareil précis, de F-BPVA (Boeing 747) à F-BVFF (Concorde), par son immatriculation : commande, livraison, mise en service, accident, retrait.",
    "order": 8,
}

# Étapes d'une vie, dans l'ordre ; record et mention sont affichés mais ne comptent pas comme étape.
STAGES = ["commande", "livraison", "premier_vol", "mise_en_service", "exploitation", "accident", "retrait"]
EXTRA = ["record", "mention"]
VAGUE = {"air france", "boeing", "airbus", "douglas", "lockheed", "avion", "hydravion"}
REG = re.compile(r"^[A-Z]{1,2}-[A-Z0-9]{3,5}$")


def normalize(reg):
    """'F.BAZZ' → 'F-BAZZ', 'FGCDG' → 'F-GCDG' ; None si ce n'est pas une immatriculation (JD, 5RMAJ, « F-Bale »…)."""
    reg = reg.strip()
    if reg != reg.upper():
        return None
    reg = reg.replace(".", "-").replace(" ", "")
    if re.fullmatch(r"F[A-Z]{4}", reg):
        reg = "F-" + reg[1:]
    return reg if REG.match(reg) else None


def prepare(data):
    by_reg = defaultdict(list)
    for r in data.records():
        seen = set()
        for a in r["aircraft"]:
            reg = normalize(a["registration"]) if a.get("registration") else None
            if not reg or (reg, a["event"]) in seen:
                continue
            seen.add((reg, a["event"]))
            by_reg[reg].append((r, a))

    planes = []
    for reg, items in by_reg.items():
        models = Counter(a["family"] or a["model"] for _, a in items if (a["family"] or a["model"]) and (a["family"] or a["model"]).lower() not in VAGUE)
        model = models.most_common(1)[0][0] if models else "Type non précisé"
        names = Counter(a["name"] for _, a in items if a.get("name") and normalize(a["name"]) != reg and a["name"] != reg)
        mentions = []
        for r, a in sorted(items, key=lambda x: (x[0]["date"], x[0]["id"])):
            m = [r["date"], r["id"], a["event"], r["title"], r["summary"]]
            other = a["family"] or a["model"]
            if other and other != model and other.lower() not in VAGUE:
                m.append(other)
            if a["event"] == "accident" and r["casualties"]:
                m.append(("morts", r["casualties"]))
            mentions.append(m)
        stages = {s for _, _, s, *_ in mentions if s in STAGES}
        planes.append({
            "reg": reg, "model": model, "names": [n for n, _ in names.most_common(2)],
            "first": mentions[0][0], "last": mentions[-1][0],
            "k": len({m[1] for m in mentions}), "n": len(stages), "ev": mentions,
        })
    planes.sort(key=lambda p: (p["first"], p["reg"]))
    models = Counter(p["model"] for p in planes)
    return {"planes": planes, "models": [m for m, _ in models.most_common()], "stages": STAGES, "extra": EXTRA}


BODY = """
<div class="card ctl">
  <label>Rechercher <input type="search" id="q" placeholder="F-BPVA, Concorde, Émeraude…"></label>
  <label>Type <select id="model"><option value="">Tous</option></select></label>
  <label>Étapes de vie au moins <input type="range" id="minN" min="0" max="6" value="0"> <b id="minNv">0</b></label>
  <label><input type="checkbox" id="acc"> avec accident</label>
  <label><input type="checkbox" id="ret"> avec retrait</label>
  <span class="muted" id="count"></span>
</div>
<div class="split">
  <div class="card" id="list"></div>
  <div class="card" id="detail"><p class="muted">Choisissez un appareil dans la liste.</p></div>
</div>
<p class="muted">Matière : seuls les textes qui citent une immatriculation permettent de suivre un appareil. La date affichée est celle de l'éphéméride (souvent le jour de l'événement, parfois une rétrospective). Un retrait de série (« les 747-100 sont retirés ») cite plusieurs immatriculations d'un coup.</p>
<style>
.ctl { display:flex; flex-wrap:wrap; gap:18px; align-items:center; margin-bottom:14px; }
.ctl input[type=search], .ctl select { padding:5px 8px; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--ink); }
.muted { color:var(--muted); font-size:13px; }
.split { display:grid; grid-template-columns:minmax(260px,340px) 1fr; gap:14px; align-items:start; }
@media (max-width:760px) { .split { grid-template-columns:1fr; } }
#list { max-height:640px; overflow:auto; padding:6px; }
.item { display:block; width:100%; text-align:left; background:none; border:0; border-bottom:1px solid var(--line); padding:7px 8px; color:var(--ink); cursor:pointer; font:inherit; }
.item:hover, .item.on { background:var(--bg); }
.item b { font-family:ui-monospace,Menlo,monospace; } .item small { display:block; color:var(--muted); }
.steps { display:flex; flex-wrap:wrap; gap:6px; margin:12px 0; }
.step { flex:1 1 120px; border:1px dashed var(--line); border-radius:8px; padding:6px 8px; color:var(--muted); font-size:12px; }
.step.has { border:1px solid var(--accent); color:var(--ink); background:var(--bg); }
.step.has.acc { border-color:var(--accent2); }
.step b { display:block; font-size:13px; }
ol.tl { list-style:none; margin:0; padding:0 0 0 14px; border-left:2px solid var(--line); }
ol.tl li { position:relative; padding:0 0 12px 12px; }
ol.tl li::before { content:""; position:absolute; left:-21px; top:6px; width:10px; height:10px; border-radius:50%; background:var(--accent); }
ol.tl li.accident::before { background:var(--accent2); } ol.tl li.mention::before { background:var(--muted); opacity:.6; }
ol.tl .d { color:var(--muted); font-size:12px; } ol.tl .ev { font-size:12px; font-weight:600; margin-left:6px; color:var(--accent); }
ol.tl li.accident .ev { color:var(--accent2); } ol.tl p { margin:2px 0 0; font-size:13px; }
</style>
"""

SCRIPT = r"""
const D = __DATA__;
const EV = {commande:"Commande", livraison:"Livraison", premier_vol:"Premier vol", mise_en_service:"Mise en service", exploitation:"Exploitation", accident:"Accident", retrait:"Retrait", record:"Record", mention:"Mention"};
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const $ = id => document.getElementById(id);
const norm = s => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
D.planes.forEach(p => { p.hay = norm(p.reg + " " + p.model + " " + p.names.join(" ")); p.has = new Set(p.ev.map(e => e[2])); });
D.models.forEach(m => $("model").insertAdjacentHTML("beforeend", `<option>${esc(m)}</option>`));
let current = null;

function filtered() {
  const q = norm($("q").value.trim()), mo = $("model").value, minN = +$("minN").value;
  return D.planes.filter(p => (!q || p.hay.includes(q)) && (!mo || p.model === mo) && p.n >= minN
    && (!$("acc").checked || p.has.has("accident")) && (!$("ret").checked || p.has.has("retrait")));
}

function drawList() {
  $("minNv").textContent = $("minN").value;
  const l = filtered();
  $("count").textContent = l.length + " appareil" + (l.length > 1 ? "s" : "") + " sur " + D.planes.length;
  $("list").innerHTML = l.map(p => `<button class="item${p === current ? " on" : ""}" data-r="${p.reg}"><b>${p.reg}</b> ${esc(p.names[0] || "")}<small>${esc(p.model)} · ${p.first.slice(0, 4)}${p.last.slice(0, 4) !== p.first.slice(0, 4) ? "–" + p.last.slice(0, 4) : ""} · ${p.k} texte${p.k > 1 ? "s" : ""}</small></button>`).join("")
    || '<p class="muted" style="padding:8px">Aucun appareil ne correspond.</p>';
}

function show(p) {
  current = p;
  const steps = D.stages.map(s => {
    const e = p.ev.find(x => x[2] === s);
    return `<div class="step${e ? " has" : ""}${e && s === "accident" ? " acc" : ""}"><b>${EV[s]}</b>${e ? e[0] : "non citée"}</div>`;
  }).join("");
  const tl = p.ev.map(e => {
    const extra = e.slice(5).map(x => Array.isArray(x) ? ` · ${x[1]} morts` : ` · cité comme « ${esc(x)} »`).join("");
    return `<li class="${e[2]}"><span class="d">${e[0]}</span><span class="ev">${EV[e[2]]}${extra}</span><p><b>${esc(e[3])}</b><br>${esc(e[4])}</p></li>`;
  }).join("");
  $("detail").innerHTML = `<h2 style="margin:0">${p.reg} <span class="muted">${esc(p.model)}${p.names.length ? " · « " + p.names.map(esc).join(" », « ") + " »" : ""}</span></h2>
    <div class="steps">${steps}</div><ol class="tl">${tl}</ol>`;
  drawList();
}

$("list").addEventListener("click", e => { const b = e.target.closest(".item"); if (b) show(D.planes.find(p => p.reg === b.dataset.r)); });
["q", "model", "minN", "acc", "ret"].forEach(id => $(id).addEventListener("input", drawList));
// départ : l'appareil à la vie la plus complète
show(D.planes.slice().sort((a, b) => b.n - a.n || b.k - a.k)[0]);
"""


def build(data):
    payload = prepare(data)
    n2 = sum(1 for p in payload["planes"] if p["n"] >= 2)
    lead = (f"{len(payload['planes'])} appareils sont cités par leur immatriculation dans les textes ; {n2} d'entre eux ont au moins deux étapes "
            "de vie documentées. Cherchez une immatriculation, un nom (« Émeraude ») ou un type, puis suivez son parcours.")
    return page_shell(META["title"], lead, BODY, script=SCRIPT.replace("__DATA__", embed(payload)))
