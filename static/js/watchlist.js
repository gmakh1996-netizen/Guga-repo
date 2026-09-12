/* GEMOVIE — სანახავი სია (რჩეულები) ბრაუზერში (localStorage).
   ანგარიში არ სჭირდება. ინახავს: {id, type, title, poster}. */
(function () {
  const KEY = "gemovie_watchlist";

  const load = () => {
    try { return JSON.parse(localStorage.getItem(KEY) || "[]"); }
    catch (e) { return []; }
  };
  const save = (list) => localStorage.setItem(KEY, JSON.stringify(list));
  const esc = (s) => (s == null ? "" : String(s)).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const keyOf = (id, type) => `${type}:${id}`;
  const has = (list, id, type) =>
    list.some((x) => keyOf(x.id, x.type) === keyOf(id, type));

  function toggle(item) {
    let list = load();
    if (has(list, item.id, item.type)) {
      list = list.filter((x) => keyOf(x.id, x.type) !== keyOf(item.id, item.type));
    } else {
      list.push(item);
    }
    save(list);
    return has(list, item.id, item.type);
  }

  // ბარათებზე ♥ ღილაკის მდგომარეობის მონიშვნა
  function markButtons() {
    const list = load();
    document.querySelectorAll(".card__fav").forEach((btn) => {
      const active = has(list, btn.dataset.id, btn.dataset.type);
      btn.classList.toggle("is-active", active);
    });
  }

  // დელეგირებული კლიკი
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".card__fav");
    if (!btn) return;
    e.preventDefault();
    const item = {
      id: Number(btn.dataset.id),
      type: btn.dataset.type,
      title: btn.dataset.title,
      poster: btn.dataset.poster,
    };
    const active = toggle(item);
    btn.classList.toggle("is-active", active);
    if (grid && !active) renderWatchlist(); // watchlist გვერდზე — წაშლა live
  });

  // watchlist გვერდის რენდერი
  const grid = document.getElementById("watchlist-grid");
  const emptyMsg = document.getElementById("watchlist-empty");

  function renderWatchlist() {
    if (!grid) return;
    const list = load();
    grid.innerHTML = "";
    if (!list.length) {
      if (emptyMsg) emptyMsg.style.display = "block";
      return;
    }
    if (emptyMsg) emptyMsg.style.display = "none";
    list.forEach((it) => {
      const href = it.type === "tv" ? `/series/${it.id}` : `/movie/${it.id}`;
      // ჩამნაცვლებელი ბექოფისიდან (base.html → window.GE_CFG)
      const ph = (window.GE_CFG || {}).placeholderPoster || "/static/theme/web/img/poster.svg";
      const poster = it.poster || ph;
      const title = esc(it.title);
      const el = document.createElement("div");
      el.className = "col-6 col-md-4 col-lg-3 col-xxl-2";
      el.innerHTML =
        `<div class="movie-card"><div class="movie-card__img">` +
        `<img src="${esc(poster)}" alt="${title}" loading="lazy" onerror="this.onerror=null;geThumbFail(this);this.classList.add('ge-ph')">` +
        `<a href="${href}" class="play"><svg viewBox="0 0 265.4 265.4" xmlns="http://www.w3.org/2000/svg"><path d="M194.2 123.7l-78.1-51.1c-1.9-1.3-4-1.9-6.1-1.9 -5.5 0-9.7 4.5-9.7 10.5v103.2c0 6 4.2 10.5 9.7 10.5 2.1 0 4.2-0.7 6.1-1.9l78.1-51.1c3.3-2.1 5.1-5.4 5.1-9C199.3 129.1 197.4 125.8 194.2 123.7z"></path></svg></a>` +
        (it.type === "tv" ? `<div class="actions"><span class="year">სერიალი</span></div>` : "") +
        `<button class="card__fav wl-remove is-active" title="ამოშლა" data-id="${it.id}" data-type="${esc(it.type)}" ` +
        `data-title="${title}" data-poster="${esc(it.poster || "")}">♥</button>` +
        `</div><div class="movie-card__title"><h2><a href="${href}"><span>${title}</span></a></h2></div></div>`;
      grid.appendChild(el);
    });
  }

  markButtons();
  renderWatchlist();
})();
