"""საიტის პარამეტრები ბაზაში (Setting ცხრილი), ნაგულისხმევებით.

მიზანი: ის მნიშვნელობები, რომლებიც დღეს კოდშია ჩაწერილი, ბექოფისიდან იცვლებოდეს
deploy-ის გარეშე. წაკითხვა იაფია (ერთი მოთხოვნა), ჩაწერა ადმინიდან იშვიათია.
"""
import json

from models import db, Setting

DEFAULTS = {
    # ბრენდინგი
    "site_name": "Movie World",
    "site_tagline": "ფილმები და სერიალები ქართულად",
    "logo_height": 52,
    "logo_alt": "",
    # რეკლამა
    "popup_ad_enabled": True,
    "popup_ad_url": "",
    # ქცევა. "hide" = დღევანდელი ქცევა (სურათი თუ არ ჩაიტვირთა, ბარათი ქრება),
    # "placeholder" = ჩამნაცვლებელი სურათი ჩანს და ფილმი გვერდიდან არ იკარგება.
    "broken_image_behavior": "hide",  # placeholder | hide

    # მთავარი გვერდი (აქამდე კოდში იყო ჩაწერილი)
    "hero_pinned_ids": [49764],       # ჰეროში ყოველთვის შემავალი ფილმები
    "hero_exclude_genre": 900000025,  # ანიმე ჰეროში არ ხვდება
    "weekly_top_years": ["2025", "2026"],
    "weekly_top_limit": 50,
}

GROUPS = {
    "site_name": "brand", "site_tagline": "brand", "logo_height": "brand",
    "logo_alt": "brand", "popup_ad_enabled": "ads", "popup_ad_url": "ads",
    "broken_image_behavior": "media",
    "hero_pinned_ids": "home", "hero_exclude_genre": "home",
    "weekly_top_years": "home", "weekly_top_limit": "home",
}


def get_value(key, default=None):
    row = db.session.get(Setting, key)
    if row is None or row.value_json is None:
        return DEFAULTS.get(key, default)
    try:
        return json.loads(row.value_json)
    except (ValueError, TypeError):
        return DEFAULTS.get(key, default)


def set_value(key, value, admin_id=None):
    row = db.session.get(Setting, key)
    if row is None:
        row = Setting(key=key, group=GROUPS.get(key, "general"))
        db.session.add(row)
    row.value_json = json.dumps(value, ensure_ascii=False)
    row.updated_by = admin_id
    db.session.commit()
    return value


def all_values():
    """ყველა პარამეტრი ერთი მოთხოვნით, ნაგულისხმევებზე დაფენილი."""
    values = dict(DEFAULTS)
    for row in Setting.query.all():
        if row.value_json is None:
            continue
        try:
            values[row.key] = json.loads(row.value_json)
        except (ValueError, TypeError):
            continue
    return values
