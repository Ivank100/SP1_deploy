# src/deepseek_client.py
import requests
from typing import List
from .config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, LLM_CHAT_MODEL

class DeepSeekClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.base_url = base_url or DEEPSEEK_BASE_URL
        
        if not self.api_key:
            raise ValueError(
                "DEEPSEEK_API_KEY is not set. Please set it in your .env file or environment.\n"
                "Example: DEEPSEEK_API_KEY=your_api_key_here"
            )
        if not self.base_url:
            raise ValueError(
                "DEEPSEEK_BASE_URL is not set. Please set it in your .env file or environment.\n"
                "Example: DEEPSEEK_BASE_URL=https://openrouter.ai/api/v1"
            )
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # OpenRouter-specific but simple values are fine
            "HTTP-Referer": "http://localhost",    # your app/site URL if you have one
            "X-Title": "notebooklm-clone",         # app name
        })


    # ---- embeddings ----
    def embed(self, texts: List[str], model: str = "deepseek-embed") -> List[list[float]]:
        # base_url already includes /v1 (e.g. https://api.openai.com/v1)
        url = f"{self.base_url.rstrip('/')}/embeddings"
        payload = {"model": model, "input": texts}
        resp = self.session.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]

       # ---- chat / LLM ----
    def chat(
        self,
        messages,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 303,
    ) -> str:
        # OpenAI-compatible: /chat/completions (OpenRouter, OpenAI, etc.)
        model = model or LLM_CHAT_MODEL
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = self.session.post(url, json=payload)

        if not resp.ok:
            raise RuntimeError(f"LLM API error {resp.status_code}: {resp.text}")

        data = resp.json()
        return data["choices"][0]["message"]["content"]
