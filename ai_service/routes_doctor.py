from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.mongo_utils import (
    verify_doctor,
    get_pending_reviews,
    update_review,
    get_review_by_session,
    save_summary
)
from app.chat_utils import generate_conversation_summary
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

router = APIRouter()

class DoctorLoginRequest(BaseModel):
    username: str
    password: str

class DoctorLoginResponse(BaseModel):
    success: bool
    message: str

@router.post("/login", response_model=DoctorLoginResponse)
def login(req: DoctorLoginRequest):
    try:
        is_valid = verify_doctor(req.username, req.password)
        if is_valid:
            return {"success": True, "message": "Login successful"}
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue")
def get_queue(status: Optional[str] = None):
    try:
        reviews = get_pending_reviews(status)
        return reviews
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ReviewActionRequest(BaseModel):
    review_id: str
    action: str # "approve" or "reject"
    finalized_response: Optional[str] = None
    doctor_username: str
    doctor_notes: Optional[str] = None

@router.post("/action")
def review_action(req: ReviewActionRequest):
    try:
        if req.action not in ["approve", "reject"]:
            raise HTTPException(status_code=400, detail="Invalid action")

        status = "approved" if req.action == "approve" else "rejected"
        
        update_review(
            review_id=req.review_id,
            status=status,
            finalized_response=req.finalized_response,
            doctor_username=req.doctor_username,
            doctor_notes=req.doctor_notes
        )

        if status == "approved":
            # generate and save summary
            review = None
            db_reviews = get_pending_reviews() # Ideally fetch by review_id but get_review_by_session is easier or we need to add get_review_by_id
            for r in db_reviews:
                if r["review_id"] == req.review_id:
                    review = r
                    break
            
            if review:
                if not API_KEY:
                    print("Warning: Cannot generate summary due to missing API_KEY")
                else:
                    summary = generate_conversation_summary(
                        api_key=API_KEY,
                        patient_name=review["patient_name"],
                        complaint=review["complaint"],
                        finalized_response=req.finalized_response or review["ai_response"]
                    )
                    save_summary(review["patient_id"], review["session_id"], summary)

        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AskPdfRequest(BaseModel):
    session_id: str
    question: str

class AskPdfResponse(BaseModel):
    answer: str

from app.vectorstore_utils import load_faiss_index, retrieve_similar_documents
from app.chat_utils import answer_doctor_question

@router.post("/ask_pdf", response_model=AskPdfResponse)
def ask_pdf(req: AskPdfRequest):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    try:
        vectorstore = load_faiss_index(req.session_id)
        if not vectorstore:
            return {"answer": "No medical documents were uploaded or found for this session."}
        
        docs = retrieve_similar_documents(vectorstore, req.question, k=4)
        context = "\n\n".join(d.page_content for d in docs)
        
        answer = answer_doctor_question(API_KEY, req.question, context)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
