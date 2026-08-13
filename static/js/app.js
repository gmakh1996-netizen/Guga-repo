/* GEMOVIE — ge.movie-style UI: AJAX rows, hero, filter + infinite scroll, search */
(function () {
  "use strict";

  var PH = "/static/theme/web/img/poster.svg";  // გატეხილი/ცარიელი პოსტერის placeholder

  var PLAY_SVG =
    '<svg viewBox="0 0 265.4 265.4" xmlns="http://www.w3.org/2000/svg"><path d="M194.2 123.7l-78.1-51.1c-1.9-1.3-4-1.9-6.1-1.9 -5.5 0-9.7 4.5-9.7 10.5v103.2c0 6 4.2 10.5 9.7 10.5 2.1 0 4.2-0.7 6.1-1.9l78.1-51.1c3.3-2.1 5.1-5.4 5.1-9C199.3 129.1 197.4 125.8 194.2 123.7z"></path></svg>';

  function esc(s) {
    return (s == null ? "" : String(s)).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function api(params) {
    var qs = Object.keys(params)
      .filter(function (k) { return params[k] !== "" && params[k] != null; })
      .map(function (k) { return k + "=" + encodeURIComponent(params[k]); })
      .join("&");
    return fetch("/api/movies?" + qs).then(function (r) { return r.json(); });
  }

  // ---- card markup (matches _moviecard.html) ----
  function cardInner(m, portrait) {
    var rates = m.rating ? '<div class="rates"><div class="imdb"><span>IMDb ' + esc(m.rating) + "</span></div></div>" : "";
    var year = m.year ? '<span class="year">' + esc(m.year) + "</span>" : "";
    var src = (portrait && m.poster_portrait) ? m.poster_portrait : (m.poster || PH);
    var img = '<img src="' + esc(src) + '" alt="' + esc(m.title) + '" loading="lazy" onerror="this.onerror=null;this.src=\'' + PH + '\';this.classList.add(\'ge-ph\')">';
    var en = m.title_en ? "<p>" + esc(m.title_en) + "</p>" : "";
    return (
      '<div class="movie-card">' +
        '<div class="movie-card__img">' + img +
          '<div class="play"><a href="' + esc(m.url) + '">' + PLAY_SVG + "</a></div>" +
          rates +
          '<div class="actions">' + year + "</div>" +
        "</div>" +
        '<div class="movie-card__title"><h2><a href="' + esc(m.url) + '"><span>' + esc(m.title) + "</span>" + en + "</a></h2></div>" +
      "</div>"
    );
  }
  function cardCol(m) { return '<div class="ge-cell">' + cardInner(m) + "</div>"; }
  function cardSlide(m, portrait) {
    var bg = portrait && m.poster ? ' data-bg="' + esc(m.poster) + '"' : "";
    return '<div class="swiper-slide"' + bg + ">" + cardInner(m, portrait) + "</div>";
  }

  // ---- category icons ----
  // Lucide icons (stroke-based, premium)
  var ICONS = {
    resume: '<path d="M9 9.003a1 1 0 0 1 1.517-.859l4.997 2.997a1 1 0 0 1 0 1.718l-4.997 2.997A1 1 0 0 1 9 14.996z"/><circle cx="12" cy="12" r="10"/>',
    film: '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 3v18"/><path d="M3 7.5h4"/><path d="M3 12h18"/><path d="M3 16.5h4"/><path d="M17 3v18"/><path d="M17 7.5h4"/><path d="M17 16.5h4"/>',
    tv: '<path d="m17 2-5 5-5-5"/><rect width="20" height="15" x="2" y="7" rx="2"/>',
    newfilm: '<path d="m12.296 3.464 3.02 3.956"/><path d="M20.2 6 3 11l-.9-2.4c-.3-1.1.3-2.2 1.3-2.5l13.5-4c1.1-.3 2.2.3 2.5 1.3z"/><path d="M3 11h18v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="m6.18 5.276 3.1 3.899"/>',
    newtv: '<path d="M15.033 9.44a.647.647 0 0 1 0 1.12l-4.065 2.352a.645.645 0 0 1-.968-.56V7.648a.645.645 0 0 1 .967-.56z"/><path d="M12 17v4"/><path d="M8 21h8"/><rect x="2" y="3" width="20" height="14" rx="2"/>',
    sparkles: '<path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z"/><path d="M20 2v4"/><path d="M22 4h-4"/><circle cx="4" cy="20" r="2"/>',
    premiere: '<path d="M18 8a2 2 0 0 0 0-4 2 2 0 0 0-4 0 2 2 0 0 0-4 0 2 2 0 0 0-4 0 2 2 0 0 0 0 4"/><path d="M10 22 9 8"/><path d="m14 22 1-14"/><path d="M20 8c.5 0 .9.4.8 1l-2.6 12c-.1.5-.7 1-1.2 1H7c-.6 0-1.1-.4-1.2-1L3.2 9c-.1-.6.3-1 .8-1Z"/>',
  };
  function iconSvg(name) {
    if (!ICONS[name]) return "";
    return '<span class="ge-ico-badge"><svg class="ge-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">' + ICONS[name] + "</svg></span>";
  }

  // ---- home rows ----
  function buildRow(el) {
    var type = el.dataset.type, sort = el.dataset.sort, title = el.dataset.title, icon = el.dataset.icon;
    var portrait = el.dataset.portrait === "1";
    api({ type: type, sort: sort, per: 18, page: 1 }).then(function (data) {
      if (!data.items || !data.items.length) { el.remove(); return; }
      var more = "/browse?type=" + type + "&sort=" + sort;
      el.innerHTML =
        '<section class="movies' + (portrait ? " movies--portrait" : "") + '">' +
          (portrait ? '<div class="ge-prem-bg" id="premBg"></div><div class="ge-prem-shade"></div>' : "") +
          '<div class="container"><div class="row"><div class="col-md-12">' +
          '<div class="ge-row-head"><div class="ge-head-left">' + iconSvg(icon) +
          '<h2 class="ge-section-title">' + esc(title) + "</h2></div>" +
          '<a class="ge-more" href="' + more + '">ყველა →</a></div>' +
          '<div class="movies-slider"><div class="sbtns">' +
            '<div class="prev-slide">‹</div><div class="next-slide">›</div></div>' +
            '<div class="swiper"><div class="swiper-wrapper">' +
              data.items.map(function (m) { return cardSlide(m, portrait); }).join("") +
            "</div></div>" +
          "</div>" +
        "</div></div></div></section>";
      if (window.Swiper) {
        var bp = portrait
          ? { 576: { slidesPerView: 4 }, 768: { slidesPerView: 5 }, 1200: { slidesPerView: 7 } }
          : { 576: { slidesPerView: 3 }, 768: { slidesPerView: 4 }, 1200: { slidesPerView: 5 } };
        new Swiper(el.querySelector(".swiper"), {
          slidesPerView: portrait ? 3 : 2, spaceBetween: 14, watchOverflow: true,
          navigation: { nextEl: el.querySelector(".next-slide"), prevEl: el.querySelector(".prev-slide") },
          breakpoints: bp,
        });
      }
      // პრემიერა — ჰოვერზე ფონად დაჰოვერებული ფილმის backdrop
      if (portrait) {
        var bgEl = el.querySelector(".ge-prem-bg");
        var slides = el.querySelectorAll(".swiper-slide[data-bg]");
        function setBg(u) { if (bgEl && u) bgEl.style.backgroundImage = "url('" + u + "')"; }
        if (slides[0]) setBg(slides[0].getAttribute("data-bg"));
        slides.forEach(function (s) {
          s.addEventListener("mouseenter", function () { setBg(s.getAttribute("data-bg")); });
        });
      }
    });
  }

  // ---- hero (featured + 3x3 thumbs, ge.movie-style) ----
  function buildHero(el) {
    var bg = el.querySelector("#heroBg");
    var title = el.querySelector("#heroTitle");
    var genres = el.querySelector("#heroGenres");
    var imdb = el.querySelector("#heroImdb");
    var featured = el.querySelector("#heroFeatured");
    var thumbs = el.querySelector("#heroThumbs");
    var items = [], idx = 0, timer = null;

    function show(i) {
      idx = i;
      var m = items[i];
      if (!m) return;
      bg.style.backgroundImage = "url('" + m.poster + "')";
      title.textContent = m.title;
      genres.innerHTML = (m.genres || []).map(function (g) { return "<span>" + esc(g) + "</span>"; }).join("");
      imdb.textContent = m.rating ? "IMDb " + m.rating : "";
      imdb.style.display = m.rating ? "" : "none";
      featured.setAttribute("href", m.url);
      [].forEach.call(thumbs.children, function (t, j) { t.classList.toggle("active", j === i); });
    }
    function rotate() {
      timer = setInterval(function () { show((idx + 1) % items.length); }, 6000);
    }

    api({ type: el.dataset.type || "movie", sort: el.dataset.sort || "popularity", per: 9, page: 1 }).then(function (data) {
      items = (data.items || []).filter(function (m) { return m.poster; });
      if (!items.length) { el.style.display = "none"; return; }
      thumbs.innerHTML = items.map(function (m, i) {
        return '<div class="ge-hero__thumb" data-i="' + i + '">' +
          '<img src="' + esc(m.poster || PH) + '" alt="' + esc(m.title) + '" loading="lazy" onerror="this.onerror=null;this.src=\'' + PH + '\';this.classList.add(\'ge-ph\')">' +
          '<span class="ge-hero__thumb-title">' + esc(m.title) + "</span></div>";
      }).join("");
      [].forEach.call(thumbs.children, function (t) {
        t.addEventListener("mouseenter", function () { if (timer) { clearInterval(timer); timer = null; } show(+this.dataset.i); });
        t.addEventListener("click", function () { location.href = items[+this.dataset.i].url; });
      });
      show(0);
      rotate();
    });
  }

  // ---- filter page + infinite scroll ----
  function initFilter() {
    var bar = document.querySelector(".ge-filterbar");
    if (!bar) return;
    var results = document.getElementById("filterResults");
    var loader = document.getElementById("filterLoader");
    var empty = document.getElementById("filterEmpty");
    var sentinel = document.getElementById("filterSentinel");
    var state = {
      type: bar.dataset.type || "movie",
      genre: bar.dataset.genre || "",
      year: bar.dataset.year || "",
      sort: bar.dataset.sort || "popularity",
      q: bar.dataset.q || "",
      page: 1, hasMore: true, loading: false,
    };

    function params() {
      return { type: state.type, genre: state.genre, year: state.year, sort: state.sort, q: state.q, page: state.page, per: 24 };
    }
    function nearBottom() {
      return sentinel.getBoundingClientRect().top < window.innerHeight + 700;
    }
    function load() {
      if (state.loading || !state.hasMore) return;
      state.loading = true; loader.hidden = false;
      api(params()).then(function (data) {
        state.loading = false; loader.hidden = true;
        state.hasMore = data.has_more;
        if (state.page === 1 && (!data.items || !data.items.length)) { empty.hidden = false; return; }
        empty.hidden = true;
        results.insertAdjacentHTML("beforeend", data.items.map(cardCol).join(""));
        state.page += 1;
        // თუ გვერდი ჯერ კიდევ ბოლოს ახლოა — ჩავტვირთოთ შემდეგიც
        if (nearBottom()) setTimeout(load, 60);
      }).catch(function () { state.loading = false; loader.hidden = true; });
    }
    function maybeLoad() { if (nearBottom()) load(); }
    function reset() {
      state.page = 1; state.hasMore = true; results.innerHTML = ""; empty.hidden = true; load();
    }
    window.addEventListener("scroll", maybeLoad, { passive: true });
    window.addEventListener("resize", maybeLoad);
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entries) {
        if (entries[0].isIntersecting) load();
      }, { rootMargin: "700px 0px" }).observe(sentinel);
    }

    var fType = document.getElementById("fType");
    var fGenre = document.getElementById("fGenre");
    var fYear = document.getElementById("fYear");
    var fSort = document.getElementById("fSort");
    if (fType) fType.addEventListener("change", function () { state.type = this.value; state.q = ""; reset(); });
    if (fGenre) fGenre.addEventListener("change", function () { state.genre = this.value; reset(); });
    if (fYear) fYear.addEventListener("change", function () { state.year = this.value; reset(); });
    if (fSort) fSort.addEventListener("change", function () { state.sort = this.value; reset(); });

    load();
  }

  // ---- search autocomplete ----
  function initSearch() {
    var input = document.getElementById("search");
    var box = document.getElementById("search_autocomplete");
    if (!input || !box) return;
    var t;
    input.addEventListener("input", function () {
      clearTimeout(t);
      var q = input.value.trim();
      if (q.length < 2) { box.innerHTML = ""; box.classList.remove("open"); return; }
      t = setTimeout(function () {
        fetch("/api/search?q=" + encodeURIComponent(q)).then(function (r) { return r.json(); }).then(function (d) {
          if (!d.items || !d.items.length) { box.innerHTML = ""; box.classList.remove("open"); return; }
          box.innerHTML = d.items.map(function (m) {
            return '<a class="ac-item" href="' + esc(m.url) + '">' +
              (m.poster ? '<img src="' + esc(m.poster) + '">' : "") +
              '<span class="ac-title">' + esc(m.title) + (m.year ? " (" + esc(m.year) + ")" : "") + "</span></a>";
          }).join("");
          box.classList.add("open");
        });
      }, 220);
    });
    document.addEventListener("click", function (e) {
      if (!box.contains(e.target) && e.target !== input) box.classList.remove("open");
    });
  }

  // ---- persons page ----
  function initPersons() {
    var results = document.getElementById("personsResults");
    if (!results) return;
    var loader = document.getElementById("personsLoader");
    var empty = document.getElementById("personsEmpty");
    var sentinel = document.getElementById("personsSentinel");
    var st = { page: 1, hasMore: true, loading: false };
    function personCard(p) {
      var img = p.photo
        ? '<img src="' + esc(p.photo) + '" alt="' + esc(p.name) + '" loading="lazy" onerror="this.outerHTML=\'<div class=&quot;ge-person__ph&quot;></div>\'">'
        : '<div class="ge-person__ph"></div>';
      var en = p.name_en ? '<div class="ge-person__en">' + esc(p.name_en) + "</div>" : "";
      return '<div class="ge-cell"><div class="ge-person">' +
        '<div class="ge-person__photo">' + img + "</div>" +
        '<div class="ge-person__name">' + esc(p.name) + "</div>" + en + "</div></div>";
    }
    function nearBottom() { return sentinel.getBoundingClientRect().top < window.innerHeight + 700; }
    function load() {
      if (st.loading || !st.hasMore) return;
      st.loading = true; loader.hidden = false;
      fetch("/api/persons?page=" + st.page + "&per=36").then(function (r) { return r.json(); }).then(function (d) {
        st.loading = false; loader.hidden = true; st.hasMore = d.has_more;
        if (st.page === 1 && (!d.items || !d.items.length)) { empty.hidden = false; return; }
        results.insertAdjacentHTML("beforeend", d.items.map(personCard).join(""));
        st.page += 1;
        if (nearBottom()) setTimeout(load, 60);
      }).catch(function () { st.loading = false; loader.hidden = true; });
    }
    window.addEventListener("scroll", function () { if (nearBottom()) load(); }, { passive: true });
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (e) { if (e[0].isIntersecting) load(); }, { rootMargin: "700px 0px" }).observe(sentinel);
    }
    load();
  }

  // ---- განაგრძე ყურება (localStorage: gemovie_recent) ----
  function renderRow(el, title, icon, items, moreHref) {
    if (!items || !items.length) { el.remove(); return; }
    el.innerHTML =
      '<section class="movies"><div class="container"><div class="row"><div class="col-md-12">' +
        '<div class="ge-row-head"><div class="ge-head-left">' + iconSvg(icon) +
        '<h2 class="ge-section-title">' + esc(title) + "</h2></div>" +
        (moreHref ? '<a class="ge-more" href="' + moreHref + '">ყველა →</a>' : "") + "</div>" +
        '<div class="movies-slider"><div class="sbtns"><div class="prev-slide">‹</div><div class="next-slide">›</div></div>' +
          '<div class="swiper"><div class="swiper-wrapper">' + items.map(cardSlide).join("") + "</div></div>" +
        "</div>" +
      "</div></div></div></section>";
    if (window.Swiper) {
      new Swiper(el.querySelector(".swiper"), {
        slidesPerView: 2, spaceBetween: 14, watchOverflow: true,
        navigation: { nextEl: el.querySelector(".next-slide"), prevEl: el.querySelector(".prev-slide") },
        breakpoints: { 576: { slidesPerView: 3 }, 768: { slidesPerView: 4 }, 1200: { slidesPerView: 5 } },
      });
    }
  }
  function initContinueWatching(el) {
    var items = [];
    try { items = JSON.parse(localStorage.getItem("gemovie_recent") || "[]"); } catch (e) {}
    renderRow(el, el.dataset.title || "განაგრძე ყურება", el.dataset.icon || "resume", items.slice(0, 18), null);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var hero = document.getElementById("HeroSlider");
    if (hero) buildHero(hero);
    var cw = document.getElementById("cwRow");
    if (cw) initContinueWatching(cw);
    document.querySelectorAll(".movies-row").forEach(buildRow);
    initFilter();
    initPersons();
    initSearch();
  });
})();
