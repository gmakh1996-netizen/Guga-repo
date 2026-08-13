"""ყოველდღიური ავტომ. განახლება — ge.movie-ს ახალი ფილმების ჩამატება.

რას აკეთებს:
  1. პოულობს ყველაზე ახალ scrape-ფაილს (ge_movies*.json) Downloads-ში ან data/-ში.
  2. თუ ეს ფაილი უკვე დამუშავებულია (იგივე mtime) — არაფერს აკეთებს.
  3. აიმპორტებს — import_streams id-ით აკეთებს upsert-ს, ე.ი. მხოლოდ *ახალი*
     ფილმები ემატება, არსებული არ მრავლდება.
  4. ინახავს ფაილს data/movies.json-ად (კანონიკური წყარო) და წერს ლოგს.

გაშვება (Scheduled Task ან ხელით):
    .venv/Scripts/python.exe update.py

ერთადერთი ხელით ნაბიჯი (Cloudflare-ის გამო) — scrape ბრაუზერში:
    scrapers/04_daily.js  (ან bookmarklet) → ge_movies_daily.json Downloads-ში.
"""
import os
import re
import sys
import glob
import json
import shutil
import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from flask import Flask

from config import Config
from models import db
from import_streams import import_file

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")
STATE_FILE = os.path.join(DATA_DIR, ".last_update.json")
LOG_FILE = os.path.join(DATA_DIR, "update.log")

# scrape-ფაილის შესაძლო სახელები (ge_movies.json, "ge_movies (11).json",
# ge_movies_daily.json და ა.შ.) — ორივე საქაღალდეში.
PATTERNS = ("ge_movies*.json", "ge_movies_daily*.json")


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:  # noqa: BLE001
        print("log write failed:", e)


def find_latest_scrape():
    """ყველაზე ახალი (mtime) ge_movies*.json Downloads-სა და data/-ში."""
    candidates = []
    for base in (DOWNLOADS, DATA_DIR):
        for pat in PATTERNS:
            candidates.extend(glob.glob(os.path.join(base, pat)))
    # movies.json-ს (კანონიკურ ფაილს) ავტომ. აღმოჩენაში არ ვითვლით
    candidates = [c for c in candidates if os.path.basename(c) != "movies.json"]
    if not candidates:
        return None
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]


def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:  # noqa: BLE001
        log(f"state write failed: {e}")


def main():
    path = find_latest_scrape()
    if not path:
        log("ახალი scrape-ფაილი ვერ მოიძებნა (Downloads/data). გამოტოვება.")
        return 0

    mtime = os.path.getmtime(path)
    state = load_state()
    if state.get("last_file") == path and state.get("last_mtime") == mtime:
        log(f"უახლესი ფაილი უკვე დამუშავებულია: {os.path.basename(path)}. ახალი არაფერია.")
        return 0

    log(f"ვამუშავებ: {path}")
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    with app.app_context():
        db.create_all()
        result = import_file(path)

    added = (result or {}).get("added", 0)
    log(
        f"✓ დასრულდა — ახალი ფილმი/სერიალი: {added}, "
        f"წყარო: {(result or {}).get('streams', 0)}"
    )

    # ფაილს ვინახავთ data/movies.json-ად (კანონიკური წყარო რესეტისთვის)
    try:
        shutil.copyfile(path, os.path.join(DATA_DIR, "movies.json"))
    except Exception as e:  # noqa: BLE001
        log(f"movies.json copy failed: {e}")

    save_state({"last_file": path, "last_mtime": mtime})
    return 0


if __name__ == "__main__":
    sys.exit(main())
