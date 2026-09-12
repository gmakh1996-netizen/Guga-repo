"""ფაილების საცავი: ლოკალური საქაღალდე ან S3-თავსებადი ობიექტური საცავი (R2).

ორივეს ერთი ინტერფეისი აქვს, არჩევანი კი ერთი env-ცვლადია:

    MEDIA_BACKEND=local   →  MEDIA_ROOT-ის საქაღალდე (Railway-ზე volume, მაგ. /data/media)
    MEDIA_BACKEND=r2      →  Cloudflare R2 / S3 (MEDIA_R2_* ცვლადები)

ამიტომ საცავის საბოლოო არჩევანი კოდს არ ცვლის.
"""
import os
import shutil


class StorageError(Exception):
    pass


def _safe_key(key):
    """საცავის გასაღები მხოლოდ წინ მიმავალი ბილიკი უნდა იყოს."""
    key = (key or "").replace("\\", "/").lstrip("/")
    if not key or ".." in key.split("/"):
        raise StorageError(f"დაუშვებელი გასაღები: {key!r}")
    return key


class BaseStorage:
    backend = "base"

    def save(self, key, data, mime=None):
        raise NotImplementedError

    def read(self, key):
        raise NotImplementedError

    def delete(self, key):
        raise NotImplementedError

    def exists(self, key):
        raise NotImplementedError

    def public_url(self, key):
        """პირდაპირი CDN-მისამართი, ან None — მაშინ ფაილს Flask გასცემს."""
        return None


class LocalStorage(BaseStorage):
    """ფაილები დისკზე. პროდაქშენში ეს ბილიკი persistent volume-ზე უნდა იყოს."""

    backend = "local"

    def __init__(self, root):
        self.root = os.path.abspath(root)

    def path(self, key):
        return os.path.join(self.root, _safe_key(key).replace("/", os.sep))

    def save(self, key, data, mime=None):
        p = self.path(key)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".part"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, p)  # ატომური: ნახევრად ჩაწერილი ფაილი არასდროს გაიცემა

    def read(self, key):
        with open(self.path(key), "rb") as f:
            return f.read()

    def delete(self, key):
        try:
            os.remove(self.path(key))
        except FileNotFoundError:
            pass

    def exists(self, key):
        return os.path.exists(self.path(key))

    def usage_bytes(self):
        total = 0
        for dirpath, _dirs, files in os.walk(self.root):
            for name in files:
                try:
                    total += os.path.getsize(os.path.join(dirpath, name))
                except OSError:
                    pass
        return total

    def free_bytes(self):
        try:
            return shutil.disk_usage(self.root).free
        except OSError:
            return None


class S3Storage(BaseStorage):
    """Cloudflare R2 ან სხვა S3-თავსებადი საცავი. boto3 იტვირთება მხოლოდ საჭიროებისას."""

    backend = "r2"

    def __init__(self, bucket, endpoint_url, access_key, secret_key,
                 public_base=None, region="auto"):
        if not bucket:
            raise StorageError("MEDIA_R2_BUCKET არ არის მითითებული.")
        self.bucket = bucket
        self.public_base = (public_base or "").rstrip("/") or None
        self._config = {
            "endpoint_url": endpoint_url,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "region_name": region,
        }
        self._cached_client = None

    @property
    def _client(self):
        """boto3 მხოლოდ მაშინ იტვირთება, როცა ნამდვილად ვწერთ ან ვკითხულობთ.

        CDN-ის რეჟიმში (MEDIA_PUBLIC_BASE მითითებულია) გვერდები მხოლოდ
        მისამართებს აგებენ, ანუ web-პროცესს boto3 საერთოდ არ სჭირდება.
        """
        if self._cached_client is not None:
            return self._cached_client
        if not all(self._config[k] for k in
                   ("endpoint_url", "aws_access_key_id", "aws_secret_access_key")):
            raise StorageError(
                "R2 კონფიგურაცია არასრულია: საჭიროა MEDIA_R2_ENDPOINT, "
                "MEDIA_R2_ACCESS_KEY და MEDIA_R2_SECRET_KEY."
            )
        try:
            import boto3  # noqa: WPS433 — განზრახ ლოკალური იმპორტი
        except ImportError as exc:  # pragma: no cover
            raise StorageError("boto3 არ არის დაყენებული (pip install boto3)") from exc
        self._cached_client = boto3.client("s3", **self._config)
        return self._cached_client

    def save(self, key, data, mime="application/octet-stream"):
        self._client.put_object(
            Bucket=self.bucket, Key=_safe_key(key), Body=data,
            ContentType=mime, CacheControl="public, max-age=31536000, immutable",
        )

    def read(self, key):
        obj = self._client.get_object(Bucket=self.bucket, Key=_safe_key(key))
        return obj["Body"].read()

    def delete(self, key):
        self._client.delete_object(Bucket=self.bucket, Key=_safe_key(key))

    def exists(self, key):
        from botocore.exceptions import ClientError
        try:
            self._client.head_object(Bucket=self.bucket, Key=_safe_key(key))
            return True
        except ClientError:
            return False

    def public_url(self, key):
        if not self.public_base:
            return None
        return f"{self.public_base}/{_safe_key(key)}"


def build_storage(config):
    """კონფიგურაციიდან საცავის აწყობა."""
    backend = (config.get("MEDIA_BACKEND") or "local").lower()
    if backend in ("r2", "s3"):
        return S3Storage(
            bucket=config.get("MEDIA_R2_BUCKET"),
            endpoint_url=config.get("MEDIA_R2_ENDPOINT"),
            access_key=config.get("MEDIA_R2_ACCESS_KEY"),
            secret_key=config.get("MEDIA_R2_SECRET_KEY"),
            public_base=config.get("MEDIA_PUBLIC_BASE"),
        )
    return LocalStorage(config.get("MEDIA_ROOT"))


def get_storage(app=None):
    """აპლიკაციაზე მიბმული საცავი (ერთხელ იქმნება)."""
    from flask import current_app
    app = app or current_app
    storage = app.extensions.get("medialib_storage")
    if storage is None:
        storage = build_storage(app.config)
        app.extensions["medialib_storage"] = storage
    return storage


def check_media_root(app):
    """გაფრთხილება ყველაზე მზაკვრულ შეცდომაზე: ატვირთვა კონტეინერის დროებით დისკზე.

    თუ MEDIA_ROOT პროექტის საქაღალდეშია და გარემო პროდაქშენია, ატვირთული ფაილი
    შემდეგ deploy-ზე ჩუმად გაქრება. ეს ერთადერთი შემთხვევაა, როცა CMS „მუშაობს",
    სანამ არ მუშაობს, ამიტომ ხმამაღლა ვწერთ ლოგში.
    """
    if (app.config.get("MEDIA_BACKEND") or "local").lower() != "local":
        return
    root = os.path.abspath(app.config.get("MEDIA_ROOT") or "")
    base = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    inside_repo = root.startswith(base + os.sep) or root == base
    # მხოლოდ Railway-ის ცვლადებზე ვრეაგირებთ: PORT ლოკალურ გარემოშიც არსებობს
    # და გაფრთხილება ყოველ გაშვებაზე ცრუდ ჩნდებოდა
    is_prod = bool(
        os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("RAILWAY_PROJECT_ID")
        or os.environ.get("RAILWAY_SERVICE_ID")
    )
    if inside_repo and is_prod:
        app.logger.error(
            "MEDIA_ROOT (%s) პროექტის საქაღალდეშია და გარემო პროდაქშენს ჰგავს. "
            "ატვირთული ფაილები შემდეგ deploy-ზე წაიშლება. დააყენეთ persistent volume "
            "(მაგ. MEDIA_ROOT=/data/media) ან MEDIA_BACKEND=r2.", root,
        )
    os.makedirs(root, exist_ok=True)
