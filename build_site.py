"""Build the whole site into site/: one page per module in pages/, plus the home page.

Usage: .venv/bin/python build_site.py [--design NAME] [slug ...]     # no slug = every page
The pages (pages/*.py) only produce their content (an Exhibit); the design (design/*.py, default
"musee") produces the full HTML around it. After changing the design, rebuild every page.
A page that fails to build is reported and skipped; the home page still lists it, marked unavailable.
"""
import importlib
import pkgutil
import sys
import traceback

import design
import pages
from pages.common import HERE, Data, Exhibit

SITE = HERE / "site"


def discover():
    modules = []
    for info in pkgutil.iter_modules(pages.__path__):
        if info.name != "common" and not info.name.endswith("_data"):
            modules.append(importlib.import_module(f"pages.{info.name}"))
    return sorted(modules, key=lambda m: m.META.get("order", 99))


def main():
    args = sys.argv[1:]
    name = None
    if "--design" in args:
        i = args.index("--design")
        name = args[i + 1]
        del args[i:i + 2]
    theme = design.load(name)
    print(f"design {theme.NAME}")
    wanted = set(args)
    SITE.mkdir(exist_ok=True)
    data = Data()
    ctx = {"texts": len(data.raw)}
    modules = discover()
    info = [{"meta": m.META, "error": None} for m in modules]
    exhibits = {}
    for module, entry in zip(modules, info):
        slug = module.META["slug"]
        if wanted and slug not in wanted:
            continue  # kept on the home page; its existing file is left as is
        try:
            exhibits[slug] = module.build(data)
        except Exception as err:  # one broken page must not block the others
            entry["error"] = f"{type(err).__name__}: {err}"
            traceback.print_exc()
    for slug, exhibit in exhibits.items():
        html = theme.render_room(exhibit, slug, info, ctx) if isinstance(exhibit, Exhibit) else exhibit
        (SITE / f"{slug}.html").write_text(html)
        print(f"{slug}.html écrit")
    (SITE / "index.html").write_text(theme.render_home(info, ctx))
    print(f"index.html écrit ({len(info)} pages, {sum(1 for e in info if e['error'])} en échec)")


if __name__ == "__main__":
    main()
