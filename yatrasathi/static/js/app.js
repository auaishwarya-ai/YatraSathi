/* YatraSathi - shared frontend helpers */
(function () {
  "use strict";
  const YS = (window.YS = window.YS || {});
  YS.lang = document.documentElement.lang || "en";
  YS.t = (key) => (YS.strings && YS.strings[key]) || key;

  /* ---------------- Icons ---------------- */
  YS.icons = function (root) {
    if (window.lucide) window.lucide.createIcons({ attrs: { "stroke-width": 1.9 }, nameAttr: "data-lucide", root: root || document });
  };

  /* ---------------- Toast ---------------- */
  YS.toast = function (msg, type) {
    let box = document.querySelector(".flashes");
    if (!box) {
      box = document.createElement("div");
      box.className = "flashes";
      document.body.appendChild(box);
    }
    const el = document.createElement("div");
    el.className = "toast " + (type || "info");
    el.textContent = msg;
    box.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  };

  /* ---------------- Fetch JSON ---------------- */
  YS.post = async function (url, data) {
    const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data || {}) });
    let body = {};
    try { body = await res.json(); } catch (e) { /* not json */ }
    return { ok: res.ok, status: res.status, body };
  };

  /* ---------------- Safe mini-markdown (bold, italics, bullets, line breaks) ---------------- */
  YS.escape = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  YS.markdown = function (text) {
    const lines = YS.escape(text).split("\n");
    let html = "", inList = false;
    const inline = (s) => s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/(^|[\s(])[*_](?!\s)(.+?)[*_](?=[\s).,!?:]|$)/g, "$1<em>$2</em>");
    for (const raw of lines) {
      const line = raw.trimEnd();
      if (/^\s*[-•]\s+/.test(line)) {
        if (!inList) { html += "<ul>"; inList = true; }
        html += "<li>" + inline(line.replace(/^\s*[-•]\s+/, "")) + "</li>";
      } else {
        if (inList) { html += "</ul>"; inList = false; }
        if (line.trim()) html += "<p>" + inline(line) + "</p>";
      }
    }
    if (inList) html += "</ul>";
    return html;
  };
  YS.plainText = (text) => String(text || "").replace(/\*\*|__|[*_]/g, "").replace(/[✓✨📖📅🕘🎟️⏳💡🍽️🍛🧭📍🚌🏨➕✅⚠️🆘🙏😊🌿📜]/gu, "").replace(/\n+/g, ". ");

  /* ---------------- Place images (local -> Wikipedia -> category placeholder) ---------------- */
  const CACHE_KEY = "ys_wiki_images_v2";
  let cache = {};
  try { cache = JSON.parse(localStorage.getItem(CACHE_KEY) || "{}"); } catch (e) { cache = {}; }
  const pending = {};
  const saveCache = () => { try { localStorage.setItem(CACHE_KEY, JSON.stringify(cache)); } catch (e) { /* quota / private mode */ } };

  async function lookup(title, name) {
    if (cache[title] !== undefined) return cache[title];
    if (pending[title]) return pending[title];
    pending[title] = (async () => {
      let url = "";
      try {
        const r = await fetch("https://en.wikipedia.org/api/rest_v1/page/summary/" + encodeURIComponent(title.replace(/ /g, "_")));
        if (r.ok) {
          const j = await r.json();
          if (j.originalimage && j.originalimage.width <= 1600) url = j.originalimage.source;
          else if (j.thumbnail) url = j.thumbnail.source.replace(/\/\d+px-/, "/960px-");
        }
      } catch (e) { /* offline */ }
      if (!url && name) {
        try {
          const q = encodeURIComponent(name + " Karnataka");
          const r = await fetch("https://en.wikipedia.org/w/api.php?action=query&format=json&origin=*&generator=search&gsrlimit=1&prop=pageimages&piprop=thumbnail&pithumbsize=960&gsrsearch=" + q);
          const j = await r.json();
          const pages = j.query && j.query.pages ? Object.values(j.query.pages) : [];
          if (pages.length && pages[0].thumbnail) url = pages[0].thumbnail.source;
        } catch (e) { /* offline */ }
      }
      cache[title] = url;
      saveCache();
      return url;
    })();
    return pending[title];
  }

  YS.loadImages = function (root) {
    (root || document).querySelectorAll("img[data-wiki]:not([data-loaded])").forEach((img) => {
      img.setAttribute("data-loaded", "1");
      const title = img.getAttribute("data-wiki");
      if (!title) return;
      lookup(title, img.getAttribute("data-name")).then((url) => {
        if (!url) return;
        const pre = new Image();
        pre.onload = () => { img.src = url; img.classList.add("loaded"); };
        pre.src = url;
      });
    });
  };
  YS.imgTag = function (p, cls) {
    const ph = "/static/images/placeholders/" + (YS.catSlug[p.category_en || p.category] || "heritage") + ".svg";
    const src = p.image_url || ph;
    const wiki = p.image_url ? "" : ` data-wiki="${YS.escape(p.wiki || p.name)}" data-name="${YS.escape(p.name)}"`;
    return `<img class="${cls || ""}" src="${YS.escape(src)}"${wiki} alt="${YS.escape(p.display_name || p.name)}" loading="lazy" onerror="this.onerror=null;this.src='${ph}'">`;
  };
  YS.catSlug = { "Heritage": "heritage", "Temples": "temples", "Hill Stations": "hill-stations", "Waterfalls": "waterfalls", "Beaches": "beaches",
    "Wildlife": "wildlife", "Adventure": "adventure", "Gardens & Parks": "gardens" };

  /* ---------------- Favourites ---------------- */
  YS.toggleFavorite = async function (btn) {
    const slug = btn.getAttribute("data-fav");
    const r = await YS.post("/api/favorites/" + slug);
    if (r.status === 401) {
      YS.toast(YS.t("Please log in to save places."), "info");
      setTimeout(() => (window.location.href = "/login?next=" + encodeURIComponent(location.pathname + location.search)), 900);
      return;
    }
    if (!r.ok) return YS.toast(YS.t("Something went wrong. Please try again."), "error");
    document.querySelectorAll(`[data-fav="${slug}"]`).forEach((b) => {
      b.classList.toggle("saved", r.body.saved);
      const label = b.querySelector(".fav-label");
      if (label) label.textContent = r.body.saved ? YS.t("Saved") : YS.t("Add to Favorites");
    });
    YS.toast(r.body.saved ? YS.t("Added to your saved places") : YS.t("Removed from saved places"), "success");
  };

  /* ---------------- Voice output (Text-to-Speech) ---------------- */
  const LOCALES = { en: "en-IN", kn: "kn-IN", hi: "hi-IN" };
  let currentAudio = null;
  YS.stopSpeaking = function () {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    if (currentAudio) { currentAudio.pause(); currentAudio = null; }
  };
  function pickVoice(lang) {
    if (!window.speechSynthesis) return null;
    const voices = window.speechSynthesis.getVoices();
    const loc = LOCALES[lang] || "en-IN";
    return voices.find((v) => v.lang === loc) || voices.find((v) => v.lang && v.lang.toLowerCase().startsWith(lang)) || null;
  }
  YS.speak = async function (text, lang) {
    YS.stopSpeaking();
    const clean = YS.plainText(text).slice(0, 1400);
    const voice = pickVoice(lang);
    if (voice || (lang === "en" && window.speechSynthesis)) {
      const u = new SpeechSynthesisUtterance(clean);
      u.lang = LOCALES[lang] || "en-IN";
      if (voice) u.voice = voice;
      u.rate = 0.98;
      window.speechSynthesis.speak(u);
      return true;
    }
    // No local voice for Kannada/Hindi -> server side gTTS (needs internet)
    try {
      const res = await fetch("/api/tts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: clean, lang }) });
      if (!res.ok) throw new Error("tts");
      const blob = await res.blob();
      currentAudio = new Audio(URL.createObjectURL(blob));
      currentAudio.play();
      return true;
    } catch (e) {
      if (window.speechSynthesis) {
        const u = new SpeechSynthesisUtterance(clean);
        u.lang = LOCALES[lang];
        window.speechSynthesis.speak(u);
        return true;
      }
      YS.toast(YS.t("Voice output is not available in this browser."), "error");
      return false;
    }
  };
  if (window.speechSynthesis) window.speechSynthesis.onvoiceschanged = () => {};

  /* ---------------- Voice input (Speech-to-Text) ---------------- */
  YS.listen = function (lang, onResult, onEnd) {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      YS.toast(YS.t("Voice input works in Chrome or Edge. Please type your question."), "error");
      if (onEnd) onEnd();
      return null;
    }
    const rec = new SR();
    rec.lang = LOCALES[lang] || "en-IN";
    rec.interimResults = true;
    rec.maxAlternatives = 1;
    rec.onresult = (e) => {
      let text = "";
      for (let i = 0; i < e.results.length; i++) text += e.results[i][0].transcript;
      onResult(text, e.results[e.results.length - 1].isFinal);
    };
    rec.onerror = (e) => {
      if (e.error === "not-allowed") YS.toast(YS.t("Microphone permission denied."), "error");
      else if (e.error !== "no-speech" && e.error !== "aborted") YS.toast(YS.t("Could not recognise speech. Please try again."), "error");
    };
    rec.onend = () => onEnd && onEnd();
    rec.start();
    return rec;
  };

  /* ---------------- Page wiring ---------------- */
  document.addEventListener("click", (e) => {
    const fav = e.target.closest("[data-fav]");
    if (fav) { e.preventDefault(); e.stopPropagation(); YS.toggleFavorite(fav); return; }
    const tabBtn = e.target.closest("[data-tab]");
    if (tabBtn) {
      const group = tabBtn.closest("[data-tabs]");
      const scope = group ? group.parentElement : document;
      group.querySelectorAll("[data-tab]").forEach((b) => b.classList.toggle("active", b === tabBtn));
      scope.querySelectorAll(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === tabBtn.getAttribute("data-tab")));
      return;
    }
    const menu = e.target.closest(".user-menu > button");
    document.querySelectorAll(".user-menu").forEach((m) => { if (!menu || !m.contains(menu)) m.classList.remove("open"); });
    if (menu) menu.parentElement.classList.toggle("open");
    const navToggle = e.target.closest(".nav-toggle");
    if (navToggle) document.querySelector(".nav-links").classList.toggle("open");
    const sideToggle = e.target.closest(".side-toggle");
    if (sideToggle) document.querySelector(".admin-side").classList.toggle("open");
    const speakBtn = e.target.closest("[data-speak]");
    if (speakBtn) {
      const target = document.querySelector(speakBtn.getAttribute("data-speak"));
      if (target) YS.speak(target.innerText, speakBtn.getAttribute("data-lang") || YS.lang);
    }
  });

  document.addEventListener("DOMContentLoaded", () => {
    try { YS.strings = JSON.parse(document.getElementById("i18n").textContent); } catch (e) { YS.strings = {}; }
    YS.icons();
    YS.loadImages();
    document.querySelectorAll(".flashes .flash").forEach((f) => setTimeout(() => f.remove(), 5000));
    document.querySelectorAll("[data-confirm]").forEach((form) => form.addEventListener("submit", (e) => {
      if (!window.confirm(form.getAttribute("data-confirm"))) e.preventDefault();
    }));
  });
})();
