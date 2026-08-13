"""ვიდეო-წყაროების იმპორტი JSON-იდან ბაზაში.

გამოყენება:
    python import_streams.py data.json

მხარდაჭერილი JSON ფორმატები (ორივე მუშაობს):

1) სრული ფორმატი — streams მასივით (იხ. streams_demo.json):
[
  {
    "id": 10331,                 # TMDB id თუ არსებობს (არასავალდებულო)
    "title": "...",
    "year": 1968,
    "overview": "...",
    "poster_url": "https://...",
    "streams": [
      {"language": "en", "label": "ინგლისური", "kind": "embed", "url": "https://..."}
    ]
  }
]

2) ბრტყელი ფორმატი — scraper-ის გამონატანი (იხ. data.json):
[
  {"title": "...", "url": "...", "stream_url": "https://embed..."},
  {"title": "...", "url": "...", "player": "https://embed..."}
]
   ამ ფორმატში stream_url / player ავტომატურად იქცევა ქართულ embed წყაროდ.

დამთხვევა (dedup): თუ id არ არის, ჩანაწერი ეძებება სათაურით. ასე data.json-ის
ქართული წყარო ებმის უკვე არსებულ TMDB ფილმს ახალი ჩანაწერის შექმნის ნაცვლად,
და ხელახალი გაშვება არ ამრავლებს ჩანაწერებს.

წყარო (url) თავად უნდა იყოს ლეგალური: public-domain, საკუთარი/ლიცენზირებული,
ან ლეგალური embed. სკრიპტი მხოლოდ ბმულს წერს, არა ვიდეო-ფაილს.
"""
import re
import sys
import json

# Windows-ის კონსოლში ქართული ტექსტის უსაფრთხო დაბეჭდვა
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from flask import Flask

from config import Config
from models import db, Movie, Series, Stream, Genre


# kinomigma-ს ჟანრები, რომლებიც კატეგორიაა და არა ნამდვილი ჟანრი → გამოტოვება
GENRE_SKIP = {
    "ფილმები", "სერიალები", "ჩვენი გახმოვანებული", "ტრეილერები",
    "მალე", "თურქული სერიალები",
}

# kinomigma-ს სახელი → TMDB-ის არსებული ჟანრის სახელი (მართლწერა/სინონიმი)
GENRE_ALIAS = {
    "თრილერი": "ტრილერი",
    "ისტორიული": "ისტორია",
    "ანიმაცია": "მულტფილმი",
    "მუსიკალური": "მუსიკა",
    "მიუზიკლი": "მუსიკა",
    "რომანტიკული": "მელოდრამა",
    "მძაფრ-სიუჟეტიანი": "მძაფრსიუჟეტიანი",
    "საშინელებათა": "საშინელება",
    "ბოევიკი": "მძაფრსიუჟეტიანი",
    "მისტიური": "დეტექტივი",
}

# ახალი ჟანრების id-ები ამ ბაზიდან, TMDB id-ებთან შეჯახების გარეშე
NEW_GENRE_ID_BASE = 900_000_000


def normalize_title(title):
    """სათაურის ნორმალიზება დამთხვევისთვის (რეგისტრი/ზედმეტი ხარვეზები)."""
    t = (title or "").strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t


def extract_streams(entry):
    """აბრუნებს stream-dict-ების სიას ორივე ფორმატიდან.

    - entry["streams"]: სრული ფორმატი (ინახება როგორც არის)
    - entry["stream_url"] / entry["player"]: ბრტყელი ფორმატი → ქართული embed
    """
    streams = []
    seen = set()

    def add(url, label="ქართულად", language="ka", kind="embed"):
        url = (url or "").strip()
        if not url:
            return
        # პროტოკოლის გარეშე ბმულის ნორმალიზება (მაგ. //ok.ru/...)
        if url.startswith("//"):
            url = "https:" + url
        if url in seen:
            return
        seen.add(url)
        streams.append(
            {"language": language, "label": label, "kind": kind, "url": url}
        )

    # 1) სრული ფორმატი — streams მასივი
    for s in entry.get("streams", []) or []:
        add(
            s.get("url"),
            label=s.get("label", "ქართულად"),
            language=s.get("language", "ka"),
            kind=s.get("kind", "embed"),
        )

    # 2) kinomigma.json — players მასივი (რამდენიმე სარკე/წყარო)
    players = entry.get("players")
    if isinstance(players, list):
        multi = len([p for p in players if (p or {}).get("source")]) > 1
        n = 0
        for p in players:
            src = (p or {}).get("source")
            if not (src or "").strip():
                continue
            n += 1
            add(src, label=(f"ქართულად {n}" if multi else "ქართულად"))

    # 3) ბრტყელი ფორმატი — stream_url ან player (ერთი ბმული)
    for field in ("stream_url", "player"):
        add(entry.get(field))

    return streams


def find_existing(Model, entry, title_index):
    """არსებული ჩანაწერის მოძებნა.

    თუ id მოცემულია — მხოლოდ id-ით (ავტორიტეტული, სათაურით არ ვაერთიანებთ,
    რომ ერთი და იმავე სახელის განსხვავებული ფილმები არ შეერწყას).
    თუ id არ არის — სათაურით.
    """
    rec_id = entry.get("id")
    if rec_id:
        return db.session.get(Model, rec_id)
    key = normalize_title(entry.get("title"))
    return title_index.get(key)


def build_title_index(Model):
    """{ნორმალიზებული სათაური -> ჩანაწერი}. TMDB-ჩანაწერი (poster_path) პრიორიტეტში."""
    index = {}
    for rec in Model.query.all():
        key = normalize_title(rec.title)
        if not key:
            continue
        current = index.get(key)
        # პრიორიტეტი ნამდვილ TMDB ჩანაწერს (poster_path არსებობს)
        if current is None or (not current.poster_path and rec.poster_path):
            index[key] = rec
    return index


def parse_genres(genre_str):
    """kinomigma-ს "ფილმები / დრამა / თრილერი" → კანონიკური ჟანრის სახელების სია."""
    names = []
    for tok in (genre_str or "").split("/"):
        tok = tok.strip()
        if not tok or tok in GENRE_SKIP:
            continue
        name = GENRE_ALIAS.get(tok, tok)
        if name not in names:
            names.append(name)
    return names


def make_genre_resolver():
    """აბრუნებს ფუნქციას, რომელიც სახელით პოულობს/ქმნის Genre-ს (ქეშით)."""
    cache = {g.name: g for g in Genre.query.all()}
    existing_ids = {g.id for g in cache.values()}
    counter = {"next": NEW_GENRE_ID_BASE + 1}

    def resolve(name):
        g = cache.get(name)
        if g is not None:
            return g
        while counter["next"] in existing_ids:
            counter["next"] += 1
        g = Genre(id=counter["next"], name=name)
        existing_ids.add(g.id)
        counter["next"] += 1
        db.session.add(g)
        db.session.flush()
        cache[name] = g
        return g

    return resolve


def import_file(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    movie_index = build_title_index(Movie)
    series_index = build_title_index(Series)
    resolve_genre = make_genre_resolver()

    added = 0
    linked = 0          # არსებულ ჩანაწერს მიბმული
    added_streams = 0
    skipped = 0

    for entry in data:
        title = (entry.get("title") or "").strip()
        # ცარიელი/გაფუჭებული ჩანაწერების გამოტოვება (title აუცილებელია)
        if not title:
            skipped += 1
            continue

        streams = extract_streams(entry)
        # ველების სახელები განსხვავდება წყაროებში (overview/description, poster_url/poster)
        overview = entry.get("overview") or entry.get("description")
        poster_url = entry.get("poster_url") or entry.get("poster")
        has_meta = bool(overview or entry.get("year") or poster_url)
        # წყაროც არ აქვს და მეტამონაცემიც არა (მაგ. კატეგორიის გვერდი) → გამოტოვება
        if not streams and not has_meta:
            skipped += 1
            continue

        is_tv = entry.get("type") == "series"
        Model = Series if is_tv else Movie
        index = series_index if is_tv else movie_index

        rec = find_existing(Model, entry, index)
        if rec is None:
            rec = Model(id=entry.get("id")) if entry.get("id") else Model()
            rec.title = title
            db.session.add(rec)
            db.session.flush()
            index[normalize_title(title)] = rec
            added += 1
        else:
            linked += 1

        # ge.movie source of truth — თუ ფრეშ scrape ველს გვაწვდის, გადავაწერთ;
        # თუ არა, ვტოვებთ არსებულს (რომ არაფერი წაიშალოს).
        rec.title = title or rec.title
        rec.overview = overview or rec.overview
        rec.poster_url = poster_url or rec.poster_url
        if entry.get("title_en"):
            rec.original_title = entry["title_en"]
        if entry.get("year"):
            rec.release_date = f"{entry['year']}-01-01"
        # რეიტინგი ge.movie-დან (მხოლოდ ვალიდური 0–10 დიაპაზონი)
        try:
            rating = float(entry.get("rating"))
        except (TypeError, ValueError):
            rating = None
        if rating is not None and 0 <= rating <= 10:
            rec.vote_average = rating
            rec.popularity = rating  # სორტირებისთვის
        if is_tv and entry.get("seasons"):
            rec.number_of_seasons = entry["seasons"]

        # ge.movie-ს დეტალური გვერდის მდიდარი ველები (გადავაწერთ ფრეშით)
        if entry.get("director"):
            rec.director = str(entry["director"])[:300]
        if entry.get("studio"):
            rec.studio = str(entry["studio"])[:300]
        if entry.get("country"):
            rec.country = str(entry["country"])[:300]
        try:
            runtime = int(entry.get("runtime"))
        except (TypeError, ValueError):
            runtime = None
        if runtime:
            rec.runtime = runtime
        for fld in ("budget", "revenue"):
            try:
                val = int(entry.get(fld))
            except (TypeError, ValueError):
                val = None
            if val:
                setattr(rec, fld, val)
        cast = entry.get("cast") or entry.get("actors")
        if isinstance(cast, list) and cast:
            # ვინახავთ [{name, photo}] ობიექტებს (photo არასავალდ.), მაქს. 30
            out = []
            for c in cast[:30]:
                if isinstance(c, dict):
                    nm = str(c.get("name") or "").strip()
                    if nm:
                        out.append({"name": nm, "photo": c.get("photo") or None})
                elif str(c).strip():
                    out.append({"name": str(c).strip(), "photo": None})
            if out:
                rec.cast_json = json.dumps(out, ensure_ascii=False)

        # ჟანრების მიბმა (ფილტრაცია საიტზე)
        for gname in parse_genres(entry.get("genre")):
            g = resolve_genre(gname)
            if g not in rec.genres:
                rec.genres.append(g)
        db.session.flush()

        # ძველი წყაროების ჩანაცვლება (იდემპოტენტური ხელახალი გაშვება)
        fk = {"series_id": rec.id} if is_tv else {"movie_id": rec.id}
        Stream.query.filter_by(**fk).delete()
        for i, s in enumerate(streams):
            db.session.add(
                Stream(
                    **fk,
                    language=s["language"],
                    label=s["label"],
                    kind=s["kind"],
                    url=s["url"],
                    sort=i,
                )
            )
            added_streams += 1

    db.session.commit()
    print(
        f"✓ ახალი ჩანაწერი: {added}, არსებულს მიბმული: {linked}, "
        f"წყარო: {added_streams}, გამოტოვებული: {skipped}"
    )
    return {
        "added": added,
        "linked": linked,
        "streams": added_streams,
        "skipped": skipped,
    }


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/movies.json"
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    with app.app_context():
        db.create_all()
        import_file(path)
