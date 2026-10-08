"""
Database models (SQLite via Flask-SQLAlchemy).

Tables
------
users, destinations, saved_places, trips (itineraries), chat_sessions,
chat_messages, feedback (reviews / feedback / support) and knowledge_docs
(the admin-editable AI knowledge base used by the RAG module).
"""
import json
from datetime import datetime

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


def utcnow():
    return datetime.utcnow()


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user")  # "user" or "admin"
    language = db.Column(db.String(5), default="en")
    interests = db.Column(db.String(255), default="")  # comma separated
    home_city = db.Column(db.String(80), default="Bangalore")
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    saved_places = db.relationship("SavedPlace", backref="user", cascade="all, delete-orphan", lazy="dynamic")
    trips = db.relationship("Trip", backref="user", cascade="all, delete-orphan", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_active(self):  # used by Flask-Login
        return bool(self.active)

    @property
    def interests_list(self):
        return [i.strip() for i in (self.interests or "").split(",") if i.strip()]

    @property
    def first_name(self):
        return (self.name or "Traveller").split()[0]

    @property
    def initials(self):
        parts = (self.name or "U").split()
        return "".join(p[0] for p in parts[:2]).upper()


class Destination(db.Model):
    __tablename__ = "destinations"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    name_kn = db.Column(db.String(160), default="")
    name_hi = db.Column(db.String(160), default="")
    district = db.Column(db.String(80), default="")
    category = db.Column(db.String(40), default="Heritage", index=True)
    tags = db.Column(db.String(400), default="")
    description = db.Column(db.Text, default="")
    history = db.Column(db.Text, default="")
    attractions = db.Column(db.Text, default="[]")  # JSON list
    food = db.Column(db.Text, default="[]")  # JSON list
    best_from = db.Column(db.Integer, default=10)  # month number
    best_to = db.Column(db.Integer, default=3)
    timings = db.Column(db.String(120), default="")
    entry_fee_indian = db.Column(db.Integer, default=0)
    entry_fee_foreign = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=4.0)
    reviews = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    cost_index = db.Column(db.Float, default=1.0)
    ideal_days = db.Column(db.Integer, default=1)
    how_to_reach = db.Column(db.Text, default="")
    tips = db.Column(db.Text, default="")
    summary_kn = db.Column(db.Text, default="")
    summary_hi = db.Column(db.Text, default="")
    wiki = db.Column(db.String(160), default="")
    image_url = db.Column(db.String(300), default="")  # optional custom image
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)

    # ---- helpers -------------------------------------------------------
    @property
    def attractions_list(self):
        try:
            return json.loads(self.attractions or "[]")
        except ValueError:
            return []

    @property
    def food_list(self):
        try:
            return json.loads(self.food or "[]")
        except ValueError:
            return []

    @property
    def tags_list(self):
        return [t.strip() for t in (self.tags or "").split(",") if t.strip()]

    def localized_name(self, lang="en"):
        if lang == "kn" and self.name_kn:
            return self.name_kn
        if lang == "hi" and self.name_hi:
            return self.name_hi
        return self.name

    def localized_summary(self, lang="en"):
        if lang == "kn" and self.summary_kn:
            return self.summary_kn
        if lang == "hi" and self.summary_hi:
            return self.summary_hi
        return self.description

    def to_dict(self, lang="en", full=False):
        data = {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "display_name": self.localized_name(lang),
            "name_kn": self.name_kn,
            "name_hi": self.name_hi,
            "district": self.district,
            "category": self.category,
            "rating": round(self.rating or 0, 1),
            "reviews": self.reviews,
            "views": self.views,
            "lat": self.lat,
            "lng": self.lng,
            "entry_fee_indian": self.entry_fee_indian,
            "entry_fee_foreign": self.entry_fee_foreign,
            "timings": self.timings,
            "best_from": self.best_from,
            "best_to": self.best_to,
            "summary": self.localized_summary(lang),
            "wiki": self.wiki,
            "image_url": self.image_url,
            "ideal_days": self.ideal_days,
        }
        if full:
            data.update({
                "description": self.description,
                "history": self.history,
                "attractions": self.attractions_list,
                "food": self.food_list,
                "tags": self.tags_list,
                "how_to_reach": self.how_to_reach,
                "tips": self.tips,
                "summary_kn": self.summary_kn,
                "summary_hi": self.summary_hi,
                "cost_index": self.cost_index,
            })
        return data


class SavedPlace(db.Model):
    __tablename__ = "saved_places"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    destination_id = db.Column(db.Integer, db.ForeignKey("destinations.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow)
    destination = db.relationship("Destination")
    __table_args__ = (db.UniqueConstraint("user_id", "destination_id"),)


class Trip(db.Model):
    """A generated itinerary. status: generated -> saved -> upcoming -> completed / cancelled."""
    __tablename__ = "trips"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    title = db.Column(db.String(160), nullable=False)
    start_city = db.Column(db.String(80), default="Bangalore")
    destination_id = db.Column(db.Integer, db.ForeignKey("destinations.id"), nullable=True)
    days = db.Column(db.Integer, default=2)
    travelers = db.Column(db.Integer, default=2)
    budget = db.Column(db.Integer, nullable=True)
    style = db.Column(db.String(20), default="standard")
    interests = db.Column(db.String(255), default="")
    plan_json = db.Column(db.Text, default="{}")
    total_cost = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="generated", index=True)
    start_date = db.Column(db.Date, nullable=True)
    source = db.Column(db.String(20), default="planner")  # planner / chat
    language = db.Column(db.String(5), default="en")
    created_at = db.Column(db.DateTime, default=utcnow)

    destination = db.relationship("Destination")

    @property
    def plan(self):
        try:
            return json.loads(self.plan_json or "{}")
        except ValueError:
            return {}

    @property
    def end_date(self):
        if not self.start_date:
            return None
        from datetime import timedelta
        return self.start_date + timedelta(days=max(self.days - 1, 0))


class ChatSession(db.Model):
    __tablename__ = "chat_sessions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    title = db.Column(db.String(160), default="New chat")
    language = db.Column(db.String(5), default="en")
    context_json = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow)

    user = db.relationship("User")
    messages = db.relationship("ChatMessage", backref="session", cascade="all, delete-orphan",
                               order_by="ChatMessage.id", lazy="dynamic")

    @property
    def context(self):
        try:
            return json.loads(self.context_json or "{}")
        except ValueError:
            return {}

    @context.setter
    def context(self, value):
        self.context_json = json.dumps(value, ensure_ascii=False)


class ChatMessage(db.Model):
    __tablename__ = "chat_messages"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_sessions.id"), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # user / bot
    content = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(40), default="")
    language = db.Column(db.String(5), default="en")
    meta_json = db.Column(db.Text, default="{}")  # places / itinerary attached to a bot reply
    created_at = db.Column(db.DateTime, default=utcnow)

    @property
    def meta(self):
        try:
            return json.loads(self.meta_json or "{}")
        except ValueError:
            return {}


class Feedback(db.Model):
    """Reviews of places, general feedback and support requests."""
    __tablename__ = "feedback"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    destination_id = db.Column(db.Integer, db.ForeignKey("destinations.id"), nullable=True)
    name = db.Column(db.String(120), default="Guest")
    email = db.Column(db.String(160), default="")
    kind = db.Column(db.String(20), default="feedback")  # review / feedback / support
    rating = db.Column(db.Integer, default=5)
    message = db.Column(db.Text, nullable=False)
    sentiment = db.Column(db.String(10), default="neutral")
    resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utcnow)

    user = db.relationship("User")
    destination = db.relationship("Destination")


class KnowledgeDoc(db.Model):
    """Documents indexed by the RAG retriever (in addition to destination data)."""
    __tablename__ = "knowledge_docs"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(60), default="General")
    content = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(20), default="admin")  # guide / admin
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow)
