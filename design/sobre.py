"""Design « sobre » : the original look, a header bar and a grid of tiles on the home page."""
from html import escape

NAME = "sobre : bandeau et grille de tuiles"

STYLE = """
:root { --bg:#f6f7f9; --card:#fff; --ink:#14213d; --muted:#5c677d; --line:#dfe3ea; --accent:#002157; --accent2:#e3001b; }
@media (prefers-color-scheme: dark) { :root { --bg:#0e1420; --card:#161e2e; --ink:#e8ecf4; --muted:#9aa5b8; --line:#26324a; --accent:#7fb0ff; --accent2:#ff6b7a; } }
* { box-sizing:border-box; }
body { margin:0; font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; background:var(--bg); color:var(--ink); }
header.site { background:var(--accent); color:#fff; padding:14px 24px; display:flex; gap:16px; align-items:baseline; }
header.site a { color:#fff; text-decoration:none; }
header.site .home { font-weight:600; }
main { max-width:1200px; margin:0 auto; padding:24px; }
h1 { margin:0 0 4px; font-size:26px; } p.lead { color:var(--muted); margin:0 0 20px; max-width:70ch; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:16px; }
a { color:var(--accent); }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:14px; }
.tile { display:flex; flex-direction:column; gap:6px; padding:16px; background:var(--card); border:1px solid var(--line); border-radius:10px; text-decoration:none; color:var(--ink); }
.tile:hover { border-color:var(--accent); } .tile span { color:var(--muted); font-size:13px; } .tile.off { opacity:.5; }
"""


def _head(title, extra=""):
    return (f'<!doctype html>\n<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)}</title><style>{STYLE}</style>{extra}</head>')


def render_room(exhibit, slug, pages, ctx):
    return (_head(f"{exhibit.title} — Musée Air France", exhibit.head_extra)
            + f'<body><header class="site"><a class="home" href="index.html">← Musée Air France · éphémérides</a><span>{escape(exhibit.title)}</span></header>'
            + f'<main><h1>{escape(exhibit.title)}</h1><p class="lead">{exhibit.lead}</p>\n{exhibit.body}\n</main><script>{exhibit.script}</script></body></html>')


def render_home(pages, ctx):
    tiles = []
    for p in pages:
        m = p["meta"]
        if p["error"]:
            tiles.append(f'<div class="tile off"><b>{escape(m["title"])}</b><span>Indisponible : {escape(p["error"][:120])}</span></div>')
        else:
            tiles.append(f'<a class="tile" href="{m["slug"]}.html"><b>{escape(m["title"])}</b><span>{escape(m["description"])}</span></a>')
    texts = f"{ctx['texts']:,}".replace(",", " ")
    return (_head("Musée Air France — éphémérides en données")
            + '<body><header class="site"><span class="home">Musée Air France</span></header><main><h1>Les éphémérides en données</h1>'
            + f'<p class="lead">{len(pages)} visualisations tirées des {texts} éphémérides, structurées une à une par un modèle de langage.</p>'
            + f'<div class="grid">{"".join(tiles)}</div></main></body></html>')
