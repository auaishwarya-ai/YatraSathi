/* YatraSathi - AI Trip Planner page */
(function () {
  "use strict";
  const YS = window.YS;
  const money = (n) => Number(n || 0).toLocaleString("en-IN");
  let lastRequest = null;
  let lastTripId = null;

  function stopIcon(kind) {
    return { travel: "car", visit: "map-pin", stay: "bed-double", activity: "shopping-bag" }[kind] || "map-pin";
  }

  function budgetBanner(plan) {
    if (!plan.budget) return "";
    const s = plan.budget_status;
    let msg = "";
    if (s === "within") msg = `${YS.t("Fits your budget of")} ₹${money(plan.budget)} (₹${money(plan.remaining)} ${YS.t("to spare")})`;
    else if (s === "optimized") msg = `${YS.t("Optimised to fit your budget of")} ₹${money(plan.budget)}: ${YS.t("style")} ${YS.t(plan.style)}, ${YS.t("travel by")} ${YS.t(plan.transport)}`;
    else if (s === "over") msg = `${YS.t("Needs about")} ₹${money(plan.costs.total)} - ${YS.t("above your budget of")} ₹${money(plan.budget)}.` +
      (plan.suggested_days ? ` ${YS.t("Try")} ${plan.suggested_days} ${YS.t("day(s)")}.` : "");
    const icon = s === "over" ? "alert-triangle" : s === "within" ? "badge-check" : "sparkles";
    return `<div class="budget-banner ${s}"><i data-lucide="${icon}"></i><div>${msg}</div></div>`;
  }

  function renderPlan(plan, tripId, alternatives) {
    lastTripId = tripId;
    const box = document.getElementById("itinerary");
    const dest = plan.destination;
    const days = plan.day_plans.map((d) => {
      const stops = d.stops.map((s) => {
        const name = s.slug ? `<a href="/place/${s.slug}">${YS.escape(s.name)}</a>` : YS.escape(s.name);
        return `<li class="${s.kind === "stay" ? "stay" : ""}"><span class="tm">${YS.escape(s.time || "")}</span><span>${name}${s.fee ? ` <span class="muted xs">(₹${s.fee})</span>` : ""}</span></li>`;
      }).join("");
      const photoPlace = { slug: d.image_slug, name: d.image_slug, wiki: "", category: dest.category, image_url: "" };
      const card = (window.YS_PLACES || {})[d.image_slug] || photoPlace;
      return `<div class="it-day">
          <div class="day-badge"><small>${YS.t("Day")}</small><b>${d.day}</b></div>
          <div class="timeline"><i></i></div>
          <div><h4>${YS.escape(d.title)}</h4>
            <div class="it-meta"><i data-lucide="route"></i>${YS.escape(d.subtitle)}</div>
            <ul class="it-stops">${stops}</ul></div>
          <div class="it-photo">${YS.imgTag(card, "it-img")}</div>
        </div>`;
    }).join("");
    const alts = (alternatives || []).length ? `<div class="mt-2"><div class="small bold mb-1">${YS.t("Other places that fit")}</div>
        <div class="msg-places">${alternatives.map((p) => `<a class="msg-place" href="/planner?destination=${p.slug}&days=${plan.days}&travelers=${plan.travelers}&start=${encodeURIComponent(plan.start_city)}">${YS.imgTag(p)}<div><b>${YS.escape(p.display_name)}</b><span class="muted">₹${money(p.estimated_total)}</span></div></a>`).join("")}</div></div>` : "";
    box.innerHTML = `
      <div class="card-head"><h3>${YS.t("AI Suggested Itinerary")} (${plan.days} ${YS.t("Days")}) - ${YS.escape(dest.display_name)}</h3>
        <a href="#plan-form" class="btn btn-outline btn-sm"><i data-lucide="pencil"></i>${YS.t("Customize")}</a></div>
      <div class="card-body" style="padding-top:8px">
        ${budgetBanner(plan)}
        ${days}
        ${alts}
        <div class="row between wrap mt-2">
          <button type="button" class="btn btn-outline" id="regen"><i data-lucide="refresh-cw"></i>${YS.t("Regenerate Itinerary")}</button>
          <button type="button" class="btn btn-light" id="save-trip"><i data-lucide="bookmark"></i>${YS.t("Save Trip")}</button>
          <a class="btn btn-primary" href="/account/trips/${tripId}/pdf"><i data-lucide="download"></i>${YS.t("Download Itinerary (PDF)")}</a>
        </div>
      </div>`;
    renderCost(plan);
    YS.icons(box);
    YS.loadImages(box);
    document.getElementById("regen").addEventListener("click", regenerate);
    document.getElementById("save-trip").addEventListener("click", saveTrip);
  }

  function renderCost(plan) {
    const c = plan.costs;
    const el = document.getElementById("cost-summary");
    if (!el) return;
    el.innerHTML = `
      <div class="row between"><div><div class="small muted">${YS.t("Estimated Trip Cost")}</div>
        <div class="row" style="gap:8px;align-items:baseline"><span class="big">₹${money(c.total)}</span><span class="small muted">(${YS.t("for")} ${plan.travelers} ${YS.t("people")})</span></div></div>
        <button class="link-sm" style="background:none;border:0;cursor:pointer;color:var(--primary)" id="toggle-break">${YS.t("View Cost Breakdown")} <i data-lucide="arrow-right"></i></button></div>
      <div id="breakdown" class="hidden mt-2">
        <div class="cost-row"><span>${YS.t("Transport")}</span><b>₹${money(c.transport)}</b></div>
        <div class="cost-row"><span>${YS.t("Local travel")}</span><b>₹${money(c.local_transport)}</b></div>
        <div class="cost-row"><span>${YS.t("Stay")} (${c.nights} ${YS.t("nights")}, ${c.rooms} ${YS.t("rooms")})</span><b>₹${money(c.accommodation)}</b></div>
        <div class="cost-row"><span>${YS.t("Food")}</span><b>₹${money(c.food)}</b></div>
        <div class="cost-row"><span>${YS.t("Entry fees")}</span><b>₹${money(c.entry_fees)}</b></div>
        <div class="cost-row"><span>${YS.t("Misc (5%)")}</span><b>₹${money(c.misc)}</b></div>
        <div class="cost-row"><span>${YS.t("Per person")}</span><b>₹${money(c.per_person)}</b></div>
        <p class="xs muted mt-1 mb-0">${YS.t("Stay")}: ${YS.t(plan.stay.type)} (~₹${money(plan.stay.rate)}/${YS.t("night")}) · ${plan.total_km} km</p>
      </div>`;
    YS.icons(el);
    el.querySelector("#toggle-break").addEventListener("click", () => el.querySelector("#breakdown").classList.toggle("hidden"));
  }

  function collect(form) {
    const fd = new FormData(form);
    return {
      start: fd.get("start"), destination: fd.get("destination"), days: fd.get("days"), travelers: fd.get("travelers"),
      budget: fd.get("budget"), style: fd.get("style"), transport: fd.get("transport"),
      interests: fd.getAll("interests"), lang: YS.lang,
    };
  }

  async function generate(payload) {
    lastRequest = payload;
    const box = document.getElementById("itinerary");
    box.innerHTML = `<div class="loading-overlay"><div class="spinner"></div>${YS.t("Generating your itinerary...")}</div>`;
    box.scrollIntoView({ behavior: "smooth", block: "start" });
    const r = await YS.post("/api/itinerary", payload);
    if (!r.ok) {
      box.innerHTML = `<div class="empty-state"><i data-lucide="alert-circle"></i>${YS.escape(r.body.error || YS.t("Something went wrong. Please try again."))}</div>`;
      YS.icons(box);
      return;
    }
    renderPlan(r.body.plan, r.body.trip_id, r.body.alternatives);
  }

  function regenerate() {
    if (!lastRequest) { generate(collect(document.getElementById("plan-form"))); return; }
    // shuffle interests a little to explore different stops
    const req = Object.assign({}, lastRequest);
    const pool = ["Nature", "Heritage", "Adventure", "Relaxation", "Spiritual", "Wildlife"];
    req.interests = Array.from(new Set((req.interests || []).concat(pool[Math.floor(Math.random() * pool.length)])));
    generate(req);
  }

  async function saveTrip() {
    if (!lastTripId) return;
    const r = await YS.post(`/api/trips/${lastTripId}/save`, {});
    if (r.status === 401) {
      YS.toast(YS.t("Please log in to save trips."), "info");
      setTimeout(() => (location.href = "/login?next=/planner"), 900);
      return;
    }
    if (r.ok) {
      YS.toast(YS.t("Trip saved to My Trips"), "success");
      const btn = document.getElementById("save-trip");
      btn.innerHTML = `<i data-lucide="bookmark-check"></i>${YS.t("Saved")}`;
      YS.icons(btn);
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("plan-form");
    if (!form) return;
    try { window.YS_PLACES = JSON.parse(document.getElementById("places-json").textContent); } catch (e) { window.YS_PLACES = {}; }
    form.addEventListener("submit", (e) => { e.preventDefault(); generate(collect(form)); });
    form.querySelectorAll(".interest").forEach((lbl) => lbl.addEventListener("click", (e) => {
      e.preventDefault();
      const cb = lbl.querySelector("input");
      cb.checked = !cb.checked;
      lbl.classList.toggle("active", cb.checked);
    }));
    document.querySelectorAll("[data-ask-plan]").forEach((b) => b.addEventListener("click", () => window.plannerChat && window.plannerChat.send(b.getAttribute("data-ask-plan"))));
    const chatRoot = document.getElementById("planner-chat");
    if (chatRoot) {
      window.plannerChat = new YS.ChatWidget(chatRoot, {
        sessionKey: "ys_planner_chat",
        onItinerary: (plan, tripId) => { lastRequest = null; renderPlan(plan, tripId, []); },
      });
      window.plannerChat.restore();
    }
    if (form.getAttribute("data-autorun") === "1") generate(collect(form));
  });
})();
