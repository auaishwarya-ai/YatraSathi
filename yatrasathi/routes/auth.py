"""Login, registration and logout."""
import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..models import ChatSession, User, db

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _safe_next(target):
    return target if target and target.startswith("/") and not target.startswith("//") else None


def _claim_guest_chats(user):
    """Attach chats started as a guest to the account after login."""
    ids = session.pop("guest_chats", [])
    if ids:
        ChatSession.query.filter(ChatSession.id.in_(ids), ChatSession.user_id.is_(None)).update(
            {"user_id": user.id}, synchronize_session=False)
        db.session.commit()


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("account.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(request.form.get("password", "")):
            if not user.active:
                flash("This account has been deactivated.", "error")
            else:
                login_user(user, remember=bool(request.form.get("remember")))
                session["lang"] = user.language or session.get("lang", "en")
                _claim_guest_chats(user)
                nxt = _safe_next(request.args.get("next"))
                return redirect(nxt or (url_for("admin.dashboard") if user.is_admin else url_for("account.dashboard")))
        else:
            flash("Invalid email or password.", "error")
    return render_template("auth.html", mode="login")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("account.dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        error = None
        if len(name) < 2:
            error = "Please enter your name."
        elif not EMAIL_RE.match(email):
            error = "Please enter a valid email address."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif User.query.filter_by(email=email).first():
            error = "An account with this email already exists."
        if error:
            flash(error, "error")
        else:
            user = User(name=name, email=email, language=session.get("lang", "en"),
                        home_city=request.form.get("home_city", "Bangalore"),
                        interests=",".join(request.form.getlist("interests")))
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            _claim_guest_chats(user)
            flash("Welcome to YatraSathi! Your account has been created.", "success")
            return redirect(url_for("account.dashboard"))
    return render_template("auth.html", mode="register")


@bp.route("/logout")
@login_required
def logout():
    lang = session.get("lang")
    logout_user()
    session.clear()
    if lang:
        session["lang"] = lang
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
"""Login, registration and logout."""
import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..models import ChatSession, User, db

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _safe_next(target):
    return target if target and target.startswith("/") and not target.startswith("//") else None


def _claim_guest_chats(user):
    """Attach chats started as a guest to the account after login."""
    ids = session.pop("guest_chats", [])
    if ids:
        ChatSession.query.filter(ChatSession.id.in_(ids), ChatSession.user_id.is_(None)).update(
            {"user_id": user.id}, synchronize_session=False)
        db.session.commit()


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("account.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(request.form.get("password", "")):
            if not user.active:
                flash("This account has been deactivated.", "error")
            else:
                login_user(user, remember=bool(request.form.get("remember")))
                session["lang"] = user.language or session.get("lang", "en")
                _claim_guest_chats(user)
                nxt = _safe_next(request.args.get("next"))
                return redirect(nxt or (url_for("admin.dashboard") if user.is_admin else url_for("account.dashboard")))
        else:
            flash("Invalid email or password.", "error")
    return render_template("auth.html", mode="login")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("account.dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        error = None
        if len(name) < 2:
            error = "Please enter your name."
        elif not EMAIL_RE.match(email):
            error = "Please enter a valid email address."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif User.query.filter_by(email=email).first():
            error = "An account with this email already exists."
        if error:
            flash(error, "error")
        else:
            user = User(name=name, email=email, language=session.get("lang", "en"),
                        home_city=request.form.get("home_city", "Bangalore"),
                        interests=",".join(request.form.getlist("interests")))
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            _claim_guest_chats(user)
            flash("Welcome to YatraSathi! Your account has been created.", "success")
            return redirect(url_for("account.dashboard"))
    return render_template("auth.html", mode="register")


@bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    # Preserve the language preference
    lang = session.get("lang", "en")

    # Clear other session data BEFORE logging out
    session.clear()

    # Log out the user and allow Flask-Login to clear
    # its remember-me cookie correctly
    logout_user()

    # Restore the language preference
    session["lang"] = lang

    flash("You have been logged out successfully.", "success")

    response = redirect(url_for("main.index"))

    # Prevent cached pages from displaying old admin content
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response

