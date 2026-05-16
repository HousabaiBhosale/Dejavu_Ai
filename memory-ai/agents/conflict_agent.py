import json
import re
from utils.llm import generate_simple


def resolve_memory_conflicts(new_facts, new_prefs, new_goals, memory_store):
    """
    Conflict Agent: Compares new memory against existing memory.
    If contradictions are found, the NEW memory takes precedence —
    outdated entries are removed from the store.

    Returns:
        tuple: (new_facts, new_prefs, new_goals, conflict_description)
            - conflict_description is a string if a conflict was detected, else None
    """
    mem = memory_store.load_memory()
    existing_facts = mem.get("facts", [])
    existing_prefs = mem.get("preferences", [])

    # Nothing to compare against
    if not existing_facts and not existing_prefs:
        return new_facts, new_prefs, new_goals, None

    # Nothing new to check
    if not new_facts and not new_prefs and not new_goals:
        return [], [], [], None

    # Format existing memory for prompt
    existing_str = ""
    if existing_facts:
        existing_str += "Existing Facts:\n" + "\n".join(f"  - {f}" for f in existing_facts)
    if existing_prefs:
        existing_str += "\n\nExisting Preferences:\n" + "\n".join(f"  - {p}" for p in existing_prefs)

    # Format new memory for prompt
    new_str = ""
    if new_facts:
        new_str += "New Facts:\n" + "\n".join(f"  - {f}" for f in new_facts)
    if new_prefs:
        new_str += "\n\nNew Preferences:\n" + "\n".join(f"  - {p}" for p in new_prefs)
    if new_goals:
        new_str += "\n\nNew Goals:\n" + "\n".join(f"  - {g}" for g in new_goals)

    prompt = f"""You are a memory conflict resolver for a personal AI assistant.
Your job is to find DIRECT contradictions between existing and new memory.

A contradiction example: "User's favorite color is blue" vs "User's favorite color is red".
Only flag it as a conflict if it is a clear contradiction, NOT just an update or addition.

Return ONLY valid JSON (no markdown, no code blocks) in this exact format:
{{
  "conflicts_found": true or false,
  "conflict_description": "One-sentence summary of what changed, e.g. User updated their favorite color from blue to red. Or null if no conflict.",
  "remove_facts": ["exact fact strings to remove from existing memory"],
  "remove_preferences": ["exact preference strings to remove from existing memory"]
}}

Existing Memory:
{existing_str}

New Memory:
{new_str}

Return ONLY valid JSON:"""

    response = generate_simple(prompt, temp=0.1)

    # Clean markdown code blocks if present
    response = response.strip()
    if response.startswith("```"):
        response = re.sub(r"```(?:json)?", "", response).replace("```", "").strip()

    conflict_description = None
    remove_facts = []
    remove_prefs = []

    try:
        data = json.loads(response)
        remove_facts = data.get("remove_facts", [])
        remove_prefs = data.get("remove_preferences", [])
        if data.get("conflicts_found") and data.get("conflict_description"):
            conflict_description = data["conflict_description"]
    except Exception:
        # Try regex fallback
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                remove_facts = data.get("remove_facts", [])
                remove_prefs = data.get("remove_preferences", [])
                if data.get("conflicts_found") and data.get("conflict_description"):
                    conflict_description = data["conflict_description"]
            except Exception:
                pass

    # Apply removals to the store
    if remove_facts or remove_prefs:
        print(f"[ConflictAgent] Removing outdated memory — facts: {remove_facts}, prefs: {remove_prefs}")
        memory_store.remove_items(remove_facts, remove_prefs)

    return new_facts, new_prefs, new_goals, conflict_description
