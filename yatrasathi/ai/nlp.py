"""
Input Processing + Query Understanding modules.

Extracts the travel entities described in the project architecture from a
free-text query in English, Kannada or Hindi:
destination(s), starting city, number of days, budget, travellers,
interests, travel style and month.
"""
import difflib
import re

from .text import STOPWORDS, detect_language, normalize, tokenize

# ---------------------------------------------------------------------------
# Lexicons
# ---------------------------------------------------------------------------
INTERESTS = ["Nature", "Adventure", "Heritage", "Relaxation", "Spiritual", "Wildlife", "Beaches", "Waterfalls", "Hill Stations"]

INTEREST_KEYWORDS = {
    "Nature": ["nature", "green", "scenic", "hills", "forest", "misty", "coffee", "plantation", "ಪ್ರಕೃತಿ", "ಹಸಿರು", "प्रकृति", "हरियाली"],
    "Adventure": ["adventure", "trek", "trekking", "rafting", "hike", "hiking", "climbing", "kayaking", "thrill", "ಸಾಹಸ", "ಚಾರಣ", "साहसिक", "ट्रेकिंग", "एडवेंचर"],
    "Heritage": ["heritage", "history", "historical", "monument", "monuments", "fort", "palace", "ruins", "architecture", "unesco", "ಪರಂಪರೆ", "ಐತಿಹಾಸಿಕ", "ಕೋಟೆ", "ಅರಮನೆ", "विरासत", "ऐतिहासिक", "किला", "महल"],
    "Relaxation": ["relax", "relaxation", "peaceful", "calm", "quiet", "honeymoon", "chill", "leisure", "ವಿಶ್ರಾಂತಿ", "ಶಾಂತ", "आराम", "शांत", "हनीमून"],
    "Spiritual": ["temple", "temples", "spiritual", "pilgrimage", "religious", "darshan", "monastery", "god", "ದೇವಾಲಯ", "ದೇವಸ್ಥಾನ", "ಯಾತ್ರೆ", "ಧಾರ್ಮಿಕ", "मंदिर", "तीर्थ", "धार्मिक", "आध्यात्मिक"],
    "Wildlife": ["wildlife", "safari", "tiger", "elephant", "elephants", "animals", "birds", "jungle", "national park", "ವನ್ಯಜೀವಿ", "ಸಫಾರಿ", "ಹುಲಿ", "ಆನೆ", "वन्यजीव", "सफारी", "सफ़ारी", "बाघ", "हाथी"],
    "Beaches": ["beach", "beaches", "sea", "coast", "coastal", "island", "ಕಡಲತೀರ", "ಬೀಚ್", "ಸಮುದ್ರ", "समुद्र", "बीच", "तट"],
    "Waterfalls": ["waterfall", "waterfalls", "falls", "ಜಲಪಾತ", "झरना", "झरने", "जलप्रपात"],
    "Hill Stations": ["hill station", "hill stations", "hills", "mountain", "mountains", "ಗಿರಿಧಾಮ", "ಬೆಟ್ಟ", "हिल स्टेशन", "पहाड़"],
}

# Categories in the database that correspond to an interest
INTEREST_TO_CATEGORY = {
    "Heritage": ["Heritage"], "Spiritual": ["Temples"], "Hill Stations": ["Hill Stations"],
    "Waterfalls": ["Waterfalls"], "Beaches": ["Beaches"], "Wildlife": ["Wildlife"],
    "Adventure": ["Adventure"], "Nature": ["Hill Stations", "Waterfalls", "Gardens & Parks"],
    "Relaxation": ["Beaches", "Gardens & Parks", "Hill Stations"],
}

EXTRA_ALIASES = {
    "coorg": ["coorg", "kodagu", "madikeri", "mercara", "ಮಡಿಕೇರಿ", "कोडागु", "मडिकेरी"],
    "chikmagalur": ["chikmagalur", "chikkamagaluru", "chikmangalur", "ಚಿಕ್ಕಮಗಳೂರ", "चिकमंगलूर"],
    "mysore-palace": ["mysore", "mysuru", "amba vilas", "ಮೈಸೂರು", "मैसूर", "मैसूरु"],
    "gol-gumbaz": ["bijapur", "vijayapura", "ವಿಜಯಪುರ", "बीजापुर", "विजयपुरा"],
    "udupi-krishna-temple": ["udupi", "krishna matha", "krishna temple", "ಉಡುಪಿ", "उडुपी"],
    "gokarna": ["gokarna", "om beach", "kudle", "ಗೋಕರ್ಣ", "गोकर्ण"],
    "br-hills": ["br hills", "biligiri", "biligiriranga", "b r hills"],
    "st-marys-island": ["st marys", "st. mary", "st mary", "saint mary"],
    "bidar-fort": ["bidar"],
    "chitradurga-fort": ["chitradurga"],
    "jog-falls": ["jog", "ಜೋಗ", "जोग"],
    "talakaveri": ["talacauvery", "talakaveri", "talakaveri", "bhagamandala"],
    "namdroling-monastery": ["namdroling", "bylakuppe", "golden temple"],
    "lalbagh": ["lalbagh", "lal bagh", "ಲಾಲ್‌ಬಾಗ್", "लालबाग"],
    "kabini": ["kabini", "ಕಬಿನಿ"],
    "dandeli": ["dandeli"],
    "yana": ["yana"],
    "shivanasamudra": ["shivanasamudra", "gaganachukki", "bharachukki"],
    "belur": ["belur", "chennakeshava"],
    "halebidu": ["halebidu", "halebeedu", "hoysaleswara"],
    "shravanabelagola": ["shravanabelagola", "gommateshwara", "bahubali"],
    "kukke-subramanya": ["kukke", "subramanya"],
    "kollur-mookambika": ["kollur", "mookambika"],
    "bannerghatta": ["bannerghatta"],
    "bangalore-palace": ["bangalore palace", "bengaluru palace"],
    "dubare-elephant-camp": ["dubare"],
}

GENERIC_WORDS = {"falls", "beach", "national", "park", "temple", "fort", "hills", "island", "sri", "st", "the",
                 "wildlife", "sanctuary", "bird", "gardens", "garden", "camp", "rocks", "monastery", "palace",
                 "bangalore", "bengaluru", "botanical", "elephant"}

NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                "a": 1, "single": 1, "ಒಂದು": 1, "ಎರಡು": 2, "ಮೂರು": 3, "ನಾಲ್ಕು": 4, "ಐದು": 5,
                "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5}

COMMON_WORDS = STOPWORDS | {"places", "place", "travel", "trips", "visit", "weekend", "budget", "temple", "temples", "beach",
                            "beaches", "falls", "waterfalls", "hills", "palace", "people", "days", "nights", "family", "friends",
                            "suggest", "recommend", "itinerary", "story", "history", "about", "nearby", "best", "plan", "food"}

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]

_DIGIT_MAP = {ord(c): str(i) for i, c in enumerate("೦೧೨೩೪೫೬೭೮೯")}
_DIGIT_MAP.update({ord(c): str(i) for i, c in enumerate("०१२३४५६७८९")})

KN_VOWEL_SIGNS = set(chr(c) for c in range(0x0CBE, 0x0CCD)) | {"್"}
HI_VOWEL_SIGNS = set(chr(c) for c in range(0x093E, 0x094D)) | {"्"}


def _stem_indic(word):
    """Drop a trailing vowel sign so inflected forms (ಹಂಪಿಯ, ಕೊಡಗಿಗೆ) still match."""
    if len(word) >= 3 and (word[-1] in KN_VOWEL_SIGNS or word[-1] in HI_VOWEL_SIGNS):
        return word[:-1]
    return word


class QueryUnderstanding:
    """Gazetteer + regex based entity extractor (Query Understanding Module)."""

    def __init__(self, destinations, cities):
        self.destinations = {d["slug"]: d for d in destinations}
        self.cities = cities
        self.city_words = set()
        for c in cities:
            for a in c["aliases"]:
                self.city_words.add(normalize(a))
                self.city_words.add(_stem_indic(normalize(a)))
        self.alias_to_slug = {}
        for d in destinations:
            for alias in self._aliases_for(d):
                self.alias_to_slug.setdefault(alias, d["slug"])
        # Sort aliases longest first so "mysore palace" wins over "mysore"
        self.sorted_aliases = sorted(self.alias_to_slug, key=len, reverse=True)
        self.single_word_aliases = [a for a in self.alias_to_slug if " " not in a and a.isascii() and len(a) >= 4]
        self.city_aliases = []
        for c in cities:
            for a in c["aliases"]:
                self.city_aliases.append((normalize(a), c["name"]))
        self.city_aliases.sort(key=lambda x: len(x[0]), reverse=True)

    # ------------------------------------------------------------------
    def _aliases_for(self, d):
        aliases = set()
        name = normalize(d["name"])
        aliases.add(name)
        aliases.add(re.sub(r"\(.*?\)", "", name).strip())
        aliases.add(d["slug"].replace("-", " "))
        first = re.sub(r"[^a-z]", "", name.split()[0]) if name.split() else ""
        if len(first) >= 4 and first not in GENERIC_WORDS:
            aliases.add(first)
        for field in ("name_kn", "name_hi"):
            local = normalize(d.get(field) or "")
            if local:
                local = re.sub(r"\(.*?\)", "", local).strip()
                aliases.add(local)
                aliases.add(_stem_indic(local))
                first_local = local.split()[0]
                if len(first_local) >= 3:
                    aliases.add(_stem_indic(first_local))
        aliases = {a for a in aliases if a and len(a) >= 3 and a not in self.city_words}
        for extra in EXTRA_ALIASES.get(d["slug"], []):  # explicit aliases always win
            aliases.add(normalize(extra))
            if not extra.isascii():
                aliases.add(_stem_indic(normalize(extra)))
        return aliases

    @staticmethod
    def _contains(text, alias):
        if alias.isascii():
            return re.search(r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])", text) is not None
        return alias in text

    # ------------------------------------------------------------------
    def find_destinations(self, text):
        found, used = [], text
        for alias in self.sorted_aliases:
            if self._contains(used, alias):
                slug = self.alias_to_slug[alias]
                if slug not in found:
                    found.append(slug)
                used = used.replace(alias, " ")
        # fuzzy match for typos (English only), on words not already matched
        for tok in tokenize(used):
            if len(tok) >= 5 and tok.isascii() and tok not in self.city_words and tok not in COMMON_WORDS:
                match = difflib.get_close_matches(tok, self.single_word_aliases, n=1, cutoff=0.84)
                if match and self.alias_to_slug[match[0]] not in found:
                    found.append(self.alias_to_slug[match[0]])
        # order by position in the text
        def pos(slug):
            positions = [text.find(a) for a, s in self.alias_to_slug.items() if s == slug and text.find(a) >= 0]
            return min(positions) if positions else 10 ** 6
        return sorted(found, key=pos)

    def find_cities(self, text):
        """Return (start_city, mentioned_cities)."""
        start, mentioned = None, []
        for alias, city in self.city_aliases:
            if not (self._contains(text, alias) or (not alias.isascii() and _stem_indic(alias) in text)):
                continue
            if city not in mentioned:
                mentioned.append(city)
            if alias.isascii():
                if re.search(r"(from|frm|starting at|starting from|leaving)\s+" + re.escape(alias), text):
                    start = start or city
            else:
                stem = _stem_indic(alias)
                if re.search(re.escape(stem) + r"\S*(ನಿಂದ|ಇಂದ)", text) or re.search(re.escape(alias) + r"\s*से", text):
                    start = start or city
        return start, mentioned

    @staticmethod
    def find_days(text):
        m = re.search(r"(\d+)\s*-?\s*(?:day|days|din|dino|ದಿನ|दिन)", text)
        if m:
            return max(1, min(int(m.group(1)), 10))
        m = re.search(r"(\d+)\s*-?\s*(?:night|nights|ರಾತ್ರಿ|रात)", text)
        if m:
            return max(1, min(int(m.group(1)) + 1, 10))
        m = re.search(r"\b(one|two|three|four|five|six|seven|a|single)\s*-?\s*days?\b", text)
        if m:
            return NUMBER_WORDS[m.group(1)]
        for word, num in NUMBER_WORDS.items():
            if not word.isascii() and re.search(re.escape(word) + r"\s*(ದಿನ|दिन)", text):
                return num
        if re.search(r"weekend|ವಾರಾಂತ್ಯ|वीकेंड|सप्ताहांत", text):
            return 2
        if re.search(r"day trip|one day|same day|ಒಂದು ದಿನ|एक दिन", text):
            return 1
        return None

    @staticmethod
    def find_budget(text):
        t = text.replace(",", "")
        patterns = [
            r"(?:rs\.?|inr|rupees?|budget(?:\s+of)?|within|under|below|less than|upto|up to|max|ರೂ\.?|ರೂಪಾಯಿ|रुपये|रुपए|रु\.?|बजट)\s*(\d+(?:\.\d+)?)\s*(k|thousand|lakh|lakhs|ಸಾವಿರ|हज़ार|हजार|लाख)?",
            r"(\d+(?:\.\d+)?)\s*(k|thousand|lakh|lakhs|ಸಾವಿರ|हज़ार|हजार|लाख)?\s*(?:rs|rupees?|inr|ರೂ|ರೂಪಾಯಿ|रुपये|रुपए|रु)(?![a-z])",
            r"(\d+(?:\.\d+)?)\s*(k)\b",
        ]
        for p in patterns:
            m = re.search(p, t)
            if m:
                value = float(m.group(1))
                unit = (m.group(2) or "").lower()
                if unit in ("k", "thousand", "ಸಾವಿರ", "हज़ार", "हजार"):
                    value *= 1000
                elif unit in ("lakh", "lakhs", "लाख"):
                    value *= 100000
                if value >= 300:
                    return int(value)
        return None

    @staticmethod
    def find_travelers(text):
        m = re.search(r"(\d+)\s*(?:people|persons|person|adults|adult|travell?ers|friends|members|pax|of us|ಜನ|ಮಂದಿ|लोग|लोगों|व्यक्ति|सदस्य)", text)
        if m:
            return max(1, min(int(m.group(1)), 20))
        m = re.search(r"\b(two|three|four|five|six)\s+(?:people|persons|adults|friends)", text)
        if m:
            return NUMBER_WORDS[m.group(1)]
        if re.search(r"couple|honeymoon|wife|husband|partner|girlfriend|boyfriend|ದಂಪತಿ|जोड़ा|पत्नी|पति", text):
            return 2
        if re.search(r"\bsolo\b|alone|by myself|ಒಬ್ಬನೇ|ಒಬ್ಬಳೇ|अकेले|अकेला", text):
            return 1
        if re.search(r"family|ಕುಟುಂಬ|परिवार", text):
            return 4
        return None

    @staticmethod
    def find_interests(text):
        found = []
        for interest, words in INTEREST_KEYWORDS.items():
            for w in words:
                if (w.isascii() and re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", text)) or (not w.isascii() and w in text):
                    found.append(interest)
                    break
        return found

    @staticmethod
    def find_style(text):
        if re.search(r"luxury|premium|5 star|five star|resort|ಐಷಾರಾಮಿ|लक्ज़री|लग्जरी", text):
            return "luxury"
        if re.search(r"cheap|budget trip|low cost|backpack|economical|affordable|ಕಡಿಮೆ ಖರ್ಚು|सस्ता|कम बजट", text):
            return "budget"
        return None

    @staticmethod
    def find_month(text):
        for i, m in enumerate(MONTHS, start=1):
            if m == "may":
                if re.search(r"\b(in|during|month of) may\b", text):
                    return 5
                continue
            if re.search(r"\b(" + m + "|" + m[:3] + r")\b", text):
                return i
        return None

    # ------------------------------------------------------------------
    def understand(self, text):
        clean = normalize(text).translate(_DIGIT_MAP)
        destinations = self.find_destinations(clean)
        start, cities = self.find_cities(clean)
        # A city used as the starting point should not also be the destination
        city_slug = {"Mysuru": "mysore-palace", "Vijayapura": "gol-gumbaz", "Udupi": "udupi-krishna-temple"}
        if start and city_slug.get(start) in destinations:
            destinations.remove(city_slug[start])
        return {
            "language": detect_language(text),
            "tokens": tokenize(clean),
            "destination": destinations[0] if destinations else None,
            "destinations": destinations,
            "start_city": start,
            "cities": cities,
            "days": self.find_days(clean),
            "budget": self.find_budget(clean),
            "travelers": self.find_travelers(clean),
            "interests": self.find_interests(clean),
            "style": self.find_style(clean),
            "month": self.find_month(clean),
            "normalized": clean,
        }
