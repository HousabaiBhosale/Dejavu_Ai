from flask import Blueprint, jsonify, request, Response
import json
import os
from memory.store import MemoryStore
from memory.decay import process_decay
from agents.consolidation_agent import run_consolidation

memory_bp = Blueprint('memory', __name__)
memory_store = MemoryStore()

@memory_bp.route("/memories", methods=["GET"])
def get_all_memories():
    """Returns all memories with metadata for the management UI"""
    # Optional: run decay or consolidation before viewing for 'freshness'
    # process_decay(memory_store)
    return jsonify(memory_store.load_memory())

@memory_bp.route("/memories/<category>/<memory_id>", methods=["DELETE"])
def delete_memory(category, memory_id):
    """Allows user to correct the AI by deleting a specific memory"""
    memories = memory_store.load_memory()
    if category in memories:
        initial_count = len(memories[category])
        memories[category] = [m for m in memories[category] if m.get("id") != memory_id]
        
        if len(memories[category]) < initial_count:
            memory_store.save_memory(memories)
            return jsonify({"success": True, "message": "Memory deleted"})
            
    return jsonify({"error": "Memory not found"}), 404

@memory_bp.route("/memories/export", methods=["GET"])
def export_memories():
    """Allows user to download their entire digital brain"""
    mem = memory_store.load_memory()
    return Response(
        json.dumps(mem, indent=4, ensure_ascii=False),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=memory_export.json"}
    )

@memory_bp.route("/memories/optimize", methods=["POST"])
def optimize_memory():
    """Manually trigger consolidation and decay"""
    process_decay(memory_store)
    run_consolidation()
    return jsonify({"success": True, "message": "Memory optimized and consolidated"})
