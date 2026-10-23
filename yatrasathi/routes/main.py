"""Public pages: Home, Explore, Place details, AI Assistant, AI Planner, Travel Guide, Nearby, Help."""
import json
import math

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user

from .. import current_lang
from ..ai.engine import get_engine
from ..ai.nlp import INTERESTS
from ..ai.sentiment import analyze
from ..i18n import LANGUAGES
from ..models import ChatSession, Destination, Feedback, SavedPlace, db
from ..seed import CATEGORIES
from ..utils.images import place_image_url

bp = Blueprint("main", __name__)

PER_PAGE = 9


def load_json(name):
    with open(current_app.config["DATA_DIR"] / name, encoding="utf-8") as f:
        return json.load(f)


def saved_ids():
    if current_user.is_authenticated:
        return {s.destination_id for s in SavedPlace.query.filter_by(user_id=current_user.id).all()}
    return set()


def category_counts():
    rows = db.session.query(Destination.category, db.func.count(Destination.id)).filter_by(active=True).group_by(Destination.category).all()
    counts = dict(rows)
    return [(c, counts.get(c, 0)) for c in CATEGORIES]


_featured_cache = {}


def featured_itineraries():
    """Featured trips with prices computed by the planner (cached per language)."""
    lang = current_lang()
    if lang not in _featured_cache:
        engine = get_engine()
        items = []
        for f in load_json("featured_itineraries.json"):
            p = f["params"]
            if p["destination"] not in engine.by_slug:
                continue
            plan = engine.planner.plan(p["destination"], p["start"], p["days"], p["travelers"], None, p["interests"], p["style"], "auto", lang)
            items.append({**f, "price_from": plan["costs"]["per_person"], "nights": p["days"] - 1,
                          "image": engine.by_slug.get(f["image_slug"]) or engine.by_slug[p["destination"]]})
        _featured_cache[lang] = items
    return _featured_cache[lang]


@bp.route("/")
def index():
    popular = Destination.query.filter_by(active=True).order_by(Destination.views.desc()).limit(8).all()
    hero = Destination.query.filter_by(slug="hampi").first()
    return render_template("index.html", popular=popular, hero=hero, categories=category_counts(), featured=featured_itineraries(),
                           guide=load_json("knowledge_base.json"), saved=saved_ids())


@bp.route("/lang/<code>")
def set_language(code):
    if code in LANGUAGES:
        session["lang"] = code
        if current_user.is_authenticated:
            current_user.language = code
            db.session.commit()
    return redirect(request.referrer or url_for("main.index"))


@bp.route("/explore")
def explore():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    district = request.args.get("district", "")
    sort = request.args.get("sort", "popularity")
    min_rating = request.args.get("rating", type=float)
    page = max(request.args.get("page", 1, type=int), 1)

    query = Destination.query.filter_by(active=True)
    if category in CATEGORIES:
        query = query.filter_by(category=category)
    if district:
        query = query.filter_by(district=district)
    if min_rating:
        query = query.filter(Destination.rating >= min_rating)
    results = query.all()

    if q:  # NLP-powered search: entity match + RAG semantic retrieval
        engine = get_engine()
        found = engine.nlu.find_destinations(q.lower())
        ranked = {s: 10 - i for i, s in enumerate(found)}
        for i, doc in enumerate(engine.rag.search(q, k=25)):
            if doc.get("slug") and doc["score"] > 0.08:
                ranked[doc["slug"]] = ranked.get(doc["slug"], 0) + doc["score"]
        for d in results:
            text = f"{d.name} {d.district} {d.category} {d.tags}".lower()
            if q.lower() in text:
                ranked[d.slug] = ranked.get(d.slug, 0) + 1
        results = sorted([d for d in results if d.slug in ranked], key=lambda d: -ranked[d.slug])
    elif sort == "rating":
        results.sort(key=lambda d: (-d.rating, -d.reviews))
    elif sort == "name":
        results.sort(key=lambda d: d.name)
    else:
        results.sort(key=lambda d: -d.views)

    total = len(results)
    pages = max(1, math.ceil(total / PER_PAGE))
    page = min(page, pages)
    items = results[(page - 1) * PER_PAGE: page * PER_PAGE]
    selected_slug = request.args.get("place") or (items[0].slug if items else None)
    selected = Destination.query.filter_by(slug=selected_slug).first() if selected_slug else None
    districts = [r[0] for r in db.session.query(Destination.district).filter_by(active=True).distinct().order_by(Destination.district)]
    map_points = [{"slug": d.slug, "name": d.localized_name(current_lang()), "lat": d.lat, "lng": d.lng, "category": d.category,
                   "rating": d.rating} for d in results]
    args = {k: v for k, v in request.args.items() if k not in ("page", "place")}
    return render_template("explore.html", items=items, total=total, page=page, pages=pages, q=q, category=category,
                           district=district, sort=sort, min_rating=min_rating, districts=districts, categories=category_counts(),
                           selected=selected, saved=saved_ids(), map_points=map_points, args=args)


@bp.route("/place/<slug>")
def place(slug):
    d = Destination.query.filter_by(slug=slug, active=True).first_or_404()
    d.views = (d.views or 0) + 1
    db.session.commit()
    engine = get_engine()
    similar = Destination.query.filter(Destination.slug.in_(engine.recommender.similar(slug, 4))).all() if slug in engine.by_slug else []
    near = engine.recommender.nearby(d.lat, d.lng, limit=6, exclude={slug}) if slug in engine.by_slug else []
    near_map = {n["slug"]: n["distance_km"] for n in near}
    nearby_places = sorted(Destination.query.filter(Destination.slug.in_(near_map)).all(), key=lambda x: near_map[x.slug])
    reviews = Feedback.query.filter_by(destination_id=d.id, kind="review").order_by(Feedback.created_at.desc()).limit(10).all()
    estimate = None
    if slug in engine.by_slug:
        start = current_user.home_city if current_user.is_authenticated else "Bangalore"
        estimate = engine.planner.plan(slug, start, d.ideal_days, 2, None, [], "standard", "auto", current_lang())
    return render_template("place.html", d=d, similar=similar, nearby_places=nearby_places, near_km=near_map,
                           reviews=reviews, saved=saved_ids(), estimate=estimate)


@bp.route("/place/<slug>/review", methods=["POST"])
def add_review(slug):
    d = Destination.query.filter_by(slug=slug).first_or_404()
    message = request.form.get("message", "").strip()
    rating = max(1, min(request.form.get("rating", 5, type=int), 5))
    if not current_user.is_authenticated:
        flash("Please log in to write a review.", "info")
        return redirect(url_for("auth.login", next=url_for("main.place", slug=slug)))
    if message:
        db.session.add(Feedback(user_id=current_user.id, destination_id=d.id, name=current_user.name, email=current_user.email,
                                kind="review", rating=rating, message=message[:1000], sentiment=analyze(message, rating)))
        # update the running average rating
        d.rating = round((d.rating * d.reviews + rating) / (d.reviews + 1), 1)
        d.reviews += 1
        db.session.commit()
        flash("Thank you! Your review has been posted.", "success")
    return redirect(url_for("main.place", slug=slug) + "#reviews")


@bp.route("/assistant")
def assistant():
    sessions = []
    if current_user.is_authenticated:
        sessions = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.updated_at.desc()).limit(12).all()
    prefill = request.args.get("q", "")
    place_slug = request.args.get("place")
    if place_slug and not prefill:
        d = Destination.query.filter_by(slug=place_slug).first()
        if d:
            prefill = {"en": f"Tell me about {d.name}", "kn": f"{d.name_kn or d.name} ಬಗ್ಗೆ ತಿಳಿಸಿ",
                       "hi": f"{d.name_hi or d.name} के बारे में बताओ"}[current_lang()]
    return render_template("assistant.html", sessions=sessions, prefill=prefill, resume=request.args.get("session", type=int))


@bp.route("/planner")
def planner():
    engine = get_engine()
    cities = load_json("cities.json")
    dests = sorted(Destination.query.filter_by(active=True).all(), key=lambda d: d.name)
    preset = None
    key = request.args.get("preset")
    if key:
        preset = next((f["params"] for f in load_json("featured_itineraries.json") if f["key"] == key), None)
    elif request.args.get("destination"):
        preset = {"destination": request.args.get("destination"), "days": request.args.get("days", type=int) or 2,
                  "start": request.args.get("start", "Bangalore"), "travelers": request.args.get("travelers", type=int) or 2,
                  "interests": request.args.getlist("interests"), "style": request.args.get("style", "standard")}
    default_start = current_user.home_city if current_user.is_authenticated and current_user.home_city else "Bangalore"
    places_map = {d.slug: {"slug": d.slug, "name": d.name, "display_name": d.localized_name(current_lang()), "wiki": d.wiki,
                           "category": d.category, "image_url": place_image_url(d.slug, d.image_url)} for d in dests}
    return render_template("planner.html", cities=cities, dests=dests, interests=INTERESTS, preset=preset, places_map=places_map,
                           default_start=default_start, engine_ready=bool(engine))


@bp.route("/guide")
@bp.route("/guide/<section>")
def guide(section=None):
    kb = load_json("knowledge_base.json")
    current = None
    if section:
        current = next((s for s in kb["sections"] if s["slug"] == section), None)
        if not current and section not in ("faqs", "emergency"):
            abort(404)
    highlights = Destination.query.filter(Destination.slug.in_(["hampi", "mysore-palace"])).all()
    return render_template("guide.html", kb=kb, current=current, section=section, highlights=highlights,
                           district_count=31, place_count=Destination.query.filter_by(active=True).count())


@bp.route("/nearby")
def nearby():
    cities = load_json("cities.json")
    places = Destination.query.filter_by(active=True).order_by(Destination.name).all()
    points = [{"slug": d.slug, "name": d.name, "display_name": d.localized_name(current_lang()), "lat": d.lat, "lng": d.lng, "category": d.category,
               "rating": d.rating, "district": d.district, "wiki": d.wiki, "image_url": place_image_url(d.slug, d.image_url)} for d in places]
    return render_template("nearby.html", cities=cities, places=places, points=points, categories=category_counts(),
                           origin=request.args.get("from", ""))


@bp.route("/help", methods=["GET", "POST"])
def help_page():
    kb = load_json("knowledge_base.json")
    if request.method == "POST":
        message = request.form.get("message", "").strip()
        if not message:
            flash("Please write a message.", "error")
        else:
            rating = request.form.get("rating", type=int) or 4
            name = request.form.get("name") or (current_user.name if current_user.is_authenticated else "Guest")
            db.session.add(Feedback(user_id=current_user.id if current_user.is_authenticated else None, name=name[:120],
                                    email=request.form.get("email", "")[:160], kind=request.form.get("kind", "feedback"),
                                    rating=rating, message=message[:2000], sentiment=analyze(message, rating)))
            db.session.commit()
            flash("Thank you! Your message has been sent to the YatraSathi team.", "success")
            return redirect(url_for("main.help_page"))
    return render_template("help.html", kb=kb)
