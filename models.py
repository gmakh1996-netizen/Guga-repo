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
