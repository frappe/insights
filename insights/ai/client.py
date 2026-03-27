import json

import frappe
from openai import OpenAI

from insights.ai.debug import log


class AIClient:
    PROVIDER_BASE_URLS = {
        "OpenRouter": "https://openrouter.ai/api/v1",
    }

    def __init__(self):
        settings = frappe.get_single("Insights Settings")
        if not settings.enable_ai:
            frappe.throw("AI features are not enabled. Please enable them in Insights Settings.")

        self.api_key = settings.get_password("ai_api_key")
        self.model = settings.ai_model
        self.provider = settings.ai_provider

        if self.provider == "OpenRouter":
            base_url = self.PROVIDER_BASE_URLS["OpenRouter"]
            self.client = OpenAI(api_key=self.api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=self.api_key)

    def complete(self, messages: list[dict]) -> list[dict]:
        """
        Send messages to the model and return a list of raw operation dicts.

        Uses json_object response format — the model is instructed via the system
        prompt to return {"operations": [...]}. We parse and validate the JSON
        ourselves with Pydantic in the validator, which avoids OpenAI's grammar
        size limits that apply to structured output mode.

        Args:
            messages: List of {"role": ..., "content": ...} dicts.

        Returns:
            List of raw operation dicts (unvalidated — caller validates).

        Raises:
            ValueError: If the response is not valid JSON or missing the
                        expected {"operations": [...]} structure.
        """
        log("client", "model={} provider={} messages={}", self.model, self.provider, len(messages))

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        log("client", "raw response ({} chars):\n{}", len(raw), raw)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            log("client", "JSON parse error: {}", e)
            raise ValueError(f"Model returned invalid JSON: {e}") from e

        if not isinstance(data, dict) or "operations" not in data:
            log("client", "missing 'operations' key, got keys: {}", list(data.keys()) if isinstance(data, dict) else type(data).__name__)
            raise ValueError(f'Expected {{"operations": [...]}}, got: {raw[:200]}')

        operations = data["operations"]
        if not isinstance(operations, list):
            log("client", "'operations' is not a list: {}", type(operations).__name__)
            raise ValueError(f"Expected 'operations' to be a list, got: {type(operations).__name__}")

        log("client", "returning {} operations", len(operations))
        return operations
