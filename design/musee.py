"""Design « musée » : the site is an airport turned museum.

The home page is the plan of the terminal seen from above: a hall, piers (jetées) whose gates are the
rooms, planes parked at the end of each pier, and a Concorde docked at a jet bridge whose cabins are
rooms too. The visitor (red dot) walks to the room that is clicked. Each page is a room: airport
signage at the top, a museum label (cartel), the exhibit in its showcase, doors to the neighbouring
rooms (also ← → on the keyboard) and the plan of the museum on demand.

Only the PLAN below knows which page is in which room; a page missing from it lands automatically in
the « Nouvelles acquisitions » pier, a slug listed here without a page is ignored.
"""
import json
import math
from html import escape

NAME = "musée : aérogare, jetées, salles et Concorde"

PLAN = [
    {"key": "A", "kind": "jetee", "name": "Le Réseau", "color": "#1f5fbf",
     "rooms": ["carte-reseau", "monde-retrecit", "villes-renommees", "prix-billets"]},
    {"key": "B", "kind": "jetee", "name": "La Flotte", "color": "#0f7f7a",
     "rooms": ["frise-avions", "vie-avion", "chiffres"]},
    {"key": "C", "kind": "jetee", "name": "Les Mémoires", "color": "#b35f12",
     "rooms": ["ce-jour-la", "personnages-lieux", "graphe-personnes", "genealogie"]},
    {"key": "D", "kind": "jetee", "name": "Les Turbulences", "color": "#c0283a",
     "rooms": ["greves-records", "barometre-crises"]},
    {"key": "K", "kind": "avion", "name": "À bord du Concorde", "color": "#6a4cb5",
     "rooms": ["quiz", "devine-annee"], "cabins": ["Cabine avant", "Cabine arrière"]},
    {"key": "H", "kind": "hall", "name": "Hall d'accueil", "color": "#b0307a",
     "rooms": ["demande-musee"], "desks": ["Information"]},
]
EXTRA = {"key": "E", "kind": "jetee", "name": "Nouvelles acquisitions", "color": "#5a6b2e", "rooms": []}

# Geometry of the plan (SVG user units).
RW, RH, CORR, VEST, GAP = 190, 80, 34, 34, 12   # room box, pier corridor width, hall-to-first-room, between rows
PIER0, PIERSTEP = 330, 240                        # x of the first pier, distance between piers (alternately up/down)
TY, TH, H = 500, 112, 1000                        # terminal centre line and height, plan height
TX0 = 90                                          # west wall of the terminal (entrance)
WALK = TY + 30                                    # the visitor walks along this line in the hall
START = (TX0 + 34, WALK)

PLANE = ("M0,-50C3.5,-47 5,-40 5,-32L5,-8L46,12L46,18L5,8L5,32L17,42L17,47L3,44L0,50L-3,44L-17,47"
         "L-17,42L-5,32L-5,8L-46,18L-46,12L-5,-8L-5,-32C-5,-40 -3.5,-47 0,-50Z")
CONCORDE = ("M0,-180C4,-170 7,-150 8,-120L9,-40C30,10 70,70 98,128L98,140L9,142L9,165L4,180L-4,180L-9,165"
            "L-9,142L-98,140L-98,128C-70,70 -30,10 -9,-40L-8,-120C-7,-150 -4,-170 0,-180Z")
CSCALE = 1.05


def _wrap(text, width=18, lines=3):
    out, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > width:
            out.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    out.append(cur)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = out[-1][: width - 1].rstrip() + "…"
    return out


def museum(pages):
    """Wings in visiting order, each with its rooms placed on the plan, and the plan size."""
    by_slug = {p["meta"]["slug"]: p for p in pages}
    wings, used = [], set()
    for spec in PLAN:
        rooms = [by_slug[s] for s in spec["rooms"] if s in by_slug]
        used |= {p["meta"]["slug"] for p in rooms}
        if rooms:
            wings.append({**spec, "pages": rooms})
    extra = [p for s, p in by_slug.items() if s not in used]
    if extra:
        last_pier = max((i for i, w in enumerate(wings) if w["kind"] == "jetee"), default=-1)
        wings.insert(last_pier + 1, {**EXTRA, "pages": extra})

    piers = [w for w in wings if w["kind"] == "jetee"]
    tx1 = (PIER0 + PIERSTEP * (len(piers) - 1) if piers else 500) + 200
    rooms = []
    for j, w in enumerate(piers):
        w["x"], w["up"] = PIER0 + j * PIERSTEP, j % 2 == 0
        sign = -1 if w["up"] else 1
        edge = TY + sign * TH / 2
        rows = math.ceil(len(w["pages"]) / 2)
        for i, page in enumerate(w["pages"]):
            cy = edge + sign * (VEST + RH / 2 + (i // 2) * (RH + GAP))
            cx = w["x"] + (-1 if i % 2 == 0 else 1) * (CORR / 2 + RW / 2)
            rooms.append({"wing": w, "page": page, "code": f"{w['key']}{i + 1}", "cx": cx, "cy": cy,
                          "path": [START, (w["x"], WALK), (w["x"], cy), (cx, cy)]})
        end = edge + sign * (VEST + rows * (RH + GAP) - GAP + 14)
        w["tip"] = end + sign * 24
        w["plane"] = w["tip"] + sign * (24 + 12 + 50)
        w["edge"] = edge

    for w in wings:
        if w["kind"] == "hall":
            n = len(w["pages"])
            for i, page in enumerate(w["pages"]):
                x = TX0 + (tx1 - TX0) * (i + 1) / (n + 1)
                rooms.append({"wing": w, "page": page, "code": f"{w['key']}{i + 1}", "cx": x, "cy": TY - 14,
                              "label": w.get("desks", [])[i] if i < len(w.get("desks", [])) else "Bureau",
                              "path": [START, (x, WALK), (x, TY + 12)]})

    px = tx1 + 170
    width = px + 120 + RW + 30
    for w in wings:
        if w["kind"] == "avion":
            w["x"] = px
            n = len(w["pages"])
            top, bottom = -170, 130
            door = TY - 40 - 120 * CSCALE
            for i, page in enumerate(w["pages"]):
                lo, hi = top + (bottom - top) * i / n, top + (bottom - top) * (i + 1) / n
                cy = TY - 40 + (lo + hi) / 2 * CSCALE
                cabins = w.get("cabins", [])
                rooms.append({"wing": w, "page": page, "code": f"{w['key']}{i + 1}", "cx": px + 120 + RW / 2, "cy": cy,
                              "seat": cy, "sect": (TY - 40 + lo * CSCALE, TY - 40 + hi * CSCALE),
                              "label": cabins[i] if i < len(cabins) else f"Cabine {i + 1}",
                              "path": [START, (tx1 - 20, WALK), (tx1 - 20, TY - 30), (px - 50, TY - 30), (px - 50, door), (px, door), (px, cy)]})

    order = {id(w): k for k, w in enumerate(wings)}
    rooms.sort(key=lambda r: (order[id(r["wing"])], r["code"]))
    return {"wings": wings, "rooms": rooms, "tx1": tx1, "W": width}


def plan_svg(m, current=None, mini=False, links=True):
    """The plan of the museum. mini = codes only (the plan inside a room); links=False for a picture of it."""
    W, tx1 = m["W"], m["tx1"]
    out = [f'<svg class="mu-plan{" mu-mini" if mini else ""}" viewBox="0 0 {W:.0f} {H}" role="img" aria-label="Plan du musée">',
           f'<rect class="mu-grass" width="{W:.0f}" height="{H}"/>',
           f'<rect class="mu-apron" x="20" y="64" width="{W - 40:.0f}" height="{H - 128}" rx="34"/>']
    for y in (14, H - 54):  # runways
        out.append(f'<rect class="mu-runway" x="40" y="{y}" width="{W - 80:.0f}" height="40" rx="4"/>'
                   f'<line class="mu-rwline" x1="90" y1="{y + 20}" x2="{W - 90:.0f}" y2="{y + 20}"/>')
        if not mini:
            out.append(f'<text class="mu-rwnum" x="62" y="{y + 26}">09</text><text class="mu-rwnum" x="{W - 62:.0f}" y="{y + 26}" text-anchor="end">27</text>')
    if not mini:  # traffic: one take-off, one landing
        out.append(f'<g class="mu-traffic"><g><path class="mu-moving" d="{PLANE}" transform="rotate(90) scale(.9)"/>'
                   f'<animateMotion dur="16s" repeatCount="indefinite" keyPoints="0;0;1" keyTimes="0;.35;1" calcMode="spline" keySplines="0 0 1 1;.6 0 1 1" path="M175,34 L{W + 120:.0f},34"/></g>'
                   f'<g><path class="mu-moving" d="{PLANE}" transform="rotate(-90) scale(.9)"/>'
                   f'<animateMotion dur="21s" begin="-6s" repeatCount="indefinite" keyPoints="0;1;1" keyTimes="0;.55;1" calcMode="spline" keySplines="0 .4 .4 1;0 0 1 1" path="M{W + 140:.0f},{H - 34} L260,{H - 34}"/></g></g>')

    # piers: corridor, tip, parked plane and its lead-in line, name
    for w in m["wings"]:
        if w["kind"] != "jetee":
            continue
        x, s = w["x"], -1 if w["up"] else 1
        y0, y1 = sorted((w["edge"], w["tip"]))
        out.append(f'<line class="mu-leadin" x1="{x}" y1="{w["tip"]}" x2="{x}" y2="{w["plane"] + s * 60}"/>')
        out.append(f'<rect class="mu-build" x="{x - CORR / 2 - 2}" y="{y0 - 2}" width="{CORR + 4}" height="{y1 - y0 + 4}"/>')
        out.append(f'<g style="--w:{w["color"]}"><circle class="mu-tip" cx="{x}" cy="{w["tip"]}" r="24"/>'
                   f'<text class="mu-signletter" x="{x}" y="{w["tip"]}">{w["key"]}</text></g>')
        out.append(f'<path class="mu-parked" d="{PLANE}" transform="translate({x},{w["plane"]}) rotate({180 if w["up"] else 0}) scale(1.05)"/>'
                   f'<rect class="mu-tail" x="{x - 2}" y="{w["plane"] + s * -50 - 3:.0f}" width="4" height="6" style="--w:{w["color"]}"/>')
        if not mini:
            out.append(f'<text class="mu-wn" x="{x + 64}" y="{w["plane"] - 4}">Jetée {w["key"]}</text>'
                       f'<text class="mu-ws" x="{x + 64}" y="{w["plane"] + 15}">{escape(w["name"])}</text>')

    # terminal
    out.append(f'<rect class="mu-build mu-terminal" x="{TX0}" y="{TY - TH / 2}" width="{tx1 - TX0}" height="{TH}" rx="24"/>'
               f'<rect class="mu-glass" x="{TX0 + 14}" y="{TY - TH / 2 + 10}" width="{tx1 - TX0 - 28}" height="6" rx="3"/>'
               f'<rect class="mu-glass" x="{TX0 + 14}" y="{TY + TH / 2 - 16}" width="{tx1 - TX0 - 28}" height="6" rx="3"/>')
    if not mini:
        out.append(f'<text class="mu-ws" x="{TX0 + 26}" y="{TY - 22}">AÉROGARE · HALL D\'ACCUEIL</text>'
                   f'<text class="mu-entry" x="{TX0 - 46}" y="{TY + 6}" transform="rotate(-90 {TX0 - 46} {TY})" text-anchor="middle">ENTRÉE</text>')
    out.append(f'<path class="mu-arrow" d="M{TX0 - 36},{WALK} h26 m-9,-8 l9,8 l-9,8"/>')

    # Concorde and jet bridge
    for w in m["wings"]:
        if w["kind"] != "avion":
            continue
        px, door = w["x"], TY - 40 - 120 * CSCALE
        out.append(f'<path class="mu-bridge" d="M{tx1},{TY - 30} H{px - 50} V{door} H{px - 9}"/>')
        out.append(f'<g transform="translate({px},{TY - 40}) scale({CSCALE})"><path class="mu-concorde" d="{CONCORDE}"/>'
                   '<line class="mu-fin" x1="0" y1="118" x2="0" y2="176"/>'
                   + "".join(f'<circle class="mu-window" cx="{sx}" cy="{wy}" r="1.6"/>' for wy in range(-150, 40, 12) for sx in (-5, 5))
                   + '</g>')
        if not mini:
            out.append(f'<text class="mu-reg" x="{px}" y="{TY + 78}" text-anchor="middle">F-BVFA</text>'
                       f'<text class="mu-wn" x="{px - 105}" y="{TY + 190}" text-anchor="middle">Porte {w["key"]}</text>'
                       f'<text class="mu-ws" x="{px - 105}" y="{TY + 208}" text-anchor="middle">{escape(w["name"])}</text>')

    # rooms
    for r in m["rooms"]:
        page, w = r["page"], r["wing"]
        slug, title, closed = page["meta"]["slug"], page["meta"]["title"], bool(page["error"])
        cls = "mu-room" + (" mu-here" if slug == current else "") + (" mu-closed" if closed else "")
        tip = f"{r['code']} · {title}" + (" (fermée)" if closed else "")
        attrs = f'class="{cls}" data-slug="{slug}" style="--w:{w["color"]}"'
        if not links:
            link = f'<g {attrs}>'
        elif closed:
            link = f'<a {attrs} aria-disabled="true">'
        else:
            link = f'<a {attrs} href="{slug}.html" aria-label="{escape(tip)}">'
        out.append(link + (f"<title>{escape(tip)}</title>" if links else ""))
        if w["kind"] == "hall":
            out.append(f'<circle class="mu-roombox" cx="{r["cx"]}" cy="{r["cy"]}" r="30"/>'
                       f'<text class="mu-info-i" x="{r["cx"]}" y="{r["cy"]}">i</text>')
            if not mini:
                out.append(f'<text class="mu-t" x="{r["cx"]}" y="{r["cy"] + 50}" text-anchor="middle">{escape(r["label"])} : {escape(title)}</text>')
            ring = (r["cx"] + 24, r["cy"] - 24)
        else:
            x, y = r["cx"] - RW / 2, r["cy"] - RH / 2
            if w["kind"] == "avion":
                lo, hi = r["sect"]
                out.append(f'<rect class="mu-cabin" x="{w["x"] - 8}" y="{lo:.0f}" width="16" height="{hi - lo:.0f}" rx="6"/>'
                           f'<line class="mu-leader" x1="{w["x"] + 12}" y1="{r["seat"]:.0f}" x2="{x}" y2="{r["seat"]:.0f}"/>')
            out.append(f'<rect class="mu-roombox" x="{x}" y="{y:.0f}" width="{RW}" height="{RH}" rx="8"/>')
            if mini:
                out.append(f'<circle class="mu-badge" cx="{r["cx"]}" cy="{r["cy"]:.0f}" r="27"/><text class="mu-c mu-cbig" x="{r["cx"]}" y="{r["cy"]:.0f}">{r["code"]}</text>')
            else:
                lines = _wrap(title)
                if w["kind"] == "avion":
                    lines = [r["label"]] + _wrap(title, lines=2)
                out.append(f'<circle class="mu-badge" cx="{x + 22}" cy="{y + 22:.0f}" r="15"/><text class="mu-c" x="{x + 22}" y="{y + 22:.0f}">{r["code"]}</text>')
                ty = r["cy"] - (len(lines) - 1) * 9
                for k, line in enumerate(lines):
                    cls_t = "mu-t mu-sub" if (w["kind"] == "avion" and k == 0) else "mu-t"
                    out.append(f'<text class="{cls_t}" x="{x + 44}" y="{ty + k * 18:.0f}">{escape(line)}</text>')
            ring = (x + RW - 12, y + 12)
        out.append(f'<g class="mu-seen"><circle cx="{ring[0]:.0f}" cy="{ring[1]:.0f}" r="9"/><path d="M{ring[0] - 4:.0f},{ring[1]:.0f} l3,3 l5,-6"/></g>{"</a>" if links else "</g>"}')

    # the visitor
    here = next((r for r in m["rooms"] if r["page"]["meta"]["slug"] == current), None)
    mx, my = (here["cx"], here["cy"] - (0 if here["wing"]["kind"] == "hall" else RH / 2 + 4)) if here else START
    me_id = "" if mini else 'id="mu-me" '
    out.append(f'<g {me_id}class="mu-me" transform="translate({mx:.0f},{my:.0f})"><circle class="mu-halo" r="18"/><circle class="mu-dot" r="8"/></g>')
    out.append("</svg>")
    return "".join(out)


STYLE = """
:root { --bg:#f1ede6; --card:#fffdf9; --ink:#1c2230; --muted:#5d6574; --line:#e0dacf; --accent:#002157; --accent2:#d4001a;
  --mu-sign:#1d232c; --mu-sign-ink:#ffd200; --mu-grass:#dde5d1; --mu-apron:#cfd4da; --mu-runway:#59606b; --mu-build:#f8f6f2;
  --mu-wall:#9aa3ae; --mu-room:#ffffff; --mu-floor:#e2dbcf; --mu-board:#0c0f14; }
@media (prefers-color-scheme: dark) { :root { --bg:#12161d; --card:#1a1f29; --ink:#e8ebf1; --muted:#9aa3b2; --line:#2b3340; --accent:#8fb5ff; --accent2:#ff6b7a;
  --mu-sign:#0a0d12; --mu-grass:#141c17; --mu-apron:#222831; --mu-runway:#363d48; --mu-build:#2c333e; --mu-wall:#566070; --mu-room:#1e2531; --mu-floor:#0e1117; } }
* { box-sizing:border-box; }
html { background:var(--bg); }
body { margin:0; font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; color:var(--ink);
  background:radial-gradient(1200px 380px at 50% -120px, color-mix(in srgb, #fff 55%, transparent), transparent 70%), var(--bg); min-height:100vh; }
@media (prefers-color-scheme: dark) { body { background:radial-gradient(1200px 380px at 50% -120px, #ffffff14, transparent 70%), var(--bg); } }
a { color:var(--accent); }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px; }
@view-transition { navigation:auto; }
::view-transition-old(root) { animation:.32s ease both mu-out; } ::view-transition-new(root) { animation:.38s ease both mu-in; }
@keyframes mu-out { to { opacity:0; transform:scale(1.03); } } @keyframes mu-in { from { opacity:0; transform:scale(.98); } }
@media (prefers-reduced-motion: reduce) { ::view-transition-old(root), ::view-transition-new(root) { animation:none; } .mu-traffic { display:none; } }

/* airport signage */
.mu-sign { view-transition-name:mu-sign; position:sticky; top:0; z-index:20; display:flex; align-items:center; gap:14px; flex-wrap:wrap;
  padding:9px 20px; background:var(--mu-sign); color:var(--mu-sign-ink); font-weight:600; letter-spacing:.02em; box-shadow:0 2px 10px #0004; }
.mu-sign a, .mu-sign .mu-btn { color:var(--mu-sign-ink); text-decoration:none; }
.mu-sign .mu-logo { font-weight:800; font-size:16px; white-space:nowrap; }
.mu-sign .mu-logo i { font-style:normal; display:inline-block; transform:rotate(-45deg); margin-right:6px; }
.mu-sign .mu-where { display:flex; align-items:center; gap:10px; color:#fff; font-weight:500; min-width:0; }
.mu-gate { display:inline-grid; place-items:center; min-width:34px; height:28px; padding:0 7px; border-radius:6px; background:var(--w, var(--accent)); color:#fff; font-weight:800; }
.mu-sign .mu-gate { background:var(--mu-sign-ink); color:var(--mu-sign); }
.mu-sign nav { margin-left:auto; min-width:0; display:flex; gap:6px; align-items:center; flex-wrap:wrap; }
.mu-sign nav a, .mu-sign .mu-btn { font:600 14px system-ui,sans-serif; padding:5px 11px; border:1px solid #ffffff2e; border-radius:6px; background:transparent; cursor:pointer; white-space:nowrap; }
.mu-sign nav a:hover, .mu-sign .mu-btn:hover { background:#ffffff1a; }
.mu-sign .mu-pass { font-size:13px; color:#cfd6e2; font-weight:500; white-space:nowrap; }
.mu-sign .mu-pass b { color:var(--mu-sign-ink); }

/* a room */
.mu-wall { max-width:1280px; margin:0 auto; padding:26px 22px 10px; }
.mu-cartel { display:flex; gap:18px; align-items:stretch; margin:0 0 22px; }
.mu-thumb { flex:0 0 280px; padding:6px; border:1px solid var(--line); border-radius:10px; background:var(--card); cursor:pointer; display:flex; flex-direction:column; gap:4px;
  color:var(--muted); font:600 12px system-ui,sans-serif; letter-spacing:.06em; text-transform:uppercase; box-shadow:0 10px 28px -18px #0008; }
.mu-thumb:hover { border-color:var(--accent); color:var(--ink); } .mu-thumb .mu-plan { border-radius:6px; }
@media (max-width:900px) { .mu-thumb { display:none; } }
.mu-plaque { flex:1; background:var(--card); border:1px solid var(--line); border-left:6px solid var(--w); border-radius:4px 10px 10px 4px;
  padding:16px 22px; box-shadow:0 10px 28px -18px #0008; }
.mu-kicker { margin:0 0 4px; font-size:12.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); font-weight:600; }
.mu-plaque h1 { margin:0 0 6px; font:700 30px/1.15 Georgia,"Iowan Old Style","Times New Roman",serif; }
.mu-plaque .lead { margin:0; color:var(--muted); max-width:80ch; }
.mu-vitrine { position:relative; padding:22px; border-radius:14px; border:1px solid var(--line);
  background:linear-gradient(180deg, color-mix(in srgb, var(--card) 70%, transparent), color-mix(in srgb, var(--card) 35%, transparent));
  box-shadow:0 30px 60px -40px #0009, inset 0 1px 0 #ffffff40; }
.mu-vitrine::before { content:""; position:absolute; inset:-26px 8% auto; height:26px; pointer-events:none;
  background:radial-gradient(closest-side, color-mix(in srgb, #ffe9a8 60%, transparent), transparent); opacity:.7; }
.mu-doors { max-width:1280px; margin:0 auto; padding:18px 22px 30px; display:grid; grid-template-columns:1fr auto 1fr; gap:14px; align-items:end; }
.mu-door { display:flex; flex-direction:column; gap:2px; padding:22px 18px 14px; min-height:112px; justify-content:flex-end; text-decoration:none; color:var(--ink);
  background:linear-gradient(180deg, color-mix(in srgb, var(--w) 20%, var(--card)), var(--card)); border:2px solid color-mix(in srgb, var(--w) 45%, var(--line));
  border-bottom-width:6px; border-radius:60px 60px 6px 6px; transition:border-color .15s, box-shadow .15s; }
.mu-door:hover { border-color:var(--w); box-shadow:0 12px 26px -16px var(--w); }
.mu-door small { color:var(--muted); font-weight:600; letter-spacing:.05em; text-transform:uppercase; font-size:12px; }
.mu-door b { font-size:16px; }
.mu-door.next { text-align:right; } .mu-door.off { visibility:hidden; }
.mu-hallbtn { display:grid; place-items:center; gap:4px; text-decoration:none; color:var(--ink); font-weight:600; padding:10px 18px; }
.mu-hallbtn span { display:grid; place-items:center; width:46px; height:46px; border-radius:50%; background:var(--mu-sign); color:var(--mu-sign-ink); font-size:22px; }
@media (max-width:760px) { .mu-doors { grid-template-columns:1fr 1fr; } .mu-hallbtn { grid-column:1 / -1; order:3; } .mu-plaque h1 { font-size:24px; } }
.mu-foot { text-align:center; color:var(--muted); font-size:12.5px; padding:16px; border-top:1px solid var(--line); background:var(--mu-floor); }

/* plan drawer in the rooms */
.mu-drawer { position:fixed; inset:0; z-index:40; background:#0009; display:grid; place-items:start center; padding:70px 16px 16px; overflow:auto; }
.mu-drawer[hidden] { display:none; }
.mu-drawer-box { width:min(1180px, 100%); background:var(--card); border-radius:14px; padding:18px; box-shadow:0 30px 80px #0008; }
.mu-drawer-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; font-weight:700; font-size:18px; }
.mu-close { font:600 14px system-ui,sans-serif; padding:6px 12px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--ink); cursor:pointer; }
.mu-legend { display:grid; grid-template-columns:repeat(auto-fill,minmax(250px,1fr)); gap:4px 18px; margin-top:12px; font-size:14px; }
.mu-legend a { display:flex; gap:8px; align-items:center; text-decoration:none; color:var(--ink); padding:3px 0; }
.mu-legend a:hover b { text-decoration:underline; } .mu-legend .mu-gate { min-width:30px; height:22px; font-size:12px; }
.mu-legend a.mu-cur b { color:var(--accent2); }
.mu-legend a.mu-done::after { content:"✓"; color:#2e9e5b; font-weight:700; }

/* the plan */
.mu-plan { display:block; width:100%; height:auto; }
.mu-plan .mu-grass { fill:var(--mu-grass); } .mu-plan .mu-apron { fill:var(--mu-apron); }
.mu-plan .mu-runway { fill:var(--mu-runway); } .mu-plan .mu-rwline { stroke:#fff; stroke-width:3; stroke-dasharray:30 24; opacity:.75; }
.mu-plan text.mu-rwnum { fill:#fff; font:700 18px system-ui,sans-serif; opacity:.8; }
.mu-plan .mu-build { fill:var(--mu-build); stroke:var(--mu-wall); stroke-width:2; }
.mu-plan .mu-glass { fill:color-mix(in srgb, #4aa3df 35%, var(--mu-build)); }
.mu-plan .mu-leadin { stroke:#e9b900; stroke-width:2.5; stroke-dasharray:10 7; }
.mu-plan .mu-tip { fill:var(--mu-sign); stroke:var(--w); stroke-width:3; }
.mu-plan text.mu-signletter { fill:var(--mu-sign-ink); font:800 24px system-ui,sans-serif; text-anchor:middle; dominant-baseline:central; }
.mu-plan .mu-parked, .mu-plan .mu-moving { fill:#fbfbfd; stroke:#7d8693; stroke-width:1.4; }
.mu-plan .mu-tail { fill:var(--w); }
.mu-plan text.mu-wn { fill:var(--ink); font:800 17px system-ui,sans-serif; }
.mu-plan text.mu-ws { fill:var(--muted); font:600 13px system-ui,sans-serif; letter-spacing:.06em; }
.mu-plan text.mu-entry { fill:var(--accent2); font:800 15px system-ui,sans-serif; letter-spacing:.2em; }
.mu-plan .mu-arrow { fill:none; stroke:var(--accent2); stroke-width:3; stroke-linecap:round; stroke-linejoin:round; }
.mu-plan .mu-bridge { fill:none; stroke:var(--mu-wall); stroke-width:16; stroke-linejoin:round; }
.mu-plan .mu-concorde { fill:#fbfbfd; stroke:#7d8693; stroke-width:1.6; }
.mu-plan .mu-fin { stroke:#7d8693; stroke-width:3; } .mu-plan .mu-window { fill:#7fa6c9; }
.mu-plan text.mu-reg { fill:#7d8693; font:700 12px system-ui,sans-serif; letter-spacing:.2em; }
.mu-plan .mu-cabin { fill:var(--w); opacity:0; transition:opacity .15s; }
.mu-plan .mu-leader { stroke:var(--w); stroke-width:1.5; stroke-dasharray:4 4; }
.mu-plan .mu-room { cursor:pointer; outline:none; }
.mu-plan .mu-roombox { fill:var(--mu-room); stroke:var(--mu-wall); stroke-width:1.5; transition:fill .15s, stroke .15s; }
.mu-plan a.mu-room:hover .mu-roombox, .mu-plan a.mu-room:focus-visible .mu-roombox { fill:color-mix(in srgb, var(--w) 16%, var(--mu-room)); stroke:var(--w); stroke-width:3.5; }
.mu-plan a.mu-room:hover .mu-cabin, .mu-plan a.mu-room:focus-visible .mu-cabin, .mu-plan .mu-here .mu-cabin { opacity:.55; }
.mu-plan a.mu-room:focus-visible .mu-roombox { stroke-width:5; }
.mu-plan .mu-badge { fill:var(--w); }
.mu-plan text.mu-c { fill:#fff; font:800 13px system-ui,sans-serif; text-anchor:middle; dominant-baseline:central; pointer-events:none; }
.mu-plan text.mu-cbig { font-size:24px; }
.mu-plan text.mu-t { fill:var(--ink); font:600 14.5px system-ui,sans-serif; dominant-baseline:central; pointer-events:none; }
.mu-plan text.mu-sub { fill:var(--w); font-size:12px; text-transform:uppercase; letter-spacing:.08em; font-weight:800; }
.mu-plan text.mu-info-i { fill:var(--w); font:italic 800 30px Georgia,serif; text-anchor:middle; dominant-baseline:central; pointer-events:none; }
.mu-plan .mu-here .mu-roombox { fill:var(--w); stroke:var(--w); }
.mu-plan .mu-here .mu-badge { fill:#fff; } .mu-plan .mu-here text.mu-c { fill:var(--w); } .mu-plan .mu-here text.mu-info-i { fill:#fff; }
.mu-plan a.mu-closed { cursor:not-allowed; opacity:.45; }
.mu-plan .mu-seen { display:none; } .mu-plan .seen .mu-seen { display:inline; }
.mu-plan .mu-seen circle { fill:#2e9e5b; } .mu-plan .mu-seen path { fill:none; stroke:#fff; stroke-width:2.2; stroke-linecap:round; stroke-linejoin:round; }
.mu-plan .mu-me { pointer-events:none; } .mu-plan .mu-dot { fill:var(--accent2); stroke:#fff; stroke-width:3; }
.mu-plan .mu-halo { fill:var(--accent2); opacity:.25; transform-box:fill-box; transform-origin:center; animation:mu-pulse 1.8s ease-out infinite; }
@keyframes mu-pulse { from { transform:scale(.5); opacity:.45; } to { transform:scale(1.6); opacity:0; } }
@media (prefers-reduced-motion: reduce) { .mu-plan .mu-halo { animation:none; } }

/* home */
.mu-home { max-width:1820px; margin:0 auto; padding:22px; }
.mu-hero { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:24px; align-items:center; margin-bottom:18px; }
.mu-hero h1 { margin:0 0 6px; font:700 40px/1.1 Georgia,"Iowan Old Style","Times New Roman",serif; }
.mu-hero p.mu-lead { margin:0; color:var(--muted); font-size:16.5px; max-width:78ch; }
.mu-ticket { display:grid; grid-template-columns:auto auto; border-radius:12px; overflow:hidden; box-shadow:0 18px 40px -24px #000a; min-width:360px; }
.mu-ticket > div { padding:14px 18px; background:var(--card); }
.mu-ticket .mu-stub { background:#002157; color:#fff; border-left:2px dashed #ffffff80; display:grid; place-items:center; text-align:center; gap:6px; }
.mu-ticket .mu-stub a { color:#002157; background:#fff; padding:6px 12px; border-radius:6px; font-weight:700; text-decoration:none; white-space:nowrap; }
.mu-ticket small { display:block; color:var(--muted); font-size:11px; letter-spacing:.08em; text-transform:uppercase; font-weight:700; }
.mu-ticket .mu-stub small { color:#ffffffb0; }
.mu-ticket .mu-big { font-size:22px; font-weight:800; }
.mu-stamps { display:flex; gap:3px; margin-top:8px; flex-wrap:wrap; max-width:260px; }
.mu-stamps i { width:12px; height:12px; border-radius:3px; background:var(--line); } .mu-stamps i.on { background:var(--w); }
.mu-planwrap { position:relative; border-radius:16px; overflow:hidden; border:1px solid var(--line); box-shadow:0 30px 60px -40px #000a; }
.mu-info { position:absolute; left:16px; bottom:16px; width:min(380px, calc(100% - 32px)); background:color-mix(in srgb, var(--card) 94%, transparent);
  border:1px solid var(--line); border-left:6px solid var(--w, var(--accent)); border-radius:10px; padding:12px 14px; box-shadow:0 12px 30px -14px #0008; backdrop-filter:blur(6px); }
.mu-info b { display:block; font-size:17px; margin:4px 0 2px; } .mu-info p { margin:0 0 8px; color:var(--muted); font-size:13.5px; }
.mu-info a { font-weight:700; } .mu-info small { color:var(--muted); font-weight:600; margin-left:6px; }
.mu-hint { color:var(--muted); font-size:13.5px; margin:10px 2px 26px; }
.mu-board { background:var(--mu-board); color:#ffd200; border-radius:14px; padding:14px 18px 18px; box-shadow:0 20px 50px -30px #000; overflow-x:auto; }
.mu-board h2 { margin:2px 0 10px; font:800 20px system-ui,sans-serif; letter-spacing:.12em; color:#fff; display:flex; gap:12px; align-items:center; }
.mu-board h2 span { color:#ffd200; }
.mu-board table { width:100%; border-collapse:separate; border-spacing:0 4px; font:600 15px ui-monospace,"SF Mono",Menlo,Consolas,monospace; text-transform:uppercase; }
.mu-board th { text-align:left; color:#8a93a3; font-size:12px; letter-spacing:.12em; padding:0 10px; }
.mu-board td { background:#1a1f28; padding:7px 10px; white-space:nowrap; }
.mu-board tr td:first-child { border-radius:4px 0 0 4px; } .mu-board tr td:last-child { border-radius:0 4px 4px 0; }
.mu-board tbody tr { cursor:pointer; } .mu-board tbody tr:hover td { background:#262d39; }
.mu-board a { color:#ffd200; text-decoration:none; } .mu-board td.mu-dest { white-space:normal; min-width:240px; }
.mu-board .mu-st { color:#3ddc84; } .mu-board .mu-st.done { color:#9aa3b2; } .mu-board .mu-st.ko { color:#ff6b7a; }
.mu-board .mu-st.go::before { content:"● "; animation:mu-blink 1.2s steps(2) infinite; }
@keyframes mu-blink { 50% { opacity:.2; } }
@media (max-width:900px) { .mu-hero { grid-template-columns:minmax(0,1fr); } .mu-ticket { min-width:0; grid-template-columns:minmax(0,1fr); }
  .mu-ticket .mu-stub { border-left:0; border-top:2px dashed #ffffff80; } .mu-hero h1 { font-size:30px; } .mu-info { position:static; width:auto; border-radius:0; } }
@media (max-width:600px) { .mu-sign { padding:8px 12px; gap:6px 10px; } .mu-sign nav { margin-left:0; } .mu-sign .mu-where > span { display:none; }
  .mu-home, .mu-wall { padding-left:12px; padding-right:12px; } .mu-vitrine { padding:10px; } }
"""

NAV_JS = r"""
(() => {
  const M = __MU__, KEY = "musee-af-visites";
  let seen = [];
  try { seen = JSON.parse(localStorage.getItem(KEY)) || []; } catch (e) {}
  if (M.slug && !seen.includes(M.slug)) { seen.push(M.slug); try { localStorage.setItem(KEY, JSON.stringify(seen)); } catch (e) {} }
  const done = M.all.filter(s => seen.includes(s));
  document.querySelectorAll("[data-mu-visits]").forEach(el => el.textContent = `${done.length}/${M.all.length}`);
  document.querySelectorAll(".mu-plan .mu-room").forEach(a => a.classList.toggle("seen", seen.includes(a.dataset.slug)));
  document.querySelectorAll(".mu-legend a").forEach(a => a.classList.toggle("mu-done", seen.includes(a.dataset.slug)));
  window.__museeVisites = seen;

  const dr = document.getElementById("mu-drawer"), btn = document.getElementById("mu-plan-btn");
  const open = v => { if (!dr) return; dr.hidden = !v; btn.setAttribute("aria-expanded", String(v)); if (v) dr.querySelector(".mu-close").focus(); else btn.focus(); };
  if (dr) {
    btn.onclick = () => open(dr.hidden);
    document.querySelectorAll("[data-mu-plan]").forEach(b => b.onclick = () => open(true));
    dr.addEventListener("click", e => { if (e.target === dr || e.target.closest(".mu-close")) open(false); });
  }
  addEventListener("keydown", e => {
    if (dr && e.key === "Escape" && !dr.hidden) { open(false); return; }
    if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    const t = e.target;
    if (t.closest && t.closest("input, textarea, select, [contenteditable], [role=slider]")) return;
    if (e.key === "ArrowLeft" && M.prev) location.href = M.prev;
    if (e.key === "ArrowRight" && M.next) location.href = M.next;
    if (dr && (e.key === "p" || e.key === "P")) open(dr.hidden);
  });
})();
"""

HOME_JS = r"""
(() => {
  const R = __ROOMS__, seen = window.__museeVisites || [];
  const by = Object.fromEntries(R.map(r => [r.slug, r]));
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  // panel describing the room under the pointer
  const info = document.getElementById("mu-info");
  const show = r => {
    info.style.setProperty("--w", r.color);
    info.innerHTML = `<span class="mu-gate" style="--w:${r.color}">${r.code}</span><small>${esc(r.wing)}</small><b>${esc(r.title)}</b><p>${esc(r.desc)}</p>`
      + (r.closed ? "<em>Fermée pour travaux</em>" : `<a href="${r.href}">Entrer dans la salle →</a>${seen.includes(r.slug) ? " <small>✓ déjà visitée</small>" : ""}`);
  };
  document.querySelectorAll(".mu-plan a.mu-room").forEach(a => {
    const r = by[a.dataset.slug];
    a.addEventListener("mouseenter", () => show(r));
    a.addEventListener("focus", () => show(r));
  });

  // the visitor walks to the room before entering it
  const me = document.getElementById("mu-me"), home = me.getAttribute("transform");
  addEventListener("pageshow", () => me.setAttribute("transform", home));
  let walking = false;
  document.querySelector(".mu-planwrap .mu-plan").addEventListener("click", e => {
    const a = e.target.closest("a.mu-room");
    if (!a) return;
    const r = by[a.dataset.slug];
    if (r.closed) { e.preventDefault(); return; }
    if (reduce || e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;
    e.preventDefault();
    if (walking) return;
    walking = true;
    const p = r.path, seg = [];
    let total = 0;
    for (let i = 1; i < p.length; i++) { const l = Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]); seg.push(l); total += l; }
    const dur = Math.min(1500, 400 + total * 0.55), t0 = performance.now();
    setTimeout(() => location.href = r.href, dur + 400);  // in case animation frames are paused
    const step = now => {
      let k = Math.min(1, (now - t0) / dur);
      const d = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      let rem = d * total, i = 0;
      while (i < seg.length - 1 && rem > seg[i]) { rem -= seg[i]; i++; }
      const f = seg[i] ? Math.min(1, rem / seg[i]) : 1;
      me.setAttribute("transform", `translate(${p[i][0] + (p[i + 1][0] - p[i][0]) * f},${p[i][1] + (p[i + 1][1] - p[i][1]) * f})`);
      if (k < 1) requestAnimationFrame(step); else { walking = false; location.href = r.href; }
    };
    requestAnimationFrame(step);
  });

  // boarding pass: next room not visited yet
  const open = R.filter(r => !r.closed), next = open.find(r => !seen.includes(r.slug)) || open[0];
  if (next) {
    document.getElementById("mu-next").innerHTML = `<span class="mu-gate" style="--w:${next.color}">${next.code}</span> ${esc(next.title)}`;
    document.getElementById("mu-go").href = next.href;
    document.getElementById("mu-go").textContent = seen.length ? "Continuer la visite →" : "Commencer la visite →";
  }
  document.querySelectorAll(".mu-stamps i").forEach(i => i.classList.toggle("on", seen.includes(i.dataset.slug)));

  // departures board
  document.querySelectorAll(".mu-board tbody tr").forEach(tr => {
    const r = by[tr.dataset.slug], st = tr.querySelector(".mu-st");
    if (!r.closed && seen.includes(r.slug)) { st.textContent = "Visitée"; st.className = "mu-st done"; }
    if (!r.closed) tr.onclick = e => { if (!e.target.closest("a")) location.href = r.href; };
  });
  if (!reduce) {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    document.querySelectorAll(".mu-flap").forEach((el, n) => {
      const final = el.textContent, frames = 8 + (n % 9);
      let f = 0;
      const id = setInterval(() => {
        f++;
        el.textContent = [...final].map((c, i) => c === " " || i < final.length * f / frames ? c : chars[Math.random() * chars.length | 0]).join("");
        if (f >= frames) { clearInterval(id); el.textContent = final; }
      }, 40);
    });
  }
})();
"""


def _place(w):
    return {"jetee": f"Jetée {w['key']}", "hall": "Hall d'accueil", "avion": f"Porte {w['key']}"}[w["kind"]]


def _head(title, extra=""):
    return ('<!doctype html>\n<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)}</title><style>{STYLE}</style>{extra}</head>')


def _sign(where, nav):
    return (f'<header class="mu-sign"><a class="mu-logo" href="index.html"><i>✈</i>Musée Air France</a>'
            f'<span class="mu-where">{where}</span><nav>{nav}</nav>'
            '<span class="mu-pass" title="Salles visitées dans ce navigateur">Carte d\'embarquement : <b data-mu-visits>0</b></span></header>')


def _nav_script(m, slug=None, prev=None, nxt=None):
    payload = {"slug": slug, "prev": prev, "next": nxt, "all": [r["page"]["meta"]["slug"] for r in m["rooms"] if not r["page"]["error"]]}
    return NAV_JS.replace("__MU__", json.dumps(payload, ensure_ascii=False))


def _legend(m, current=None):
    items = []
    for r in m["rooms"]:
        meta, w = r["page"]["meta"], r["wing"]
        if r["page"]["error"]:
            continue
        cur = ' class="mu-cur"' if meta["slug"] == current else ""
        items.append(f'<a href="{meta["slug"]}.html" data-slug="{meta["slug"]}"{cur}><span class="mu-gate" style="--w:{w["color"]}">{r["code"]}</span>'
                     f'<b>{escape(meta["title"])}</b></a>')
    return f'<div class="mu-legend">{"".join(items)}</div>'


def render_room(exhibit, slug, pages, ctx):
    m = museum(pages)
    rooms = [r for r in m["rooms"] if not r["page"]["error"]]
    i = next(k for k, r in enumerate(rooms) if r["page"]["meta"]["slug"] == slug)
    r, w = rooms[i], rooms[i]["wing"]
    prev, nxt = (rooms[i - 1] if i > 0 else None), (rooms[i + 1] if i + 1 < len(rooms) else None)
    href = lambda x: f'{x["page"]["meta"]["slug"]}.html' if x else None
    place = _place(w)
    room_name = r.get("label") or f"Porte {r['code']}"
    where = f'<b class="mu-gate">{r["code"]}</b><span>{escape(place)} · {escape(w["name"])}</span>'
    nav = ((f'<a href="{href(prev)}" title="{escape(prev["page"]["meta"]["title"])}">← {prev["code"]}</a>' if prev else "")
           + '<a href="index.html" title="Retour au hall et au plan">Hall</a>'
           + '<button class="mu-btn" id="mu-plan-btn" aria-expanded="false" aria-controls="mu-drawer" title="Plan du musée (touche P)">Plan</button>'
           + (f'<a href="{href(nxt)}" title="{escape(nxt["page"]["meta"]["title"])}">{nxt["code"]} →</a>' if nxt else ""))

    def door(x, cls, label):
        if not x:
            return f'<span class="mu-door {cls} off"></span>'
        return (f'<a class="mu-door {cls}" href="{href(x)}" style="--w:{x["wing"]["color"]}">'
                f'<small>{label} · {x["code"]}</small><b>{escape(x["page"]["meta"]["title"])}</b></a>')

    kicker = f"{escape(room_name)} · {escape(place)} — {escape(w['name'])} · salle {i + 1} sur {len(rooms)}"
    return (_head(f"{exhibit.title} — Musée Air France", exhibit.head_extra)
            + "<body>" + _sign(where, nav)
            + f'<div class="mu-wall"><section class="mu-cartel"><div class="mu-plaque" style="--w:{w["color"]}"><p class="mu-kicker">{kicker}</p>'
            + f'<h1>{escape(exhibit.title)}</h1><p class="lead">{exhibit.lead}</p></div>'
            + f'<button class="mu-thumb" data-mu-plan title="Ouvrir le plan du musée (touche P)">{plan_svg(m, current=slug, mini=True, links=False)}<span>Vous êtes ici · {r["code"]} · voir le plan</span></button></section>'
            + f'<main class="mu-vitrine">\n{exhibit.body}\n</main></div>'
            + f'<nav class="mu-doors" aria-label="Salles voisines">{door(prev, "prev", "← Salle précédente")}'
            + '<a class="mu-hallbtn" href="index.html"><span>⌂</span>Retour au hall</a>'
            + f'{door(nxt, "next", "Salle suivante →")}</nav>'
            + '<footer class="mu-foot">Musée Air France · les éphémérides en données · ← → pour changer de salle, P pour le plan</footer>'
            + f'<div class="mu-drawer" id="mu-drawer" hidden><div class="mu-drawer-box" role="dialog" aria-label="Plan du musée">'
            + '<div class="mu-drawer-head"><span>Plan du musée · vous êtes en ' + r["code"] + '</span><button class="mu-close">Fermer ✕</button></div>'
            + plan_svg(m, current=slug, mini=True) + _legend(m, slug) + "</div></div>"
            + f"<script>{exhibit.script}</script><script>{_nav_script(m, slug, href(prev), href(nxt))}</script></body></html>")


def render_home(pages, ctx):
    m = museum(pages)
    texts = f"{ctx['texts']:,}".replace(",", " ")
    open_rooms = [r for r in m["rooms"] if not r["page"]["error"]]
    piers = sum(1 for w in m["wings"] if w["kind"] == "jetee")
    data = [{"slug": r["page"]["meta"]["slug"], "href": f'{r["page"]["meta"]["slug"]}.html', "code": r["code"],
             "wing": f'{_place(r["wing"])} · {r["wing"]["name"]}',
             "color": r["wing"]["color"], "title": r["page"]["meta"]["title"], "desc": r["page"]["meta"]["description"],
             "closed": bool(r["page"]["error"]), "path": [[round(x), round(y)] for x, y in r["path"]]} for r in m["rooms"]]

    rows = []
    for k, r in enumerate(m["rooms"]):
        meta, w = r["page"]["meta"], r["wing"]
        hour = f"{9 + (k * 15) // 60:02d}:{(k * 15) % 60:02d}"
        status = '<span class="mu-st ko">Fermée</span>' if r["page"]["error"] else '<span class="mu-st go">Embarquement</span>'
        dest = escape(meta["title"]) if r["page"]["error"] else f'<a href="{meta["slug"]}.html">{escape(meta["title"])}</a>'
        rows.append(f'<tr data-slug="{meta["slug"]}"><td class="mu-flap">{hour}</td><td class="mu-flap">MAF {101 + k}</td>'
                    f'<td class="mu-dest">{dest}</td><td><span class="mu-gate" style="--w:{w["color"]}">{r["code"]}</span></td>'
                    f'<td>{escape(w["name"])}</td><td>{status}</td></tr>')
    stamps = "".join(f'<i data-slug="{r["page"]["meta"]["slug"]}" style="--w:{r["wing"]["color"]}" title="{r["code"]} · {escape(r["page"]["meta"]["title"])}"></i>' for r in open_rooms)

    first = open_rooms[0]["page"]["meta"]["slug"] if open_rooms else "index"
    nav = (f'<a href="{first}.html">Commencer la visite →</a>' if open_rooms else "") + '<a href="#mu-departs">Départs</a>'
    body = f"""
<main class="mu-home">
  <section class="mu-hero">
    <div><p class="mu-kicker">Aérogare des éphémérides · {len(open_rooms)} salles</p>
      <h1>Bienvenue au Musée Air France</h1>
      <p class="mu-lead">{texts} éphémérides de la compagnie, lues et structurées une à une, exposées dans une aérogare : {piers} jetées, un hall d'accueil et un Concorde à quai. Chaque porte ouvre une salle. Cliquez sur une salle du plan pour vous y rendre.</p></div>
    <div class="mu-ticket"><div><small>Carte d'embarquement · passager</small><span class="mu-big">Visiteur</span>
        <small style="margin-top:8px">Salles visitées</small><span class="mu-big" data-mu-visits>0</span><div class="mu-stamps">{stamps}</div></div>
      <div class="mu-stub"><small>Prochaine porte</small><span id="mu-next"></span><a id="mu-go" href="{first}.html">Commencer la visite →</a></div></div>
  </section>
  <section class="mu-planwrap">{plan_svg(m)}
    <div class="mu-info" id="mu-info" aria-live="polite"><b>Vous êtes à l'entrée</b><p>Survolez une salle pour lire son cartel, cliquez pour vous y rendre. Le point rouge, c'est vous.</p></div></section>
  <p class="mu-hint">Dans chaque salle : les portes en bas de page et les flèches ← → du clavier mènent aux salles voisines, la touche P affiche le plan. Les salles visitées sont cochées (mémorisées dans ce navigateur).</p>
  <section class="mu-board" id="mu-departs"><h2><span>✈</span> DÉPARTS · TOUTES LES SALLES</h2>
    <table><thead><tr><th>Heure</th><th>Vol</th><th>Salle</th><th>Porte</th><th>Aile</th><th>Statut</th></tr></thead><tbody>{"".join(rows)}</tbody></table></section>
</main>
<footer class="mu-foot">Musée Air France · les éphémérides en données</footer>"""
    return (_head("Musée Air France — l'aérogare des éphémérides")
            + "<body>" + _sign("<span>Hall d'accueil · Plan du musée</span>", nav) + body
            + f"<script>{_nav_script(m)}</script><script>{HOME_JS.replace('__ROOMS__', json.dumps(data, ensure_ascii=False))}</script></body></html>")
