import json
from utils.llm import generate_simple
from memory.store import MemoryStore

class ConsolidationAgent:
    """
    Nightly optimization agent: Merges similar memories and cleans up contradictions.
    This is what makes the system feel 'alive' and organized.
    """
    
    def __init__(self, memory_store):
        self.store = memory_store

    def consolidate(self):
        print("[ConsolidationAgent] Starting memory optimization...")
        memories = self.store.load_memory()
        
        for cat in ["facts", "preferences", "goals"]:
            if not memories[cat]: continue
            
            # Group items for LLM analysis
            content_list = [m["content"] for m in memories[cat]]
            
            prompt = f"""You are a Memory Consolidation Expert. 
Review these {cat} in a user's digital brain:
{json.dumps(content_list, indent=2)}

TASK:
1. Identify items that are redundant or very similar.
2. Identify items that are contradictions.
3. Merge them into a single, better-written fact if they represent the same thing.
4. Keep original items that are unique.

RETURN a JSON object:
{{
  "to_remove": ["exact old strings to delete"],
  "to_add": ["newly merged high-quality strings"]
}}
Only return JSON.
"""
            res_raw = generate_simple(prompt, temp=0.3)
            try:
                # Basic JSON extraction
                import re
                match = re.search(r'(\{.*\})', res_raw, re.DOTALL)
                if not match: continue
                res = json.loads(match.group(1))
                
                # Apply changes
                to_remove = res.get("to_remove", [])
                to_add = res.get("to_add", [])
                
                if to_remove or to_add:
                    print(f"[ConsolidationAgent] Optimizing {cat}: Removing {len(to_remove)}, Adding {len(to_add)}")
                    
                    def should_remove(item_content, removal_list):
                        normalized = item_content.strip().lower()
                        for r in removal_list:
                            if r.strip().lower() == normalized:
                                return True
                        return False

                    # Filter out removed items using fuzzy/normalized check
                    memories[cat] = [m for m in memories[cat] if not should_remove(m["content"], to_remove)]
                    
                    # Add new ones
                    for new_c in to_add:
                        memories[cat].append({"content": new_c, "importance": 0.7})
                
            except Exception as e:
                print(f"[ConsolidationAgent] Error processing {cat}: {e}")
                
        self.store.save_memory(memories)
        print("[ConsolidationAgent] Consolidation complete.")

def run_consolidation():
    store = MemoryStore()
    agent = ConsolidationAgent(store)
    agent.consolidate()
