"""Input processing + query understanding (entity extraction) tests."""
from yatrasathi.ai.text import detect_language, preprocess


def test_language_detection():
    assert detect_language("Plan a trip to Coorg") == "en"
    assert detect_language("ಹಂಪಿಯ ಕಥೆ ಹೇಳಿ") == "kn"
    assert detect_language("हम्पी की कहानी सुनाओ") == "hi"


def test_preprocess_removes_stopwords_and_stems():
    tokens = preprocess("Tell me about the waterfalls of Karnataka")
    assert "the" not in tokens and "about" not in tokens
    assert "waterfal" in tokens or "waterfall" in tokens


def test_entities_english(engine):
    u = engine.nlu.understand("Suggest a 3 day trip to Coorg from Bangalore for 4 people within Rs 15,000")
    assert u["destination"] == "coorg"
    assert u["start_city"] == "Bangalore"
    assert u["days"] == 3
    assert u["travelers"] == 4
    assert u["budget"] == 15000


def test_entities_budget_formats(engine):
    assert engine.nlu.understand("places for 2 days within ₹5000")["budget"] == 5000
    assert engine.nlu.understand("weekend trip under 8k")["budget"] == 8000
    assert engine.nlu.understand("weekend trip under 8k")["days"] == 2
    assert engine.nlu.understand("2 nights in hampi")["days"] == 3


def test_entities_kannada_and_hindi(engine):
    kn = engine.nlu.understand("ಬೆಂಗಳೂರಿನಿಂದ ಕೊಡಗಿಗೆ 2 ದಿನದ ಪ್ರವಾಸ")
    assert kn["destination"] == "coorg" and kn["start_city"] == "Bangalore" and kn["days"] == 2
    hi = engine.nlu.understand("कूर्ग के लिए 3 दिन की यात्रा योजना बनाओ, बजट 10 हजार")
    assert hi["destination"] == "coorg" and hi["days"] == 3 and hi["budget"] == 10000


def test_typo_tolerance(engine):
    assert engine.nlu.understand("plan trip to chikmaglur")["destination"] == "chikmagalur"


def test_interests(engine):
    assert "Waterfalls" in engine.nlu.understand("show me waterfalls")["interests"]
    assert "Wildlife" in engine.nlu.understand("tiger safari please")["interests"]
