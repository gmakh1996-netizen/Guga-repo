"""ბექოფისის ავტორიზაცია: სესია, CSRF, როლები, აუდიტი.

მნიშვნელოვანი: ატვირთვის endpoint-ები ამ ფენის გარეშე არასდროს უნდა გაიხსნას.
"""
import hmac
import secrets
import time
from collections import defaultdict
from datetime import datetime, timezone
from functools import wraps

from flask import (
    abort, flash, g, redirect, render_template, request, session, url_for,
)

from models import db, AdminUser, AuditLog
from . import admin_bp

SESSION_KEY = "admin_id"
CSRF_KEY = "_csrf"

# შესვლის მცდელობების შეზღუდვა (პროცესის მეხსიერებაში).
# შენიშვნა: gunicorn-ის თითო მუშას საკუთარი ასლი აქვს, ანუ რეალური ლიმიტი
# მუშების რაოდენობაზე მრავლდება. სერიოზული დაცვისთვის საჭიროა ბაზა ან Redis.
LOGIN_WINDOW = 15 * 60
LOGIN_MAX = 5
_attempts = defaultdict(list)


def _client_ip():
    fwd = request.headers.get("X-Forwarded-For", "")
    return (fwd.split(",")[0].strip() if fwd else request.remote_addr) or "?"


def _rate_limited(ip):
    now = time.time()
    hits = [t for t in _attempts[ip] if now - t < LOGIN_WINDOW]
    _attempts[ip] = hits
    return len(hits) >= LOGIN_MAX


def _record_attempt(ip):
    _attempts[ip].append(time.time())


def csrf_token():
    token = session.get(CSRF_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_KEY] = token
    return token


def check_csrf():
    sent = request.form.get("_csrf") or request.headers.get("X-CSRF-Token") or ""
    expected = session.get(CSRF_KEY) or ""
    if not expected or not hmac.compare_digest(str(sent), str(expected)):
        abort(400, "CSRF ტოკენი არასწორია. გადატვირთეთ გვერდი და სცადეთ ხელახლა.")


def current_admin():
    if getattr(g, "_admin_loaded", False):
        return g._admin
    admin_id = session.get(SESSION_KEY)
    admin = db.session.get(AdminUser, admin_id) if admin_id else None
    if admin is not None and not admin.is_active:
        admin = None
    g._admin = admin
    g._admin_loaded = True
    return admin


def role_required(*roles):
    """კონკრეტული როლის მოთხოვნა (owner ყოველთვის გადის)."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            admin = current_admin()
            if admin is None:
                return redirect(url_for("admin.login", next=request.path))
            if roles and admin.role not in roles and not admin.is_owner:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def log_action(action, entity_type=None, entity_id=None, detail=None):
    admin = current_admin()
    db.session.add(AuditLog(
        admin_id=admin.id if admin else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        detail=detail,
        ip=_client_ip(),
    ))
    db.session.commit()


@admin_bp.before_request
def _guard():
    """ერთი ადგილი, სადაც ყველა /admin მოთხოვნა მოწმდება."""
    public = {"admin.login"}
    if request.endpoint in public:
        if request.method == "POST":
            check_csrf()
        return None
    if current_admin() is None:
        if request.accept_mimetypes.best == "application/json":
            return {"error": "არაავტორიზებული"}, 401
        return redirect(url_for("admin.login", next=request.full_path))
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        check_csrf()
    return None


@admin_bp.after_request
def _no_index(response):
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


@admin_bp.context_processor
def _inject():
    return {"csrf_token": csrf_token, "admin_user": current_admin()}


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_admin() is not None:
        return redirect(url_for("admin.dashboard"))

    error = None
    if request.method == "POST":
        ip = _client_ip()
        if _rate_limited(ip):
            error = "ძალიან ბევრი მცდელობა. სცადეთ 15 წუთში."
        else:
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            admin = AdminUser.query.filter_by(username=username).first()
            if admin is None or not admin.is_active or not admin.check_password(password):
                _record_attempt(ip)
                error = "მომხმარებელი ან პაროლი არასწორია."
            else:
                session.clear()
                session[SESSION_KEY] = admin.id
                session.permanent = True
                csrf_token()
                admin.last_login_at = datetime.now(timezone.utc)
                db.session.commit()
                g._admin_loaded = False
                log_action("login", "admin_user", admin.id)
                nxt = request.args.get("next") or ""
                if nxt.startswith("/admin"):
                    return redirect(nxt)
                return redirect(url_for("admin.dashboard"))

    return render_template("admin/login.html", error=error, csrf_token=csrf_token)


@admin_bp.route("/logout", methods=["POST"])
def logout():
    log_action("logout")
    session.clear()
    flash("სესია დასრულდა.", "ok")
    return redirect(url_for("admin.login"))
