import os
import shutil
import hashlib
from typing import List

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

VECTOR_DB_ROOT = "vector_db"

# ── Load embedding model ONCE globally (expensive) ───────────────────────────
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2"
)


def _session_path(session_id: str) -> str:
    """Each session gets its own isolated subfolder."""
    return os.path.join(VECTOR_DB_ROOT, session_id)


def _compute_text_hash(texts: List[str]) -> str:
    return hashlib.md5("".join(texts).encode("utf-8")).hexdigest()


def create_faiss_index(texts: List[str], session_id: str) -> FAISS:
    """
    Create or reuse a FAISS index scoped to this session.
    - Same session + same content  → load existing index (no re-embedding)
    - Same session + new content   → rebuild index
    - Different session            → always isolated, no interference
    """
    session_dir = _session_path(session_id)
    os.makedirs(session_dir, exist_ok=True)

    index_path = os.path.join(session_dir, "index.faiss")
    hash_path  = os.path.join(session_dir, "text_hash.txt")
    new_hash   = _compute_text_hash(texts)

    # ── Reuse existing index if content unchanged ─────────────────────────────
    if os.path.exists(index_path) and os.path.exists(hash_path):
        with open(hash_path, "r") as f:
            old_hash = f.read().strip()

        if new_hash == old_hash:
            print("✅ Existing embeddings reused (no re-processing needed)")
            return FAISS.load_local(
                session_dir,
                embeddings,
                allow_dangerous_deserialization=True,
            )

        print("🔄 Updated documents detected — rebuilding embeddings…")

    # ── Build fresh index ─────────────────────────────────────────────────────
    vectorstore = FAISS.from_texts(texts, embeddings)
    vectorstore.save_local(session_dir)

    with open(hash_path, "w") as f:
        f.write(new_hash)

    return vectorstore

def load_faiss_index(session_id: str) -> FAISS:
    session_dir = _session_path(session_id)
    index_path = os.path.join(session_dir, "index.faiss")
    if os.path.exists(index_path):
        return FAISS.load_local(
            session_dir,
            embeddings,
            allow_dangerous_deserialization=True,
        )
    return None

def retrieve_similar_documents(vectorstore: FAISS, query: str, k: int = 4):
    """Similarity search — no embedding needed, just vector lookup."""
    return vectorstore.similarity_search(query, k=k)


def cleanup_session_index(session_id: str):
    """
    Delete the FAISS index for a completed/expired session.
    Call this after the consultation is submitted to free disk space.
    """
    session_dir = _session_path(session_id)
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir, ignore_errors=True)