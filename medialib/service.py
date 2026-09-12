"""მედიის სერვისი: ატვირთვა, მიბმა, მისამართის აგება, წაშლა.

ეს არის ერთადერთი ადგილი, საიდანაც საიტი სურათს იღებს. შაბლონები და JSON API
`brand_bundle()`-ს და `asset_url()`-ს იყენებენ, არა პირდაპირ ბაზას.
"""
import hashlib
from datetime import datetime, timezone

from models import db, MediaAsset, MediaVariant, MediaLink
from . import images
from .images import MediaError
from .storage import get_storage

SITE = "site"

# გლობალური (საიტის) როლები — ბრენდინგის ეკრანი ამ სიით იხატება
SITE_ROLES = [
    {"role": "logo_light", "size": "სიმაღლე 120 px ან მეტი, PNG გამჭვირვალე ფონით", "size_note": "ჩანს 52 px სიმაღლეზე (მობილურზე 28)", "label": "ლოგო", "profile": "logo",
     "hint": "PNG გამჭვირვალე ფონით. გამოჩნდება header-ში, 52 პიქსელის სიმაღლეზე."},
    {"role": "logo_dark", "size": "სიმაღლე 120 px ან მეტი, PNG გამჭვირვალე ფონით", "size_note": "იგივე ადგილი, მუქ ფონზე", "label": "ლოგო (მუქი ფონისთვის)", "profile": "logo",
     "hint": "არასავალდებულო. თუ ცარიელია, ყველგან ძირითადი ლოგო გამოჩნდება."},
    {"role": "logo_mobile", "size": "სიმაღლე 80 px ან მეტი, PNG გამჭვირვალე ფონით", "size_note": "ჩანს 28 px სიმაღლეზე", "label": "ლოგო (მობილური)", "profile": "logo",
     "hint": "არასავალდებულო. ვიწრო ეკრანზე ხშირად მხოლოდ ნიშანი გამოდგება."},
    {"role": "favicon", "size": "512×512 px, კვადრატული", "size_note": "მისგან იჭრება 16-დან 512-მდე ყველა ზომა", "label": "Favicon", "profile": "icon",
     "hint": "ერთი კვადრატული სურათი, სასურველია 512×512. ნაკრები (ico, 16-512px, "
             "apple-touch) ავტომატურად დაგენერირდება."},
    {"role": "og_default", "size": "1200×630 px", "size_note": "Facebook-ისა და Telegram-ის სტანდარტი", "label": "სოციალური ქსელის სურათი", "profile": "banner",
     "hint": "როცა საიტის ბმულს Facebook-ზე ან Telegram-ზე გააზიარებენ. 1200×630."},
    {"role": "placeholder_poster", "size": "800×450 px (16:9)", "size_note": "ბარათი ჩანს 367×206 px-ზე", "label": "ჩამნაცვლებელი: ფილმი", "profile": "art",
     "hint": "რა გამოჩნდეს, როცა ფილმს სურათი არ აქვს ან არ ჩაიტვირთა."},
    {"role": "placeholder_person", "size": "400×400 px, კვადრატული", "size_note": "ჩანს მრგვლად", "label": "ჩამნაცვლებელი: მსახიობი", "profile": "art",
     "hint": "იგივე, მსახიობის მრგვალი ფოტოსთვის."},
    {"role": "popup_ad", "size": "1400×200 px (7:1)", "size_note": "ბანერი ჩანს 700×100 px-ზე", "label": "პოპაპ-ბანერი", "profile": "banner",
     "hint": "მთავარ გვერდზე ამომხტარი ბანერი. დღევანდელი ზომაა 1400×196."},
    {"role": "page_background", "size": "1920×1080 px", "size_note": "იჭიმება მთელ ეკრანზე", "label": "საიტის ფონი", "profile": "art",
     "hint": "მთელი საიტის უკანა ფონი. ცარიელის შემთხვევაში თემის ნაგულისხმევი ფონი რჩება."},
]

SITE_ROLE_MAP = {r["role"]: r for r in SITE_ROLES}

# ფილმის/სერიალის როლები. ge.movie-დან მხოლოდ ერთი landscape სურათი მოდის,
# რომელიც ერთდროულად ბარათიცაა, ჰეროს ფონიც და დეტალურის ფონიც. აქ ისინი იყოფა.
TITLE_ROLES = [
    {"role": "backdrop", "size": "1280×720 px (16:9)", "size_note": "ბარათი 367×206, დეტალურის ფონი 1128 px", "label": "ბარათის სურათი", "profile": "art",
     "hint": "განივი (16:9). ჩანს ბარათებზე, დეტალური გვერდის ფონად და ძებნაში."},
    {"role": "poster", "size": "600×900 px (2:3)", "size_note": "ვერტიკალური ბარათი ჩანს 152×228 px-ზე", "label": "ვერტიკალური პოსტერი", "profile": "portrait",
     "hint": "2:3. დღეს ბაზაში არცერთ ფილმს არ აქვს, ამიტომ ბარათებზე განივი სურათი დგას."},
    {"role": "hero", "size": "1920×960 px (2:1)", "size_note": "მთავარის დიდი ბლოკი ჩანს 1128×560 px-ზე", "label": "ჰეროს განიერი სურათი", "profile": "art",
     "hint": "მთავარი გვერდის დიდი ბლოკისთვის. ცარიელის შემთხვევაში ბარათის სურათი გამოიყენება."},
]

TITLE_ROLE_MAP = {r["role"]: r for r in TITLE_ROLES}

# სხვა ობიექტების როლები (მენიუ, რიგები, მსახიობები)
OTHER_ROLES = [
    {"role": "icon", "size": "64×64 px, კვადრატული, გამჭვირვალე PNG", "size_note": "ჩანს 18-22 px-ზე", "label": "აიქონი", "profile": "logo",
     "hint": "ატვირთული სურათი ჩაშენებული აიქონის ნაცვლად. კვადრატული, გამჭვირვალე PNG."},
    {"role": "row_bg", "size": "1920×480 px", "size_note": "რიგის ფონი ჩანს 1910×420 px-ზე", "label": "რიგის ფონი", "profile": "banner",
     "hint": "ფართო სურათი, რომელიც რიგის უკან გაიშლება."},
    {"role": "photo", "size": "400×600 px (2:3)", "size_note": "მსახიობის ფოტო ჩანს მრგვლად", "label": "ფოტო", "profile": "portrait",
     "hint": "მსახიობის ფოტო. კვადრატულად ან ვერტიკალურად."},
]

ALL_ROLES = TITLE_ROLES + SITE_ROLES + OTHER_ROLES

ROLE_PROFILE = {r["role"]: r["profile"] for r in ALL_ROLES}
ROLE_MAP = {r["role"]: r for r in ALL_ROLES}

# რომელი ზომა ავიღოთ, როცა კონკრეტული არ არის მითითებული
DEFAULT_PREFERENCE = {
    "logo": ["h128", "h256", "h64"],
    "icon": ["i192", "i180", "i512"],
    "art": ["w640", "w320", "w1280"],
    "portrait": ["w300", "w600"],
    "banner": ["w1400", "w640"],
    "raw": [],
}


# ---------------------------------------------------------------- ატვირთვა

def _keys(sha256, ext):
    return "orig/%s/%s/%s.%s" % (sha256[:2], sha256[2:4], sha256, ext)


def _variant_key(sha256, name, ext):
    return "var/%s/%s/%s/%s.%s" % (sha256[:2], sha256[2:4], sha256, name, ext)


def store_bytes(data, filename=None, profile="art", admin_id=None,
                source="upload", source_url=None, alt=None):
    """ბაიტებიდან MediaAsset. ერთი და იგივე ფაილი მეორედ არ ინახება."""
    info = images.probe(data)
    sha256 = hashlib.sha256(data).hexdigest()

    storage = get_storage()
    existing = MediaAsset.query.filter_by(sha256=sha256).first()
    if existing is not None:
        if existing.is_deleted:  # ნაგვიდან დაბრუნება
            existing.is_deleted = False
            existing.deleted_at = None
            db.session.commit()
        # ჩანაწერი არის, ფაილი კი შეიძლება არ იყოს: ასე ხდება, როცა ბაზა გიტით
        # გადადის ახალ სერვერზე, სადაც საცავი ჯერ ცარიელია. ასეთ შემთხვევაში
        # იმავე კომანდის ხელახლა გაშვება აღადგენს ფაილს, ახალს არ ქმნის.
        missing_variants = [
            v for v in existing.variants if not storage.exists(v.storage_key)
        ]
        if not storage.exists(existing.storage_key):
            storage.save(existing.storage_key, data, mime=existing.mime)
        if not existing.variants or missing_variants:
            generate_variants(existing, data, profile)
        else:
            # იგივე ფაილი სხვა როლზეც გამოიყენეს (მაგ. ჯერ ბანერად, მერე აიქონად).
            # ამ პროფილის ზომები შეიძლება არ არსებობდეს — დავამატოთ, არსებულის
            # წაშლის გარეშე, თორემ პირველი როლი სურათებს დაკარგავდა.
            ensure_variants(existing, data, profile)
        return existing

    key = _keys(sha256, info["ext"])
    storage.save(key, data, mime=info["mime"])

    asset = MediaAsset(
        sha256=sha256,
        storage_backend=storage.backend,
        storage_key=key,
        mime=info["mime"],
        ext=info["ext"],
        width=info["width"],
        height=info["height"],
        bytes=len(data),
        has_alpha=info["has_alpha"],
        source=source,
        source_url=source_url,
        original_filename=(filename or "")[:255] or None,
        alt_text=(alt or None),
        uploaded_by=admin_id,
    )
    db.session.add(asset)
    db.session.flush()

    generate_variants(asset, data, profile, commit=False)
    db.session.commit()
    return asset


def generate_variants(asset, data=None, profile="art", commit=True):
    """წარმოებული ზომების (ხელახლა) გენერაცია."""
    storage = get_storage()
    if data is None:
        data = storage.read(asset.storage_key)

    for old in list(asset.variants):
        storage.delete(old.storage_key)
        db.session.delete(old)
    # წაშლა ბაზაში ჩასმამდე უნდა მივიდეს, თორემ იმავე (asset, name, fmt)-ზე
    # ახალი ჩანაწერი უნიკალურობის შეზღუდვას დაეჯახება
    db.session.flush()

    made = images.derive(data, profile, has_alpha=asset.has_alpha)
    for item in made:
        key = _variant_key(asset.sha256, item["name"], item["fmt"])
        mime = {"webp": "image/webp", "jpg": "image/jpeg", "png": "image/png",
                "ico": "image/x-icon"}.get(item["fmt"], "application/octet-stream")
        storage.save(key, item["data"], mime=mime)
        db.session.add(MediaVariant(
            asset_id=asset.id, name=item["name"], fmt=item["fmt"], storage_key=key,
            width=item["width"], height=item["height"], bytes=len(item["data"]),
        ))
    if commit:
        db.session.commit()
    return len(made)


def ensure_variants(asset, data=None, profile="art"):
    """ამ პროფილის დაკლებული ზომების დამატება, არსებულის შენარჩუნებით.

    `generate_variants` ყველაფერს შლის და თავიდან ქმნის — ეს კი მხოლოდ
    აკლიას ავსებს, ამიტომ ერთი ფაილი რამდენიმე როლზე უპრობლემოდ იყენებ.
    """
    have = {(v.name, v.fmt) for v in asset.variants}
    storage = get_storage()
    if data is None:
        data = storage.read(asset.storage_key)

    added = 0
    for item in images.derive(data, profile, has_alpha=asset.has_alpha):
        if (item["name"], item["fmt"]) in have:
            continue
        key = _variant_key(asset.sha256, item["name"], item["fmt"])
        mime = {"webp": "image/webp", "jpg": "image/jpeg", "png": "image/png",
                "ico": "image/x-icon"}.get(item["fmt"], "application/octet-stream")
        storage.save(key, item["data"], mime=mime)
        db.session.add(MediaVariant(
            asset_id=asset.id, name=item["name"], fmt=item["fmt"], storage_key=key,
            width=item["width"], height=item["height"], bytes=len(item["data"]),
        ))
        added += 1
    if added:
        db.session.commit()
    return added


def store_upload(file_storage, profile="art", admin_id=None, alt=None):
    """Flask-ის ატვირთული ფაილიდან MediaAsset."""
    if file_storage is None or not file_storage.filename:
        raise MediaError("ფაილი არ აირჩა.")
    data = file_storage.read()
    return store_bytes(
        data, filename=file_storage.filename, profile=profile,
        admin_id=admin_id, source="upload", alt=alt,
    )


# ---------------------------------------------------------------- მიბმა

def bind(subject_type, subject_id, role, asset, position=0):
    """როლზე სურათის მიბმა (არსებული ჩანაცვლდება).

    asset.id ჯერ ვკითხულობთ და მერე ვეხებით სესიას: commit-ის შემდეგ ობიექტი
    expired-ია, მისი წაკითხვა refresh-ს იწვევს, refresh კი autoflush-ს — და
    ჯერ შეუვსებელი MediaLink ნაადრევად ჩაიწერებოდა.
    """
    asset_id = asset.id
    link = MediaLink.query.filter_by(
        subject_type=subject_type, subject_id=subject_id or 0,
        role=role, position=position,
    ).first()
    if link is None:
        link = MediaLink(
            subject_type=subject_type, subject_id=subject_id or 0,
            role=role, position=position, asset_id=asset_id,
        )
        db.session.add(link)
    else:
        link.asset_id = asset_id
    db.session.commit()
    return link


def unbind(subject_type, subject_id, role, position=None):
    """როლიდან სურათის მოხსნა. თვითონ ფაილი რჩება ბიბლიოთეკაში."""
    q = MediaLink.query.filter_by(
        subject_type=subject_type, subject_id=subject_id or 0, role=role,
    )
    if position is not None:
        q = q.filter_by(position=position)
    removed = 0
    for link in q.all():
        db.session.delete(link)
        removed += 1
    db.session.commit()
    return removed


def site_assets():
    """ყველა გლობალური სურათი ერთი მოთხოვნით: {role: MediaAsset}."""
    rows = (
        db.session.query(MediaLink, MediaAsset)
        .join(MediaAsset, MediaAsset.id == MediaLink.asset_id)
        .filter(MediaLink.subject_type == SITE, MediaAsset.is_deleted.is_(False))
        .all()
    )
    return {link.role: asset for link, asset in rows}


def usage(asset):
    """სად გამოიყენება ეს ფაილი."""
    return MediaLink.query.filter_by(asset_id=asset.id).all()


# -------------------------------------------------- ფილმის/სერიალის სურათები

# რომელი მოდელი რომელ subject_type-ს შეესაბამება
SUBJECT_BY_CLASS = {
    "Movie": "movie", "Series": "series", "Person": "person",
    "MenuItem": "menu_item", "HomeRow": "home_row", "Genre": "genre",
}


def subject_of(rec):
    """მოდელის ობიექტი → (subject_type, id)."""
    return SUBJECT_BY_CLASS.get(rec.__class__.__name__, "movie"), rec.id


def _art_cache():
    """მოთხოვნის ფარგლებში ქეში, რომ ერთი და იგივე ფილმი ორჯერ არ მოვიკითხოთ."""
    try:
        from flask import g, has_request_context
        if not has_request_context():
            return None
        cache = getattr(g, "_art_cache", None)
        if cache is None:
            cache = {}
            g._art_cache = cache
        return cache
    except Exception:  # noqa: BLE001
        return None


def _load_links(subject_type, ids):
    # ვარიანტებიც იმავე გავლით იტვირთება: მათ გარეშე თითო სურათზე თითო
    # დამატებითი მოთხოვნა ხდებოდა და 18-ბარათიანი რიგი 18-ჯერ ურტყამდა ბაზას
    from sqlalchemy.orm import selectinload

    rows = (
        db.session.query(MediaLink, MediaAsset)
        .join(MediaAsset, MediaAsset.id == MediaLink.asset_id)
        .options(selectinload(MediaAsset.variants))
        .filter(
            MediaLink.subject_type == subject_type,
            MediaLink.subject_id.in_(list(ids)),
            MediaAsset.is_deleted.is_(False),
        ).all()
    )
    out = {int(i): {} for i in ids}
    for link, asset in rows:
        out[link.subject_id][link.role] = asset
    return out


def prefetch_art(records):
    """სიაში მყოფი ყველა ფილმის სურათი ერთი-ორი მოთხოვნით ჩაიტვირთოს.

    ამის გარეშე მთავარი გვერდი თითო ბარათზე თითო მოთხოვნას გააკეთებდა.
    """
    cache = _art_cache()
    if cache is None or not records:
        return
    wanted = {}
    for rec in records:
        subject_type, rec_id = subject_of(rec)
        if (subject_type, rec_id) not in cache:
            wanted.setdefault(subject_type, set()).add(rec_id)
    for subject_type, ids in wanted.items():
        for rec_id, roles in _load_links(subject_type, ids).items():
            cache[(subject_type, rec_id)] = roles


def art_for(subject_type, subject_id):
    """{role: MediaAsset} კონკრეტული ფილმისთვის."""
    cache = _art_cache()
    key = (subject_type, int(subject_id))
    if cache is not None and key in cache:
        return cache[key]
    roles = _load_links(subject_type, [int(subject_id)]).get(int(subject_id), {})
    if cache is not None:
        cache[key] = roles
    return roles


def art_asset(rec, role):
    subject_type, rec_id = subject_of(rec)
    return art_for(subject_type, rec_id).get(role)


def art_url(rec, role, size=None):
    """ბექოფისიდან დაყენებული სურათის მისამართი, ან None."""
    asset = art_asset(rec, role)
    if asset is None:
        return None
    return asset_url(asset, name=size, profile=ROLE_PROFILE.get(role, "art"))


def invalidate_art(rec=None):
    """ქეშის გასუფთავება (ბექოფისში ცვლილების შემდეგ)."""
    cache = _art_cache()
    if cache is None:
        return
    if rec is None:
        cache.clear()
    else:
        cache.pop(subject_of(rec), None)


def delete_asset(asset, hard=False):
    """წაშლა. ნაგულისხმევად რბილი: ბმულები ეხსნება, ფაილი რჩება აღსადგენად."""
    for link in usage(asset):
        db.session.delete(link)
    if hard:
        storage = get_storage()
        for variant in list(asset.variants):
            storage.delete(variant.storage_key)
        storage.delete(asset.storage_key)
        db.session.delete(asset)
    else:
        asset.is_deleted = True
        asset.deleted_at = datetime.now(timezone.utc)
    db.session.commit()


# ---------------------------------------------------------------- მისამართები

def _parse_size(name):
    """'w640' → ('w', 640). სხვა სახელებზე (ico, orig) აბრუნებს (None, 0)."""
    if not name or len(name) < 2 or name[0] not in "whi" or not name[1:].isdigit():
        return None, 0
    return name[0], int(name[1:])


def best_variant(asset, name, fmt=None):
    """მოთხოვნილი ზომა, ან მასზე ახლოს მდგომი არსებული.

    ორიგინალზე დიდი ზომა არასდროს გენერირდება, ამიტომ 800px-იან სურათს
    w1280 არ ექნება. ასეთ დროს ორიგინალის ნაცვლად (რომელიც PNG-ია და მძიმე)
    ყველაზე დიდ არსებულ ვარიანტს ვაბრუნებთ.
    """
    exact = asset.variant(name, fmt)
    if exact is not None:
        return exact
    kind, target = _parse_size(name)
    if kind is None:
        return None
    candidates = []
    for variant in asset.variants:
        v_kind, v_size = _parse_size(variant.name)
        if v_kind != kind or (fmt and variant.fmt != fmt):
            continue
        # თანაბარ ზომაზე webp ჯობნის (უფრო მსუბუქია)
        candidates.append((v_size, 0 if variant.fmt == "webp" else 1, variant))
    if not candidates:
        return None
    below = [c for c in candidates if c[0] <= target]
    pool = below or candidates
    best = min(
        (c for c in pool if c[0] == max(x[0] for x in pool)), key=lambda c: c[1]
    )
    return best[2]


def asset_url(asset, name=None, fmt=None, profile=None):
    """სურათის საჯარო მისამართი.

    name=None → პროფილის ნაგულისხმევი ზომა, ხოლო თუ ის არ არსებობს, ორიგინალი.
    """
    if asset is None:
        return None
    variant = None
    if name:
        variant = best_variant(asset, name, fmt)
    elif profile:
        for candidate in DEFAULT_PREFERENCE.get(profile, []):
            variant = asset.variant(candidate, fmt)
            if variant is not None:
                break
        if variant is None:
            variant = best_variant(asset, "w9999", fmt)

    storage = get_storage()
    if variant is not None:
        public = storage.public_url(variant.storage_key)
        if public:
            return public
        return "/m/%d/%s-%s.%s" % (asset.id, variant.name, asset.sha8, variant.fmt)

    public = storage.public_url(asset.storage_key)
    if public:
        return public
    return "/m/%d/orig-%s.%s" % (asset.id, asset.sha8, asset.ext)


def srcset(asset, fmt="webp", widths=(320, 640, 1280)):
    """srcset სტრიქონი. აბრუნებს ცარიელს, თუ ვარიანტები არ არსებობს."""
    if asset is None:
        return ""
    parts = []
    for width in widths:
        variant = asset.variant("w%d" % width, fmt)
        if variant is not None:
            parts.append("%s %dw" % (asset_url(asset, variant.name, variant.fmt), variant.width))
    return ", ".join(parts)


# ---------------------------------------------------------------- ბრენდინგი

THEME_PLACEHOLDER = "/static/theme/web/img/poster.svg"


def brand_bundle(site_name="Movie World"):
    """შაბლონისთვის მზა ბრენდინგის ნაკრები.

    ლოგოს არარსებობა შეცდომა არ არის: ამ დროს header-ში საიტის სახელი ჩანს ტექსტად.
    """
    assets = site_assets()

    def pack(role, profile, name=None):
        asset = assets.get(role)
        if asset is None:
            return None
        variant = asset.variant(name) if name else None
        return {
            "url": asset_url(asset, name=name, profile=profile),
            "width": variant.width if variant else asset.width,
            "height": variant.height if variant else asset.height,
            "alt": asset.alt_text or site_name,
            "id": asset.id,
        }

    favicon = assets.get("favicon")
    placeholder = assets.get("placeholder_poster")
    person_ph = assets.get("placeholder_person")

    return {
        "site_name": site_name,
        "logo": pack("logo_light", "logo", "h128"),
        "logo_dark": pack("logo_dark", "logo", "h128"),
        "logo_mobile": pack("logo_mobile", "logo", "h64"),
        "og_default": pack("og_default", "banner"),
        "page_background": pack("page_background", "art", "w1920"),
        "popup_ad": pack("popup_ad", "banner"),
        "favicon": {
            "ico": asset_url(favicon, name="ico") if favicon else None,
            "png32": asset_url(favicon, name="i32") if favicon else None,
            "png192": asset_url(favicon, name="i192") if favicon else None,
            "apple": asset_url(favicon, name="i180") if favicon else None,
            "version": favicon.sha8 if favicon else None,
        } if favicon else None,
        "placeholder_poster": (
            asset_url(placeholder, profile="art") if placeholder else THEME_PLACEHOLDER
        ),
        "placeholder_person": (
            asset_url(person_ph, profile="art") if person_ph else THEME_PLACEHOLDER
        ),
    }
