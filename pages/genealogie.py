"""Généalogie des compagnies : fusions, créations, absorptions et filiales autour d'Air France, 1909-2022."""
import re
import unicodedata
from collections import Counter, defaultdict

from .common import embed, page_shell

META = {
    "slug": "genealogie",
    "title": "Généalogie des compagnies",
    "description": "De la Compagnie Générale Transaérienne (1909) à Air France-KLM : qui a fusionné, absorbé, créé ou cédé quoi, chaque lien renvoyant au texte qui l'atteste.",
    "order": 7,
}

END_YEAR = 2023.0

# Nœuds : row = ligne d'affichage (deux nœuds de même row se suivent : renommage), born/died = id du texte qui date la
# naissance/la fin ; born_approx = le texte n'est que la première trace ; names = noms servant à calculer les
# premières/dernières mentions quand born/died manquent ; open = toujours actif en 2022 ; group = couleur.
NODES = [
    dict(id="transaerienne", label="Cie Générale Transaérienne", row=0, born=5, died=24, group="pionnier", names=["Compagnie Générale Transaérienne"]),
    dict(id="cma", label="Messageries Aériennes", row=1, born=24, born_approx=True, died=78, group="pionnier"),
    dict(id="grands_express", label="Grands Express Aériens", row=2, born=78, born_approx=True, died=78, group="pionnier"),
    dict(id="aeronavale", label="Aéronavale", row=3, born=141, born_approx=True, died=141, group="pionnier"),
    dict(id="air_union", label="Air Union", row=4, born=78, died=238, group="pionnier"),
    dict(id="farman", label="Lignes Farman", row=5, born=65, born_approx=True, died=65, group="pionnier"),
    dict(id="sgta", label="SGTA", row=5, born=65, died=238, group="pionnier"),
    dict(id="cidna", label="Franco-Roumaine / CIDNA", row=6, died=238, group="pionnier", names=["Franco-Roumaine", "CIDNA"], max_year=1933),
    dict(id="air_orient", label="Air Orient", row=7, died=238, group="pionnier", names=["Air Orient"], max_year=1933),
    dict(id="scela", label="SCELA (compagnie provisoire)", row=8, born=226, died=239, group="pionnier"),
    dict(id="cgea", label="CGEA (Latécoère)", row=9, died=152, group="pionnier", names=["CGEA"]),
    dict(id="aeropostale", label="Aéropostale", row=9, born=152, died=234, group="pionnier"),
    dict(id="transafricaine", label="Transafricaine d'Aviation", row=10, born=179, died=263, group="outremer"),
    dict(id="regie_afrique", label="Régie Air Afrique", row=10, born=263, group="outremer", names=["Régie Air Afrique"], max_year=1946),
    dict(id="regie_malgache", label="Régie Malgache", row=11, died=444, group="outremer", names=["Régie Malgache"], max_year=1937),
    dict(id="air_france", label="Air France", row=12, born=238, open=True, group="af"),
    dict(id="rlaf", label="RLAF", row=13, born=480, group="af", names=["RLAF"], max_year=1949),
    dict(id="air_bleu", label="Air Bleu", row=14, born=326, group="af", names=["Air Bleu"], max_year=1949),
    dict(id="aeromaritime", label="Aéromaritime", row=15, born=321, group="outremer", names=["Aéromaritime"], max_year=1995),
    dict(id="tai", label="TAI", row=16, born=529, died=2907, group="prive"),
    dict(id="uat", label="UAT", row=17, died=2907, group="prive", names=["UAT", "U.A.T."]),
    dict(id="aigle_azur", label="Aigle Azur", row=18, died=1553, group="prive", names=["Aigle Azur"], max_year=1955),
    dict(id="uta", label="UTA", row=19, born=2907, died=5818, group="prive"),
    dict(id="af_afrique", label="Air Afrique (AF + UAT)", row=20, born=2378, died=2557, group="outremer"),
    dict(id="air_afrique", label="Air Afrique (multinationale)", row=20, born=2557, died=7020, group="outremer"),
    dict(id="air_vietnam", label="Air Vietnam", row=21, born=957, group="outremer", names=["Air Vietnam"], max_year=1980),
    dict(id="air_inter", label="Air Inter", row=22, born=1472, died=6220, group="af"),
    dict(id="air_france_europe", label="Air France Europe", row=22, born=6220, died=6476, group="af"),
    dict(id="groupe_af", label="Groupe Air France SA", row=23, born=6032, died=6476, group="af"),
    dict(id="air_charter", label="Air Charter", row=24, died=6667, group="af", names=["Air Charter"]),
    dict(id="tat", label="TAT", row=25, group="prive", names=["TAT"], max_year=1997),
    dict(id="sea", label="Sté d'exploitation Aéropostale", row=26, born=5587, died=7029, group="af"),
    dict(id="jet_tours", label="Jet Tours", row=27, died=6577, group="af", names=["Jet Tours"]),
    dict(id="brit_air", label="Brit Air", row=28, died=8718, group="regional", names=["Brit Air", "Britair"], max_year=2013),
    dict(id="regional_airlines", label="Regional Airlines", row=29, died=6923, group="regional", names=["Regional Airlines"], max_year=2001),
    dict(id="proteus", label="Proteus Airlines", row=30, died=6923, group="regional", names=["Proteus Airlines"], max_year=2001),
    dict(id="flandre", label="Flandre Air", row=31, died=6923, group="regional", names=["Flandre Air"], max_year=2001),
    dict(id="regional", label="Régional", row=32, born=6923, died=8718, group="regional"),
    dict(id="airlinair", label="Airlinair", row=33, died=8718, group="regional", names=["Airlinair"], max_year=2013),
    dict(id="hop", label="HOP! (Air France HOP)", row=34, born=8718, open=True, group="regional"),
    dict(id="klm", label="KLM", row=35, open=True, group="klm", names=["KLM"]),
    dict(id="af_klm", label="Groupe Air France-KLM", row=36, born=7307, open=True, group="klm"),
    dict(id="transavia", label="Transavia France", row=37, born=10425, open=True, group="klm"),
    dict(id="joon", label="Joon", row=38, born=9227, died=9807, group="klm"),
    dict(id="atlas", label="Groupe ATLAS", row=39, born=3654, group="alliance", names=["ATLAS"], max_year=1990),
    dict(id="kssu", label="Groupe KSSU", row=40, born=3865, group="alliance", names=["KSSU"], max_year=1990),
    dict(id="skyteam", label="Alliance SkyTeam", row=41, open=True, group="alliance", names=["SkyTeam"], min_year=2000),
]

# Liens : (source, cible, type, id du texte). La date du lien est celle du texte.
EDGES = [
    ("transaerienne", "cma", "absorption", 24),
    ("cma", "air_union", "fusion", 78),
    ("grands_express", "air_union", "fusion", 78),
    ("aeronavale", "air_union", "absorption", 141),
    ("farman", "sgta", "renommage", 65),
    ("air_union", "air_france", "fusion", 238),
    ("sgta", "air_france", "fusion", 238),
    ("cidna", "air_france", "fusion", 238),
    ("air_orient", "air_france", "fusion", 238),
    ("air_union", "scela", "fusion", 226),
    ("sgta", "scela", "fusion", 226),
    ("cidna", "scela", "fusion", 226),
    ("air_orient", "scela", "fusion", 226),
    ("scela", "air_france", "renommage", 239),
    ("cgea", "aeropostale", "renommage", 152),
    ("aeropostale", "air_france", "absorption", 234),
    ("transafricaine", "regie_afrique", "renommage", 263),
    ("regie_malgache", "regie_afrique", "absorption", 444),
    ("regie_afrique", "rlaf", "participation", 480),
    ("air_france", "rlaf", "participation", 480),
    ("air_france", "air_bleu", "participation", 439),
    ("air_france", "air_afrique", "participation", 6956),
    ("air_france", "af_afrique", "fusion", 2378),
    ("uat", "af_afrique", "fusion", 2378),
    ("af_afrique", "air_afrique", "renommage", 2557),
    ("uta", "aeromaritime", "participation", 5368),
    ("air_france", "air_vietnam", "creation", 957),
    ("uat", "air_vietnam", "creation", 957),
    ("uat", "aigle_azur", "absorption", 1553),
    ("tai", "uta", "fusion", 2907),
    ("uat", "uta", "fusion", 2907),
    ("air_france", "air_inter", "participation", 2781),
    ("air_france", "uta", "participation", 5370),
    ("uta", "air_france", "absorption", 5818),
    ("air_inter", "air_france_europe", "renommage", 6220),
    ("air_france_europe", "air_france", "absorption", 6476),
    ("groupe_af", "air_france", "fusion", 6476),
    ("groupe_af", "air_inter", "participation", 6073),
    ("air_charter", "air_france", "absorption", 6667),
    ("air_france", "tat", "participation", 5309),
    ("air_france", "tat", "cession", 5628),
    ("air_france", "sea", "creation", 5587),
    ("tat", "sea", "creation", 5587),
    ("air_france", "sea", "participation", 6857),
    ("air_france", "jet_tours", "cession", 6577),
    ("air_france", "brit_air", "participation", 6884),
    ("regional_airlines", "regional", "fusion", 6923),
    ("proteus", "regional", "fusion", 6923),
    ("flandre", "regional", "fusion", 6923),
    ("brit_air", "hop", "fusion", 8718),
    ("regional", "hop", "fusion", 8718),
    ("airlinair", "hop", "fusion", 8718),
    ("klm", "af_klm", "fusion", 7307),
    ("air_france", "af_klm", "fusion", 7307),
    ("af_klm", "transavia", "creation", 10425),
    ("air_france", "joon", "creation", 9227),
    ("joon", "air_france", "absorption", 9807),
    ("air_france", "atlas", "alliance", 3654),
    ("uta", "kssu", "alliance", 3865),
    ("klm", "kssu", "alliance", 3865),
    ("air_france", "skyteam", "alliance", 8842),
]

# Repères (ticks) sur une barre : (nœud, id du texte, libellé court).
MARKS = [
    ("air_france", 684, "Compagnie Nationale (1948)"),
    ("air_france", 5370, "contrôle d'UTA et d'Air Inter (1990)"),
    ("air_france", 7319, "OPE sur KLM (2004)"),
    ("air_inter", 2060, "exploitation suspendue (1958)"),
    ("air_inter", 2345, "reprise (1960)"),
    ("air_inter", 5370, "Air France actionnaire majoritaire (1990)"),
    ("regie_afrique", 431, "texte : « Air Afrique » née de la fusion (1937)"),
    ("hop", 9742, "rebaptisé Air France HOP (2019)"),
    ("sea", 6857, "Air France actionnaire unique (2000)"),
]

NOTES = {
    "air_union": "Ne pas confondre avec le projet européen « Air Union » de 1959-1962 (textes 2156-2802), sans rapport : il n'est pas rattaché à ce nœud.",
    "uta": "Issue de la fusion UAT + TAI (1963), contrôlée par Air France en 1990, absorbée en décembre 1992.",
    "air_afrique": "Société multinationale africaine créée en 1961 ; elle reprend le nom de l'« Air Afrique » commune à Air France et à l'UAT (1960).",
    "regie_afrique": "Le texte 431 (1937) décrit une fusion créant « Air Afrique » alors que le texte 444 (sept. 1937) montre la Régie Air Afrique absorbant la Régie Malgache : les deux sont gardés tels quels.",
    "scela": "Société provisoire de 1933 pour exploiter le réseau d'État avant la compagnie unique ; le texte 239 la nomme « SECLA » (graphie probable erronée).",
    "kssu": "KLM, SAS, Swissair, UTA (texte 3865) : lien affiché pour KLM et UTA seulement.",
    "atlas": "Alitalia, Air France, DLH, Sabena (texte 3654) : lien affiché pour Air France seulement.",
    "skyteam": "Début = première mention dans les textes (2000) ; Air France y est dite « membre fondateur » (texte 8842).",
}

TYPES = {
    "fusion": "Fusion / regroupement",
    "absorption": "Absorption / reprise",
    "renommage": "Changement de nom",
    "creation": "Création d'une filiale",
    "participation": "Prise de participation",
    "cession": "Cession",
    "alliance": "Alliance",
}

# Variantes d'orthographe à fusionner pour l'index des compagnies.
ALIAS = {
    "air france klm": "Air France-KLM", "klm royal dutch airlines": "KLM", "delta": "Delta Air Lines",
    "china southern": "China Southern Airlines", "transavia france": "Transavia", "hop air france": "HOP!",
    "britair": "Brit Air", "csa": "CSA Czech Airlines", "czech airlines": "CSA Czech Airlines",
    "northwest": "Northwest Airlines", "continental": "Continental Airlines", "japan air lines": "Japan Airlines",
    "regional": "Régional", "u a t": "UAT", "deutsche lufthansa": "Lufthansa", "dlh": "Lufthansa",
    "regional airlines": "Regional Airlines", "airbus industrie": "Airbus", "tarom": "Tarom", "titre": None,
}


def norm(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def clean(html):
    t = re.sub(r"<br\s*/?>|</p>", "\n", html)
    t = re.sub(r"<[^>]+>", "", t).replace("&nbsp;", " ").replace("&amp;", "&")
    t = re.sub(r"jour et mois à rechercher", "", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def yearf(date):
    y, m, d = (int(x) for x in date.split("-"))
    return round(y + ((m - 1) * 30.4 + d - 1) / 365.0, 3)


def build(data):
    recs = data.enriched
    by_name = defaultdict(list)  # nom exact -> dates
    for r in recs.values():
        for c in r["companies"]:
            by_name[c].append(r["date"])

    def mentions(names, lo=None, hi=None):
        ds = [d for n in names for d in by_name.get(n, [])]
        if lo:
            ds = [d for d in ds if yearf(d) >= lo]
        if hi:
            ds = [d for d in ds if yearf(d) <= hi + 1]
        return sorted(ds)

    used_ids = set()

    def use(i):
        assert i in recs, f"texte {i} introuvable"
        used_ids.add(i)
        return i

    nodes = []
    for n in NODES:
        names = n.get("names", [])
        start, s_approx, s_src = None, False, None
        if n.get("born"):
            s_src = use(n["born"])
            start, s_approx = yearf(recs[s_src]["date"]), bool(n.get("born_approx"))
        else:
            ds = mentions(names, n.get("min_year"), n.get("max_year"))
            assert ds, f"aucune mention pour {n['id']}"
            start, s_approx = yearf(ds[0]), True
        end, e_approx, e_src = None, False, None
        if n.get("died"):
            e_src = use(n["died"])
            end = yearf(recs[e_src]["date"])
        elif n.get("open"):
            end = END_YEAR
        else:
            ds = mentions(names, n.get("min_year"), n.get("max_year")) if names else []
            end = yearf(ds[-1]) if ds else start
            e_approx = True
        end = max(end, start)
        # textes d'entreprise_capital citant le nœud (hors dates absurdes), pour le panneau
        related = []
        if names:
            lo, hi = start - 1, (end + 1 if not n.get("open") else 99999)
            for r in recs.values():
                if "entreprise_capital" in r["categories"] and any(c in names for c in r["companies"]) and lo <= yearf(r["date"]) <= hi:
                    related.append(r)
            related.sort(key=lambda r: (-r["interest"], r["date"]))
            related = [use(r["id"]) for r in related[:12]]
            related.sort(key=lambda i: recs[i]["date"])
        nodes.append({
            "id": n["id"], "label": n["label"], "row": n["row"], "group": n["group"], "start": start, "end": end,
            "sa": s_approx, "ea": e_approx, "born": s_src, "died": e_src, "related": related,
            "note": NOTES.get(n["id"], ""), "open": bool(n.get("open")),
        })
    ids = {n["id"] for n in nodes}
    edges = []
    for src, dst, typ, tid in EDGES:
        assert src in ids and dst in ids and typ in TYPES, (src, dst, typ)
        edges.append({"s": src, "d": dst, "t": typ, "x": yearf(recs[use(tid)]["date"]), "id": tid})
    marks = [{"n": n, "x": yearf(recs[use(t)]["date"]), "id": t, "l": l} for n, t, l in MARKS]

    # --- index de toutes les compagnies (textes de catégorie entreprise_capital) ---
    groups = defaultdict(lambda: {"raw": Counter(), "all": [], "cap": []})
    for r in recs.values():
        seen = set()
        for c in r["companies"]:
            k = norm(c)
            if not k or k in seen:
                continue
            seen.add(k)
            k = norm(ALIAS[k]) if ALIAS.get(k) else k
            g = groups[k]
            g["raw"][ALIAS.get(norm(c)) or c] += 1
            g["all"].append(r["date"])
            if "entreprise_capital" in r["categories"]:
                g["cap"].append(r)
    index = []
    for k, g in groups.items():
        if len(g["cap"]) < 3 or k == "air france":
            continue
        caps = sorted(g["cap"], key=lambda r: (-r["interest"], r["date"]))[:8]
        caps = sorted((use(r["id"]) for r in caps), key=lambda i: recs[i]["date"])
        index.append([g["raw"].most_common(1)[0][0], len(g["all"]), len(g["cap"]), min(g["all"])[:4], max(g["all"])[:4], caps])
    index.sort(key=lambda r: (-r[2], -r[1]))

    texts = {}
    for i in sorted(used_ids):
        r = recs[i]
        full = clean(data.text(i)) if i in data.raw else ""
        texts[i] = [r["date"], r["title"], r["summary"], full[:700] + ("…" if len(full) > 700 else ""), r["interest"]]

    payload = {"nodes": nodes, "edges": edges, "marks": marks, "types": TYPES, "texts": texts, "index": index}
    return page_shell(
        META["title"],
        "Chaque barre est une compagnie, de sa naissance à sa disparition ; chaque trait vertical est un lien (fusion, absorption, filiale…) daté et attesté par un texte des éphémérides. Cliquez sur une barre ou un lien pour lire les sources.",
        BODY, HEAD, SCRIPT.replace("__DATA__", embed(payload)),
    )


HEAD = """<script src="https://cdn.jsdelivr.net/npm/d3@7"></script><style>
.ctl { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin-bottom:10px; }
.ctl button, .ctl input { font:inherit; padding:5px 12px; border:1px solid var(--line); border-radius:8px; background:var(--card); color:var(--ink); cursor:pointer; }
.ctl button.on { background:var(--accent); color:var(--bg); border-color:var(--accent); }
.ctl input { cursor:text; min-width:200px; }
.legend { display:flex; flex-wrap:wrap; gap:6px 16px; font-size:13px; color:var(--muted); margin:4px 0 10px; }
.legend span.sw { display:inline-block; width:26px; vertical-align:middle; margin-right:5px; }
.legend .gp { display:inline-block; width:12px; height:12px; border-radius:3px; vertical-align:middle; margin-right:5px; }
.layout { display:grid; grid-template-columns:minmax(0,1fr) 340px; gap:16px; align-items:start; }
@media (max-width:1000px) { .layout { grid-template-columns:1fr; } }
#chart { overflow:auto; max-height:80vh; padding:6px; }
#panel { position:sticky; top:10px; max-height:85vh; overflow:auto; font-size:14px; }
#panel h3 { margin:0 0 4px; font-size:17px; } #panel .meta { color:var(--muted); margin-bottom:8px; }
.src { border-top:1px solid var(--line); padding:8px 0; } .src b { display:block; } .src .d { color:var(--muted); font-size:12px; }
.src details summary { cursor:pointer; color:var(--accent); font-size:13px; } .src p { margin:6px 0 0; white-space:pre-line; font-size:13px; }
.note { background:var(--bg); border-left:3px solid var(--accent2); padding:6px 10px; margin:8px 0; font-size:13px; }
.bar { cursor:pointer; } .bar:hover { stroke:var(--ink); stroke-width:1.5; }
.lnk { cursor:pointer; } .lnk-hit { stroke:transparent; stroke-width:12; fill:none; }
text.lab { font-size:11.5px; fill:var(--ink); paint-order:stroke; stroke:var(--card); stroke-width:3px; pointer-events:none; }
text.axis { font-size:11px; fill:var(--muted); } .grid line { stroke:var(--line); }
.g-pionnier { fill:#2a78d6; } .g-af { fill:#0b3d91; } .g-prive { fill:#eb6834; } .g-outremer { fill:#2f9e44; }
.g-regional { fill:#9c36b5; } .g-klm { fill:#0c8599; } .g-alliance { fill:#868e96; }
@media (prefers-color-scheme: dark) { .g-af { fill:#7fb0ff; } .g-pionnier { fill:#4d9aff; } .g-prive { fill:#ff8a5c; } .g-outremer { fill:#51cf66; } .g-regional { fill:#d17df0; } .g-klm { fill:#3bc9db; } .g-alliance { fill:#adb5bd; } }
.tp-fusion { stroke:#2a78d6; } .tp-absorption { stroke:#e8590c; } .tp-renommage { stroke:#868e96; } .tp-creation { stroke:#2f9e44; }
.tp-participation { stroke:#9c36b5; } .tp-cession { stroke:#c92a2a; } .tp-alliance { stroke:#0c8599; }
table.idx { border-collapse:collapse; width:100%; font-size:14px; } table.idx th, table.idx td { padding:5px 8px; border-bottom:1px solid var(--line); text-align:left; }
table.idx th { cursor:pointer; color:var(--muted); font-weight:600; } table.idx tr.row { cursor:pointer; } table.idx tr.row:hover { background:var(--bg); }
#tip { position:fixed; pointer-events:none; background:var(--card); color:var(--ink); border:1px solid var(--line); border-radius:6px; padding:4px 8px; font-size:12px; display:none; z-index:9; max-width:300px; }
</style>"""

BODY = """
<div class="ctl" id="tabs"><button data-tab="graph" class="on">Généalogie</button><button data-tab="index">Toutes les compagnies citées</button></div>
<div id="v-graph">
 <div class="ctl" id="periods"></div>
 <div class="ctl"><input type="search" id="q" placeholder="Chercher une compagnie…"><span id="count" style="color:var(--muted);font-size:13px"></span></div>
 <div class="legend" id="legend-groups"></div><div class="legend" id="legend-types"></div>
 <div class="layout"><div class="card" id="chart"></div><div class="card" id="panel"><p style="color:var(--muted)">Cliquez sur une barre (compagnie) ou un trait (lien) pour voir le texte qui l'atteste.</p></div></div>
 <p style="color:var(--muted);font-size:13px;max-width:90ch">Lecture : une barre pleine commence à un événement daté ; une barre <i>pointillée</i> à son début ou à sa fin signifie que la date vient de la première ou de la dernière mention dans les textes (approximation). Les liens et les dates de naissance ou de fin ne viennent que des textes ; une compagnie sans texte qui l'atteste n'apparaît pas ici (voir l'onglet « Toutes les compagnies »).</p>
</div>
<div id="v-index" style="display:none">
 <div class="ctl"><input type="search" id="q2" placeholder="Filtrer…"><span style="color:var(--muted);font-size:13px">Compagnies citées dans au moins 3 textes d'entreprise et de capital (variantes d'orthographe regroupées).</span></div>
 <div class="card"><table class="idx" id="idx"></table></div>
</div>
<div id="tip"></div>"""

SCRIPT = r"""
const D = __DATA__;
const GROUPS = {pionnier:"Pionniers avant 1933", af:"Air France et son groupe", prive:"Compagnies privées", outremer:"Afrique, Outre-mer, Asie", regional:"Régionales", klm:"KLM et Air France-KLM", alliance:"Alliances"};
const DASH = {fusion:"", absorption:"", renommage:"2 3", creation:"", participation:"6 3", cession:"6 2 1 2", alliance:"10 4"};
const WIDTH = {absorption:3, fusion:2, creation:2, renommage:2, participation:2, cession:2, alliance:2};
const PERIODS = [["Tout (1909-2022)",1905,2024],["Avant 1946",1905,1947],["1946-1990",1945,1991],["1990-2022",1989,2024]];
const nodeById = Object.fromEntries(D.nodes.map(n => [n.id, n]));
const fmtY = x => Math.floor(x);
const tip = document.getElementById("tip");
function showTip(ev, html) { tip.innerHTML = html; tip.style.display = "block"; tip.style.left = (ev.clientX + 12) + "px"; tip.style.top = (ev.clientY + 12) + "px"; }
function hideTip() { tip.style.display = "none"; }
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

let period = PERIODS[0], query = "", selected = null;

// légendes
document.getElementById("legend-groups").innerHTML = Object.entries(GROUPS).map(([k,v]) => `<span><span class="gp g-${k}"></span>${v}</span>`).join("");
document.getElementById("legend-types").innerHTML = Object.entries(D.types).map(([k,v]) =>
  `<span><svg class="sw" height="10" width="26"><line x1="0" x2="26" y1="5" y2="5" class="tp-${k}" stroke-width="${WIDTH[k]}" stroke-dasharray="${DASH[k]}"/></svg>${v}</span>`).join("");
const pEl = document.getElementById("periods");
PERIODS.forEach((p, i) => { const b = document.createElement("button"); b.textContent = p[0]; if (!i) b.className = "on";
  b.onclick = () => { period = p; [...pEl.children].forEach(c => c.classList.toggle("on", c === b)); draw(); }; pEl.appendChild(b); });
document.getElementById("q").oninput = e => { query = e.target.value.trim().toLowerCase(); draw(); };

function textHtml(id) {
  const t = D.texts[id];
  return `<div class="src"><span class="d">${t[0]} · intérêt ${t[4]}/5 · texte n° ${id}</span><b>${esc(t[1])}</b>${esc(t[2])}
  ${t[3] ? `<details><summary>Texte d'origine</summary><p>${esc(t[3])}</p></details>` : ""}</div>`;
}
function nodeDates(n) {
  const a = (n.sa ? "vers " : "") + fmtY(n.start), b = n.open ? "aujourd'hui" : (n.ea ? "jusqu'à ~" : "") + fmtY(n.end);
  return `${a} → ${b}`;
}
function showNode(n) {
  selected = n.id;
  const ev = [];
  if (n.born) ev.push(n.born);
  D.edges.filter(e => e.s === n.id || e.d === n.id).forEach(e => ev.push(e.id));
  D.marks.filter(m => m.n === n.id).forEach(m => ev.push(m.id));
  if (n.died) ev.push(n.died);
  const ids = [...new Set(ev)].sort((a, b) => D.texts[a][0].localeCompare(D.texts[b][0]));
  const rel = n.related.filter(i => !ids.includes(i));
  const links = D.edges.filter(e => e.s === n.id || e.d === n.id).sort((a,b) => a.x - b.x).map(e => {
    const other = nodeById[e.s === n.id ? e.d : e.s];
    return `<li>${fmtY(e.x)} · ${D.types[e.t].toLowerCase()} — ${e.s === n.id ? "→" : "←"} ${esc(other.label)}</li>`; }).join("");
  document.getElementById("panel").innerHTML = `<h3>${esc(n.label)}</h3><div class="meta">${GROUPS[n.group]} · ${nodeDates(n)}</div>
    ${n.note ? `<div class="note">${esc(n.note)}</div>` : ""}${links ? `<ul style="margin:6px 0;padding-left:18px">${links}</ul>` : ""}
    <h4 style="margin:10px 0 0">Textes qui l'attestent</h4>${ids.map(textHtml).join("") || "<p style='color:var(--muted)'>Aucun texte daté ; dates tirées des mentions.</p>"}
    ${rel.length ? `<h4 style="margin:10px 0 0">Autres textes d'entreprise et de capital</h4>${rel.map(textHtml).join("")}` : ""}`;
  draw();
}
function showEdge(e) {
  const s = nodeById[e.s], d = nodeById[e.d];
  document.getElementById("panel").innerHTML = `<h3>${esc(D.types[e.t])}</h3><div class="meta">${esc(s.label)} → ${esc(d.label)} · ${fmtY(e.x)}</div>${textHtml(e.id)}`;
}

function draw() {
  const [, lo, hi] = period;
  const vis = D.nodes.filter(n => n.end >= lo && n.start <= hi && (!query || n.label.toLowerCase().includes(query)));
  document.getElementById("count").textContent = vis.length + " compagnies affichées sur " + D.nodes.length;
  const rows = [...new Set(vis.map(n => n.row))].sort((a, b) => a - b);
  const ry = Object.fromEntries(rows.map((r, i) => [r, 30 + i * 28]));
  const W = 1100, M = {l: 10, r: 200}, H = 50 + rows.length * 28;
  const x = d3.scaleLinear().domain([lo, hi]).range([M.l, W - M.r]);
  const clampX = v => Math.max(x(lo), Math.min(x(hi), x(v)));
  const svg = d3.create("svg").attr("width", W).attr("height", H).attr("viewBox", `0 0 ${W} ${H}`);
  const step = hi - lo > 80 ? 10 : 5;
  const g = svg.append("g").attr("class", "grid");
  for (let y = Math.ceil(lo / step) * step; y <= hi; y += step) {
    g.append("line").attr("x1", x(y)).attr("x2", x(y)).attr("y1", 18).attr("y2", H - 6);
    svg.append("text").attr("class", "axis").attr("x", x(y)).attr("y", 12).attr("text-anchor", "middle").text(y);
  }
  const visIds = new Set(vis.map(n => n.id));
  // liens
  const eg = svg.append("g");
  D.edges.filter(e => visIds.has(e.s) && visIds.has(e.d) && e.x >= lo && e.x <= hi).forEach(e => {
    const xs = x(e.x), ys = ry[nodeById[e.s].row], yd = ry[nodeById[e.d].row];
    const gr = eg.append("g").attr("class", "lnk");
    if (ys === yd) {
      gr.append("path").attr("d", `M${xs},${ys - 9}L${xs + 6},${ys}L${xs},${ys + 9}L${xs - 6},${ys}Z`).attr("class", "tp-" + e.t).attr("fill", "var(--card)").attr("stroke-width", 2);
    } else {
      gr.append("line").attr("x1", xs).attr("x2", xs).attr("y1", ys).attr("y2", yd).attr("class", "tp-" + e.t)
        .attr("stroke-width", WIDTH[e.t]).attr("stroke-dasharray", DASH[e.t]).attr("opacity", .9);
      gr.append("circle").attr("cx", xs).attr("cy", yd).attr("r", 4).attr("class", "tp-" + e.t).attr("fill", "var(--card)").attr("stroke-width", 2);
      gr.append("line").attr("x1", xs).attr("x2", xs).attr("y1", ys).attr("y2", yd).attr("class", "lnk-hit");
    }
    gr.on("mousemove", ev => showTip(ev, `${fmtY(e.x)} · ${esc(D.types[e.t])}<br>${esc(nodeById[e.s].label)} → ${esc(nodeById[e.d].label)}`))
      .on("mouseleave", hideTip).on("click", () => { hideTip(); showEdge(e); });
  });
  // barres
  const bg = svg.append("g");
  vis.forEach(n => {
    const y = ry[n.row], x0 = clampX(n.start), x1 = Math.max(clampX(n.end), x0 + 4);
    const bar = bg.append("rect").attr("class", `bar g-${n.group}`).attr("x", x0).attr("y", y - 7).attr("width", x1 - x0).attr("height", 14).attr("rx", 4)
      .attr("opacity", selected && selected !== n.id ? .75 : 1)
      .attr("stroke", selected === n.id ? "var(--ink)" : "none").attr("stroke-width", 2);
    // extrémités approximatives : pointillés sur le bord
    if (n.sa && n.start >= lo) bg.append("line").attr("x1", x0).attr("x2", x0).attr("y1", y - 9).attr("y2", y + 9).attr("stroke", "var(--ink)").attr("stroke-dasharray", "2 2").attr("pointer-events", "none");
    if (n.ea && n.end <= hi) bg.append("line").attr("x1", x1).attr("x2", x1).attr("y1", y - 9).attr("y2", y + 9).attr("stroke", "var(--ink)").attr("stroke-dasharray", "2 2").attr("pointer-events", "none");
    bar.on("mousemove", ev => showTip(ev, `<b>${esc(n.label)}</b><br>${nodeDates(n)}`)).on("mouseleave", hideTip).on("click", () => { hideTip(); showNode(n); });
    const w = n.label.length * 6.1;
    const inside = x1 - x0 > w + 10;
    bg.append("text").attr("class", "lab").attr("x", inside ? x0 + 6 : x1 + 6).attr("y", y + 4)
      .style("fill", inside ? "#fff" : "var(--ink)").style("stroke", inside ? "none" : "var(--card)").text(n.label);
  });
  // repères
  D.marks.filter(m => visIds.has(m.n) && m.x >= lo && m.x <= hi).forEach(m => {
    const y = ry[nodeById[m.n].row];
    bg.append("path").attr("d", `M${x(m.x)},${y - 7}l5,-6h-10z`).attr("fill", "var(--ink)").style("cursor", "pointer")
      .on("mousemove", ev => showTip(ev, `${fmtY(m.x)} · ${esc(m.l)}`)).on("mouseleave", hideTip)
      .on("click", () => { hideTip(); showNode(nodeById[m.n]); });
  });
  const c = document.getElementById("chart"); const sc = c.scrollTop;
  c.innerHTML = ""; c.appendChild(svg.node()); c.scrollTop = sc;
}

// onglets + index
document.querySelectorAll("#tabs button").forEach(b => b.onclick = () => {
  document.querySelectorAll("#tabs button").forEach(x => x.classList.toggle("on", x === b));
  document.getElementById("v-graph").style.display = b.dataset.tab === "graph" ? "" : "none";
  document.getElementById("v-index").style.display = b.dataset.tab === "index" ? "" : "none";
});
let idxSort = 2, idxDir = -1, idxQ = "", idxOpen = null;
function drawIdx() {
  let rows = D.index.filter(r => !idxQ || r[0].toLowerCase().includes(idxQ));
  rows = rows.slice().sort((a, b) => (typeof a[idxSort] === "string" ? a[idxSort].localeCompare(b[idxSort]) : a[idxSort] - b[idxSort]) * idxDir);
  const heads = ["Compagnie", "Textes", "Entreprise / capital", "Première année", "Dernière année"];
  let h = "<tr>" + heads.map((t, i) => `<th data-c="${i}">${t}${i === idxSort ? (idxDir > 0 ? " ▲" : " ▼") : ""}</th>`).join("") + "</tr>";
  rows.forEach(r => {
    h += `<tr class="row" data-n="${esc(r[0])}"><td>${esc(r[0])}</td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td><td>${r[4]}</td></tr>`;
    if (idxOpen === r[0]) h += `<tr><td colspan="5">${r[5].map(textHtml).join("")}<p class="d" style="color:var(--muted);font-size:12px">${r[2] > r[5].length ? "Les " + r[5].length + " textes les plus marquants sur " + r[2] + "." : ""}</p></td></tr>`;
  });
  const t = document.getElementById("idx"); t.innerHTML = h;
  t.querySelectorAll("th").forEach(th => th.onclick = () => { const c = +th.dataset.c; idxDir = c === idxSort ? -idxDir : (c === 0 ? 1 : -1); idxSort = c; drawIdx(); });
  t.querySelectorAll("tr.row").forEach(tr => tr.onclick = () => { idxOpen = idxOpen === tr.dataset.n ? null : tr.dataset.n; drawIdx(); });
}
document.getElementById("q2").oninput = e => { idxQ = e.target.value.trim().toLowerCase(); drawIdx(); };
drawIdx(); draw();
"""
