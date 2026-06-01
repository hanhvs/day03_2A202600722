"""Factory: build LLM provider from environment (@hanhvs H7)."""
import os
from typing import Optional

from dotenv import load_dotenv

from src.core.llm_provider import LLMProvider
from src.core.openai_provider import OpenAIProvider


def get_llm_from_env(env_path: Optional[str] = None) -> LLMProvider:
    load_dotenv(env_path)

    provider = os.getenv("DEFAULT_PROVIDER", "openai").lower().strip()
    model = os.getenv("DEFAULT_MODEL", "gpt-4o")

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when DEFAULT_PROVIDER=openai")
        return OpenAIProvider(model_name=model, api_key=api_key)

    if provider in ("google", "gemini"):
        from src.core.gemini_provider import GeminiProvider

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required when DEFAULT_PROVIDER=google")
        return GeminiProvider(model_name=model or "gemini-1.5-flash", api_key=api_key)

    if provider == "local":
        from src.core.local_provider import LocalProvider

        path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        return LocalProvider(model_path=path)

    raise ValueError(f"Unknown DEFAULT_PROVIDER: {provider}. Use openai | google | local")
