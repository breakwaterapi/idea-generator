import json
import logging
import os
from typing import Dict, List

from mistralai import Mistral

logger = logging.getLogger(__name__)


class MistralClient:
    """Wrapper around the Mistral API for idea generation."""

    def __init__(self, api_key: str = None, model_name: str = "mistral-large-latest"):
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY must be set in the environment or passed to the constructor.")

        self.client = Mistral(api_key=self.api_key)
        self.model_id = model_name

    @staticmethod
    def _strip_code_fences(payload: str) -> str:
        cleaned = payload.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            cleaned = cleaned.rsplit("```", 1)[0]
        return cleaned.strip()

    @staticmethod
    def _normalize_ideas(payload) -> List[Dict[str, str]]:
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

    def generate_project_ideas(
        self,
        context: str,
        idea_count: int = 5,
        focus_area: str | None = None,
    ) -> List[Dict[str, str]]:
        """Generate structured project ideas from the provided context."""
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

        try:
            response = self.client.chat.complete(
                model=self.model_id,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not isinstance(content, str):
                content = str(content)

            parsed = json.loads(self._strip_code_fences(content))
            ideas = self._normalize_ideas(parsed)
            return ideas[:idea_count]
        except Exception as exc:
            logger.error("Error calling Mistral API: %s", exc)
            raise
