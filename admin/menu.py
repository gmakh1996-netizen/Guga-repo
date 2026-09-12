"""გვერდითი მენიუს მართვა."""
import menu_items as menu_defaults
from flask import flash, redirect, render_template, request, url_for

from medialib import service
from models import MenuItem, db

from . import admin_bp
from .auth import log_action


def _back():
    return redirect(url_for("admin.menu_list"))


def _apply(item):
    item.label = (request.form.get("label") or "").strip()[:60] or "უსახელო"
    item.url = (request.form.get("url") or "/").strip()[:300] or "/"
    icon = (request.form.get("icon") or "movies").strip()
    item.icon = icon if icon in menu_defaults.ICONS else "movies"
    item.match = (request.form.get("match") or "").strip()[:60] or None
    item.is_active = bool(request.form.get("is_active"))
    item.visible_desktop = bool(request.form.get("visible_desktop"))
    item.visible_mobile = bool(request.form.get("visible_mobile"))
    item.new_tab = bool(request.form.get("new_tab"))
    return item


@admin_bp.route("/menu")
def menu_list():
    items = MenuItem.query.order_by(MenuItem.position, MenuItem.id).all()
    service.prefetch_art(items)
    rows = []
    for item in items:
        rows.append({
            "item": item,
            "icon_asset": service.art_asset(item, "icon"),
            "icon_url": service.art_url(item, "icon", "h64"),
        })
    spec = service.ROLE_MAP.get("icon", {})
    return render_template(
        "admin/menu.html", rows=rows, icons=menu_defaults.ICONS,
        icon_size=spec.get("size", ""), icon_size_note=spec.get("size_note", ""),
    )


@admin_bp.route("/menu/seed", methods=["POST"])
def menu_seed():
    replace = bool(request.form.get("replace"))
    added = menu_defaults.seed(replace=replace)
    log_action("menu.seed", detail="replace=%s added=%d" % (replace, added))
    flash("ჩაიწერა %d პუნქტი." % added if added
          else "მენიუ უკვე არსებობს. ჩასანაცვლებლად მონიშნეთ წაშლა.", "ok" if added else "error")
    return _back()


@admin_bp.route("/menu/new", methods=["POST"])
def menu_new():
    last = MenuItem.query.order_by(MenuItem.position.desc()).first()
    item = MenuItem(position=(last.position + 1) if last else 0)
    _apply(item)
    db.session.add(item)
    db.session.commit()
    log_action("menu.new", "menu_item", item.id, detail=item.label)
    flash("პუნქტი დაემატა.", "ok")
    return _back()


@admin_bp.route("/menu/<int:item_id>/save", methods=["POST"])
def menu_save(item_id):
    item = db.session.get(MenuItem, item_id)
    if item is None:
        flash("პუნქტი ვერ მოიძებნა.", "error")
        return _back()
    _apply(item)
    db.session.commit()
    log_action("menu.save", "menu_item", item_id, detail=item.label)
    flash("შენახულია.", "ok")
    return _back()


@admin_bp.route("/menu/<int:item_id>/delete", methods=["POST"])
def menu_delete(item_id):
    item = db.session.get(MenuItem, item_id)
    if item is None:
        flash("პუნქტი ვერ მოიძებნა.", "error")
        return _back()
    label = item.label
    service.unbind("menu_item", item_id, "icon")
    db.session.delete(item)
    db.session.commit()
    log_action("menu.delete", "menu_item", item_id, detail=label)
    flash("„%s“ წაიშალა." % label, "ok")
    return _back()


@admin_bp.route("/menu/<int:item_id>/move", methods=["POST"])
def menu_move(item_id):
    ordered = MenuItem.query.order_by(MenuItem.position, MenuItem.id).all()
    index = next((i for i, r in enumerate(ordered) if r.id == item_id), None)
    if index is None:
        flash("პუნქტი ვერ მოიძებნა.", "error")
        return _back()
    step = -1 if request.form.get("dir") == "up" else 1
    target = index + step
    if 0 <= target < len(ordered):
        ordered[index], ordered[target] = ordered[target], ordered[index]
    for position, item in enumerate(ordered):
        item.position = position
    db.session.commit()
    log_action("menu.move", "menu_item", item_id, detail=request.form.get("dir"))
    return _back()
