"""GEMOVIE — ლეგალური ფილმების კატალოგი (Flask + TMDB).

გაშვება:  python app.py   →  http://127.0.0.1:5000
"""
import atexit
import difflib
import json
import os
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, abort, jsonify, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler

import settings_store
from config import Config
from models import db, Movie, Series, Genre, Person, Stream, HomeRow, MenuItem
from medialib import service as media_service
from medialib.routes import media_bp
from medialib.storage import check_media_root
import tmdb
from sync import sync_all


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_schema()
        tune_sqlite(app)

    register_routes(app)
    register_cli(app)

    # ბექოფისი და მედიის გაცემა
    from admin import admin_bp
    app.register_blueprint(admin_bp)
    app.register_blueprint(media_bp)
    check_media_root(app)
    # TMDB ავტო-სინქი გათიშულია — საიტი მთლიანად kinomigma-ს მონაცემებზე დგას.
    # register_scheduler(app)
    return app


def tune_sqlite(app):
    """SQLite-ის რეჟიმი, რომელიც პარალელურ ჩაწერას უძლებს.

    ფონური ამოცანა (სურათების ჩამოტანა) ბაზაში წერს მაშინ, როცა საიტი
    კითხულობს. WAL-ის გარეშე ეს „database is locked"-ს გამოიწვევდა.

    ⚠️ WAL ქმნის `gemovie.db-wal` და `-shm` ფაილებს (gitignore-შია). სანამ
    ბაზას გიტში დაacommit-ებთ, გააკეთეთ checkpoint:
        PRAGMA wal_checkpoint(TRUNCATE); PRAGMA journal_mode=DELETE;
    """
    from sqlalchemy import event

    engine = db.engine
    if engine.url.get_backend_name() != "sqlite":
        return

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection, _record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=8000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

    # უკვე გახსნილ კავშირზეც
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL")
            conn.exec_driver_sql("PRAGMA busy_timeout=8000")
    except Exception as exc:  # noqa: BLE001
        app.logger.warning("SQLite-ის რეჟიმი ვერ დაყენდა: %s", exc)


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

        # ბრენდინგი ბაზიდან: ლოგო, favicon, placeholder-ები, პოპაპ-ბანერი.
        # ბაზის პრობლემამ საიტი არ უნდა ჩამოაგდოს, ამიტომ ჩავარდნისას ნაგულისხმევებით ვაგრძელებთ.
        try:
            cfg = settings_store.all_values()
            brand = media_service.brand_bundle(cfg.get("site_name", "Movie World"))
        except Exception:  # noqa: BLE001
            cfg = dict(settings_store.DEFAULTS)
            brand = {"site_name": cfg["site_name"], "logo": None, "favicon": None,
                     "popup_ad": None, "og_default": None, "logo_dark": None,
                     "logo_mobile": None,
                     "placeholder_poster": media_service.THEME_PLACEHOLDER,
                     "placeholder_person": media_service.THEME_PLACEHOLDER}

        def art(rec, role, size=None):
            """ბექოფისიდან დაყენებული სურათი შაბლონისთვის, ან None."""
            try:
                return media_service.art_url(rec, role, size)
            except Exception:  # noqa: BLE001
                return None

        # მენიუ ბაზიდან; ცარიელი სია ნიშნავს, რომ _navbar.html ძველ წყობას დახატავს
        try:
            menu_items = (MenuItem.query.filter_by(is_active=True)
                          .order_by(MenuItem.position, MenuItem.id).all())
            media_service.prefetch_art(menu_items)
        except Exception:  # noqa: BLE001
            menu_items = []

        return {
            "img": img,
            "art": art,
            "menu_items": menu_items,
            "all_genres": Genre.query.order_by(Genre.name).all(),
            "site_name": brand["site_name"],
            "brand": brand,
            "site_settings": cfg,
        }

    @app.route("/favicon.ico")
    def favicon():
        return redirect(url_for("static", filename="favicon.ico"), code=301)

    def _active_home_rows():
        """მთავარი გვერდის რიგები ბაზიდან, სეზონურობის გათვალისწინებით.

        თუ ცხრილი ჯერ ცარიელია (ან ბაზას პრობლემა აქვს), ცარიელ სიას ვაბრუნებთ
        და index.html ძველ, ჩაწერილ რიგებს დახატავს — საიტი არასდროს რჩება ცარიელი.
        """
        try:
            today = (datetime.utcnow() + timedelta(hours=4)).date()  # თბილისი = UTC+4
            rows = (HomeRow.query.filter_by(is_active=True)
                    .order_by(HomeRow.position, HomeRow.id).all())
            visible = [r for r in rows if r.visible_on(today)]
            media_service.prefetch_art(visible)   # რიგების ფონები ერთი მოთხოვნით
            return visible
        except Exception:  # noqa: BLE001
            return []

    @app.route("/")
    def index():
        # მთავარი გვერდი — მსუბუქი shell; რიგები/ჰერო AJAX-ით ივსება (/api/movies)
        return render_template("index.html", home_rows=_active_home_rows())

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
        original_ok = db.and_(
            col.isnot(None), col != "",
            db.or_(
                col.ilike("%.jpg"), col.ilike("%.jpeg"),
                col.ilike("%.png"), col.ilike("%.webp"),
            ),
        )
        # ბექოფისიდან დაყენებული სურათიც ითვლება: თორემ ის 21 ჩანაწერი, რომელსაც
        # გატეხილი poster_url აქვს, CMS-ში გასწორების შემდეგაც უხილავი დარჩებოდა
        subject_type = "series" if Model is Series else "movie"
        from models import MediaLink
        with_art = db.session.query(MediaLink.subject_id).filter(
            MediaLink.subject_type == subject_type
        )
        return db.or_(original_ok, Model.id.in_(with_art))

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

    # ეს პარამეტრები ადრე კოდში იყო ჩაწერილი. ახლა ბექოფისიდან იცვლება
    # (/admin/home), ბაზის პრობლემის შემთხვევაში კი ძველ მნიშვნელობებს ვუბრუნდებით.
    def _setting(key, fallback):
        try:
            value = settings_store.get_value(key)
            return fallback if value is None else value
        except Exception:  # noqa: BLE001
            return fallback

    def _weekly_top_years():
        years = _setting("weekly_top_years", ["2025", "2026"])
        return tuple(str(y) for y in years) if years else ("2025", "2026")

    def _weekly_top_limit():
        try:
            return max(1, min(int(_setting("weekly_top_limit", 50)), 200))
        except (TypeError, ValueError):
            return 50

    def _hero_pinned_ids():
        raw = _setting("hero_pinned_ids", [49764]) or []
        return [int(x) for x in raw if str(x).strip().lstrip("-").isdigit()]

    def _load_weekly_top_cache():
        try:
            with open(WEEKLY_TOP_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_weekly_top_cache(cache):
        with open(WEEKLY_TOP_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)

    def _weekly_top_ids(media_key, Model, years=None):
        """მოცემულ წლებში ყველაზე მაღალრეიტინგული (ჩვენს ბაზაში — რეალური ინტერნეტ
        ნახვადობის მონაცემი არ გვაქვს, IMDb-რეიტინგი ვიყენებთ პროქსად) ფილმები/სერიალები.
        სია გამოითვლება მაქსიმუმ კვირაში ერთხელ და ინახება ფაილში — ამ დროში
        ხელახლა არ გამოითვლება, თუნდაც ბაზა შეიცვალოს."""
        years = tuple(years) if years else _weekly_top_years()
        limit = _weekly_top_limit()
        params = "%s|%d" % (",".join(years), limit)

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
        # პარამეტრების შეცვლა ბექოფისიდან ქეშს დაუყოვნებლივ აძველებს
        if entry and entry.get("params") not in (None, params):
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
            .limit(limit)
            .all()
        )
        ids = [r.id for r in rows]
        cache[media_key] = {"computed_at": now.isoformat(), "ids": ids, "params": params}
        _save_weekly_top_cache(cache)
        return ids

    def _serialize(rec):
        # ბექოფისიდან დაყენებული სურათი ყოველთვის ჯობნის ge.movie-ს ორიგინალს
        art = media_service.art_for(*media_service.subject_of(rec))
        backdrop = media_service.asset_url(art.get("backdrop"), profile="art")
        portrait = media_service.asset_url(art.get("poster"), profile="portrait")
        hero = media_service.asset_url(art.get("hero"), name="w1280") \
            or media_service.asset_url(art.get("hero"), profile="art")
        return {
            "id": rec.id,
            "type": "tv" if isinstance(rec, Series) else "movie",
            "title": rec.title,
            "title_en": rec.original_title or "",
            "year": rec.year or "",
            "rating": rec.rating or 0,
            "poster": backdrop or rec.poster_url or "",
            "poster_portrait": portrait or rec.poster_portrait or "",
            "hero": hero or backdrop or rec.poster_url or "",
            "genres": [g.name for g in rec.genres][:3],
            "has_stream": bool(rec.streams),
            "url": ("/series/" if isinstance(rec, Series) else "/movie/") + str(rec.id),
        }

    def _serialize_many(rows):
        """სიის სერიალიზაცია. სურათები ერთი მოთხოვნით იტვირთება, არა თითოზე ცალკე."""
        media_service.prefetch_art(rows)
        return [_serialize(x) for x in rows]

    @app.route("/api/movies")
    def api_movies():
        media = request.args.get("type", "movie")
        genre_id = request.args.get("genre", type=int)
        year = request.args.get("year", "").strip()
        sort = request.args.get("sort", "popularity")
        q = request.args.get("q", "").strip()
        page = max(request.args.get("page", 1, type=int), 1)
        per = min(request.args.get("per", 24, type=int), 60)

        # ხელით შედგენილი/შეშაფლული რიგი: ზუსტად ეს ჩანაწერები, ზუსტად ამ რიგით.
        # ფორმატი: ids=movie:49764,tv:50526
        ids_raw = request.args.get("ids", "").strip()
        if ids_raw:
            wanted = []
            for token in ids_raw.split(","):
                kind, _, rid = token.strip().partition(":")
                if rid.isdigit():
                    wanted.append(
                        ("tv" if kind in ("tv", "series", "serial") else "movie", int(rid))
                    )
            wanted = wanted[:120]
            found = {}
            for key, Model in (("movie", Movie), ("tv", Series)):
                group = [rid for k, rid in wanted if k == key]
                if group:
                    for rec in Model.query.filter(Model.id.in_(group)).all():
                        found[(key, rec.id)] = rec
            ordered = [found[k] for k in wanted if k in found]
            return jsonify(
                items=_serialize_many(ordered), page=1, per=len(ordered),
                has_more=False, total=len(ordered),
            )

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
                items=_serialize_many(items), page=page, per=per,
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
                items=_serialize_many(items), page=page, per=per,
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
                items=_serialize_many(items),
                page=page,
                per=per,
                has_more=page * per < total,
                total=total,
            )

        if sort == "hero_top":
            # მთავარი გვერდის ჰერო — კონკრეტულად მოთხოვნილი ფილმ(ებ)ი ყოველთვის შედის,
            # დანარჩენს ავსებს 2026-ის ყველაზე მაღალრეიტინგული ფილმებით (კვირაში ერთხელ
            # განახლებადი). დუბლირება არასდროს — pinned ID-ები გამორიცხულია top-ის სიიდან.
            pinned_ids = _hero_pinned_ids() if Model is Movie else []
            top_ids = _weekly_top_ids("movie_2026_hero" if Model is Movie else "serial_2026_hero", Model, years=("2026",))
            ordered_ids = pinned_ids + [i for i in top_ids if i not in pinned_ids]
            query = query.filter(Model.id.in_(ordered_ids), _has_poster(Model))
            rows = query.all()
            rank = {rid: i for i, rid in enumerate(ordered_ids)}
            rows.sort(key=lambda r: rank.get(r.id, len(ordered_ids)))
            total = len(rows)
            items = rows[(page - 1) * per: page * per]
            return jsonify(
                items=_serialize_many(items),
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
            items=_serialize_many(items),
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

        # რიგის სურათებიც ბექოფისიდან უნდა მოდიოდეს, როგორც ყველგან
        media_service.prefetch_art([series for _stream, series in rows])
        items = []
        for s, series in rows:
            m = re.search(r"სეზონი\s*(\d+)", series.title or "")
            season = int(m.group(1)) if m else 1
            items.append({
                "id": series.id,
                "title": series.title,
                "title_en": series.original_title or "",
                "poster": (media_service.art_url(series, "backdrop", "w640")
                           or series.poster_url or ""),
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
        return jsonify(items=_serialize_many(combined))

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

    @app.route("/movie/<int:movie_id>")
    def movie_detail(movie_id):
        movie = db.session.get(Movie, movie_id)
        if movie is None:
            abort(404)
        similar = _similar_by_genre(Movie, movie)
        return render_template(
            "movie.html", movie=movie, providers=None, similar=similar,
        )

    @app.route("/series/<int:series_id>")
    def series_detail(series_id):
        series = db.session.get(Series, series_id)
        if series is None:
            abort(404)
        similar = _similar_by_genre(Series, series)
        return render_template(
            "movie.html", movie=series, providers=None, similar=similar,
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
        media_service.prefetch_art(items)
        return jsonify(
            items=[{
                "id": p.id, "name": p.name, "name_en": p.name_en,
                # ბექოფისიდან ატვირთული ფოტო ჯობნის ge.movie-ს ორიგინალს
                "photo": media_service.art_url(p, "photo", "w300") or p.photo,
                "url": "/person/%d" % p.id,
            } for p in items],
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

    # ძველი „Sync Movies" გვერდი მოხსნილია: TMDB აღარ გამოიყენება და /admin
    # ახლა სრულფასოვანი ბექოფისია (იხ. admin/ პაკეტი).

    @app.route("/robots.txt")
    def robots():
        body = "User-agent: *\nDisallow: /admin/\n"
        return app.response_class(body, mimetype="text/plain")

    @app.errorhandler(404)
    def not_found(_):
        return render_template("404.html"), 404


def register_cli(app):
    """ტერმინალის კომანდები: ადმინის შექმნა და ბრენდინგის საწყისი შევსება."""
    import click

    from models import AdminUser

    @app.cli.command("create-admin")
    @click.argument("username")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--role", default="owner",
                  type=click.Choice(["owner", "editor", "moderator"]))
    @click.option("--email", default=None)
    def create_admin(username, password, role, email):
        """ბექოფისის მომხმარებლის შექმნა ან პაროლის შეცვლა."""
        user = AdminUser.query.filter_by(username=username).first()
        if user is None:
            user = AdminUser(username=username, role=role, email=email)
            db.session.add(user)
            action = "შეიქმნა"
        else:
            user.role = role
            if email:
                user.email = email
            user.is_active = True
            action = "განახლდა"
        user.set_password(password)
        db.session.commit()
        click.echo("ადმინი %s: %s (%s)" % (action, username, role))

    @app.cli.command("media-verify")
    @click.option("--full", is_flag=True, help="ყველა ფაილი შემოწმდეს, არა შერჩევა")
    def media_verify(full):
        """ამოწმებს, ნამდვილად დევს თუ არა ბაზაში ჩაწერილი ფაილები საცავში."""
        from medialib.storage import get_storage
        from models import MediaAsset, MediaVariant

        storage = get_storage()
        click.echo("საცავი: %s" % storage.backend)

        assets = MediaAsset.query.filter_by(is_deleted=False).all()
        if not full and len(assets) > 300:
            step = max(1, len(assets) // 300)
            sample = assets[::step]
            click.echo("შერჩევა: %d ჩანაწერი %d-დან (--full ყველასთვის)"
                       % (len(sample), len(assets)))
        else:
            sample = assets

        missing_orig = [a for a in sample if not storage.exists(a.storage_key)]
        variant_total = variant_missing = 0
        for asset in sample:
            for variant in asset.variants:
                variant_total += 1
                if not storage.exists(variant.storage_key):
                    variant_missing += 1

        click.echo("ორიგინალი: %d-დან აკლია %d" % (len(sample), len(missing_orig)))
        click.echo("ვარიანტები: %d-დან აკლია %d" % (variant_total, variant_missing))
        if missing_orig or variant_missing:
            with_source = sum(1 for a in missing_orig if a.source_url)
            click.echo(
                "აკლია ფაილები. საიტი არ ტყდება: /m/ ავტომატურად გადაამისამართებს\n"
                "ორიგინალ წყაროზე (%d-ს აქვს source_url). სრული აღდგენისთვის:\n"
                "  MEDIA_BACKEND=r2 ... flask media-push   (ან ხელახლა flask mirror-images)"
                % with_source
            )
        else:
            click.echo("ყველა ფაილი ადგილზეა.")

    @app.cli.command("media-push")
    @click.option("--dry-run", is_flag=True, help="მხოლოდ დათვლა, ატვირთვის გარეშე")
    def media_push(dry_run):
        """ლოკალური media/ საქაღალდე ატვირთოს კონფიგურირებულ R2/S3 საცავში.

        გაშვება: MEDIA_BACKEND=r2 და MEDIA_R2_* ცვლადებით. MEDIA_ROOT უნდა
        მიუთითებდეს ლოკალურ media/ საქაღალდეზე, საიდანაც ვიღებთ.
        """
        from medialib.storage import LocalStorage, get_storage
        from models import MediaAsset

        target = get_storage()
        if isinstance(target, LocalStorage):
            click.echo("MEDIA_BACKEND=local არის. ატვირთვისთვის დააყენეთ "
                       "MEDIA_BACKEND=r2 და MEDIA_R2_* ცვლადები.")
            return

        source = LocalStorage(app.config["MEDIA_ROOT"])
        assets = MediaAsset.query.filter_by(is_deleted=False).all()
        keys = []
        for asset in assets:
            keys.append((asset.storage_key, asset.mime))
            for variant in asset.variants:
                mime = {"webp": "image/webp", "jpg": "image/jpeg",
                        "png": "image/png", "ico": "image/x-icon"}.get(
                            variant.fmt, "application/octet-stream")
                keys.append((variant.storage_key, mime))

        click.echo("ასატვირთი ფაილი: %d (%d ჩანაწერიდან)" % (len(keys), len(assets)))
        if dry_run:
            return

        uploaded = skipped = failed = 0
        for index, (key, mime) in enumerate(keys, start=1):
            if not source.exists(key):
                skipped += 1
                continue
            try:
                target.save(key, source.read(key), mime=mime)
                uploaded += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                if failed <= 5:
                    click.echo("  ვერ აიტვირთა %s: %s" % (key, exc))
            if index % 500 == 0:
                click.echo("  %d / %d" % (index, len(keys)))
        click.echo("აიტვირთა %d, გამოტოვდა %d, ჩავარდა %d" % (uploaded, skipped, failed))

    @app.cli.command("mirror-images")
    @click.option("--limit", default=0, help="მაქსიმუმ რამდენი ჩანაწერი (0 = ყველა)")
    @click.option("--types", default="movie,series", help="movie, series ან ორივე")
    def mirror_images(limit, types):
        """გარე სურათების ჩამოტანა ჩვენს საცავში (იდემპოტენტური, შეწყვეტადი).

        პროგრესი Job ცხრილში იწერება, ანუ /admin/jobs-ზე ცოცხლად ჩანს.
        """
        from medialib import jobs as job_engine
        from medialib import mirror

        plan = mirror.plan()
        click.echo("დარჩენილი: %d (TMDB-დან %d, სხვა %d)"
                   % (plan["pending"], plan["tmdb_ready"], plan["other"]))
        if not plan["pending"]:
            return

        subject_types = [t.strip() for t in types.split(",") if t.strip()]
        job = job_engine.create_job(
            "media_mirror",
            {"limit": limit, "prefer_tmdb": True, "subject_types": subject_types},
        )
        click.echo("ამოცანა #%d გაეშვა. /admin/jobs-ზე ჩანს." % job.id)

        ctx = job_engine.JobContext(job.id)
        from datetime import datetime as _dt, timezone as _tz
        job.status = "running"
        job.started_at = _dt.now(_tz.utc)
        db.session.commit()
        try:
            result = mirror.run(ctx, {"limit": limit, "prefer_tmdb": True,
                                      "subject_types": subject_types})
            ctx.flush()
            job = db.session.get(type(job), job.id)
            job.status = "done"
            job.result_json = json.dumps(result, ensure_ascii=False)
        except job_engine.Cancelled:
            db.session.rollback()
            job = db.session.get(type(job), job.id)
            job.status = "cancelled"
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            job = db.session.get(type(job), job.id)
            job.status = "failed"
            job.log_text = (job.log_text or "") + "\nშეცდომა: %s" % exc
            raise
        finally:
            job.finished_at = _dt.now(_tz.utc)
            db.session.commit()
            click.echo("სტატუსი: %s | ჩამოიტანა %s | ჩავარდა %s | %.2f გბ"
                       % (job.status, job.done, job.failed,
                          (job.bytes_fetched or 0) / 1024 ** 3))

    @app.cli.command("seed-menu")
    @click.option("--replace", is_flag=True, help="არსებული პუნქტები ჯერ წაიშალოს")
    def seed_menu(replace):
        """გვერდითი მენიუს ნაგულისხმევი 7 პუნქტის ჩაწერა ბაზაში."""
        import menu_items
        added = menu_items.seed(replace=replace)
        click.echo("ჩაიწერა %d პუნქტი." % added if added
                   else "მენიუ უკვე არსებობს (--replace ჩასანაცვლებლად).")

    @app.cli.command("seed-home-rows")
    @click.option("--replace", is_flag=True, help="არსებული რიგები ჯერ წაიშალოს")
    def seed_home_rows(replace):
        """მთავარი გვერდის ნაგულისხმევი 11 რიგის ჩაწერა ბაზაში."""
        import home_rows
        added = home_rows.seed(replace=replace)
        if added:
            click.echo("ჩაიწერა %d რიგი." % added)
        else:
            click.echo("რიგები უკვე არსებობს (--replace ჩასანაცვლებლად).")

    @app.cli.command("seed-branding")
    def seed_branding():
        """არსებული ლოგო/favicon/ბანერი ბაზაში გადმოაქვს, რომ CMS-იდან იმართებოდეს."""
        here = os.path.dirname(os.path.abspath(__file__))
        pairs = [
            ("logo_light", "static/img/logo.png", "logo"),
            ("favicon", "static/favicon.png", "icon"),
            ("popup_ad", "static/img/popup-ad.jpg", "banner"),
        ]
        for role, rel, profile in pairs:
            path = os.path.join(here, rel.replace("/", os.sep))
            if not os.path.exists(path):
                click.echo("გამოტოვდა (ფაილი არ არის): %s" % rel)
                continue
            with open(path, "rb") as f:
                data = f.read()
            # source_url-ს იმიტომ ვინახავთ, რომ ახალ სერვერზე (სადაც media/
            # ჯერ ცარიელია) /m/ ამ სტატიკურ ფაილზე გადაამისამართოს და
            # ლოგო არ გატყდეს volume-ის დაყენებამდე
            static_url = "/" + rel
            asset = media_service.store_bytes(
                data, filename=os.path.basename(path), profile=profile,
                source="seed", source_url=static_url,
            )
            if not asset.source_url:          # უკვე არსებულ ჩანაწერს ვასწორებთ
                asset.source_url = static_url
                db.session.commit()
            media_service.bind(media_service.SITE, 0, role, asset)
            click.echo("%s ← %s (%d ვარიანტი)" % (role, rel, len(asset.variants)))
        click.echo("მზადაა. გახსენით /admin/branding.")


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
