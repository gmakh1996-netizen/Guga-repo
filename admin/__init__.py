"""ბექოფისი — ცალკე Blueprint იმავე Flask აპში.

/admin-ის ქვეშ ყველაფერი სესიით არის დაცული (იხ. auth.py). საჯარო საიტის
თემა აქ არ გამოიყენება: ადმინს საკუთარი მსუბუქი ლეიაუტი აქვს.
"""
from flask import Blueprint

admin_bp = Blueprint(
    "admin", __name__,
    url_prefix="/admin",
    template_folder="../templates/admin",
)

from . import auth  # noqa: E402,F401  — მარშრუტების რეგისტრაცია
from . import views  # noqa: E402,F401
from . import content  # noqa: E402,F401
from . import home  # noqa: E402,F401
from . import home_items  # noqa: E402,F401
from . import jobs  # noqa: E402,F401
from . import images  # noqa: E402,F401
from . import menu  # noqa: E402,F401
from . import persons  # noqa: E402,F401
