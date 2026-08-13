"""აპლიკაციის კონფიგურაცია — იკითხება .env ფაილიდან."""
import os
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

    # სურათების საბაზისო URL-ები (TMDB CDN)
    IMG_BASE = "https://image.tmdb.org/t/p"
    POSTER_SIZE = "w500"
    BACKDROP_SIZE = "w1280"
    PROFILE_SIZE = "w185"
