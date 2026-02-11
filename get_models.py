import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    response = requests.get(url)
    with open('models.txt', 'w') as f:
        if response.status_code == 200:
            data = response.json()
            f.write("[-] Available Models:\n")
            for model in data.get('models', []):
                # Clean name: remove "models/" prefix if present
                clean_name = model['name'].replace('models/', '')
                f.write(f"{clean_name}\n")
        else:
            f.write(f"Status: {response.status_code}\nResponse: {response.text}")
    print("Done writing models.txt")
except Exception as e:
    with open('models.txt', 'w') as f:
        f.write(f"Error: {e}")
    print(f"Error: {e}")
