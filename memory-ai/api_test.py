import requests
import json
import time

url_chat = "http://localhost:5000/api/chat"
url_mem = "http://localhost:5000/api/memories"
headers = {"Content-Type": "application/json"}

# 1. Reset (optional, but for clean test we check what's there)
print("--- STARTING CONFLICT TEST ---")

# 2. Set Name
print("\nStep 1: Setting name to Housa...")
r1 = requests.post(url_chat, json={"message": "My name is Housa"}, headers=headers)
print(f"Chat Response: {r1.json().get('reply')}")

# 3. Conflict
print("\nStep 2: Correcting name to Bob (Conflict)...")
payload = {"message": "Actually, my name is not Housa, it is Bob."}
r2 = requests.post(url_chat, json=payload, headers=headers)
print(f"Chat Response: {r2.json().get('reply')}")
print(f"Conflict Detected: {r2.json().get('conflict')}")

# 4. Verify Store
print("\nStep 3: Verifying Persistent Memory Store...")
time.sleep(1) # Give it a second to save
r3 = requests.get(url_mem)
memories = r3.json()

facts = [f['content'] for f in memories.get('facts', [])]
print(f"Current Facts in Store: {facts}")

if any("Bob" in f for f in facts) and not any("Housa" in f for f in facts):
    print("\nSUCCESS: Conflict resolved! 'Housa' removed, 'Bob' stored.")
else:
    print("\nFAILURE: Conflict logic failed. 'Housa' might still be present or 'Bob' missing.")
