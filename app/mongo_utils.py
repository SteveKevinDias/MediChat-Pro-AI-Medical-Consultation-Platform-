from pymongo import MongoClient
from datetime import datetime
import hashlib
import uuid
import streamlit as st


@st.cache_resource
def _get_mongo_client():
    """Single cached MongoClient — shared connection pool across all requests."""
    return MongoClient(st.secrets["MONGO_URI"])


def get_db():
    """Return the medichat_pro MongoDB database using the pooled client."""
    return _get_mongo_client()["medichat_pro"]


# ── Patient Operations ────────────────────────────────────────────────────────

def find_or_create_patient(name: str, dob: str):
    """
    Find patient by (normalized name + DOB) or create a new record.
    Returns: (patient_id: str, is_new: bool)
    """
    db = get_db()
    name_norm = name.strip().lower()
    patient = db.patients.find_one({"name_normalized": name_norm, "dob": dob})
    if patient:
        return patient["patient_id"], False

    patient_id = str(uuid.uuid4())
    db.patients.insert_one({
        "patient_id":      patient_id,
        "name_normalized": name_norm,
        "display_name":    name.strip().title(),
        "dob":             dob,
        "created_at":      datetime.utcnow(),
    })
    return patient_id, True


def get_patient_info(patient_id: str):
    db = get_db()
    return db.patients.find_one({"patient_id": patient_id}, {"_id": 0})


# ── Conversation Summaries ────────────────────────────────────────────────────

def save_summary(patient_id: str, session_id: str, summary: str):
    """Save/update a clinical summary for a completed consultation."""
    db = get_db()
    db.conversation_summaries.update_one(
        {"session_id": session_id},
        {"$set": {
            "patient_id": patient_id,
            "session_id": session_id,
            "summary":    summary,
            "created_at": datetime.utcnow(),
        }},
        upsert=True,
    )


def get_patient_summaries(patient_id: str) -> list:
    """Return all past consultation summaries for a patient (oldest first)."""
    db = get_db()
    docs = list(
        db.conversation_summaries
        .find({"patient_id": patient_id}, {"_id": 0})
        .sort("created_at", 1)
    )
    return [d["summary"] for d in docs]


# ── Pending Reviews ───────────────────────────────────────────────────────────

def save_pending_review(
    patient_id:     str,
    patient_name:   str,
    dob:            str,
    session_id:     str,
    complaint:      str,
    ai_response:    str,
    history_report: str,
    images:         list = None,
) -> str:
    """Insert a new pending review document. Returns review_id."""
    db = get_db()
    review_id = str(uuid.uuid4())
    db.pending_reviews.insert_one({
        "review_id":          review_id,
        "patient_id":         patient_id,
        "patient_name":       patient_name,
        "dob":                dob,
        "session_id":         session_id,
        "complaint":          complaint,
        "ai_response":        ai_response,
        "history_report":     history_report,
        "images":             images or [],
        "status":             "pending",
        "created_at":         datetime.utcnow(),
        "reviewed_at":        None,
        "doctor_username":    None,
        "doctor_notes":       None,
        "finalized_response": None,
    })
    return review_id


def get_pending_reviews(status: str = None) -> list:
    """Return reviews filtered by status (None = all), newest first."""
    db = get_db()
    query = {} if status is None else {"status": status}
    return list(
        db.pending_reviews.find(query, {"_id": 0}).sort("created_at", -1)
    )


def get_review_by_session(session_id: str):
    db = get_db()
    return db.pending_reviews.find_one({"session_id": session_id}, {"_id": 0})


def get_patient_approved_reviews(patient_id: str) -> list:
    """
    Return all doctor-approved consultations for a patient, newest first.
    Used to show the patient their full consultation history.
    """
    db = get_db()
    return list(
        db.pending_reviews
        .find({"patient_id": patient_id, "status": "approved"}, {"_id": 0})
        .sort("reviewed_at", -1)
    )


def update_review(
    review_id:          str,
    status:             str,
    finalized_response: str  = None,
    doctor_username:    str  = None,
    doctor_notes:       str  = None,
):
    """Update a review's status and optional finalized response."""
    db = get_db()
    payload = {
        "status":          status,
        "reviewed_at":     datetime.utcnow(),
        "doctor_username": doctor_username,
        "doctor_notes":    doctor_notes,
    }
    if finalized_response is not None:
        payload["finalized_response"] = finalized_response
    db.pending_reviews.update_one({"review_id": review_id}, {"$set": payload})


# ── Doctor Auth ───────────────────────────────────────────────────────────────

def verify_doctor(username: str, password: str) -> bool:
    db = get_db()
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    return db.doctors.find_one({"username": username, "password_hash": pwd_hash}) is not None


def seed_doctors(doctors_dict: dict):
    """Upsert doctor credentials from a {username: password} dict."""
    db = get_db()
    for username, password in doctors_dict.items():
        pwd_hash = hashlib.sha256(password.encode()).hexdigest()
        db.doctors.update_one(
            {"username": username},
            {"$set": {
                "username":     username,
                "password_hash": pwd_hash,
                "updated_at":   datetime.utcnow(),
            }},
            upsert=True,
        )
