/* YatraSathi - Explore Karnataka page: preview panel + map view */
(function () {
  "use strict";
  const YS = window.YS;
  let map = null;

  async function showPreview(slug) {
    const panel = document.getElementById("preview");
    if (!panel || getComputedStyle(panel.parentElement).display === "none") {
      location.href = "/place/" + slug;
      return;
    }
    document.querySelectorAll(".place-card").forEach((c) => c.classList.toggle("selected", c.getAttribute("data-slug") === slug));
    const res = await fetch(`/api/destinations/${slug}?lang=${YS.lang}`);
    if (!res.ok) return;
    const d = await res.json();
    const fee = d.entry_fee_indian || d.entry_fee_foreign
      ? `₹${d.entry_fee_indian} ${YS.t("for Indians")}<br>₹${d.entry_fee_foreign} ${YS.t("for Foreigners")}` : YS.t("Free");
    panel.querySelector("[data-p=img]").outerHTML = YS.imgTag({ ...d, category: d.category }, "preview-img").replace("<img ", '<img data-p="img" ');
    panel.querySelector("[data-p=name]").textContent = d.display_name;
    panel.querySelector("[data-p=district]").textContent = `${d.district}, Karnataka`;
    panel.querySelector("[data-p=rating]").textContent = `${d.rating} (${d.reviews.toLocaleString("en-IN")} ${YS.t("reviews")})`;
    panel.querySelector("[data-p=summary]").textContent = d.summary;
    panel.querySelector("[data-p=best]").textContent = d.best_time;
    panel.querySelector("[data-p=timings]").textContent = d.timings;
    panel.querySelector("[data-p=fee]").innerHTML = fee;
    panel.querySelector("[data-p=attractions]").innerHTML = (d.attractions || []).map((a, i) => `<li>${YS.escape(a)}</li>`).join("");
    panel.querySelector("[data-p=reach]").textContent = d.how_to_reach;
    panel.querySelector("[data-p=food]").innerHTML = (d.food || []).map((f) => `<li>${YS.escape(f)}</li>`).join("");
    panel.querySelectorAll("[data-p=link]").forEach((a) => (a.href = "/place/" + slug));
    panel.querySelector("[data-p=ask]").href = "/assistant?place=" + slug;
    panel.querySelector("[data-p=plan]").href = "/planner?destination=" + slug + "&days=" + (d.ideal_days || 2);
    const fav = panel.querySelector("[data-fav]");
    fav.setAttribute("data-fav", slug);
    fav.classList.toggle("saved", d.saved);
    fav.querySelector(".fav-label").textContent = d.saved ? YS.t("Saved") : YS.t("Add to Favorites");
    const mapEl = panel.querySelector("#mini-map");
    if (mapEl && window.L) {
      if (mapEl._map) mapEl._map.remove();
      mapEl._map = L.map(mapEl, { zoomControl: false, attributionControl: false }).setView([d.lat, d.lng], 9);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18 }).addTo(mapEl._map);
      L.marker([d.lat, d.lng]).addTo(mapEl._map);
    }
    panel.querySelector("[data-p=maplink]").href = `https://www.google.com/maps/search/?api=1&query=${d.lat},${d.lng}`;
    YS.icons(panel);
    YS.loadImages(panel);
  }

  function initMap() {
    const el = document.getElementById("map-view");
    if (!el || map || !window.L) return;
    const points = JSON.parse(document.getElementById("map-points").textContent);
    map = L.map(el).setView([14.5, 76.0], 7);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "© OpenStreetMap" }).addTo(map);
    const bounds = [];
    points.forEach((p) => {
      L.marker([p.lat, p.lng]).addTo(map).bindPopup(`<b>${YS.escape(p.name)}</b><br>${YS.escape(p.category)} · ⭐ ${p.rating}<br><a href="/place/${p.slug}">${YS.t("View details")}</a>`);
      bounds.push([p.lat, p.lng]);
    });
    if (bounds.length) map.fitBounds(bounds, { padding: [30, 30] });
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".explore-grid .place-card").forEach((card) => card.addEventListener("click", (e) => {
      if (e.target.closest("[data-fav]")) return;
      if (e.metaKey || e.ctrlKey) return;
      e.preventDefault();
      showPreview(card.getAttribute("data-slug"));
    }));
    const toggle = document.getElementById("toggle-map");
    if (toggle) toggle.addEventListener("click", () => {
      const grid = document.getElementById("grid-view");
      const mapBox = document.getElementById("map-box");
      const showMap = mapBox.classList.contains("hidden");
      grid.classList.toggle("hidden", showMap);
      mapBox.classList.toggle("hidden", !showMap);
      toggle.querySelector("span").textContent = showMap ? YS.t("View as Grid") : YS.t("View on Map");
      if (showMap) { initMap(); setTimeout(() => map && map.invalidateSize(), 50); }
    });
    const mini = document.getElementById("mini-map");
    if (mini && window.L) {
      const lat = parseFloat(mini.getAttribute("data-lat")), lng = parseFloat(mini.getAttribute("data-lng"));
      mini._map = L.map(mini, { zoomControl: false, attributionControl: false }).setView([lat, lng], 9);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18 }).addTo(mini._map);
      L.marker([lat, lng]).addTo(mini._map);
    }
  });
})();
