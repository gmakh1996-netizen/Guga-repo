# GEMOVIE — პროექტის გზამკვლევი (Claude, წაიკითხე ეს ჯერ)

ქართული ფილმების/სერიალების საიტი, **მთლიანად ge.movie-ს მიხედვით** (დიზაინი, კატეგორიები,
ფლეერი, მონაცემი). TMDB **აღარ გამოიყენება** — ყველაფერი ge.movie-დანაა.

- **სამუშაო საქაღალdე:** `C:\Users\Asus\Desktop\gemovie-build` (ყველა ფაილი აქ არის — Downloads აღარ სჭირდება)
- **სტეკი:** Python + Flask + SQLAlchemy + SQLite (`gemovie.db`). Frontend — ge.movie-ს CSS/JS თემა + AJAX.
- **ვირტ. გარემო:** `.venv` (Windows). Python: `.venv/Scripts/python.exe`

## გაშვება
```bash
.venv/Scripts/python.exe app.py      # → http://127.0.0.1:5000
```
launch.json-ში კონფიგი ჰქვია **"GEMOVIE (Flask)"** (fluentra-build-ის .claude/launch.json-შია).
ტესტისას ქართული ტექსტისთვის: `PYTHONIOENCODING=utf-8`.

## რა არის უკვე გაკეთებული
- ge.movie-ს სრული კატალოგი დაskреიპილი და ბაზაშია: **~10 100 ფილმი + ~1 275 სერიალი**,
  ~11 400 ფლეერი, ~24 ჟანრი, **1 000 მსახიობი**, **11 388 თრეილერი**.
- ge.movie-ს **დიზაინი ატანილია** (გვერდითი მენიუ, header, ფერები/ფონტები — FiraGO).
- **მთავარი გვერდი:** ჰერო = მარცხნივ დიდი ფილმი + მარჯვნივ 3×3 ესკიზების ბადე (ge.movie-ვით),
  ქვემოთ AJAX რიგები (ტრენდში/ახლახან/სერიალები/მაღალი რეიტინგი) აიქონებით.
- **ფილტრი/დათვალიერება** (`/browse`, `/filter-movies`): 5-სვეტიანი landscape ბადე,
  ფილტრები (კატეგორია/ჟანრი/წელი/დალაგება) + **infinite scroll**, ყველაფერი AJAX-ით.
- **დეტალური გვერდი** (`/movie/<id>`, `/series/<id>`): ge.movie-ს დიზაინი — მარცხნივ პოსტერი +
  თრეილერის ღილაკი, მარჯვნივ ფლეერი; ქვემოთ სათაური + ORIGINAL (caps) + სამოქმ. ღილაკები
  (♥/მოგვ./შეტყ./დახმარება), IMDb + ვარსკვლავები, ინფო-სია (ჟანრი/სტუდია/წელი/რეჟისორი/ხანგრძ./
  ქვეყანა — ცარიელი ველი იმალება), „ფილმის სიუჟეტი", „მსახიობები" (cast-ის არსებობისას) + „მსგავსი".
  **NB:** studio/director/country/runtime/cast მხოლოდ დეტალურ გვერდზეა ge.movie-ზე → საჭიროა
  `01_movies.js`-ის ხელახალი გაშვება, რომ ეს ველები ჩამოიტვირთოს (ld+json-იდან).
- **მსახიობები** (`/persons`): მრგვალფოტოებიანი ბადე, infinite scroll (ფოტოიანები წინ).
- **თრეილერები** (`/browse?type=trailer`): ფილმები თრეილერით; დეტალურზე თრეილერი YouTube-ით უკრავს.

## სტრუქტურა
```
app.py            Flask აპი: გვერდები + JSON API (/api/movies, /api/persons, /api/search)
models.py         Movie, Series, Stream, Genre, Person
import_streams.py ფილმების/სერიალების იმპორტი  →  data/movies.json
import_persons.py მსახიობების იმპორტი          →  data/persons.json
import_trailers.py თრეილერების იმპორტი (trailer_key) → data/trailers.json
config.py, sync.py, tmdb.py   (sync/tmdb ЛEGACY — აღარ გამოიყენება; auto-sync გამორთულია app.py-ში)
templates/        base.html (shell), index.html (ჰერო+რიგები), browse.html (ფილტრი),
                  movie.html (დეტალური), persons.html, _moviecard.html (macro)
static/theme/     ge.movie-ს ნამდვილი თემა (CSS/JS/ფონტები) — ლოკალურად სარკირებული
static/css/ge-custom.css   ჩვენი დამატებითი/გადამფარავი CSS (ge.movie-ს იერზე)
static/js/app.js  frontend: ჰერო, რიგები, ფილტრი+infinite scroll, ძებნა, ბარათები
data/             წყარო-მონაცემი (ქვემოთ)
scrapers/         ge.movie-ს ამომღები Console-სკრიპტები + README (ხელახალი scrape-ისთვის)
archive/          ძველი/გამოუყენებელი seed-ები (kinomigma, sample) — არ გამოიყენება
```

## data/ — წყარო-მონაცემი
| ფაილი | შიგთავსი | იმპორტი |
|---|---|---|
| `data/movies.json`   | ge.movie ფილმები+სერიალები (id, title, title_en, type, year, rating, genre, description, poster, player + **director, studio, country, runtime, cast[]**) | `python import_streams.py` |
| `data/persons.json`  | მსახიობები (id, name „ka / en", photo, url) | `python import_persons.py` |
| `data/trailers.json` | თრეილერები (id, type, trailer=videodb URL с YouTube key) | `python import_trailers.py` |
| `data/browser_state.json` | ge.movie-ს სესიის ქუქიები (მხოლოდ ბრაუზერისთვის) | — |

**ბაზის თავიდან აწყობა:** გაუშვი სამივე import სკრიპტი (თანმიმდევრობა: movies → trailers → persons).

## მონაცემის წყარო (მნიშვნელოვანი)
ge.movie **Cloudflare-ის უკანაა** — სერვერიდან პირდაპირ ვერ ვskреიპავთ (403).
მონაცემი ამოღებულია **ბრაუზერის Console-ში** (მომხმარებელი გადის Cloudflare-ს), `scrapers/`-ის
სკრიპტებით. ბაზა უკვე აწყობილია `data/`-დან; ხელახლა მხოლოდ მაშინ, თუ ge.movie განახლდა.
დეტალები: `scrapers/README.md`.

## ცნობილი შეზღუდვები / დასახვეწი
- **პორტრეტული პოსტერი არ გვაქვ** — ge.movie-ს დეტალურ გვერდზე ის JS-ით ისმება და HTML-ში
  არაა; ჩვენს scrape-ში ვერ მოხვდა. ამიტომ ბარათებში/პოსტერში **landscape backdrop** (16:9) გამოიყენება.
- გარე embed-ფლეერები (videodb.stream, em.filmx.my...) შეიძლcan referer-ს ამოწმებდნენ — localhost-ზე
  ზოგი შეიძლება არ დაუკრას (თრეილერი YouTube-ით საიმედოდ უკრავს).
- სერიალებს ცალკე ეპიზოდების არჩევანი არ აქვთ (თითო serial-ს ერთი embed).
- მსახიობის ბარათზე დაჭერით ფილმოგრაფია ჯერ არ იხსნება (`/person/<id>` გვერდი არ არსებობს).
- გვერდითი მენიუ სტაბილურია ≥768px; მობილურ ვიწრო ეკრანზე ge.movie-ს responsive-ს ვცვლით ge-custom.css-ში.
