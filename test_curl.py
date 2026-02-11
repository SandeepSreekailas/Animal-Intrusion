import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

print(f"Testing URL: https://generativelanguage.googleapis.com/v1beta/models?key=HIDDEN")

try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        print("[-] Available Models:")
        for model in data.get('models', []):
            print(f"  - {model['name']}")
    else:
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
