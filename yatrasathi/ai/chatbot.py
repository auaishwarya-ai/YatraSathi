"""
Conversational AI orchestrator (NLP & Conversational AI Module).

Pipeline for every user message (mirrors the system architecture):
  User Input -> Input Processing (language detection, tokenisation)
  -> Query Understanding (entities) + Intent Recognition (ML classifier)
  -> Context merge (remembers destination, days, budget ... across turns)
  -> RAG Retrieval / Recommendation Engine / Trip Planner
  -> AI Response Generation (LLM if configured, otherwise templates)
  -> Output (text + places + itinerary + follow-up suggestions)
"""
import re

from .geo import fmt_hours, road_km, travel_hours
from .intent import IntentClassifier
from .llm import LLMClient
from .nlp import QueryUnderstanding
from .planner import TripPlanner
from .rag import KnowledgeIndex
from .recommender import Recommender
from .responses import category_name, money, month_range, t
from .text import detect_language

PLACE_INTENTS = {"place_info", "story", "best_time", "food", "how_to_reach", "timings_fee", "attractions", "nearby", "budget"}
GUIDE_INTENTS = {"festival", "safety", "weather", "transport"}
FOLLOW_UP = r"\b(there|that place|it|this place|its)\b|ಅಲ್ಲಿ|ಅಲ್ಲಿನ|ಅದರ|वहाँ|वहां|उसका|उसकी|उसके"
INTEREST_LABELS = {
    "kn": {"Nature": "ಪ್ರಕೃತಿ", "Adventure": "ಸಾಹಸ", "Heritage": "ಪರಂಪರೆ", "Relaxation": "ವಿಶ್ರಾಂತಿ", "Spiritual": "ಆಧ್ಯಾತ್ಮಿಕ",
           "Wildlife": "ವನ್ಯಜೀವಿ", "Beaches": "ಕಡಲತೀರ", "Waterfalls": "ಜಲಪಾತ", "Hill Stations": "ಗಿರಿಧಾಮ"},
    "hi": {"Nature": "प्रकृति", "Adventure": "साहसिक", "Heritage": "विरासत", "Relaxation": "आराम", "Spiritual": "आध्यात्मिक",
           "Wildlife": "वन्यजीव", "Beaches": "समुद्र तट", "Waterfalls": "झरने", "Hill Stations": "हिल स्टेशन"},
}


class ChatEngine:
    def __init__(self, destinations, cities, guide, intents_path, admin_docs=None, llm_config=None):
        self.destinations = destinations
        self.by_slug = {d["slug"]: d for d in destinations}
        self.cities = cities
        self.guide = guide
        self.nlu = QueryUnderstanding(destinations, cities)
        self.intents = IntentClassifier(intents_path)
        self.rag = KnowledgeIndex(destinations, guide.get("sections", []), admin_docs or [])
        self.recommender = Recommender(destinations)
        self.planner = TripPlanner(destinations, cities, self.recommender)
        llm_config = llm_config or {}
        self.llm = LLMClient(llm_config.get("api_key", ""), llm_config.get("model", "gpt-4o-mini"),
                             llm_config.get("base_url", "https://api.openai.com/v1"))

    # ------------------------------------------------------------------ helpers
    def name(self, slug, lang):
        d = self.by_slug[slug]
        return (d.get(f"name_{lang}") or d["name"]) if lang in ("kn", "hi") else d["name"]

    def city_label(self, city, lang):
        for c in self.cities:
            if c["name"] == city:
                return c.get(f"name_{lang}") or city if lang in ("kn", "hi") else city
        return city

    def card(self, slug, lang, extra=None):
        d = self.by_slug[slug]
        return {"slug": slug, "name": d["name"], "display_name": self.name(slug, lang), "district": d["district"],
                "category": category_name(lang, d["category"]), "category_en": d["category"], "rating": d.get("rating"), "wiki": d.get("wiki", ""),
                "image_url": d.get("image_url", ""), "extra": extra or ""}

    def suggestions(self, lang, kind="default", slug=None):
        items = t(lang, "suggestions")[kind]
        name = self.name(slug, lang) if slug else ""
        return [s.format(name=name) for s in items]

    # ------------------------------------------------------------------ main entry
    def reply(self, message, lang="en", context=None, user=None, history=None):
        message = (message or "").strip()
        context = dict(context or {})
        user = user or {}
        detected = detect_language(message)
        lang = detected if detected in ("kn", "hi") else (lang if lang in ("en", "kn", "hi") else "en")

        u = self.nlu.understand(message)
        intent, confidence, method = self.intents.predict(message, u)

        # ---- context-awareness -------------------------------------------------
        has_new_dest = bool(u["destination"])
        refers_back = bool(re.search(FOLLOW_UP, u["normalized"]))
        modifiers = any([u["travelers"], u["days"], u["budget"], u["style"]])
        if (not has_new_dest and context.get("last_intent") == "plan_trip" and context.get("destination")
                and modifiers and intent in ("budget", "recommend", "plan_trip", "unknown", "thanks")):
            intent, method = "plan_trip", "context"
        destination = u["destination"]
        if method == "context" and not destination:
            destination = context.get("destination")
        if not destination and (intent in PLACE_INTENTS or refers_back) and intent not in ("recommend",):
            destination = context.get("destination")
        if intent == "nearby" and not destination and u["cities"]:
            destination = None  # handled as city-based nearby

        # Follow-up questions reuse the trip details from earlier turns; a new
        # destination or a fresh recommendation request starts from defaults.
        follow = not has_new_dest and intent not in ("recommend",)
        params = {
            "start": u["start_city"] or context.get("start") or user.get("home_city") or "Bangalore",
            "days": u["days"] or (context.get("days") if follow else None),
            "travelers": u["travelers"] or (context.get("travelers") if follow else None) or 2,
            "budget": u["budget"] or (context.get("budget") if follow and intent == "plan_trip" else None),
            "interests": u["interests"] or context.get("interests") or user.get("interests") or [],
            "style": u["style"] or (context.get("style") if follow else None) or "standard",
            "month": u["month"],
        }

        handler = getattr(self, f"_handle_{intent}", None)
        if intent in GUIDE_INTENTS:
            result = self._handle_guide(intent, message, lang, history)
        elif handler:
            result = handler(message=message, lang=lang, destination=destination, params=params, u=u,
                             user=user, history=history)
        else:
            result = self._handle_unknown(message=message, lang=lang, destination=destination, params=params, u=u,
                                          user=user, history=history)

        # ---- update conversation context ----------------------------------------
        new_dest = result.get("destination", destination)
        if new_dest:
            context["destination"] = new_dest
        for key in ("start", "travelers", "style"):
            if key == "start" and u["start_city"]:
                context["start"] = u["start_city"]
            elif key != "start" and (u.get(key) or (key == "style" and u["style"])):
                context[key] = params[key]
        if u["days"]:
            context["days"] = u["days"]
        if u["budget"]:
            context["budget"] = u["budget"]
        if u["interests"]:
            context["interests"] = u["interests"]
        context["last_intent"] = intent
        context["language"] = lang

        result.setdefault("places", [])
        result.setdefault("itinerary", None)
        result.setdefault("sources", [])
        result.setdefault("llm", False)
        result.setdefault("suggestions", self.suggestions(lang, "place" if new_dest else "default", new_dest))
        result.update({
            "language": lang, "intent": intent, "confidence": round(float(confidence), 2), "method": method,
            "entities": {k: u[k] for k in ("destination", "start_city", "days", "budget", "travelers", "interests", "style", "month")},
            "context": context,
        })
        result["entities"]["destination"] = new_dest
        return result

    # ------------------------------------------------------------------ simple intents
    def _handle_greeting(self, lang, **_):
        return {"reply": t(lang, "greeting")}

    def _handle_help(self, lang, **_):
        return {"reply": t(lang, "help")}

    def _handle_thanks(self, lang, **_):
        return {"reply": t(lang, "thanks")}

    def _handle_goodbye(self, lang, **_):
        return {"reply": t(lang, "goodbye")}

    # ------------------------------------------------------------------ RAG helpers
    def _rag(self, message, slug=None, intent=None, k=4):
        query = message
        if slug:
            query = f"{self.by_slug[slug]['name']} {message}"
        return self.rag.search(query, k=k, slug=slug, intent=intent)

    @staticmethod
    def _sources(passages):
        seen, out = set(), []
        for p in passages:
            if p["title"] in seen:
                continue
            seen.add(p["title"])
            out.append({"title": p["title"], "slug": p.get("slug"), "source": p.get("source"), "score": p.get("score")})
        return out[:3]

    def _llm_or(self, message, passages, lang, history, offline_text, facts=None):
        text = self.llm.answer(message, passages, lang, history, facts) if self.llm.enabled else None
        return (text, True) if text else (offline_text, False)

    def _need_place(self, lang):
        return {"reply": t(lang, "ask_place"), "places": [self.card(s, lang) for s in ("hampi", "coorg", "mysore-palace", "jog-falls")]}

    def _facts(self, d, lang):
        lines = [f"**{self.name(d['slug'], lang)}** · {category_name(lang, d['category'])} · {d['district']} · ⭐ {d['rating']}"]
        return "\n".join(lines)

    def _fee_text(self, d, lang):
        if not d.get("entry_fee_indian") and not d.get("entry_fee_foreign"):
            return t(lang, "free")
        return f"₹{d['entry_fee_indian']} ({t(lang, 'indians')}), ₹{d['entry_fee_foreign']} ({t(lang, 'foreigners')})"

    # ------------------------------------------------------------------ place intents
    def _handle_place_info(self, message, lang, destination, history, **_):
        if not destination:
            return self._handle_unknown(message=message, lang=lang, destination=None, history=history)
        d = self.by_slug[destination]
        passages = self._rag(message, destination, "place_info")
        summary = d["description"] if lang == "en" else (d.get(f"summary_{lang}") or d["description"])
        lines = [self._facts(d, lang), "", summary, "",
                 f"- 📅 {t(lang, 'best_label')}: {month_range(lang, d['best_from'], d['best_to'])}",
                 f"- 🕘 {t(lang, 'timings')}: {d.get('timings')}",
                 f"- 🎟️ {t(lang, 'entry')}: {self._fee_text(d, lang)}",
                 f"- ⏳ {t(lang, 'ideal')}: {d.get('ideal_days', 1)} {t(lang, 'days')}"]
        if lang == "en" and d.get("tips"):
            lines += ["", f"💡 **{t(lang, 'tip')}:** {d['tips']}"]
        text, used = self._llm_or(message, passages, lang, history, "\n".join(lines))
        return {"reply": text, "llm": used, "destination": destination, "sources": self._sources(passages),
                "places": [self.card(destination, lang)]}

    def _handle_story(self, message, lang, destination, history, **_):
        if not destination:
            return self._need_place(lang)
        d = self.by_slug[destination]
        passages = self._rag(message, destination, "story")
        name = self.name(destination, lang)
        if lang == "en":
            body = f"{d.get('history', '')}\n\n{d['description']} Walking through {d['name']} today feels like stepping back in time."
        else:
            body = d.get(f"summary_{lang}") or d["description"]
            if d.get("history"):
                body += "\n\n📜 " + d["history"]
        offline = f"{t(lang, 'story_title').format(name=name)}\n\n{body}\n\n{t(lang, 'story_outro').format(name=name)}"
        text, used = self._llm_or(f"Tell the story / history of {d['name']} as an engaging narrative. {message}",
                                  passages, lang, history, offline)
        return {"reply": text, "llm": used, "destination": destination, "sources": self._sources(passages),
                "places": [self.card(destination, lang)], "speak": True,
                "suggestions": self.suggestions(lang, "place", destination)}

    def _handle_best_time(self, message, lang, destination, history, **_):
        if not destination:
            passages = self.rag.search(message, k=3, intent="weather")
            text = t(lang, "from_guide") + "\n" + "\n".join(f"- **{p['title'].split(' - ')[-1]}**: {p['text']}" for p in passages[:2])
            return {"reply": text, "sources": self._sources(passages)}
        d = self.by_slug[destination]
        passages = self._rag(message, destination, "best_time")
        lines = [t(lang, "best_time").format(name=self.name(destination, lang), months=month_range(lang, d["best_from"], d["best_to"]))]
        if d["category"] == "Waterfalls":
            lines.append(t(lang, "monsoon_note"))
        lines.append(f"- 🕘 {t(lang, 'timings')}: {d.get('timings')}")
        if lang == "en" and d.get("tips"):
            lines.append(f"- 💡 {d['tips']}")
        text, used = self._llm_or(message, passages, lang, history, "\n".join(lines))
        return {"reply": text, "llm": used, "destination": destination, "sources": self._sources(passages)}

    def _handle_food(self, message, lang, destination, history, **_):
        if not destination:
            passages = self.rag.search(message, k=4, intent="food")
            cuisine = next(s for s in self.guide["sections"] if s["slug"] == "cuisine")
            lines = [f"🍛 **{cuisine.get('title_' + lang, cuisine['title']) if lang != 'en' else cuisine['title']}**"]
            lines += [f"- **{c['heading']}**: {c['text']}" for c in cuisine["content"][:4]]
            text, used = self._llm_or(message, passages, lang, history, "\n".join(lines))
            return {"reply": text, "llm": used, "sources": self._sources(passages)}
        d = self.by_slug[destination]
        passages = self._rag(message, destination, "food")
        lines = [t(lang, "food").format(name=self.name(destination, lang))] + [f"- 🍽️ {f}" for f in d.get("food", [])]
        text, used = self._llm_or(message, passages, lang, history, "\n".join(lines))
        return {"reply": text, "llm": used, "destination": destination, "sources": self._sources(passages)}

    def _handle_how_to_reach(self, message, lang, destination, params, history, **_):
        if not destination:
            return self._need_place(lang)
        d = self.by_slug[destination]
        passages = self._rag(message, destination, "how_to_reach")
        start_name, start_pos, _ = self.planner.resolve_start(params["start"])
        km = road_km(*start_pos, d["lat"], d["lng"])
        name = self.name(destination, lang)
        lines = [f"🧭 {t(lang, 'how_reach').format(name=name)}",
                 t(lang, "distance").format(km=int(round(km)), city=self.city_label(start_name, lang), hours=fmt_hours(travel_hours(km)), name=name)]
        if lang == "en":
            lines.append(d.get("how_to_reach", ""))
        text, used = self._llm_or(message, passages, lang, history, "\n\n".join(lines),
                                  facts=f"Road distance from {start_name} to {d['name']} is about {int(km)} km ({fmt_hours(travel_hours(km))}).")
        return {"reply": text, "llm": used, "destination": destination, "sources": self._sources(passages)}

    def _handle_timings_fee(self, message, lang, destination, history, **_):
        if not destination:
            return self._need_place(lang)
        d = self.by_slug[destination]
        passages = self._rag(message, destination, "timings_fee")
        lines = [f"**{self.name(destination, lang)}**",
                 f"- 🕘 {t(lang, 'timings')}: {d.get('timings')}",
                 f"- 🎟️ {t(lang, 'entry')}: {self._fee_text(d, lang)}"]
        if lang == "en" and d.get("tips"):
            lines.append(f"- 💡 {d['tips']}")
        lines.append(f"\n_{t(lang, 'estimate_note')}_")
        text, used = self._llm_or(message, passages, lang, history, "\n".join(lines))
        return {"reply": text, "llm": used, "destination": destination, "sources": self._sources(passages)}

    def _handle_attractions(self, message, lang, destination, history, **_):
        if not destination:
            return self._handle_recommend(message=message, lang=lang, destination=None, params={"start": "Bangalore", "days": None,
                                          "travelers": 2, "budget": None, "interests": [], "style": "standard", "month": None},
                                          u={"interests": []}, user={}, history=history)
        d = self.by_slug[destination]
        passages = self._rag(message, destination, "attractions")
        lines = [t(lang, "attractions").format(name=self.name(destination, lang))] + [f"- 📍 {a}" for a in d.get("attractions", [])]
        text, used = self._llm_or(message, passages, lang, history, "\n".join(lines))
        similar = self.recommender.similar(destination, 3)
        return {"reply": text, "llm": used, "destination": destination, "sources": self._sources(passages),
                "places": [self.card(destination, lang)] + [self.card(s, lang) for s in similar]}

    def _handle_nearby(self, message, lang, destination, u, **_):
        if destination:
            d = self.by_slug[destination]
            lat, lng, name = d["lat"], d["lng"], self.name(destination, lang)
        elif u.get("cities"):
            c = next(c for c in self.cities if c["name"] == u["cities"][0])
            lat, lng, name = c["lat"], c["lng"], self.city_label(c["name"], lang)
        else:
            return self._need_place(lang)
        near = self.recommender.nearby(lat, lng, limit=6, exclude={destination} if destination else None)
        lines = [t(lang, "nearby").format(name=name)]
        lines += [f"- **{self.name(n['slug'], lang)}** - {int(round(n['distance_km'] * 1.3))} km" for n in near]
        return {"reply": "\n".join(lines), "destination": destination,
                "places": [self.card(n["slug"], lang, f"{int(round(n['distance_km'] * 1.3))} km") for n in near]}

    def _handle_budget(self, message, lang, destination, params, **kw):
        if not destination:
            return self._handle_recommend(message=message, lang=lang, destination=None, params=params, **kw)
        d = self.by_slug[destination]
        days = params["days"] or d.get("ideal_days", 2)
        plan = self.planner.plan(destination, params["start"], days, params["travelers"], params["budget"],
                                 params["interests"], params["style"], "auto", lang)
        c = plan["costs"]
        lines = [t(lang, "budget_intro").format(days=days, name=self.name(destination, lang), travelers=plan["travelers"],
                                                city=plan["start_label"]),
                 f"- 🚌 {t(lang, 'transport')}: ₹{money(c['transport'] + c['local_transport'])}",
                 f"- 🏨 {t(lang, 'stay')}: ₹{money(c['accommodation'])}",
                 f"- 🍛 {t(lang, 'food_cost')}: ₹{money(c['food'])}",
                 f"- 🎟️ {t(lang, 'entry_fees')}: ₹{money(c['entry_fees'])}",
                 f"- ➕ {t(lang, 'misc')}: ₹{money(c['misc'])}",
                 "", self._total_line(plan, lang), self._budget_line(plan, lang), f"_{t(lang, 'estimate_note')}_"]
        return {"reply": "\n".join(x for x in lines if x is not None), "destination": destination, "itinerary": plan,
                "suggestions": self.suggestions(lang, "plan", destination)}

    # ------------------------------------------------------------------ planning
    def _total_line(self, plan, lang):
        c = plan["costs"]
        return t(lang, "plan_total").format(total=money(c["total"]), pp=money(c["per_person"]),
                                            style=t(lang, "styles")[plan["style"]], transport=t(lang, "transports")[plan["transport"]])

    def _budget_line(self, plan, lang):
        status = plan["budget_status"]
        if status == "within":
            return t(lang, "budget_ok").format(budget=money(plan["budget"]), remaining=money(plan["remaining"]))
        if status == "optimized":
            changes = []
            for adj in plan["adjustments"]:
                if adj == "dropped_paid":
                    changes.append(t(lang, "changes")["dropped_paid"])
                else:
                    kind, rest = adj.split(":")
                    a, b = rest.split("->")
                    names = t(lang, "styles") if kind == "style" else t(lang, "transports")
                    changes.append(t(lang, "changes")[kind].format(a=names.get(a, a), b=names.get(b, b)))
            return t(lang, "budget_optimized").format(budget=money(plan["budget"]), changes=", ".join(changes))
        if status == "over":
            line = t(lang, "budget_over").format(total=money(plan["costs"]["total"]), budget=money(plan["budget"]))
            if plan.get("suggested_days"):
                line += t(lang, "suggest_days").format(days=plan["suggested_days"])
            return line
        return ""

    def plan_text(self, plan, lang):
        name = plan["destination"]["display_name"]
        lines = [t(lang, "plan_intro").format(days=plan["days"], name=name, city=plan["start_label"], travelers=plan["travelers"]), ""]
        for day in plan["day_plans"]:
            visits = [s["name"] for s in day["stops"] if s["kind"] in ("visit", "activity")]
            lines.append(f"**{t(lang, 'day')} {day['day']}: {day['title']}** ({day['subtitle']})")
            if visits:
                lines.append("✓ " + " · ".join(visits))
        lines += ["", self._total_line(plan, lang)]
        budget_line = self._budget_line(plan, lang)
        if budget_line:
            lines.append(budget_line)
        return "\n".join(lines)

    def _handle_plan_trip(self, message, lang, destination, params, user, **kw):
        alternatives = []
        if not destination:
            fits, cheapest = self.planner.suggest_by_budget(params["start"], params["days"] or 2, params["travelers"],
                                                           params["budget"], params["interests"], params["style"],
                                                           params["month"], limit=4, lang=lang)
            options = fits or cheapest
            if not options:
                return self._need_place(lang)
            destination = options[0]["slug"]
            alternatives = [self.card(o["slug"], lang, t(lang, "est_cost").format(cost=money(o["total"]))) for o in options[1:]]
        d = self.by_slug[destination]
        days = params["days"] or d.get("ideal_days", 2)
        plan = self.planner.plan(destination, params["start"], days, params["travelers"], params["budget"],
                                 params["interests"], params["style"], "auto", lang)
        return {"reply": self.plan_text(plan, lang), "destination": destination, "itinerary": plan,
                "places": alternatives, "suggestions": self.suggestions(lang, "plan", destination)}

    def _handle_recommend(self, message, lang, params, u, user, **_):
        interests = u.get("interests") or params.get("interests") or []
        start = params["start"]
        start_name, start_pos, _ = self.planner.resolve_start(start)
        city = self.city_label(start_name, lang)
        labels = [INTEREST_LABELS.get(lang, {}).get(i, i) for i in interests]
        if params.get("budget"):
            days = params["days"] or 2
            fits, cheapest = self.planner.suggest_by_budget(start, days, params["travelers"], params["budget"], interests,
                                                           params["style"], params["month"], limit=5, lang=lang)
            if fits:
                criteria = t(lang, "within_budget").format(budget=money(params["budget"]), days=days,
                                                           travelers=params["travelers"], city=city)
                lines = [t(lang, "recommend_intro").format(criteria=criteria)]
                places = []
                for o in fits:
                    extra = f"₹{money(o['total'])} · {o['km']} km"
                    lines.append(f"- **{self.name(o['slug'], lang)}** - {t(lang, 'est_cost').format(cost=money(o['total']))} "
                                 f"({o['km']} km, {t(lang, 'styles')[o['style']]}, {t(lang, 'transports')[o['transport']]})")
                    places.append(self.card(o["slug"], lang, extra))
            else:
                lines = [t(lang, "nothing_fits").format(budget=money(params["budget"]), days=days, travelers=params["travelers"], city=city)]
                places = []
                for o in cheapest:
                    lines.append(f"- **{self.name(o['slug'], lang)}** - {t(lang, 'est_cost').format(cost=money(o['total']))}")
                    places.append(self.card(o["slug"], lang, f"₹{money(o['total'])}"))
            lines.append(f"\n_{t(lang, 'estimate_note')}_")
            return {"reply": "\n".join(lines), "places": places, "destination": None,
                    "suggestions": [self.suggestions(lang, "place", p["slug"])[3] for p in places[:2]] + self.suggestions(lang)[2:]}
        recs = self.recommender.recommend(interests=interests, query_text="" if interests else message, origin=start_pos,
                                          month=params.get("month"), limit=6, personal_slugs=user.get("saved"))
        criteria = t(lang, "for_interest").format(interests=", ".join(labels)) if labels else ""
        lines = [t(lang, "recommend_intro").format(criteria=criteria)]
        places = []
        for r in recs:
            d = self.by_slug[r["slug"]]
            lines.append(f"- **{self.name(r['slug'], lang)}** ({category_name(lang, d['category'])}, ⭐ {d['rating']}) - {r['distance_km']} km")
            places.append(self.card(r["slug"], lang, f"{r['distance_km']} km"))
        return {"reply": "\n".join(lines), "places": places, "destination": None}

    # ------------------------------------------------------------------ guide intents
    def _handle_guide(self, intent, message, lang, history):
        section_slug = {"festival": "festivals", "safety": "safety", "weather": "weather", "transport": "transportation"}[intent]
        section = next(s for s in self.guide["sections"] if s["slug"] == section_slug)
        passages = self.rag.search(message, k=4, intent=intent)
        title = section.get(f"title_{lang}") if lang != "en" else section["title"]
        summary = section.get(f"summary_{lang}") if lang != "en" else section["summary"]
        top = [p for p in passages if p.get("section") == section_slug][:3] or passages[:3]
        lines = [f"**{title or section['title']}** - {summary or section['summary']}", ""]
        lines += [f"- **{p['title'].split(' - ', 1)[-1]}**: {p['text']}" for p in top]
        if intent == "safety":
            lines += ["", "🆘 " + t(lang, "emergency")]
        text, used = self._llm_or(message, passages, lang, history, "\n".join(lines))
        return {"reply": text, "llm": used, "sources": self._sources(passages)}

    def _handle_unknown(self, message, lang, destination=None, history=None, **_):
        passages = self._rag(message, destination, None, k=4)
        if passages and passages[0]["score"] > 0.22:
            offline = f"{t(lang, 'from_guide')}\n\n**{passages[0]['title']}**\n{passages[0]['text']}"
            text, used = self._llm_or(message, passages, lang, history, offline)
            return {"reply": text, "llm": used, "sources": self._sources(passages), "destination": passages[0].get("slug") or destination}
        return {"reply": t(lang, "fallback")}
