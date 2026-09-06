/* GEMOVIE — ge.movie-style UI: AJAX rows, hero, filter + infinite scroll, search */
(function () {
  "use strict";

  var PH = "/static/theme/web/img/poster.svg";  // გატეხილი/ცარიელი პოსტერის placeholder

  // სურათის ჩატვირთვა თუ ჩავარდა → მთელი ბარათი ამოვშალოთ (placeholder-ის ნაცვლად),
  // რომ უფოტო ფილმი/სერიალი არსად გამოჩნდეს. სერვერიც ფილტრავს, ეს — უსაფრთხოების ბადე.
  window.geImgFail = function (img) {
    var card = img.closest(".swiper-slide") || img.closest(".ge-cell") || img.closest(".movie-card");
    if (!card || !card.parentNode) { img.style.visibility = "hidden"; return; }
    var cont = card.closest(".swiper");
    card.parentNode.removeChild(card);
    if (cont && cont.swiper) { try { cont.swiper.update(); } catch (e) {} }
  };

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
    var img = '<img src="' + esc(src) + '" alt="' + esc(m.title) + '" loading="lazy" onerror="this.onerror=null;geImgFail(this)">';
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
    top: '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
  };
  function iconSvg(name) {
    if (!ICONS[name]) return "";
    return '<span class="ge-ico-badge"><svg class="ge-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">' + ICONS[name] + "</svg></span>";
  }

  // ---- home rows ----
  function buildRow(el, usedIds) {
    var type = el.dataset.type, sort = el.dataset.sort, title = el.dataset.title, icon = el.dataset.icon;
    var portrait = el.dataset.portrait === "1";
    var genre = el.dataset.genre || "";
    var excludeGenre = el.dataset.excludeGenre || "";
    var excludeIds = (usedIds && usedIds[type] && usedIds[type].size) ? Array.from(usedIds[type]).join(",") : "";
    return api({ type: type, sort: sort, genre: genre, exclude_genre: excludeGenre, exclude_ids: excludeIds, per: 18, page: 1 }).then(function (data) {
      if (!data.items || !data.items.length) { el.remove(); return; }
      if (usedIds && usedIds[type]) { data.items.forEach(function (m) { usedIds[type].add(m.id); }); }
      var more = "/browse?type=" + type + "&sort=" + sort + (genre ? "&genre=" + genre : "");
      var isAnime = genre === "900000025";
      var animeVariant = isAnime ? (type === "serial" ? " movies--abstract-bg-2" : " movies--abstract-bg") : "";
      el.innerHTML =
        '<section class="movies' + (portrait ? " movies--portrait" : "") + animeVariant + '">' +
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
          ? { 576: { slidesPerView: 4 }, 768: { slidesPerView: 5 }, 1200: { slidesPerView: 8 } }
          : { 576: { slidesPerView: 3 }, 768: { slidesPerView: 4 }, 1200: { slidesPerView: 5 } };
        new Swiper(el.querySelector(".swiper"), {
          slidesPerView: portrait ? 3 : 2, spaceBetween: 14, watchOverflow: true,
          navigation: { nextEl: el.querySelector(".next-slide"), prevEl: el.querySelector(".prev-slide") },
          breakpoints: bp,
        });
      }
      // პრემიერა — ჰოვერზე ფონად დაჰოვერებული ფილმის backdrop
      // (ანიმეს რიგებზე კი — საკუთარი, ორიგინალური აბსტრაქტული ფონია CSS-ით, არა პოსტერი,
      // რადგან ანიმეს დაბალხარისხიანი პოსტერები დიდ ბექგრაუნდში დამახინჯებული ჩანდა)
      if (portrait && !isAnime) {
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

  // ---- „ტოპ 9" რიგი: 1 დიდი ქარდი მარცხნივ + 8 ჩვეულებრივი ზომის ბადეში მარჯვნივ ----
  function topFeatureCard(m, rank) {
    var rates = m.rating ? '<div class="rates"><div class="imdb"><span>IMDb ' + esc(m.rating) + "</span></div></div>" : "";
    var en = m.title_en ? '<p class="ge-top9__en">' + esc(m.title_en) + "</p>" : "";
    return (
      '<a class="ge-top9__feature" href="' + esc(m.url) + '">' +
        '<img src="' + esc(m.poster || PH) + '" alt="' + esc(m.title) + '" loading="lazy" onerror="this.onerror=null;geImgFail(this)">' +
        '<span class="ge-top9__rank">' + rank + "</span>" +
        rates +
        '<div class="ge-top9__info"><h3>' + esc(m.title) + "</h3>" + en + "</div>" +
      "</a>"
    );
  }
  function topGridCell(m, rank) {
    return (
      '<div class="ge-top9__cell">' +
        '<span class="ge-top9__cell-rank">' + rank + "</span>" +
        cardInner(m) +
      "</div>"
    );
  }
  function buildTopRow(el, usedIds) {
    var type = el.dataset.type, sort = el.dataset.sort, title = el.dataset.title, icon = el.dataset.icon;
    var excludeGenre = el.dataset.excludeGenre || "";
    var excludeIds = (usedIds && usedIds[type] && usedIds[type].size) ? Array.from(usedIds[type]).join(",") : "";
    return api({ type: type, sort: sort, exclude_genre: excludeGenre, exclude_ids: excludeIds, per: 9, page: 1 }).then(function (data) {
      if (!data.items || data.items.length < 2) { el.remove(); return; }
      if (usedIds && usedIds[type]) { data.items.forEach(function (m) { usedIds[type].add(m.id); }); }
      var more = "/browse?type=" + type + "&sort=" + sort;
      var feature = data.items[0];
      var rest = data.items.slice(1, 9);
      el.innerHTML =
        '<section class="movies">' +
          '<div class="container"><div class="row"><div class="col-md-12">' +
          '<div class="ge-row-head"><div class="ge-head-left">' + iconSvg(icon) +
          '<h2 class="ge-section-title">' + esc(title) + "</h2></div>" +
          '<a class="ge-more" href="' + more + '">ყველა →</a></div>' +
          '<div class="ge-top9">' +
            topFeatureCard(feature, 1) +
            '<div class="ge-top9__grid">' +
              rest.map(function (m, i) { return topGridCell(m, i + 2); }).join("") +
            "</div>" +
          "</div>" +
        "</div></div></div></section>";
    });
  }

  // ---- hero (featured + 3x3 thumbs, ge.movie-style) ----
  function buildHero(el, usedIds) {
    var bg = el.querySelector("#heroBg");
    var title = el.querySelector("#heroTitle");
    var genres = el.querySelector("#heroGenres");
    var imdb = el.querySelector("#heroImdb");
    var featured = el.querySelector("#heroFeatured");
    var thumbs = el.querySelector("#heroThumbs");
    var items = [], idx = 0, timer = null;
    var type = el.dataset.type || "movie";

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

    return api({ type: type, sort: el.dataset.sort || "popularity", exclude_genre: el.dataset.excludeGenre || "", per: 9, page: 1 }).then(function (data) {
      items = (data.items || []).filter(function (m) { return m.poster; });
      if (!items.length) { el.style.display = "none"; return; }
      if (usedIds && usedIds[type]) { items.forEach(function (m) { usedIds[type].add(m.id); }); }
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

  // ---- filter page + numbered pagination ----
  var FILTER_PER = 24;
  function initFilter() {
    var bar = document.querySelector(".ge-filterbar");
    if (!bar) return;
    var results = document.getElementById("filterResults");
    var loader = document.getElementById("filterLoader");
    var empty = document.getElementById("filterEmpty");
    var pager = document.getElementById("filterPager");
    var state = {
      type: bar.dataset.type || "movie",
      genre: bar.dataset.genre || "",
      year: bar.dataset.year || "",
      sort: bar.dataset.sort || "popularity",
      q: bar.dataset.q || "",
      page: 1, loading: false,
    };

    function params() {
      return { type: state.type, genre: state.genre, year: state.year, sort: state.sort, q: state.q, page: state.page, per: FILTER_PER };
    }
    // 1 … cur-1 cur cur+1 … last — რომ ბევრი გვერდის შემთხვევაშიც (100+) კომპაქტური დარჩეს
    function pageList(cur, total) {
      var keep = {}; keep[1] = true; keep[total] = true;
      for (var i = cur - 1; i <= cur + 1; i++) if (i >= 1 && i <= total) keep[i] = true;
      var out = [], prev = 0;
      Object.keys(keep).map(Number).sort(function (a, b) { return a - b; }).forEach(function (i) {
        if (prev && i - prev > 1) out.push("…");
        out.push(i); prev = i;
      });
      return out;
    }
    function renderPager(total) {
      var pages = Math.max(Math.ceil(total / FILTER_PER), 1);
      if (pages <= 1) { pager.innerHTML = ""; pager.hidden = true; return; }
      var html = '<div class="ge-pager__nums">';
      if (state.page > 1) html += '<button type="button" class="ge-pager__btn ge-pager__arrow" data-go="' + (state.page - 1) + '">‹</button>';
      pageList(state.page, pages).forEach(function (p) {
        if (p === "…") { html += '<span class="ge-pager__dots">…</span>'; return; }
        html += p === state.page
          ? '<span class="ge-pager__num is-active">' + p + "</span>"
          : '<button type="button" class="ge-pager__num" data-go="' + p + '">' + p + "</button>";
      });
      if (state.page < pages) html += '<button type="button" class="ge-pager__btn ge-pager__arrow" data-go="' + (state.page + 1) + '">›</button>';
      html += "</div>";
      if (pages > 7) {
        html +=
          '<form class="ge-pager__jump" id="pagerJumpForm">' +
            "<span>გვერდზე გადასვლა</span>" +
            '<input type="number" min="1" max="' + pages + '" value="' + state.page + '" id="pagerJumpInput">' +
            '<button type="submit" class="ge-pager__btn">გადასვლა</button>' +
          "</form>";
      }
      pager.innerHTML = html;
      pager.hidden = false;
      var jumpForm = document.getElementById("pagerJumpForm");
      if (jumpForm) {
        jumpForm.addEventListener("submit", function (e) {
          e.preventDefault();
          var v = +document.getElementById("pagerJumpInput").value;
          if (v >= 1 && v <= pages && v !== state.page) { state.page = v; load(true); }
        });
      }
    }
    function load(scrollUp) {
      if (state.loading) return;
      state.loading = true; loader.hidden = false; empty.hidden = true;
      api(params()).then(function (data) {
        state.loading = false; loader.hidden = true;
        if (!data.items || !data.items.length) {
          results.innerHTML = ""; pager.innerHTML = ""; pager.hidden = true;
          empty.hidden = false; return;
        }
        results.innerHTML = data.items.map(cardCol).join("");
        renderPager(data.total || 0);
        if (scrollUp) results.scrollIntoView({ behavior: "smooth", block: "start" });
      }).catch(function () { state.loading = false; loader.hidden = true; });
    }
    function reset() { state.page = 1; load(false); }

    pager.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-go]");
      if (!btn) return;
      state.page = +btn.dataset.go;
      load(true);
    });

    var fType = document.getElementById("fType");
    var fGenre = document.getElementById("fGenre");
    var fYear = document.getElementById("fYear");
    var fSort = document.getElementById("fSort");
    if (fType) fType.addEventListener("change", function () { state.type = this.value; state.q = ""; reset(); });
    if (fGenre) fGenre.addEventListener("change", function () { state.genre = this.value; reset(); });
    if (fYear) fYear.addEventListener("change", function () { state.year = this.value; reset(); });
    if (fSort) fSort.addEventListener("change", function () { state.sort = this.value; reset(); });

    load(false);
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

  // ---- ბოლოს დამატებული ეპიზოდები (ცალკეული ეპიზოდები, არა მთლიანი სერიალი) ----
  function episodeCard(it) {
    var src = it.poster || PH;
    var titleEn = it.title_en ? '<div class="ge-ep-title-en">' + esc(it.title_en) + "</div>" : "";
    return (
      '<a class="ge-ep-card" href="' + esc(it.url) + '">' +
        '<div class="ge-ep-thumb">' +
          '<img src="' + esc(src) + '" alt="' + esc(it.title) + '" loading="lazy" onerror="this.onerror=null;this.src=\'' + PH + '\';this.classList.add(\'ge-ph\')">' +
          '<span class="ge-ep-lang">ქარ</span>' +
        "</div>" +
        '<div class="ge-ep-info">' +
          '<div class="ge-ep-title">' + esc(it.title) + "</div>" +
          titleEn +
          '<div class="ge-ep-meta">SE' + esc(it.season) + " | EP" + esc(it.episode) + "</div>" +
        "</div>" +
      "</a>"
    );
  }
  function buildRecentEpisodes(el, usedIds) {
    var title = el.dataset.title || "ბოლოს დამატებული ეპიზოდები";
    var icon = el.dataset.icon || "newtv";
    var excludeIds = (usedIds && usedIds.serial && usedIds.serial.size) ? Array.from(usedIds.serial).join(",") : "";
    fetch("/api/recent-episodes?per=18" + (excludeIds ? "&exclude_ids=" + encodeURIComponent(excludeIds) : "")).then(function (r) { return r.json(); }).then(function (data) {
      if (!data.items || !data.items.length) { el.remove(); return; }
      if (usedIds && usedIds.serial) { data.items.forEach(function (m) { usedIds.serial.add(m.id); }); }
      el.innerHTML =
        '<section class="movies"><div class="container"><div class="row"><div class="col-md-12">' +
          '<div class="ge-row-head"><div class="ge-head-left">' + iconSvg(icon) +
          '<h2 class="ge-section-title">' + esc(title) + "</h2></div></div>" +
          '<div class="ge-ep-grid">' + data.items.map(episodeCard).join("") + "</div>" +
        "</div></div></div></section>";
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    // მთავარ გვერდზე ერთი და იგივე ფილმი/სერიალი აღარ განმეორდეს სხვადასხვა
    // რიგში — რიგები ჩაწერით (თანმიმდევრულად) იტვირთება, თითოეული გამორიცხავს
    // წინა რიგებში უკვე ნაჩვენებ id-ებს (ცალკე set ფილმებისთვის/სერიალებისთვის).
    var usedIds = { movie: new Set(), serial: new Set() };
    var hero = document.getElementById("HeroSlider");
    var heroP = hero ? buildHero(hero, usedIds) : Promise.resolve();
    var cw = document.getElementById("cwRow");
    if (cw) initContinueWatching(cw);
    var epRow = document.getElementById("recentEpisodesRow");
    heroP.then(function () {
      var rows = Array.prototype.slice.call(document.querySelectorAll(".movies-row"));
      return rows.reduce(function (chain, el) {
        return chain.then(function () {
          return el.dataset.layout === "top9" ? buildTopRow(el, usedIds) : buildRow(el, usedIds);
        });
      }, Promise.resolve());
    }).then(function () {
      if (epRow) buildRecentEpisodes(epRow, usedIds);
    });
    initFilter();
    initPersons();
    initSearch();
  });
})();
