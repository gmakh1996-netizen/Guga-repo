"""მსახიობების მართვა: ფოტო, სახელი, პოპულარობა.

ბაზაში 1 000 მსახიობია და მხოლოდ 210-ს აქვს ფოტო. აქედან შეგიძლიათ
დანარჩენებს ხელით დაუყენოთ, ან გარე მისამართიდან ჩამოტანოთ.
"""
from flask import flash, redirect, render_template, request, url_for

from medialib import service
from models import Person, db

from . import admin_bp
from .auth import log_action

PER_PAGE = 36


@admin_bp.route("/persons")
def persons_list():
    q = (request.args.get("q") or "").strip()
    only = request.args.get("only") or ""
    page = max(request.args.get("page", 1, type=int), 1)

    query = Person.query
    if q:
        query = query.filter(db.or_(
            Person.name.ilike("%%%s%%" % q),
            Person.name_en.ilike("%%%s%%" % q),
        ))
    if only == "missing":
        query = query.filter(db.or_(Person.photo.is_(None), Person.photo == ""))
    elif only == "custom":
        from models import MediaLink
        owned = db.session.query(MediaLink.subject_id).filter(
            MediaLink.subject_type == "person"
        )
        query = query.filter(Person.id.in_(owned))

    total = query.count()
    people = (query.order_by(Person.popularity.desc(), Person.id.asc())
              .offset((page - 1) * PER_PAGE).limit(PER_PAGE).all())
    service.prefetch_art(people)

    rows = []
    for person in people:
        asset = service.art_asset(person, "photo")
        cms_url = service.art_url(person, "photo", "w300")
        rows.append({
            "person": person,
            "asset": asset,
            "cms_url": cms_url,                      # მხოლოდ ბექოფისიდან დაყენებული
            "url": cms_url or person.photo or None,  # რაც საიტზე ნამდვილად ჩანს
            "is_custom": asset is not None,
        })

    spec = service.ROLE_MAP.get("photo", {})
    return render_template(
        "admin/persons.html", rows=rows, total=total, page=page,
        has_more=page * PER_PAGE < total, q=q, only=only,
        photo_size=spec.get("size", ""), photo_size_note=spec.get("size_note", ""),
    )


@admin_bp.route("/persons/<int:person_id>/save", methods=["POST"])
def persons_save(person_id):
    person = db.session.get(Person, person_id)
    if person is None:
        flash("მსახიობი ვერ მოიძებნა.", "error")
        return redirect(url_for("admin.persons_list"))

    name = (request.form.get("name") or "").strip()
    if name:
        person.name = name[:200]
    person.name_en = (request.form.get("name_en") or "").strip()[:200] or None
    db.session.commit()
    log_action("persons.save", "person", person_id, detail=person.name)
    flash("შენახულია.", "ok")
    target = request.form.get("next") or url_for("admin.persons_list")
    return redirect(target if target.startswith("/admin") else url_for("admin.persons_list"))
