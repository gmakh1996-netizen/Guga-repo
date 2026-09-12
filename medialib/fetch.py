"""გარე სურათის ჩამოტვირთვა ჩვენს საცავში.

გამოიყენება ბექოფისის ღილაკით „ჩამოიტანე ამჟამინდელი სურათი": ფილმის პოსტერი
დღეს სხვისი სერვერიდან იტვირთება, ეს კი მის ასლს ჩვენთან ინახავს, რომ ბმულის
გატეხვა ან hotlink-ის დაბლოკვა ჩვენს საიტს აღარ ეხებოდეს.
"""
import os
from urllib.parse import unquote, urlparse

import requests

from .images import MediaError

TIMEOUT = 20
MAX_BYTES = 15 * 1024 * 1024
# ჩვეულებრივი ბრაუზერის User-Agent: ზოგი CDN ცარიელ UA-ს აბრუნებს უკან
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def fetch_image(url):
    """აბრუნებს (bytes, filename). შეცდომაზე აგდებს MediaError-ს ქართული ტექსტით."""
    if not url or not str(url).startswith(("http://", "https://")):
        raise MediaError("მისამართი არასწორია (უნდა იწყებოდეს http:// ან https://).")

    try:
        resp = requests.get(
            url, timeout=TIMEOUT, stream=True,
            headers={"User-Agent": UA, "Accept": "image/*,*/*;q=0.8"},
        )
    except requests.RequestException as exc:
        raise MediaError("ჩამოტვირთვა ვერ მოხერხდა: %s" % exc) from exc

    if resp.status_code == 403:
        raise MediaError(
            "წყარომ წვდომა აკრძალა (403). ეს ჰოსტი სავარაუდოდ Cloudflare-ის უკანაა, "
            "ატვირთეთ ფაილი ხელით."
        )
    if resp.status_code != 200:
        raise MediaError("წყარომ დააბრუნა %d." % resp.status_code)

    ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
    if ctype and not ctype.startswith("image/"):
        raise MediaError("ბმულზე სურათი არ არის (%s)." % ctype)

    buf = bytearray()
    for chunk in resp.iter_content(64 * 1024):
        buf.extend(chunk)
        if len(buf) > MAX_BYTES:
            raise MediaError("ფაილი ძალიან დიდია (%d მბ-ზე მეტი)." % (MAX_BYTES // 1024 // 1024))
    if not buf:
        raise MediaError("წყარომ ცარიელი ფაილი დააბრუნა.")

    name = os.path.basename(unquote(urlparse(url).path)) or "downloaded"
    return bytes(buf), name[:255]
