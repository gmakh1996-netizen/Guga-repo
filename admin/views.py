"""ბექოფისის ეკრანები: დაფა, ბრენდინგი, მედია-ბიბლიოთეკა."""
import os

from flask import (
    current_app, flash, jsonify, redirect, render_template, request, url_for,
)

import settings_store
from medialib import service
from medialib.images import MediaError, webp_supported
from medialib.storage import LocalStorage, get_storage
from models import db, MediaAsset, MediaLink, Movie, Person, Series

from . import admin_bp
from .auth import log_action

PER_PAGE = 48


def _human_bytes(n):
    if n is None:
        return "?"
    for unit in ("ბ", "კბ", "მბ", "გბ", "ტბ"):
        if n < 1024 or unit == "ტბ":
            return "%.0f %s" % (n, unit) if unit == "ბ" else "%.1f %s" % (n, unit)
        n /= 1024.0
    return "%.1f ტბ" % n


# ------------------------------------------------------------------ დაფა

@admin_bp.route("/")
def dashboard():
    storage = get_storage()
    assets_count = MediaAsset.query.filter_by(is_deleted=False).count()
    assets_bytes = (
        db.session.query(db.func.sum(MediaAsset.bytes))
        .filter(MediaAsset.is_deleted.is_(False)).scalar() or 0
    )

    # სურათის გარეშე დარჩენილი ჩანაწერები (იგივე პირობა, რითაც საიტი მალავს)
    def _broken(Model):
        col = Model.poster_url
        return Model.query.filter(
            db.or_(
                col.is_(None), col == "",
                db.not_(db.or_(
                    col.ilike("%.jpg"), col.ilike("%.jpeg"),
                    col.ilike("%.png"), col.ilike("%.webp"),
                )),
            )
        ).count()

    warnings = []
    if not webp_supported():
        warnings.append("Pillow-ს WebP მხარდაჭერა არ აქვს: მხოლოდ JPEG/PNG ვარიანტები შეიქმნება.")
    if current_app.config.get("SECRET_KEY") in ("dev-secret-change-me", "change_me_in_production"):
        warnings.append("SECRET_KEY ნაგულისხმევია. შეცვალეთ .env-ში, თორემ სესია არ არის დაცული.")
    if isinstance(storage, LocalStorage):
        root = os.path.abspath(storage.root)
        base = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        if root.startswith(base + os.sep) or root == base:
            warnings.append(
                "MEDIA_ROOT პროექტის საქაღალდეშია (%s). ლოკალურად ეს ნორმალურია, "
                "მაგრამ Railway-ზე ატვირთული ფაილები შემდეგ deploy-ზე წაიშლება. "
                "პროდაქშენში დააყენეთ volume (MEDIA_ROOT=/data/media) ან MEDIA_BACKEND=r2." % root
            )

    stats = {
        "movies": Movie.query.count(),
        "series": Series.query.count(),
        "persons": Person.query.count(),
        "assets": assets_count,
        "assets_bytes": _human_bytes(assets_bytes),
        "broken_movies": _broken(Movie),
        "broken_series": _broken(Series),
        "storage_backend": storage.backend,
        "storage_free": _human_bytes(storage.free_bytes()) if isinstance(storage, LocalStorage) else None,
    }
    brand_roles = service.site_assets()
    missing_brand = [r for r in service.SITE_ROLES if r["role"] not in brand_roles]
    return render_template(
        "admin/dashboard.html", stats=stats, warnings=warnings,
        missing_brand=missing_brand,
    )


# ------------------------------------------------------------- ბრენდინგი

@admin_bp.route("/branding")
def branding():
    assets = service.site_assets()
    # რა ჩანს საიტზე ახლა, სანამ ბექოფისიდან არაფერი აიტვირთა
    CURRENT = {
        "logo_light": ("/static/img/logo.png", "ახლანდელი ლოგო"),
        "favicon": ("/static/favicon.png", "ახლანდელი აიქონი"),
        "popup_ad": ("/static/img/popup-ad.jpg", "ახლანდელი ბანერი"),
        "placeholder_poster": (service.THEME_PLACEHOLDER, "თემის ნაგულისხმევი"),
        "placeholder_person": (service.THEME_PLACEHOLDER, "თემის ნაგულისხმევი"),
        "logo_dark": ("", "ცარიელის შემთხვევაში ძირითადი ლოგო გამოიყენება"),
        "logo_mobile": ("", "ცარიელის შემთხვევაში ძირითადი ლოგო გამოიყენება"),
        "page_background": ("", "ახლა თემის ნაგულისხმევი ფონია"),
        "og_default": ("", "ახლა გაზიარებისას სურათი არ ჩანს"),
    }
    rows = []
    for spec in service.SITE_ROLES:
        asset = assets.get(spec["role"])
        current_url, current_label = CURRENT.get(spec["role"], ("", ""))
        rows.append({
            **spec,
            "asset": asset,
            "url": service.asset_url(asset, profile=spec["profile"]) if asset else None,
            "current_url": current_url,
            "current_label": current_label,
        })
    return render_template(
        "admin/branding.html", rows=rows, settings=settings_store.all_values(),
    )


@admin_bp.route("/branding/settings", methods=["POST"])
def branding_settings():
    from .auth import current_admin
    admin = current_admin()
    admin_id = admin.id if admin else None

    site_name = (request.form.get("site_name") or "").strip()
    if site_name:
        settings_store.set_value("site_name", site_name, admin_id)
    settings_store.set_value("logo_alt", (request.form.get("logo_alt") or "").strip(), admin_id)
    try:
        height = int(request.form.get("logo_height") or 52)
        settings_store.set_value("logo_height", max(16, min(height, 200)), admin_id)
    except ValueError:
        pass
    settings_store.set_value("popup_ad_url", (request.form.get("popup_ad_url") or "").strip(), admin_id)
    settings_store.set_value("popup_ad_enabled", bool(request.form.get("popup_ad_enabled")), admin_id)

    behavior = request.form.get("broken_image_behavior")
    if behavior in ("hide", "placeholder"):
        settings_store.set_value("broken_image_behavior", behavior, admin_id)

    log_action("branding.settings")
    flash("პარამეტრები შენახულია.", "ok")
    return redirect(url_for("admin.branding"))


# ------------------------------------------------------- მედია-ბიბლიოთეკა

@admin_bp.route("/media")
def media_library():
    page = max(request.args.get("page", 1, type=int), 1)
    q = (request.args.get("q") or "").strip()
    only = request.args.get("only") or ""

    query = MediaAsset.query.filter_by(is_deleted=False)
    if q:
        query = query.filter(db.or_(
            MediaAsset.original_filename.ilike("%%%s%%" % q),
            MediaAsset.alt_text.ilike("%%%s%%" % q),
        ))
    if only == "orphan":
        used = db.session.query(MediaLink.asset_id).distinct()
        query = query.filter(~MediaAsset.id.in_(used))
    elif only == "site":
        used = db.session.query(MediaLink.asset_id).filter(
            MediaLink.subject_type == service.SITE
        )
        query = query.filter(MediaAsset.id.in_(used))

    total = query.count()
    assets = (
        query.order_by(MediaAsset.uploaded_at.desc(), MediaAsset.id.desc())
        .offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()
    )
    items = [{
        "asset": a,
        "url": service.asset_url(a, profile="art"),
        "uses": len(service.usage(a)),
        "size": _human_bytes(a.bytes),
    } for a in assets]

    return render_template(
        "admin/media.html", items=items, total=total, page=page,
        per_page=PER_PAGE, has_more=page * PER_PAGE < total, q=q, only=only,
    )


@admin_bp.route("/media/upload", methods=["POST"])
def media_upload():
    from .auth import current_admin
    admin = current_admin()
    profile = request.form.get("profile") or "art"
    saved, errors = [], []
    for file_storage in request.files.getlist("files"):
        try:
            asset = service.store_upload(
                file_storage, profile=profile, admin_id=admin.id if admin else None
            )
            saved.append(asset.id)
        except MediaError as exc:
            errors.append("%s: %s" % (file_storage.filename, exc))

    if saved:
        log_action("media.upload", "media_asset", ",".join(str(i) for i in saved))
        flash("ატვირთულია %d ფაილი." % len(saved), "ok")
    for err in errors:
        flash(err, "error")
    return redirect(url_for("admin.media_library"))


@admin_bp.route("/media/<int:asset_id>")
def media_detail(asset_id):
    asset = db.session.get(MediaAsset, asset_id)
    if asset is None:
        return jsonify(error="ვერ მოიძებნა"), 404
    links = service.usage(asset)
    return jsonify(
        id=asset.id,
        filename=asset.original_filename,
        mime=asset.mime,
        width=asset.width,
        height=asset.height,
        bytes=asset.bytes,
        size=_human_bytes(asset.bytes),
        alt=asset.alt_text,
        url=service.asset_url(asset),
        uploaded_at=asset.uploaded_at.isoformat() if asset.uploaded_at else None,
        variants=[{"name": v.name, "fmt": v.fmt, "width": v.width,
                   "height": v.height, "size": _human_bytes(v.bytes)}
                  for v in sorted(asset.variants, key=lambda v: (v.name, v.fmt))],
        uses=[{"subject_type": l.subject_type, "subject_id": l.subject_id,
               "role": l.role} for l in links],
    )


@admin_bp.route("/media/<int:asset_id>/delete", methods=["POST"])
def media_delete(asset_id):
    asset = db.session.get(MediaAsset, asset_id)
    if asset is None:
        flash("ფაილი ვერ მოიძებნა.", "error")
        return redirect(url_for("admin.media_library"))
    uses = len(service.usage(asset))
    service.delete_asset(asset, hard=False)
    log_action("media.delete", "media_asset", asset_id)
    if uses:
        flash("ფაილი წაიშალა და %d ადგილას მოიხსნა." % uses, "ok")
    else:
        flash("ფაილი წაიშალა.", "ok")
    return redirect(url_for("admin.media_library", **request.args.to_dict()))
