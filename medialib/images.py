"""სურათის შემოწმება და წარმოებული ზომების გენერაცია (Pillow).

მთავარი წესები:
  * ვამოწმებთ ნამდვილ შიგთავსს, არა ფაილის გაფართოებას;
  * არასდროს ვადიდებთ სურათს (ორიგინალზე დიდი ზომა არ იქმნება);
  * გამჭვირვალობის შემთხვევაში სათადარიგო ფორმატი PNG-ია, არა JPEG;
  * SVG ნაგულისხმევად არ მიიღება (იგივე დომენიდან გაცემული SVG სკრიპტის გაშვების საშუალებაა).
"""
import io

from PIL import Image, ImageOps, features

MAX_PIXELS = 12000          # ერთ გვერდზე მაქსიმალური პიქსელი
MIN_PIXELS = 8

# ნებადართული ნამდვილი ფორმატები (Pillow-ის სახელები) → (mime, ext)
ALLOWED = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
    "GIF": ("image/gif", "gif"),
}

# პროფილი = რა ზომები გამოვიმუშაოთ ამ დანიშნულების სურათისთვის
PROFILES = {
    # ფილმის ბარათი/ჰერო/დეტალურის ფონი
    "art": {"widths": [320, 640, 1280, 1920]},
    # ვერტიკალური პოსტერი
    "portrait": {"widths": [300, 600]},
    # ლოგო: სიმაღლით ვზომავთ, გამჭვირვალობა უნდა შენარჩუნდეს
    "logo": {"heights": [64, 128, 256], "keep_alpha": True},
    # favicon: კვადრატული ნაკრები + .ico
    "icon": {"squares": [16, 32, 48, 64, 180, 192, 512], "ico": [16, 32, 48],
             "keep_alpha": True},
    # ბანერი, კოლექციის გარეკანი და მისთანები
    "banner": {"widths": [640, 1400]},
    # მხოლოდ ორიგინალი (placeholder-ები, SVG-ის მაგივრობის სურათები)
    "raw": {},
}


class MediaError(Exception):
    """მომხმარებელს ჩვენებადი შეცდომა (ქართულად)."""


def webp_supported():
    try:
        return features.check("webp")
    except Exception:  # noqa: BLE001
        return False


def probe(data):
    """ფაილის ნამდვილი ტიპი და ზომები. აბრუნებს dict-ს ან აგდებს MediaError-ს."""
    if not data:
        raise MediaError("ფაილი ცარიელია.")
    try:
        with Image.open(io.BytesIO(data)) as probe_img:
            probe_img.verify()  # verify-ის შემდეგ ობიექტი აღარ გამოდგება
        img = Image.open(io.BytesIO(data))
    except MediaError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise MediaError("ფაილი სურათი არ არის ან დაზიანებულია.") from exc

    fmt = (img.format or "").upper()
    if fmt not in ALLOWED:
        raise MediaError(
            "დაუშვებელი ფორმატი: %s. ნებადართულია JPEG, PNG, WebP და GIF." % (fmt or "უცნობი")
        )

    w, h = img.size
    if w < MIN_PIXELS or h < MIN_PIXELS:
        raise MediaError("სურათი ძალიან პატარაა (%d×%d)." % (w, h))
    if w > MAX_PIXELS or h > MAX_PIXELS:
        raise MediaError(
            "სურათი ძალიან დიდია (%d×%d). მაქსიმუმი %d პიქსელია გვერდზე." % (w, h, MAX_PIXELS)
        )

    mime, ext = ALLOWED[fmt]
    has_alpha = img.mode in ("RGBA", "LA") or (
        img.mode == "P" and "transparency" in img.info
    )
    return {
        "mime": mime, "ext": ext, "format": fmt,
        "width": w, "height": h, "has_alpha": has_alpha,
    }


def _load(data):
    """პირველი კადრი, სწორად შემობრუნებული (EXIF orientation)."""
    img = Image.open(io.BytesIO(data))
    try:
        img.seek(0)
    except (EOFError, ValueError):
        pass
    img = ImageOps.exif_transpose(img) or img
    return img


def _encode(img, fmt, keep_alpha):
    """სურათი ბაიტებად. აბრუნებს (bytes, ext)."""
    buf = io.BytesIO()
    if fmt == "webp":
        src = img if keep_alpha else img.convert("RGB")
        src.save(buf, format="WEBP", quality=82, method=4)
        return buf.getvalue(), "webp"
    if fmt == "png":
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), "png"
    # jpg
    src = img.convert("RGB")
    src.save(buf, format="JPEG", quality=85, optimize=True, progressive=True)
    return buf.getvalue(), "jpg"


def _fallback_fmt(has_alpha):
    return "png" if has_alpha else "jpg"


def _square_canvas(img, size, keep_alpha):
    """კვადრატში ჩასმა მოჭრის გარეშე (ლოგო არ უნდა მოიჭრას)."""
    fitted = ImageOps.contain(img, (size, size), Image.LANCZOS)
    mode = "RGBA" if keep_alpha else "RGB"
    bg = (0, 0, 0, 0) if keep_alpha else (255, 255, 255)
    canvas = Image.new(mode, (size, size), bg)
    src = fitted.convert("RGBA") if keep_alpha else fitted.convert("RGB")
    offset = ((size - fitted.width) // 2, (size - fitted.height) // 2)
    if keep_alpha:
        canvas.paste(src, offset, src)
    else:
        canvas.paste(src, offset)
    return canvas


def derive(data, profile_name, has_alpha=False):
    """წარმოებული ზომების გენერაცია.

    აბრუნებს სიას: [{name, fmt, data, width, height}, ...].
    ორიგინალზე დიდი ზომა არასდროს იქმნება.
    """
    profile = PROFILES.get(profile_name)
    if profile is None:
        raise MediaError("უცნობი პროფილი: %s" % profile_name)
    if not profile:  # "raw" — მხოლოდ ორიგინალი
        return []

    keep_alpha = bool(profile.get("keep_alpha") and has_alpha)
    formats = ["webp"] if webp_supported() else []
    formats.append(_fallback_fmt(keep_alpha))

    img = _load(data)
    out = []

    for width in profile.get("widths", []):
        if width > img.width:
            continue
        resized = ImageOps.contain(img, (width, 10 * width), Image.LANCZOS)
        for fmt in formats:
            blob, ext = _encode(resized, fmt, keep_alpha)
            out.append({"name": "w%d" % width, "fmt": ext, "data": blob,
                        "width": resized.width, "height": resized.height})

    for height in profile.get("heights", []):
        if height > img.height:
            continue
        resized = ImageOps.contain(img, (10 * height, height), Image.LANCZOS)
        for fmt in formats:
            blob, ext = _encode(resized, fmt, keep_alpha)
            out.append({"name": "h%d" % height, "fmt": ext, "data": blob,
                        "width": resized.width, "height": resized.height})

    for size in profile.get("squares", []):
        if size > max(img.width, img.height):
            continue
        canvas = _square_canvas(img, size, keep_alpha)
        blob, ext = _encode(canvas, "png", keep_alpha)
        out.append({"name": "i%d" % size, "fmt": ext, "data": blob,
                    "width": size, "height": size})

    ico_sizes = [s for s in profile.get("ico", []) if s <= max(img.width, img.height)]
    if ico_sizes:
        base = _square_canvas(img, max(ico_sizes), True)
        buf = io.BytesIO()
        base.save(buf, format="ICO", sizes=[(s, s) for s in ico_sizes])
        out.append({"name": "ico", "fmt": "ico", "data": buf.getvalue(),
                    "width": max(ico_sizes), "height": max(ico_sizes)})

    return out
