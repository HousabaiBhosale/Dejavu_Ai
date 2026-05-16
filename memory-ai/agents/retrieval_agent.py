import re
from utils.llm import generate_simple


def retrieve_relevant_memory(user_input, memory_store):
    """
    Retrieval Agent: Scans stored memory and returns only the parts
    that are relevant to the user's current message.

    Returns:
        str: Relevant memory context string, or "" if nothing applies.
    """
    mem = memory_store.load_memory()
    facts = mem.get("facts", [])
    prefs = mem.get("preferences", [])
    goals = mem.get("goals", [])

    if not facts and not prefs and not goals:
        return ""

    # Format stored memory for LLM evaluation
    memory_context = ""
    if facts:
        memory_context += "Facts:\n" + "\n".join(f"  - {f}" for f in facts) + "\n\n"
    if prefs:
        memory_context += "Preferences:\n" + "\n".join(f"  - {p}" for p in prefs) + "\n\n"
    if goals:
        memory_context += "Goals:\n" + "\n".join(f"  - {g}" for g in goals)

    prompt = f"""You are a memory retrieval system for a personal AI assistant.
Given the user's new message, identify which stored memories are directly relevant and useful for crafting a personalized response.

Instructions:
- Return ONLY the relevant items as a brief, readable summary.
- If NO stored memory is relevant to the user's message, reply with exactly the word: None
- Do NOT include irrelevant or tangentially related items.
- Do NOT repeat the user's message back.

Stored Memory:
{memory_context}

User Message: {user_input}

Relevant memory summary (or "None"):"""

    result = generate_simple(prompt, temp=0.1)
    result = result.strip()

    if result.lower() == "none" or not result:
        return ""

    return result
