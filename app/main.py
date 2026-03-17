"""
app/main.py — FastAPI server
Endpoints: /agent/chat, /health, /business/load_pdf, /admin/*
"""
import os
import json
import uuid
import shutil
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

import structlog
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from logger import setup_logging, get_logger
from db.client import (
    create_session, get_session, close_session,
    get_messages, list_businesses, get_business_by_name,
    upsert_business, get_orders_by_session, get_appointments_by_session,
    get_db, _row_to_dict, delete_business, get_business_by_id
)
from agent.graph import run_agent_turn
from agent.business_profile import extract_business_profile, clear_profile_cache
from rag.ingestion import ingest_pdf, search_knowledge, clear_cache as clear_rag_cache

# --------------------------------------------------------------------------- #
#  Setup
# --------------------------------------------------------------------------- #
setup_logging(settings.LOG_LEVEL)
logger = get_logger("app.main")

os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)
os.makedirs(settings.PDF_UPLOAD_PATH, exist_ok=True)
os.makedirs("data", exist_ok=True)

app = FastAPI(
    title="Generic AI Agent — Orders + Scheduling",
    description="Business-agnostic AI agent backed by PDF knowledge base",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
#  Request / Response models
# --------------------------------------------------------------------------- #
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    business_name: str

class ChatResponse(BaseModel):
    response: str
    session_id: str
    business_name: str
    iterations: int
    duration_ms: int
    tool_calls: Optional[List[Dict[str, Any]]] = None
    citations: Optional[List[Dict[str, Any]]] = None

class LoadPDFRequest(BaseModel):
    business_name: str
    business_type: str
    description: Optional[str] = None


# --------------------------------------------------------------------------- #
#  Session cache (in-memory, keyed by session_id)
# --------------------------------------------------------------------------- #
_session_cache: Dict[str, Dict] = {}


def _get_or_create_session(session_id: Optional[str], business_name: str) -> Dict:
    """Get existing session or create new one."""
    if session_id and session_id in _session_cache:
        return _session_cache[session_id]

    # Load business from DB
    business = get_business_by_name(business_name)
    if not business:
        raise HTTPException(
            status_code=404,
            detail=f"Business '{business_name}' not found. Load a PDF first via POST /business/load_pdf"
        )

    if session_id:
        db_session = get_session(session_id)
        if db_session:
            _session_cache[session_id] = {
                "session_id": session_id,
                "business_id": business["id"],
                "business_name": business["name"],
                "history": [],
                "order_id": None,
                "appointment_id": None,
            }
            return _session_cache[session_id]

    # Create new
    new_session = create_session(business["id"])
    sid = new_session["id"]
    _session_cache[sid] = {
        "session_id": sid,
        "business_id": business["id"],
        "business_name": business["name"],
        "history": [],
        "order_id": None,
        "appointment_id": None,
    }
    return _session_cache[sid]


# --------------------------------------------------------------------------- #
#  Routes
# --------------------------------------------------------------------------- #

@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": time.time(),
        "model": settings.GEMINI_MODEL,
    }


@app.post("/agent/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Main conversational endpoint.
    Send a message and get the agent's response.
    Maintains conversation history per session.
    """
    logger.info(
        "POST /agent/chat",
        business=req.business_name,
        session_id=req.session_id,
        message=req.message[:100],
    )

    session = _get_or_create_session(req.session_id, req.business_name)
    session_id = session["session_id"]

    # business_context artık yok — profil PDF'ten her turn'de otomatik yüklenir
    # Tüm iş kuralları (vergi, teslimat, randevu süresi vb.) PDF profilinden gelir
    result = run_agent_turn(
        user_message=req.message,
        session_id=session_id,
        business_id=session["business_id"],
        business_name=session["business_name"],
        conversation_history=session["history"],
    )

    # Update history
    session["history"].append({"role": "user", "content": req.message})
    session["history"].append({"role": "assistant", "content": result["response"]})

    return ChatResponse(
        response=result["response"],
        session_id=session_id,
        business_name=req.business_name,
        iterations=result["iterations"],
        duration_ms=result["duration_ms"],
        tool_calls=result.get("tool_calls"),
        citations=result.get("citations"),
    )


@app.post("/business/load_pdf")
async def load_pdf(
    file: UploadFile = File(...),
    business_name: str = Form(...),
    business_type: str = Form(...),
    description: str = Form(""),
):
    """
    Upload a business PDF and index it into the vector store.
    This must be done before chatting with that business.
    """
    logger.info("POST /business/load_pdf", name=business_name, type=business_type)

    # Save PDF
    pdf_filename = f"{business_name.replace(' ', '_')}_{uuid.uuid4().hex[:8]}.pdf"
    pdf_path = os.path.join(settings.PDF_UPLOAD_PATH, pdf_filename)
    os.makedirs(settings.PDF_UPLOAD_PATH, exist_ok=True)

    with open(pdf_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Register business in DB
    business = upsert_business(
        name=business_name,
        business_type=business_type,
        pdf_path=pdf_path,
        description=description,
    )

    # Ingest into vector store
    store_path = ingest_pdf(
        pdf_path=pdf_path,
        business_id=business["id"],
        business_name=business_name,
    )

    # PDF'ten iş kurallarını otomatik çıkar (vergi, randevu süresi, yetenekler vs.)
    logger.info("Extracting business profile from PDF...", business=business_name)
    clear_profile_cache(business["id"])
    profile = extract_business_profile(
        business_id=business["id"],
        business_name=business_name,
    )

    return {
        "message": f"PDF for '{business_name}' loaded and indexed",
        "business_id": business["id"],
        "business_name": business_name,
        "pdf_path": pdf_path,
        "vector_store_path": store_path,
        "extracted_profile": {
            "business_type": profile.get("business_type"),
            "capabilities": profile.get("capabilities"),
            "tax_rate": profile.get("tax_rate"),
            "currency": profile.get("currency"),
            "default_appointment_duration_min": profile.get("default_appointment_duration_min"),
            "has_delivery": profile.get("has_delivery_option"),
            "item_categories": profile.get("item_categories", []),
        },
        "status": "ready",
    }


@app.get("/business/list")
def list_businesses_endpoint():
    """List all registered businesses."""
    return {"businesses": list_businesses()}


@app.delete("/business/{business_id}")
def delete_business_endpoint(business_id: str):
    """Delete a business, its PDF, and its vector store."""
    logger.info("DELETE /business", id=business_id)
    
    biz = get_business_by_id(business_id)
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    
    pdf_path = biz.get("pdf_path")
    
    # 2. Delete from Database
    success = delete_business(business_id)
    if not success:
        raise HTTPException(status_code=500, detail="Deletion from database failed")
    
    # 3. Cleanup Files
    try:
        if pdf_path and os.path.exists(pdf_path):
            os.remove(pdf_path)
            logger.info("PDF deleted", path=pdf_path)
            
        store_dir = os.path.join(settings.VECTOR_STORE_PATH, business_id)
        if os.path.exists(store_dir):
            shutil.rmtree(store_dir)
            logger.info("Vector store deleted", path=store_dir)
            
        # 4. Clear Caches
        clear_profile_cache(business_id)
        clear_rag_cache(business_id)
        
    except Exception as e:
        logger.warning("cleanup_failed", error=str(e))
        
    return {"message": "Business and all its data deleted successfully"}


@app.get("/admin/session/{session_id}")
def get_session_details(session_id: str):
    """Debug: get full session details including messages and orders."""
    session = get_session(session_id)
    messages = get_messages(session_id)
    orders = get_orders_by_session(session_id)
    appointments = get_appointments_by_session(session_id)

    return {
        "session": session,
        "messages_count": len(messages),
        "messages": messages,
        "orders": orders,
        "appointments": appointments,
    }


@app.get("/admin/audit/{session_id}")
def get_audit_log(session_id: str, limit: int = 50):
    """Debug: get audit log for a session — all tool calls, LLM requests, RAG retrievals."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM audit_logs WHERE session_id = ? ORDER BY created_at LIMIT ?",
        (session_id, limit)
    ).fetchall()
    conn.close()
    return {"session_id": session_id, "logs": [_row_to_dict(r) for r in rows]}


@app.get("/admin/orders")
def get_all_orders(status: str = None, limit: int = 20):
    """Debug: list all orders, optionally filtered by status."""
    conn = get_db()
    query = "SELECT * FROM orders"
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return {"orders": [_row_to_dict(r) for r in rows]}


@app.get("/admin/appointments")
def get_all_appointments(status: str = None, limit: int = 20):
    """Debug: list all appointments."""
    from db.client import get_db, _row_to_dict
    conn = get_db()
    query = "SELECT * FROM appointments"
    params = []
    if status:
        query += " WHERE status = ?"
        params.append(status)
    query += " ORDER BY scheduled_at LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return {"appointments": [_row_to_dict(r) for r in rows]}
