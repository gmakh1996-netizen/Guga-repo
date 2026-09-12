"""უნივერსალური სურათის მართვა: ატვირთვა, ჩანაცვლება, მოხსნა.

ერთი წყვილი endpoint-ი ემსახურება ყველაფერს: ფილმს, სერიალს, მსახიობს,
მენიუს პუნქტს, მთავარი გვერდის რიგს, ჟანრს და საიტის გლობალურ სურათებს.
ამიტომ ახალი ადგილის დამატება მხოლოდ როლის აღწერას ითხოვს, ახალ კოდს არა.

    POST /admin/image/<subject_type>/<subject_id>/<role>/upload
    POST /admin/image/<subject_type>/<subject_id>/<role>/delete
    POST /admin/image/<subject_type>/<subject_id>/<role>/pick     (ბიბლიოთეკიდან)
    POST /admin/image/<subject_type>/<subject_id>/<role>/fetch    (გარე მისამართიდან)

subject_id = 0 ნიშნავს გლობალურს (საიტის ლოგო, ფონი და ა.შ.).
"""
from flask import flash, redirect, request

from medialib import service
from medialib.fetch import fetch_image
from medialib.images import MediaError
from models import Genre, HomeRow, MediaAsset, MenuItem, Movie, Person, Series, db

from . import admin_bp
from .auth import current_admin, log_action

# რომელ ობიექტზე ვუშვებთ სურათის მიბმას
SUBJECTS = {
    "site": None,          # გლობალური, subject_id = 0
    "movie": Movie,
    "series": Series,
    "person": Person,
    "menu_item": MenuItem,
    "home_row": HomeRow,
    "genre": Genre,
}


def _resolve(subject_type, subject_id, role):
    """ვამოწმებთ, რომ ობიექტიც და როლიც ნამდვილია. აბრუნებს (ok, spec)."""
    if subject_type not in SUBJECTS:
        return False, None
    spec = service.ROLE_MAP.get(role)
    if spec is None:
        return False, None
    Model = SUBJECTS[subject_type]
    if Model is None:                      # site
        return subject_id == 0, spec
    return db.session.get(Model, subject_id) is not None, spec


def _back():
    """იქვე ვბრუნდებით, საიდანაც ფორმა გამოიგზავნა."""
    target = request.form.get("next") or request.referrer or "/admin/"
    if not target.startswith("/admin"):
        target = "/admin/"
    return redirect(target)


def _guard(subject_type, subject_id, role):
    ok, spec = _resolve(subject_type, subject_id, role)
    if not ok:
        flash("არასწორი მისამართი (%s/%s/%s)." % (subject_type, subject_id, role), "error")
    return ok, spec


@admin_bp.route("/image/<subject_type>/<int:subject_id>/<role>/upload", methods=["POST"])
def image_upload(subject_type, subject_id, role):
    ok, spec = _guard(subject_type, subject_id, role)
    if not ok:
        return _back()

    admin = current_admin()
    try:
        asset = service.store_upload(
            request.files.get("file"), profile=spec["profile"],
            admin_id=admin.id if admin else None,
            alt=(request.form.get("alt") or "").strip() or None,
        )
    except MediaError as exc:
        flash(str(exc), "error")
        return _back()

    service.bind(subject_type, subject_id, role, asset)
    log_action("image.upload", subject_type, subject_id, detail=role)
    flash("%s განახლდა." % spec["label"], "ok")
    return _back()


@admin_bp.route("/image/<subject_type>/<int:subject_id>/<role>/fetch", methods=["POST"])
def image_fetch(subject_type, subject_id, role):
    ok, spec = _guard(subject_type, subject_id, role)
    if not ok:
        return _back()

    url = (request.form.get("url") or "").strip()
    admin = current_admin()
    try:
        data, name = fetch_image(url)
        asset = service.store_bytes(
            data, filename=name, profile=spec["profile"],
            admin_id=admin.id if admin else None, source="mirror", source_url=url,
        )
    except MediaError as exc:
        flash(str(exc), "error")
        return _back()

    service.bind(subject_type, subject_id, role, asset)
    log_action("image.fetch", subject_type, subject_id, detail="%s ← %s" % (role, url))
    flash("%s ჩამოიტვირთა (%d×%d)." % (spec["label"], asset.width, asset.height), "ok")
    return _back()


@admin_bp.route("/image/<subject_type>/<int:subject_id>/<role>/pick", methods=["POST"])
def image_pick(subject_type, subject_id, role):
    ok, spec = _guard(subject_type, subject_id, role)
    if not ok:
        return _back()

    asset_id = request.form.get("asset_id", type=int)
    asset = db.session.get(MediaAsset, asset_id) if asset_id else None
    if asset is None or asset.is_deleted:
        flash("ფაილი ვერ მოიძებნა ბიბლიოთეკაში.", "error")
        return _back()

    service.bind(subject_type, subject_id, role, asset)
    log_action("image.pick", subject_type, subject_id, detail=role)
    flash("%s განახლდა." % spec["label"], "ok")
    return _back()


@admin_bp.route("/image/<subject_type>/<int:subject_id>/<role>/delete", methods=["POST"])
def image_delete(subject_type, subject_id, role):
    ok, spec = _guard(subject_type, subject_id, role)
    if not ok:
        return _back()

    removed = service.unbind(subject_type, subject_id, role)
    log_action("image.delete", subject_type, subject_id, detail=role)
    flash("%s მოიხსნა." % spec["label"] if removed else "ისედაც ცარიელი იყო.", "ok")
    return _back()
