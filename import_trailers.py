"""თრეილერების იმპორტი data/trailers.json-იდან — trailer_key ფილმებზე/სერიალებზე.

გამოყენება:
    python import_trailers.py            # ნაგულისხმევად data/trailers.json
    python import_trailers.py path.json

წყარო: ge.movie დეტალურ გვერდზე თრეილერის ღილაკის data-url
(videodb.cloud/embed/trailers.php?type=...&id=<YouTubeKey>) — იხ. scrapers/03_trailers.js.
ვინახავთ YouTube key-ს (trailer_key), დეტალურ გვერდზე YouTube embed-ად უკრავს.
"""
import re
import sys
import json

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from flask import Flask
from config import Config
from models import db, Movie, Series


def ytkey(url):
    m = re.search(r"[?&]id=([^&]+)", url or "")
    return m.group(1) if m else None


def import_file(path):
    data = json.load(open(path, "r", encoding="utf-8"))
    nm = ns = 0
    for e in data:
        key = ytkey(e.get("trailer"))
        if not e.get("id") or not key:
            continue
        if e.get("type") == "series":
            r = db.session.get(Series, e["id"])
            if r:
                r.trailer_key = key
                ns += 1
        else:
            r = db.session.get(Movie, e["id"])
            if r:
                r.trailer_key = key
                nm += 1
    db.session.commit()
    print(f"✓ თრეილერი — ფილმი: {nm}, სერიალი: {ns}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/trailers.json"
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    with app.app_context():
        db.create_all()
        import_file(path)
