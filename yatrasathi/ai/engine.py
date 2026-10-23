"""
Builds the AI engine (NLP + intent model + RAG index + recommender + planner)
from the database and keeps one shared instance for the whole app.
Call `refresh_engine()` after the admin changes destinations or the knowledge base.
"""
import json
import threading

from flask import current_app

_engine = None
_lock = threading.Lock()


def _load_json(name):
    with open(current_app.config["DATA_DIR"] / name, encoding="utf-8") as f:
        return json.load(f)


def build_engine():
    from ..models import Destination, KnowledgeDoc
    from .chatbot import ChatEngine

    destinations = [d.to_dict(full=True) for d in Destination.query.filter_by(active=True).order_by(Destination.id).all()]
    admin_docs = [{"id": k.id, "title": k.title, "content": k.content, "category": k.category}
                  for k in KnowledgeDoc.query.filter_by(active=True, source="admin").all()]
    cfg = current_app.config
    return ChatEngine(
        destinations=destinations,
        cities=_load_json("cities.json"),
        guide=_load_json("knowledge_base.json"),
        intents_path=cfg["DATA_DIR"] / "intents.json",
        admin_docs=admin_docs,
        llm_config={"api_key": cfg.get("OPENAI_API_KEY"), "model": cfg.get("OPENAI_MODEL"), "base_url": cfg.get("OPENAI_BASE_URL")},
    )


def get_engine():
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = build_engine()
    return _engine


def refresh_engine():
    global _engine
    with _lock:
        _engine = build_engine()
    return _engine
