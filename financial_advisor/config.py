"""Central configuration: environment loading + a model-agnostic LLM factory."""
import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()

# API keys 
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")

# Model IDs
WORKHORSE_MODEL = os.getenv("WORKHORSE_MODEL", "google_genai:gemini-2.5-flash")
STRATEGIST_MODEL = os.getenv("STRATEGIST_MODEL", "google_genai:gemini-2.5-pro")


def make_llm(model_id: str, *, temperature: float = 0.0, **kwargs):
    """Build a chat model from a 'provider:model' string."""
    return init_chat_model(model_id, temperature=temperature, **kwargs)


def workhorse_llm(*, temperature: float = 0.0, **kwargs):
    """Cheap, fast model for routing, profiling, and the research loop."""
    return make_llm(WORKHORSE_MODEL, temperature=temperature, **kwargs)


def strategist_llm(*, temperature: float = 0.3, **kwargs):
    """Stronger reasoning model for constructing the allocation."""
    return make_llm(STRATEGIST_MODEL, temperature=temperature, **kwargs)
