"""მთავარი გვერდის რიგების ნაგულისხმევი წყობა და მისი ბაზაში ჩაწერა.

ეს არის ზუსტად ის 11 რიგი, რომელიც აქამდე `templates/index.html`-ში იყო ჩაწერილი.
ბექოფისის ღილაკი „ნაგულისხმევი წყობის ჩატვირთვა" და CLI კომანდა ერთსა და იმავე
სიას იყენებენ, რომ ორ ადგილას აღარ მეორდებოდეს.
"""
from models import HomeRow, db

ANIME_GENRE = 900000025

# (kind, title, icon, media_type, sort_mode, layout, genre_id, exclude_genre_id)
DEFAULTS = [
    ("continue", "განაგრძე ყურება", "resume", None, None, "landscape", None, None),
    ("movies", "ფილმები ქართულად", "film", "movie", "trending", "landscape", None, ANIME_GENRE),
    ("movies", "ტოპ ფილმები", "top", "movie", "weekly_top", "top9", None, ANIME_GENRE),
    ("movies", "სერიალები ქართულად", "tv", "serial", "recent", "landscape", None, ANIME_GENRE),
    ("movies", "ტოპ სერიალები", "top", "serial", "weekly_top", "top9", None, ANIME_GENRE),
    ("movies", "პრემიერა", "premiere", "movie", "recent", "portrait", None, ANIME_GENRE),
    ("movies", "ახალი დამატებული ფილმები", "newfilm", "movie", "recent", "landscape", None, ANIME_GENRE),
    ("movies", "ახალი დამატებული ეპიზოდები", "newtv", "serial", "recent", "landscape", None, ANIME_GENRE),
    ("movies", "ანიმე სერიალები ქართულად", "sparkles", "serial", "recent", "portrait", ANIME_GENRE, None),
    ("recent_episodes", "ბოლოს დამატებული ეპიზოდები", "newtv", None, None, "landscape", None, None),
    ("movies", "ანიმეები ქართულად", "sparkles", "movie", "recent", "portrait", ANIME_GENRE, None),
]

# ბექოფისის ფორმების არჩევანი
KINDS = [
    ("movies", "ფილმების რიგი"),
    ("continue", "განაგრძე ყურება (ბრაუზერის მეხსიერებიდან)"),
    ("recent_episodes", "ბოლოს დამატებული ეპიზოდები"),
]
MEDIA_TYPES = [
    ("movie", "ფილმები"), ("serial", "სერიალები"), ("anime", "ანიმე"),
    ("animation", "ანიმაცია"), ("trailer", "თრეილერები"),
]
SORTS = [
    ("trending", "ტრენდში"), ("recent", "ახლახან დამატებული"),
    ("newest", "გამოშვების თარიღით"), ("rating", "რეიტინგით"),
    ("weekly_top", "კვირის ტოპი"), ("popularity", "პოპულარობით"),
]
LAYOUTS = [
    ("landscape", "განივი ბარათები"), ("portrait", "ვერტიკალური ბარათები"),
    ("top9", "ტოპ 9 (ნუმერაციით)"),
]
ICONS = ["film", "tv", "top", "newfilm", "newtv", "sparkles", "premiere", "resume"]

VALID_KINDS = {k for k, _ in KINDS}
VALID_MEDIA = {k for k, _ in MEDIA_TYPES}
VALID_SORTS = {k for k, _ in SORTS}
VALID_LAYOUTS = {k for k, _ in LAYOUTS}


def seed(replace=False):
    """ნაგულისხმევი წყობის ჩაწერა. აბრუნებს დამატებული რიგების რაოდენობას."""
    if replace:
        HomeRow.query.delete()
        db.session.commit()
    elif HomeRow.query.count():
        return 0

    for position, row in enumerate(DEFAULTS):
        kind, title, icon, media_type, sort_mode, layout, genre_id, exclude_genre_id = row
        db.session.add(HomeRow(
            kind=kind, title=title, icon=icon,
            media_type=media_type or "movie",
            sort_mode=sort_mode or "popularity",
            layout=layout, genre_id=genre_id, exclude_genre_id=exclude_genre_id,
            item_limit=9 if layout == "top9" else 18,
            position=position, is_active=True,
        ))
    db.session.commit()
    return len(DEFAULTS)
