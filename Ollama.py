import requests
import sys

# -------- CONFIG --------
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"   # <-- change this to whatever model you want
# ------------------------

def ask_ollama(prompt):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    r = requests.post(OLLAMA_URL, json=payload)
    r.raise_for_status()

    return r.json()["response"]

def main():
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = input("Prompt: ")

    response = ask_ollama(prompt)
    print("\n--- Ollama Response ---\n")
    print(response)

if __name__ == "__main__":
    main()
