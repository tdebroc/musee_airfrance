"""Designs (habillages) of the site, interchangeable without touching the pages.

A design module exposes:
  NAME = "..."                                   short description, printed by build_site.py
  render_room(exhibit, slug, pages, ctx) -> str  full HTML of site/<slug>.html around one Exhibit
  render_home(pages, ctx) -> str                 full HTML of site/index.html
where
  pages = [{"meta": META, "error": None | "message"}, ...]   every page module, in META["order"]
  ctx   = {"texts": number of éphémérides}
The design must define the CSS variables used by the exhibits (--bg --card --ink --muted --line
--accent --accent2) and the .card class, and must not put a transformed ancestor around the exhibit
(several exhibits position their tooltips with position:fixed).

Choose one with: .venv/bin/python build_site.py --design sobre
"""
import importlib
import pkgutil

DEFAULT = "musee"


def available():
    return sorted(info.name for info in pkgutil.iter_modules(__path__))


def load(name=None):
    name = name or DEFAULT
    if name not in available():
        raise SystemExit(f"design inconnu : {name} (disponibles : {', '.join(available())})")
    return importlib.import_module(f"design.{name}")
