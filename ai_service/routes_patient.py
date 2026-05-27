from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Any
import os
from app.mongo_utils import (
    find_or_create_patient,
    get_patient_summaries,
    get_patient_approved_reviews,
    save_pending_review,
    get_pending_reviews,
    get_review_by_session,
    update_review,
    verify_doctor,
from app.pdf_utils import extract_text_from_pdf
from app.vectorstore_utils import create_faiss_index
from app.cache_utils import get_cached_summaries, set_cached_summaries
from app.s3_utils import upload_file_to_s3, download_file_from_s3
from langchain_text_splitters import RecursiveCharacterTextSplitter
from datetime import datetime
import io
from fastapi.responses import Response

router = APIRouter()

class PatientIdentifyRequest(BaseModel):
    name: str
    dob: str

class PatientIdentifyResponse(BaseModel):
    patient_id: str
    is_new: bool
    summaries: List[str]

@router.post("/identify", response_model=PatientIdentifyResponse)
def identify_patient(req: PatientIdentifyRequest):
    try:
        pid, is_new = find_or_create_patient(req.name, req.dob)
        
        # Check cache first
        summaries = get_cached_summaries(pid)
        if summaries is None:
            # Fetch from DB and cache it
            summaries = get_patient_summaries(pid)
            set_cached_summaries(pid, summaries)
            
        return {"patient_id": pid, "is_new": is_new, "summaries": summaries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload_pdf")
async def upload_pdf(session_id: str = Form(...), file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        object_name = f"{session_id}/{file.filename}"
        
        # Upload to S3/MinIO
        upload_success = upload_file_to_s3(file_bytes, object_name)
        if not upload_success:
            raise HTTPException(status_code=500, detail="Failed to upload file to S3")
        
        # Extract and Index
        with io.BytesIO(file_bytes) as f:
            text = extract_text_from_pdf(f)
        
        if text.strip():
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            chunks = splitter.split_text(text)
            create_faiss_index(chunks, session_id)
            
        return {"success": True, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download_pdf/{session_id}/{filename}")
async def download_pdf(session_id: str, filename: str):
    object_name = f"{session_id}/{filename}"
    file_bytes = download_file_from_s3(object_name)
    
    if file_bytes is not None:
        return Response(content=file_bytes, media_type="application/pdf")
        
    raise HTTPException(status_code=404, detail="File not found in S3")

class ConsultationSubmitRequest(BaseModel):
    patient_id: str
    patient_name: str
    dob: str
    session_id: str
    complaint: str
    ai_response: str
    history_report: str
    images: List[dict] = []
    pdf_files: List[str] = []

class ConsultationSubmitResponse(BaseModel):
    review_id: str

@router.post("/consultation", response_model=ConsultationSubmitResponse)
def submit_consultation(req: ConsultationSubmitRequest):
    try:
        rid = save_pending_review(
            patient_id=req.patient_id,
            patient_name=req.patient_name,
            dob=req.dob,
            session_id=req.session_id,
            complaint=req.complaint,
            ai_response=req.ai_response,
            history_report=req.history_report,
            images=req.images,
            pdf_files=req.pdf_files
        )
        return {"review_id": rid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{session_id}")
def get_status(session_id: str):
    try:
        review = get_review_by_session(session_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        # Ensure we can serialize datetimes if present in the review dict
        # Typically pymongo returns dict with datetime, so we may need to convert
        return review
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/approved_reviews/{patient_id}")
def get_approved_reviews(patient_id: str):
    try:
        reviews = get_patient_approved_reviews(patient_id)
        return reviews
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
