"""
Basic NLP utilities: language detection, tokenisation, stop-word removal and
stemming. Uses NLTK where it does not need extra downloads and falls back to
built-in lists so the project runs fully offline.
"""
import re
import unicodedata

try:  # NLTK tokenizer + stemmer need no corpus download
    from nltk.stem import PorterStemmer
    from nltk.tokenize import wordpunct_tokenize
    _stemmer = PorterStemmer()
except Exception:  # pragma: no cover - NLTK missing
    _stemmer = None

    def wordpunct_tokenize(text):
        return re.findall(r"\w+|[^\w\s]+", text)

_EN_STOPWORDS = set("""
a about above after again against all am an and any are as at be because been before being below between both but by
can could did do does doing down during each few for from further had has have having he her here hers herself him
himself his how i if in into is it its itself just let me more most my myself no nor not now of off on once only or
other our ours ourselves out over own same she should so some such than that the their theirs them themselves then
there these they this those through to too under until up very was we were what when where which while who whom why
will with would you your yours yourself yourselves please tell show give want like know also get go going need
can't im i'm us
""".split())

try:
    from nltk.corpus import stopwords as _sw
    _EN_STOPWORDS |= set(_sw.words("english"))
except Exception:
    pass

_KN_STOPWORDS = {"ಮತ್ತು", "ಈ", "ಆ", "ಒಂದು", "ನನಗೆ", "ನಾನು", "ಬಗ್ಗೆ", "ಹೇಳಿ", "ಏನು", "ಇದೆ", "ಇವೆ", "ಮಾಡಿ", "ದಯವಿಟ್ಟು", "ಗೆ", "ಅಲ್ಲಿ", "ಇಲ್ಲಿ"}
_HI_STOPWORDS = {"और", "का", "की", "के", "है", "में", "से", "को", "मुझे", "मैं", "यह", "वह", "एक", "बताओ", "बताइए", "क्या", "पर", "हैं", "कृपया", "लिए"}

STOPWORDS = _EN_STOPWORDS | _KN_STOPWORDS | _HI_STOPWORDS

KANNADA_RANGE = (0x0C80, 0x0CFF)
DEVANAGARI_RANGE = (0x0900, 0x097F)


def detect_language(text: str, default: str = "en") -> str:
    """Detect English / Kannada / Hindi from the Unicode script of the text."""
    kn = hi = latin = 0
    for ch in text or "":
        code = ord(ch)
        if KANNADA_RANGE[0] <= code <= KANNADA_RANGE[1]:
            kn += 1
        elif DEVANAGARI_RANGE[0] <= code <= DEVANAGARI_RANGE[1]:
            hi += 1
        elif ch.isascii() and ch.isalpha():
            latin += 1
    if kn == hi == latin == 0:
        return default
    if kn >= hi and kn >= latin * 0.3 and kn > 0:
        return "kn"
    if hi > kn and hi >= latin * 0.3:
        return "hi"
    return "en"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "").lower()
    text = text.replace("₹", " rs ")
    return re.sub(r"\s+", " ", text).strip()


_TOKEN_RE = re.compile(r"[a-z0-9]+|[ಀ-೿‌‍]+|[ऀ-ॿ]+")


def tokenize(text: str):
    """Lower-case word tokens. English uses NLTK's word-punct tokenizer;
    Kannada / Devanagari words are kept intact (vowel signs included)."""
    text = normalize(text)
    if text.isascii():
        return [t for t in wordpunct_tokenize(text) if re.match(r"^[a-z0-9]+$", t)]
    return _TOKEN_RE.findall(text)


def remove_stopwords(tokens):
    return [t for t in tokens if t not in STOPWORDS]


def stem(token: str) -> str:
    if _stemmer and token.isascii():
        return _stemmer.stem(token)
    return token


def preprocess(text: str):
    """Full pipeline used by the retriever: tokenize -> stopwords -> stem."""
    return [stem(t) for t in remove_stopwords(tokenize(text))]
