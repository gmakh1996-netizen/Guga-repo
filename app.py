"""GEMOVIE — ლეგალური ფილმების კატალოგი (Flask + TMDB).

გაშვება:  python app.py   →  http://127.0.0.1:5000
"""
import atexit
import json
import os
from functools import wraps

from flask import Flask, render_template, request, abort, jsonify, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler

from config import Config
from models import db, Movie, Series, Genre, Person
import tmdb
from sync import sync_all


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_schema()

    register_routes(app)
    # TMDB ავტო-სინქი გათიშულია — საიტი მთლიანად kinomigma-ს მონაცემებზე დგას.
    # register_scheduler(app)
    return app


def ensure_schema():
    """არსებულ SQLite ბაზას დააკლდეს ახალი სვეტები (create_all არ აკეთებს ALTER-ს).

    ge.movie-ს მდიდარი ველები (director/studio/country/cast_json + series.runtime)
    ემატება იდემპოტენტურად — თუ სვეტი უკვე არსებობს, გამოტოვდება.
    """
    from sqlalchemy import text
    add = {
        "movie": [
            ("director", "VARCHAR(300)"), ("studio", "VARCHAR(300)"),
            ("country", "VARCHAR(300)"), ("cast_json", "TEXT"),
            ("budget", "BIGINT"), ("revenue", "BIGINT"),
            ("poster_portrait", "VARCHAR(400)"),
        ],
        "series": [
            ("director", "VARCHAR(300)"), ("studio", "VARCHAR(300)"),
            ("country", "VARCHAR(300)"), ("cast_json", "TEXT"),
            ("runtime", "INTEGER"), ("budget", "BIGINT"), ("revenue", "BIGINT"),
            ("poster_portrait", "VARCHAR(400)"),
        ],
    }
    for table, cols in add.items():
        try:
            existing = {
                row[1]
                for row in db.session.execute(text(f'PRAGMA table_info("{table}")'))
            }
        except Exception:  # noqa: BLE001 — ცხრილი ჯერ არ არსებობს
            continue
        for name, ddl in cols:
            if name not in existing:
                db.session.execute(
                    text(f'ALTER TABLE "{table}" ADD COLUMN {name} {ddl}')
                )
    db.session.commit()


def register_scheduler(app):
    """ავტომატური სინქრონიზაცია — ყოველ N საათში ფონურ რეჟიმში."""
    if app.config.get("TESTING"):
        return

    scheduler = BackgroundScheduler(daemon=True)

    def job():
        with app.app_context():
            try:
                sync_all()
            except Exception as e:  # noqa: BLE001
                app.logger.warning("Sync შეფერხდა: %s", e)

    hours = app.config.get("SYNC_INTERVAL_HOURS", 6)
    # ყოველ N საათში (ნაგულისხმევად 6)
    scheduler.add_job(job, "interval", hours=hours, id="periodic_sync")
    scheduler.start()
    app.logger.info("ავტო-სინქრონიზაცია ჩართულია: ყოველ %s საათში", hours)
    atexit.register(lambda: scheduler.shutdown(wait=False))


def require_admin(fn):
    """admin endpoint-ის დაცვა ADMIN_TOKEN-ით (Bearer ან X-Admin-Token)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        expected = Config.ADMIN_TOKEN
        # თუ token საერთოდ არ არის დაყენებული — endpoint დახურულია
        if not expected:
            return jsonify(error="ADMIN_TOKEN არ არის დაყენებული .env-ში"), 503
        auth = request.headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else request.headers.get(
            "X-Admin-Token", ""
        )
        if token != expected:
            return jsonify(error="არაავტორიზებული"), 401
        return fn(*args, **kwargs)

    return wrapper


def register_routes(app):
    @app.template_filter("streams_json")
    def streams_json(streams):
        """Stream ობიექტების სია → JSON სტრიქონი ფლეერისთვის."""
        data = [
            {"label": s.label or s.language or "წყარო", "kind": s.kind, "url": s.url}
            for s in sorted(streams, key=lambda s: s.sort or 0)
        ]
        return json.dumps(data, ensure_ascii=True)

    @app.context_processor
    def inject_globals():
        def img(path, size=app.config["POSTER_SIZE"]):
            if not path:
                return None
            if path.startswith("http"):  # სრული URL (მაგ. Archive.org) — პირდაპირ
                return path
            return f"{app.config['IMG_BASE']}/{size}{path}"

        return {
            "img": img,
            "all_genres": Genre.query.order_by(Genre.name).all(),
            "site_name": "Movie World",
        }

    @app.route("/favicon.ico")
    def favicon():
        return redirect(url_for("static", filename="favicon.ico"), code=301)

    @app.route("/")
    def index():
        # მთავარი გვერდი — მსუბუქი shell; რიგები/ჰერო AJAX-ით ივსება (/api/movies)
        return render_template("index.html")

    # ---------- JSON API (AJAX + infinite scroll) ----------
    def _model_for(media):
        return Series if media in ("serial", "tv", "series") else Movie

    def _serialize(rec):
        return {
            "id": rec.id,
            "type": "tv" if isinstance(rec, Series) else "movie",
            "title": rec.title,
            "title_en": rec.original_title or "",
            "year": rec.year or "",
            "rating": rec.rating or 0,
            "poster": rec.poster_url or "",
            "poster_portrait": rec.poster_portrait or "",
            "genres": [g.name for g in rec.genres][:3],
            "has_stream": bool(rec.streams),
            "url": ("/series/" if isinstance(rec, Series) else "/movie/") + str(rec.id),
        }

    @app.route("/api/movies")
    def api_movies():
        media = request.args.get("type", "movie")
        genre_id = request.args.get("genre", type=int)
        year = request.args.get("year", "").strip()
        sort = request.args.get("sort", "popularity")
        q = request.args.get("q", "").strip()
        page = max(request.args.get("page", 1, type=int), 1)
        per = min(request.args.get("per", 24, type=int), 60)

        # ძებნა — ორივე მოდელში (ფილმი + სერიალი)
        if media == "search" and q:
            combined = []
            for M in (Movie, Series):
                combined += M.query.filter(M.title.ilike(f"%{q}%")).order_by(
                    M.popularity.desc()
                ).limit(300).all()
            combined.sort(key=lambda x: x.popularity or 0, reverse=True)
            total = len(combined)
            items = combined[(page - 1) * per: page * per]
            return jsonify(
                items=[_serialize(x) for x in items], page=page, per=per,
                has_more=page * per < total, total=total,
            )

        Model = _model_for(media)
        query = Model.query
        if media == "trailer":  # თრეილერების გვერდი — ფილმები, რომლებსაც აქვთ თრეილერი
            Model = Movie
            query = Movie.query.filter(Movie.trailer_key.isnot(None))
        if genre_id:
            query = query.filter(Model.genres.any(Genre.id == genre_id))
        if year.isdigit():
            query = query.filter(Model.release_date.like(f"{year}%"))
        if q:
            query = query.filter(Model.title.ilike(f"%{q}%"))
        if sort == "rating":
            query = query.order_by(Model.vote_average.desc())
        elif sort == "newest":
            query = query.order_by(Model.release_date.desc())
        elif sort == "recent":
            # ge.movie-ს id თანმიმდევრულია → მაღალი id = ახლახან დამატებული
            query = query.order_by(Model.id.desc())
        elif sort == "trending":
            # „ბოლო კვირის პოპულარული" აპროქსიმაცია: უახლესი წელი პრიორიტეტში,
            # წლის შიგნით — მაღალი რეიტინგი (ge.movie-ს ცოცხალი view-count არ გვაქვ).
            # მხოლოდ ისეთი ფილმები, რომლებსაც ნამდვილი ფლეერი აქვთ (ატვირთული ფილმი,
            # არა მხოლოდ თრეილერი) + 0-რეიტინგიანი (ჯერ უნახავი) გამოვრიცხოთ.
            query = query.filter(Model.vote_average > 0, Model.streams.any()).order_by(
                Model.release_date.desc(), Model.vote_average.desc()
            )
        else:
            query = query.order_by(Model.popularity.desc(), Model.vote_average.desc())

        total = query.count()
        items = query.offset((page - 1) * per).limit(per).all()
        return jsonify(
            items=[_serialize(x) for x in items],
            page=page,
            per=per,
            has_more=page * per < total,
            total=total,
        )

    @app.route("/api/search")
    def api_search():
        q = request.args.get("q", "").strip()
        if len(q) < 2:
            return jsonify(items=[])
        movies = Movie.query.filter(Movie.title.ilike(f"%{q}%")).order_by(
            Movie.popularity.desc()
        ).limit(6).all()
        series = Series.query.filter(Series.title.ilike(f"%{q}%")).order_by(
            Series.popularity.desc()
        ).limit(4).all()
        return jsonify(items=[_serialize(x) for x in movies + series])

    def _similar_by_genre(Model, rec, limit=12):
        """მსგავსი ჩანაწერები იმავე ჟანრით (kinomigma-ს მიხედვით, TMDB-ს გარეშე)."""
        if not rec.genres:
            return []
        gid = rec.genres[0].id
        return (
            Model.query.filter(Model.id != rec.id, Model.genres.any(Genre.id == gid))
            .order_by(Model.popularity.desc())
            .limit(limit)
            .all()
        )

    def _cast_with_photos(rec):
        """მსახიობები → [{name, photo}]. cast_json შეიძლ. იყოს {name,photo} ობიექტების სია
        (scraper/enrich-იდან) ან უბრალო სახელების სია (ფოტო Person-ის ბაზიდან მოინახება)."""
        raw = rec.cast[:18] if rec.cast else []
        if not raw:
            return []
        # უკვე ობიექტებია (name+photo) → პირდაპირ
        if isinstance(raw[0], dict):
            return [{"name": c.get("name", ""), "photo": c.get("photo")}
                    for c in raw if c.get("name")]
        # უბრალო სახელები → ფოტო Person-იდან
        lookup = {}
        rows = Person.query.filter(
            db.or_(Person.name.in_(raw), Person.name_en.in_(raw))
        ).all()
        for p in rows:
            if p.name:
                lookup.setdefault(p.name, p.photo)
            if p.name_en:
                lookup.setdefault(p.name_en, p.photo)
        return [{"name": n, "photo": lookup.get(n)} for n in raw]

    @app.route("/movie/<int:movie_id>")
    def movie_detail(movie_id):
        movie = db.session.get(Movie, movie_id)
        if movie is None:
            abort(404)
        similar = _similar_by_genre(Movie, movie)
        return render_template(
            "movie.html", movie=movie, providers=None, similar=similar,
            cast=_cast_with_photos(movie),
        )

    @app.route("/series/<int:series_id>")
    def series_detail(series_id):
        series = db.session.get(Series, series_id)
        if series is None:
            abort(404)
        similar = _similar_by_genre(Series, series)
        return render_template(
            "movie.html", movie=series, providers=None, similar=similar,
            cast=_cast_with_photos(series),
        )

    @app.route("/genre/<int:genre_id>")
    def genre_page(genre_id):
        genre = db.session.get(Genre, genre_id)
        if genre is None:
            abort(404)
        page = request.args.get("page", 1, type=int)
        movies = genre.movies.order_by(Movie.popularity.desc()).paginate(
            page=page, per_page=24, error_out=False
        )
        return render_template("list.html", title=genre.name, movies=movies)

    @app.route("/browse")
    @app.route("/filter-movies")
    def browse():
        """დათვალიერება/ფილტრი — shell; შედეგები AJAX-ით (/api/movies)."""
        media = request.args.get("type", "movie")
        if media in ("search", "serial"):
            media = "tv" if media == "serial" else media
        return render_template(
            "browse.html",
            media=media,
            genre_id=request.args.get("genre", type=int),
            year=request.args.get("year", "").strip(),
            sort=request.args.get("sort", "popularity"),
            q=request.args.get("search", "").strip(),
            years=list(range(2026, 1950, -1)),
        )

    @app.route("/persons")
    def persons():
        return render_template("persons.html")

    @app.route("/api/persons")
    def api_persons():
        q = request.args.get("q", "").strip()
        page = max(request.args.get("page", 1, type=int), 1)
        per = min(request.args.get("per", 36, type=int), 60)
        query = Person.query
        if q:
            query = query.filter(Person.name.ilike(f"%{q}%"))
        query = query.order_by(Person.popularity.desc(), Person.id.asc())
        total = query.count()
        items = query.offset((page - 1) * per).limit(per).all()
        return jsonify(
            items=[{"id": p.id, "name": p.name, "name_en": p.name_en,
                    "photo": p.photo, "url": "/person/%d" % p.id} for p in items],
            page=page, per=per, has_more=page * per < total, total=total,
        )

    @app.route("/watchlist")
    def watchlist():
        """სანახავი სია — ბრაუზერში ინახება (localStorage), JS-ით ივსება."""
        return render_template("watchlist.html")

    @app.route("/catalog")
    def catalog():
        """ძველი ცალკე კატალოგი მოხსნილია — გადავამისამართოთ დათვალიერებაზე."""
        return redirect(url_for("browse"), code=301)

    @app.route("/search")
    def search():
        q = request.args.get("q", "").strip()
        results = []
        if q:
            # ჯერ ლოკალურ ბაზაში (ფილმი + სერიალი), შემდეგ პირდაპირ TMDB-ში
            results = (
                Movie.query.filter(Movie.title.ilike(f"%{q}%"))
                .order_by(Movie.popularity.desc())
                .limit(24)
                .all()
            )
            results += (
                Series.query.filter(Series.title.ilike(f"%{q}%"))
                .order_by(Series.popularity.desc())
                .limit(24)
                .all()
            )
            if not results:
                try:
                    results = tmdb.search(q)
                except tmdb.TMDBError:
                    results = []
        return render_template("search.html", q=q, results=results)

    # ---- ადმინი: დაცული სინქრონიზაცია ----

    @app.route("/admin")
    def admin_page():
        """მარტივი ადმინ-პანელი: „Sync Movies“ ღილაკი. token ბრაუზერში ინახება."""
        return render_template("admin.html")

    @app.route("/api/admin/sync", methods=["POST"])
    @require_admin
    def admin_sync():
        """ხელით სინქრონიზაცია. აბრუნებს სტატისტიკას JSON-ად."""
        try:
            stats = sync_all()
            return jsonify(ok=True, stats=stats)
        except Exception as e:  # noqa: BLE001
            app.logger.exception("admin sync ჩავარდა")
            return jsonify(ok=False, error=str(e)), 500

    @app.errorhandler(404)
    def not_found(_):
        return render_template("404.html"), 404


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
