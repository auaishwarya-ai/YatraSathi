"""
YatraSathi - Context-Aware Conversational AI for Intelligent Travel Planning
and Smart Tourism (Karnataka).

Flask application factory.
"""
import json
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, request, session
from flask_login import LoginManager, current_user

from config import Config

from .i18n import JS_STRINGS, LANGUAGES, translate
from .models import User, db
from .utils.images import place_image_url

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"

CATEGORY_ICONS = {
    "Heritage": "landmark", "Temples": "church", "Hill Stations": "mountain-snow", "Waterfalls": "waves",
    "Beaches": "umbrella", "Wildlife": "paw-print", "Adventure": "tent", "Gardens & Parks": "flower-2",
}
CATEGORY_SLUGS = {
    "Heritage": "heritage", "Temples": "temples", "Hill Stations": "hill-stations", "Waterfalls": "waterfalls",
    "Beaches": "beaches", "Wildlife": "wildlife", "Adventure": "adventure", "Gardens & Parks": "gardens",
}


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def current_lang():
    lang = session.get("lang")
    if not lang and current_user and getattr(current_user, "is_authenticated", False):
        lang = current_user.language
    return lang if lang in LANGUAGES else "en"


def create_app(config_class=Config):
    app = Flask(__name__, instance_path=str(Path(__file__).resolve().parent.parent / "instance"))
    app.config.from_object(config_class)
    app.json.ensure_ascii = False
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    db.init_app(app)
    login_manager.init_app(app)

    from .routes.account import bp as account_bp
    from .routes.admin import bp as admin_bp
    from .routes.api import bp as api_bp
    from .routes.auth import bp as auth_bp
    from .routes.main import bp as main_bp
    for bp in (main_bp, auth_bp, account_bp, admin_bp, api_bp):
        app.register_blueprint(bp)

    @app.context_processor
    def inject_helpers():
        lang = current_lang()

        def _(text, **kwargs):
            out = translate(text, lang)
            return out.format(**kwargs) if kwargs else out

        def place_name(dest):
            if dest is None:
                return ""
            if isinstance(dest, dict):
                return dest.get(f"name_{lang}") or dest.get("name") if lang != "en" else dest.get("name")
            return dest.localized_name(lang)

        def place_image(dest):
            """Local image if downloaded, else custom URL; the browser fetches a Wikipedia photo otherwise."""
            if isinstance(dest, dict):
                return place_image_url(dest["slug"], dest.get("image_url"))
            return place_image_url(dest.slug, dest.image_url)

        def placeholder(category):
            return f"/static/images/placeholders/{CATEGORY_SLUGS.get(category, 'heritage')}.svg"

        return {
            "_": _, "lang": lang, "LANGUAGES": LANGUAGES, "place_name": place_name, "place_image": place_image,
            "placeholder": placeholder, "CATEGORY_ICONS": CATEGORY_ICONS, "now": datetime.utcnow(),
            "js_strings": json.dumps({k: translate(k, lang) for k in JS_STRINGS}, ensure_ascii=False),
            "llm_enabled": bool(app.config.get("OPENAI_API_KEY")),
        }

    @app.template_filter("money")
    def money_filter(value):
        from .ai.responses import money
        return money(value)

    @app.template_filter("month_range")
    def month_range_filter(dest):
        from .ai.responses import month_range
        return month_range(current_lang(), dest.best_from, dest.best_to)

    @app.template_filter("category")
    def category_filter(cat):
        return translate(cat, current_lang())

    @app.template_filter("dt")
    def dt_filter(value, fmt="%d %b %Y"):
        return value.strftime(fmt) if value else ""

    @app.before_request
    def remember_language():
        lang = request.args.get("lang")
        if lang in LANGUAGES:
            session["lang"] = lang

    from flask import render_template

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403, message="You do not have permission to view this page."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, message="Sorry, we could not find that page."), 404

    @app.errorhandler(500)
    def server_error(_e):
        db.session.rollback()
        return render_template("error.html", code=500, message="Something went wrong. Please try again."), 500

    from .ai import engine as engine_module
    engine_module._engine = None  # fresh engine per app instance

    from .seed import init_database
    init_database(app)
    return app
