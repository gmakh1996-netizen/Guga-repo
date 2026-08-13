# ge.movie scrapers

ge.movie Cloudflare-ის უკანაა — სერვერიდან პირდაპირ **ვერ** ჩამოიტვირთება (403).
ამიტომ ეს სკრიპტები უნდა გაეშვას **ბრაუზერის Console-ში**, ge.movie-ზე, სადაც
მომხმარებელი უკვე გავლილია Cloudflare challenge-ს (human-in-the-loop).

## როგორ გავუშვათ
1. გახსენი https://ge.movie და გაიარე Cloudflare challenge (დაელოდე გვერდის ჩატვირთვას).
2. F12 → Console.
3. ჩააკოპირე შესაბამისი `.js` ფაილის შიგთავსი და გაუშვი.
4. დაელოდე „დასრულდა!" შეტყობინებას — ავტომატურად ჩამოიტვირთება JSON.
   (თუ დაბლოკა multiple-download, გამოჩნდება წითელი ღილაკი — დააჭირე მას.)
5. ჩამოტვირთული JSON გადმოიტანე `data/`-ში და გაუშვი შესაბამისი import სკრიპტი.

## ფაილები
| სკრიპტი | გამონატანი | იმპორტი |
|---|---|---|
| `01_movies.js`   | `ge_movies.json` → `data/movies.json`   | `python import_streams.py data/movies.json` |
| `02_persons.js`  | `persons.json` → `data/persons.json`     | `python import_persons.py` |
| `03_trailers.js` | `trailers.json` → `data/trailers.json`   | `python import_trailers.py` |

## შენიშვნა
- `data/browser_state.json` — ge.movie-ს სესიის ქუქიები (ci_session). Cloudflare-ს ვერ ვცდით
  ავტომატურად — ესეც მხოლოდ ბრაუზერის სესიისთვისაა.
- სურათები/პოსტერები TMDB/static.moviege CDN-ზეა (Cloudflare-ს გარეშე) — ეს პირდაპირ იტვირთება.
- ge.movie-ს **პორტრეტული პოსტერი** JS-ით ისმება, სტატიკურ HTML-ში არაა — ამ scrape-ში ვერ ხვდება
  (ამიტომ ბარ/ ბარათებში landscape backdrop გამოიყენება).
