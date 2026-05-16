import json
import re
from flask import Blueprint, request, jsonify
from utils.llm import generate_simple

try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

from memory.store import MemoryStore

legal_bp = Blueprint('legal', __name__)
memory_store = MemoryStore()


# ─────────────────────────────────────────────────────────────────────────────
# POST /analyze-legal
# Accepts: JSON { "text": "..." }  OR  multipart form with a PDF file
# Returns: { summary, risks[], clauses[] }
# ─────────────────────────────────────────────────────────────────────────────
@legal_bp.route("/analyze-legal", methods=["POST"])
def analyze_legal():
    text = ""

    # ── Handle PDF file upload ─────────────────────────────────────────────
    if "file" in request.files:
        file = request.files["file"]
        filename = file.filename.lower()

        if filename.endswith(".pdf"):
            if not PDF_SUPPORT:
                return jsonify({"error": "PDF support not installed. Run: pip install PyPDF2"}), 500
            try:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            except Exception as e:
                return jsonify({"error": f"Failed to read PDF: {str(e)}"}), 400
        else:
            # Plain text file
            try:
                text = file.read().decode("utf-8", errors="ignore")
            except Exception as e:
                return jsonify({"error": f"Failed to read file: {str(e)}"}), 400

    # ── Handle plain JSON body ─────────────────────────────────────────────
    elif request.is_json:
        body = request.get_json(force=True)
        text = (body.get("text") or "").strip()

    if not text.strip():
        return jsonify({"error": "No document text provided. Send JSON {text} or upload a file."}), 400

    # Trim to avoid token limits (keep first ~8000 chars ≈ ~2000 tokens)
    text = text[:8000]

    # ── Build LLM analysis prompt ──────────────────────────────────────────
    prompt = f"""You are an expert legal document analyzer. Analyze the following legal document and return a structured JSON analysis.

Return ONLY valid JSON (no markdown, no code blocks) in this exact format:
{{
  "summary": "2-3 sentence plain English overview of what this document is and what it governs.",
  "risks": [
    "Risk 1 — description of the risk and why the user should be aware",
    "Risk 2 — ...",
    "Risk 3 — ..."
  ],
  "clauses": [
    {{"title": "Clause Name", "content": "Plain English explanation of what this clause means for the user."}},
    {{"title": "Clause Name", "content": "..."}},
    {{"title": "Clause Name", "content": "..."}}
  ]
}}

Rules:
- summary: must be clear to someone with no legal background
- risks: list 3-6 specific risks or concerning terms; be concrete, not generic
- clauses: identify 3-8 important clauses; use simple language
- If the text is too short or not a legal document, still return the JSON with appropriate content

Legal Document:
{text}

Return ONLY valid JSON:"""

    response = generate_simple(prompt, temp=0.2)

    # Clean markdown wrappers if Gemini added them
    response = response.strip()
    if response.startswith("```"):
        response = re.sub(r"```(?:json)?", "", response).replace("```", "").strip()

    # ── Final Response & Memory Save ───────────────────────────────────────
    final_summary = "Analyzed a legal document."
    final_risks = []
    final_clauses = []

    try:
        data = json.loads(response)
        final_summary = data.get("summary", final_summary)
        final_risks = data.get("risks", [])
        final_clauses = data.get("clauses", [])
    except Exception:
        # Regex fallback
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                final_summary = data.get("summary", final_summary)
                final_risks = data.get("risks", [])
                final_clauses = data.get("clauses", [])
            except Exception:
                pass
        
        if final_summary == "Analyzed a legal document." and response:
            final_summary = response[:600].strip()

    # SAVE TO PERSISTENT MEMORY
    print(f"[Legal] Integrated Learning: Saving summary to Memory Store...")
    memory_store.add_fact(f"Legal Doc Summary: {final_summary}")

    return jsonify({
        "summary": final_summary,
        "risks":   final_risks,
        "clauses": final_clauses
    })
