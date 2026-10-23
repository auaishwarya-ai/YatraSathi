"""
Itinerary & Budget Generation (budget-optimised trip planner).

Given a starting city, destination, number of days, travellers, budget,
interests and travel style it:
  1. selects attractions of the destination and nearby places that match the
     user's interests (using the Recommender scores),
  2. clusters them into days and orders each day's stops with a greedy
     nearest-neighbour route (simple route optimisation),
  3. estimates transport, accommodation, food, entry fees and misc costs,
  4. if a budget is given, searches cheaper style / transport combinations
     (and drops optional paid stops) until the plan fits the budget.
All costs are estimates intended for planning, not quotes.
"""
import math

from .geo import fmt_hours, haversine_km, road_km, travel_hours

STYLES = {
    "budget":   {"room": 1200, "food": 450,  "local_day": 300,  "bus_rate": 1.6, "label": "Budget lodge / homestay"},
    "standard": {"room": 2800, "food": 850,  "local_day": 700,  "bus_rate": 2.3, "label": "3-star hotel / plantation homestay"},
    "luxury":   {"room": 7000, "food": 1800, "local_day": 1500, "bus_rate": 2.6, "label": "Resort / heritage hotel"},
}
STYLE_ORDER = ["luxury", "standard", "budget"]
TRAIN_RATE = 1.1           # Rs per km per person (sleeper / chair car average)
DRIVER_ALLOWANCE = 400     # Rs per day for an outstation cab
TRANSPORTS = ("bus", "car", "train")

TEXT = {
    "en": {"local": "{dest} Local Sightseeing", "excursion": "Excursion to {place}", "overnight": "Overnight stay in {place}",
           "departure": "Departure to {place}", "return": "Return to {place}", "arrive": "Arrive in {place} & check in",
           "explore": "Explore {place}", "day_trip": "Day trip: {start} → {dest}", "breakfast": "Breakfast & local food",
           "shopping": "Shopping for local products", "start": "Start from {place}"},
    "kn": {"local": "{dest} ಸ್ಥಳೀಯ ದೃಶ್ಯವೀಕ್ಷಣೆ", "excursion": "{place} ಪ್ರವಾಸ", "overnight": "ರಾತ್ರಿ ತಂಗುವಿಕೆ: {place}",
           "departure": "ಹಿಂತಿರುಗುವಿಕೆ: {place}", "return": "ಹಿಂತಿರುಗಿ: {place}", "arrive": "{place} ತಲುಪಿ ಚೆಕ್-ಇನ್",
           "explore": "{place} ವೀಕ್ಷಣೆ", "day_trip": "ಒಂದು ದಿನದ ಪ್ರವಾಸ: {start} → {dest}", "breakfast": "ಉಪಹಾರ ಮತ್ತು ಸ್ಥಳೀಯ ಆಹಾರ",
           "shopping": "ಸ್ಥಳೀಯ ಉತ್ಪನ್ನಗಳ ಖರೀದಿ", "start": "ಪ್ರಯಾಣ ಆರಂಭ: {place}"},
    "hi": {"local": "{dest} स्थानीय भ्रमण", "excursion": "{place} की सैर", "overnight": "{place} में रात्रि विश्राम",
           "departure": "{place} के लिए प्रस्थान", "return": "{place} वापसी", "arrive": "{place} पहुँचें और चेक-इन करें",
           "explore": "{place} घूमें", "day_trip": "एक दिन की यात्रा: {start} → {dest}", "breakfast": "नाश्ता और स्थानीय भोजन",
           "shopping": "स्थानीय उत्पादों की खरीदारी", "start": "{place} से यात्रा शुरू"},
}


def _r10(x):
    return int(round(x / 10.0) * 10)


def _fmt_time(hours_float):
    h = int(hours_float) % 24
    m = int(round((hours_float - int(hours_float)) * 60 / 15) * 15)
    if m == 60:
        h, m = (h + 1) % 24, 0
    suffix = "AM" if h < 12 else "PM"
    return f"{(h % 12) or 12}:{m:02d} {suffix}"


class TripPlanner:
    def __init__(self, destinations, cities, recommender):
        self.dest = {d["slug"]: d for d in destinations}
        self.destinations = destinations
        self.cities = {c["name"].lower(): c for c in cities}
        self.recommender = recommender

    # ------------------------------------------------------------------
    def resolve_start(self, start):
        start = (start or "Bangalore").strip()
        key = start.lower()
        for c in self.cities.values():
            if key == c["name"].lower() or key in [a.lower() for a in c["aliases"]]:
                return c["name"], (c["lat"], c["lng"]), c
        if key in self.dest:
            d = self.dest[key]
            return d["name"], (d["lat"], d["lng"]), None
        c = self.cities["bangalore"]
        return c["name"], (c["lat"], c["lng"]), c

    def _local_name(self, d, lang):
        return d.get(f"name_{lang}") or d["name"] if lang in ("kn", "hi") else d["name"]

    def _city_label(self, city_obj, name, lang):
        if city_obj and lang in ("kn", "hi"):
            return city_obj.get(f"name_{lang}") or name
        return name

    def _match_attraction(self, text, anchor):
        """Link an attraction string (e.g. 'Abbey Falls') to a destination record if one exists."""
        t = text.lower()
        for d in self.destinations:
            if d["slug"] == anchor["slug"]:
                continue
            core = d["name"].lower().split("(")[0].strip()
            first = core.split()[0]
            if (core in t or (len(first) >= 5 and first in t and first not in ("mysore", "bangalore"))) and \
                    haversine_km(anchor["lat"], anchor["lng"], d["lat"], d["lng"]) < 90:
                return d
        return None

    # ------------------------------------------------------------------
    def _candidate_stops(self, anchor, interests, days, lang):
        anchor_items, linked = [], set()
        for a in anchor.get("attractions", []):
            d = self._match_attraction(a, anchor)
            if d and d["slug"] in linked:
                continue
            if d:
                linked.add(d["slug"])
                anchor_items.append({"name": self._local_name(d, lang), "slug": d["slug"], "lat": d["lat"], "lng": d["lng"],
                                     "fee": d.get("entry_fee_indian", 0), "visit_h": 1.5, "optional": d.get("entry_fee_indian", 0) > 0})
            else:
                anchor_items.append({"name": a, "slug": None, "lat": anchor["lat"], "lng": anchor["lng"],
                                     "fee": 0, "visit_h": 1.0, "optional": False})
        radius = 70 if days <= 3 else 140
        scores, _ = self.recommender.score_all(interests=interests, origin=(anchor["lat"], anchor["lng"]))
        nearby = []
        for idx, d in enumerate(self.recommender.destinations):
            if d["slug"] == anchor["slug"] or d["slug"] in linked:
                continue
            km = haversine_km(anchor["lat"], anchor["lng"], d["lat"], d["lng"])
            if km > radius:
                continue
            score = float(scores[idx]) + 0.25 * (1 - km / radius)
            nearby.append((score, {"name": self._local_name(d, lang), "slug": d["slug"], "lat": d["lat"], "lng": d["lng"],
                                   "fee": d.get("entry_fee_indian", 0), "visit_h": 2.0, "km_from_anchor": km,
                                   "optional": True}))
        nearby.sort(key=lambda x: -x[0])
        return anchor_items, [n for _, n in nearby]

    @staticmethod
    def _order_nearest(items, start_pos):
        ordered, pos, pool = [], start_pos, list(items)
        while pool:
            nxt = min(pool, key=lambda it: haversine_km(pos[0], pos[1], it["lat"], it["lng"]))
            ordered.append(nxt)
            pool.remove(nxt)
            pos = (nxt["lat"], nxt["lng"])
        return ordered

    def _layout(self, anchor, start_name, start_pos, start_obj, days, interests, lang, drop_optional=False):
        txt = TEXT.get(lang, TEXT["en"])
        anchor_items, nearby = self._candidate_stops(anchor, interests, days, lang)
        if drop_optional:
            anchor_items = [a for a in anchor_items if not (a["optional"] and a["fee"] > 0)]
            nearby = [n for n in nearby if n["fee"] == 0]
        dest_name = self._local_name(anchor, lang)
        start_label = self._city_label(start_obj, start_name, lang)
        anchor_pos = (anchor["lat"], anchor["lng"])
        leg1 = road_km(*start_pos, *anchor_pos)
        leg1_h = travel_hours(leg1)

        # day capacities
        if days == 1:
            caps = [3 if leg1_h <= 2.5 else (2 if leg1_h <= 4 else 1)]
        else:
            first = 3 if leg1_h <= 3 else (2 if leg1_h <= 6.5 else 1)
            last = 2 if leg1_h <= 4 else 1
            caps = [first] + [4] * (days - 2) + [last]

        remaining_anchor = list(anchor_items)
        remaining_near = list(nearby)
        day_plans, base, base_name, base_slug = [], anchor_pos, dest_name, anchor["slug"]
        intercity_km, local_km, entry_fees, overnight_bases = 0.0, 0.0, anchor.get("entry_fee_indian", 0), []

        for day in range(1, days + 1):
            cap = caps[day - 1]
            is_first, is_last = day == 1, day == days
            chosen = []
            if is_first:
                chosen = remaining_anchor[:cap]
                remaining_anchor = remaining_anchor[cap:]
            elif not is_last:
                # destination highlights first, then a cluster of nearby places
                if len(remaining_anchor) >= 2:
                    chosen = remaining_anchor[:cap]
                    remaining_anchor = remaining_anchor[cap:]
                else:
                    chosen, remaining_anchor = list(remaining_anchor), []
                    if remaining_near:
                        seed = remaining_near.pop(0)
                        cluster = sorted(remaining_near, key=lambda n: haversine_km(seed["lat"], seed["lng"], n["lat"], n["lng"]))
                        cluster = [c for c in cluster if haversine_km(seed["lat"], seed["lng"], c["lat"], c["lng"]) < 45]
                        cluster = cluster[:max(cap - len(chosen) - 1, 0)]
                        for c in cluster:
                            remaining_near.remove(c)
                        chosen += [seed] + cluster
            else:  # last day: something on the way home
                if travel_hours(road_km(base[0], base[1], *start_pos)) > 4:
                    cap = 1
                if remaining_anchor:
                    chosen = remaining_anchor[:cap]
                    remaining_anchor = remaining_anchor[cap:]
                elif remaining_near:
                    best = min(remaining_near, key=lambda n: haversine_km(start_pos[0], start_pos[1], n["lat"], n["lng"]))
                    remaining_near.remove(best)
                    chosen = [best][:cap]

            # Where does the day start?
            day_start = start_pos if is_first else base
            ordered = self._order_nearest(chosen, anchor_pos if is_first else day_start)
            stops, clock = [], 7.0 if (is_first and leg1_h > 3) else 8.5
            day_km, pos = 0.0, day_start

            if is_first:
                stops.append({"name": txt["start"].format(place=start_label), "time": _fmt_time(clock), "kind": "travel"})
                day_km += leg1
                intercity_km += leg1
                clock += leg1_h
                pos = anchor_pos
                if days > 1:
                    stops.append({"name": txt["arrive"].format(place=dest_name), "time": _fmt_time(clock), "kind": "travel"})
                    clock += 0.75
            for item in ordered:
                hop = road_km(pos[0], pos[1], item["lat"], item["lng"])
                hop = max(hop, 4.0)
                day_km += hop
                local_km += hop
                clock += travel_hours(hop)
                stops.append({"name": item["name"], "slug": item["slug"], "time": _fmt_time(clock), "kind": "visit",
                              "fee": item["fee"]})
                entry_fees += item["fee"]
                clock += item["visit_h"]
                pos = (item["lat"], item["lng"])

            # overnight / return
            if is_last:
                back = road_km(pos[0], pos[1], *start_pos)
                if not is_first or days == 1:
                    if days > 1 and not ordered:
                        stops.append({"name": txt["shopping"], "time": _fmt_time(clock), "kind": "activity"})
                        clock += 1
                    stops.append({"name": txt["departure"].format(place=start_label) if days > 1 else txt["return"].format(place=start_label),
                                  "time": _fmt_time(clock), "kind": "travel"})
                day_km += back
                intercity_km += back
                title = (txt["day_trip"].format(start=start_label, dest=dest_name) if days == 1
                         else f"{base_name} → {start_label}")
                overnight = None
            else:
                far = bool(ordered) and ordered[-1]["slug"] is not None and \
                    haversine_km(base[0], base[1], ordered[-1]["lat"], ordered[-1]["lng"]) > 90
                if far:  # move the overnight base closer to the next sights
                    base = (ordered[-1]["lat"], ordered[-1]["lng"])
                    base_name = ordered[-1]["name"]
                    base_slug = ordered[-1]["slug"]
                else:
                    back_to_base = road_km(pos[0], pos[1], *base)
                    day_km += back_to_base
                    local_km += back_to_base
                    base_slug = base_slug if day > 1 else anchor["slug"]
                overnight = base_name
                overnight_bases.append(base_slug)
                stops.append({"name": txt["overnight"].format(place=base_name), "time": "", "kind": "stay"})
                if is_first:
                    title = f"{start_label} → {dest_name}"
                elif far:
                    title = txt["excursion"].format(place=base_name)
                else:
                    title = txt["local"].format(dest=dest_name)
            day_plans.append({
                "day": day, "title": title, "km": int(round(day_km)), "hours": round(travel_hours(day_km), 1),
                "subtitle": f"{int(round(day_km))} km • {fmt_hours(travel_hours(day_km))}",
                "stops": stops, "overnight": overnight,
                "image_slug": (ordered[0]["slug"] if ordered and ordered[0]["slug"] else anchor["slug"]),
            })
        return {
            "day_plans": day_plans, "intercity_km": intercity_km, "local_km": local_km, "entry_fees_pp": entry_fees,
            "overnight_bases": overnight_bases, "leg1_km": leg1, "leg1_hours": leg1_h,
        }

    # ------------------------------------------------------------------
    def _costs(self, layout, anchor, days, travelers, style, transport):
        s = STYLES[style]
        rooms = math.ceil(travelers / 2)
        nights = max(days - 1, 0)
        cost_index = {b: self.dest[b].get("cost_index", 1.0) for b in layout["overnight_bases"] if b in self.dest}
        accommodation = sum(s["room"] * cost_index.get(b, anchor.get("cost_index", 1.0)) * rooms
                            for b in layout["overnight_bases"][:nights])
        food = s["food"] * travelers * days
        entry = layout["entry_fees_pp"] * travelers
        groups = math.ceil(travelers / 3)
        if transport == "car":
            if travelers <= 4:
                rate, vehicles = 14, 1
            elif travelers <= 7:
                rate, vehicles = 18, 1
            else:
                rate, vehicles = 24, math.ceil(travelers / 12)
            transport_cost = (layout["intercity_km"] + layout["local_km"]) * rate * vehicles + DRIVER_ALLOWANCE * days * vehicles
            local = 0
        elif transport == "train":
            transport_cost = layout["intercity_km"] * TRAIN_RATE * travelers
            local = s["local_day"] * days * groups + layout["local_km"] * 3 * groups
        else:
            transport_cost = layout["intercity_km"] * s["bus_rate"] * travelers
            local = s["local_day"] * days * groups + layout["local_km"] * 3 * groups
        subtotal = transport_cost + local + accommodation + food + entry
        misc = subtotal * 0.05
        total = subtotal + misc
        return {
            "transport": _r10(transport_cost), "local_transport": _r10(local), "accommodation": _r10(accommodation),
            "food": _r10(food), "entry_fees": _r10(entry), "misc": _r10(misc), "total": _r10(total),
            "per_person": _r10(total / travelers), "rooms": rooms, "nights": nights,
        }

    @staticmethod
    def _auto_transport(style, travelers, km):
        if style == "budget":
            return "bus"
        if style == "luxury" or travelers >= 3:
            return "car"
        return "bus" if km > 150 else "car"

    # ------------------------------------------------------------------
    def plan(self, destination, start="Bangalore", days=2, travelers=2, budget=None, interests=None,
             style="standard", transport="auto", lang="en"):
        anchor = self.dest.get(destination)
        if not anchor:
            raise ValueError(f"Unknown destination: {destination}")
        days = max(1, min(int(days or anchor.get("ideal_days", 2)), 10))
        travelers = max(1, min(int(travelers or 2), 20))
        style = style if style in STYLES else "standard"
        interests = interests or []
        start_name, start_pos, start_obj = self.resolve_start(start)
        warnings = []

        layout = self._layout(anchor, start_name, start_pos, start_obj, days, interests, lang)
        requested_transport = transport if transport in TRANSPORTS else self._auto_transport(style, travelers, layout["leg1_km"])
        costs = self._costs(layout, anchor, days, travelers, style, requested_transport)
        chosen_style, chosen_transport, status, adjustments = style, requested_transport, "none", []

        if budget:
            budget = int(budget)
            if costs["total"] <= budget:
                status = "within"
            else:
                status = "over"
                styles = STYLE_ORDER[STYLE_ORDER.index(style):]
                candidates = []
                for st in styles:
                    for tr in ([requested_transport] + [t for t in ("bus", "train", "car") if t != requested_transport]):
                        if tr == "train" and layout["leg1_km"] < 150:
                            continue
                        candidates.append((st, tr))
                for st, tr in candidates:
                    c = self._costs(layout, anchor, days, travelers, st, tr)
                    if c["total"] <= budget:
                        costs, chosen_style, chosen_transport, status = c, st, tr, "optimized"
                        break
                if status == "over":  # drop optional paid stops
                    lean = self._layout(anchor, start_name, start_pos, start_obj, days, interests, lang, drop_optional=True)
                    c = min(((self._costs(lean, anchor, days, travelers, "budget", tr), tr) for tr in ("bus", "train")
                             if not (tr == "train" and lean["leg1_km"] < 150)), key=lambda x: x[0]["total"])
                    if c[0]["total"] <= budget:
                        layout, costs, chosen_style, chosen_transport, status = lean, c[0], "budget", c[1], "optimized"
                        adjustments.append("dropped_paid")
                    else:
                        cheapest = self._costs(lean, anchor, days, travelers, "budget", "bus")
                        costs, chosen_style, chosen_transport, layout = cheapest, "budget", "bus", lean
                if chosen_style != style:
                    adjustments.append(f"style:{style}->{chosen_style}")
                if chosen_transport != requested_transport:
                    adjustments.append(f"transport:{requested_transport}->{chosen_transport}")

        if days == 1 and layout["leg1_hours"] > 4:
            warnings.append("long_day_trip")
        if layout["leg1_hours"] > days * 6:
            warnings.append("too_far")

        suggested_days = None
        if status == "over" and days > 1:
            for d in range(days - 1, 0, -1):
                lay = self._layout(anchor, start_name, start_pos, start_obj, d, interests, lang, drop_optional=True)
                if self._costs(lay, anchor, d, travelers, "budget", "bus")["total"] <= budget:
                    suggested_days = d
                    break

        s = STYLES[chosen_style]
        room_rate = _r10(s["room"] * anchor.get("cost_index", 1.0))
        return {
            "destination": {"slug": anchor["slug"], "name": anchor["name"], "display_name": self._local_name(anchor, lang),
                            "district": anchor["district"], "category": anchor["category"], "wiki": anchor.get("wiki", ""),
                            "lat": anchor["lat"], "lng": anchor["lng"], "image_url": anchor.get("image_url", "")},
            "title": f"{anchor['name']} {days}-Day Trip",
            "start_city": start_name, "start_label": self._city_label(start_obj, start_name, lang),
            "days": days, "travelers": travelers, "interests": interests,
            "style": chosen_style, "requested_style": style, "transport": chosen_transport,
            "budget": budget, "budget_status": status, "adjustments": adjustments, "suggested_days": suggested_days,
            "costs": costs, "remaining": (budget - costs["total"]) if budget else None,
            "total_km": int(round(sum(d["km"] for d in layout["day_plans"]))),
            "one_way_km": int(round(layout["leg1_km"])), "one_way_hours": round(layout["leg1_hours"], 1),
            "day_plans": layout["day_plans"],
            "stay": {"type": s["label"], "style": chosen_style, "rate": room_rate, "rooms": costs["rooms"], "nights": costs["nights"]},
            "best_from": anchor["best_from"], "best_to": anchor["best_to"],
            "tips": anchor.get("tips", ""), "warnings": warnings, "language": lang,
        }

    # ------------------------------------------------------------------
    def suggest_by_budget(self, start="Bangalore", days=2, travelers=2, budget=None, interests=None,
                          style="standard", month=None, limit=5, lang="en"):
        """Recommend destinations whose full trip fits the budget (abstract example:
        'Suggest places in Karnataka for 2 days within Rs 5000')."""
        days = max(1, min(int(days or 2), 10))
        travelers = max(1, int(travelers or 2))
        start_name, start_pos, _ = self.resolve_start(start)
        max_hours = {1: 3.5, 2: 6.5, 3: 8.5}.get(days, 11)
        scores, _ = self.recommender.score_all(interests=interests, origin=start_pos, month=month)
        bonus = [0.05 if d.get("ideal_days", 1) >= min(days, 2) else 0 for d in self.recommender.destinations]
        ranked = sorted(range(len(self.recommender.destinations)), key=lambda i: -(scores[i] + bonus[i]))
        results, over = [], []
        for idx in ranked:
            d = self.recommender.destinations[idx]
            hours = travel_hours(road_km(*start_pos, d["lat"], d["lng"]))
            if hours > max_hours or hours < 0.3:
                continue
            if any(haversine_km(d["lat"], d["lng"], self.dest[r["slug"]]["lat"], self.dest[r["slug"]]["lng"]) < 20 for r in results):
                continue  # keep the suggestions diverse
            p = self.plan(d["slug"], start_name, days, travelers, budget, interests, style, "auto", lang)
            item = {"slug": d["slug"], "score": round(float(scores[idx]), 3), "total": p["costs"]["total"],
                    "per_person": p["costs"]["per_person"], "km": p["one_way_km"], "hours": p["one_way_hours"],
                    "style": p["style"], "transport": p["transport"]}
            if not budget or p["costs"]["total"] <= budget:
                results.append(item)
            else:
                over.append(item)
            if len(results) >= limit:
                break
        if not results:  # nothing fits: show the cheapest options
            over.sort(key=lambda x: x["total"])
            return [], over[:3]
        return results, []
