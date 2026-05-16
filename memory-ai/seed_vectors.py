"""
Seed the ChromaDB vector store with existing memories from memory.json.
Run this once to bootstrap the semantic search engine.
"""
import json
from memory.vector_store import get_vector_store

def seed():
    print("[Seed] Loading existing memories from memory.json...")
    with open("memory.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    vs = get_vector_store()
    if not vs:
        print("[Seed] ERROR: Vector store failed to initialize.")
        return

    count = 0
    for cat in ["facts", "preferences", "goals"]:
        for item in data.get(cat, []):
            content = item.get("content", item) if isinstance(item, dict) else str(item)
            if content:
                vs.add_memory(content, cat.rstrip("s"))  # facts -> fact
                count += 1
                print(f"  + [{cat}] {content}")

    print(f"\n[Seed] Done! Indexed {count} memories into ChromaDB.")

if __name__ == "__main__":
    seed()
