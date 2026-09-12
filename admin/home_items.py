"""მთავარი გვერდის რიგის შიგთავსი: ხელით შედგენა, შაფლი, გადათრევა.

თუ რიგს ფიქსირებული სია აქვს (`HomeRowItem`), საიტი ზუსტად მას აჩვენებს,
ამ თანმიმდევრობით. თუ არა, რიგი ავტომატურად ივსება, როგორც აქამდე.
შაფლიც იმავე სიას ავსებს, უბრალოდ შემთხვევითი შერჩევით იმავე კატეგორიიდან.
"""
import random

from flask import flash, jsonify, redirect, request, url_for

from medialib import service
from models import Genre, HomeRow, HomeRowItem, Movie, Series, db

from . import admin_bp
from .auth import log_action

ITEM_MODELS = {"movie": Movie, "tv": Series}
ANIME_GENRE = 900000025
ANIMATION_GENRE = 900000009


def _back():
    return redirect(url_for("admin.home_builder"))


def _has_image(Model):
    col = Model.poster_url
    return db.and_(
        col.isnot(None), col != "",
        db.or_(col.ilike("%.jpg"), col.ilike("%.jpeg"),
               col.ilike("%.png"), col.ilike("%.webp")),
    )


def row_candidates(row):
    """საიდან ირჩევს შაფლი: იგივე წესები, რითაც რიგი ავტომატურად ივსება."""
    media = row.media_type or "movie"
    pairs = []
    if media in ("anime", "animation"):
        genre = ANIME_GENRE if media == "anime" else ANIMATION_GENRE
        for key, Model in ITEM_MODELS.items():
            pairs.append((key, Model.query.filter(
                Model.genres.any(Genre.id == genre), _has_image(Model))))
    elif media == "trailer":
        pairs.append(("movie", Movie.query.filter(
            Movie.trailer_key.isnot(None), _has_image(Movie))))
    else:
        key = "tv" if media in ("serial", "tv", "series") else "movie"
        Model = ITEM_MODELS[key]
        query = Model.query.filter(_has_image(Model))
        if row.genre_id:
            query = query.filter(Model.genres.any(Genre.id == row.genre_id))
        if row.exclude_genre_id:
            query = query.filter(~Model.genres.any(Genre.id == row.exclude_genre_id))
        pairs.append((key, query))
    return pairs


def row_items_view(row):
    """რიგის ფიქსირებული სია სათაურითა და ესკიზით (ბექოფისის ვერტიკალური სია)."""
    items = sorted(row.items, key=lambda i: i.position)
    if not items:
        return []

    by_type = {}
    for it in items:
        by_type.setdefault(it.media_type, []).append(it.item_id)

    found = {}
    for key, ids in by_type.items():
        Model = ITEM_MODELS.get(key)
        if Model is None:
            continue
        recs = Model.query.filter(Model.id.in_(ids)).all()
        service.prefetch_art(recs)
        for rec in recs:
            found[(key, rec.id)] = rec

    view = []
    for it in items:
        rec = found.get((it.media_type, it.item_id))
        view.append({
            "pk": it.id,
            "media_type": it.media_type,
            "item_id": it.item_id,
            "title": rec.title if rec else "ვერ მოიძებნა (#%d)" % it.item_id,
            "year": (rec.year if rec else ""),
            "thumb": ((service.art_url(rec, "backdrop", "w320") or rec.poster_url)
                      if rec else None),
            "url": ("/series/" if it.media_type == "tv" else "/movie/") + str(it.item_id),
        })
    return view


def _renumber(row_id):
    items = (HomeRowItem.query.filter_by(row_id=row_id)
             .order_by(HomeRowItem.position, HomeRowItem.id).all())
    for position, it in enumerate(items):
        it.position = position


@admin_bp.route("/home/<int:row_id>/shuffle", methods=["POST"])
def home_shuffle(row_id):
    """სიის შემთხვევითი შევსება რიგის საკუთარი კატეგორიიდან."""
    row = db.session.get(HomeRow, row_id)
    if row is None:
        flash("რიგი ვერ მოიძებნა.", "error")
        return _back()

    limit = max(3, min(row.item_limit or 18, 60))
    pairs = row_candidates(row)
    per_source = max(1, limit // max(len(pairs), 1)) + 3

    picked = []
    for key, query in pairs:
        for rec in query.order_by(db.func.random()).limit(per_source).all():
            picked.append((key, rec.id))
    random.shuffle(picked)
    picked = picked[:limit]

    if not picked:
        flash("ამ კატეგორიაში ჩანაწერი ვერ მოიძებნა.", "error")
        return _back()

    HomeRowItem.query.filter_by(row_id=row.id).delete(synchronize_session=False)
    for position, (key, rec_id) in enumerate(picked):
        db.session.add(HomeRowItem(row_id=row.id, media_type=key,
                                   item_id=rec_id, position=position))
    db.session.commit()
    log_action("home.shuffle", "home_row", row_id, detail="%d ჩანაწერი" % len(picked))
    flash("„%s“ შეიშაფლა: %d ჩანაწერი." % (row.title, len(picked)), "ok")
    return _back()


@admin_bp.route("/home/<int:row_id>/items/clear", methods=["POST"])
def home_items_clear(row_id):
    row = db.session.get(HomeRow, row_id)
    if row is None:
        flash("რიგი ვერ მოიძებნა.", "error")
        return _back()
    removed = HomeRowItem.query.filter_by(row_id=row.id).delete(synchronize_session=False)
    db.session.commit()
    log_action("home.items.clear", "home_row", row_id, detail=str(removed))
    flash("სია გასუფთავდა, რიგი ისევ ავტომატურად ივსება.", "ok")
    return _back()


@admin_bp.route("/home/<int:row_id>/items/add", methods=["POST"])
def home_items_add(row_id):
    row = db.session.get(HomeRow, row_id)
    if row is None:
        flash("რიგი ვერ მოიძებნა.", "error")
        return _back()

    raw = (request.form.get("media_type") or "movie").strip()
    media_type = "tv" if raw.startswith(("tv", "ser")) else "movie"
    item_id = request.form.get("item_id", type=int)
    Model = ITEM_MODELS[media_type]
    if not item_id or db.session.get(Model, item_id) is None:
        flash("ასეთი ჩანაწერი ვერ მოიძებნა.", "error")
        return _back()

    if HomeRowItem.query.filter_by(row_id=row.id, media_type=media_type,
                                   item_id=item_id).first() is not None:
        flash("ეს უკვე სიაშია.", "error")
        return _back()

    last = (HomeRowItem.query.filter_by(row_id=row.id)
            .order_by(HomeRowItem.position.desc()).first())
    db.session.add(HomeRowItem(
        row_id=row.id, media_type=media_type, item_id=item_id,
        position=(last.position + 1) if last else 0,
    ))
    db.session.commit()
    log_action("home.items.add", "home_row", row_id,
               detail="%s:%d" % (media_type, item_id))
    flash("დაემატა სიაში.", "ok")
    return _back()


@admin_bp.route("/home/<int:row_id>/items/<int:pk>/remove", methods=["POST"])
def home_items_remove(row_id, pk):
    it = db.session.get(HomeRowItem, pk)
    if it is None or it.row_id != row_id:
        flash("ჩანაწერი ვერ მოიძებნა.", "error")
        return _back()
    db.session.delete(it)
    db.session.commit()
    _renumber(row_id)
    db.session.commit()
    log_action("home.items.remove", "home_row", row_id, detail=str(pk))
    flash("მოიხსნა სიიდან.", "ok")
    return _back()


@admin_bp.route("/home/<int:row_id>/items/reorder", methods=["POST"])
def home_items_reorder(row_id):
    """გადათრევის შედეგი: ფილმების ახალი თანმიმდევრობა."""
    order = request.form.get("order") or ""
    ids = [int(x) for x in order.split(",") if x.strip().isdigit()]
    items = {it.id: it for it in HomeRowItem.query.filter_by(row_id=row_id).all()}

    position = 0
    for pk in ids:
        if pk in items:
            items[pk].position = position
            position += 1
    for pk, it in items.items():          # რაც სიაში არ მოხვდა, ბოლოში
        if pk not in ids:
            it.position = position
            position += 1
    db.session.commit()
    log_action("home.items.reorder", "home_row", row_id, detail=str(len(ids)))
    return jsonify(ok=True, count=len(ids))


@admin_bp.route("/home/reorder", methods=["POST"])
def home_reorder():
    """რიგების გადათრევა: ახალი თანმიმდევრობა ერთ მოთხოვნაში."""
    order = request.form.get("order") or ""
    ids = [int(x) for x in order.split(",") if x.strip().isdigit()]
    rows = {r.id: r for r in HomeRow.query.all()}

    position = 0
    for row_id in ids:
        if row_id in rows:
            rows[row_id].position = position
            position += 1
    for row_id, row in rows.items():
        if row_id not in ids:
            row.position = position
            position += 1
    db.session.commit()
    log_action("home.reorder", detail="%d რიგი" % len(ids))
    return jsonify(ok=True, count=len(ids))


@admin_bp.route("/home/search")
def home_search():
    """სათაურით ძებნა, რომ რიგში ხელით დაამატოთ."""
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify(items=[])

    out = []
    for key, Model in ITEM_MODELS.items():
        recs = (Model.query.filter(
            db.or_(Model.title.ilike("%%%s%%" % q),
                   Model.original_title.ilike("%%%s%%" % q)),
            _has_image(Model))
            .order_by(Model.release_date.desc()).limit(8).all())
        for rec in recs:
            out.append({
                "media_type": key, "id": rec.id, "title": rec.title,
                "year": rec.year or "", "thumb": rec.poster_url or "",
                "kind": "სერიალი" if key == "tv" else "ფილმი",
            })
    out.sort(key=lambda x: x["year"], reverse=True)
    return jsonify(items=out[:12])

@admin_bp.route("/home/<int:row_id>/items/<int:pk>/replace", methods=["POST"])
def home_items_replace(row_id, pk):
    """ამ ადგილზე მდგომი ფილმის ჩანაცვლება სხვით, ნომრის შენარჩუნებით."""
    it = db.session.get(HomeRowItem, pk)
    if it is None or it.row_id != row_id:
        flash("ჩანაწერი ვერ მოიძებნა.", "error")
        return _back()

    raw = (request.form.get("media_type") or "movie").strip()
    media_type = "tv" if raw.startswith(("tv", "ser")) else "movie"
    item_id = request.form.get("item_id", type=int)
    Model = ITEM_MODELS[media_type]
    rec = db.session.get(Model, item_id) if item_id else None
    if rec is None:
        flash("ასეთი ჩანაწერი ვერ მოიძებნა.", "error")
        return _back()

    clash = HomeRowItem.query.filter(
        HomeRowItem.row_id == row_id,
        HomeRowItem.media_type == media_type,
        HomeRowItem.item_id == item_id,
        HomeRowItem.id != pk,
    ).first()
    if clash is not None:
        flash("ეს უკვე სიაშია, სხვა ადგილას.", "error")
        return _back()

    old = "%s:%d" % (it.media_type, it.item_id)
    it.media_type = media_type
    it.item_id = item_id
    db.session.commit()
    log_action("home.items.replace", "home_row", row_id,
               detail="%s → %s:%d" % (old, media_type, item_id))
    flash("ჩანაცვლდა: %s" % rec.title, "ok")
    return _back()


@admin_bp.route("/home/<int:row_id>/items/<int:pk>/move-to", methods=["POST"])
def home_items_move_to(row_id, pk):
    """ნომრის პირდაპირ მითითება: ჩანაწერი გადადის მე-N ადგილზე."""
    it = db.session.get(HomeRowItem, pk)
    if it is None or it.row_id != row_id:
        flash("ჩანაწერი ვერ მოიძებნა.", "error")
        return _back()

    items = (HomeRowItem.query.filter_by(row_id=row_id)
             .order_by(HomeRowItem.position, HomeRowItem.id).all())
    target = request.form.get("position", type=int) or 1
    target = max(1, min(target, len(items))) - 1        # 1-იდან ითვლება

    items.remove(it)
    items.insert(target, it)
    for position, item in enumerate(items):
        item.position = position
    db.session.commit()
    log_action("home.items.move_to", "home_row", row_id,
               detail="%d → %d" % (pk, target + 1))
    flash("გადავიდა %d-ე ადგილზე." % (target + 1), "ok")
    return _back()
