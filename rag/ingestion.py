"""
rag/ingestion.py — LLM-based logical chunking & keyword retrieval (NO EMBEDDINGS)
"""
import os
import json
import time
import math
import re
from typing import List, Dict, Optional

import structlog
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from config import settings
from logger import get_logger
from db.client import write_audit_log

logger = get_logger(__name__)

# --------------------------------------------------------------------------- #
# Simple BM25 / Keyword Matcher for Retrieval (No Embeddings)
# --------------------------------------------------------------------------- #
class SimpleMatcher:
    def __init__(self, chunks: List[Dict]):
        self.chunks = chunks
        self.doc_freqs = {}
        self.N = len(chunks)
        self.avg_len = 0
        if self.N == 0: return
        
        total_len = 0
        for i, c in enumerate(chunks):
            text = (str(c.get("topic", "")) + " " + str(c.get("content", ""))).lower()
            words = set(re.findall(r'\w+', text))
            c["word_count"] = len(re.findall(r'\w+', text))
            total_len += c["word_count"]
            for w in words:
                self.doc_freqs[w] = self.doc_freqs.get(w, 0) + 1
        self.avg_len = total_len / self.N

    def score(self, query: str) -> List[tuple]:
        q_words = re.findall(r'\w+', query.lower())
        results = []
        for c in self.chunks:
            s_score = 0
            text = (str(c.get("topic", "")) + " " + str(c.get("content", ""))).lower()
            text_words = re.findall(r'\w+', text)
            for w in q_words:
                if w in text_words:
                    df = self.doc_freqs.get(w, 1)
                    idf = math.log(1 + (self.N - df + 0.5) / (df + 0.5))
                    tf = text_words.count(w)
                    denom = tf + 1.5 * (1 - 0.75 + 0.75 * (c.get("word_count", 1) / (self.avg_len or 1)))
                    s_score += idf * (tf * 2.5) / denom
            
            # Additional simple regex/keyword boosting 
            overlap = sum(1 for w in q_words if w in text_words)
            s_score += overlap * 0.1
            
            results.append((c, s_score))
            
        results.sort(key=lambda x: x[1], reverse=True)
        return results

# --------------------------------------------------------------------------- #
#  Ingest PDF → LLM Decompose → JSON (NO FAISS/EMBEDDING)
# --------------------------------------------------------------------------- #
def ingest_pdf(
    pdf_path: str,
    business_id: str,
    business_name: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> str:
    start_ts = time.time()
    logger.info("rag.ingest_start_no_embedding", pdf=pdf_path, business=business_name)

    # 1. Load PDF
    loader = PyPDFLoader(pdf_path)
    raw_docs = loader.load()
    
    # 2. Extract Text
    full_text = "\n\n".join([d.page_content for d in raw_docs])
    
    # 3. Use LLM to decompose into logical blocks (Func 8)
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.0
    )
    
    prompt = f"""
You are tasked with decomposing the following business document into distinct, standalone LOGICAL TOPICS or SKILLS.
First, split the explicit information into blocks such as:
- Contact and Address Info
- Business Hours
- General Pricing & Tax Rules
- Specific Item/Service Details
- Cancellation & Appointment Policies

THEN (CRITICAL STEP for Knowledge Expansion):
Generate additional logical blocks that INFER and EXPAND the business rules:
- "Inferred Upsell Opportunities": Suggest item combinations, logical add-ons, or drinks that go well with the services/items listed.
- "Inferred Skills": Customer service logic, typical constraints, and operational heuristics derived from the text.
- "Service Enrichment": If an item lacks details (e.g., car rental, basic service), intelligently infer standard features, add-ons, or standard operating times that apply in the real world.

Do not omit any details, prices, or rules.
Output the result ONLY as a valid JSON Array of objects with this structure:
[
  {{ "topic": "Short Topic Title", "content": "Full detailed content representing this logical block. Include numbers, fees, options, and your inferred logic." }}
]

DOCUMENT TEXT:
{full_text[:30000]}
"""
    try:
        res = llm.invoke([HumanMessage(content=prompt)])
        raw = res.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        raw = raw.strip()
        blocks = json.loads(raw)
    except Exception as e:
        logger.error("rag.llm_decomposition_failed", error=str(e))
        # Fallback mechanical split
        blocks = [{"topic": f"Chunk {i}", "content": full_text[i:i+1500]} for i in range(0, len(full_text), 1500)]
        
    for i, b in enumerate(blocks):
        b["chunk_index"] = i
        b["business_id"] = business_id
        b["source"] = os.path.basename(pdf_path)
        
    # 4. Save to JSON instead of FAISS
    store_dir = os.path.join(settings.VECTOR_STORE_PATH, business_id)
    os.makedirs(store_dir, exist_ok=True)
    out_path = os.path.join(store_dir, "chunks.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(blocks, f, ensure_ascii=False, indent=2)

    duration_ms = int((time.time() - start_ts) * 1000)
    logger.info("rag.llm_chunks_created", total_chunks=len(blocks), business=business_name)

    write_audit_log(
        event_type="rag_ingest",
        business_id=business_id,
        input_data={"pdf_path": pdf_path, "pages": len(raw_docs)},
        output_data={"logical_chunks": len(blocks), "store_path": out_path},
        duration_ms=duration_ms,
    )
    return store_dir

# --------------------------------------------------------------------------- #
# Cache & Retrieval
# --------------------------------------------------------------------------- #
_vs_cache = {}

def load_chunks(business_id: str) -> List[Dict]:
    if business_id in _vs_cache:
        return _vs_cache[business_id]
        
    store_dir = os.path.join(settings.VECTOR_STORE_PATH, business_id)
    out_path = os.path.join(store_dir, "chunks.json")
    if not os.path.exists(out_path):
        return []
        
    with open(out_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _vs_cache[business_id] = data
    return data

def clear_cache(business_id: str = None) -> None:
    if business_id: _vs_cache.pop(business_id, None)
    else: _vs_cache.clear()

def search_knowledge(
    query: str,
    business_id: str,
    k: int = 5,
    session_id: str = None,
) -> List[Dict]:
    """
    Non-embedding semantic search over JSON chunks (Func 7).
    """
    start_ts = time.time()
    
    chunks = load_chunks(business_id)
    if not chunks:
        return []

    matcher = SimpleMatcher(chunks)
    scored = matcher.score(query)
    
    top_matches = [s for s in scored if s[1] > 0.0][:k]
    
    # Fallback to general matches
    if not top_matches and chunks:
        top_matches = [(c, 0.1) for c in chunks[:k]]

    results = []
    for c, score in top_matches:
        results.append({
            "content": str(c.get("topic", "")) + ": " + str(c.get("content", "")),
            "score": round(score, 4),
            "source": c.get("source", "unknown"),
            "chunk_index": c.get("chunk_index", -1),
            "page": c.get("topic", "Topic"),
        })

    duration_ms = int((time.time() - start_ts) * 1000)
    logger.info("rag.search_no_embedding", query=query, results=len(results), duration_ms=duration_ms)

    write_audit_log(
        event_type="rag_retrieval",
        session_id=session_id,
        business_id=business_id,
        input_data={"query": query, "k": k, "type": "non-embedding"},
        output_data={"results_count": len(results)},
        rag_chunks=results,
        duration_ms=duration_ms,
    )
    return results
