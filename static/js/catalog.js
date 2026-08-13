// GEMOVIE — ლოკალური data.json-ით მართული კატალოგი.
// ძებნა სათაურით, ფილტრი ჟანრი/ტიპი, ბარათების ბადე, დეტალური მოდალი,
// movie → iframe player, series → ეპიზოდების ღილაკები (src ცვლილება).
(function () {
  "use strict";

  var raw = document.getElementById("catalog-data");
  var items = [];
  try {
    items = JSON.parse((raw && raw.textContent) || "[]");
  } catch (e) {
    items = [];
  }

  var grid = document.getElementById("catGrid");
  var empty = document.getElementById("catEmpty");
  var searchEl = document.getElementById("catSearch");
  var genreEl = document.getElementById("catGenre");
  var typeEl = document.getElementById("catType");

  var modal = document.getElementById("catModal");
  var mTitle = document.getElementById("mTitle");
  var mMeta = document.getElementById("mMeta");
  var mDesc = document.getElementById("mDesc");
  var mStage = document.getElementById("mStage");
  var mFrame = document.getElementById("mFrame");
  var mEpisodes = document.getElementById("mEpisodes");
  var mNote = document.getElementById("mNote");
  var mSource = document.getElementById("mSource");

  function typeLabel(t) {
    return t === "movie" ? "ფილმი" : "სერიალი";
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  // ---- ჟანრების dropdown-ის დინამიური აგება ----
  var seen = {};
  var genres = [];
  items.forEach(function (i) {
    if (i.genre && !seen[i.genre]) {
      seen[i.genre] = true;
      genres.push(i.genre);
    }
  });
  genres.sort();
  genres.forEach(function (g) {
    var o = document.createElement("option");
    o.value = g;
    o.textContent = g;
    genreEl.appendChild(o);
  });

  // ---- ბადის რენდერი + ფილტრი ----
  function render() {
    var q = searchEl.value.trim().toLowerCase();
    var g = genreEl.value;
    var t = typeEl.value;

    var filtered = items.filter(function (it) {
      var okSearch = (it.title || "").toLowerCase().indexOf(q) !== -1;
      var okGenre = g === "all" || it.genre === g;
      var okType = t === "all" || it.type === t;
      return okSearch && okGenre && okType;
    });

    grid.innerHTML = "";
    empty.hidden = filtered.length !== 0;

    filtered.forEach(function (it) {
      var hasPlayer =
        (it.type === "movie" && it.player) ||
        (it.type === "series" && (it.episodes || []).length);
      var meta = [it.year, it.genre].filter(Boolean).join(" · ");

      var card = document.createElement("div");
      card.className = "card catalog__card";
      card.innerHTML =
        '<div class="card__poster catalog__poster">' +
        '<span class="catalog__ph">' + esc(it.title) + "</span>" +
        '<span class="card__badge">' + esc(typeLabel(it.type)) + "</span>" +
        (hasPlayer ? '<span class="card__play">▶</span>' : "") +
        "</div>" +
        '<div class="card__meta">' +
        '<span class="card__title">' + esc(it.title) + "</span>" +
        '<span class="card__year">' + esc(meta) + "</span>" +
        "</div>";
      card.addEventListener("click", function () {
        openModal(it);
      });
      grid.appendChild(card);
    });
  }

  // ---- iframe src მართვა ----
  function setFrame(src) {
    if (src) {
      mFrame.src = src;
      mStage.hidden = false;
      mNote.hidden = true;
    } else {
      mFrame.removeAttribute("src");
      mStage.hidden = true;
      mNote.hidden = false;
    }
  }

  // ---- მოდალის გახსნა ----
  function openModal(it) {
    mTitle.textContent = it.title || "";
    mMeta.textContent = [it.year, it.genre, typeLabel(it.type)]
      .filter(Boolean)
      .join(" · ");
    mDesc.textContent = it.description || "";

    if (it.url) {
      mSource.href = it.url;
      mSource.hidden = false;
    } else {
      mSource.hidden = true;
    }

    mEpisodes.innerHTML = "";
    var src = null;

    if (it.type === "movie" && it.player) {
      // movie + player → სტანდარტული iframe
      src = it.player;
    } else if (it.type === "series" && (it.episodes || []).length) {
      // series + episodes → ეპიზოდების ღილაკები, პირველი აქტიური
      src = it.episodes[0].player;

      var heading = document.createElement("h3");
      heading.className = "modal__eptitle";
      heading.textContent = "ეპიზოდები";
      mEpisodes.appendChild(heading);

      var tabs = document.createElement("div");
      tabs.className = "player__tabs";
      it.episodes.forEach(function (ep, i) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "player__tab" + (i === 0 ? " is-active" : "");
        b.textContent = ep.title || "ეპიზოდი " + (i + 1);
        b.addEventListener("click", function () {
          // ღილაკზე დაჭერით iframe-ის src იცვლება
          setFrame(ep.player);
          var all = tabs.querySelectorAll(".player__tab");
          for (var j = 0; j < all.length; j++) {
            all[j].classList.remove("is-active");
          }
          b.classList.add("is-active");
        });
        tabs.appendChild(b);
      });
      mEpisodes.appendChild(tabs);
    }

    setFrame(src);
    modal.hidden = false;
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    modal.hidden = true;
    setFrame(null); // playback-ის გაჩერება
    mEpisodes.innerHTML = "";
    document.body.style.overflow = "";
  }

  // ---- მოვლენები ----
  searchEl.addEventListener("input", render);
  genreEl.addEventListener("change", render);
  typeEl.addEventListener("change", render);

  modal.addEventListener("click", function (e) {
    if (e.target.hasAttribute("data-close")) closeModal();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !modal.hidden) closeModal();
  });

  render();
})();
