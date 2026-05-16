import os
import google.generativeai as genai
from dotenv import load_dotenv
import json

load_dotenv()
key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=key)

system_prompt = """You are 'Memory AI'. 
OUTPUT FORMAT:
Return ONLY a valid JSON object with these keys:
- "reply": your response
- "memory_retrieved": summary
- "decision": why
- "new_memory": {"facts": [], "preferences": [], "goals": []}
- "conflict": null
- "remove_items": {"facts": [], "preferences": []}
"""

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "Hello, I am a developer named Housa."}
]

print("Attempting Master Call...")
try:
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        system_instruction=system_prompt
    )
    # Convert messages for Gemini
    gemini_history = [] # No history for first call
    last_msg = "Hello, I am a developer named Housa."

    chat = model.start_chat(history=gemini_history)
    response = chat.send_message(
        last_msg,
        generation_config=genai.types.GenerationConfig(temperature=0.7)
    )
    print("SUCCESS!")
    print("RAW RESPONSE:")
    print(response.text)
    
    # Try parsing
    print("\nPARSING TEST:")
    json.loads(response.text.strip())
    print("JSON PARSE OK")
except Exception as e:
    print(f"FAILED: {e}")
