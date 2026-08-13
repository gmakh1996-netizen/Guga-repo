/* ge.movie — ყოველდღიური „მხოლოდ ახლების" ამომღები.
   განსხვავება 01_movies.js-გან: არ იღებს მთელ 10k კატალოგს — მხოლოდ
   ყველაზე ახალ ~LIMIT ID-ს (ge.movie ახალ ფილმს ახალ ID-ს აძლევს).
   სწრაფია (~1-2 წთ). გაუშვი ge.movie-ს Console-ში (ან bookmarklet-ით).

   გამონატანი: ge_movies_daily.json  ->  Downloads
   იმპორტი ავტომ.: Scheduled Task → update.py  (მხოლოდ ახალი დაემატება).  */
(async () => {
  const LIMIT = 400; // რამდენ უახლეს ID-ს შევამოწმოთ (გაზარდე თუ დიდი ხნით არ გიგუშვია)
  const log = (...a) => console.log('%c[GE-daily]', 'color:#32e3e3;font-weight:bold', ...a);
  const F = async (u, ms = 25000) => { const c = new AbortController(), t = setTimeout(() => c.abort(), ms);
    try { const r = await fetch(u, { credentials: 'include', signal: c.signal }); return await r.text(); }
    catch (e) { return ''; } finally { clearTimeout(t); } };
  const un = s => (s || '').replace(/\\\//g, '/');

  async function collectSitemap(u, acc) {
    const xml = await F(u);
    for (const m of xml.matchAll(/<loc>([^<]+)<\/loc>/g)) { const l = m[1].trim(); if (/\.xml$/i.test(l)) await collectSitemap(l, acc); else acc.push(l); }
  }
  log('sitemaps იკითხება...');
  const urls = [];
  await collectSitemap('https://ge.movie/movie_sitemap.xml', urls);
  await collectSitemap('https://ge.movie/serial_sitemap.xml', urls);
  const idOf = u => { const m = u.match(/\/(?:movie|serial)\/(\d+)/); return m ? +m[1] : 0; };
  // ყველაზე ახალი ID-ები წინ (კლებადობით), ვიღებთ მხოლოდ ზედა LIMIT-ს
  const pages = [...new Set(urls)].filter(u => /\/(movie|serial)\/\d+/.test(u))
    .sort((a, b) => idOf(b) - idOf(a)).slice(0, LIMIT);
  log('ვამოწმებ უახლეს', pages.length, 'გვერდს (ID', idOf(pages[pages.length - 1]), '–', idOf(pages[0]) + ')');

  function parsePage(html, url) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const type = url.includes('/serial/') ? 'series' : 'movie';
    const cwS = [...doc.querySelectorAll('script')].map(s => s.textContent).find(t => /var\s+CW\s*=/.test(t)) || '';
    const g = re => { const m = cwS.match(re); return m ? m[1] : ''; };
    const title_ge = g(/title_ge:\s*"([^"]*)"/), title_en = g(/title_en:\s*"([^"]*)"/);
    let year = g(/year:\s*"([^"]*)"/), imdb = g(/imdb:\s*"([^"]*)"/), thumb = un(g(/thumb:\s*"([^"]*)"/));
    let genre = [], desc = '', image = '', name = '';
    let director = [], cast = [], country = [], studio = [], runtime = '';
    const persons = v => [].concat(v || []).map(p => (typeof p === 'string' ? p : (p && p.name) || '')).filter(Boolean);
    const named = v => [].concat(v || []).map(c => (typeof c === 'string' ? c : (c && c.name) || '')).filter(Boolean);
    for (const s of doc.querySelectorAll('script[type="application/ld+json"]')) {
      try { const j = JSON.parse(s.textContent); if (j.genre) genre = [].concat(j.genre);
        desc = j.description || desc; image = j.image || image; name = j.name || name;
        if (j.director) director = director.concat(persons(j.director));
        if (j.actor) cast = cast.concat(persons(j.actor));
        if (j.countryOfOrigin) country = country.concat(named(j.countryOfOrigin));
        if (j.productionCompany) studio = studio.concat(named(j.productionCompany));
        if (!runtime && j.duration) { const d = String(j.duration).match(/PT(?:(\d+)H)?(?:(\d+)M)?/); if (d) runtime = String((+d[1] || 0) * 60 + (+d[2] || 0)); }
        if (!year && j.datePublished) year = (j.datePublished.match(/\d{4}/) || [''])[0]; } catch (e) {}
    }
    const cwArr = re => { const m = cwS.match(re); if (!m) return []; try { return JSON.parse('[' + m[1] + ']').flat().map(x => (x && x.name) || x).filter(Boolean); } catch (e) { return []; } };
    if (!studio.length) studio = cwArr(/studio:\s*(\[[^\]]*\])/);
    if (!country.length) country = cwArr(/country:\s*(\[[^\]]*\])/);
    if (!director.length) director = cwArr(/director:\s*(\[[^\]]*\])/);
    if (!runtime) runtime = g(/(?:runtime|duration):\s*"?(\d+)"?/);
    const og = k => doc.querySelector(`meta[property="og:${k}"],meta[name="${k}"]`)?.content || '';
    desc = desc || og('description'); image = image || og('image');
    const ifr = doc.querySelector('#movie_embed,#serial_embed,.movies-full__player iframe,#player iframe');
    const player = ifr ? (ifr.getAttribute('src') || ifr.getAttribute('data-src') || '') : '';
    const title = (title_ge || name || '').replace(/\s+/g, ' ').trim();

    const dirSet = new Set(director.map(d => (d || '').split(',')[0].trim()));
    const castObjs = [], seenC = new Set();
    for (const a of doc.querySelectorAll('a[href*="/person/"]')) {
      const img = a.querySelector('img');
      let nm = (a.getAttribute('title') || (img && img.getAttribute('alt')) || a.textContent || '')
        .replace(/\s+/g, ' ').trim().split(',')[0].split(' / ')[0].trim();
      if (!nm || nm.length > 60 || seenC.has(nm) || dirSet.has(nm)) continue;
      seenC.add(nm);
      let photo = img ? un(img.getAttribute('src') || img.getAttribute('data-src') || '') : '';
      if (photo && photo.startsWith('//')) photo = 'https:' + photo;
      if (photo && /512\.png|no-?photo|placeholder/i.test(photo)) photo = '';
      castObjs.push({ name: nm, photo: photo || null });
    }
    const castFinal = (castObjs.length ? castObjs
      : [...new Set(cast)].map(n => ({ name: n, photo: null }))).slice(0, 25);

    const money = re => { const m = (cwS.match(re) || (doc.body ? doc.body.textContent : '').match(re)); return m ? m[1].replace(/[,\s$]/g, '') : ''; };
    const budget = money(/(?:budget|ბიუჯეტი)[^\d$]*\$?\s*([\d][\d,\s]{3,})/i);
    const revenue = money(/(?:revenue|შემოსავალი)[^\d$]*\$?\s*([\d][\d,\s]{3,})/i);

    return { title, title_en, type, year, rating: imdb, genre: genre.join(' / '), description: (desc || '').trim(), poster: image || thumb, player, url,
      director: [...new Set(director)].join(', '), studio: [...new Set(studio)].join(', '), country: [...new Set(country)].join(', '),
      runtime, budget, revenue, cast: castFinal };
  }

  const results = []; let done = 0, i = 0;
  window.__GE = results;
  window.__downloadGE = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(results)], { type: 'application/json' })); a.download = 'ge_movies_daily.json'; a.click(); };
  async function worker() { while (i < pages.length) { const u = pages[i++]; const html = await F(u);
    if (html) { try { const e = parsePage(html, u); if (e.title) results.push(e); } catch (err) {} }
    if (++done % 50 === 0) log(done + '/' + pages.length + ' (' + results.length + ' ok)'); } }
  await Promise.all(Array.from({ length: 6 }, worker));
  log('%cდასრულდა! ' + results.length + ' ჩანაწერი — ge_movies_daily.json ჩამოიტვირთა', 'color:#0f0;font-size:16px');
  window.__downloadGE();
})();
