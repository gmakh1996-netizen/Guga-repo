"""გვერდითი მენიუს ნაგულისხმევი პუნქტები (ის, რაც _navbar.html-ში იყო ჩაწერილი)."""

from models import MenuItem, db

ICONS = ['home', 'movies', 'series', 'anime', 'animation', 'trailers', 'watchlist']

# (label, url, icon, match, desktop, mobile)
DEFAULTS = [
    ('მთავარი', '/', 'home', 'path:/', True, False),
    ('ფილმები', '/browse?type=movie', 'movies', 'media:movie', True, True),
    ('სერიალები', '/browse?type=serial', 'series', 'media:tv', True, True),
    ('ანიმეები', '/browse?type=anime', 'anime', 'media:anime', True, True),
    ('ანიმაციები', '/browse?type=animation', 'animation', 'media:animation', True, True),
    ('თრეილერები', '/browse?type=trailer', 'trailers', 'media:trailer', True, False),
    ('სანახავი', '/watchlist', 'watchlist', 'path:/watchlist', True, True),
]


def seed(replace=False):
    """ნაგულისხმევი მენიუს ჩაწერა. აბრუნებს დამატებულთა რაოდენობას."""
    if replace:
        MenuItem.query.delete()
        db.session.commit()
    elif MenuItem.query.count():
        return 0

    for position, row in enumerate(DEFAULTS):
        label, url, icon, match, desktop, mobile = row
        db.session.add(MenuItem(
            label=label, url=url, icon=icon, match=match, position=position,
            visible_desktop=desktop, visible_mobile=mobile, is_active=True,
        ))
    db.session.commit()
    return len(DEFAULTS)
