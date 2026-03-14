import os

def make_railtracks_llm():
    provider = os.getenv("LLM_PROVIDER", "gemini")
    
    if provider == "gemini":
        from railtracks.providers.gemini import GeminiProvider
        return GeminiProvider(api_key=os.getenv("GEMINI_API_KEY"))
    elif provider == "openai":
        from railtracks.providers.openai import OpenAIProvider
        return OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))
    elif provider == "anthropic":
        from railtracks.providers.anthropic import AnthropicProvider
        return AnthropicProvider(api_key=os.getenv("ANTHROPIC_API_KEY"))
    elif provider == "portkey":
        from railtracks.providers.portkey import PortkeyProvider
        return PortkeyProvider(api_key=os.getenv("PORTKEY_API_KEY"), virtual_key=os.getenv("PORTKEY_VIRTUAL_KEY"))
    elif provider == "ollama":
        from railtracks.providers.ollama import OllamaProvider
        return OllamaProvider(base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
