import os
from dotenv import load_dotenv
from google import genai
import traceback

# Load .env
load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

print(f"[-] API Key found: {'YES' if api_key else 'NO'}")

if not api_key:
    print("Cannot test without API Key")
    exit(1)

print("\n--- TEST: google-genai (New SDK) ---")

candidates = [
    'gemini-2.0-flash',
    'gemini-2.0-flash-exp',
    'gemini-1.5-flash',
    'gemini-1.5-pro',
    'gemini-1.0-pro',
    'gemini-pro'
]

success = False
for model_name in candidates:
    print(f"\n[-] Testing model: '{model_name}'...")
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents='Hello, are you online?'
        )
        print(f"[SUCCESS] Model '{model_name}' works! Response: {response.text}")
        success = True
        break
    except Exception as e:
        print(f"[FAILED] Model '{model_name}' failed. Error: {e}")

if not success:
    print("\n[CRITICAL FAILURE] No tested models worked.")
