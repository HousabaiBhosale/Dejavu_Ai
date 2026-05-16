import requests
import json
import time

url_legal = "http://localhost:5000/api/analyze-legal"
url_mem = "http://localhost:5000/api/memories"
headers = {"Content-Type": "application/json"}

print("--- TESTING INTEGRATED LEARNING (LEGAL -> MEMORY) ---")

# 1. Analyze a dummy document
print("\nStep 1: Analyzing a legal document...")
doc_text = "This Employment Agreement is between Bob and the user. Bob agrees to work as a Python Developer for $200,000 per year."
r1 = requests.post(url_legal, json={"text": doc_text}, headers=headers)
print(f"Legal Analyzer Status: {r1.status_code}")
summary = r1.json().get('summary')
print(f"Summary: {summary}")

# 2. Check if it appeared in memory
print("\nStep 2: Checking Memory Store for the new fact...")
time.sleep(1) # Wait for filesystem save
r2 = requests.get(url_mem)
memories = r2.json()
facts = [f['content'] for f in memories.get('facts', [])]
print(f"Memory Store Facts: {facts}")

# 3. Validation
found = False
for f in facts:
    if "Legal Doc Summary" in f:
        found = True
        break

if found:
    print("\nSUCCESS: Integrated Learning working! Legal summary persisted to memory.")
else:
    print("\nFAILURE: Legal summary NOT found in memory store.")
