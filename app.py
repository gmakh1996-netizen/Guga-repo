"""GEMOVIE — ლეგალური ფილმების კატალოგი (Flask + TMDB).

გაშვება:  python app.py   →  http://127.0.0.1:5000
"""
import atexit
import difflib
import json
import os
from collections import Counter
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, abort, jsonify, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler

from config import Config
from models import db, Movie, Series, Genre, Person, Stream
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

    def _has_poster(Model):
        """მხოლოდ ისეთი ჩანაწერები, რომლებსაც ნამდვილი სურათი აქვთ.

        ge.movie-ს ზოგ ჩანაწერს poster_url გატეხილი აქვს (მაგ. `.../big/original`
        ფაილის სახელის გარეშე) → ბარათი placeholder-ით ჩნდება და დიზაინს აფუჭებს.
        ვფილტრავთ URL-ს ნამდვილი სურათის გაფართოებით — ცარიელი/გატეხილი გამოირიცხოს.
        """
        col = Model.poster_url
        return db.and_(
            col.isnot(None), col != "",
            db.or_(
                col.ilike("%.jpg"), col.ilike("%.jpeg"),
                col.ilike("%.png"), col.ilike("%.webp"),
            ),
        )

    def _title_match(Model, q):
        """ქართულ (title) და ინგლისურ (original_title) სათაურშიც ეძებს, სიტყვების
        მიხედვით (ნებისმიერი მიმდევრობა/ველი) — რომ "Spider" აღმოაჩინოს
        "Spider-Man"-ში, თუნდაც ქართული title-ში ეს სიტყვა საერთოდ არ იყოს."""
        words = [w for w in q.split() if w]
        if not words:
            return db.false()
        conds = [db.or_(Model.title.ilike(f"%{w}%"), Model.original_title.ilike(f"%{w}%")) for w in words]
        return db.and_(*conds)

    def _fuzzy_search(Model, q, limit=24):
        """სუსტი/არაზუსტი დამთხვევებისთვის (ერთი ასო/სიმბოლო რომ არასწორად აწერო) —
        ბოლო საშუალება, მხოლოდ მაშინ ვრთავთ, როცა ზუსტმა ძებნამ არაფერი იპოვა.
        ყველა სათაურს ადარებს difflib-ით და საუკეთესო მსგავსობის მიხედვით ალაგებს."""
        rows = (
            Model.query.filter(_has_poster(Model))
            .with_entities(Model.id, Model.title, Model.original_title, Model.release_date)
            .all()
        )
        q_low = q.lower()
        scored = []
        for rid, title, title_en, rdate in rows:
            best = 0.0
            for candidate in (title, title_en):
                if not candidate:
                    continue
                c_low = candidate.lower()
                ratio = difflib.SequenceMatcher(None, q_low, c_low).ratio()
                if q_low in c_low:
                    ratio = max(ratio, 0.9)
                best = max(best, ratio)
            if best >= 0.55:
                scored.append((rid, best, rdate or ""))
        scored.sort(key=lambda x: (x[1], x[2]), reverse=True)
        ordered_ids = [rid for rid, _, _ in scored[:limit]]
        if not ordered_ids:
            return []
        found = {r.id: r for r in Model.query.filter(Model.id.in_(ordered_ids)).all()}
        return [found[rid] for rid in ordered_ids if rid in found]

    WEEKLY_TOP_CACHE_PATH = os.path.join(os.path.dirname(__file__), "data", "weekly_top_cache.json")
    WEEKLY_TOP_YEARS = ("2025", "2026")
    WEEKLY_TOP_LIMIT = 50
    # ჰერო-ს (მთავარი გვერდის ზედა 9 ფილმი) კონკრეტულად სთხოვილი "ფიქსირებული" ფილმები —
    # ყოველთვის ჩნდება სიაში, დანარჩენს ავსებს 2026-ის ყველაზე მაღალრეიტინგული ფილმებით.
    HERO_PINNED_MOVIE_IDS = [49764]  # სპაიდერმენი: ახალი დღე (Spider-Man: Brand New Day, 2026)

    def _load_weekly_top_cache():
        try:
            with open(WEEKLY_TOP_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_weekly_top_cache(cache):
        with open(WEEKLY_TOP_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)

    def _weekly_top_ids(media_key, Model, years=WEEKLY_TOP_YEARS):
        """მოცემულ წლებში ყველაზე მაღალრეიტინგული (ჩვენს ბაზაში — რეალური ინტერნეტ
        ნახვადობის მონაცემი არ გვაქვს, IMDb-რეიტინგი ვიყენებთ პროქსად) ფილმები/სერიალები.
        სია გამოითვლება მაქსიმუმ კვირაში ერთხელ და ინახება ფაილში — ამ დროში
        ხელახლა არ გამოითვლება, თუნდაც ბაზა შეიცვალოს."""
        cache = _load_weekly_top_cache()
        entry = cache.get(media_key)
        now = datetime.utcnow()
        stale = True
        if entry and entry.get("computed_at"):
            try:
                computed_at = datetime.fromisoformat(entry["computed_at"])
                stale = (now - computed_at) > timedelta(days=7)
            except (ValueError, TypeError):
                stale = True
        if entry and not stale:
            return entry["ids"]

        rows = (
            Model.query.filter(
                db.or_(*[Model.release_date.like(f"{y}%") for y in years]),
                Model.vote_average > 0,
                Model.streams.any(),
                _has_poster(Model),
            )
            .order_by(Model.vote_average.desc(), Model.popularity.desc())
            .limit(WEEKLY_TOP_LIMIT)
            .all()
        )
        ids = [r.id for r in rows]
        cache[media_key] = {"computed_at": now.isoformat(), "ids": ids}
        _save_weekly_top_cache(cache)
        return ids

    def _studio_counts(limit=30):
        """ყველაზე ხშირი კინოსტუდიები (studio ველი მძიმით გამოყოფილი კომპანიების
        სია) — ორივე მოდელში ერთად დათვლილი. ჯერჯერობით cache არ სჭირდება
        (სწრაფია, ~11k მოკლე სტრიქონზე), დამატება მარტივია მერე, თუ დაგჭირდება."""
        counts = Counter()
        for Model in (Movie, Series):
            rows = (
                Model.query.filter(Model.studio.isnot(None), Model.studio != "")
                .with_entities(Model.studio)
                .all()
            )
            for (s,) in rows:
                for name in s.split(","):
                    name = name.strip()
                    if name:
                        counts[name] += 1
        return counts.most_common(limit)

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

        # ძებნა — ორივე მოდელში (ფილმი + სერიალი), ქართული და ინგლისური სათაურით,
        # პრიორიტეტი უახლეს წლებს (release_date desc); თუ ზუსტმა ვერაფერი იპოვა —
        # სუსტი/არაზუსტი დამთხვევის fallback (_fuzzy_search)
        if media == "search" and q:
            combined = []
            for M in (Movie, Series):
                combined += M.query.filter(_title_match(M, q), _has_poster(M)).order_by(
                    M.release_date.desc()
                ).limit(300).all()
            if not combined:
                for M in (Movie, Series):
                    combined += _fuzzy_search(M, q, limit=60)
            else:
                combined.sort(key=lambda x: x.release_date or "", reverse=True)
            total = len(combined)
            items = combined[(page - 1) * per: page * per]
            return jsonify(
                items=[_serialize(x) for x in items], page=page, per=per,
                has_more=page * per < total, total=total,
            )

        # ანიმეები/ანიმაციები — არა ცალკე "ტიპი", არამედ ჟანრი, რომელიც ორივე
        # მოდელში გვხვდება (ფილმიც და სერიალიც) — search-ის იგივე კომბინირების
        # ლოგიკით ვმართავთ, რომ ორივე ერთად, გვერდობრივად დაითვალიერო
        GENRE_GROUP_TYPES = {"anime": 900000025, "animation": 900000009}
        if media in GENRE_GROUP_TYPES:
            gid = GENRE_GROUP_TYPES[media]
            combined = []
            for M in (Movie, Series):
                gq = M.query.filter(M.genres.any(Genre.id == gid), _has_poster(M))
                if genre_id and genre_id != gid:
                    gq = gq.filter(M.genres.any(Genre.id == genre_id))
                if year.isdigit():
                    gq = gq.filter(M.release_date.like(f"{year}%"))
                if q:
                    gq = gq.filter(_title_match(M, q))
                if sort == "rating":
                    gq = gq.order_by(M.vote_average.desc())
                elif sort == "newest":
                    gq = gq.order_by(M.release_date.desc())
                else:
                    gq = gq.order_by(M.popularity.desc())
                combined += gq.limit(300).all()
            if sort == "rating":
                combined.sort(key=lambda x: x.vote_average or 0, reverse=True)
            elif sort == "newest":
                combined.sort(key=lambda x: x.release_date or "", reverse=True)
            else:
                combined.sort(key=lambda x: x.popularity or 0, reverse=True)
            total = len(combined)
            items = combined[(page - 1) * per: page * per]
            return jsonify(
                items=[_serialize(x) for x in items], page=page, per=per,
                has_more=page * per < total, total=total,
            )

        # კინოსტუდიები — /studios გვერდიდან დაკლიკვისას, ისევ ორივე მოდელს
        # ერთად ვამოწმებთ (HBO-ს, მაგ., ძირითადად სერიალები აქვს, არა ფილმები)
        studio_name = request.args.get("studio", "").strip()
        if media == "studio" and studio_name:
            combined = []
            for M in (Movie, Series):
                sq = M.query.filter(M.studio.ilike(f"%{studio_name}%"), _has_poster(M))
                if year.isdigit():
                    sq = sq.filter(M.release_date.like(f"{year}%"))
                if q:
                    sq = sq.filter(_title_match(M, q))
                if sort == "rating":
                    sq = sq.order_by(M.vote_average.desc())
                elif sort == "newest":
                    sq = sq.order_by(M.release_date.desc())
                else:
                    sq = sq.order_by(M.popularity.desc())
                combined += sq.limit(500).all()
            if sort == "rating":
                combined.sort(key=lambda x: x.vote_average or 0, reverse=True)
            elif sort == "newest":
                combined.sort(key=lambda x: x.release_date or "", reverse=True)
            else:
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
        exclude_genre_id = request.args.get("exclude_genre", type=int)
        if exclude_genre_id:
            query = query.filter(~Model.genres.any(Genre.id == exclude_genre_id))
        exclude_ids_raw = request.args.get("exclude_ids", "").strip()
        if exclude_ids_raw:
            exclude_ids = [int(x) for x in exclude_ids_raw.split(",") if x.strip().isdigit()]
            if exclude_ids:
                query = query.filter(~Model.id.in_(exclude_ids))
        if year.isdigit():
            query = query.filter(Model.release_date.like(f"{year}%"))
        if q:
            query = query.filter(_title_match(Model, q))
        if sort == "weekly_top":
            # „ტოპ ფილმები/სერიალები" — 2025-2026, კვირაში ერთხელ გამოთვლილი/დაცული სია
            # (იხ. _weekly_top_ids) — რიგითობა დაცული უნდა იყოს id-ების სიის მიხედვით,
            # არა SQL-ის ჩვეულებრივი ORDER BY-ით.
            media_key = "serial" if Model is Series else "movie"
            weekly_ids = _weekly_top_ids(media_key, Model)
            query = query.filter(Model.id.in_(weekly_ids), _has_poster(Model))
            rows = query.all()
            rank = {rid: i for i, rid in enumerate(weekly_ids)}
            rows.sort(key=lambda r: rank.get(r.id, len(weekly_ids)))
            total = len(rows)
            items = rows[(page - 1) * per: page * per]
            return jsonify(
                items=[_serialize(x) for x in items],
                page=page,
                per=per,
                has_more=page * per < total,
                total=total,
            )

        if sort == "hero_top":
            # მთავარი გვერდის ჰერო — კონკრეტულად მოთხოვნილი ფილმ(ებ)ი ყოველთვის შედის,
            # დანარჩენს ავსებს 2026-ის ყველაზე მაღალრეიტინგული ფილმებით (კვირაში ერთხელ
            # განახლებადი). დუბლირება არასდროს — pinned ID-ები გამორიცხულია top-ის სიიდან.
            pinned_ids = [i for i in HERO_PINNED_MOVIE_IDS if Model is Movie]
            top_ids = _weekly_top_ids("movie_2026_hero" if Model is Movie else "serial_2026_hero", Model, years=("2026",))
            ordered_ids = pinned_ids + [i for i in top_ids if i not in pinned_ids]
            query = query.filter(Model.id.in_(ordered_ids), _has_poster(Model))
            rows = query.all()
            rank = {rid: i for i, rid in enumerate(ordered_ids)}
            rows.sort(key=lambda r: rank.get(r.id, len(ordered_ids)))
            total = len(rows)
            items = rows[(page - 1) * per: page * per]
            return jsonify(
                items=[_serialize(x) for x in items],
                page=page,
                per=per,
                has_more=page * per < total,
                total=total,
            )

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

        # უფოტო/გატეხილპოსტერიანი ჩანაწერები არასდროს დაბრუნდეს (მთავარი/ჰერო/ბრაუზი/თრეილერი)
        query = query.filter(_has_poster(Model))

        total = query.count()
        items = query.offset((page - 1) * per).limit(per).all()
        return jsonify(
            items=[_serialize(x) for x in items],
            page=page,
            per=per,
            has_more=page * per < total,
            total=total,
        )

    @app.route("/api/recent-episodes")
    def api_recent_episodes():
        """ბოლოს დამატებული ეპიზოდები — ერთი (ბოლო) ეპიზოდი თითო სერიალზე,
        რომ ლენტა მრავალფეროვანი იყოს და არა ერთი სერიალის ყველა ეპიზოდი ზედიზედ."""
        import re

        page = max(request.args.get("page", 1, type=int), 1)
        per = min(request.args.get("per", 20, type=int), 40)

        latest_per_series = (
            db.session.query(
                Stream.series_id.label("series_id"),
                db.func.max(Stream.id).label("max_id"),
            )
            .filter(Stream.episode.isnot(None), Stream.series_id.isnot(None))
            .group_by(Stream.series_id)
            .subquery()
        )

        query = (
            db.session.query(Stream, Series)
            .join(latest_per_series, Stream.id == latest_per_series.c.max_id)
            .join(Series, Stream.series_id == Series.id)
            .filter(_has_poster(Series))
            .order_by(Stream.id.desc())
        )
        exclude_ids_raw = request.args.get("exclude_ids", "").strip()
        if exclude_ids_raw:
            exclude_ids = [int(x) for x in exclude_ids_raw.split(",") if x.strip().isdigit()]
            if exclude_ids:
                query = query.filter(~Series.id.in_(exclude_ids))
        total = query.count()
        rows = query.offset((page - 1) * per).limit(per).all()

        items = []
        for s, series in rows:
            m = re.search(r"სეზონი\s*(\d+)", series.title or "")
            season = int(m.group(1)) if m else 1
            items.append({
                "id": series.id,
                "title": series.title,
                "title_en": series.original_title or "",
                "poster": series.poster_url or "",
                "season": season,
                "episode": s.episode,
                "url": f"/series/{series.id}",
            })

        return jsonify(items=items, page=page, per=per, has_more=page * per < total, total=total)

    @app.route("/api/search")
    def api_search():
        q = request.args.get("q", "").strip()
        if len(q) < 2:
            return jsonify(items=[])
        movies = Movie.query.filter(_title_match(Movie, q), _has_poster(Movie)).order_by(
            Movie.release_date.desc()
        ).limit(10).all()
        series = Series.query.filter(_title_match(Series, q), _has_poster(Series)).order_by(
            Series.release_date.desc()
        ).limit(10).all()
        if not movies and not series:
            movies = _fuzzy_search(Movie, q, limit=10)
            series = _fuzzy_search(Series, q, limit=10)
        combined = sorted(movies + series, key=lambda x: x.release_date or "", reverse=True)[:10]
        return jsonify(items=[_serialize(x) for x in combined])

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
            studio=request.args.get("studio", "").strip(),
            years=list(range(2026, 1950, -1)),
        )

    @app.route("/studios")
    def studios_page():
        """კინოსტუდიები — ყველაზე ხშირი სტუდიების სია, თითოეულზე დაკლიკვით
        იმ სტუდიის ფილმები/სერიალები ჩანს (/browse?type=studio&studio=...)."""
        return render_template("studios.html", studios=_studio_counts(limit=30))

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
