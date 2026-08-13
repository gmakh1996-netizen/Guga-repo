"""დეტალური მეტამონაცემის შევსება TMDB-დან (იგივე წყარო, რომელსაც ge.movie იყენებს —
ge.movie-ს პოსტერები/მსახიობთა ფოტოებიც image.tmdb.org-იდანაა).

ავსებს: studio, director, country, runtime, budget, revenue, cast[{name, photo}].
მსახიობის სახელი ქართულად აიღება `data/persons.json`-იდან (თუ ემთხვევა en-სახელი),
თორემ რჩება ორიგინალი; ფოტო — TMDB profile.

გამოყენება:
    python enrich_tmdb.py 1304 49832 1379      # კონკრეტული id-ები
    python enrich_tmdb.py --missing 200        # პირველი N ფილმი ცარიელი studio-თი
"""
import sys
import json

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from flask import Flask
from config import Config
from models import db, Movie
import tmdb

IMG = "https://image.tmdb.org/t/p/w300"

# ISO 3166-1 → ქართული (ge.movie-ს სტილში); უცნობი კოდი → TMDB-ს ინგლ. სახელი
COUNTRY_KA = {
    "US": "აშშ", "GB": "დიდი ბრიტანეთი", "FR": "საფრანგეთი", "DE": "გერმანია",
    "IT": "იტალია", "ES": "ესპანეთი", "RU": "რუსეთი", "JP": "იაპონია",
    "CN": "ჩინეთი", "KR": "სამხრეთ კორეა", "IN": "ინდოეთი", "CA": "კანადა",
    "AU": "ავსტრალია", "TR": "თურქეთი", "GE": "საქართველო", "UA": "უკრაინა",
    "SE": "შვედეთი", "NO": "ნორვეგია", "DK": "დანია", "NL": "ნიდერლანდები",
    "BE": "ბელგია", "MX": "მექსიკა", "BR": "ბრაზილია", "AR": "არგენტინა",
    "PL": "პოლონეთი", "CZ": "ჩეხეთი", "IE": "ირლანდია", "NZ": "ახალი ზელანდია",
    "HK": "ჰონგ კონგი", "TH": "ტაილანდი", "IR": "ირანი", "IL": "ისრაელი",
    "FI": "ფინეთი", "AT": "ავსტრია", "CH": "შვეიცარია", "GR": "საბერძნეთი",
}


def country_ka(c):
    return COUNTRY_KA.get(c.get("iso_3166_1"), c.get("name"))


def load_person_index():
    """{en_name_lower: ka_name} `data/persons.json`-იდან (name = 'ka / en, ...')."""
    idx = {}
    try:
        data = json.load(open("data/persons.json", encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return idx
    for p in data if isinstance(data, list) else []:
        nm = (p.get("name") or "").split(",")[0]
        if " / " in nm:
            ka, en = nm.split(" / ", 1)
            ka, en = ka.strip(), en.strip().lower()
            if ka and en:
                idx.setdefault(en, ka)
    return idx


def pick_match(results, want_year):
    """TMDB search-შედეგებიდან საუკეთესო: ჯერ წლის დამთხვევა, მერე პოპულარობა."""
    if not results:
        return None
    if want_year:
        exact = [r for r in results if (r.get("release_date") or "")[:4] == str(want_year)]
        if exact:
            return max(exact, key=lambda r: r.get("popularity", 0))
    return max(results, key=lambda r: r.get("popularity", 0))


def enrich_one(rec, pidx):
    q = rec.original_title or rec.title
    try:
        results = tmdb.search(q)
    except tmdb.TMDBError as e:
        print(f"  ! search fail {rec.id} {q}: {e}")
        return False
    m = pick_match(results, rec.year)
    if not m:
        print(f"  - no TMDB match: {rec.id} {q} ({rec.year})")
        return False
    try:
        d = tmdb.movie_details(m["id"])
    except tmdb.TMDBError as e:
        print(f"  ! details fail {rec.id}: {e}")
        return False

    rec.studio = ", ".join(c["name"] for c in d.get("production_companies", [])[:3]) or rec.studio
    rec.country = ", ".join(country_ka(c) for c in d.get("production_countries", [])) or rec.country
    crew = d.get("credits", {}).get("crew", [])
    directors = [c["name"] for c in crew if c.get("job") == "Director"]
    if directors:
        rec.director = ", ".join(directors)
    if d.get("runtime"):
        rec.runtime = d["runtime"]
    if d.get("budget"):
        rec.budget = d["budget"]
    if d.get("revenue"):
        rec.revenue = d["revenue"]
    if not rec.vote_average and d.get("vote_average"):
        rec.vote_average = d["vote_average"]
    if not rec.vote_count and d.get("vote_count"):
        rec.vote_count = d["vote_count"]

    cast = []
    for c in d.get("credits", {}).get("cast", [])[:15]:
        en = (c.get("name") or "").strip()
        if not en:
            continue
        name = pidx.get(en.lower(), en)  # ქართული თუ ვიპოვეთ
        photo = IMG + c["profile_path"] if c.get("profile_path") else None
        cast.append({"name": name, "photo": photo})
    if cast:
        rec.cast_json = json.dumps(cast, ensure_ascii=False)
    return True


def main():
    args = sys.argv[1:]
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    with app.app_context():
        pidx = load_person_index()
        print(f"persons index: {len(pidx)} ka-names")
        if args and args[0] == "--missing":
            n = int(args[1]) if len(args) > 1 else 100
            recs = (Movie.query.filter(Movie.studio.is_(None))
                    .order_by(Movie.popularity.desc()).limit(n).all())
        else:
            ids = [int(a) for a in args] or [1304, 49832, 1379]
            recs = [db.session.get(Movie, i) for i in ids]
            recs = [r for r in recs if r]
        ok = 0
        for rec in recs:
            print(f"→ {rec.id} {rec.original_title or rec.title} ({rec.year})")
            if enrich_one(rec, pidx):
                ok += 1
                db.session.commit()
        print(f"\n✓ შევსდა: {ok}/{len(recs)}")


if __name__ == "__main__":
    main()
