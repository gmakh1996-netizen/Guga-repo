"""საჯარო მისამართი მედიისთვის: /m/<asset_id>/<name>-<sha8>.<ext>

მისამართში ჰეში იმიტომ წერია, რომ ფაილი სამუდამოდ ქეშირებადი იყოს: სურათის
შეცვლისას მისამართიც იცვლება, ანუ ვიზიტორს ძველი ვერსია აღარ დარჩება.

R2/CDN-ის რეჟიმში ეს მარშრუტი საერთოდ არ გამოიყენება: `asset_url()` პირდაპირ
CDN-ის მისამართს აბრუნებს და სურათები Python-ს გვერდს უვლიან.
"""
import os

from flask import Blueprint, abort, make_response, redirect, send_file

from models import db, MediaAsset
from .storage import LocalStorage, get_storage

media_bp = Blueprint("media", __name__)


def _missing(asset):
    """ფაილი საცავში არ არის: ვბრუნდებით ორიგინალ, გარე მისამართზე.

    ეს ის შემთხვევაა, როცა ბაზა ახალ სერვერზე გადავიდა, საცავი კი ჯერ ცარიელია
    (`media/` გიტში არ მიდის). ასეთ დროს გატეხილი სურათის ნაცვლად ვიზიტორი
    ხედავს იმავე სურათს პირვანდელი წყაროდან, საიტი კი უცვლელად მუშაობს.
    გადამისამართება დროებითია (302), ანუ ფაილების ატვირთვისთანავე თავისით სწორდება.
    """
    if asset is not None and asset.source_url:
        resp = redirect(asset.source_url, code=302)
        resp.headers["Cache-Control"] = "public, max-age=300"
        return resp
    abort(404)

_MIME = {
    "webp": "image/webp", "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png", "gif": "image/gif", "ico": "image/x-icon",
}

CACHE = "public, max-age=31536000, immutable"


@media_bp.route("/m/<int:asset_id>/<path:filename>")
def serve(asset_id, filename):
    asset = db.session.get(MediaAsset, asset_id)
    if asset is None or asset.is_deleted:
        abort(404)

    stem, _, ext = filename.rpartition(".")
    if not stem or not ext:
        abort(404)
    name = stem.rsplit("-", 1)[0]  # "w640-1a2b3c4d" → "w640"

    if name == "orig":
        key, mime = asset.storage_key, asset.mime
    else:
        variant = asset.variant(name, ext)
        if variant is None:
            abort(404)
        key, mime = variant.storage_key, _MIME.get(ext, "application/octet-stream")

    storage = get_storage()
    if isinstance(storage, LocalStorage):
        path = storage.path(key)
        if not os.path.exists(path):
            return _missing(asset)
        resp = make_response(send_file(path, mimetype=mime, conditional=True))
    else:
        try:
            data = storage.read(key)
        except Exception:  # noqa: BLE001
            return _missing(asset)
        resp = make_response(data)
        resp.headers["Content-Type"] = mime

    resp.headers["Cache-Control"] = CACHE
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp
