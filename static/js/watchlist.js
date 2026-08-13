/* GEMOVIE — სანახავი სია (რჩეულები) ბრაუზერში (localStorage).
   ანგარიში არ სჭირდება. ინახავს: {id, type, title, poster}. */
(function () {
  const KEY = "gemovie_watchlist";

  const load = () => {
    try { return JSON.parse(localStorage.getItem(KEY) || "[]"); }
    catch (e) { return []; }
  };
  const save = (list) => localStorage.setItem(KEY, JSON.stringify(list));
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
      const poster = it.poster
        ? `<img src="${it.poster}" alt="${it.title}" loading="lazy">`
        : `<div class="card__noposter">${it.title}</div>`;
      const el = document.createElement("div");
      el.className = "card";
      el.innerHTML =
        `<a class="card__link" href="${href}"><div class="card__poster">${poster}` +
        (it.type === "tv" ? `<span class="card__badge">სერიალი</span>` : "") +
        `</div><div class="card__meta"><span class="card__title">${it.title}</span></div></a>` +
        `<button class="card__fav is-active" data-id="${it.id}" data-type="${it.type}" ` +
        `data-title="${it.title}" data-poster="${it.poster || ""}">♥</button>`;
      grid.appendChild(el);
    });
  }

  markButtons();
  renderWatchlist();
})();
