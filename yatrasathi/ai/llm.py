"""
Optional Large Language Model client (OpenAI-compatible Chat Completions API).

If OPENAI_API_KEY is set, informational answers are written by the LLM using
ONLY the passages retrieved by the RAG module (grounded generation). If the
key is missing or the call fails, YatraSathi silently falls back to its
built-in template generator, so the project always works offline.
"""
import logging

import requests

log = logging.getLogger(__name__)

LANGUAGE_NAMES = {"en": "English", "kn": "Kannada (ಕನ್ನಡ script)", "hi": "Hindi (देवनागरी script)"}

SYSTEM_PROMPT = (
    "You are YatraSathi, a friendly, context-aware AI travel assistant for Karnataka tourism. "
    "Answer the traveller's question using ONLY the facts in the provided context. If the context does not contain "
    "the answer, say you are not sure and suggest what you can help with. Keep answers under 170 words, use short "
    "paragraphs or '- ' bullet points, use **bold** for key facts, and use Indian Rupees (₹). "
    "When asked for a story or history, narrate it in an engaging storytelling style. "
    "Always reply in {language}."
)


class LLMClient:
    def __init__(self, api_key, model="gpt-4o-mini", base_url="https://api.openai.com/v1", timeout=25):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.enabled = bool(api_key)

    def answer(self, question, passages, lang="en", history=None, facts=None):
        if not self.enabled:
            return None
        context = "\n\n".join(f"[{i + 1}] {p['title']}: {p['text']}" for i, p in enumerate(passages))
        if facts:
            context = facts + "\n\n" + context
        messages = [{"role": "system", "content": SYSTEM_PROMPT.format(language=LANGUAGE_NAMES.get(lang, "English"))}]
        for turn in (history or [])[-6:]:
            messages.append({"role": "user" if turn["role"] == "user" else "assistant", "content": turn["content"][:800]})
        messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"})
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "messages": messages, "temperature": 0.4, "max_tokens": 450},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # network error, bad key, quota ...
            log.warning("LLM call failed, using offline generator: %s", exc)
            return None
