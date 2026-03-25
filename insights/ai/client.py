import frappe
from openai import OpenAI


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

    def generate_query(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_tokens=4096,
        )
        return response.choices[0].message.content
