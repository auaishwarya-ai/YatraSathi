"""Intent model, RAG retrieval, recommender, planner and chatbot tests."""
import pytest

HELD_OUT = [
    ("hey there", "greeting"), ("thank you very much", "thanks"),
    ("make a 2 day itinerary for gokarna", "plan_trip"), ("plan my trip to badami for 3 days", "plan_trip"),
    ("tell me about belur", "place_info"), ("what is jog falls famous for", "place_info"),
    ("history of chitradurga fort", "story"), ("best season to visit hampi", "best_time"),
    ("what should i eat in udupi", "food"), ("how do i get to kabini", "how_to_reach"),
    ("entry ticket for mysore palace", "timings_fee"), ("things to do in dandeli", "attractions"),
    ("places near udupi", "nearby"), ("when is dasara", "festival"), ("police helpline", "safety"),
    ("weather in chikmagalur", "weather"), ("suggest hill stations for a weekend", "recommend"),
    ("ಮೈಸೂರಿನ ಇತಿಹಾಸ", "story"), ("ಕೊಡಗಿಗೆ ಹೋಗಲು ಉತ್ತಮ ಸಮಯ", "best_time"), ("हम्पी कैसे पहुँचें", "how_to_reach"),
]


def test_intent_accuracy(engine):
    correct = 0
    for text, expected in HELD_OUT:
        u = engine.nlu.understand(text)
        intent, conf, _ = engine.intents.predict(text, u)
        correct += intent == expected
    assert correct / len(HELD_OUT) >= 0.85


def test_rag_retrieves_relevant_passage(engine):
    top = engine.rag.search("who built gol gumbaz", k=3, slug="gol-gumbaz", intent="story")
    assert top[0]["slug"] == "gol-gumbaz" and top[0]["section"] == "history"
    fest = engine.rag.search("when is mysuru dasara celebrated", k=3, intent="festival")
    assert any("Dasara" in r["title"] for r in fest)


def test_recommender_respects_interests(engine):
    recs = engine.recommender.recommend(interests=["Beaches"], limit=5)
    cats = [engine.by_slug[r["slug"]]["category"] for r in recs]
    assert cats.count("Beaches") >= 4


def test_similar_places(engine):
    sim = engine.recommender.similar("belur", 3)
    assert "halebidu" in sim


@pytest.mark.parametrize("dest,days", [("coorg", 3), ("hampi", 5), ("mysore-palace", 1), ("gokarna", 2)])
def test_plan_structure(engine, dest, days):
    p = engine.planner.plan(dest, "Bangalore", days, 2)
    assert len(p["day_plans"]) == days
    c = p["costs"]
    parts = c["transport"] + c["local_transport"] + c["accommodation"] + c["food"] + c["entry_fees"] + c["misc"]
    assert abs(parts - c["total"]) <= 60
    assert c["nights"] == days - 1


def test_budget_optimisation(engine):
    rich = engine.planner.plan("coorg", "Bangalore", 3, 2, budget=None, style="luxury")
    tight = engine.planner.plan("coorg", "Bangalore", 3, 2, budget=12000, style="luxury")
    assert tight["costs"]["total"] <= 12000
    assert tight["budget_status"] == "optimized"
    assert tight["costs"]["total"] < rich["costs"]["total"]
    impossible = engine.planner.plan("coorg", "Bangalore", 3, 2, budget=1000)
    assert impossible["budget_status"] == "over"


def test_suggest_by_budget(engine):
    fits, _ = engine.planner.suggest_by_budget("Bangalore", 2, 2, 5000)
    assert fits and all(f["total"] <= 5000 for f in fits)


def test_chat_context_and_languages(engine):
    r1 = engine.reply("Suggest a 3 day trip to Coorg from Bangalore", "en", {})
    assert r1["intent"] == "plan_trip" and r1["itinerary"]["days"] == 3
    r2 = engine.reply("Plan for 4 people", "en", r1["context"])
    assert r2["itinerary"]["destination"]["slug"] == "coorg" and r2["itinerary"]["travelers"] == 4
    r3 = engine.reply("what to eat there", "en", r2["context"])
    assert r3["intent"] == "food" and "Pandi" in r3["reply"]
    kn = engine.reply("ಹಂಪಿಯ ಕಥೆ ಹೇಳಿ", "en", {})
    assert kn["language"] == "kn" and "ಹಂಪಿ" in kn["reply"]
    hi = engine.reply("गोल गुंबज का प्रवेश शुल्क", "en", {})
    assert hi["language"] == "hi" and "₹25" in hi["reply"]


def test_unknown_question_fallback(engine):
    r = engine.reply("what is the capital of france", "en", {})
    assert r["intent"] == "unknown"


def test_sentiment():
    from yatrasathi.ai.sentiment import analyze
    assert analyze("Great platform, very helpful!", 5) == "positive"
    assert analyze("Itinerary suggestions can be more optimized.", 3) == "negative" or analyze("Itinerary suggestions can be more optimized.", 3) == "neutral"
    assert analyze("Very bad and slow", 1) == "negative"
