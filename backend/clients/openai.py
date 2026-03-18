"""This file creates the OpenAI-compatible client used by backend AI features.
Services import it so chat, embeddings, and generation use one shared configuration."""


# src/openai_client.py
import requests
from typing import List

from ..core.config import OPENAI_API_KEY, OPENAI_BASE_URL, LLM_CHAT_MODEL


class OpenAIClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or OPENAI_API_KEY
        self.base_url = base_url or OPENAI_BASE_URL

        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Please set it in your .env file or environment.\n"
                "Example: OPENAI_API_KEY=your_api_key_here"
            )
        if not self.base_url:
            raise ValueError(
                "OPENAI_BASE_URL is not set. Please set it in your .env file or environment.\n"
                "Example: OPENAI_BASE_URL=https://api.openai.com/v1"
            )

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

    def embed(self, texts: List[str], model: str = "text-embedding-3-small") -> List[list[float]]:
        url = f"{self.base_url.rstrip('/')}/embeddings"
        payload = {"model": model, "input": texts}
        resp = self.session.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]

    def chat(
        self,
        messages,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 500,
    ) -> str:
        model = model or LLM_CHAT_MODEL
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = self.session.post(url, json=payload, timeout=120)

        if not resp.ok:
            raise RuntimeError(f"LLM API error {resp.status_code}: {resp.text}")

        data = resp.json()
        return data["choices"][0]["message"]["content"]
