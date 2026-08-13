/* GEMOVIE — ვიდეო-ფლეერი.
   კითხულობს #player[data-streams]-ს და რენდერავს არჩეულ წყაროს.
   kind: 'embed' (iframe) | 'mp4' (video) | 'hls' (video + hls.js). */
(function () {
  const root = document.getElementById("player");
  if (!root) return;

  let streams = [];
  try {
    streams = JSON.parse(root.dataset.streams || "[]");
  } catch (e) {
    console.error("streams JSON ვერ დაიპარსა", e);
  }
  if (!streams.length) return;

  const stage = document.getElementById("player-stage");
  const tabs = document.getElementById("player-tabs");

  function render(stream) {
    stage.innerHTML = "";

    if (stream.kind === "embed") {
      const iframe = document.createElement("iframe");
      iframe.src = stream.url;
      iframe.allow = "fullscreen; encrypted-media; picture-in-picture";
      iframe.allowFullscreen = true;
      iframe.setAttribute("loading", "lazy");
      stage.appendChild(iframe);
      return;
    }

    const video = document.createElement("video");
    video.controls = true;
    video.playsInline = true;

    if (stream.kind === "hls") {
      // მშობლიური HLS (Safari) ან hls.js (სხვები)
      if (video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = stream.url;
      } else {
        loadHls(function () {
          if (window.Hls && window.Hls.isSupported()) {
            const hls = new window.Hls();
            hls.loadSource(stream.url);
            hls.attachMedia(video);
          } else {
            video.src = stream.url; // fallback
          }
        });
      }
    } else {
      video.src = stream.url; // mp4 და მისთ.
    }
    stage.appendChild(video);
  }

  function loadHls(cb) {
    if (window.Hls) return cb();
    const s = document.createElement("script");
    s.src = "https://cdn.jsdelivr.net/npm/hls.js@1";
    s.onload = cb;
    s.onerror = () => console.error("hls.js ვერ ჩაიტვირთა");
    document.head.appendChild(s);
  }

  // ტაბები (ენა/წყარო), თუ ერთზე მეტია
  if (tabs && streams.length > 1) {
    streams.forEach((st, i) => {
      const btn = document.createElement("button");
      btn.textContent = st.label;
      btn.className = "player__tab" + (i === 0 ? " is-active" : "");
      btn.addEventListener("click", () => {
        tabs.querySelectorAll(".player__tab").forEach((b) =>
          b.classList.remove("is-active")
        );
        btn.classList.add("is-active");
        render(st);
      });
      tabs.appendChild(btn);
    });
  }

  render(streams[0]);
})();
