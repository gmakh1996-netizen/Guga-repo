# GEMOVIE — ფილმების კატალოგი

ლეგალური ფილმების კატალოგი: **Flask + SQLite + TMDB**.
ინახავს მხოლოდ მეტამონაცემებს (პოსტერი, აღწერა, რეიტინგი, ტრეილერი). ვიდეო-ფაილებს **არ** ჰოსტავს.

---

## 1. გაშვება

```bash
# ვირტუალური გარემო
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# დამოკიდებულებები
pip install -r requirements.txt

# კონფიგი — დააკოპირეთ და ჩაწერეთ TMDB გასაღები
copy .env.example .env         # Windows
# cp .env.example .env         # macOS / Linux
```

`.env`-ში ჩაწერეთ თქვენი გასაღები:
```
TMDB_API_KEY=თქვენი_v3_გასაღები
```
> გასაღები უფასოა: https://www.themoviedb.org/settings/api → "API Key (v3 auth)".

## 2. ბაზის შევსება (პირველი გაშვება)

```bash
python sync.py
```
ეს ავსებს ბაზას პოპულარული/ტრენდული ფილმებით TMDB-დან.

## 3. საიტის გაშვება

```bash
python app.py
```
გახსენით http://127.0.0.1:5000

---

## ავტომატური განახლება

**ორი გზა — რომელიც მოგწონთ:**

1. **ჩაშენებული (მარტივი):** `app.py` თავად უშვებს სინქრონიზაციას ყოველ ღამე 03:00-ზე
   (APScheduler). სანამ საიტი მუშაობს, ფილმები თავისით ახლდება.

2. **Cron / Task Scheduler (საიმედო):** დააყენეთ სისტემური განრიგი, რომელიც ყოველ ღამე უშვებს:
   ```bash
   python sync.py
   ```
   - **Windows:** Task Scheduler → ახალი დავალება → ყოველდღიური → Action: `python C:\...\sync.py`
   - **Linux:** `crontab -e` → `0 3 * * * cd /path && .venv/bin/python sync.py`

---

## სტრუქტურა

```
app.py          — Flask აპი, routes (მთავარი, დეტალი, ჟანრი, ძებნა)
tmdb.py         — TMDB API კლიენტი (ერთადერთი გარე წყარო)
sync.py         — ავტომატური სინქრონიზაცია ბაზაში
models.py       — SQLAlchemy მოდელები (Movie, Genre)
config.py       — კონფიგი (.env-იდან)
templates/      — Jinja2 შაბლონები
static/css/     — დიზაინი
```

## შემდეგი ნაბიჯები (თქვენ)
- მომხმარებლის ავტორიზაცია + რჩეულები/სანახავი სია
- სერიალების დამატება (TMDB `/tv` ენდპოინტები)
- SQLite → Postgres (მხოლოდ `DATABASE_URL` იცვლება)
```
