import os
import time
import requests
import json
from dotenv import load_dotenv

# Load env variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip().strip('"').strip("'")

FAST_MODELS = [
    "meta-llama/llama-3-8b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "openai/gpt-oss-120b:free"
]

REASONING_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/llama-3.1-nemotron-70b-instruct:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3-8b-instruct:free" # Fallback if larger models fail
]

def call_openrouter(messages: list, model: str, temperature: float = 0.1, max_tokens: int = 1500) -> str:
    """
    Call the OpenRouter API with a specific model.
    """
    if not OPENROUTER_API_KEY:
        raise ValueError(
            "OPENROUTER_API_KEY is missing from environment. Please add it to your backend/.env file."
        )

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/enterprise/copilot",
        "X-Title": "Agentic Enterprise Copilot"
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=45)
    response.raise_for_status()
    result = response.json()
    
    if "choices" not in result or not result["choices"]:
        raise ValueError(f"Unexpected response format from OpenRouter: {result}")
        
    return result["choices"][0]["message"]["content"]

def call_llm(messages: list, role: str = "fast", temperature: float = 0.1, max_tokens: int = 1500) -> str:
    """
    Wrapper to call OpenRouter LLM using model fallbacks based on role ('fast' or 'reasoning').
    """
    models = FAST_MODELS if role == "fast" else REASONING_MODELS
    last_error = None
    
    for idx, model in enumerate(models):
        try:
            print(f"[{role.upper()} LLM] Trying model: {model} (Fallback level {idx})...")
            content = call_openrouter(messages, model, temperature, max_tokens)
            print(f"[{role.upper()} LLM] Success using {model}")
            return content
        except Exception as e:
            print(f"[{role.upper()} LLM] Error with {model}: {e}")
            last_error = e
            # Brief sleep before retrying fallback
            time.sleep(1)
            
    raise ValueError(f"All models failed for role '{role}'. Last error: {last_error}")
