# ყოველდღიური ავტომ. განახლება — Movie World

ge.movie **Cloudflare-ის უკანაა**, ამიტ სერვერი თვითონ ვერ ამოწმებს (403).
scrape ერთხელ ხდება ბრაუზერში (შენ გადიხარ Cloudflare-ს), დანარჩენი — ავტომატურია.

## შენი ყოველდღიური რუტინა (1 ნაბიჯი, ~2 წთ)

1. გახსენი **https://ge.movie** ბრაუზერში (გაატარე Cloudflare თუ სთხოვს).
2. დააჭირე **bookmarklet-ს** „GE Daily" (იხ. დაყენება ქვემოთ).
   → ~2 წთ-ში ავტომ. ჩამოიტვირთება `ge_movies_daily.json` Downloads-ში.

სულ ეს არის. დანარჩენს კომპიუტერი თვითონ აკეთებს:

- **Windows Scheduled Task „MovieWorld Daily Update"** ყოველ დღე **10:00**-ზე ეშვება,
  პოულობს Downloads-ში უახლეს `ge_movies*.json`-ს და აიმპორტებს **მხოლოდ ახალ** ფილმებს
  (`update.py`). არსებული ფილმები არ მრავლდება, არაფერი იშლება.
- შედეგი იწერება `data/update.log`-ში (რამდენი ახალი დაემატა).

> რჩევა: scrape გააკეთე **10:00-მდე**, რომ იმავე დღეს აიმპორტდეს. თუ გამოგრჩა —
> მეორე დღეს ავტომ. აიმპორტდება (ან ხელით: ორმაგი დაწკაპ. `run_update.bat`-ზე).

## bookmarklet-ის დაყენება (ერთხელ)

1. ბრაუზერში დააჭირე ⭐ (bookmark დამატება) ნებისმიერ გვერდზე.
2. სახელი: **GE Daily**
3. URL/მისამართის ველში ჩასვი **მთელი შიგთავსი** ფაილიდან:
   `scrapers/bookmarklet.txt` (იწყება `javascript:`-ით).
4. შეინახე. ახლა ge.movie-ზე ყოფნისას ერთი დაწკაპუნებით ეშვება scrape.

## ხელით გაშვება (bookmarklet-ის გარეშე)

scrape: ge.movie Console-ში (F12) ჩასვი `scrapers/04_daily.js`-ის შიგთავსი, Enter.
იმპორტი: ორმაგი დაწკაპ. `run_update.bat` (ან `.venv\Scripts\python.exe update.py`).

## პარამეტრები

- **დროის შეცვლა:** `schtasks /Change /TN "MovieWorld Daily Update" /ST 14:00`
- **გამორთვა:** `schtasks /Delete /TN "MovieWorld Daily Update" /F`
- **რამდენ ID-ს ამოწმებს:** `04_daily.js`-ში `LIMIT = 400` (გაზარდე თუ დიდხანს არ გიგუშვია).
