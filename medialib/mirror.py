"""ფილმების სურათების ჩამოტანა გარე სერვერებიდან ჩვენს საცავში.

დღეს საიტის თითქმის ყველა სურათი სხვისი სერვერიდან იტვირთება. ეს მოდული
თითოეულის ასლს ჩვენთან ინახავს და `backdrop` როლზე აბამს, ანუ საიტი წყვეტს
გარე ჰოსტზე დამოკიდებულებას.

ორი წესი, რომელიც მნიშვნელოვანია:

1. **TMDB-ს უპირატესობა.** `static.moviege.com`-ის პოსტერების 95.4%-ს ფაილის
   სახელად TMDB-ის 27-სიმბოლოიანი ჰეში აქვს. იგივე ფაილი `image.tmdb.org`-ზე
   უფრო მაღალი ხარისხითაა და ის Cloudflare-ის უკან არ დგას. ამიტომ ასეთ
   შემთხვევაში TMDB-დან ვიღებთ, ორიგინალ ჰოსტს კი მხოლოდ სათადარიგოდ ვტოვებთ.

2. **ხელით დაყენებულს არ ვეხებით.** თუ ფილმს ბექოფისიდან უკვე აქვს სურათი,
   გამოტოვდება. ამიტომვეა ამოცანა თავიდან გაშვებადი: ის, რაც უკვე ჩამოიტანა,
   მეორედ აღარ ჩამოიტვირთება.
"""
import os
import re
import time
from collections import Counter
from urllib.parse import urlparse

from models import MediaLink, Movie, Series, db

from . import service
from .fetch import fetch_image
from .images import MediaError

TMDB_HASH = re.compile(r"^[A-Za-z0-9]{27}$")
TMDB_ORIGINAL = "https://image.tmdb.org/t/p/original/%s.jpg"

# თითო ჰოსტზე მოთხოვნებს შორის მინიმალური პაუზა (წამი)
HOST_DELAY = {
    "image.tmdb.org": 0.12,
    "static.moviege.com": 0.7,
    "_default": 0.5,
}
# თუ ერთი ჰოსტი ზედიზედ ამდენჯერ ჩავარდა, ვჩერდებით: სჯობს ამოცანა შეწყდეს,
# ვიდრე ათასობით ცრუ „გატეხილი" ჩანაწერი დაგროვდეს
HOST_FAIL_LIMIT = 20
# დისკზე ამაზე ნაკლები რომ დარჩეს, ამოცანა ჩერდება: სჯობს შეწყდეს,
# ვიდრე მთელი დისკი გაივსოს და სისტემამ ხელი შეგიშალოთ
MIN_FREE_BYTES = 3 * 1024 ** 3

MODELS = {"movie": Movie, "series": Series}


def _free_bytes():
    from .storage import LocalStorage, get_storage
    storage = get_storage()
    if isinstance(storage, LocalStorage):
        return storage.free_bytes()
    return None


def tmdb_candidate(url):
    """თუ ფაილის სახელი TMDB-ის ჰეშია, აბრუნებს TMDB-ის მისამართს."""
    if not url:
        return None
    name = os.path.basename(urlparse(url).path)
    stem = name.rsplit(".", 1)[0] if "." in name else name
    if TMDB_HASH.match(stem):
        return TMDB_ORIGINAL % stem
    return None


def _pending_query(Model, subject_type):
    """ჩანაწერები, რომლებსაც გარე სურათი აქვთ და ჩვენი ასლი ჯერ არა."""
    owned = db.session.query(MediaLink.subject_id).filter(
        MediaLink.subject_type == subject_type,
        MediaLink.role == "backdrop",
    )
    return Model.query.filter(
        Model.poster_url.isnot(None),
        Model.poster_url != "",
        Model.poster_url.like("http%"),
        ~Model.id.in_(owned),
    )


def plan():
    """რა და რამდენი დაგვრჩა. ქსელს არ ეკარება, ამიტომ მყისიერია."""
    hosts = Counter()
    tmdb_ready = 0
    total = 0
    for subject_type, Model in MODELS.items():
        rows = _pending_query(Model, subject_type).with_entities(
            Model.id, Model.poster_url
        ).all()
        total += len(rows)
        for _id, url in rows:
            hosts[(urlparse(url).netloc or "?")] += 1
            if tmdb_candidate(url):
                tmdb_ready += 1

    owned = db.session.query(MediaLink).filter(
        MediaLink.subject_type.in_(tuple(MODELS)), MediaLink.role == "backdrop"
    ).count()

    return {
        "pending": total,
        "already_owned": owned,
        "tmdb_ready": tmdb_ready,
        "other": total - tmdb_ready,
        "hosts": hosts.most_common(),
    }


def _sleep_for(host, last_seen):
    delay = HOST_DELAY.get(host, HOST_DELAY["_default"])
    previous = last_seen.get(host)
    if previous is not None:
        wait = delay - (time.time() - previous)
        if wait > 0:
            time.sleep(wait)
    last_seen[host] = time.time()


def run(ctx, params):
    """ამოცანის სხეული. params: limit (0 = ყველა), prefer_tmdb, subject_types."""
    limit = int(params.get("limit") or 0)
    prefer_tmdb = params.get("prefer_tmdb", True)
    wanted = params.get("subject_types") or list(MODELS)

    items = []
    for subject_type in wanted:
        Model = MODELS.get(subject_type)
        if Model is None:
            continue
        rows = _pending_query(Model, subject_type).with_entities(
            Model.id, Model.poster_url
        ).order_by(Model.id.desc()).all()
        items.extend((subject_type, rid, url) for rid, url in rows)

    if limit:
        items = items[:limit]
    ctx.set_total(len(items))
    ctx.log("დასამუშავებელია %d ჩანაწერი." % len(items))
    if not items:
        return {"pending": 0}

    last_seen = {}
    host_fails = Counter()
    fetched_bytes = 0
    sample_sizes = []

    for index, (subject_type, rec_id, url) in enumerate(items, start=1):
        # უკვე დამუშავებული (ამოცანის ხელახლა გაშვება ან პარალელური ცვლილება)
        exists = MediaLink.query.filter_by(
            subject_type=subject_type, subject_id=rec_id, role="backdrop"
        ).first()
        if exists is not None:
            ctx.bump("skipped")
            continue

        sources = []
        if prefer_tmdb:
            candidate = tmdb_candidate(url)
            if candidate:
                sources.append(candidate)
        sources.append(url)

        saved = None
        last_error = None
        for source in sources:
            host = urlparse(source).netloc or "?"
            if host_fails[host] >= HOST_FAIL_LIMIT:
                last_error = "ჰოსტი %s ზედიზედ ბევრჯერ ჩავარდა, გამოტოვებულია" % host
                continue
            _sleep_for(host, last_seen)
            try:
                data, name = fetch_image(source)
                asset = service.store_bytes(
                    data, filename=name, profile="art",
                    source="mirror", source_url=source,
                )
                service.bind(subject_type, rec_id, "backdrop", asset)
                # ზოგი წყარო (ანიმეს ჰოსტები) ვერტიკალურ სურათს იძლევა. ასეთი
                # ჩანაწერისთვის იმავე ფაილს „ვერტიკალური პოსტერის" როლზეც ვაბამთ:
                # ეს ველი ბაზაში ყველგან ცარიელია და ბარათებს იერს უუმჯობესებს.
                if asset.height > asset.width * 1.2:
                    service.bind(subject_type, rec_id, "poster", asset)
                saved = asset
                host_fails[host] = 0
                fetched_bytes += len(data)
                if len(sample_sizes) < 40:
                    sample_sizes.append(len(data))
                break
            except MediaError as exc:
                last_error = "%s: %s" % (host, exc)
                host_fails[host] += 1
            except Exception as exc:  # noqa: BLE001
                db.session.rollback()
                last_error = "%s: %s" % (host, exc)
                host_fails[host] += 1

        if saved is not None:
            ctx.bump("done")
            ctx.counters["bytes_fetched"] = fetched_bytes
        else:
            ctx.bump("failed")
            ctx.log("ვერ ჩამოიტვირთა %s #%s — %s" % (subject_type, rec_id, last_error))

        # პირველი ოცდაათის შემდეგ ვაქვეყნებთ პროგნოზს, რომ ციფრები ადრევე ჩანდეს
        if index == 30 and sample_sizes:
            average = sum(sample_sizes) / len(sample_sizes)
            projected = average * len(items) * 2.1  # ორიგინალი + წარმოებულები
            ctx.log("საშუალო ზომა %.0f კბ, სავარაუდო ჯამი დაახლოებით %.2f გბ."
                    % (average / 1024, projected / 1024 ** 3))

        if index % 200 == 0:
            ctx.log("დამუშავებულია %d / %d" % (index, len(items)))
            free = _free_bytes()
            if free is not None and free < MIN_FREE_BYTES:
                ctx.log("დისკზე დარჩა მხოლოდ %.1f გბ. ამოცანა ჩერდება." % (free / 1024 ** 3))
                ctx.flush()
                return {"stopped": "low_disk", "processed": index,
                        "bytes_fetched": fetched_bytes}

    ctx.flush()
    return {
        "processed": len(items),
        "bytes_fetched": fetched_bytes,
        "gb": round(fetched_bytes / 1024 ** 3, 3),
    }
