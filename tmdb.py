"""TMDB API კლიენტი.

ერთადერთი გარე წყარო. იძლევა მხოლოდ მეტამონაცემებს (ინფო, პოსტერი),
არასდროს — თავად ვიდეოს. ეს არის ლეგალური ნაწილი.
დოკუმენტაცია: https://developer.themoviedb.org/reference/intro/getting-started
"""
import requests
from config import Config

BASE_URL = "https://api.themoviedb.org/3"


class TMDBError(Exception):
    pass


def _get(path, **params):
    """საბაზისო GET მოთხოვნა TMDB-ზე."""
    if not Config.TMDB_API_KEY:
        raise TMDBError("TMDB_API_KEY არ არის მითითებული .env ფაილში.")

    params.setdefault("api_key", Config.TMDB_API_KEY)
    params.setdefault("language", Config.TMDB_LANGUAGE)

    resp = requests.get(f"{BASE_URL}{path}", params=params, timeout=15)
    if resp.status_code != 200:
        raise TMDBError(f"TMDB {resp.status_code}: {resp.text[:200]}")
    return resp.json()


# ---- სიები (მთავარი გვერდისთვის და sync-ისთვის) ----

def popular(page=1):
    return _get("/movie/popular", page=page).get("results", [])


def now_playing(page=1):
    return _get("/movie/now_playing", page=page).get("results", [])


def top_rated(page=1):
    return _get("/movie/top_rated", page=page).get("results", [])


def upcoming(page=1):
    return _get("/movie/upcoming", page=page).get("results", [])


def trending(window="week"):
    # trending არ იღებ language-ს ისე მკაცრად; window: "day" | "week"
    return _get(f"/trending/movie/{window}").get("results", [])


def by_genre(genre_id, page=1):
    return _get(
        "/discover/movie",
        with_genres=genre_id,
        sort_by="popularity.desc",
        page=page,
    ).get("results", [])


def discover_movie(page=1, **params):
    """მოქნილი discover — უახლესი რელიზებისთვის (primary_release_year, sort_by).

    მაგ: discover_movie(primary_release_year=2026, sort_by="release_date.desc").
    """
    params.setdefault("include_adult", "false")
    return _get("/discover/movie", page=page, **params).get("results", [])


def search(query, page=1):
    if not query.strip():
        return []
    return _get("/search/movie", query=query, page=page, include_adult="false").get(
        "results", []
    )


def genre_list():
    return _get("/genre/movie/list").get("genres", [])


# ---- სერიალები (TV) ----

def tv_popular(page=1):
    return _get("/tv/popular", page=page).get("results", [])


def tv_top_rated(page=1):
    return _get("/tv/top_rated", page=page).get("results", [])


def tv_on_the_air(page=1):
    return _get("/tv/on_the_air", page=page).get("results", [])


def tv_trending(window="week"):
    return _get(f"/trending/tv/{window}").get("results", [])


def tv_by_genre(genre_id, page=1):
    return _get(
        "/discover/tv",
        with_genres=genre_id,
        sort_by="popularity.desc",
        page=page,
    ).get("results", [])


def tv_search(query, page=1):
    if not query.strip():
        return []
    return _get("/search/tv", query=query, page=page, include_adult="false").get(
        "results", []
    )


def tv_genre_list():
    return _get("/genre/tv/list").get("genres", [])


def tv_details(tv_id):
    data = _get(
        f"/tv/{tv_id}",
        append_to_response="credits,videos,similar,watch/providers",
    )
    if not data.get("overview"):
        try:
            en = _get(f"/tv/{tv_id}", language="en-US")
            data["overview"] = en.get("overview", "")
        except TMDBError:
            pass
    return data


def tv_watch_providers(tv_id, region=None):
    region = region or Config.TMDB_REGION
    data = _get(f"/tv/{tv_id}/watch/providers")
    return data.get("results", {}).get(region, {})


# ---- ერთი ფილმის სრული დეტალები ----

def movie_details(movie_id):
    """სრული დეტალები: credits, videos, similar, watch/providers ერთ მოთხოვნაში."""
    data = _get(
        f"/movie/{movie_id}",
        append_to_response="credits,videos,similar,watch/providers",
    )

    # თუ ქართული overview ცარიელია — გადმოვიღოთ ინგლისური, რომ გვერდი არ დარჩეს ცარიელი
    if not data.get("overview"):
        try:
            en = _get(f"/movie/{movie_id}", language="en-US")
            data["overview"] = en.get("overview", "")
            if not data.get("title"):
                data["title"] = en.get("title", "")
        except TMDBError:
            pass

    return data


def watch_providers(movie_id, region=None):
    """'სად ვნახო ლეგალურად' — JustWatch-ის მონაცემები რეგიონის მიხედვით."""
    region = region or Config.TMDB_REGION
    data = _get(f"/movie/{movie_id}/watch/providers")
    return data.get("results", {}).get(region, {})


# ---- დამხმარე ----

def pick_trailer(videos):
    """YouTube-ის ტრეილერის key-ს ამორჩევა videos ბლოკიდან."""
    results = (videos or {}).get("results", [])
    # ჯერ ოფიციალური Trailer, მერე ნებისმიერი YouTube ვიდეო
    for v in results:
        if v.get("site") == "YouTube" and v.get("type") == "Trailer":
            return v.get("key")
    for v in results:
        if v.get("site") == "YouTube":
            return v.get("key")
    return None
