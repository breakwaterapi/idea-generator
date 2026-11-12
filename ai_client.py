import json
import logging
import os
from typing import Any, Dict, List

from mistralai.client import Mistral

logger = logging.getLogger(__name__)

FALLBACK_MODELS = [
    "mistral-small-latest",
    "open-mistral-nemo",
    "ministral-8b-latest",
    "open-mistral-7b",
]


def is_tier_restriction_error(exc: Exception) -> bool:
    """Check if exception is caused by subscription tier restrictions."""
    msg = str(exc).lower()
    if "tier_not_allowed" in msg or "1910" in msg or "subscription tier" in msg:
        return True
    if hasattr(exc, "status_code") and getattr(exc, "status_code") == 403:
        return True
    return False


class MistralClient:
    """Wrapper around the Mistral API for idea generation."""

    def __init__(self, api_key: str = None, model_name: str | None = None):
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY must be set in the environment or passed to the constructor.")

        self.client = Mistral(api_key=self.api_key)
        self.model_id = model_name or os.getenv("MISTRAL_MODEL", "mistral-small-latest")
        self.last_used_model = self.model_id
        self.fallback_triggered = False

    @staticmethod
    def _strip_code_fences(payload: str) -> str:
        cleaned = payload.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0]
        return cleaned.strip()

    @staticmethod
    def _normalize_ideas(payload) -> List[Dict[str, Any]]:
        if isinstance(payload, dict):
            items = payload.get("ideas")
            if not isinstance(items, list):
                items = [payload]
        elif isinstance(payload, list):
            items = payload
        else:
            raise ValueError("Unexpected response structure from Mistral.")

        normalized = []
        for item in items:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "project-title": item.get("project-title") or item.get("title") or "Untitled Project",
                    "tech-stack": item.get("tech-stack") or item.get("stack") or "Not specified",
                    "description": item.get("description") or item.get("summary") or "No description provided.",
                    "target-users": item.get("target-users") or item.get("users") or "Not specified",
                    "first-milestone": (
                        item.get("first-milestone")
                        or item.get("first_step")
                        or "Define a narrow MVP and build the first working workflow."
                    ),
                    "references": item.get("references", []),
                }
            )

        return normalized

    @staticmethod
    def _prepare_context(context: str, max_chars: int = 18000) -> str:
        cleaned = context.strip()
        if len(cleaned) <= max_chars:
            return cleaned
        return cleaned[:max_chars] + "\n\n[Context truncated for length.]"

    def _call_completion(self, model: str, prompt: str):
        return self.client.chat.complete(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )

    def generate_project_ideas(
        self,
        context: str,
        idea_count: int = 5,
        focus_area: str | None = None,
    ) -> List[Dict[str, Any]]:
        """Generate structured project ideas from the provided context with automatic tier fallback."""
        prepared_context = self._prepare_context(context)
        focus_clause = f"Focus especially on {focus_area}." if focus_area else "Keep the ideas broad and commercially realistic."

        prompt = f"""
        You are an expert software architect and product strategist.
        Analyze the source text and propose exactly {idea_count} distinct technical project ideas.

        Constraints:
        - Prefer practical, buildable ideas over vague concepts.
        - Each idea should be clearly different from the others.
        - Use beginner-friendly language and explain technical concepts simply.
        - Include 2-3 specific learning references or tutorials for each idea.
        - {focus_clause}

        Return valid JSON in this exact shape:
        {{
          "ideas": [
            {{
              "project-title": "Concise project name",
              "tech-stack": "Recommended stack",
              "description": "Short beginner-friendly description explaining the product and why it matters",
              "target-users": "Primary users or buyers",
              "first-milestone": "A concrete first implementation milestone",
              "references": [
                {{
                  "title": "Topic or tutorial name",
                  "url": "https://example.com/reference"
                }}
              ]
            }}
          ]
        }}

        Context:
        {prepared_context}
        """

        models_to_try = [self.model_id] + [m for m in FALLBACK_MODELS if m != self.model_id]
        last_tier_error = None

        for idx, model_to_attempt in enumerate(models_to_try):
            try:
                response = self._call_completion(model=model_to_attempt, prompt=prompt)
                content = response.choices[0].message.content
                if not isinstance(content, str):
                    content = str(content)

                parsed = json.loads(self._strip_code_fences(content))
                ideas = self._normalize_ideas(parsed)
                self.last_used_model = model_to_attempt
                self.fallback_triggered = (idx > 0)
                if self.fallback_triggered:
                    logger.warning(
                        "Successfully generated ideas using fallback model '%s' after '%s' was restricted.",
                        model_to_attempt,
                        self.model_id,
                    )
                return ideas[:idea_count]

            except Exception as exc:
                if is_tier_restriction_error(exc):
                    last_tier_error = exc
                    logger.warning(
                        "Model '%s' is not available in subscription tier (%s). Trying fallback...",
                        model_to_attempt,
                        exc,
                    )
                    continue
                logger.error("Error calling Mistral API with model '%s': %s", model_to_attempt, exc)
                raise

        raise ValueError(
            f"Mistral model '{self.model_id}' is not available in your subscription tier. "
            f"Attempted fallbacks ({FALLBACK_MODELS}) but all were restricted. "
            f"Original error: {last_tier_error}"
        )
