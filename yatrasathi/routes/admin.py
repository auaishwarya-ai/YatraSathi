"""Admin panel: dashboard + destination, user, itinerary, feedback, knowledge base and chat management."""
import csv
import io
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import (Blueprint, Response, abort, current_app, flash, redirect, render_template, request, url_for)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from ..ai.engine import get_engine, refresh_engine
from ..models import ChatMessage, ChatSession, Destination, Feedback, KnowledgeDoc, SavedPlace, Trip, User, db
from ..seed import CATEGORIES

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def _growth(model, field, days=30):
    now = datetime.utcnow()
    cur = model.query.filter(field >= now - timedelta(days=days)).count()
    prev = model.query.filter(field >= now - timedelta(days=2 * days), field < now - timedelta(days=days)).count()
    if prev == 0:
        return 100.0 if cur else 0.0
    return round((cur - prev) * 100.0 / prev, 1)


@bp.route("/")
@admin_required
def dashboard():
    now = datetime.utcnow()
    start = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
    labels = [(start + timedelta(days=i)).strftime("%d %b") for i in range(30)]

    def daily(model, field):
        counts = Counter(r[0].strftime("%d %b") for r in db.session.query(field).filter(field >= start).all())
        return [counts.get(lbl, 0) for lbl in labels]

    stats = {
        "destinations": Destination.query.filter_by(active=True).count(),
        "dest_new": Destination.query.filter(Destination.created_at >= now - timedelta(days=30)).count(),
        "users": User.query.count(), "users_growth": _growth(User, User.created_at),
        "chats": ChatSession.query.count(), "chats_growth": _growth(ChatSession, ChatSession.created_at),
        "itineraries": Trip.query.count(), "itineraries_growth": _growth(Trip, Trip.created_at),
    }
    chart = {"labels": labels, "users": daily(User, User.created_at), "chats": daily(ChatSession, ChatSession.created_at),
             "itineraries": daily(Trip, Trip.created_at)}
    lang_counts = dict(db.session.query(ChatSession.language, db.func.count(ChatSession.id)).group_by(ChatSession.language).all())
    total_chats = sum(lang_counts.values()) or 1
    languages = [{"code": c, "label": lbl, "count": lang_counts.get(c, 0), "pct": round(lang_counts.get(c, 0) * 100 / total_chats)}
                 for c, lbl in (("en", "English"), ("kn", "ಕನ್ನಡ (Kannada)"), ("hi", "हिंदी (Hindi)"))]
    # weekly registrations (last 5 weeks)
    weeks = []
    for i in range(4, -1, -1):
        w_end = now - timedelta(days=7 * i)
        w_start = w_end - timedelta(days=7)
        weeks.append({"label": w_start.strftime("%d %b"),
                      "count": User.query.filter(User.created_at >= w_start, User.created_at < w_end).count()})
    top = Destination.query.order_by(Destination.views.desc()).limit(5).all()
    recent_trips = Trip.query.filter(Trip.user_id.isnot(None)).order_by(Trip.created_at.desc()).limit(5).all()
    feedback = Feedback.query.filter_by(kind="feedback").order_by(Feedback.created_at.desc()).limit(3).all()
    date_range = f"{start.strftime('%d %b %Y')} - {now.strftime('%d %b %Y')}"
    return render_template("admin/dashboard.html", stats=stats, date_range=date_range, chart=json.dumps(chart), languages=languages,
                           lang_chart=json.dumps([l["count"] for l in languages]), weeks=weeks,
                           weeks_json=json.dumps(weeks), top=top, recent_trips=recent_trips, feedback=feedback, active="dashboard")


# ---------------------------------------------------------------------------
# Destinations
# ---------------------------------------------------------------------------
@bp.route("/destinations")
@admin_required
def destinations():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    query = Destination.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Destination.name.ilike(like), Destination.district.ilike(like), Destination.tags.ilike(like)))
    if category:
        query = query.filter_by(category=category)
    items = query.order_by(Destination.name).all()
    counts = dict(db.session.query(Destination.category, db.func.count(Destination.id)).group_by(Destination.category).all())
    return render_template("admin/destinations.html", items=items, q=q, category=category, categories=CATEGORIES,
                           counts=counts, active="destinations")


def _slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:70] or "place"


def _lines(value):
    return [x.strip() for x in (value or "").replace("\r", "").split("\n") if x.strip()]


@bp.route("/destinations/new", methods=["GET", "POST"])
@bp.route("/destinations/<int:dest_id>/edit", methods=["GET", "POST"])
@admin_required
def destination_form(dest_id=None):
    d = db.session.get(Destination, dest_id) if dest_id else None
    if dest_id and not d:
        abort(404)
    if request.method == "POST":
        f = request.form
        name = f.get("name", "").strip()
        try:
            lat, lng = float(f.get("lat")), float(f.get("lng"))
        except (TypeError, ValueError):
            flash("Latitude and longitude must be numbers.", "error")
            return render_template("admin/destination_form.html", d=d, vals=f.to_dict(), categories=CATEGORIES, active="destinations")
        if not name:
            flash("Name is required.", "error")
            return render_template("admin/destination_form.html", d=d, vals=f.to_dict(), categories=CATEGORIES, active="destinations")
        if d is None:
            slug = _slugify(f.get("slug") or name)
            if Destination.query.filter_by(slug=slug).first():
                slug = f"{slug}-{int(datetime.utcnow().timestamp()) % 10000}"
            d = Destination(slug=slug, lat=lat, lng=lng)
            db.session.add(d)
        d.name, d.lat, d.lng = name, lat, lng
        for field in ("name_kn", "name_hi", "district", "description", "history", "timings", "how_to_reach", "tips",
                      "summary_kn", "summary_hi", "wiki", "image_url"):
            setattr(d, field, f.get(field, "").strip())
        d.category = f.get("category") if f.get("category") in CATEGORIES else "Heritage"
        d.tags = ",".join(t.strip() for t in f.get("tags", "").split(",") if t.strip())
        d.attractions = json.dumps(_lines(f.get("attractions")), ensure_ascii=False)
        d.food = json.dumps(_lines(f.get("food")), ensure_ascii=False)
        for field, default in (("best_from", 10), ("best_to", 3), ("entry_fee_indian", 0), ("entry_fee_foreign", 0), ("ideal_days", 1)):
            setattr(d, field, f.get(field, type=int) if f.get(field, type=int) is not None else default)
        d.rating = min(max(f.get("rating", type=float) or 4.0, 0), 5)
        d.cost_index = f.get("cost_index", type=float) or 1.0
        d.active = bool(f.get("active"))
        upload = request.files.get("image")
        if upload and upload.filename:
            ext = Path(secure_filename(upload.filename)).suffix.lower()
            if ext in (".jpg", ".jpeg", ".png", ".webp"):
                folder = Path(current_app.config["UPLOAD_FOLDER"])
                folder.mkdir(parents=True, exist_ok=True)
                filename = f"{d.slug}{ext}"
                upload.save(folder / filename)
                d.image_url = url_for("static", filename=f"uploads/{filename}")
            else:
                flash("Only JPG, PNG or WEBP images are allowed.", "error")
        db.session.commit()
        refresh_engine()
        flash(f"Destination '{d.name}' saved. AI index updated.", "success")
        return redirect(url_for("admin.destinations"))
    if d:
        vals = {c.name: getattr(d, c.name) for c in Destination.__table__.columns}
        vals.update(attractions="\n".join(d.attractions_list), food="\n".join(d.food_list))
    else:
        vals = {"lat": 12.97, "lng": 77.59, "rating": 4.2, "entry_fee_indian": 0, "entry_fee_foreign": 0, "best_from": 10,
                "best_to": 3, "ideal_days": 1, "cost_index": 1.0, "timings": "9:00 AM - 5:30 PM", "active": True, "category": "Heritage"}
    return render_template("admin/destination_form.html", d=d, vals=vals, categories=CATEGORIES, active="destinations")


@bp.route("/destinations/<int:dest_id>/toggle", methods=["POST"])
@admin_required
def destination_toggle(dest_id):
    d = db.session.get(Destination, dest_id) or abort(404)
    d.active = not d.active
    db.session.commit()
    refresh_engine()
    flash(f"'{d.name}' is now {'visible' if d.active else 'hidden'}.", "info")
    return redirect(request.referrer or url_for("admin.destinations"))


@bp.route("/destinations/<int:dest_id>/delete", methods=["POST"])
@admin_required
def destination_delete(dest_id):
    d = db.session.get(Destination, dest_id) or abort(404)
    SavedPlace.query.filter_by(destination_id=d.id).delete()
    Feedback.query.filter_by(destination_id=d.id).update({"destination_id": None})
    Trip.query.filter_by(destination_id=d.id).update({"destination_id": None})
    db.session.delete(d)
    db.session.commit()
    refresh_engine()
    flash("Destination deleted.", "info")
    return redirect(url_for("admin.destinations"))


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
@bp.route("/users")
@admin_required
def users():
    q = request.args.get("q", "").strip()
    query = User.query
    if q:
        query = query.filter(db.or_(User.name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")))
    items = query.order_by(User.created_at.desc()).all()
    trip_counts = dict(db.session.query(Trip.user_id, db.func.count(Trip.id)).group_by(Trip.user_id).all())
    return render_template("admin/users.html", items=items, q=q, trip_counts=trip_counts, active="users")


@bp.route("/users/<int:user_id>/<action>", methods=["POST"])
@admin_required
def user_action(user_id, action):
    u = db.session.get(User, user_id) or abort(404)
    if u.id == current_user.id and action in ("toggle", "role", "delete"):
        flash("You cannot change your own admin account here.", "error")
        return redirect(url_for("admin.users"))
    if action == "toggle":
        u.active = not u.active
        flash(f"{u.name} is now {'active' if u.active else 'deactivated'}.", "info")
    elif action == "role":
        u.role = "user" if u.is_admin else "admin"
        flash(f"{u.name} is now {u.role}.", "info")
    elif action == "delete":
        for s in ChatSession.query.filter_by(user_id=u.id).all():
            db.session.delete(s)
        Feedback.query.filter_by(user_id=u.id).update({"user_id": None})
        db.session.delete(u)
        flash("User deleted.", "info")
    db.session.commit()
    return redirect(url_for("admin.users"))


# ---------------------------------------------------------------------------
# Itineraries
# ---------------------------------------------------------------------------
@bp.route("/itineraries")
@admin_required
def itineraries():
    status = request.args.get("status", "")
    query = Trip.query
    if status:
        query = query.filter_by(status=status)
    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(Trip.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    counts = dict(db.session.query(Trip.status, db.func.count(Trip.id)).group_by(Trip.status).all())
    return render_template("admin/itineraries.html", pagination=pagination, status=status, counts=counts, active="itineraries")


@bp.route("/itineraries/<int:trip_id>/delete", methods=["POST"])
@admin_required
def itinerary_delete(trip_id):
    t = db.session.get(Trip, trip_id) or abort(404)
    db.session.delete(t)
    db.session.commit()
    flash("Itinerary deleted.", "info")
    return redirect(request.referrer or url_for("admin.itineraries"))


# ---------------------------------------------------------------------------
# Reviews & feedback
# ---------------------------------------------------------------------------
@bp.route("/feedback")
@admin_required
def feedback():
    kind = request.args.get("kind", "")
    query = Feedback.query
    if kind:
        query = query.filter_by(kind=kind)
    items = query.order_by(Feedback.created_at.desc()).all()
    sentiments = Counter(f.sentiment for f in Feedback.query.all())
    return render_template("admin/feedback.html", items=items, kind=kind, sentiments=sentiments, active="feedback")


@bp.route("/feedback/<int:fid>/<action>", methods=["POST"])
@admin_required
def feedback_action(fid, action):
    f = db.session.get(Feedback, fid) or abort(404)
    if action == "resolve":
        f.resolved = not f.resolved
    elif action == "delete":
        db.session.delete(f)
    db.session.commit()
    return redirect(request.referrer or url_for("admin.feedback"))


# ---------------------------------------------------------------------------
# AI knowledge base (RAG documents)
# ---------------------------------------------------------------------------
@bp.route("/knowledge", methods=["GET", "POST"])
@admin_required
def knowledge():
    if request.method == "POST":
        doc_id = request.form.get("id", type=int)
        title, content = request.form.get("title", "").strip(), request.form.get("content", "").strip()
        if not title or not content:
            flash("Title and content are required.", "error")
        else:
            doc = db.session.get(KnowledgeDoc, doc_id) if doc_id else KnowledgeDoc(source="admin")
            doc.title, doc.content = title[:200], content
            doc.category = request.form.get("category", "General")[:60]
            doc.updated_at = datetime.utcnow()
            db.session.add(doc)
            db.session.commit()
            refresh_engine()
            flash("Knowledge document saved and AI index rebuilt.", "success")
        return redirect(url_for("admin.knowledge"))
    engine = get_engine()
    test_q = request.args.get("test", "").strip()
    results = engine.rag.search(test_q, k=5) if test_q else []
    docs = KnowledgeDoc.query.order_by(KnowledgeDoc.source, KnowledgeDoc.updated_at.desc()).all()
    edit = db.session.get(KnowledgeDoc, request.args.get("edit", type=int)) if request.args.get("edit") else None
    return render_template("admin/knowledge.html", docs=docs, edit=edit, test_q=test_q, results=results,
                           index_size=engine.rag.size, intents=engine.intents.labels,
                           training=engine.intents.training_size, llm=engine.llm.enabled, active="knowledge")


@bp.route("/knowledge/<int:doc_id>/delete", methods=["POST"])
@admin_required
def knowledge_delete(doc_id):
    doc = db.session.get(KnowledgeDoc, doc_id) or abort(404)
    if doc.source != "admin":
        flash("Travel-guide documents are managed in data/knowledge_base.json.", "error")
    else:
        db.session.delete(doc)
        db.session.commit()
        refresh_engine()
        flash("Document deleted and AI index rebuilt.", "info")
    return redirect(url_for("admin.knowledge"))


@bp.route("/knowledge/rebuild", methods=["POST"])
@admin_required
def knowledge_rebuild():
    engine = refresh_engine()
    flash(f"AI data updated: {engine.rag.size} knowledge passages indexed, intent model retrained.", "success")
    return redirect(request.referrer or url_for("admin.knowledge"))


# ---------------------------------------------------------------------------
# Chat sessions
# ---------------------------------------------------------------------------
@bp.route("/chats")
@admin_required
def chats():
    page = request.args.get("page", 1, type=int)
    lang = request.args.get("lang", "")
    query = ChatSession.query
    if lang:
        query = query.filter_by(language=lang)
    pagination = query.order_by(ChatSession.updated_at.desc()).paginate(page=page, per_page=20, error_out=False)
    msg_counts = dict(db.session.query(ChatMessage.session_id, db.func.count(ChatMessage.id)).group_by(ChatMessage.session_id).all())
    intents = Counter(r[0] for r in db.session.query(ChatMessage.intent).filter(ChatMessage.role == "bot").all() if r[0])
    selected = db.session.get(ChatSession, request.args.get("view", type=int)) if request.args.get("view") else None
    return render_template("admin/chats.html", pagination=pagination, msg_counts=msg_counts, intents=intents.most_common(10),
                           selected=selected, lang=lang, active="chats")


@bp.route("/chats/<int:sid>/delete", methods=["POST"])
@admin_required
def chat_delete(sid):
    s = db.session.get(ChatSession, sid) or abort(404)
    db.session.delete(s)
    db.session.commit()
    flash("Chat session deleted.", "info")
    return redirect(url_for("admin.chats"))


# ---------------------------------------------------------------------------
# Analytics & reports
# ---------------------------------------------------------------------------
@bp.route("/reports")
@admin_required
def reports():
    trips = Trip.query.all()
    by_dest = Counter(t.destination.name for t in trips if t.destination)
    by_style = Counter(t.style for t in trips)
    avg_cost = int(sum(t.total_cost for t in trips) / len(trips)) if trips else 0
    avg_days = round(sum(t.days for t in trips) / len(trips), 1) if trips else 0
    intents = Counter(r[0] for r in db.session.query(ChatMessage.intent).filter(ChatMessage.role == "bot").all() if r[0])
    ratings = [f.rating for f in Feedback.query.all() if f.rating]
    cat_views = dict(db.session.query(Destination.category, db.func.sum(Destination.views)).group_by(Destination.category).all())
    return render_template("admin/reports.html", by_dest=by_dest.most_common(8), by_style=by_style, avg_cost=avg_cost,
                           avg_days=avg_days, intents=intents.most_common(), avg_rating=round(sum(ratings) / len(ratings), 2) if ratings else 0,
                           cat_views=cat_views, total_trips=len(trips), active="reports")


@bp.route("/reports/<kind>.csv")
@admin_required
def export_csv(kind):
    buf = io.StringIO()
    w = csv.writer(buf)
    if kind == "users":
        w.writerow(["id", "name", "email", "role", "language", "home_city", "interests", "active", "created_at"])
        for u in User.query.all():
            w.writerow([u.id, u.name, u.email, u.role, u.language, u.home_city, u.interests, u.active, u.created_at])
    elif kind == "itineraries":
        w.writerow(["id", "user", "title", "start_city", "destination", "days", "travelers", "style", "budget", "total_cost", "status", "created_at"])
        for t in Trip.query.all():
            w.writerow([t.id, t.user.email if t.user else "guest", t.title, t.start_city, t.destination.name if t.destination else "",
                        t.days, t.travelers, t.style, t.budget or "", t.total_cost, t.status, t.created_at])
    elif kind == "feedback":
        w.writerow(["id", "kind", "name", "destination", "rating", "sentiment", "message", "resolved", "created_at"])
        for f in Feedback.query.all():
            w.writerow([f.id, f.kind, f.name, f.destination.name if f.destination else "", f.rating, f.sentiment, f.message, f.resolved, f.created_at])
    elif kind == "destinations":
        w.writerow(["slug", "name", "district", "category", "rating", "reviews", "views", "entry_fee_indian", "lat", "lng", "active"])
        for d in Destination.query.all():
            w.writerow([d.slug, d.name, d.district, d.category, d.rating, d.reviews, d.views, d.entry_fee_indian, d.lat, d.lng, d.active])
    else:
        abort(404)
    return Response("﻿" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=yatrasathi-{kind}.csv"})
