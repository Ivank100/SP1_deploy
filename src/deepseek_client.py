# src/deepseek_client.py
import requests
from typing import List
from .config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

class DeepSeekClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.base_url = base_url or DEEPSEEK_BASE_URL
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
        url = f"{self.base_url}/v1/embeddings"   # adjust to real path
        payload = {"model": model, "input": texts}
        resp = self.session.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return [item["embedding"] for item in data["data"]]

       # ---- chat / LLM ----
    def chat(self, messages, model: str = "openrouter/auto", temperature: float = 0.2) -> str:
        # OpenRouter is OpenAI-compatible: /chat/completions
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,        # you can swap to any OpenRouter model id
            "messages": messages,
            "temperature": temperature,
        }
        resp = self.session.post(url, json=payload)

        if not resp.ok:
            # nicer error message than bare raise_for_status()
            raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text}")

        data = resp.json()
        return data["choices"][0]["message"]["content"]
