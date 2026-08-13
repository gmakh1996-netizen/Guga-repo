/* ──────────────────────────────────────────────────────────────────────────
   "Continue watching" enhancer — runs on EVERY web page.
   Finds any serial/movie card whose id matches an entry in the
   `keepwatching` localStorage list, then:
     1. injects a thin progress bar between the thumbnail and the title;
     2. rewrites all card links to resume at the saved season/episode + time
        (same query-string contract as the home block & serial.php saver).

   Self-contained: ships its own CSS via a one-shot <style> injection.
   Kept plain ES5 / no-jQuery so it can run before base.js if needed.
   ────────────────────────────────────────────────────────────────────────── */
(function(){
	"use strict";

	// One-shot CSS injection. Scoped via .kw-progress so we cannot collide
	// with anything else on the page. Bar sits between the thumbnail and
	// the title, matching the existing "continue watching" red (#f10202).
	var STYLE_ID = "kw-enhancer-style";
	function injectStyle(){
		if (document.getElementById(STYLE_ID)) return;
		var st = document.createElement("style");
		st.id = STYLE_ID;
		st.textContent =
			".kw-progress{" +
				"display:block;width:100%;height:3px;" +
				"background:rgba(93,93,93,.44);" +
				"overflow:hidden;position:relative;" +
				"margin:0;padding:0;line-height:0;" +
			"}" +
			".kw-progress__fill{" +
				"display:block;height:100%;background:#f10202;" +
				"transition:width .25s ease-out;" +
			"}";
		(document.head || document.documentElement).appendChild(st);
	}

	function loadList(){
		try {
			var raw = localStorage.getItem("keepwatching");
			var arr = raw ? JSON.parse(raw) : [];
			return Array.isArray(arr) ? arr : [];
		} catch(_) { return []; }
	}

	function normalizeType(t){
		// Tolerate both legacy ("movies"/"serials") and new ("movie"/"serial").
		if (t === "movies")  return "movie";
		if (t === "serials") return "serial";
		return t || "";
	}

	// Build an index keyed by "type:id". For serials the user may have many
	// episodes saved — we keep ONLY the most-recent one (highest created_at)
	// because that's the natural "continue from here" anchor.
	function buildIndex(list){
		var idx = {};
		for (var i = 0; i < list.length; i++) {
			var it = list[i];
			if (!it || !it.id) continue;
			if (!(Number(it.seek) > 0) && !(Number(it.start) > 0)) continue;

			var type = normalizeType(it.type);
			if (type !== "movie" && type !== "serial") continue;

			var key = type + ":" + String(it.id);
			var ts  = Number(it.created_at) || 0;
			var prev = idx[key];
			if (!prev || (Number(prev.created_at) || 0) < ts) idx[key] = it;
		}
		return idx;
	}

	function progressPct(item){
		var start = Number(item.start || item.seek) || 0;
		var end   = Number(item.end) || 0;
		if (end <= 0) return 0;
		var pct = (start * 100) / end;
		return Math.max(1, Math.min(100, pct));
	}

	function buildResumeQuery(item){
		var type = normalizeType(item.type);
		var qs   = "";
		if (type === "serial" && item.play_id && /^\d+-\d+$/.test(item.play_id)) {
			var parts = String(item.play_id).split("-");
			qs = "?season=" + encodeURIComponent(parts[0]) +
			     "&episode=" + encodeURIComponent(parts[1]);
		}
		var seek = Math.round(Number(item.start || item.seek) || 0);
		if (seek > 0) qs += (qs ? "&" : "?") + "t=" + seek;
		return qs;
	}

	function stripQueryAndHash(url){
		return String(url || "").replace(/[?#].*$/, "");
	}

	// Card layouts on the site (web/) — three known wrappers, each with a
	// matching `__img` child. Anything else (hero slider, comments, etc.)
	// is intentionally ignored.
	var CARD_SELECTOR = ".movie-card, .serials-card, .popular-card";
	var IMG_SELECTOR  = ".movie-card__img, .serials-card__img, .popular-card__img";

	// Don't touch the existing "continue watching" home block — it has its
	// own progress UI and would double-render here.
	function isInsideKeepWatchingBlock(el){
		while (el && el !== document.body) {
			if (el.id === "block_watching") return true;
			el = el.parentNode;
		}
		return false;
	}

	function enhance(){
		var idx = buildIndex(loadList());
		var keys = Object.keys(idx);
		if (!keys.length) return;

		injectStyle();

		// Match links of shape /serial/<id>/... or /movie/<id>/... regardless
		// of host (relative or absolute) — we filter via regex below.
		var links = document.querySelectorAll('a[href*="/serial/"], a[href*="/movie/"]');
		var seen  = []; // we use a plain array because Set is not in IE11

		for (var i = 0; i < links.length; i++) {
			var link = links[i];
			var href = link.getAttribute("href") || "";
			var m = href.match(/\/(serial|movie)\/(\d+)(?:\/|\?|#|$)/);
			if (!m) continue;

			var type = m[1];
			var id   = m[2];
			var item = idx[type + ":" + id];
			if (!item) continue;

			var card = link.closest ? link.closest(CARD_SELECTOR) : null;
			if (!card || isInsideKeepWatchingBlock(card)) continue;

			// Skip cards we've already touched on a prior link iteration
			// (titles + thumbnails both live inside the same card).
			if (seen.indexOf(card) !== -1) continue;
			seen.push(card);

			var imgWrap = card.querySelector(IMG_SELECTOR);
			if (!imgWrap || !imgWrap.parentNode) continue;

			// Build the bar once per card, insert it right after the thumb
			// wrapper (= sibling), so it sits between thumbnail and title.
			var bar = document.createElement("div");
			bar.className = "kw-progress";
			bar.setAttribute("data-kw-id", type + ":" + id);
			var fill = document.createElement("div");
			fill.className = "kw-progress__fill";
			fill.style.width = progressPct(item).toFixed(1) + "%";
			bar.appendChild(fill);
			imgWrap.parentNode.insertBefore(bar, imgWrap.nextSibling);

			// Rewrite EVERY link inside this card (both thumb anchor and title
			// anchor) to land directly at the saved spot, but keep the canonical
			// slug already rendered in the DOM (do not trust stale localStorage slug).
			var resumeQuery = buildResumeQuery(item);
			var inner = card.querySelectorAll('a[href*="/' + type + '/' + id + '"]');
			for (var j = 0; j < inner.length; j++) {
				var currentHref = inner[j].getAttribute("href") || "";
				var baseHref = stripQueryAndHash(currentHref);
				if (!/\/(?:serial|movie)\/\d+\/[^\/?#]+/i.test(baseHref)) {
					// Fallback should rarely happen; keep previous behavior as safety net.
					baseHref = "/" + type + "/" + encodeURIComponent(id) + "/" + encodeURIComponent(item.slug || "");
				}
				inner[j].setAttribute("href", baseHref + resumeQuery);
			}
		}
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", enhance, false);
	} else {
		// Run on the next tick so other DOM-mutating scripts (e.g. lazy
		// thumb loaders) finish their initial pass first.
		setTimeout(enhance, 0);
	}
})();
