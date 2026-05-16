import json
import re
import traceback
from flask import Blueprint, request, jsonify
from utils.llm import generate_response
from memory.store import MemoryStore
from memory.vector_store import get_vector_store

chat_bp = Blueprint('chat', __name__)

# Single user memory store (JSON/MySQL)
memory_store = MemoryStore("memory.json", user_id="default")

# Vector store for semantic search (ChromaDB)
vector_store = get_vector_store()
if vector_store:
    print("[Chat] Semantic memory engine ACTIVE (ChromaDB)")
else:
    print("[Chat] Semantic memory engine unavailable, using keyword-only retrieval")

# In-session conversation history
session_history = []


@chat_bp.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)
        user_input = (data.get("message") or "").strip()
        continue_session = data.get("continue", False)

        if not user_input:
            return jsonify({"error": "Message is required"}), 400

        # Load current memory
        current_memory = memory_store.load_memory()
        memory_context = memory_store.get_recap()

        # ── SEMANTIC SEARCH (Vector DB) ──────────────────────────────────────
        semantic_context = ""
        if vector_store:
            try:
                results = vector_store.search(user_input, top_k=5)
                if results:
                    semantic_hits = [f"  - {r['content']} (relevance: {1 - r['distance']:.0%})" for r in results]
                    semantic_context = "\n".join(semantic_hits)
                    print(f"[Chat] Semantic search found {len(results)} relevant memories")
            except Exception as e:
                print(f"[Chat] Semantic search failed (non-fatal): {e}")

        # ── HANDLE SESSION CONTINUE ──────────────────────────────────────────
        if continue_session:
            if memory_context:
                recap_prompt = f"""Based on these memories, give a warm 2-3 sentence recap to resume.
                {memory_context}"""
                from utils.llm import generate_simple
                recap = generate_simple(recap_prompt, temp=0.7)
                session_history.clear()
                return jsonify({
                    "reply": recap,
                    "debug": {"memory_retrieved": memory_context, "decision": "User resumed session."},
                    "is_recap": True
                })
            return jsonify({"reply": "Welcome back! Let's start fresh.", "is_recap": True})

        # ── MASTER CONSOLIDATED PROMPT ───────────────────────────────────────
        semantic_section = ""
        if semantic_context:
            semantic_section = f"\n\nSEMANTIC RETRIEVAL (Most relevant memories to this message):\n{semantic_context}"

        system_prompt = f"""You are 'Memory AI', an empathetic assistant with a persistent digital second brain.
        
CURRENT MEMORY STORE (What you already know):
{memory_context if memory_context else 'Empty'}{semantic_section}

YOUR TASK:
1. INTERNAL RETRIEVAL: From the 'CURRENT MEMORY STORE', identify facts/prefs relevant to the user's message.
2. CHAT RESPONSE: Respond naturally and conversationally. Do NOT start responses with repetitive phrases like "I remember you mentioned that" or "I recall". Instead, weave the knowledge into the flow (e.g., "Since you love Python, you might like this...").
3. MEMORY EXTRACTION: Extract NEW permanent facts, preferences, or goals.
4. CONFLICT & REDUNDANCY DETECTION: 
   - CONFLICT: If the user explicitly contradicts a piece of 'CURRENT MEMORY STORE' (e.g., they say their name is 'Bob' but you have 'Housa' stored), you MUST identify this as a conflict. The NEW info overrides the old.
   - REDUNDANCY: If the info is exactly the same or very similar to what's already stored, do NOT add it to "new_memory". Note this in "decision".

OUTPUT FORMAT:
Return ONLY a valid JSON object:
{{
  "reply": "conversational response",
  "memory_retrieved": "summary of relevant old memories",
  "decision": "Explain if you found new info, a conflict, or if it was redundant.",
  "new_memory": {{"facts": [], "preferences": [], "goals": []}},
  "conflict": "User-friendly description of the contradiction found, otherwise null",
  "remove_items": {{"facts": [], "preferences": []}}
}}

RULES:
- IF CONFLICT: The new info takes precedence. Put the OLD text in "remove_items".
- NATURAL ACKNOWLEDGEMENT: Acknowledge previous info naturally without template phrases.
- RETURN ONLY JSON.
"""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(session_history)
        messages.append({"role": "user", "content": user_input})

        # Single LLM Call
        raw_response = generate_response(messages, temp=0.7)
        print(f"[Chat Debug] Raw LLM Response: {raw_response[:500]}...")
        
        # Clean JSON from response
        json_str = raw_response.strip()

        # Check if the LLM client exhausted all fallbacks and returned an explicit error string
        if json_str.startswith("Error:"):
            return jsonify({
                "reply": "System notice: Neural link models are temporarily unavailable or over quota. Please wait a few moments and try again.",
                "debug": {"error_detail": json_str},
                "conflict": None
            }), 200
        
        # 1. Standard markdown block removal
        if "```" in json_str:
            json_str = re.sub(r"```(?:json)?", "", json_str).replace("```", "").strip()
        
        # 2. Extract anything between curly braces as a primary strategy
        res = None
        try:
            res = json.loads(json_str)
        except Exception:
            # Try to find the FIRST leading { and LAST trailing }
            match = re.search(r'(\{.*\})', json_str, re.DOTALL)
            if match:
                try:
                    res = json.loads(match.group(1))
                except Exception as e:
                    print(f"[JSON Error] Failed last-ditch parse: {e}")
                    raise ValueError(f"Could not parse Gemini JSON response even with regex: {json_str[:200]}...")
            else:
                # If no JSON at all, maybe it's a raw conversational error string
                if "sorry" in json_str.lower() or "connection" in json_str.lower():
                    return jsonify({"error": json_str}), 500
                raise ValueError(f"No JSON object found in Gemini response: {json_str[:200]}...")

        # ── UPDATE MEMORY STORE ──────────────────────────────────────────────
        new_mem = res.get("new_memory", {})
        rem_items = res.get("remove_items", {})
        
        # 1. Remove conflicts
        if rem_items.get("facts") or rem_items.get("preferences"):
            memory_store.remove_items(rem_items.get("facts", []), rem_items.get("preferences", []))
            
        # 2. Add new memories (JSON + Vector DB)
        if new_mem.get("facts") or new_mem.get("preferences") or new_mem.get("goals"):
            memory_store.update_memory(
                new_mem.get("facts", []), 
                new_mem.get("preferences", []), 
                new_mem.get("goals", [])
            )
            # Sync to vector store for semantic search
            if vector_store:
                try:
                    for fact in new_mem.get("facts", []):
                        vector_store.add_memory(fact, "fact")
                    for pref in new_mem.get("preferences", []):
                        vector_store.add_memory(pref, "preference")
                    for goal in new_mem.get("goals", []):
                        vector_store.add_memory(goal, "goal")
                except Exception as e:
                    print(f"[Chat] Vector store sync failed (non-fatal): {e}")

        # Update Session History
        session_history.append({"role": "user", "content": user_input})
        session_history.append({"role": "assistant", "content": res.get("reply", "")})

        return jsonify({
            "reply": res.get("reply"),
            "debug": {
                "memory_retrieved": res.get("memory_retrieved"),
                "semantic_context": semantic_context if semantic_context else "No semantic matches",
                "context_used": res.get("memory_retrieved"),
                "decision": res.get("decision"),
                "conflict": res.get("conflict"),
                "stored_memory": memory_store.load_memory(),
                "vector_db_active": vector_store is not None
            },
            "conflict": res.get("conflict")
        })

    except Exception as e:
        print(f"[Chat Error] {e}")
        error_trace = traceback.format_exc()
        return jsonify({"error": f"Neural link unstable. Details: {e}\n{error_trace}"}), 500


@chat_bp.route("/check-memory", methods=["GET"])
def check_memory():
    has_mem = memory_store.has_memory()
    return jsonify({"has_memory": has_mem})
