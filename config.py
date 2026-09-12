"""აპლიკაციის კონფიგურაცია — იკითხება .env ფაილიდან."""
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

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
    MEDIA_ROOT = os.environ.get("MEDIA_ROOT", os.path.join(BASE_DIR, "media"))
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
