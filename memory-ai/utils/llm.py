import os
import traceback
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

class GeminiClient:
    def __init__(self, model_id=None):
        self.client = genai.Client(api_key=API_KEY)
        self.model_id = model_id
        self.available_models = []
        self._initialize_model()

    def _initialize_model(self):
        """Automatically find the best WORKING model for this API key"""
        try:
            print("[LLM] Discovering models for this API key...")
            model_list = list(self.client.models.list())
            # Filter to ONLY models that support text generation (gemini models)
            valid_models = [m.name for m in model_list if "gemini" in m.name.lower()]
            sorted_models = sorted(valid_models, reverse=True)
            self.available_models = sorted_models
            print(f"[LLM] Discovered Text Models: {sorted_models[:5]}... (Total: {len(sorted_models)})")
            
            # Prefer stable latest aliases
            preferred = ["models/gemini-2.5-flash", "models/gemini-2.0-flash", "models/gemini-flash-latest", "models/gemini-pro-latest", "models/gemini-1.5-flash"]
            
            # Find the first preferred model THAT PASSES A HEARTBEAT TEST
            for p in preferred:
                if p in sorted_models:
                    try:
                        print(f"[LLM] Heartbeat check for {p}...")
                        # Tiny test call
                        self.client.models.generate_content(model=p, contents="ping", config=types.GenerateContentConfig(max_output_tokens=1))
                        self.model_id = p
                        print(f"[LLM] Success! Neural link established with: {self.model_id}")
                        return
                    except Exception as e:
                        print(f"[LLM Warning] Model failed heartbeat ({p}): {e}")
                        continue

            # Absolute fallback
            self.model_id = sorted_models[0] if sorted_models else "models/gemini-1.5-flash"
            print(f"[LLM] Warning: Using best effort fallback: {self.model_id}")

        except Exception as e:
            print(f"[LLM Error] Error during model discovery: {e}")
            self.model_id = "models/gemini-1.5-flash"

    def generate_chat(self, messages, temp=0.7):
        """Standard chat with fallback chain"""
        # Chain models to try
        models_to_try = [self.model_id] + self.available_models[:3]
        
        system_instr = next((m['content'] for m in messages if m['role'] == 'system'), "You are Memory AI")
        
        contents = []
        for msg in messages:
            if msg['role'] == 'system': continue
            role = "user" if msg['role'] == 'user' else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg['content'])]
            ))

        last_error = None
        for model in models_to_try:
            if not model: continue
            try:
                print(f"[LLM] Handshaking with {model}...")
                response = self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=temp,
                        system_instruction=system_instr
                    )
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                last_error = e
                print(f"[LLM Warning] {model} failed: {e}")
                continue
        
        return f"Error: {last_error}"

    def generate_simple(self, prompt, temp=0.1):
        """Single completion with fallback chain"""
        models_to_try = [self.model_id] + self.available_models[:2]
        last_error = None

        for model in models_to_try:
            if not model: continue
            try:
                print(f"[LLM] Simple handshake with {model}...")
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=temp)
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                last_error = e
                print(f"[LLM Warning] generate_simple {model} failed: {e}")
                continue
        
        print(f"[LLM Error] generate_simple complete failure after trying {len(models_to_try)} models.")
        return ""

# Singleton
_client = GeminiClient()

def generate_response(messages, temp=0.7):
    return _client.generate_chat(messages, temp)

def generate_simple(prompt, temp=0.1):
    return _client.generate_simple(prompt, temp)

if __name__ == "__main__":
    print("Testing Neural Link...")
    test_msg = [{"role": "user", "content": "Neural Handshake Test"}]
    print(f"Response: {generate_response(test_msg)}")
