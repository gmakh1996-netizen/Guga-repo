"""ავტომატური სინქრონიზაცია TMDB-დან ბაზაში.

ეს არის ის "ავტომატური მოტანა":
  • პირველი გაშვება — ავსებს ბაზას პოპულარული/ტრენდული/ახალი ფილმებით.
  • შემდეგი გაშვებები — ამატებს ახლებს და აახლებს არსებულებს (ინკრემენტული).

გაშვება ხელით:      python sync.py
გაშვება cron-ით:    ყოველ 6 საათში (იხ. README).
ავტომატურად აპში:   app.py უშვებს ამ ფუნქციას APScheduler-ით ყოველ 6 საათში.

აბრუნებს სტატისტიკის dict-ს: found / new / updated / skipped / errors.
"""
import os
import sys
from datetime import datetime, timezone

# Windows-ის კონსოლში ქართული ტექსტის უსაფრთხო დაბეჭდვა
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from config import Config
from models import db, Movie, Series, Genre
import tmdb

# ცალკე error-ლოგი
LOG_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "logs")
ERROR_LOG = os.path.join(LOG_DIR, "sync_errors.log")


def _log(msg):
    """[SYNC] პრეფიქსით ლოგი კონსოლში."""
    print(f"[SYNC] {msg}")


def _log_error(msg):
    """შეცდომა კონსოლში + ცალკე ფაილში."""
    print(f"[SYNC] ! {msg}")
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} {msg}\n")
    except Exception:  # noqa: BLE001
        pass  # ლოგირება არასდროს აჩერებს სინქრონიზაციას


def sync_genres():
    """ჟანრების ცნობარის განახლება (ფილმი + სერიალი)."""
    for g in tmdb.genre_list() + tmdb.tv_genre_list():
        genre = db.session.get(Genre, g["id"])
        if genre is None:
            genre = Genre(id=g["id"], name=g["name"])
            db.session.add(genre)
        else:
            genre.name = g["name"]
    db.session.commit()


def _upsert_movie(item, with_details=True):
    """ერთი ფილმის ჩაწერა/განახლება. აბრუნებს 'new' | 'updated' | 'skipped'."""
    movie_id = item.get("id")
    if not movie_id:
        return "skipped"

    existing = db.session.get(Movie, movie_id)
    is_new = existing is None
    movie = existing or Movie(id=movie_id)

    # საბაზისო ველები (მოდის სიის ან დეტალების response-იდან)
    movie.title = item.get("title") or item.get("original_title") or "უცნობი"
    movie.original_title = item.get("original_title")
    movie.overview = item.get("overview") or movie.overview
    movie.poster_path = item.get("poster_path") or movie.poster_path
    movie.backdrop_path = item.get("backdrop_path") or movie.backdrop_path
    movie.release_date = item.get("release_date") or movie.release_date
    movie.vote_average = item.get("vote_average", movie.vote_average or 0)
    movie.vote_count = item.get("vote_count", movie.vote_count or 0)
    movie.popularity = item.get("popularity", movie.popularity or 0)

    # ჟანრები სიიდან მოდის როგორც genre_ids, დეტალებიდან — genres
    genre_ids = item.get("genre_ids")
    if genre_ids is None and item.get("genres"):
        genre_ids = [g["id"] for g in item["genres"]]
    if genre_ids:
        movie.genres = [
            g for g in (db.session.get(Genre, gid) for gid in genre_ids) if g
        ]

    # სრული დეტალები (runtime, ტრეილერი, tagline, imdb) — მხოლოდ ახალ ფილმებზე
    if with_details and is_new:
        try:
            details = tmdb.movie_details(movie_id)
            movie.runtime = details.get("runtime")
            movie.tagline = details.get("tagline")
            movie.imdb_id = details.get("imdb_id")
            movie.overview = details.get("overview") or movie.overview
            movie.trailer_key = tmdb.pick_trailer(details.get("videos"))
        except tmdb.TMDBError as e:
            _log_error(f"დეტალები ვერ ჩამოვიდა movie#{movie_id}: {e}")

    if is_new:
        db.session.add(movie)
    return "new" if is_new else "updated"


def _upsert_series(item, with_details=True):
    """ერთი სერიალის ჩაწერა/განახლება. აბრუნებს 'new' | 'updated' | 'skipped'."""
    tv_id = item.get("id")
    if not tv_id:
        return "skipped"

    existing = db.session.get(Series, tv_id)
    is_new = existing is None
    series = existing or Series(id=tv_id)

    # TV-ში სათაური = name, თარიღი = first_air_date
    series.title = item.get("name") or item.get("original_name") or "უცნობი"
    series.original_title = item.get("original_name")
    series.overview = item.get("overview") or series.overview
    series.poster_path = item.get("poster_path") or series.poster_path
    series.backdrop_path = item.get("backdrop_path") or series.backdrop_path
    series.release_date = item.get("first_air_date") or series.release_date
    series.vote_average = item.get("vote_average", series.vote_average or 0)
    series.vote_count = item.get("vote_count", series.vote_count or 0)
    series.popularity = item.get("popularity", series.popularity or 0)

    genre_ids = item.get("genre_ids")
    if genre_ids is None and item.get("genres"):
        genre_ids = [g["id"] for g in item["genres"]]
    if genre_ids:
        series.genres = [
            g for g in (db.session.get(Genre, gid) for gid in genre_ids) if g
        ]

    if with_details and is_new:
        try:
            details = tmdb.tv_details(tv_id)
            series.tagline = details.get("tagline")
            series.number_of_seasons = details.get("number_of_seasons")
            series.number_of_episodes = details.get("number_of_episodes")
            series.overview = details.get("overview") or series.overview
            series.trailer_key = tmdb.pick_trailer(details.get("videos"))
        except tmdb.TMDBError as e:
            _log_error(f"დეტალები ვერ ჩამოვიდა tv#{tv_id}: {e}")

    if is_new:
        db.session.add(series)
    return "new" if is_new else "updated"


def _ingest(items, upsert_fn, seen, stats, label):
    """items-ის სია → ბაზა. ერთი ჩანაწერის შეცდომა არ აჩერებს დანარჩენს."""
    for item in items:
        iid = item.get("id")
        if iid is None:
            stats["skipped"] += 1
            continue
        if iid in seen:
            stats["skipped"] += 1  # იმავე გაშვებაში დუბლიკატი
            continue
        seen.add(iid)
        stats["found"] += 1
        try:
            status = upsert_fn(item)
            if status in ("new", "updated"):
                stats[status] += 1
            else:
                stats["skipped"] += 1
        except Exception as e:  # noqa: BLE001
            stats["errors"] += 1
            _log_error(f"{label} #{iid} parsing ჩავარდა: {e}")


def sync_all(pages=2):
    """მთავარი სინქრონიზაცია — ივსება რამდენიმე კატეგორიიდან.

    აბრუნებს: {"found", "new", "updated", "skipped", "errors",
               "total_movies", "total_series"}.
    """
    started = datetime.now(timezone.utc)
    _log(f"Starting... ({started:%Y-%m-%d %H:%M} UTC)")
    stats = {"found": 0, "new": 0, "updated": 0, "skipped": 0, "errors": 0}

    try:
        sync_genres()
    except tmdb.TMDBError as e:
        _log_error(f"ჟანრები ვერ ჩამოვიდა: {e}")

    this_year = started.year

    # ---- ფილმები ----
    movie_seen = set()

    # უახლესი რელიზები — მიმდინარე + წინა წლის ცნობადი ფილმები (პოსტერით).
    # popularity.desc + vote_count ფილტრი, რომ არ შემოვიდეს უპოსტერო „ხმაური“.
    for yr in (this_year, this_year - 1):
        for page in range(1, pages + 1):
            try:
                items = tmdb.discover_movie(
                    page=page,
                    primary_release_year=yr,
                    sort_by="popularity.desc",
                    **{"vote_count.gte": 10},
                )
            except tmdb.TMDBError as e:
                _log_error(f"discover {yr} გვ.{page}: {e}")
                break
            items = [it for it in items if it.get("poster_path")]  # მხოლოდ პოსტერიანი
            _log(f"Movies · newest {yr} · page {page}: {len(items)} found")
            _ingest(items, _upsert_movie, movie_seen, stats, "movie")
        db.session.commit()

    # ტრენდი + კატეგორიები
    try:
        trending = tmdb.trending("week")
        _log(f"Movies · trending week: {len(trending)} found")
        _ingest(trending, _upsert_movie, movie_seen, stats, "movie")
    except tmdb.TMDBError as e:
        _log_error(f"trending: {e}")

    movie_sources = {
        "popular": tmdb.popular,
        "top_rated": tmdb.top_rated,
        "now_playing": tmdb.now_playing,
        "upcoming": tmdb.upcoming,
    }
    for name, fn in movie_sources.items():
        for page in range(1, pages + 1):
            try:
                items = fn(page=page)
            except tmdb.TMDBError as e:
                _log_error(f"{name} გვ.{page}: {e}")
                break
            _log(f"Movies · {name} · page {page}: {len(items)} found")
            _ingest(items, _upsert_movie, movie_seen, stats, "movie")
        db.session.commit()

    # ---- სერიალები (TV) ----
    tv_seen = set()
    try:
        tv_trend = tmdb.tv_trending("week")
        _log(f"Series · trending week: {len(tv_trend)} found")
        _ingest(tv_trend, _upsert_series, tv_seen, stats, "series")
    except tmdb.TMDBError as e:
        _log_error(f"tv trending: {e}")

    tv_sources = {
        "tv_popular": tmdb.tv_popular,
        "tv_top_rated": tmdb.tv_top_rated,
        "tv_on_the_air": tmdb.tv_on_the_air,
    }
    for name, fn in tv_sources.items():
        for page in range(1, pages + 1):
            try:
                items = fn(page=page)
            except tmdb.TMDBError as e:
                _log_error(f"{name} გვ.{page}: {e}")
                break
            _log(f"Series · {name} · page {page}: {len(items)} found")
            _ingest(items, _upsert_series, tv_seen, stats, "series")
        db.session.commit()

    db.session.commit()
    stats["total_movies"] = db.session.query(Movie).count()
    stats["total_series"] = db.session.query(Series).count()

    took = (datetime.now(timezone.utc) - started).total_seconds()
    _log(
        f"Finished in {took:.0f}s · Found: {stats['found']} · "
        f"New: {stats['new']} · Updated: {stats['updated']} · "
        f"Skipped: {stats['skipped']} · Errors: {stats['errors']}"
    )
    _log(f"DB now: {stats['total_movies']} movies, {stats['total_series']} series")
    return stats


if __name__ == "__main__":
    # დამოუკიდებელი გაშვება (cron-ისთვის) — ვქმნით მინიმალურ აპ-კონტექსტს
    from flask import Flask

    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    with app.app_context():
        db.create_all()
        sync_all()
