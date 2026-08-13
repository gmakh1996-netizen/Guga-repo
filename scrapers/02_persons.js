/* ge.movie — მსახიობების ამომღები. გაუშვი ge.movie-ს Console-ში.
   გამონატანი: persons.json  ->  პროექტში data/persons.json
   იმპორტი:   python import_persons.py                                      */
(async () => {
  const log = (...a) => console.log('%c[GE-persons]', 'color:#e50914;font-weight:bold', ...a);
  const F = async (u, ms = 25000) => { const c = new AbortController(), t = setTimeout(() => c.abort(), ms);
    try { const r = await fetch(u, { credentials: 'include', signal: c.signal }); return await r.text(); }
    catch (e) { return ''; } finally { clearTimeout(t); } };
  async function sm(u, acc) { const x = await F(u); for (const m of x.matchAll(/<loc>([^<]+)<\/loc>/g)) { const l = m[1].trim(); if (/\.xml$/i.test(l)) await sm(l, acc); else acc.push(l); } }
  const urls = []; await sm('https://ge.movie/persons_sitemap.xml', urls);
  const pages = [...new Set(urls)].filter(u => /\/person\/\d+/.test(u));
  log('სულ მსახიობი:', pages.length);
  function parse(html, url) {
    const d = new DOMParser().parseFromString(html, 'text/html');
    const og = k => d.querySelector(`meta[property="og:${k}"],meta[name="${k}"]`)?.content || '';
    let name = (d.querySelector('h1')?.innerText || og('title') || '').replace(/\s*[-|].*GE\.?MOVIE.*$/i, '').trim();
    let photo = ''; for (const s of d.querySelectorAll('script[type="application/ld+json"]')) { try { const j = JSON.parse(s.textContent); if (j.image) photo = j.image; if (j.name && !name) name = j.name; } catch (e) {} }
    photo = photo || og('image');
    const id = (url.match(/\/person\/(\d+)/) || [])[1];
    return { id: id ? +id : null, name, photo, url };
  }
  const out = []; let i = 0, done = 0; window.__P = out;
  window.__dlP = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(out)], { type: 'application/json' })); a.download = 'persons.json'; a.click(); };
  async function worker() { while (i < pages.length) { const u = pages[i++]; const h = await F(u); if (h) { try { const e = parse(h, u); if (e.name) out.push(e); } catch (_) {} } if (++done % 50 === 0) log(done + '/' + pages.length + ' (' + out.length + ' ok)'); if (done % 1500 === 0) window.__dlP(); } }
  await Promise.all(Array.from({ length: 6 }, worker));
  log('%cდასრულდა! ' + out.length + ' მსახიობი', 'color:#0f0;font-size:15px');
  window.__dlP();
})();
