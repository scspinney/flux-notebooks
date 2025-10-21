import os, requests

def ask_llm(message, path="."):
    """Send message to Flux Assistant LLM API."""
    url = os.environ.get("LLM_API_URL", "http://localhost:8081/chat")
    r = requests.post(url, json={"message": message, "path": path}, timeout=20)
    r.raise_for_status()
    return r.json()
