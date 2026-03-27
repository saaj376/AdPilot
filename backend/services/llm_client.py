import httpx
from crewai import LLM
from config import settings

def get_llm() -> LLM:
    """
    Returns a CrewAI LLM instance pointed at the local Ollama gemma3:4b model.
    Call this once per agent definition — CrewAI handles the rest.
    """
    return LLM(
        model=f"ollama/{settings.OLLAMA_MODEL}",
        base_url=settings.OLLAMA_BASE_URL,
        timeout=120,
    )

async def check_ollama_health() -> None:
    """
    Called by main.py startup — confirms Ollama is running and
    gemma3:4b is available before the server accepts any requests.
    Raises a clear RuntimeError if anything is wrong.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
    except httpx.ConnectError:
        raise RuntimeError(
            f"Ollama is not running. Start it with: ollama serve"
        )
    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"Ollama returned an unexpected response: {e.response.status_code}"
        )
    # Confirm the model is actually downloaded
    models = response.json().get("models", [])
    model_names = [m.get("name", "") for m in models]
 
    # Ollama model names can be "gemma3:4b" or "gemma3:4b-..."
    model_found = any(
        settings.OLLAMA_MODEL in name for name in model_names
    )
 
    if not model_found:
        raise RuntimeError(
            f"Model '{settings.OLLAMA_MODEL}' not found in Ollama. "
            f"Pull it with: ollama pull {settings.OLLAMA_MODEL}\n"
            f"Available models: {', '.join(model_names) or 'none'}"
        )
 
    print(f"Ollama healthy — model '{settings.OLLAMA_MODEL}' is ready.")