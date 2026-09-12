"""ბექოფისის და მედიის E2E შემოწმება (pytest არ სჭირდება).

რას ამოწმებს:
  * /admin დაცულია და შესვლაზე გადამისამართებს;
  * არასწორი პაროლი არ გადის, სწორი გადის;
  * CSRF-ის გარეშე POST არ გადის;
  * ლოგოს ატვირთვა ქმნის ვარიანტებს და საჯარო გვერდზე ჩნდება;
  * ლოგოს წაშლის შემდეგ header-ში საიტის სახელი ჩანს ტექსტად (გატეხილი სურათი არა);
  * /m/ მისამართი გასცემს ფაილს სწორი ქეშ-სათაურებით;
  * მედია-ბიბლიოთეკა იხსნება.

ტესტი თავის შემდეგ ალაგებს: დროებით ადმინს და ატვირთულ ფაილს შლის,
ხოლო ლოგოს თავდაპირველ მიბმას აღადგენს.

გაშვება:
    .venv/Scripts/python.exe tests/test_backoffice.py
"""
import datetime
import io
import os
import re
import secrets
import sys
import threading
import time
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from PIL import Image  # noqa: E402

from app import app  # noqa: E402
from medialib import jobs as job_engine  # noqa: E402
from medialib import mirror  # noqa: E402
from medialib import service  # noqa: E402
from models import (  # noqa: E402
    AdminUser, HomeRow, HomeRowItem, Job, MediaAsset, MediaLink, MenuItem,
    Movie, Person, db,
)

FAILED = []
TEST_ROW = "zz-test-row"



def check(name, ok, extra=""):
    print(("  [OK]   " if ok else "  [FAIL] ") + name + ((" — " + str(extra)) if extra else ""))
    if not ok:
        FAILED.append(name)


def make_png(color=(200, 30, 30, 255), size=(420, 420)):
    buf = io.BytesIO()
    Image.new("RGBA", size, color).save(buf, format="PNG")
    return buf.getvalue()


def home_titles(client):
    """მთავარი გვერდის რიგების სათაურები, იმ თანმიმდევრობით, როგორც ირენდერება."""
    html = client.get("/").get_data(as_text=True)
    return re.findall(r'data-title="([^"]+)"', html)


def csrf_of(client):
    with client.session_transaction() as sess:
        token = sess.get("_csrf")
        if not token:
            token = secrets.token_urlsafe(16)
            sess["_csrf"] = token
    return token


def main():
    password = secrets.token_urlsafe(18)
    username = "t_" + secrets.token_hex(4)

    with app.app_context():
        import settings_store
        saved_settings = {
            key: settings_store.get_value(key)
            for key in ("hero_pinned_ids", "hero_exclude_genre",
                        "weekly_top_years", "weekly_top_limit")
        }
        user = AdminUser(username=username, role="owner")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        original_logo = service.site_assets().get("logo_light")
        original_logo_id = original_logo.id if original_logo else None

    client = app.test_client()
    new_asset_id = None
    title_asset_ids = []
    movie_id = None
    new_row_id = None
    menu_asset_ids = []

    try:
        # --- დაცვა -----------------------------------------------------
        r = client.get("/admin/", follow_redirects=False)
        check("დაუშვებელი წვდომა /admin-ზე გადამისამართდება", r.status_code == 302
              and "/admin/login" in r.headers.get("Location", ""), r.status_code)

        token = csrf_of(client)
        r = client.post("/admin/login", data={
            "username": username, "password": "wrong-password", "_csrf": token,
        })
        check("არასწორი პაროლი არ გადის", r.status_code == 200
              and "არასწორია" in r.get_data(as_text=True))

        token = csrf_of(client)
        r = client.post("/admin/login", data={
            "username": username, "password": password, "_csrf": token,
        }, follow_redirects=False)
        check("სწორი პაროლით შესვლა", r.status_code == 302, r.status_code)

        r = client.get("/admin/")
        check("დაფა იხსნება", r.status_code == 200 and "დაფა" in r.get_data(as_text=True))

        r = client.get("/admin/branding")
        check("ბრენდინგის ეკრანი იხსნება", r.status_code == 200)

        # --- CSRF ------------------------------------------------------
        r = client.post("/admin/branding/settings", data={"site_name": "Hack"})
        check("CSRF-ის გარეშე POST არ გადის", r.status_code == 400, r.status_code)

        # --- ატვირთვა --------------------------------------------------
        token = csrf_of(client)
        r = client.post(
            "/admin/image/site/0/logo_light/upload",
            data={"_csrf": token, "file": (io.BytesIO(make_png()), "test-logo.png")},
            content_type="multipart/form-data", follow_redirects=True,
        )
        check("ლოგოს ატვირთვა", r.status_code == 200)

        with app.app_context():
            asset = service.site_assets().get("logo_light")
            new_asset_id = asset.id if asset else None
            names = sorted({v.name for v in asset.variants}) if asset else []
            logo_url = service.asset_url(asset, name="h128") if asset else None
        check("ვარიანტები დაგენერირდა", names == ["h128", "h256", "h64"], names)
        check("ატვირთული ფაილი ახალია", new_asset_id and new_asset_id != original_logo_id)

        # --- საჯარო გვერდი ---------------------------------------------
        r = client.get("/")
        html = r.get_data(as_text=True)
        check("მთავარი გვერდი იხსნება", r.status_code == 200, r.status_code)
        check("ახალი ლოგო საჯარო გვერდზეა", logo_url and logo_url in html, logo_url)

        r = client.get(logo_url)
        check("/m/ გასცემს ფაილს", r.status_code == 200
              and r.headers.get("Content-Type", "").startswith("image/"), r.status_code)
        check("/m/ ქეშ-სათაური", "immutable" in r.headers.get("Cache-Control", ""),
              r.headers.get("Cache-Control"))

        r = client.get("/m/%d/orig-deadbeef.png" % (new_asset_id or 0))
        check("არასწორი ვარიანტი 404 არ ტეხს", r.status_code in (200, 404), r.status_code)

        # --- ლოგოს წაშლა ------------------------------------------------
        token = csrf_of(client)
        r = client.post("/admin/image/site/0/logo_light/delete",
                        data={"_csrf": token}, follow_redirects=True)
        check("ლოგოს წაშლა", r.status_code == 200)

        r = client.get("/")
        html = r.get_data(as_text=True)
        check("წაშლის შემდეგ ლოგოს სურათი აღარ არის", logo_url not in html)
        check("წაშლის შემდეგ საიტის სახელი ტექსტად ჩანს",
              "header-top__logo-text" in html)

        # --- ფილმის სურათები --------------------------------------------
        # 49764 მთავარი გვერდის ჰეროშია დაპინული (HERO_PINNED_MOVIE_IDS), ანუ
        # sort=hero_top-ის პასუხში ყოველთვის არის — ამიტომ API-ს შემოწმება სტაბილურია.
        with app.app_context():
            movie = db.session.get(Movie, 49764) or Movie.query.order_by(Movie.id).first()
            movie_id = movie.id
            movie_title = movie.title

        r = client.get("/admin/content?type=movie")
        check("კონტენტის სია იხსნება", r.status_code == 200)

        r = client.get("/admin/content?type=movie&only=missing")
        check("ფილტრი „უსურათო\" მუშაობს", r.status_code == 200)

        r = client.get("/admin/content/movie/%d" % movie_id)
        check("ფილმის სურათების ეკრანი", r.status_code == 200
              and movie_title in r.get_data(as_text=True))

        token = csrf_of(client)
        r = client.post(
            "/admin/image/movie/%d/backdrop/upload" % movie_id,
            data={"_csrf": token,
                  "file": (io.BytesIO(make_png((20, 90, 200, 255), (800, 450))), "bd.png")},
            content_type="multipart/form-data", follow_redirects=True,
        )
        check("ბარათის სურათის ატვირთვა", r.status_code == 200)

        token = csrf_of(client)
        r = client.post(
            "/admin/image/movie/%d/hero/upload" % movie_id,
            data={"_csrf": token,
                  "file": (io.BytesIO(make_png((90, 20, 120, 255), (1600, 900))), "hero.png")},
            content_type="multipart/form-data", follow_redirects=True,
        )
        check("ჰეროს სურათის ატვირთვა", r.status_code == 200)

        with app.app_context():
            rec = db.session.get(Movie, movie_id)
            art = service.art_for("movie", movie_id)
            title_asset_ids = [a.id for a in art.values()]
            bd_url = service.asset_url(art.get("backdrop"), profile="art")
            hero_url = service.asset_url(art.get("hero"), name="w1280")
            # დეტალური გვერდი იმავე დამხმარეს იძახებს, ოღონდ სხვა ზომით
            bd_detail = service.art_url(rec, "backdrop", "w1280")
            hero_detail = service.art_url(rec, "hero", "w1920")
        check("ორივე როლი მიება", sorted(art.keys()) == ["backdrop", "hero"], sorted(art.keys()))
        check("არარსებული ზომა ორიგინალზე არ ვარდება",
              bd_detail and "/orig-" not in bd_detail
              and hero_detail and "/orig-" not in hero_detail,
              "%s | %s" % (bd_detail, hero_detail))

        r = client.get("/movie/%d" % movie_id)
        html = r.get_data(as_text=True)
        check("დეტალურ გვერდზე ახალი სურათია", bd_detail and bd_detail in html, bd_detail)
        check("ფონად ჰეროს სურათია", hero_detail and hero_detail in html, hero_detail)

        # ჰეროს API-ს შემოწმება არ უნდა იყოს დამოკიდებული ბაზაში მიმდინარე
        # პარამეტრზე: სატესტო ფილმს თვითონ ვაპინავთ (finally აღადგენს)
        with app.app_context():
            import settings_store as _ss
            _ss.set_value("hero_pinned_ids", [movie_id])
        if True:
            r = client.get("/api/movies?type=movie&sort=hero_top&per=9&page=1")
            item = next((i for i in (r.get_json() or {}).get("items", [])
                         if i["id"] == movie_id), None)
            check("API აბრუნებს ბექოფისის სურათს", item and item.get("poster") == bd_url,
                  item and item.get("poster"))
            check("API აბრუნებს ჰეროს სურათს", item and item.get("hero") == hero_url)

        token = csrf_of(client)
        r = client.post("/admin/image/movie/%d/backdrop/delete" % movie_id,
                        data={"_csrf": token}, follow_redirects=True)
        check("ფილმის სურათის მოხსნა", r.status_code == 200)

        with app.app_context():
            still = service.art_for("movie", movie_id)
        check("მოხსნის შემდეგ backdrop აღარ არის", "backdrop" not in still, list(still))

        r = client.get("/movie/%d" % movie_id)
        check("მოხსნის შემდეგ ორიგინალი დაბრუნდა",
              bd_detail not in r.get_data(as_text=True))

        # --- ბიბლიოთეკა -------------------------------------------------
        r = client.get("/admin/media")
        check("მედია-ბიბლიოთეკა იხსნება", r.status_code == 200)

        r = client.get("/admin/media/%d" % new_asset_id)
        check("ფაილის დეტალები (JSON)", r.status_code == 200
              and r.get_json().get("id") == new_asset_id)

        # --- მთავარი გვერდის კონსტრუქტორი --------------------------------
        r = client.get("/admin/home")
        check("მთავარი გვერდის ეკრანი იხსნება", r.status_code == 200)

        before = home_titles(client)
        check("რიგები ბაზიდან ირენდერება", len(before) >= 5, len(before))

        token = csrf_of(client)
        r = client.post("/admin/home/new", data={
            "_csrf": token, "title": TEST_ROW, "kind": "movies", "icon": "film",
            "media_type": "movie", "sort_mode": "rating", "layout": "landscape",
            "item_limit": "12", "is_active": "on",
        }, follow_redirects=True)
        check("ახალი რიგის დამატება", r.status_code == 200)

        with app.app_context():
            row = HomeRow.query.filter_by(title=TEST_ROW).first()
            new_row_id = row.id if row else None
        titles = home_titles(client)
        check("ახალი რიგი მთავარ გვერდზეა", TEST_ROW in titles)
        check("ბოლოში დაემატა", titles and titles[-1] == TEST_ROW, titles[-1] if titles else None)

        token = csrf_of(client)
        client.post("/admin/home/%d/move" % new_row_id,
                    data={"_csrf": token, "dir": "up"}, follow_redirects=True)
        moved = home_titles(client)
        check("აწევა მუშაობს", moved.index(TEST_ROW) == len(moved) - 2,
              "%d / %d" % (moved.index(TEST_ROW), len(moved)))

        token = csrf_of(client)
        client.post("/admin/home/%d/save" % new_row_id, data={
            "_csrf": token, "title": TEST_ROW, "kind": "movies", "icon": "film",
            "media_type": "movie", "sort_mode": "rating", "layout": "landscape",
            "item_limit": "12",  # is_active გამორთული
        }, follow_redirects=True)
        check("გამორთული რიგი აღარ ჩანს", TEST_ROW not in home_titles(client))

        # სეზონურობა: ფანჯარა, რომელშიც დღევანდელი თარიღი არ ხვდება
        today = datetime.date.today()
        far = today + datetime.timedelta(days=60)
        near = today + datetime.timedelta(days=90)
        token = csrf_of(client)
        client.post("/admin/home/%d/save" % new_row_id, data={
            "_csrf": token, "title": TEST_ROW, "kind": "movies", "icon": "film",
            "media_type": "movie", "sort_mode": "rating", "layout": "landscape",
            "item_limit": "12", "is_active": "on",
            "starts_on": "%02d-%02d" % (far.month, far.day),
            "ends_on": "%02d-%02d" % (near.month, near.day),
        }, follow_redirects=True)
        check("სეზონის გარეთ რიგი არ ჩანს", TEST_ROW not in home_titles(client))

        token = csrf_of(client)
        r = client.post("/admin/home/%d/delete" % new_row_id,
                        data={"_csrf": token}, follow_redirects=True)
        check("რიგის წაშლა", r.status_code == 200 and TEST_ROW not in home_titles(client))
        check("წაშლის შემდეგ თავდაპირველი წყობა", home_titles(client) == before)

        # ჰეროს დაპინვა
        with app.app_context():
            pin_target = Movie.query.filter(
                Movie.poster_url.ilike("%.jpg"), Movie.id != movie_id
            ).order_by(Movie.id.desc()).first()
            pin_id = pin_target.id if pin_target else None
        if pin_id:
            token = csrf_of(client)
            client.post("/admin/home/settings", data={
                "_csrf": token, "hero_pinned_ids": str(pin_id),
                "hero_exclude_genre": "", "weekly_top_years": "2025 2026",
                "weekly_top_limit": "50",
            }, follow_redirects=True)
            r = client.get("/api/movies?type=movie&sort=hero_top&per=9&page=1")
            items = (r.get_json() or {}).get("items", [])
            check("ჰეროში დაპინული ფილმი პირველია",
                  items and items[0]["id"] == pin_id,
                  items[0]["id"] if items else None)

        # --- მენიუ --------------------------------------------------------
        r = client.get("/admin/menu")
        check("მენიუს ეკრანი იხსნება", r.status_code == 200)

        with app.app_context():
            items = MenuItem.query.order_by(MenuItem.position).all()
            first_id = items[0].id if items else None
            first_label = items[0].label if items else None
            second_label = items[1].label if len(items) > 1 else None
        check("მენიუ ბაზიდან ირენდერება", first_id is not None, len(items))

        html = client.get("/").get_data(as_text=True)
        check("მენიუს პუნქტი საიტზეა", first_label and first_label in html)

        token = csrf_of(client)
        r = client.post(
            "/admin/image/menu_item/%d/icon/upload" % first_id,
            data={"_csrf": token,
                  "file": (io.BytesIO(make_png((240, 200, 40, 255), (128, 128))), "ico.png")},
            content_type="multipart/form-data", follow_redirects=True,
        )
        check("მენიუს აიქონის ატვირთვა", r.status_code == 200)

        with app.app_context():
            item = db.session.get(MenuItem, first_id)
            icon_url = service.art_url(item, "icon", "h64")
            menu_asset_ids.append(service.art_asset(item, "icon").id)
        html = client.get("/").get_data(as_text=True)
        check("ატვირთული აიქონი მენიუშია", icon_url and icon_url in html, icon_url)
        check("ჩაშენებული SVG ჩანაცვლდა", 'class="nav-link__img"' in html)

        token = csrf_of(client)
        client.post("/admin/image/menu_item/%d/icon/delete" % first_id,
                    data={"_csrf": token}, follow_redirects=True)
        html = client.get("/").get_data(as_text=True)
        check("აიქონის მოხსნის შემდეგ SVG დაბრუნდა",
              icon_url not in html and first_label in html)

        # თანმიმდევრობა
        token = csrf_of(client)
        client.post("/admin/menu/%d/move" % first_id,
                    data={"_csrf": token, "dir": "down"}, follow_redirects=True)
        with app.app_context():
            after = [m.label for m in MenuItem.query.order_by(MenuItem.position).all()]
        check("მენიუს გადალაგება მუშაობს", after[:2] == [second_label, first_label],
              after[:2])
        token = csrf_of(client)
        client.post("/admin/menu/%d/move" % first_id,
                    data={"_csrf": token, "dir": "up"}, follow_redirects=True)

        # --- მსახიობი -----------------------------------------------------
        r = client.get("/admin/persons")
        check("მსახიობების ეკრანი იხსნება", r.status_code == 200)

        with app.app_context():
            person = Person.query.order_by(Person.popularity.desc()).first()
            person_id = person.id if person else None
        if person_id:
            token = csrf_of(client)
            r = client.post(
                "/admin/image/person/%d/photo/upload" % person_id,
                data={"_csrf": token,
                      "file": (io.BytesIO(make_png((40, 200, 160, 255), (400, 600))), "face.png")},
                content_type="multipart/form-data", follow_redirects=True,
            )
            check("მსახიობის ფოტოს ატვირთვა", r.status_code == 200)
            with app.app_context():
                p = db.session.get(Person, person_id)
                photo_url = service.art_url(p, "photo", "w300")
                menu_asset_ids.append(service.art_asset(p, "photo").id)
            data = client.get("/api/persons?per=60&page=1").get_json() or {}
            found = next((x for x in data.get("items", []) if x["id"] == person_id), None)
            check("API აბრუნებს ატვირთულ ფოტოს",
                  found and found.get("photo") == photo_url, found and found.get("photo"))

        # --- საიტის ფონი და რიგის ფონი -------------------------------------
        token = csrf_of(client)
        client.post("/admin/image/site/0/page_background/upload",
                    data={"_csrf": token,
                          "file": (io.BytesIO(make_png((15, 15, 30, 255), (1200, 800))), "bg.png")},
                    content_type="multipart/form-data", follow_redirects=True)
        with app.app_context():
            bg_asset = service.site_assets().get("page_background")
            if bg_asset:
                menu_asset_ids.append(bg_asset.id)
        html = client.get("/").get_data(as_text=True)
        check("საიტის ფონი გამოიყენება", "background-image: url(" in html)

        with app.app_context():
            movies_row = HomeRow.query.filter_by(kind="movies").order_by(HomeRow.position).first()
            row_id = movies_row.id if movies_row else None
        if row_id:
            token = csrf_of(client)
            client.post("/admin/image/home_row/%d/row_bg/upload" % row_id,
                        data={"_csrf": token,
                              "file": (io.BytesIO(make_png((60, 20, 80, 255), (1400, 500))), "rowbg.png")},
                        content_type="multipart/form-data", follow_redirects=True)
            with app.app_context():
                row = db.session.get(HomeRow, row_id)
                row_bg_url = service.art_url(row, "row_bg", "w1400")
                menu_asset_ids.append(service.art_asset(row, "row_bg").id)
            html = client.get("/").get_data(as_text=True)
            check("რიგის ფონი მთავარ გვერდზეა",
                  row_bg_url and ('data-bg="%s"' % row_bg_url) in html, row_bg_url)

        # --- რიგის ფილმების სია: შაფლი, ხელით დამატება, გადათრევა ----------
        with app.app_context():
            pin_row = (HomeRow.query.filter_by(kind="movies", media_type="movie")
                       .order_by(HomeRow.position).first())
            pin_row_id = pin_row.id
            pin_limit = pin_row.item_limit or 18

        token = csrf_of(client)
        r = client.post("/admin/home/%d/shuffle" % pin_row_id,
                        data={"_csrf": token}, follow_redirects=True)
        check("შაფლი მუშაობს", r.status_code == 200)

        with app.app_context():
            row = db.session.get(HomeRow, pin_row_id)
            first_pick = [(i.media_type, i.item_id) for i in
                          sorted(row.items, key=lambda x: x.position)]
        check("შაფლმა სია შეავსო", len(first_pick) == pin_limit,
              "%d / %d" % (len(first_pick), pin_limit))

        html = client.get("/").get_data(as_text=True)
        expect = ",".join("%s:%d" % p for p in first_pick)
        check("სია მთავარ გვერდზე გადადის", ('data-ids="%s"' % expect) in html)

        data = client.get("/api/movies?ids=" + expect).get_json() or {}
        got = [(i["type"], i["id"]) for i in data.get("items", [])]
        check("API ზუსტად ამ რიგით აბრუნებს", got == first_pick,
              "%d დაბრუნდა" % len(got))

        # მეორედ შაფლი სხვა სიას უნდა მოგვცემდეს
        token = csrf_of(client)
        client.post("/admin/home/%d/shuffle" % pin_row_id,
                    data={"_csrf": token}, follow_redirects=True)
        with app.app_context():
            row = db.session.get(HomeRow, pin_row_id)
            second_pick = [(i.media_type, i.item_id) for i in
                           sorted(row.items, key=lambda x: x.position)]
        check("ხელახალი შაფლი სხვა შედეგს იძლევა", second_pick != first_pick)

        # ხელით დამატება
        token = csrf_of(client)
        r = client.post("/admin/home/%d/items/add" % pin_row_id,
                        data={"_csrf": token, "media_type": "movie",
                              "item_id": str(movie_id)}, follow_redirects=True)
        with app.app_context():
            row = db.session.get(HomeRow, pin_row_id)
            pks = [i.id for i in sorted(row.items, key=lambda x: x.position)]
            has = any(i.item_id == movie_id and i.media_type == "movie"
                      for i in row.items)
        check("ხელით დამატება", has and len(pks) == len(second_pick) + 1)

        # იგივე მეორედ აღარ ემატება
        token = csrf_of(client)
        client.post("/admin/home/%d/items/add" % pin_row_id,
                    data={"_csrf": token, "media_type": "movie",
                          "item_id": str(movie_id)}, follow_redirects=True)
        with app.app_context():
            row = db.session.get(HomeRow, pin_row_id)
            check("დუბლიკატი არ ემატება", len(row.items) == len(pks))

        # გადათრევა: ბოლო ელემენტი პირველ ადგილას
        moved = [pks[-1]] + pks[:-1]
        token = csrf_of(client)
        r = client.post("/admin/home/%d/items/reorder" % pin_row_id,
                        data={"_csrf": token, "order": ",".join(str(p) for p in moved)})
        with app.app_context():
            row = db.session.get(HomeRow, pin_row_id)
            now = [i.id for i in sorted(row.items, key=lambda x: x.position)]
        check("ფილმების გადათრევა ინახება", r.status_code == 200 and now[0] == pks[-1],
              now[:2])

        # ძებნა
        data = client.get("/admin/home/search?q=" + quote(movie_title[:10])).get_json() or {}
        check("ძებნა პასუხობს", isinstance(data.get("items"), list))

        # ჩანაცვლება ადგილზე: ნომერი უნდა შენარჩუნდეს
        with app.app_context():
            row = db.session.get(HomeRow, pin_row_id)
            ordered = sorted(row.items, key=lambda x: x.position)
            target = ordered[1]
            target_pk, target_pos, before_id = target.id, target.position, target.item_id
            taken = {(i.media_type, i.item_id) for i in row.items}
            swap_in = (Movie.query.filter(Movie.poster_url.ilike("%.jpg"))
                       .filter(~Movie.id.in_([i.item_id for i in row.items]))
                       .order_by(Movie.id.desc()).first())
            swap_id = swap_in.id

        token = csrf_of(client)
        r = client.post("/admin/home/%d/items/%d/replace" % (pin_row_id, target_pk),
                        data={"_csrf": token, "media_type": "movie",
                              "item_id": str(swap_id)}, follow_redirects=True)
        with app.app_context():
            it = db.session.get(HomeRowItem, target_pk)
            swapped, same_pos = it.item_id == swap_id, it.position == target_pos
        check("ჩანაცვლება ადგილზე", r.status_code == 200 and swapped and before_id != swap_id)
        check("ჩანაცვლებისას ნომერი რჩება", same_pos, "%s → %s" % (target_pos, it.position))

        # დუბლიკატზე ჩანაცვლება არ გადის
        with app.app_context():
            other = [i for i in sorted(
                db.session.get(HomeRow, pin_row_id).items, key=lambda x: x.position)
                if i.id != target_pk][0]
            other_id, other_type = other.item_id, other.media_type
        token = csrf_of(client)
        client.post("/admin/home/%d/items/%d/replace" % (pin_row_id, target_pk),
                    data={"_csrf": token, "media_type": other_type,
                          "item_id": str(other_id)}, follow_redirects=True)
        with app.app_context():
            still = db.session.get(HomeRowItem, target_pk).item_id
        check("დუბლიკატზე ჩანაცვლება არ გადის", still == swap_id)

        # ნომრის პირდაპირ მითითება
        token = csrf_of(client)
        r = client.post("/admin/home/%d/items/%d/move-to" % (pin_row_id, target_pk),
                        data={"_csrf": token, "position": "1"}, follow_redirects=True)
        with app.app_context():
            row = db.session.get(HomeRow, pin_row_id)
            first = sorted(row.items, key=lambda x: x.position)[0]
            positions = sorted(i.position for i in row.items)
        check("ნომრით გადატანა", r.status_code == 200 and first.id == target_pk)
        check("ნომრები უწყვეტია", positions == list(range(len(positions))), positions[:4])

        # დიაპაზონს გარეთ მითითება არ ტეხს
        token = csrf_of(client)
        client.post("/admin/home/%d/items/%d/move-to" % (pin_row_id, target_pk),
                    data={"_csrf": token, "position": "9999"}, follow_redirects=True)
        with app.app_context():
            row = db.session.get(HomeRow, pin_row_id)
            last = sorted(row.items, key=lambda x: x.position)[-1]
            count_ok = len(row.items) == len(positions)
        check("არასწორი ნომერი უსაფრთხოდ იჭრება", last.id == target_pk and count_ok)

        # რიგების გადათრევა
        with app.app_context():
            order_before = [r_.id for r_ in
                            HomeRow.query.order_by(HomeRow.position).all()]
        flipped = [order_before[1], order_before[0]] + order_before[2:]
        token = csrf_of(client)
        r = client.post("/admin/home/reorder",
                        data={"_csrf": token, "order": ",".join(str(i) for i in flipped)})
        with app.app_context():
            order_after = [r_.id for r_ in
                           HomeRow.query.order_by(HomeRow.position).all()]
        check("რიგების გადათრევა ინახება",
              r.status_code == 200 and order_after == flipped, order_after[:3])
        token = csrf_of(client)
        client.post("/admin/home/reorder",
                    data={"_csrf": token, "order": ",".join(str(i) for i in order_before)})

        # გასუფთავება: რიგი ისევ ავტომატური
        token = csrf_of(client)
        r = client.post("/admin/home/%d/items/clear" % pin_row_id,
                        data={"_csrf": token}, follow_redirects=True)
        with app.app_context():
            row = db.session.get(HomeRow, pin_row_id)
            empty = len(row.items) == 0
        html = client.get("/").get_data(as_text=True)
        check("გასუფთავების შემდეგ სია ცარიელია", empty)
        check("გასუფთავების შემდეგ data-ids ქრება",
              ('data-ids="%s"' % expect) not in html)

        # --- „სლოტი არის, მაგრამ არაფერს აკეთებს" კლასის რეგრესიები ---------
        # ეს ხუთი ერთი და იმავე ტიპის ხარვეზი იყო: ბექოფისში ატვირთვა მუშაობდა,
        # საიტი კი ატვირთულს უგულებელყოფდა. თითოეული აქ იბლოკება.
        with app.app_context():
            top9 = HomeRow.query.filter_by(layout="top9").order_by(HomeRow.position).first()
            top9_id = top9.id if top9 else None

        if top9_id:
            for role, fname, colour in (("row_bg", "t9bg.png", (30, 80, 30, 255)),
                                        ("icon", "t9icon.png", (80, 30, 30, 255))):
                token = csrf_of(client)
                client.post("/admin/image/home_row/%d/%s/upload" % (top9_id, role),
                            data={"_csrf": token,
                                  "file": (io.BytesIO(make_png(colour, (900, 400))), fname)},
                            content_type="multipart/form-data", follow_redirects=True)
            with app.app_context():
                row = db.session.get(HomeRow, top9_id)
                t9_bg = service.art_url(row, "row_bg", "w1400")
                t9_icon = service.art_url(row, "icon", "h64")
                for role in ("row_bg", "icon"):
                    a = service.art_asset(row, role)
                    if a:
                        menu_asset_ids.append(a.id)
            html = client.get("/").get_data(as_text=True)
            check("ტოპ-9 რიგს ფონი ეძლევა", t9_bg and ('data-bg="%s"' % t9_bg) in html, t9_bg)
            check("რიგის ატვირთული აიქონი გადაეცემა",
                  t9_icon and ('data-icon-img="%s"' % t9_icon) in html, t9_icon)

        js = client.get("/static/js/app.js").get_data(as_text=True)
        check("ტოპ-9 რიგი ფონს კითხულობს", "buildTopRow" in js and js.count("el.dataset.bg") >= 2)
        check("მსახიობის ჩამნაცვლებელი JS-ში იკითხება", "CFG.placeholderPerson" in js)
        check("ჰერო hero-სურათიან ჩანაწერს არ ყრის", "m.hero || m.poster" in js)
        check("ძებნის ესკიზს ჩამნაცვლებელი აქვს", "geThumbFail" in js)

        wl = client.get("/static/js/watchlist.js").get_data(as_text=True)
        check("სანახავი სიის ჩამნაცვლებელი ბექოფისიდანაა",
              "GE_CFG" in wl and "geThumbFail" in wl)

        # ამ მომენტისთვის ტესტმა ლოგო უკვე წაშალა — <picture> მხოლოდ მაშინ ჩნდება,
        # როცა ძირითადი ლოგო არსებობს, ამიტომ ჯერ თავდაპირველს ვაბრუნებთ
        with app.app_context():
            if original_logo_id:
                original = db.session.get(MediaAsset, original_logo_id)
                if original is not None:
                    service.bind(service.SITE, 0, "logo_light", original)

        token = csrf_of(client)
        client.post("/admin/image/site/0/logo_mobile/upload",
                    data={"_csrf": token,
                          "file": (io.BytesIO(make_png((120, 120, 200, 255), (200, 200))), "lm.png")},
                    content_type="multipart/form-data", follow_redirects=True)
        with app.app_context():
            lm = service.site_assets().get("logo_mobile")
            if lm:
                menu_asset_ids.append(lm.id)
                lm_url = service.asset_url(lm, name="h64")
        html = client.get("/").get_data(as_text=True)
        check("მობილურის ლოგო რეალურად გამოიყენება",
              "<picture>" in html and lm_url and lm_url in html, lm_url)

        with app.app_context():
            service.unbind("site", 0, "logo_mobile")
            if top9_id:
                for role in ("row_bg", "icon"):
                    service.unbind("home_row", top9_id, role)

        # --- ფაილი აკლია: ორიგინალზე დაბრუნება ---------------------------
        # ეს ის შემთხვევაა, როცა ბაზა ახალ სერვერზე გადადის, საცავი კი ცარიელია.
        # საიტი არ უნდა გატყდეს: /m/ დროებით ორიგინალ წყაროზე გადაამისამართებს.
        from medialib.storage import get_storage
        with app.app_context():
            probe = service.store_bytes(
                make_png((7, 120, 90, 255), (500, 300)), filename="fallback.png",
                profile="art", source="mirror",
                source_url="https://example.invalid/original.jpg",
            )
            probe_id = probe.id
            title_asset_ids.append(probe_id)
            variant = probe.variants[0]
            probe_url = "/m/%d/%s-%s.%s" % (probe.id, variant.name, probe.sha8, variant.fmt)
            probe_path = get_storage().path(variant.storage_key)

        os.rename(probe_path, probe_path + ".hidden")  # ჯერ ვმალავთ, მერე ვითხოვთ
        try:
            r = client.get(probe_url)
            location = r.headers.get("Location") or ""
            r.close()
            check("ფაილის არარსებობისას გადამისამართება ორიგინალზე",
                  r.status_code == 302 and location == "https://example.invalid/original.jpg",
                  "%s %s" % (r.status_code, location))
        finally:
            os.rename(probe_path + ".hidden", probe_path)

        r = client.get(probe_url)
        ok = r.status_code == 200
        r.close()
        check("ფაილის დაბრუნებისას ისევ პირდაპირ გაიცემა", ok)

        # --- ფონური ამოცანები (ქსელის გარეშე) ----------------------------
        r = client.get("/admin/jobs")
        check("ამოცანების ეკრანი იხსნება", r.status_code == 200)

        with app.app_context():
            plan = mirror.plan()
        check("mirror.plan ითვლის დარჩენილს", plan["pending"] > 0, plan["pending"])
        check("TMDB-ის კანდიდატები გამოცნობილია",
              plan["tmdb_ready"] > plan["other"], "%s / %s" % (plan["tmdb_ready"], plan["other"]))
        check("TMDB-ის ჰეში ცნობადია",
              mirror.tmdb_candidate(
                  "https://static.moviege.com/movies/bg/big/bvpI11RJbE6lHSWCrhvNC1S1MtO.jpg"
              ) == "https://image.tmdb.org/t/p/original/bvpI11RJbE6lHSWCrhvNC1S1MtO.jpg")
        check("არა-TMDB მისამართი არ გარდაიქმნება",
              mirror.tmdb_candidate("https://animetv.ge/uploads/posts/x.webp") is None)

        # ძრავი მოწმდება ყალბი ამოცანით: ქსელი არ სჭირდება და სწრაფია
        def _fake(ctx, params):
            ctx.set_total(4)
            for _ in range(4):
                ctx.bump("done")
            ctx.log("დასრულდა")
            ctx.flush()
            return {"ok": True}

        with app.app_context():
            job = job_engine.create_job("test_job", {"x": 1})
            job_id = job.id
        thread = job_engine.start(app, job_id, _fake)
        thread.join(timeout=20)

        r = client.get("/admin/jobs/%d/status" % job_id)
        data = r.get_json() or {}
        check("ამოცანა დასრულდა", data.get("status") == "done", data.get("status"))
        check("პროგრესი ჩაიწერა", data.get("done") == 4 and data.get("percent") == 100,
              "%s / %s" % (data.get("done"), data.get("percent")))
        check("ლოგი ინახება", "დასრულდა" in (data.get("log") or ""))
        check("შედეგი ინახება", (data.get("result") or {}).get("ok") is True)

        # გაჩერება
        stop = threading.Event()

        def _slow(ctx, params):
            ctx.set_total(1000)
            for _ in range(1000):
                ctx.bump("done", 1)
                ctx.flush()
                if stop.wait(0.02):
                    break
            return {}

        with app.app_context():
            job2 = job_engine.create_job("test_job_slow", {})
            job2_id = job2.id
        thread2 = job_engine.start(app, job2_id, _slow)
        time.sleep(0.6)
        with app.app_context():
            cancelled = job_engine.request_cancel(job2_id)
        thread2.join(timeout=20)
        stop.set()
        with app.app_context():
            j2 = db.session.get(Job, job2_id)
            db.session.refresh(j2)
            final = j2.status
        check("გაჩერების მოთხოვნა მიიღება", cancelled)
        check("ამოცანა ჩერდება", final == "cancelled", final)

        # --- გასვლა -----------------------------------------------------
        token = csrf_of(client)
        r = client.post("/admin/logout", data={"_csrf": token}, follow_redirects=False)
        check("გასვლა", r.status_code == 302)
        r = client.get("/admin/", follow_redirects=False)
        check("გასვლის შემდეგ წვდომა დახურულია", r.status_code == 302)

    finally:
        # --- დასუფთავება -------------------------------------------------
        with app.app_context():
            for asset_id in [new_asset_id] + list(title_asset_ids) + list(menu_asset_ids):
                if not asset_id:
                    continue
                asset = db.session.get(MediaAsset, asset_id)
                if asset is not None:
                    service.delete_asset(asset, hard=True)
            if movie_id:
                for role in ("backdrop", "poster", "hero"):
                    service.unbind("movie", movie_id, role)
            HomeRow.query.filter_by(title=TEST_ROW).delete()
            if 'pin_row_id' in dir():
                pass
            for st, role in (("site", "page_background"),):
                service.unbind(st, 0, role)
            Job.query.filter(Job.kind.like('test_job%')).delete(synchronize_session=False)
            import settings_store
            for key, value in saved_settings.items():
                settings_store.set_value(key, value)
            if original_logo_id:
                original = db.session.get(MediaAsset, original_logo_id)
                if original is not None:
                    service.bind(service.SITE, 0, "logo_light", original)
            MediaLink.query.filter_by(asset_id=None).delete()
            user = db.session.get(AdminUser, user_id)
            if user is not None:
                db.session.delete(user)
            db.session.commit()

            restored = service.site_assets().get("logo_light")
            print("\nდასუფთავება: ლოგო აღდგენილია =", bool(restored and restored.id == original_logo_id))

    print("\n%s" % ("ყველა შემოწმება გავიდა." if not FAILED
                    else "ჩავარდა %d: %s" % (len(FAILED), ", ".join(FAILED))))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
