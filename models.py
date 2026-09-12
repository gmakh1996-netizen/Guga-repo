"""მონაცემთა ბაზის მოდელები (SQLAlchemy).

აქ ინახება მხოლოდ TMDB-ის მეტამონაცემები (პოსტერი, აღწერა, რეიტინგი და ა.შ.).
ვიდეო-ფაილები არსად ინახება — ეს ლეგალური კატალოგია.
"""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# ფილმი ⇄ ჟანრი (many-to-many)
movie_genres = db.Table(
    "movie_genres",
    db.Column("movie_id", db.Integer, db.ForeignKey("movie.id"), primary_key=True),
    db.Column("genre_id", db.Integer, db.ForeignKey("genre.id"), primary_key=True),
)

# სერიალი ⇄ ჟანრი (many-to-many)
series_genres = db.Table(
    "series_genres",
    db.Column("series_id", db.Integer, db.ForeignKey("series.id"), primary_key=True),
    db.Column("genre_id", db.Integer, db.ForeignKey("genre.id"), primary_key=True),
)


class Genre(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # TMDB genre id
    name = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f"<Genre {self.name}>"


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # TMDB movie id
    title = db.Column(db.String(300), nullable=False)
    original_title = db.Column(db.String(300))
    overview = db.Column(db.Text)
    tagline = db.Column(db.String(400))

    poster_path = db.Column(db.String(200))
    poster_url = db.Column(db.String(400))  # landscape backdrop
    poster_portrait = db.Column(db.String(400))  # პორტრეტ-პოსტერი (ge.movie card)
    backdrop_path = db.Column(db.String(200))

    release_date = db.Column(db.String(20))  # "2023-07-19"
    runtime = db.Column(db.Integer)
    vote_average = db.Column(db.Float, default=0.0)
    vote_count = db.Column(db.Integer, default=0)
    popularity = db.Column(db.Float, default=0.0)

    trailer_key = db.Column(db.String(50))  # YouTube key
    imdb_id = db.Column(db.String(20))

    # ge.movie-ს დეტალური გვერდის მდიდარი მეტამონაცემი
    director = db.Column(db.String(300))     # რეჟისორ(ებ)ი
    studio = db.Column(db.String(300))       # სტუდია / პროდიუსერი
    country = db.Column(db.String(300))      # ქვეყანა
    budget = db.Column(db.BigInteger)        # ბიუჯეტი ($)
    revenue = db.Column(db.BigInteger)       # შემოსავალი ($)
    cast_json = db.Column(db.Text)           # მსახიობები — JSON სია [{name, photo}]

    added_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    genres = db.relationship(
        "Genre", secondary=movie_genres, backref=db.backref("movies", lazy="dynamic")
    )

    streams = db.relationship(
        "Stream", backref="movie", cascade="all, delete-orphan", lazy="select"
    )

    media_type = "movie"

    @property
    def year(self):
        return self.release_date[:4] if self.release_date else ""

    @property
    def rating(self):
        return round(self.vote_average, 1) if self.vote_average else 0

    @property
    def cast(self):
        """მსახიობთა სახელების სია (cast_json-იდან)."""
        if not self.cast_json:
            return []
        try:
            import json as _json
            data = _json.loads(self.cast_json)
            return data if isinstance(data, list) else []
        except (ValueError, TypeError):
            return []

    def __repr__(self):
        return f"<Movie {self.title} ({self.year})>"


class Series(db.Model):
    """სერიალი (TV). სტრუქტურულად ფილმის მსგავსი, TMDB /tv ენდპოინტებიდან."""
    id = db.Column(db.Integer, primary_key=True)  # TMDB tv id
    title = db.Column(db.String(300), nullable=False)  # name
    original_title = db.Column(db.String(300))
    overview = db.Column(db.Text)
    tagline = db.Column(db.String(400))

    poster_path = db.Column(db.String(200))
    poster_url = db.Column(db.String(400))
    poster_portrait = db.Column(db.String(400))
    backdrop_path = db.Column(db.String(200))

    release_date = db.Column(db.String(20))  # first_air_date
    runtime = db.Column(db.Integer)          # ეპიზოდის ხანგრძლივობა (წთ)
    number_of_seasons = db.Column(db.Integer)
    number_of_episodes = db.Column(db.Integer)
    vote_average = db.Column(db.Float, default=0.0)
    vote_count = db.Column(db.Integer, default=0)
    popularity = db.Column(db.Float, default=0.0)

    trailer_key = db.Column(db.String(50))

    # ge.movie-ს დეტალური გვერდის მდიდარი მეტამონაცემი
    director = db.Column(db.String(300))
    studio = db.Column(db.String(300))
    country = db.Column(db.String(300))
    budget = db.Column(db.BigInteger)
    revenue = db.Column(db.BigInteger)
    cast_json = db.Column(db.Text)

    added_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    genres = db.relationship(
        "Genre", secondary=series_genres, backref=db.backref("series", lazy="dynamic")
    )
    streams = db.relationship(
        "Stream", backref="series", cascade="all, delete-orphan", lazy="select"
    )

    media_type = "tv"

    @property
    def year(self):
        return self.release_date[:4] if self.release_date else ""

    @property
    def rating(self):
        return round(self.vote_average, 1) if self.vote_average else 0

    @property
    def cast(self):
        if not self.cast_json:
            return []
        try:
            import json as _json
            data = _json.loads(self.cast_json)
            return data if isinstance(data, list) else []
        except (ValueError, TypeError):
            return []

    def __repr__(self):
        return f"<Series {self.title} ({self.year})>"


class Stream(db.Model):
    """ვიდეო-წყარო ფილმზე. kind: 'embed' | 'mp4' | 'hls'.

    URL-ის წყარო თავად უნდა იყოს ლეგალური (public-domain, საკუთარი/ლიცენზირებული,
    ან ლეგალური embed). ცხრილი მხოლოდ ბმულს ინახავს, არა ვიდეო-ფაილს.
    """
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey("movie.id"), nullable=True, index=True)
    series_id = db.Column(db.Integer, db.ForeignKey("series.id"), nullable=True, index=True)
    language = db.Column(db.String(10))          # 'ka' | 'ru' | 'en' ...
    label = db.Column(db.String(60))             # ღილაკზე ჩვენებადი წარწერა
    kind = db.Column(db.String(10), default="embed")  # embed | mp4 | hls
    url = db.Column(db.String(600), nullable=False)
    sort = db.Column(db.Integer, default=0)
    episode = db.Column(db.Integer, nullable=True, index=True)  # NULL = ერთეპიზოდიანი (ფილმი); 1,2,3... = სერიის ეპიზოდი

    def __repr__(self):
        return f"<Stream {self.label} ({self.kind})>"


class Person(db.Model):
    """მსახიობი/რეჟისორი — ge.movie-ს /person/<id>-დან."""
    id = db.Column(db.Integer, primary_key=True)  # ge.movie person id
    name = db.Column(db.String(200), nullable=False)   # ქართული სახელი
    name_en = db.Column(db.String(200))                 # ინგლისური
    photo = db.Column(db.String(400))
    url = db.Column(db.String(400))
    popularity = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f"<Person {self.name}>"


# ---------------------------------------------------------------------------
# ბექოფისი: ადმინები, პარამეტრები, მედია
# ---------------------------------------------------------------------------


class AdminUser(db.Model):
    """ბექოფისის მომხმარებელი. პაროლი მხოლოდ ჰეშად ინახება."""
    __tablename__ = "admin_user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(60), nullable=False, unique=True, index=True)
    email = db.Column(db.String(200))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="owner")  # owner|editor|moderator
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, raw):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, raw)

    @property
    def is_owner(self):
        return self.role == "owner"

    def __repr__(self):
        return f"<AdminUser {self.username} ({self.role})>"


class Setting(db.Model):
    """საიტის პარამეტრი. მნიშვნელობა JSON-ად, რომ ტიპი არ დაიკარგოს."""
    __tablename__ = "setting"

    key = db.Column(db.String(80), primary_key=True)
    value_json = db.Column(db.Text)
    group = db.Column(db.String(30), default="general")
    updated_by = db.Column(db.Integer, db.ForeignKey("admin_user.id"))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self):
        return f"<Setting {self.key}>"


class MediaAsset(db.Model):
    """ერთი ჩანაწერი = ერთი ატვირთული/ჩამოტვირთული ფაილი.

    ფაილი თვითონ საცავშია (ლოკალური საქაღალდე ან S3/R2), აქ მხოლოდ მეტამონაცემია.
    `sha256` უნიკალურია — ერთი და იგივე ფაილი ორჯერ არ ინახება.
    """
    __tablename__ = "media_asset"

    id = db.Column(db.Integer, primary_key=True)
    sha256 = db.Column(db.String(64), nullable=False, unique=True, index=True)
    storage_backend = db.Column(db.String(16), nullable=False, default="local")
    storage_key = db.Column(db.String(255), nullable=False)
    mime = db.Column(db.String(64), nullable=False)
    ext = db.Column(db.String(8), nullable=False)
    width = db.Column(db.Integer, nullable=False, default=0)
    height = db.Column(db.Integer, nullable=False, default=0)
    bytes = db.Column(db.Integer, nullable=False, default=0)
    has_alpha = db.Column(db.Boolean, nullable=False, default=False)

    source = db.Column(db.String(16), nullable=False, default="upload")  # upload|mirror|seed
    source_url = db.Column(db.String(600))
    original_filename = db.Column(db.String(255))
    alt_text = db.Column(db.String(300))

    uploaded_by = db.Column(db.Integer, db.ForeignKey("admin_user.id"))
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False, index=True)
    deleted_at = db.Column(db.DateTime)

    variants = db.relationship(
        "MediaVariant", backref="asset", cascade="all, delete-orphan", lazy="select"
    )
    links = db.relationship(
        "MediaLink", backref="asset", cascade="all, delete-orphan", lazy="select"
    )

    @property
    def sha8(self):
        return self.sha256[:8]

    def variant(self, name, fmt=None):
        """კონკრეტული წარმოებული ზომა; fmt=None → პირველი ნაპოვნი."""
        for v in self.variants:
            if v.name == name and (fmt is None or v.fmt == fmt):
                return v
        return None

    def __repr__(self):
        return f"<MediaAsset {self.id} {self.original_filename}>"


class MediaVariant(db.Model):
    """ერთი ორიგინალიდან წარმოებული ზომა/ფორმატი (webp 640w, png 128h და ა.შ.)."""
    __tablename__ = "media_variant"

    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(
        db.Integer, db.ForeignKey("media_asset.id"), nullable=False, index=True
    )
    name = db.Column(db.String(24), nullable=False)   # c320 | b1280 | logo_h128 | ico ...
    fmt = db.Column(db.String(8), nullable=False)     # webp | jpg | png | ico
    storage_key = db.Column(db.String(255), nullable=False)
    width = db.Column(db.Integer, nullable=False, default=0)
    height = db.Column(db.Integer, nullable=False, default=0)
    bytes = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint("asset_id", "name", "fmt", name="uq_variant"),
    )

    def __repr__(self):
        return f"<MediaVariant {self.name}.{self.fmt} of {self.asset_id}>"


class MediaLink(db.Model):
    """ვინ სად იყენებს სურათს: (subject_type, subject_id, role) → asset.

    subject_id = 0 ნიშნავს გლობალურს (საიტის ლოგო, favicon, placeholder და ა.შ.).
    ამით სურათის ველი არცერთ არსებულ ცხრილს არ ემატება და ერთი ფაილი
    შეიძლება რამდენიმე ადგილას იყოს მიბმული.
    """
    __tablename__ = "media_link"

    id = db.Column(db.Integer, primary_key=True)
    subject_type = db.Column(db.String(20), nullable=False)  # site|movie|series|person|...
    subject_id = db.Column(db.Integer, nullable=False, default=0)
    role = db.Column(db.String(32), nullable=False)
    asset_id = db.Column(
        db.Integer, db.ForeignKey("media_asset.id"), nullable=False, index=True
    )
    position = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint(
            "subject_type", "subject_id", "role", "position", name="uq_media_link"
        ),
        db.Index("ix_media_link_subject", "subject_type", "subject_id"),
    )

    def __repr__(self):
        return f"<MediaLink {self.subject_type}:{self.subject_id} {self.role}>"


class HomeRow(db.Model):
    """მთავარი გვერდის ერთი რიგი.

    აქამდე 11 რიგი პირდაპირ `templates/index.html`-ში იყო ჩაწერილი და მათი
    შეცვლა deploy-ს მოითხოვდა. ახლა თითოეული ჩანაწერია და ბექოფისიდან იმართება.
    """
    __tablename__ = "home_row"

    id = db.Column(db.Integer, primary_key=True)
    # movies = ჩვეულებრივი რიგი /api/movies-იდან; continue = „განაგრძე ყურება"
    # (ბრაუზერის მეხსიერებიდან); recent_episodes = ბოლოს დამატებული ეპიზოდები
    kind = db.Column(db.String(20), nullable=False, default="movies")
    title = db.Column(db.String(120), nullable=False)
    icon = db.Column(db.String(20), default="film")

    media_type = db.Column(db.String(20), default="movie")   # movie|serial|anime|animation|trailer
    sort_mode = db.Column(db.String(20), default="popularity")
    genre_id = db.Column(db.Integer)
    exclude_genre_id = db.Column(db.Integer)
    layout = db.Column(db.String(20), default="landscape")   # landscape|portrait|top9
    item_limit = db.Column(db.Integer, default=18)

    position = db.Column(db.Integer, nullable=False, default=0, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    # სეზონური რიგი: თარიღები "MM-DD" ფორმატში, წლის გარეშე (ყოველწლიურად მეორდება)
    starts_on = db.Column(db.String(5))
    ends_on = db.Column(db.String(5))

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    items = db.relationship(
        "HomeRowItem", backref="row", cascade="all, delete-orphan",
        order_by="HomeRowItem.position", lazy="select",
    )

    def visible_on(self, today):
        """სეზონურობის შემოწმება. today — datetime.date."""
        if not self.starts_on or not self.ends_on:
            return True
        stamp = "%02d-%02d" % (today.month, today.day)
        if self.starts_on <= self.ends_on:
            return self.starts_on <= stamp <= self.ends_on
        # წლის გადასვლა (მაგ. 12-20 → 01-10)
        return stamp >= self.starts_on or stamp <= self.ends_on

    def __repr__(self):
        return f"<HomeRow {self.position} {self.title}>"


class HomeRowItem(db.Model):
    """კონკრეტული ფილმი/სერიალი კონკრეტულ რიგში, ფიქსირებულ ადგილზე.

    თუ რიგს ასეთი ჩანაწერები აქვს, საიტი ზუსტად მათ აჩვენებს, ამ თანმიმდევრობით.
    თუ არა, რიგი ავტომატურად ივსება (ტრენდში, ახლახან და ა.შ.).
    შაფლი იმავე ცხრილს ავსებს, უბრალოდ შემთხვევითი შერჩევით.
    """
    __tablename__ = "home_row_item"

    id = db.Column(db.Integer, primary_key=True)
    row_id = db.Column(
        db.Integer, db.ForeignKey("home_row.id"), nullable=False, index=True
    )
    media_type = db.Column(db.String(10), nullable=False, default="movie")  # movie|tv
    item_id = db.Column(db.Integer, nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("row_id", "media_type", "item_id", name="uq_home_row_item"),
    )

    def __repr__(self):
        return f"<HomeRowItem row={self.row_id} {self.media_type}:{self.item_id}>"


class MenuItem(db.Model):
    """გვერდითი მენიუს პუნქტი.

    აქამდე 7 პუნქტი `templates/_navbar.html`-ში იყო ჩაწერილი inline SVG-ებით.
    ახლა თითოეული ჩანაწერია: სახელი, მისამართი, აიქონი (ჩაშენებული ნაკრებიდან
    ან ატვირთული სურათი `MediaLink`-ით), თანმიმდევრობა და ხილვადობა.
    """
    __tablename__ = "menu_item"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(60), nullable=False)
    url = db.Column(db.String(300), nullable=False, default="/")
    icon = db.Column(db.String(30), default="film")     # ჩაშენებული აიქონის სახელი
    match = db.Column(db.String(60))                    # რომელ გვერდზე ჩაითვალოს აქტიურად

    position = db.Column(db.Integer, nullable=False, default=0, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    visible_desktop = db.Column(db.Boolean, nullable=False, default=True)
    visible_mobile = db.Column(db.Boolean, nullable=False, default=True)
    new_tab = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<MenuItem {self.position} {self.label}>"


class Job(db.Model):
    """ფონური ამოცანა (სურათების ჩამოტანა, ზომების გადათვლა და ა.შ.).

    პროგრესი ბაზაში იწერება, რომ ბექოფისმა ცოცხლად აჩვენოს და deploy-ის
    ან გადატვირთვის შემდეგ იქიდან გააგრძელოს, სადაც შეწყდა.
    """
    __tablename__ = "job"

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(40), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    # pending | running | done | failed | cancelled

    total = db.Column(db.Integer, default=0)
    done = db.Column(db.Integer, default=0)
    failed = db.Column(db.Integer, default=0)
    skipped = db.Column(db.Integer, default=0)
    bytes_fetched = db.Column(db.BigInteger, default=0)

    params_json = db.Column(db.Text)
    result_json = db.Column(db.Text)
    log_text = db.Column(db.Text)
    cancel_requested = db.Column(db.Boolean, nullable=False, default=False)

    admin_id = db.Column(db.Integer, db.ForeignKey("admin_user.id"))
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)

    @property
    def is_live(self):
        return self.status in ("pending", "running")

    @property
    def percent(self):
        if not self.total:
            return 0
        handled = (self.done or 0) + (self.failed or 0) + (self.skipped or 0)
        return min(100, int(handled * 100 / self.total))

    def __repr__(self):
        return f"<Job {self.id} {self.kind} {self.status}>"


class AuditLog(db.Model):
    """ვინ რა შეცვალა და როდის."""
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admin_user.id"), index=True)
    action = db.Column(db.String(60), nullable=False)
    entity_type = db.Column(db.String(40))
    entity_id = db.Column(db.String(40))
    detail = db.Column(db.Text)
    ip = db.Column(db.String(45))
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.admin_id}>"
