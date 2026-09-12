"""კონტენტი: ფილმებისა და სერიალების სია და თითოეულის სურათების მართვა."""
from flask import flash, redirect, render_template, request, url_for

from medialib import service
from medialib.fetch import fetch_image
from medialib.images import MediaError
from models import MediaAsset, Movie, Series, db

from . import admin_bp
from .auth import current_admin, log_action

MODELS = {"movie": Movie, "series": Series}
PER_PAGE = 40


def _model(subject_type):
    return MODELS.get(subject_type)


def _no_image(Model):
    """იგივე პირობა, რითაც საჯარო საიტი მალავს უსურათო ჩანაწერებს."""
    col = Model.poster_url
    return db.or_(
        col.is_(None), col == "",
        db.not_(db.or_(
            col.ilike("%.jpg"), col.ilike("%.jpeg"),
            col.ilike("%.png"), col.ilike("%.webp"),
        )),
    )


@admin_bp.route("/content")
def content_list():
    subject_type = request.args.get("type") or "movie"
    if subject_type not in MODELS:
        subject_type = "movie"
    Model = _model(subject_type)

    q = (request.args.get("q") or "").strip()
    only = request.args.get("only") or ""
    page = max(request.args.get("page", 1, type=int), 1)

    query = Model.query
    if q:
        query = query.filter(db.or_(
            Model.title.ilike("%%%s%%" % q),
            Model.original_title.ilike("%%%s%%" % q),
        ))
    if only == "missing":
        query = query.filter(_no_image(Model))
    elif only == "custom":
        from models import MediaLink
        owned = db.session.query(MediaLink.subject_id).filter(
            MediaLink.subject_type == subject_type
        )
        query = query.filter(Model.id.in_(owned))

    total = query.count()
    rows = (
        query.order_by(Model.release_date.desc(), Model.id.desc())
        .offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()
    )
    service.prefetch_art(rows)

    items = []
    for rec in rows:
        art = service.art_for(*service.subject_of(rec))
        items.append({
            "rec": rec,
            "thumb": (service.asset_url(art.get("backdrop"), profile="art")
                      or rec.poster_url or None),
            "custom": sorted(art.keys()),
        })

    return render_template(
        "admin/content_list.html", items=items, total=total, page=page,
        has_more=page * PER_PAGE < total, q=q, only=only,
        subject_type=subject_type,
    )


@admin_bp.route("/content/<subject_type>/<int:subject_id>")
def content_images(subject_type, subject_id):
    Model = _model(subject_type)
    if Model is None:
        flash("უცნობი ტიპი.", "error")
        return redirect(url_for("admin.content_list"))
    rec = db.session.get(Model, subject_id)
    if rec is None:
        flash("ჩანაწერი ვერ მოიძებნა.", "error")
        return redirect(url_for("admin.content_list", type=subject_type))

    art = service.art_for(subject_type, subject_id)
    rows = []
    for spec in service.TITLE_ROLES:
        asset = art.get(spec["role"])
        rows.append({
            **spec,
            "asset": asset,
            "url": service.asset_url(asset, profile=spec["profile"]) if asset else None,
        })

    public_url = ("/series/" if subject_type == "series" else "/movie/") + str(subject_id)
    return render_template(
        "admin/content_images.html", rec=rec, rows=rows,
        subject_type=subject_type, subject_id=subject_id,
        public_url=public_url, source_url=rec.poster_url or "",
    )


def _back(subject_type, subject_id):
    return redirect(url_for("admin.content_images",
                            subject_type=subject_type, subject_id=subject_id))


def _check(subject_type, subject_id, role):
    """აბრუნებს (rec, spec) ან (None, None), თუ მისამართი არასწორია."""
    Model = _model(subject_type)
    spec = service.TITLE_ROLE_MAP.get(role)
    if Model is None or spec is None:
        return None, None
    return db.session.get(Model, subject_id), spec


@admin_bp.route("/content/<subject_type>/<int:subject_id>/<role>/upload", methods=["POST"])
def content_image_upload(subject_type, subject_id, role):
    rec, spec = _check(subject_type, subject_id, role)
    if rec is None:
        flash("არასწორი მისამართი.", "error")
        return redirect(url_for("admin.content_list"))

    admin = current_admin()
    try:
        asset = service.store_upload(
            request.files.get("file"), profile=spec["profile"],
            admin_id=admin.id if admin else None,
        )
    except MediaError as exc:
        flash(str(exc), "error")
        return _back(subject_type, subject_id)

    service.bind(subject_type, subject_id, role, asset)
    log_action("content.image.upload", subject_type, subject_id, detail=role)
    flash("%s განახლდა." % spec["label"], "ok")
    return _back(subject_type, subject_id)


@admin_bp.route("/content/<subject_type>/<int:subject_id>/<role>/fetch", methods=["POST"])
def content_image_fetch(subject_type, subject_id, role):
    """ამჟამინდელი გარე სურათის ასლის ჩამოტვირთვა ჩვენს საცავში."""
    rec, spec = _check(subject_type, subject_id, role)
    if rec is None:
        flash("არასწორი მისამართი.", "error")
        return redirect(url_for("admin.content_list"))

    url = (request.form.get("url") or rec.poster_url or "").strip()
    admin = current_admin()
    try:
        data, name = fetch_image(url)
        asset = service.store_bytes(
            data, filename=name, profile=spec["profile"],
            admin_id=admin.id if admin else None,
            source="mirror", source_url=url,
        )
    except MediaError as exc:
        flash(str(exc), "error")
        return _back(subject_type, subject_id)

    service.bind(subject_type, subject_id, role, asset)
    log_action("content.image.fetch", subject_type, subject_id, detail="%s ← %s" % (role, url))
    flash("სურათი ჩამოიტვირთა და შეინახა (%d×%d)." % (asset.width, asset.height), "ok")
    return _back(subject_type, subject_id)


@admin_bp.route("/content/<subject_type>/<int:subject_id>/<role>/pick", methods=["POST"])
def content_image_pick(subject_type, subject_id, role):
    """ბიბლიოთეკაში უკვე არსებული ფაილის მიბმა."""
    rec, spec = _check(subject_type, subject_id, role)
    if rec is None:
        flash("არასწორი მისამართი.", "error")
        return redirect(url_for("admin.content_list"))

    asset_id = request.form.get("asset_id", type=int)
    asset = db.session.get(MediaAsset, asset_id) if asset_id else None
    if asset is None or asset.is_deleted:
        flash("ფაილი ვერ მოიძებნა ბიბლიოთეკაში.", "error")
        return _back(subject_type, subject_id)

    service.bind(subject_type, subject_id, role, asset)
    log_action("content.image.pick", subject_type, subject_id, detail=role)
    flash("%s განახლდა." % spec["label"], "ok")
    return _back(subject_type, subject_id)


@admin_bp.route("/content/<subject_type>/<int:subject_id>/<role>/delete", methods=["POST"])
def content_image_delete(subject_type, subject_id, role):
    rec, spec = _check(subject_type, subject_id, role)
    if rec is None:
        flash("არასწორი მისამართი.", "error")
        return redirect(url_for("admin.content_list"))

    removed = service.unbind(subject_type, subject_id, role)
    log_action("content.image.delete", subject_type, subject_id, detail=role)
    if removed:
        flash("%s მოიხსნა, საიტი ორიგინალ სურათს დაუბრუნდა." % spec["label"], "ok")
    else:
        flash("%s ისედაც ცარიელი იყო." % spec["label"], "ok")
    return _back(subject_type, subject_id)
