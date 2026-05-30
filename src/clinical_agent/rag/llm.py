"""LLM backend. Offline deterministic stub, or OpenAI / Anthropic.

The stub composes a grounded answer purely from the supplied context, so the
whole pipeline (and its faithfulness/citation metrics) works with no API key.
Every backend implements the same two methods:

  generate(*, system, user, context) -> str   grounded answer over CONTEXT lines
  chat(*, system, user) -> str                 free-form completion (MCQ gen, judging)
"""
from __future__ import annotations

from clinical_agent.config import get_settings


class StubLLM:
    """Deterministic, extractive 'LLM' — every sentence is drawn from context,
    guaranteeing high groundedness for demos and tests."""

    name = "stub"

    def generate(self, *, system: str, user: str, context: list[str]) -> str:
        if not context:
            return ("I don't have sufficient grounded evidence to answer. "
                    "Please consult primary clinical sources.")
        lead = context[0]
        extra = context[1] if len(context) > 1 else ""
        ans = f"Based on the available evidence: {lead}"
        if extra:
            ans += f" Additionally, {extra}"
        ans += " Verify against the cited sources before acting."
        return ans

    def chat(self, *, system: str, user: str) -> str:
        # Deterministic stub: the real MCQ/judge paths only call chat() on a live
        # backend; this keeps offline callers from crashing.
        return user.strip()[:200]


class OpenAILLM:
    name = "openai"

    def __init__(self, model: str, temperature: float, api_key: str, max_tokens: int = 1024):
        from openai import OpenAI  # lazy
        self._client = OpenAI(api_key=api_key)
        self._model, self._temp, self._max = model, temperature, max_tokens

    def _complete(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model, temperature=self._temp, max_tokens=self._max,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content or ""

    def generate(self, *, system: str, user: str, context: list[str]) -> str:
        ctx = "\n".join(f"- {c}" for c in context)
        return self._complete(system, f"CONTEXT:\n{ctx}\n\nQUESTION: {user}")

    def chat(self, *, system: str, user: str) -> str:
        return self._complete(system, user)


class AnthropicLLM:
    name = "anthropic"

    def __init__(self, model: str, temperature: float, api_key: str, max_tokens: int = 1024):
        import anthropic  # lazy
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model, self._temp, self._max = model, temperature, max_tokens

    def _complete(self, system: str, user: str) -> str:
        msg = self._client.messages.create(
            model=self._model, temperature=self._temp, max_tokens=self._max,
            system=system, messages=[{"role": "user", "content": user}],
        )
        # content is a list of blocks; concatenate the text blocks
        return "".join(getattr(b, "text", "") for b in msg.content)

    def generate(self, *, system: str, user: str, context: list[str]) -> str:
        ctx = "\n".join(f"- {c}" for c in context)
        return self._complete(system, f"CONTEXT:\n{ctx}\n\nQUESTION: {user}")

    def chat(self, *, system: str, user: str) -> str:
        return self._complete(system, user)


def get_llm():
    s = get_settings()
    if s.llm_provider == "openai" and s.openai_api_key:
        return OpenAILLM(s.llm_model, s.llm_temperature, s.openai_api_key, s.llm_max_tokens)
    if s.llm_provider == "anthropic" and s.anthropic_api_key:
        return AnthropicLLM(s.anthropic_model, s.llm_temperature, s.anthropic_api_key,
                            s.llm_max_tokens)
    return StubLLM()
