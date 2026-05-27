import os
from celery import Celery
from app.chat_utils import generate_ai_diagnosis
from app.vectorstore_utils import load_faiss_index, retrieve_similar_documents
from dotenv import load_dotenv

load_dotenv()

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
API_KEY = os.getenv("OPENAI_API_KEY")

celery_app = Celery("medichat_tasks", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

@celery_app.task(name="generate_diagnosis_task")
def generate_diagnosis_task(patient_name, past_summaries, current_complaint, session_id, images):
    if not API_KEY:
        raise Exception("OPENAI_API_KEY not configured")
        
    med_context = ""
    vectorstore = load_faiss_index(session_id)
    if vectorstore:
        docs = retrieve_similar_documents(vectorstore, current_complaint, k=4)
        med_context = "\n\n".join(d.page_content for d in docs)

    diagnosis_result = generate_ai_diagnosis(
        api_key=API_KEY,
        patient_name=patient_name,
        past_summaries=past_summaries,
        current_complaint=current_complaint,
        medical_context=med_context,
        images=images
    )
    
    return diagnosis_result
