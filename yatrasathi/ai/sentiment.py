"""Lexicon-based sentiment analysis for reviews and feedback (EN / KN / HI)."""
import re

from .text import tokenize

POSITIVE = {
    "good", "great", "excellent", "amazing", "awesome", "helpful", "useful", "wonderful", "love", "loved", "nice", "best",
    "beautiful", "easy", "informative", "perfect", "fantastic", "smooth", "accurate", "recommend", "enjoyed", "superb",
    "fast", "friendly", "clean", "happy", "brilliant",
    "ಚೆನ್ನಾಗಿದೆ", "ಉತ್ತಮ", "ಅದ್ಭುತ", "ಸುಂದರ", "ಉಪಯುಕ್ತ", "ಇಷ್ಟ",
    "अच्छा", "बढ़िया", "शानदार", "सुंदर", "उपयोगी", "बेहतरीन", "पसंद",
}
NEGATIVE = {
    "bad", "poor", "worst", "slow", "wrong", "useless", "confusing", "difficult", "hate", "boring", "terrible", "awful",
    "inaccurate", "expensive", "dirty", "crowded", "broken", "error", "problem", "issue", "late", "unhelpful", "disappointed",
    "ಕೆಟ್ಟ", "ನಿಧಾನ", "ತಪ್ಪು", "ಕಷ್ಟ",
    "बुरा", "खराब", "धीमा", "गलत", "मुश्किल", "बेकार",
}
NEGATIONS = {"not", "no", "never", "dont", "don't", "isn't", "wasn't", "ಇಲ್ಲ", "नहीं", "न"}
SOFTENERS = r"can be (more |better )?(improved|optimi[sz]ed)|could be better|needs improvement|should be"


def analyze(text, rating=None):
    """Return 'positive', 'neutral' or 'negative'."""
    tokens = tokenize(text or "")
    score = 0
    for i, tok in enumerate(tokens):
        val = 1 if tok in POSITIVE else -1 if tok in NEGATIVE else 0
        if val and i > 0 and tokens[i - 1] in NEGATIONS:
            val = -val
        score += val
    if re.search(SOFTENERS, (text or "").lower()):
        score -= 1
    if rating:
        score += (int(rating) - 3)
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"
