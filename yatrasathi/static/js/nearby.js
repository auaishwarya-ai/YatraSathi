/* YatraSathi - Nearby Places (location-based filtering) */
(function () {
  "use strict";
  const YS = window.YS;
  let map, originMarker, layer, points = [], cities = [], origin = null, category = "";

  function km(a, b, c, d) {
    const R = 6371, dLat = (c - a) * Math.PI / 180, dLng = (d - b) * Math.PI / 180;
    const x = Math.sin(dLat / 2) ** 2 + Math.cos(a * Math.PI / 180) * Math.cos(c * Math.PI / 180) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(x)) * 1.3;
  }

  function render() {
    const list = document.getElementById("nearby-list");
    if (!origin) return;
    const rows = points
      .filter((p) => !category || p.category === category)
      .map((p) => Object.assign({ dist: km(origin.lat, origin.lng, p.lat, p.lng) }, p))
      .filter((p) => p.dist > 0.5 || origin.slug !== p.slug)
      .sort((a, b) => a.dist - b.dist)
      .slice(0, 15);
    document.getElementById("origin-label").textContent = origin.name;
    list.innerHTML = rows.map((p, i) => `
      <div class="nearby-item" data-i="${i}">
        ${YS.imgTag(p)}
        <div class="flex-1"><b>${YS.escape(p.display_name)}</b>
          <div class="d">${YS.escape(YS.t(p.category))} · ${YS.escape(p.district)}</div>
          <div class="d">${p.dist.toFixed(1)} km · ≈ ${Math.max(10, Math.round(p.dist / 50 * 60 / 5) * 5)} min</div></div>
        <div class="stars"><i data-lucide="star"></i>${p.rating}</div>
      </div>`).join("") || `<div class="empty-state">${YS.t("No places found")}</div>`;
    YS.icons(list);
    YS.loadImages(list);
    if (!map) return;
    layer.clearLayers();
    if (originMarker) originMarker.remove();
    originMarker = L.circleMarker([origin.lat, origin.lng], { radius: 10, color: "#3b36d1", fillColor: "#3b36d1", fillOpacity: .8 }).addTo(map).bindPopup(YS.escape(origin.name));
    const bounds = [[origin.lat, origin.lng]];
    const markers = rows.map((p) => {
      const m = L.marker([p.lat, p.lng]).addTo(layer).bindPopup(`<b>${YS.escape(p.display_name)}</b><br>${p.dist.toFixed(1)} km<br><a href="/place/${p.slug}">${YS.t("View details")}</a> · <a target="_blank" rel="noopener" href="https://www.google.com/maps/dir/?api=1&origin=${origin.lat},${origin.lng}&destination=${p.lat},${p.lng}">${YS.t("Directions")}</a>`);
      bounds.push([p.lat, p.lng]);
      return m;
    });
    map.fitBounds(bounds.slice(0, 9), { padding: [30, 30] });
    list.querySelectorAll(".nearby-item").forEach((el) => el.addEventListener("click", () => {
      list.querySelectorAll(".nearby-item").forEach((x) => x.classList.remove("active"));
      el.classList.add("active");
      const m = markers[+el.getAttribute("data-i")];
      map.setView(m.getLatLng(), 11);
      m.openPopup();
    }));
    document.getElementById("open-maps").href = `https://www.google.com/maps/search/tourist+attractions/@${origin.lat},${origin.lng},11z`;
  }

  function setOrigin(o) { origin = o; render(); }

  document.addEventListener("DOMContentLoaded", () => {
    points = JSON.parse(document.getElementById("points-json").textContent);
    cities = JSON.parse(document.getElementById("cities-json").textContent);
    const mapEl = document.getElementById("nearby-map");
    if (window.L && mapEl) {
      map = L.map(mapEl).setView([14.5, 76], 7);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "© OpenStreetMap" }).addTo(map);
      layer = L.layerGroup().addTo(map);
    }
    const sel = document.getElementById("origin-select");
    sel.addEventListener("change", () => {
      const v = sel.value;
      if (v.startsWith("city:")) {
        const c = cities.find((x) => x.name === v.slice(5));
        setOrigin({ name: c.name, lat: c.lat, lng: c.lng });
      } else if (v.startsWith("place:")) {
        const p = points.find((x) => x.slug === v.slice(6));
        setOrigin({ name: p.display_name, lat: p.lat, lng: p.lng, slug: p.slug });
      }
    });
    document.getElementById("use-location").addEventListener("click", () => {
      if (!navigator.geolocation) return YS.toast(YS.t("Location is not available in this browser."), "error");
      navigator.geolocation.getCurrentPosition(
        (pos) => setOrigin({ name: YS.t("Your location"), lat: pos.coords.latitude, lng: pos.coords.longitude }),
        () => YS.toast(YS.t("Could not get your location. Choose a city instead."), "error"),
        { timeout: 10000 }
      );
    });
    document.querySelectorAll("[data-cat]").forEach((b) => b.addEventListener("click", () => {
      category = b.getAttribute("data-cat");
      document.querySelectorAll("[data-cat]").forEach((x) => x.classList.toggle("active", x === b));
      render();
    }));
    sel.dispatchEvent(new Event("change"));
  });
})();
