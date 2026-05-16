import os
import traceback
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print(f"DEBUG: Using API Key: {api_key[:10]}...{api_key[-5:] if api_key else 'NONE'}")

try:
    client = genai.Client(api_key=api_key)
    print("Listing all models...")
    models = list(client.models.list())
    print(f"Total models found: {len(models)}")
    
    for m in models:
        print(f" - {m.name}")
        
    print("\nAttempting basic generation with top models...")
    test_models = ["models/gemini-1.5-flash", "models/gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.0-flash"]
    
    for model_id in test_models:
        try:
            print(f"Trying {model_id}...")
            response = client.models.generate_content(model=model_id, contents="Hello")
            print(f"  SUCCESS! {model_id} responded.")
            break
        except Exception as e:
            print(f"  FAIL {model_id}: {e}")
            
except Exception as e:
    print(f"CRITICAL ERROR in debug script: {e}")
    traceback.print_exc()
