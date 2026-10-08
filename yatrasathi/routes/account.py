"""My Account: dashboard, My Trips, Saved Places, Chat History, Profile & preferences."""
import json
from datetime import date, datetime

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, session, url_for
from flask_login import current_user, login_required, logout_user

from ..ai.nlp import INTERESTS
from ..i18n import LANGUAGES
from ..models import ChatSession, Feedback, SavedPlace, Trip, db
from ..utils.pdf import itinerary_pdf

bp = Blueprint("account", __name__, url_prefix="/account")


def _cities():
    with open(current_app.config["DATA_DIR"] / "cities.json", encoding="utf-8") as f:
        return json.load(f)


def _user_trips():
    return Trip.query.filter(Trip.user_id == current_user.id, Trip.status != "generated")


def trip_tabs():
    today = date.today()
    trips = _user_trips().order_by(Trip.start_date.is_(None), Trip.start_date, Trip.created_at.desc()).all()
    upcoming = [t for t in trips if t.status == "upcoming" and (not t.start_date or t.start_date >= today)]
    completed = [t for t in trips if t.status == "completed" or (t.status == "upcoming" and t.start_date and t.start_date < today)]
    saved = [t for t in trips if t.status == "saved"]
    return upcoming, saved, completed


@bp.route("/")
@login_required
def dashboard():
    upcoming, saved, completed = trip_tabs()
    stats = {
        "upcoming": len(upcoming),
        "saved_places": current_user.saved_places.count(),
        "chats": ChatSession.query.filter_by(user_id=current_user.id).count(),
        "itineraries": _user_trips().count(),
        "reviews": Feedback.query.filter_by(user_id=current_user.id).count(),
    }
    recent = (upcoming + saved + completed)[:5]
    recent_itins = _user_trips().order_by(Trip.created_at.desc()).limit(3).all()
    return render_template("account/dashboard.html", stats=stats, trips=recent, recent_itins=recent_itins, active="dashboard")


@bp.route("/trips")
@login_required
def trips():
    upcoming, saved, completed = trip_tabs()
    tab = request.args.get("tab", "upcoming")
    lists = {"upcoming": upcoming, "saved": saved, "completed": completed}
    return render_template("account/trips.html", tab=tab, trips=lists.get(tab, upcoming),
                           counts={k: len(v) for k, v in lists.items()}, active="trips")


def _get_trip(trip_id, allow_guest=True):
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id is None and allow_guest:
        return trip
    if not current_user.is_authenticated or (trip.user_id != current_user.id and not current_user.is_admin):
        abort(403)
    return trip


@bp.route("/trips/<int:trip_id>")
def trip_detail(trip_id):
    trip = _get_trip(trip_id)
    return render_template("account/trip_detail.html", trip=trip, plan=trip.plan, active="trips")


@bp.route("/trips/<int:trip_id>/update", methods=["POST"])
@login_required
def trip_update(trip_id):
    trip = _get_trip(trip_id, allow_guest=False)
    status = request.form.get("status")
    if status in ("saved", "upcoming", "completed", "cancelled"):
        trip.status = status
    start = request.form.get("start_date")
    if start:
        try:
            trip.start_date = datetime.strptime(start, "%Y-%m-%d").date()
            if trip.status == "saved":
                trip.status = "upcoming"
        except ValueError:
            flash("Invalid date.", "error")
    title = request.form.get("title", "").strip()
    if title:
        trip.title = title[:160]
    db.session.commit()
    flash("Trip updated.", "success")
    return redirect(request.referrer or url_for("account.trip_detail", trip_id=trip.id))


@bp.route("/trips/<int:trip_id>/delete", methods=["POST"])
@login_required
def trip_delete(trip_id):
    trip = _get_trip(trip_id, allow_guest=False)
    db.session.delete(trip)
    db.session.commit()
    flash("Trip deleted.", "info")
    return redirect(url_for("account.trips"))


@bp.route("/trips/<int:trip_id>/pdf")
def trip_pdf(trip_id):
    trip = _get_trip(trip_id)
    try:
        buf = itinerary_pdf(trip)
    except ImportError:  # PDF library blocked/missing on this computer
        flash("PDF download is unavailable on this computer. Use the Print button and choose 'Save as PDF'.", "error")
        return redirect(url_for("account.trip_detail", trip_id=trip.id))
    name = f"YatraSathi-{trip.title.replace(' ', '-')}.pdf"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=name)


@bp.route("/saved")
@login_required
def saved():
    items = SavedPlace.query.filter_by(user_id=current_user.id).order_by(SavedPlace.created_at.desc()).all()
    return render_template("account/saved.html", items=items, active="saved")


@bp.route("/chats")
@login_required
def chats():
    sessions = ChatSession.query.filter_by(user_id=current_user.id).order_by(ChatSession.updated_at.desc()).all()
    return render_template("account/chats.html", sessions=sessions, active="chats")


@bp.route("/chats/<int:session_id>/delete", methods=["POST"])
@login_required
def chat_delete(session_id):
    s = ChatSession.query.get_or_404(session_id)
    if s.user_id != current_user.id:
        abort(403)
    db.session.delete(s)
    db.session.commit()
    flash("Conversation deleted.", "info")
    return redirect(url_for("account.chats"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        action = request.form.get("action", "profile")
        if action == "profile":
            name = request.form.get("name", "").strip()
            if len(name) >= 2:
                current_user.name = name[:120]
            current_user.home_city = request.form.get("home_city", current_user.home_city)
            current_user.interests = ",".join(i for i in request.form.getlist("interests") if i in INTERESTS)
            lang = request.form.get("language")
            if lang in LANGUAGES:
                current_user.language = lang
                session["lang"] = lang
            db.session.commit()
            flash("Profile updated.", "success")
        elif action == "password":
            if not current_user.check_password(request.form.get("current_password", "")):
                flash("Current password is incorrect.", "error")
            elif len(request.form.get("new_password", "")) < 6:
                flash("Password must be at least 6 characters.", "error")
            else:
                current_user.set_password(request.form["new_password"])
                db.session.commit()
                flash("Password changed.", "success")
        return redirect(url_for("account.profile", section=request.form.get("section", "")))
    return render_template("account/profile.html", cities=_cities(), interests=INTERESTS, active=request.args.get("section") or "profile")


@bp.route("/delete", methods=["POST"])
@login_required
def delete_account():
    if current_user.is_admin:
        flash("Admin accounts cannot be deleted from here.", "error")
        return redirect(url_for("account.profile"))
    if not current_user.check_password(request.form.get("password", "")):
        flash("Password is incorrect.", "error")
        return redirect(url_for("account.profile", section="privacy"))
    user = current_user._get_current_object()
    for s in ChatSession.query.filter_by(user_id=user.id).all():
        db.session.delete(s)
    Feedback.query.filter_by(user_id=user.id).update({"user_id": None})
    logout_user()
    db.session.delete(user)
    db.session.commit()
    flash("Your account has been deleted.", "info")
    return redirect(url_for("main.index"))
