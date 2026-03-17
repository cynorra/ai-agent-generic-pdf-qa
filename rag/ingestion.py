"""
rag/ingestion.py — PDF ingestion + embedding + FAISS vector store
Uses Google Gemini embeddings. Business PDF → searchable knowledge base.
"""
import os
import json
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import structlog
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document

from config import settings
from logger import get_logger
from db.client import write_audit_log

logger = get_logger(__name__)

# --------------------------------------------------------------------------- #
#  Embeddings
# --------------------------------------------------------------------------- #
def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=settings.GEMINI_EMBEDDING_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
    )


# --------------------------------------------------------------------------- #
#  Ingest PDF → FAISS
# --------------------------------------------------------------------------- #
def ingest_pdf(
    pdf_path: str,
    business_id: str,
    business_name: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> str:
    """
    Parse PDF, chunk text, embed with Gemini, save FAISS index.
    Returns path to saved vector store.
    """
    start_ts = time.time()
    logger.info("rag.ingest_start", pdf=pdf_path, business=business_name)

    # Load PDF
    loader = PyPDFLoader(pdf_path)
    raw_docs = loader.load()
    logger.info("rag.pdf_loaded", pages=len(raw_docs), pdf=pdf_path)

    # Chunk
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " "],
    )
    docs = splitter.split_documents(raw_docs)

    # Add metadata to every chunk
    for i, doc in enumerate(docs):
        doc.metadata.update({
            "business_id": business_id,
            "business_name": business_name,
            "chunk_index": i,
            "source": Path(pdf_path).name,
        })

    logger.info("rag.chunks_created", total_chunks=len(docs), business=business_name)

    # Embed + build FAISS index
    embeddings = get_embeddings()
    vectorstore = FAISS.from_documents(docs, embeddings)

    # Persist to disk
    store_dir = os.path.join(settings.VECTOR_STORE_PATH, business_id)
    os.makedirs(store_dir, exist_ok=True)
    vectorstore.save_local(store_dir)

    duration_ms = int((time.time() - start_ts) * 1000)
    logger.info(
        "rag.ingest_complete",
        business=business_name,
        chunks=len(docs),
        store_path=store_dir,
        duration_ms=duration_ms,
    )

    write_audit_log(
        event_type="rag_ingest",
        business_id=business_id,
        input_data={"pdf_path": pdf_path, "pages": len(raw_docs)},
        output_data={"chunks": len(docs), "store_path": store_dir},
        duration_ms=duration_ms,
    )

    return store_dir


# --------------------------------------------------------------------------- #
#  Load vector store
# --------------------------------------------------------------------------- #
_vs_cache: Dict[str, FAISS] = {}


def load_vector_store(business_id: str) -> Optional[FAISS]:
    if business_id in _vs_cache:
        return _vs_cache[business_id]

    store_dir = os.path.join(settings.VECTOR_STORE_PATH, business_id)
    if not os.path.exists(store_dir):
        logger.warning("rag.vector_store_not_found", business_id=business_id)
        return None

    embeddings = get_embeddings()
    vs = FAISS.load_local(
        store_dir, embeddings, allow_dangerous_deserialization=True
    )
    _vs_cache[business_id] = vs
    logger.info("rag.vector_store_loaded", business_id=business_id)
    return vs


def clear_cache(business_id: str = None) -> None:
    if business_id:
        _vs_cache.pop(business_id, None)
    else:
        _vs_cache.clear()


# --------------------------------------------------------------------------- #
#  Retrieval
# --------------------------------------------------------------------------- #
def search_knowledge(
    query: str,
    business_id: str,
    k: int = 5,
    session_id: str = None,
) -> List[Dict]:
    """
    Semantic search over the business PDF knowledge base.
    Returns list of {content, score, metadata} dicts.
    """
    start_ts = time.time()
    logger.info("rag.search_start", query=query, business_id=business_id, k=k)

    vs = load_vector_store(business_id)
    if vs is None:
        logger.warning("rag.no_vector_store", business_id=business_id)
        return []

    results = vs.similarity_search_with_relevance_scores(query, k=k)

    chunks = []
    for doc, score in results:
        chunks.append({
            "content": doc.page_content,
            "score": round(score, 4),
            "source": doc.metadata.get("source", "unknown"),
            "chunk_index": doc.metadata.get("chunk_index", -1),
            "page": doc.metadata.get("page", 0),
        })

    duration_ms = int((time.time() - start_ts) * 1000)

    logger.info(
        "rag.search_complete",
        query=query,
        results=len(chunks),
        top_score=chunks[0]["score"] if chunks else 0,
        duration_ms=duration_ms,
    )

    # Log chunks to console for traceability
    for i, chunk in enumerate(chunks):
        logger.debug(
            "rag.chunk_retrieved",
            rank=i + 1,
            score=chunk["score"],
            source=chunk["source"],
            preview=chunk["content"][:150].replace("\n", " "),
        )

    write_audit_log(
        event_type="rag_retrieval",
        session_id=session_id,
        business_id=business_id,
        input_data={"query": query, "k": k},
        output_data={"results_count": len(chunks)},
        rag_chunks=chunks,
        duration_ms=duration_ms,
    )

    return chunks
