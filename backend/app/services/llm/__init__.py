"""
Single entry point for getting an LLM provider. Every place that needs to
talk to an LLM calls get_llm_provider() -- never imports OllamaProvider or
ClaudeProvider directly. That's what makes LLM_PROVIDER=claude in .env
enough to switch, with no code changes anywhere else.
"""

from app.config import settings
from app.services.llm.base import LLMProvider


def get_llm_provider() -> LLMProvider:
    if settings.llm_provider == "ollama":
        from app.services.llm.ollama_provider import OllamaProvider
        return OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model)

    if settings.llm_provider == "claude":
        if not settings.anthropic_api_key:
            raise ValueError("LLM_PROVIDER=claude requires ANTHROPIC_API_KEY to be set")
        from app.services.llm.claude_provider import ClaudeProvider
        return ClaudeProvider(api_key=settings.anthropic_api_key)

    raise ValueError(
        f"Unknown LLM_PROVIDER '{settings.llm_provider}'. "
        "Supported: 'ollama', 'claude' (openai/gemini not implemented yet)."
    )