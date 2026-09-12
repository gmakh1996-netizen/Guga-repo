"""აპლიკაციის კონფიგურაცია — იკითხება .env ფაილიდან."""
import os
import secrets
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _is_production():
    return bool(
        os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("RAILWAY_PROJECT_ID")
        or os.environ.get("RAILWAY_SERVICE_ID")
    )


def _resolve_secret_key(media_root):
    """სესიის გასაღები, რომელიც პროდაქშენში არასდროს არის ცნობილი მნიშვნელობა.

    თუ SECRET_KEY ცვლადი არ არის დაყენებული, ლოკალურად ნაგულისხმევს ვტოვებთ,
    პროდაქშენში კი ვქმნით შემთხვევითს და ვინახავთ ფაილად. ფაილი იმიტომ, რომ
    gunicorn-ის ორივე მუშას ერთი და იგივე გასაღები სჭირდება — თორემ ერთის
    გამოწერილ ქუქის მეორე არ მიიღებდა.

    ცნობილი გასაღები პროდაქშენში ნიშნავს, რომ ნებისმიერს, ვინც repo-ს ხედავს,
    ადმინის სესიის გაყალბება შეუძლია. ამიტომ აქ ავტომატურად ვიცავთ თავს.
    """
    value = os.environ.get("SECRET_KEY", "").strip()
    if value and value not in ("dev-secret-change-me", "change_me_in_production"):
        return value
    if not _is_production():
        return "dev-secret-change-me"

    path = os.path.join(media_root, ".secret_key")
    try:
        if os.path.exists(path):
            with open(path) as f:
                stored = f.read().strip()
            if stored:
                return stored
        os.makedirs(media_root, exist_ok=True)
        generated = secrets.token_urlsafe(48)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(generated)
        return generated
    except FileExistsError:          # მეორე მუშამ გვასწრო
        with open(path) as f:
            return f.read().strip()
    except OSError:                  # ჩაწერა ვერ მოხერხდა
        return secrets.token_urlsafe(48)


_MEDIA_ROOT = os.environ.get("MEDIA_ROOT", os.path.join(BASE_DIR, "media"))


class Config:
    SECRET_KEY = _resolve_secret_key(_MEDIA_ROOT)

    # SQLite ნაგულისხმევად; მარტივად შეიცვლება Postgres-ზე DATABASE_URL-ით
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'gemovie.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # TMDB
    TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
    TMDB_LANGUAGE = os.environ.get("TMDB_LANGUAGE", "ka-GE")
    TMDB_REGION = os.environ.get("TMDB_REGION", "GE")

    # ადმინის დაცული sync — token .env-ში, არასდროს კოდში
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
    # ავტომატური სინქრონიზაციის ინტერვალი (საათებში)
    SYNC_INTERVAL_HOURS = int(os.environ.get("SYNC_INTERVAL_HOURS", "6"))

    # ---- ბექოფისი და მედია ----
    # საცავი: local (საქაღალდე, პროდაქშენში persistent volume) ან r2 (S3-თავსებადი)
    MEDIA_BACKEND = os.environ.get("MEDIA_BACKEND", "local")
    MEDIA_ROOT = _MEDIA_ROOT
    # CDN-ის საჯარო პრეფიქსი (r2-ის რეჟიმში). ცარიელი → ფაილს Flask გასცემს /m/-ზე
    MEDIA_PUBLIC_BASE = os.environ.get("MEDIA_PUBLIC_BASE", "")
    MEDIA_R2_BUCKET = os.environ.get("MEDIA_R2_BUCKET", "")
    MEDIA_R2_ENDPOINT = os.environ.get("MEDIA_R2_ENDPOINT", "")
    MEDIA_R2_ACCESS_KEY = os.environ.get("MEDIA_R2_ACCESS_KEY", "")
    MEDIA_R2_SECRET_KEY = os.environ.get("MEDIA_R2_SECRET_KEY", "")

    # ატვირთვის მაქსიმალური ზომა
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "12")) * 1024 * 1024

    # სესიის ქუქი (ბექოფისი)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = bool(
        os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("FORCE_HTTPS")
    )
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)

    # სურათების საბაზისო URL-ები (TMDB CDN)
    IMG_BASE = "https://image.tmdb.org/t/p"
    POSTER_SIZE = "w500"
    BACKDROP_SIZE = "w1280"
    PROFILE_SIZE = "w185"
