"""მთავარი გვერდის კონსტრუქტორი: რიგები, თანმიმდევრობა, ჰერო."""
import home_rows
import settings_store
from flask import flash, redirect, render_template, request, url_for

from medialib import service
from models import Genre, HomeRow, Movie, db

from . import admin_bp
from .auth import current_admin, log_action


def _admin_id():
    admin = current_admin()
    return admin.id if admin else None


def _back():
    return redirect(url_for("admin.home_builder"))


def _int_or_none(name):
    raw = (request.form.get(name) or "").strip()
    return int(raw) if raw.isdigit() else None


def _apply_form(row):
    """ფორმიდან მნიშვნელობების გადმოტანა, ვალიდაციით."""
    row.title = (request.form.get("title") or "").strip()[:120] or "უსათაურო"
    kind = request.form.get("kind") or "movies"
    row.kind = kind if kind in home_rows.VALID_KINDS else "movies"
    icon = request.form.get("icon") or "film"
    row.icon = icon if icon in home_rows.ICONS else "film"

    media = request.form.get("media_type") or "movie"
    row.media_type = media if media in home_rows.VALID_MEDIA else "movie"
    sort_mode = request.form.get("sort_mode") or "popularity"
    row.sort_mode = sort_mode if sort_mode in home_rows.VALID_SORTS else "popularity"
    layout = request.form.get("layout") or "landscape"
    row.layout = layout if layout in home_rows.VALID_LAYOUTS else "landscape"

    row.genre_id = _int_or_none("genre_id")
    row.exclude_genre_id = _int_or_none("exclude_genre_id")

    try:
        row.item_limit = max(3, min(int(request.form.get("item_limit") or 18), 60))
    except ValueError:
        row.item_limit = 18

    row.is_active = bool(request.form.get("is_active"))

    def _season(name):
        value = (request.form.get(name) or "").strip()
        if len(value) == 5 and value[2] == "-" and value[:2].isdigit() and value[3:].isdigit():
            return value
        return None

    starts, ends = _season("starts_on"), _season("ends_on")
    row.starts_on = starts if (starts and ends) else None
    row.ends_on = ends if (starts and ends) else None
    return row


@admin_bp.route("/home")
def home_builder():
    rows = HomeRow.query.order_by(HomeRow.position, HomeRow.id).all()
    service.prefetch_art(rows)
    ANIME_GENRE = 900000025

    def _bg_hint(row):
        """რა ხდება ამ რიგის ფონთან ახლა, სანამ სურათი არ აიტვირთა."""
        if row.genre_id == ANIME_GENRE:
            return ("ახლა თემის აბსტრაქტული ფონია (CSS-ში ჩაწერილი). "
                    "ატვირთული სურათი მას ჩაანაცვლებს.")
        if row.layout == "portrait":
            return ("ახლა ფონი ფილმებს მიჰყვება: ჩანს იმ ფილმის სურათი, რომელზეც "
                    "მაუსს დაიტანენ. ატვირთეთ სურათი, თუ გინდათ ფიქსირებული ფონი.")
        return "ცარიელის შემთხვევაში ამ რიგს ფონი არ აქვს."

    def _bg_current(row):
        """რა სურათი დგას იმ ადგილას ახლა (აღქმისთვის)."""
        if row.genre_id == ANIME_GENRE:
            return ("/static/img/anime-bg/sakura-night.jpg"
                    if row.media_type == "serial"
                    else "/static/img/anime-bg/tokyo-street.jpg"), "ახლანდელი ფონი"
        if row.layout == "portrait":
            return "", "ახლა ფიქსირებული სურათი არ დგას: ფონი ფილმებს მიჰყვება"
        return "", "ახლა ამ რიგს ფონი არ აქვს"

    spec_bg = service.ROLE_MAP.get("row_bg", {})
    spec_icon = service.ROLE_MAP.get("icon", {})
    bg = {}
    for r in rows:
        cur_url, cur_label = _bg_current(r)
        bg[r.id] = {
            "asset": service.art_asset(r, "row_bg"),
            "url": service.art_url(r, "row_bg", "w640"),
            "hint": _bg_hint(r),
            "size": spec_bg.get("size", ""),
            "size_note": spec_bg.get("size_note", ""),
            "current_url": cur_url,
            "current_label": cur_label,
            "icon_asset": service.art_asset(r, "icon"),
            "icon_url": service.art_url(r, "icon", "h64"),
            "icon_size": spec_icon.get("size", ""),
            "icon_size_note": spec_icon.get("size_note", ""),
        }
    from .home_items import row_items_view
    items = {r.id: row_items_view(r) for r in rows}

    genres = Genre.query.order_by(Genre.name).all()
    values = settings_store.all_values()

    pinned = values.get("hero_pinned_ids") or []
    pinned_titles = []
    if pinned:
        found = {m.id: m for m in Movie.query.filter(Movie.id.in_(pinned)).all()}
        pinned_titles = [
            {"id": pid, "title": found[pid].title if pid in found else "ვერ მოიძებნა"}
            for pid in pinned
        ]

    return render_template(
        "admin/home.html", rows=rows, genres=genres, settings=values, bg=bg,
        items=items,
        pinned_titles=pinned_titles,
        kinds=home_rows.KINDS, media_types=home_rows.MEDIA_TYPES,
        sorts=home_rows.SORTS, layouts=home_rows.LAYOUTS, icons=home_rows.ICONS,
    )


@admin_bp.route("/home/seed", methods=["POST"])
def home_seed():
    replace = bool(request.form.get("replace"))
    added = home_rows.seed(replace=replace)
    log_action("home.seed", detail="replace=%s added=%d" % (replace, added))
    if added:
        flash("ჩაიტვირთა %d ნაგულისხმევი რიგი." % added, "ok")
    else:
        flash("რიგები უკვე არსებობს. ჩასანაცვლებლად მონიშნეთ „არსებულის წაშლა“.", "error")
    return _back()


@admin_bp.route("/home/new", methods=["POST"])
def home_new():
    last = HomeRow.query.order_by(HomeRow.position.desc()).first()
    row = HomeRow(position=(last.position + 1) if last else 0)
    _apply_form(row)
    db.session.add(row)
    db.session.commit()
    log_action("home.new", "home_row", row.id, detail=row.title)
    flash("რიგი დაემატა.", "ok")
    return _back()


@admin_bp.route("/home/<int:row_id>/save", methods=["POST"])
def home_save(row_id):
    row = db.session.get(HomeRow, row_id)
    if row is None:
        flash("რიგი ვერ მოიძებნა.", "error")
        return _back()
    _apply_form(row)
    db.session.commit()
    log_action("home.save", "home_row", row_id, detail=row.title)
    flash("„%s“ შენახულია." % row.title, "ok")
    return _back()


@admin_bp.route("/home/<int:row_id>/delete", methods=["POST"])
def home_delete(row_id):
    row = db.session.get(HomeRow, row_id)
    if row is None:
        flash("რიგი ვერ მოიძებნა.", "error")
        return _back()
    title = row.title
    db.session.delete(row)
    db.session.commit()
    log_action("home.delete", "home_row", row_id, detail=title)
    flash("„%s“ წაიშალა." % title, "ok")
    return _back()


@admin_bp.route("/home/<int:row_id>/move", methods=["POST"])
def home_move(row_id):
    """რიგის აწევა-ჩამოწევა. პოზიციები ყოველ ჯერზე თავიდან ინომრება."""
    row = db.session.get(HomeRow, row_id)
    if row is None:
        flash("რიგი ვერ მოიძებნა.", "error")
        return _back()

    ordered = HomeRow.query.order_by(HomeRow.position, HomeRow.id).all()
    index = next((i for i, r in enumerate(ordered) if r.id == row_id), None)
    step = -1 if request.form.get("dir") == "up" else 1
    target = (index or 0) + step
    if index is not None and 0 <= target < len(ordered):
        ordered[index], ordered[target] = ordered[target], ordered[index]
    for position, item in enumerate(ordered):
        item.position = position
    db.session.commit()
    log_action("home.move", "home_row", row_id, detail=request.form.get("dir"))
    return _back()


@admin_bp.route("/home/settings", methods=["POST"])
def home_settings():
    admin_id = _admin_id()

    raw = (request.form.get("hero_pinned_ids") or "").replace(",", " ").split()
    pinned = []
    for token in raw:
        if token.isdigit() and int(token) not in pinned:
            pinned.append(int(token))
    settings_store.set_value("hero_pinned_ids", pinned, admin_id)

    exclude = (request.form.get("hero_exclude_genre") or "").strip()
    settings_store.set_value(
        "hero_exclude_genre", int(exclude) if exclude.isdigit() else None, admin_id
    )

    years = [y for y in (request.form.get("weekly_top_years") or "").replace(",", " ").split()
             if y.isdigit() and len(y) == 4]
    if years:
        settings_store.set_value("weekly_top_years", years, admin_id)
    try:
        limit = max(1, min(int(request.form.get("weekly_top_limit") or 50), 200))
        settings_store.set_value("weekly_top_limit", limit, admin_id)
    except ValueError:
        pass

    log_action("home.settings")
    flash("პარამეტრები შენახულია. კვირის ტოპი ახალი პარამეტრებით გადაითვლება.", "ok")
    return _back()
