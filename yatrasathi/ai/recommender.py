"""
Recommendation Engine.

Hybrid, content-based recommender:
  * Content similarity  - TF-IDF vectors of each place (category, tags,
    description, attractions) compared with the user's interests.
  * Popularity & rating - higher rated / reviewed places rank higher.
  * Geographic filtering - closer places score higher (location intelligence).
  * Seasonality         - places in their best season for the travel month.
  * Personalisation     - similarity to places the user has saved.
Budget filtering / cost estimation is done together with the TripPlanner.
"""
import math

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .geo import haversine_km
from .nlp import INTEREST_TO_CATEGORY
from .text import preprocess

INTEREST_QUERIES = {
    "Nature": "nature hill station waterfall forest coffee plantation green misty scenic trekking garden",
    "Adventure": "adventure trekking rafting kayaking safari climbing hiking jeep ride",
    "Heritage": "heritage history temple fort palace ruins unesco architecture sculpture monument",
    "Relaxation": "relaxation beach homestay peaceful garden lake backwaters sunset",
    "Spiritual": "temple pilgrimage spiritual monastery krishna shiva jain",
    "Wildlife": "wildlife safari tiger elephant birds national park sanctuary",
    "Beaches": "beach coastal island sea water sports",
    "Waterfalls": "waterfall falls monsoon",
    "Hill Stations": "hill station misty coffee peak viewpoint",
}


def in_season(month, start, end):
    if not month:
        return True
    if start <= end:
        return start <= month <= end
    return month >= start or month <= end


class Recommender:
    def __init__(self, destinations):
        self.destinations = destinations
        self.index = {d["slug"]: i for i, d in enumerate(destinations)}
        docs = [" ".join([d["category"], d["category"], " ".join(d.get("tags", [])) * 2, d.get("description", ""),
                          " ".join(d.get("attractions", []))]) for d in destinations]
        self.vectorizer = TfidfVectorizer(tokenizer=preprocess, lowercase=False, token_pattern=None, sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform(docs)
        reviews = np.array([max(d.get("reviews", 0), 1) for d in destinations], dtype=float)
        self.popularity = np.log1p(reviews) / np.log1p(reviews).max()
        self.rating = np.clip((np.array([d.get("rating", 4.0) for d in destinations]) - 3.5) / 1.5, 0, 1)

    # ------------------------------------------------------------------
    def score_all(self, interests=None, query_text="", origin=None, month=None, personal_slugs=None):
        """Return an array of scores (0..1) and per-place reasons."""
        n = len(self.destinations)
        content = np.zeros(n)
        terms = " ".join(INTEREST_QUERIES.get(i, i) for i in (interests or []))
        if query_text:
            terms += " " + query_text
        if terms.strip():
            q = self.vectorizer.transform([terms])
            content = cosine_similarity(q, self.matrix).ravel()
            if content.max() > 0:
                content = content / content.max()
            # category match bonus
            cats = {c for i in (interests or []) for c in INTEREST_TO_CATEGORY.get(i, [])}
            for idx, d in enumerate(self.destinations):
                if d["category"] in cats:
                    content[idx] = min(1.0, content[idx] + 0.35)
        else:
            content = np.full(n, 0.5)

        distance = np.full(n, 0.5)
        dist_km = np.zeros(n)
        if origin:
            for idx, d in enumerate(self.destinations):
                dist_km[idx] = haversine_km(origin[0], origin[1], d["lat"], d["lng"])
            distance = np.clip(1 - dist_km / 550.0, 0, 1)

        season = np.array([1.0 if in_season(month, d["best_from"], d["best_to"]) else 0.3 for d in self.destinations])

        personal = np.zeros(n)
        if personal_slugs:
            rows = [self.index[s] for s in personal_slugs if s in self.index]
            if rows:
                profile = np.asarray(self.matrix[rows].mean(axis=0))
                personal = cosine_similarity(profile, self.matrix).ravel()
                for r in rows:
                    personal[r] = 0  # don't recommend what is already saved

        scores = (0.40 * content + 0.18 * self.rating + 0.10 * self.popularity + 0.17 * distance
                  + 0.08 * season + 0.07 * personal)
        return scores, dist_km

    def recommend(self, interests=None, query_text="", origin=None, month=None, limit=6,
                  exclude=None, categories=None, personal_slugs=None, max_km=None):
        scores, dist_km = self.score_all(interests, query_text, origin, month, personal_slugs)
        results = []
        for idx in np.argsort(-scores):
            d = self.destinations[idx]
            if exclude and d["slug"] in exclude:
                continue
            if categories and d["category"] not in categories:
                continue
            if max_km and origin and dist_km[idx] > max_km:
                continue
            results.append({"slug": d["slug"], "score": round(float(scores[idx]), 3),
                            "distance_km": round(float(dist_km[idx]) * 1.3) if origin else None})
            if len(results) >= limit:
                break
        return results

    def similar(self, slug, limit=4):
        if slug not in self.index:
            return []
        i = self.index[slug]
        sims = cosine_similarity(self.matrix[i], self.matrix).ravel()
        base = self.destinations[i]
        for j, d in enumerate(self.destinations):
            km = haversine_km(base["lat"], base["lng"], d["lat"], d["lng"])
            sims[j] = 0.75 * sims[j] + 0.25 * math.exp(-km / 150)
        sims[i] = -1
        return [self.destinations[j]["slug"] for j in np.argsort(-sims)[:limit]]

    def nearby(self, lat, lng, limit=8, radius_km=None, exclude=None, categories=None):
        rows = []
        for d in self.destinations:
            if exclude and d["slug"] in exclude:
                continue
            if categories and d["category"] not in categories:
                continue
            km = haversine_km(lat, lng, d["lat"], d["lng"])
            if radius_km and km > radius_km:
                continue
            rows.append((km, d["slug"]))
        rows.sort()
        return [{"slug": s, "distance_km": round(km, 1)} for km, s in rows[:limit]]
