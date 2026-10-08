"""
Intent Recognition.

A machine-learning text classifier (TF-IDF word + character n-grams fed to a
Logistic Regression model) trained on the multilingual examples in
data/intents.json, combined with a small set of high-precision keyword rules.
Character n-grams make the model work for English, Kannada and Hindi alike.
"""
import json
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from .text import normalize

# (intent, regex) checked in order - first match wins
RULES = [
    ("story", r"\bstory\b|\bstories\b|history|historical background|legend|who built|narrate|ಕಥೆ|ಇತಿಹಾಸ|ದಂತಕಥೆ|कहानी|इतिहास|किसने बनवाया|ಕಟ್ಟಿದವರು"),
    ("best_time", r"best time|when (should|to|can) (i )?(visit|go)|which month|best month|best season|good time|ಉತ್ತಮ ಸಮಯ|ಯಾವಾಗ|ಯಾವ ತಿಂಗಳು|सबसे अच्छा समय|कब जाएँ|कब जाना|किस महीने"),
    ("timings_fee", r"entry fee|entrance fee|ticket|timing|opening hours|open(ing)? time|closing time|when does .* open|ಪ್ರವೇಶ ಶುಲ್ಕ|ಟಿಕೆಟ್|ಸಮಯ ಎಷ್ಟು|ಸಮಯ$|प्रवेश शुल्क|टिकट|खुलने का समय|का समय"),
    ("how_to_reach", r"how (to|do i|can i) (reach|get|go)|reach .* from|nearest (railway|station|airport|bus)|how far|distance (from|to|between)|ಹೇಗೆ ಹೋಗುವುದು|ಹೇಗೆ ತಲುಪ|ಎಷ್ಟು ದೂರ|ರೈಲು ನಿಲ್ದಾಣ|कैसे पहुँच|कैसे पहुंच|कैसे जाएँ|दूरी|रेलवे स्टेशन"),
    ("food", r"\bfood\b|\beat\b|cuisine|dish|dishes|restaurant|must try|sweets|snack|breakfast|ಆಹಾರ|ತಿನ್ನ|ತಿಂಡಿ|ಸಿಹಿ|खाना|व्यंजन|क्या खाएँ|मिठाई"),
    ("festival", r"festival|dasara|dussehra|kambala|utsav|karaga|ugadi|ಹಬ್ಬ|ದಸರಾ|ಕಂಬಳ|त्योहार|दशहरा|कंबाला"),
    ("safety", r"\bsafe\b|safety|emergency|helpline|police|ambulance|ಸುರಕ್ಷ|ತುರ್ತು|ಸಹಾಯವಾಣಿ|सुरक्षा|सुरक्षित|आपात|हेल्पलाइन"),
    ("place_info", r"travel tips|tips for|\btips\b|things to know|ಸಲಹೆಗಳು|टिप्स"),
    ("weather", r"weather|climate|rain|monsoon|temperature|cold|hot in|ಹವಾಮಾನ|ಮಳೆ|मौसम|बारिश|जलवायु"),
    ("transport", r"ksrtc|\bbus(es)?\b booking|metro|local transport|taxi charges|train options|ಸಾರಿಗೆ|परिवहन"),
    ("nearby", r"\bnear\b|nearby|around|close to|surrounding|ಹತ್ತಿರ|ಸಮೀಪ|पास|नज़दीक|नजदीक"),
    ("attractions", r"things to do|what to see|places to see|top attractions|attractions in|sightseeing|must visit spots|ನೋಡಬೇಕಾದ|ಆಕರ್ಷಣೆ|देखने लायक|आकर्षण|क्या देखें"),
    ("plan_trip", r"itinerar|plan (a|my|the)?\s*\w*\s*trip|trip plan|travel plan|day.?wise|schedule|plan for|ಯೋಜನೆ|ವೇಳಾಪಟ್ಟಿ|योजना|प्लान|कार्यक्रम"),
    ("budget", r"how much|cost|budget|expense|price|enough|ಎಷ್ಟು ಖರ್ಚು|ಖರ್ಚು|ವೆಚ್ಚ|ಬಜೆಟ್|खर्च|बजट|कितना"),
    ("recommend", r"suggest|recommend|where (should|can) (i|we) go|best places|places to visit|getaway|ಸೂಚಿಸಿ|ಶಿಫಾರಸು|ಸ್ಥಳಗಳು|सुझाओ|सुझाव|जगहें|घूमने"),
    ("help", r"what can you do|who are you|how do you work|your features|ನೀನು ಏನು|ನೀನು ಯಾರು|तुम क्या|तुम कौन"),
]


class IntentClassifier:
    def __init__(self, intents_path):
        with open(intents_path, encoding="utf-8") as f:
            data = json.load(f)
        texts, labels = [], []
        for intent, examples in data.items():
            for ex in examples:
                texts.append(normalize(ex))
                labels.append(intent)
        self.labels = sorted(set(labels))
        self.model = Pipeline([
            ("features", FeatureUnion([
                ("words", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), token_pattern=r"(?u)[\wಀ-೿ऀ-ॿ]+", sublinear_tf=True)),
                ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True)),
            ])),
            ("clf", LogisticRegression(C=8.0, max_iter=3000, class_weight="balanced")),
        ])
        self.model.fit(texts, labels)
        self.training_size = len(texts)

    def predict_ml(self, text):
        probs = self.model.predict_proba([normalize(text)])[0]
        best = probs.argmax()
        return str(self.model.classes_[best]), float(probs[best])

    def predict(self, text, entities=None):
        """Return (intent, confidence, method)."""
        clean = normalize(text)
        entities = entities or {}
        ml_intent, ml_conf = self.predict_ml(clean)
        rule_intent = None
        for intent, pattern in RULES:
            if re.search(pattern, clean):
                rule_intent = intent
                break

        # Contextual adjustments
        if rule_intent == "budget" and not entities.get("destination"):
            rule_intent = "recommend"  # "places within 5000" -> budget based recommendation
        if rule_intent in ("recommend", "budget") and entities.get("destination") and entities.get("days") and re.search(r"trip|itinerar|plan|ಪ್ರವಾಸ|यात्रा|ट्रिप", clean):
            rule_intent = "plan_trip"
        elif rule_intent == "recommend" and entities.get("destination") and not entities.get("budget"):
            rule_intent = "attractions"  # "best places in Coorg"
        if rule_intent is None and ml_intent == "plan_trip" and not (entities.get("destination") or entities.get("days") or entities.get("budget")):
            ml_intent, ml_conf = "recommend", ml_conf * 0.9

        if rule_intent:
            return rule_intent, max(0.9, ml_conf if ml_intent == rule_intent else 0.9), "rule+ml" if ml_intent == rule_intent else "rule"
        if entities.get("interests") and not entities.get("destination") and (ml_conf < 0.5 or ml_intent in ("place_info", "attractions")):
            return "recommend", max(ml_conf, 0.6), "context"
        if ml_conf < 0.25:
            if entities.get("destination"):
                return "place_info", ml_conf, "fallback"
            return "unknown", ml_conf, "fallback"
        return ml_intent, ml_conf, "ml"
