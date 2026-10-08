/* YatraSathi - conversational AI chat widget (text + voice, multilingual) */
(function () {
  "use strict";
  const YS = window.YS;

  function now() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  class ChatWidget {
    constructor(root, opts) {
      this.root = root;
      this.opts = Object.assign({ sessionKey: "ys_chat_session", onItinerary: null, autoSpeak: false }, opts || {});
      this.lang = this.opts.lang || YS.lang;
      this.list = root.querySelector(".chat-messages");
      this.form = root.querySelector("form.chat-form");
      this.input = root.querySelector(".chat-text");
      this.suggestBox = root.querySelector(".suggest-row");
      this.micButtons = root.querySelectorAll("[data-mic]");
      this.sessionId = this.opts.sessionId || null;
      this.busy = false;
      this.voiceMode = false;
      this.bind();
    }

    bind() {
      this.form.addEventListener("submit", (e) => { e.preventDefault(); this.send(this.input.value); });
      this.micButtons.forEach((b) => b.addEventListener("click", () => this.toggleMic(b)));
      this.root.addEventListener("click", (e) => {
        const chip = e.target.closest("[data-ask]");
        if (chip) { e.preventDefault(); this.send(chip.getAttribute("data-ask")); }
        const langBtn = e.target.closest("[data-chat-lang]");
        if (langBtn) this.setLang(langBtn.getAttribute("data-chat-lang"));
        const speakToggle = e.target.closest("[data-voice-toggle]");
        if (speakToggle) {
          this.opts.autoSpeak = !this.opts.autoSpeak;
          speakToggle.classList.toggle("active", this.opts.autoSpeak);
          if (!this.opts.autoSpeak) YS.stopSpeaking();
          YS.toast(this.opts.autoSpeak ? YS.t("Voice replies on") : YS.t("Voice replies off"), "info");
        }
        const newChat = e.target.closest("[data-new-chat]");
        if (newChat) { e.preventDefault(); this.reset(); }
      });
    }

    setLang(lang) {
      this.lang = lang;
      this.root.querySelectorAll("[data-chat-lang]").forEach((b) => b.classList.toggle("active", b.getAttribute("data-chat-lang") === lang));
    }

    reset() {
      this.sessionId = null;
      try { sessionStorage.removeItem(this.opts.sessionKey); } catch (e) { /* ignore */ }
      this.list.innerHTML = "";
      this.welcome();
      if (window.history && location.search.includes("session=")) history.replaceState(null, "", location.pathname);
    }

    welcome() {
      this.addBot({ reply: YS.t("chat_welcome"), suggestions: [], places: [] }, { time: "" });
    }

    async restore() {
      let id = this.sessionId;
      if (!id) { try { id = sessionStorage.getItem(this.opts.sessionKey); } catch (e) { id = null; } }
      if (!id) { this.welcome(); return; }
      try {
        const res = await fetch("/api/chat/" + id);
        if (!res.ok) throw new Error("gone");
        const data = await res.json();
        this.sessionId = data.session_id;
        this.list.innerHTML = "";
        this.welcome();
        data.messages.forEach((m) => {
          if (m.role === "user") this.addUser(m.content, m.time);
          else this.addBot({ reply: m.content, places: (m.meta && m.meta.places) || [], trip_id: m.meta && m.meta.trip_id,
            sources: (m.meta && m.meta.sources) || [], language: data.language }, { time: m.time, restored: true });
        });
      } catch (e) {
        this.sessionId = null;
        this.welcome();
      }
    }

    scroll() { this.list.scrollTop = this.list.scrollHeight; }

    addUser(text, time) {
      const el = document.createElement("div");
      el.className = "msg user";
      el.innerHTML = `<div class="bubble">${YS.escape(text)}<div class="time">${time || now()} <i data-lucide="check-check"></i></div></div>`;
      this.list.appendChild(el);
      YS.icons(el);
      this.scroll();
    }

    addTyping() {
      const el = document.createElement("div");
      el.className = "msg bot typing-msg";
      el.innerHTML = `<div class="bot-face"><img src="/static/images/bot.svg" alt=""></div><div class="bubble"><span class="typing"><span></span><span></span><span></span></span></div>`;
      this.list.appendChild(el);
      this.scroll();
      return el;
    }

    placesHtml(places) {
      if (!places || !places.length) return "";
      return `<div class="msg-places">${places.slice(0, 6).map((p) => `
        <a class="msg-place" href="/place/${p.slug}">${YS.imgTag(p)}
          <div><b>${YS.escape(p.display_name || p.name)}</b><span class="muted">${YS.escape(p.extra || p.category || "")}</span></div></a>`).join("")}</div>`;
    }

    itineraryHtml(data) {
      const plan = data.itinerary;
      if (!plan && !data.trip_id) return "";
      const id = data.trip_id;
      let html = "";
      if (plan) {
        html += `<div class="msg-tools">`;
        if (this.opts.onItinerary) html += `<button type="button" data-show-plan><i data-lucide="map"></i>${YS.t("Show itinerary")}</button>`;
        html += `</div>`;
      }
      if (id) {
        html += `<div class="msg-tools"><a href="/account/trips/${id}"><i data-lucide="calendar-days"></i>${YS.t("Open full plan")}</a>
          <a href="/account/trips/${id}/pdf"><i data-lucide="download"></i>PDF</a></div>`;
      }
      return html;
    }

    addBot(data, extra) {
      extra = extra || {};
      const el = document.createElement("div");
      el.className = "msg bot";
      const lang = data.language || this.lang;
      const sources = (data.sources || []).filter((s) => s.title).slice(0, 3);
      el.innerHTML = `<div class="bot-face"><img src="/static/images/bot.svg" alt=""></div>
        <div class="bubble">
          <div class="md">${YS.markdown(data.reply)}</div>
          ${this.placesHtml(data.places)}
          ${this.itineraryHtml(data)}
          ${sources.length ? `<div class="msg-sources"><i data-lucide="book-open" style="width:12px;height:12px"></i> ${YS.t("Sources")}: ${sources.map((s) => YS.escape(s.title)).join(" · ")}</div>` : ""}
          <div class="msg-tools">
            <button type="button" data-say><i data-lucide="volume-2"></i>${YS.t("Listen")}</button>
            <button type="button" data-copy><i data-lucide="copy"></i>${YS.t("Copy")}</button>
            ${data.llm ? `<span class="pill purple xs">LLM + RAG</span>` : ""}
          </div>
          <div class="time">${extra.time === undefined ? now() : extra.time}</div>
        </div>`;
      el.querySelector("[data-say]").addEventListener("click", () => YS.speak(data.reply, lang));
      el.querySelector("[data-copy]").addEventListener("click", () => {
        navigator.clipboard && navigator.clipboard.writeText(YS.plainText(data.reply));
        YS.toast(YS.t("Copied"), "success");
      });
      const show = el.querySelector("[data-show-plan]");
      if (show && this.opts.onItinerary) show.addEventListener("click", () => this.opts.onItinerary(data.itinerary, data.trip_id));
      this.list.appendChild(el);
      YS.icons(el);
      YS.loadImages(el);
      this.scroll();
      return el;
    }

    setSuggestions(items) {
      if (!this.suggestBox || !items || !items.length) return;
      this.suggestBox.innerHTML = items.slice(0, 4).map((s) => `<button type="button" class="chip" data-ask="${YS.escape(s)}">${YS.escape(s)}</button>`).join("");
    }

    async send(text) {
      text = (text || "").trim();
      if (!text || this.busy) return;
      this.busy = true;
      this.input.value = "";
      this.addUser(text);
      const typing = this.addTyping();
      try {
        const r = await YS.post("/api/chat", { message: text, session_id: this.sessionId, lang: this.lang });
        typing.remove();
        if (!r.ok) throw new Error(r.body.error || "error");
        const data = r.body;
        this.sessionId = data.session_id;
        try { sessionStorage.setItem(this.opts.sessionKey, data.session_id); } catch (e) { /* ignore */ }
        this.addBot(data);
        this.setSuggestions(data.suggestions);
        if (data.itinerary && this.opts.onItinerary) this.opts.onItinerary(data.itinerary, data.trip_id);
        if (this.opts.autoSpeak || this.voiceMode) YS.speak(data.reply, data.language);
        if (this.opts.onReply) this.opts.onReply(data);
      } catch (e) {
        typing.remove();
        this.addBot({ reply: YS.t("Sorry, I could not reach the server. Please try again."), places: [] });
      } finally {
        this.busy = false;
        this.voiceMode = false;
      }
    }

    toggleMic(btn) {
      if (this.rec) { this.rec.stop(); return; }
      YS.stopSpeaking();
      const all = this.micButtons;
      all.forEach((b) => b.classList.add("listening"));
      this.input.placeholder = YS.t("Listening...");
      let finalText = "";
      this.rec = YS.listen(this.lang, (text, isFinal) => {
        this.input.value = text;
        if (isFinal) finalText = text;
      }, () => {
        all.forEach((b) => b.classList.remove("listening"));
        this.input.placeholder = YS.t("Type your message...");
        this.rec = null;
        const text = finalText || this.input.value;
        if (text.trim()) { this.voiceMode = true; this.send(text); }
      });
      if (!this.rec) all.forEach((b) => b.classList.remove("listening"));
    }
  }

  YS.ChatWidget = ChatWidget;
})();
