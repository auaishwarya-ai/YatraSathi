"""JSON API used by the frontend (chat, itinerary, recommendations, favourites, nearby, TTS)."""
import io
import json
from datetime import datetime

from flask import Blueprint, abort, jsonify, request, send_file, session
from flask_login import current_user

from .. import current_lang
from ..ai.engine import get_engine
from ..models import ChatMessage, ChatSession, Destination, SavedPlace, Trip, db
from ..utils.images import place_image_url, with_images
from ..utils.pdf import brochure_pdf

bp = Blueprint("api", __name__, url_prefix="/api")


def _user_profile():
    if not current_user.is_authenticated:
        return {}
    saved = [s.destination.slug for s in current_user.saved_places if s.destination]
    return {"home_city": current_user.home_city, "interests": current_user.interests_list, "saved": saved}


def _can_access_session(s):
    if s.user_id is None:
        return s.id in session.get("guest_chats", [])
    return current_user.is_authenticated and current_user.id == s.user_id


# ---------------------------------------------------------------------------
# Destinations & recommendations
# ---------------------------------------------------------------------------
@bp.route("/destinations")
def destinations():
    lang = request.args.get("lang") or current_lang()
    query = Destination.query.filter_by(active=True)
    if request.args.get("category"):
        query = query.filter_by(category=request.args["category"])
    items = [d.to_dict(lang) for d in query.order_by(Destination.views.desc()).all()]
    return jsonify({"count": len(items), "items": items})


@bp.route("/destinations/<slug>")
def destination(slug):
    lang = request.args.get("lang") or current_lang()
    d = Destination.query.filter_by(slug=slug, active=True).first_or_404()
    data = d.to_dict(lang, full=True)
    from ..ai.responses import category_name, month_range
    data["best_time"] = month_range(lang, d.best_from, d.best_to)
    data["category_label"] = category_name(lang, d.category)
    data["image_url"] = place_image_url(d.slug, d.image_url)
    data["saved"] = bool(current_user.is_authenticated and SavedPlace.query.filter_by(user_id=current_user.id, destination_id=d.id).first())
    return jsonify(data)


@bp.route("/recommendations")
def recommendations():
    engine = get_engine()
    lang = current_lang()
    interests = [i for i in request.args.get("interests", "").split(",") if i]
    start = request.args.get("start") or (current_user.home_city if current_user.is_authenticated else "Bangalore")
    budget = request.args.get("budget", type=int)
    days = request.args.get("days", type=int) or 2
    travelers = request.args.get("travelers", type=int) or 2
    if budget:
        fits, cheapest = engine.planner.suggest_by_budget(start, days, travelers, budget, interests, "standard", None, 6, lang)
        rows = [{**engine.card(o["slug"], lang), "estimated_total": o["total"], "km": o["km"]} for o in (fits or cheapest)]
        return jsonify({"fits_budget": bool(fits), "items": rows})
    _, pos, _ = engine.planner.resolve_start(start)
    profile = _user_profile()
    recs = engine.recommender.recommend(interests=interests or profile.get("interests"), origin=pos, limit=6,
                                        personal_slugs=profile.get("saved"))
    return jsonify({"items": [{**engine.card(r["slug"], lang), "score": r["score"], "km": r["distance_km"]} for r in recs]})


@bp.route("/nearby")
def nearby():
    engine = get_engine()
    lat, lng = request.args.get("lat", type=float), request.args.get("lng", type=float)
    if lat is None or lng is None:
        return jsonify({"error": "lat and lng are required"}), 400
    cats = [c for c in request.args.get("category", "").split(",") if c]
    rows = engine.recommender.nearby(lat, lng, limit=request.args.get("limit", 12, type=int),
                                     radius_km=request.args.get("radius", type=float), categories=cats or None)
    lang = current_lang()
    return jsonify({"items": [{**engine.card(r["slug"], lang), "distance_km": round(r["distance_km"] * 1.3, 1),
                               "lat": engine.by_slug[r["slug"]]["lat"], "lng": engine.by_slug[r["slug"]]["lng"]} for r in rows]})


# ---------------------------------------------------------------------------
# Favourites
# ---------------------------------------------------------------------------
@bp.route("/favorites/<slug>", methods=["POST"])
def toggle_favorite(slug):
    if not current_user.is_authenticated:
        return jsonify({"error": "login_required"}), 401
    d = Destination.query.filter_by(slug=slug).first_or_404()
    existing = SavedPlace.query.filter_by(user_id=current_user.id, destination_id=d.id).first()
    if existing:
        db.session.delete(existing)
        saved = False
    else:
        db.session.add(SavedPlace(user_id=current_user.id, destination_id=d.id))
        saved = True
    db.session.commit()
    return jsonify({"saved": saved, "count": current_user.saved_places.count()})


# ---------------------------------------------------------------------------
# Conversational AI
# ---------------------------------------------------------------------------
@bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "empty message"}), 400
    message = message[:1000]
    lang = data.get("lang") or current_lang()

    chat_session = None
    if data.get("session_id"):
        chat_session = db.session.get(ChatSession, int(data["session_id"]))
        if chat_session and not _can_access_session(chat_session):
            chat_session = None
    if chat_session is None:
        chat_session = ChatSession(user_id=current_user.id if current_user.is_authenticated else None,
                                   title=message[:60], language=lang)
        db.session.add(chat_session)
        db.session.flush()
        if not current_user.is_authenticated:
            session["guest_chats"] = (session.get("guest_chats", []) + [chat_session.id])[-20:]

    history = [{"role": m.role, "content": m.content} for m in chat_session.messages.order_by(ChatMessage.id.desc()).limit(6)][::-1]
    engine = get_engine()
    result = engine.reply(message, lang, chat_session.context, _user_profile(), history)
    with_images(result["places"])

    trip_id = None
    if result.get("itinerary"):
        trip_id = _store_trip(result["itinerary"], source="chat", lang=result["language"]).id

    chat_session.context = result["context"]
    chat_session.language = result["language"]
    chat_session.updated_at = datetime.utcnow()
    meta = {"places": result["places"], "trip_id": trip_id, "sources": result["sources"]}
    db.session.add(ChatMessage(session_id=chat_session.id, role="user", content=message, language=result["language"]))
    db.session.add(ChatMessage(session_id=chat_session.id, role="bot", content=result["reply"], intent=result["intent"],
                               language=result["language"], meta_json=json.dumps(meta, ensure_ascii=False)))
    db.session.commit()

    result.pop("context", None)
    result.update({"session_id": chat_session.id, "trip_id": trip_id})
    return jsonify(result)


@bp.route("/chat/<int:session_id>")
def chat_history(session_id):
    s = db.session.get(ChatSession, session_id)
    if not s or not _can_access_session(s):
        abort(404)
    return jsonify({"session_id": s.id, "title": s.title, "language": s.language,
                    "messages": [{"role": m.role, "content": m.content, "intent": m.intent, "meta": m.meta,
                                  "time": m.created_at.strftime("%H:%M")} for m in s.messages]})


# ---------------------------------------------------------------------------
# Trip planner
# ---------------------------------------------------------------------------
def _store_trip(plan, source="planner", lang="en"):
    dest = Destination.query.filter_by(slug=plan["destination"]["slug"]).first()
    trip = Trip(user_id=current_user.id if current_user.is_authenticated else None,
                title=f"{plan['destination']['name']} {'Getaway' if plan['days'] > 1 else 'Day Trip'}",
                start_city=plan["start_city"], destination_id=dest.id if dest else None, days=plan["days"],
                travelers=plan["travelers"], budget=plan.get("budget"), style=plan["style"],
                interests=",".join(plan.get("interests") or []), plan_json=json.dumps(plan, ensure_ascii=False),
                total_cost=plan["costs"]["total"], status="generated", source=source, language=lang)
    db.session.add(trip)
    db.session.flush()
    return trip


@bp.route("/itinerary", methods=["POST"])
def itinerary():
    data = request.get_json(silent=True) or request.form.to_dict()
    engine = get_engine()
    lang = data.get("lang") or current_lang()
    interests = data.get("interests") or []
    if isinstance(interests, str):
        interests = [i for i in interests.split(",") if i]
    try:
        days = int(data.get("days") or 2)
        travelers = int(data.get("travelers") or 2)
        budget = int(data["budget"]) if data.get("budget") else None
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid number in days / travellers / budget"}), 400
    start = data.get("start") or "Bangalore"
    destination = data.get("destination") or ""
    alternatives = []
    if not destination or destination == "auto":
        fits, cheapest = engine.planner.suggest_by_budget(start, days, travelers, budget, interests, data.get("style", "standard"), None, 4, lang)
        options = fits or cheapest
        if not options:
            return jsonify({"error": "No destination found for these settings."}), 404
        destination = options[0]["slug"]
        alternatives = [{**engine.card(o["slug"], lang), "estimated_total": o["total"]} for o in options[1:]]
    if destination not in engine.by_slug:
        return jsonify({"error": "Unknown destination"}), 404
    plan = engine.planner.plan(destination, start, days, travelers, budget, interests, data.get("style", "standard"),
                               data.get("transport", "auto"), lang)
    trip = _store_trip(plan, "planner", lang)
    db.session.commit()
    return jsonify({"trip_id": trip.id, "plan": plan, "summary": engine.plan_text(plan, lang), "alternatives": with_images(alternatives)})


@bp.route("/trips/<int:trip_id>/save", methods=["POST"])
def save_trip(trip_id):
    if not current_user.is_authenticated:
        return jsonify({"error": "login_required"}), 401
    trip = db.session.get(Trip, trip_id) or abort(404)
    if trip.user_id not in (None, current_user.id):
        abort(403)
    data = request.get_json(silent=True) or {}
    trip.user_id = current_user.id
    if trip.status == "generated":
        trip.status = "saved"
    if data.get("start_date"):
        try:
            trip.start_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
            trip.status = "upcoming"
        except ValueError:
            pass
    db.session.commit()
    return jsonify({"saved": True, "trip_id": trip.id, "status": trip.status})


# ---------------------------------------------------------------------------
# Voice: server-side text-to-speech fallback (needs internet for gTTS)
# ---------------------------------------------------------------------------
@bp.route("/tts", methods=["POST"])
def tts():
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()[:1500]
    lang = data.get("lang", "en")
    if not text:
        return jsonify({"error": "empty text"}), 400
    try:
        from gtts import gTTS
        buf = io.BytesIO()
        gTTS(text=text, lang={"en": "en", "kn": "kn", "hi": "hi"}.get(lang, "en"), tld="co.in" if lang == "en" else "com").write_to_fp(buf)
        buf.seek(0)
        return send_file(buf, mimetype="audio/mpeg")
    except Exception as exc:  # gTTS missing or offline
        return jsonify({"error": f"Text-to-speech unavailable: {exc.__class__.__name__}"}), 503


@bp.route("/brochure.pdf")
def brochure():
    try:
        buf = brochure_pdf(Destination.query.filter_by(active=True).order_by(Destination.category, Destination.name).all())
    except ImportError:
        return jsonify({"error": "PDF library unavailable on this computer"}), 503
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="YatraSathi-Karnataka-Brochure.pdf")


@bp.route("/health")
def health():
    engine = get_engine()
    return jsonify({"status": "ok", "destinations": len(engine.destinations), "knowledge_passages": engine.rag.size,
                    "intent_training_examples": engine.intents.training_size, "llm_enabled": engine.llm.enabled})
