/* ge.movie — თრეილერების ამომღები. გაუშვი ge.movie-ს Console-ში.
   გამონატანი: trailers.json  ->  პროექტში data/trailers.json
   იმპორტი:   python import_trailers.py                                     */
(async () => {
  const log = (...a) => console.log('%c[GE-trailers]', 'color:#e50914;font-weight:bold', ...a);
  const F = async (u, ms = 25000) => { const c = new AbortController(), t = setTimeout(() => c.abort(), ms);
    try { const r = await fetch(u, { credentials: 'include', signal: c.signal }); return await r.text(); }
    catch (e) { return ''; } finally { clearTimeout(t); } };
  async function sm(u, acc) { const x = await F(u); for (const m of x.matchAll(/<loc>([^<]+)<\/loc>/g)) { const l = m[1].trim(); if (/\.xml$/i.test(l)) await sm(l, acc); else acc.push(l); } }
  const urls = []; await sm('https://ge.movie/movie_sitemap.xml', urls); await sm('https://ge.movie/serial_sitemap.xml', urls);
  const pages = [...new Set(urls)].filter(u => /\/(movie|serial)\/\d+/.test(u));
  log('სულ გვერდი:', pages.length);
  const out = []; let i = 0, done = 0; window.__T = out;
  window.__dlT = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(out)], { type: 'application/json' })); a.download = 'trailers.json'; a.click(); };
  function parse(html, url) {
    const d = new DOMParser().parseFromString(html, 'text/html');
    const b = d.querySelector('#triler_popup, .trailer[data-url]');
    const t = b ? b.getAttribute('data-url') : '';
    if (!t) return null;
    const id = (url.match(/\/(?:movie|serial)\/(\d+)/) || [])[1];
    return { id: id ? +id : null, type: url.includes('/serial/') ? 'series' : 'movie', trailer: t };
  }
  async function worker() { while (i < pages.length) { const u = pages[i++]; const h = await F(u); if (h) { try { const e = parse(h, u); if (e && e.id) out.push(e); } catch (_) {} } if (++done % 100 === 0) log(done + '/' + pages.length + ' (' + out.length + ' trailer)'); if (done % 2000 === 0) window.__dlT(); } }
  await Promise.all(Array.from({ length: 6 }, worker));
  log('%cდასრულდა! ' + out.length + ' თრეილერი', 'color:#0f0;font-size:15px');
  window.__dlT();
})();
