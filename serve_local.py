"""Sert ephemerides.html en local, au même chemin que sur le site, pour tester le fil d'Ariane et le menu.

Le menu, le pied de page et les scripts utilisent des chemins absolus (/musee/fr/menuHorizontal/menuh.json...) :
un simple `python3 -m http.server` ne les trouve pas. Ici, seule la page est servie depuis le disque,
tout le reste de /musee/ est relayé vers le vrai site.

Usage : python3 serve_local.py [chemin_de_la_page] [port]
Puis ouvrir http://127.0.0.1:8123/musee/files/ephemerides_2.html
(127.0.0.1 et non localhost : "localhost" peut pointer vers IPv6, où un autre serveur peut écouter sur le même port.)
"""
import http.server
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
PAGE_PATH = sys.argv[1] if len(sys.argv) > 1 else "/musee/files/ephemerides_2.html"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8123
REMOTE = "https://musee.airfrance.fr"


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == PAGE_PATH:
            # Relu à chaque requête : regénérer la page puis recharger suffit.
            body, content_type = (HERE / "ephemerides.html").read_bytes(), "text/html; charset=utf-8"
        else:
            try:
                response = urllib.request.urlopen(REMOTE + self.path, timeout=30)
            except Exception as error:
                self.send_error(502, str(error))
                return
            body, content_type = response.read(), response.headers.get("Content-Type", "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"http://127.0.0.1:{PORT}{PAGE_PATH}")
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
