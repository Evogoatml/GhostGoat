import os, requests

API_URL = "https://api-inference.huggingface.co/models/google/gemma-2b-it"
API_KEY = os.environ.get("HF_API_KEY") or "hf_your_token_here"

def ask(prompt, max_new_tokens=128, temperature=0.7, top_p=0.9):
    if not API_KEY or API_KEY.startswith("hf_your"):
        return "HF_API_KEY not set."
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
    }
    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=90)
        if resp.status_code == 200:
            result = resp.json()
            if isinstance(result, list) and result:
                return result[0].get("generated_text", str(result))
            elif isinstance(result, dict):
                return result.get("generated_text") or str(result)
            return str(result)
        return f"Error {resp.status_code}: {resp.text}"
    except Exception as e:
        return f"Network error: {e}"
