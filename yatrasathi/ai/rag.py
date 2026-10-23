"""
RAG Retrieval System.

Builds a searchable knowledge index from:
  * the travel database (destination overview, history, attractions,
    travel info and food for every place),
  * the Travel Guide knowledge base (festivals, cuisine, transport ...),
  * documents added by the admin in the "AI Knowledge Base" screen.

Retrieval = hybrid TF-IDF semantic search (stemmed word n-grams + character
n-grams) + context matching boosts (detected destination, intent section).
The top passages are handed to the AI Response Generation module.
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from .text import preprocess

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August",
               "September", "October", "November", "December"]

# which document section answers which intent best
INTENT_SECTIONS = {
    "story": ["history"], "place_info": ["overview", "summary"], "attractions": ["attractions"],
    "food": ["food", "cuisine"], "how_to_reach": ["travel"], "timings_fee": ["travel"],
    "best_time": ["travel", "weather"], "festival": ["festivals"], "safety": ["safety"],
    "weather": ["weather"], "transport": ["transportation"], "budget": ["travel"],
}


def month_range(start, end):
    return f"{MONTH_NAMES[start - 1]} to {MONTH_NAMES[end - 1]}" if start != end else MONTH_NAMES[start - 1]


def _chunks(text, size=600):
    parts, current = [], ""
    for para in [p.strip() for p in text.split("\n") if p.strip()]:
        if len(current) + len(para) > size and current:
            parts.append(current)
            current = ""
        current = (current + "\n" + para).strip()
    if current:
        parts.append(current)
    return parts or [text]


class KnowledgeIndex:
    def __init__(self, destinations, guide_sections=None, admin_docs=None):
        self.docs = []
        for d in destinations:
            self._add_destination(d)
        for sec in guide_sections or []:
            for item in sec.get("content", []):
                self.docs.append({
                    "id": f"guide:{sec['slug']}:{item['heading']}", "title": f"{sec['title']} - {item['heading']}",
                    "text": item["text"], "slug": None, "section": sec["slug"], "source": "Travel Guide",
                })
        for doc in admin_docs or []:
            for i, chunk in enumerate(_chunks(doc["content"])):
                self.docs.append({
                    "id": f"kb:{doc['id']}:{i}", "title": doc["title"], "text": chunk, "slug": doc.get("slug"),
                    "section": (doc.get("category") or "general").lower(), "source": "Knowledge Base",
                })
        self._fit()

    def _add_destination(self, d):
        name = d["name"]
        add = lambda section, title, text: self.docs.append({
            "id": f"dest:{d['slug']}:{section}", "title": title, "text": text, "slug": d["slug"],
            "section": section, "source": "Travel Database"})
        add("overview", f"{name} - Overview",
            f"{name} is a {d['category'].lower()} destination in {d['district']} district, Karnataka. {d['description']} "
            f"Known for: {', '.join(d.get('tags', []))}.")
        if d.get("history"):
            add("history", f"{name} - History & Story", d["history"])
        if d.get("attractions"):
            add("attractions", f"{name} - Top Attractions", f"Top attractions in {name}: " + "; ".join(d["attractions"]) + ".")
        fee = (f"Entry fee is about Rs {d['entry_fee_indian']} for Indians and Rs {d['entry_fee_foreign']} for foreigners."
               if d.get("entry_fee_indian") else "There is no entry fee.")
        add("travel", f"{name} - Travel Information",
            f"Best time to visit {name}: {month_range(d['best_from'], d['best_to'])}. Timings: {d.get('timings')}. {fee} "
            f"How to reach: {d.get('how_to_reach', '')} Tips: {d.get('tips', '')}")
        if d.get("food"):
            add("food", f"{name} - Food to Try", f"Food to try in and around {name}: " + ", ".join(d["food"]) + ".")
        for lang in ("kn", "hi"):
            if d.get(f"summary_{lang}"):
                local_name = d.get(f"name_{lang}") or name
                add(f"summary", f"{local_name}", f"{local_name}: {d[f'summary_{lang}']}")
                self.docs[-1]["id"] += f":{lang}"

    def _fit(self):
        texts = [doc["title"] + ". " + doc["text"] for doc in self.docs]
        self.word_vec = TfidfVectorizer(tokenizer=preprocess, lowercase=False, token_pattern=None,
                                        ngram_range=(1, 2), sublinear_tf=True)
        self.char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, max_features=60000)
        self.word_matrix = self.word_vec.fit_transform(texts)
        self.char_matrix = self.char_vec.fit_transform(texts)

    @property
    def size(self):
        return len(self.docs)

    def search(self, query, k=4, slug=None, intent=None, min_score=0.0):
        """Return the top-k passages as dicts with a relevance score."""
        if not self.docs:
            return []
        w = linear_kernel(self.word_vec.transform([query]), self.word_matrix).ravel()
        c = linear_kernel(self.char_vec.transform([query]), self.char_matrix).ravel()
        scores = 0.6 * w + 0.4 * c
        wanted_sections = INTENT_SECTIONS.get(intent, [])
        for i, doc in enumerate(self.docs):
            if slug and doc["slug"] == slug:
                scores[i] += 0.35
            elif slug and doc["slug"] and doc["slug"] != slug:
                scores[i] -= 0.05
            if doc["section"] in wanted_sections:
                scores[i] += 0.3
        order = np.argsort(-scores)[:k]
        results = []
        for i in order:
            if scores[i] <= min_score:
                continue
            doc = dict(self.docs[i])
            doc["score"] = round(float(scores[i]), 3)
            results.append(doc)
        return results
