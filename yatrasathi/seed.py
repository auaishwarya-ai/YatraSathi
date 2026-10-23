"""
Data Collection -> Data Preprocessing -> Travel Database.

1. Loads the raw tourism dataset (data/destinations/*.json).
2. Cleans it with pandas: removes duplicates, fills missing values,
   normalises text, validates ratings / fees / coordinates.
3. Stores the clean records in the SQLite travel database.
4. Optionally creates demo users, trips, chats and feedback so the admin
   dashboard has something to show on first run.
"""
import json
import random
from datetime import date, datetime, timedelta

import pandas as pd

from .ai.sentiment import analyze
from .models import (ChatMessage, ChatSession, Destination, Feedback, KnowledgeDoc, SavedPlace, Trip, User, db)

KARNATAKA_BBOX = {"lat": (11.4, 18.6), "lng": (73.9, 78.7)}
# demo popularity (matches the design mock-ups)
TOP_VIEWS = {"hampi": 15632, "mysore-palace": 12845, "coorg": 10243, "jog-falls": 9876, "gokarna": 8761, "badami": 7920,
             "chikmagalur": 7410, "udupi-krishna-temple": 7105}
CATEGORIES = ["Heritage", "Temples", "Hill Stations", "Waterfalls", "Beaches", "Wildlife", "Adventure", "Gardens & Parks"]


# ---------------------------------------------------------------------------
# Data collection + preprocessing
# ---------------------------------------------------------------------------
def load_raw_destinations(data_dir):
    records = []
    for path in sorted((data_dir / "destinations").glob("*.json")):
        with open(path, encoding="utf-8") as f:
            records.extend(json.load(f))
    return pd.DataFrame(records)


def preprocess_destinations(df):
    """Clean the raw dataset and return a list of dicts ready for the database."""
    df = df.copy()
    # 1. Remove duplicate / incomplete records
    df["slug"] = df["slug"].astype(str).str.strip().str.lower()
    df = df.drop_duplicates(subset="slug", keep="first")
    df = df.dropna(subset=["name", "lat", "lng"])
    # 2. Normalise text columns
    text_cols = ["name", "name_kn", "name_hi", "district", "category", "description", "history", "timings",
                 "how_to_reach", "tips", "summary_kn", "summary_hi", "wiki"]
    for col in text_cols:
        if col not in df:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    df["category"] = df["category"].where(df["category"].isin(CATEGORIES), "Heritage")
    # 3. Handle missing numeric values and clip to valid ranges
    df["rating"] = pd.to_numeric(df.get("rating"), errors="coerce").fillna(4.0).clip(0, 5)
    df["reviews"] = pd.to_numeric(df.get("reviews"), errors="coerce").fillna(0).astype(int).clip(lower=0)
    for col in ("entry_fee_indian", "entry_fee_foreign"):
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0).astype(int).clip(lower=0)
    df["cost_index"] = pd.to_numeric(df.get("cost_index"), errors="coerce").fillna(1.0).clip(0.5, 2.5)
    df["ideal_days"] = pd.to_numeric(df.get("ideal_days"), errors="coerce").fillna(1).astype(int).clip(1, 5)
    # 4. Filter records outside Karnataka (bad coordinates)
    df = df[df["lat"].between(*KARNATAKA_BBOX["lat"]) & df["lng"].between(*KARNATAKA_BBOX["lng"])]
    # 5. Structure list fields
    for col in ("tags", "attractions", "food"):
        df[col] = df[col].apply(lambda v: [str(x).strip() for x in v if str(x).strip()] if isinstance(v, list) else [])
    df["best_from"] = df["best_months"].apply(lambda v: int(v[0]) if isinstance(v, list) and len(v) == 2 else 10)
    df["best_to"] = df["best_months"].apply(lambda v: int(v[1]) if isinstance(v, list) and len(v) == 2 else 3)
    return df.to_dict(orient="records")


def seed_destinations(data_dir):
    records = preprocess_destinations(load_raw_destinations(data_dir))
    rng = random.Random(7)
    for r in records:
        if Destination.query.filter_by(slug=r["slug"]).first():
            continue
        db.session.add(Destination(
            slug=r["slug"], name=r["name"], name_kn=r["name_kn"], name_hi=r["name_hi"], district=r["district"],
            category=r["category"], tags=",".join(r["tags"]), description=r["description"], history=r["history"],
            attractions=json.dumps(r["attractions"], ensure_ascii=False), food=json.dumps(r["food"], ensure_ascii=False),
            best_from=r["best_from"], best_to=r["best_to"], timings=r["timings"],
            entry_fee_indian=r["entry_fee_indian"], entry_fee_foreign=r["entry_fee_foreign"],
            rating=round(float(r["rating"]), 1), reviews=int(r["reviews"]),
            views=TOP_VIEWS.get(r["slug"], int(r["reviews"] * rng.uniform(5, 8))), lat=float(r["lat"]), lng=float(r["lng"]),
            cost_index=float(r["cost_index"]), ideal_days=int(r["ideal_days"]), how_to_reach=r["how_to_reach"],
            tips=r["tips"], summary_kn=r["summary_kn"], summary_hi=r["summary_hi"], wiki=r["wiki"],
        ))
    db.session.commit()
    return len(records)


def seed_knowledge(data_dir):
    with open(data_dir / "knowledge_base.json", encoding="utf-8") as f:
        kb = json.load(f)
    if KnowledgeDoc.query.filter_by(source="guide").count():
        return
    for sec in kb["sections"]:
        for item in sec["content"]:
            db.session.add(KnowledgeDoc(title=f"{sec['title']} - {item['heading']}", category=sec["title"],
                                        content=item["text"], source="guide"))
    db.session.commit()


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------
FIRST = ["Rahul", "Priya", "Ankit", "Sneha", "Vikram", "Neha", "Arjun", "Kavya", "Rohan", "Divya", "Karthik", "Meghana",
         "Suresh", "Pooja", "Manoj", "Ananya", "Nikhil", "Shreya", "Varun", "Bhavana", "Harish", "Lakshmi", "Pranav",
         "Ishita", "Sagar", "Ramya", "Aditya", "Spoorthi", "Gaurav", "Nandini", "Tejas", "Akshata", "Imran", "Fathima",
         "Joseph", "Sanjana", "Mohan", "Deepa", "Kiran", "Swathi"]
LAST = ["Sharma", "Nair", "Verma", "Iyer", "Singh", "Kumar", "Rao", "Reddy", "Gowda", "Hegde", "Shetty", "Patil",
        "Joshi", "Bhat", "Kulkarni", "Naik", "Menon", "Das", "Khan", "D'Souza"]

DEMO_FEEDBACK = [
    ("Great platform! AI assistant is very helpful.", 5),
    ("Itinerary suggestions can be more optimized.", 3),
    ("Wonderful experience. Very informative!", 5),
    ("Kannada voice answers are amazing for my parents.", 5),
    ("Budget estimate for Coorg was accurate, thanks!", 4),
    ("Map view is useful but loading images was slow.", 3),
    ("Loved the Hampi story mode.", 5),
    ("Please add more places in North Karnataka.", 4),
]

DEMO_CHATS = [
    ("en", ["Suggest a 3 day trip to Coorg from Bangalore", "Best time to visit Coorg"]),
    ("en", ["Tell me the story of Hampi", "How to reach Hampi from Bangalore"]),
    ("kn", ["ಹಂಪಿಯ ಕಥೆ ಹೇಳಿ", "ಮೈಸೂರು ಅರಮನೆಯ ಸಮಯ"]),
    ("hi", ["कूर्ग के लिए 3 दिन की यात्रा योजना बनाओ", "जोग फॉल्स कब जाएँ"]),
    ("en", ["Suggest places in Karnataka for 2 days within ₹5000"]),
    ("en", ["Must try food in Mangalore", "Places near Udupi"]),
    ("kn", ["ಕೊಡಗಿನ ಪ್ರಸಿದ್ಧ ಆಹಾರ"]),
    ("en", ["Top waterfalls", "Best time to visit Jog Falls"]),
]


def seed_demo(engine_factory):
    """Create admin, demo user and ~40 demo users with trips, chats and feedback."""
    if User.query.count():
        return
    rng = random.Random(42)
    now = datetime.utcnow()

    admin = User(name="Admin", email="admin@yatrasathi.in", role="admin", home_city="Bangalore", created_at=now - timedelta(days=90))
    admin.set_password("admin123")
    demo = User(name="Aishwarya U", email="aishwarya@yatrasathi.in", home_city="Bangalore", language="en",
                interests="Heritage,Nature,Adventure", created_at=now - timedelta(days=60))
    demo.set_password("user123")
    db.session.add_all([admin, demo])

    users = [demo]
    for i in range(38):
        name = f"{FIRST[i % len(FIRST)]} {LAST[rng.randrange(len(LAST))]}"
        u = User(name=name, email=f"{name.split()[0].lower()}{i}@example.com",
                 language=rng.choices(["en", "kn", "hi"], weights=[52, 28, 15])[0],
                 interests=",".join(rng.sample(["Nature", "Heritage", "Adventure", "Spiritual", "Wildlife", "Beaches"], 2)),
                 home_city=rng.choice(["Bangalore", "Mysuru", "Mangaluru", "Hubballi", "Belagavi"]),
                 created_at=now - timedelta(days=int(rng.triangular(0, 60, 0)), hours=rng.randint(0, 23)))
        u.set_password("user123")
        users.append(u)
        db.session.add(u)
    db.session.commit()

    engine = engine_factory()
    dests = {d.slug: d for d in Destination.query.all()}
    popular = ["coorg", "hampi", "mysore-palace", "gokarna", "chikmagalur", "jog-falls", "udupi-krishna-temple",
               "kabini", "badami", "dandeli", "murudeshwar", "nandi-hills"]

    # Saved places for the demo user
    for slug in ["hampi", "coorg", "mysore-palace", "jog-falls", "gokarna", "badami", "chikmagalur", "kabini"]:
        db.session.add(SavedPlace(user_id=demo.id, destination_id=dests[slug].id))
    for u in users[1:]:
        for slug in rng.sample(popular, 2):
            db.session.add(SavedPlace(user_id=u.id, destination_id=dests[slug].id))

    # Trips / itineraries
    today = date.today()
    demo_trips = [("coorg", 3, "upcoming", 6), ("mysore-palace", 2, "upcoming", 14), ("hampi", 3, "upcoming", 40),
                  ("gokarna", 3, "saved", None), ("chikmagalur", 2, "completed", -30)]
    for slug, days, status, offset in demo_trips:
        _make_trip(engine, demo, slug, days, 2, status, today + timedelta(days=offset) if offset is not None else None,
                   now - timedelta(days=rng.randint(1, 25)))
    for _ in range(160):
        u = rng.choice(users[1:])
        slug = rng.choice(popular)
        status = rng.choices(["generated", "saved", "upcoming", "completed"], weights=[50, 20, 15, 15])[0]
        _make_trip(engine, u, slug, rng.randint(1, 4), rng.choice([1, 2, 2, 3, 4]), status,
                   today + timedelta(days=rng.randint(-40, 60)) if status in ("upcoming", "completed") else None,
                   now - timedelta(days=int(rng.triangular(0, 60, 0)), hours=rng.randint(0, 23)),
                   style=rng.choice(["budget", "standard", "standard", "luxury"]))

    # Chat sessions (with real engine replies)
    for i in range(90):
        lang, msgs = DEMO_CHATS[i % len(DEMO_CHATS)]
        u = rng.choice(users + [None])
        created = now - timedelta(days=int(rng.triangular(0, 60, 0)), hours=rng.randint(0, 23))
        session = ChatSession(user_id=u.id if u else None, language=lang, title=msgs[0][:60], created_at=created, updated_at=created)
        db.session.add(session)
        db.session.flush()
        ctx = {}
        for m in msgs:
            r = engine.reply(m, lang, ctx)
            ctx = r["context"]
            db.session.add(ChatMessage(session_id=session.id, role="user", content=m, language=lang, created_at=created))
            db.session.add(ChatMessage(session_id=session.id, role="bot", content=r["reply"], intent=r["intent"],
                                       language=r["language"], created_at=created))
        session.context = ctx

    # Feedback & reviews
    for i, (msg, rating) in enumerate(DEMO_FEEDBACK):
        u = users[i + 3]
        db.session.add(Feedback(user_id=u.id, name=f"{u.name.split()[0]} {u.name.split()[-1][0]}.", email=u.email, kind="feedback",
                                rating=rating, message=msg, sentiment=analyze(msg, rating),
                                created_at=now - timedelta(days=i, hours=rng.randint(0, 12))))
    review_texts = ["Beautiful place, must visit!", "Crowded on weekends but worth it.", "Amazing history and architecture.",
                    "Great for a family trip.", "Roads were bad but the view was superb."]
    for slug in popular[:8]:
        for _ in range(2):
            u = rng.choice(users[1:])
            msg = rng.choice(review_texts)
            rating = rng.choice([4, 5, 5, 3])
            db.session.add(Feedback(user_id=u.id, destination_id=dests[slug].id, name=u.name, kind="review",
                                    rating=rating, message=msg, sentiment=analyze(msg, rating),
                                    created_at=now - timedelta(days=rng.randint(0, 40))))
    db.session.commit()


def _make_trip(engine, user, slug, days, travelers, status, start_date, created, style="standard"):
    plan = engine.planner.plan(slug, user.home_city or "Bangalore", days, travelers, None, user.interests_list, style)
    dest = Destination.query.filter_by(slug=slug).first()
    db.session.add(Trip(user_id=user.id, title=f"{dest.name} {'Getaway' if days > 1 else 'Day Trip'}",
                        start_city=plan["start_city"], destination_id=dest.id, days=plan["days"], travelers=travelers,
                        style=plan["style"], interests=",".join(user.interests_list),
                        plan_json=json.dumps(plan, ensure_ascii=False), total_cost=plan["costs"]["total"], status=status,
                        start_date=start_date, created_at=created))


def init_database(app):
    """Create tables and seed data on first run."""
    from .ai.engine import get_engine
    with app.app_context():
        db.create_all()
        if Destination.query.count() == 0:
            n = seed_destinations(app.config["DATA_DIR"])
            app.logger.info("Seeded %s destinations", n)
        seed_knowledge(app.config["DATA_DIR"])
        if User.query.count() == 0:
            if app.config.get("LOAD_DEMO_DATA"):
                seed_demo(get_engine)
            else:
                admin = User(name="Admin", email="admin@yatrasathi.in", role="admin")
                admin.set_password("admin123")
                db.session.add(admin)
                db.session.commit()
