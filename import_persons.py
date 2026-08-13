"""მსახიობების იმპორტი data/persons.json-იდან ბაზაში.

გამოყენება:
    python import_persons.py            # ნაგულისხმევად data/persons.json
    python import_persons.py path.json

წყარო: ge.movie /person/<id> გვერდები (იხ. scrapers/02_persons.js).
სახელი ge.movie-ზე ინახება ფორმით "ქართული / English, ფილმები, ..." — ვასუფთავებთ.
photo == '/512.png' ge.movie-ს ნაგულისხმევი „ფოტო არ არის" — ვცლით.
"""
import sys
import json

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from flask import Flask
from config import Config
from models import db, Person


def clean_name(raw):
    first = (raw or "").split(",")[0].strip()
    if " / " in first:
        ka, en = first.split(" / ", 1)
        return ka.strip(), en.strip()
    return first, ""


def import_file(path):
    data = json.load(open(path, "r", encoding="utf-8"))
    Person.query.delete()
    n = 0
    for e in data:
        if not e.get("id") or not (e.get("name") or "").strip():
            continue
        ka, en = clean_name(e["name"])
        photo = e.get("photo") or ""
        if not photo.startswith("http"):  # /512.png და მისთ. — ნაგულისხმევი placeholder
            photo = ""
        db.session.add(Person(
            id=e["id"], name=ka, name_en=en, photo=photo,
            url=e.get("url"),
            popularity=1.0 if photo else 0.0,  # ფოტოიანები წინ დალაგდნენ
        ))
        n += 1
    db.session.commit()
    print(f"✓ მსახიობი: {n}, ფოტოთი: {Person.query.filter(Person.photo.like('http%')).count()}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/persons.json"
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    with app.app_context():
        db.create_all()
        import_file(path)
