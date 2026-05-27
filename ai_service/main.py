from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
import os
import uvicorn
from dotenv import load_dotenv

from app.chat_utils import generate_patient_history_report
from celery_worker import generate_diagnosis_task, celery_app
from celery.result import AsyncResult
from app.pdf_utils import extract_text_from_pdf
from app.vectorstore_utils import create_faiss_index, retrieve_similar_documents, cleanup_session_index
from langchain_text_splitters import RecursiveCharacterTextSplitter
import base64
from fastapi.middleware.cors import CORSMiddleware
from routes_patient import router as patient_router
from routes_doctor import router as doctor_router

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="MediChat AI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patient_router, prefix="/api/patient", tags=["patient"])
app.include_router(doctor_router, prefix="/api/doctor", tags=["doctor"])

# ── Pydantic Models ────────────────────────────────────────────────────────────

class HistoryReportRequest(BaseModel):
    patient_name: str
    past_summaries: List[str]

class HistoryReportResponse(BaseModel):
    report: str

class DiagnosisRequest(BaseModel):
    patient_name: str
    past_summaries: List[str]
    current_complaint: str
    session_id: str
    images: List[dict] = [] # list of dicts with 'data' and 'mime_type'

class DiagnosisResponse(BaseModel):
    task_id: str

class DiagnosisStatusResponse(BaseModel):
    task_id: str
    status: str
    diagnosis: Optional[str] = None
    
class DocumentProcessResponse(BaseModel):
    success: bool
    message: str

# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/api/ai/history_report", response_model=HistoryReportResponse)
async def history_report(req: HistoryReportRequest):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    try:
        report = generate_patient_history_report(API_KEY, req.patient_name, req.past_summaries)
        return {"report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/diagnosis", response_model=DiagnosisResponse)
async def diagnosis(req: DiagnosisRequest):
    try:
        # Enqueue Celery Task
        task = generate_diagnosis_task.delay(
            req.patient_name,
            req.past_summaries,
            req.current_complaint,
            req.session_id,
            req.images
        )
        return {"task_id": task.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/diagnosis/status/{task_id}", response_model=DiagnosisStatusResponse)
def get_diagnosis_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    if task_result.state == 'PENDING':
        return {"task_id": task_id, "status": "PENDING"}
    elif task_result.state == 'SUCCESS':
        return {"task_id": task_id, "status": "SUCCESS", "diagnosis": task_result.result}
    elif task_result.state == 'FAILURE':
        return {"task_id": task_id, "status": "FAILURE"}
    else:
        return {"task_id": task_id, "status": task_result.state}

# Note: /api/ai/process_documents might be better handled directly if possible, or we keep vectorstore in memory here.
# For a stateless service, building the index per request might be slow.
# Assuming session-based indexing for now, similar to original app.

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
