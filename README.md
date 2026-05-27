# 🏥 MediChat Pro — AI Medical Consultation Platform

> An intelligent, human-in-the-loop medical consultation platform where patients describe their symptoms and receive AI-generated diagnoses reviewed and approved by a licensed doctor before delivery.

![React](https://img.shields.io/badge/React-18-blue?logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green?logo=mongodb)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 🌟 Key Features

### 👤 Patient Portal
- **Identity-based History Retrieval** — Patients log in with name + date of birth; all past consultation history is automatically loaded from MongoDB
- **AI Medical History Report** — Synthesized summary of all previous visits generated on every login
- **Symptom Consultation** — Patients describe their current complaint in detail
- **📸 Photo Upload** — Patients can upload photos (rashes, wounds, skin conditions) for visual AI analysis
- **📄 Medical Document Upload** — Upload external PDFs (lab reports, prescriptions) for RAG-based context extraction
- **Real-time Status Tracking** — Track whether the doctor has reviewed and approved the consultation

### 👨‍⚕️ Doctor Dashboard
- **Secure Login** — SHA-256 hashed doctor credentials stored in MongoDB
- **Review Queue** — View all pending, approved, and rejected consultations
- **Approve As-Is** — One-click approval of AI-generated responses
- **Edit & Approve** — Modify the AI response before delivering it to the patient
- **Reject with Notes** — Return consultations with feedback for resubmission
- **Patient Photo Viewer** — Visual grid display of patient-uploaded images
- **Full History Context** — AI's history report shown alongside each review

### 🤖 AI Engine
- **Vision AI** — GPT-4.1-nano via EURI AI analyses patient-uploaded photos alongside the text complaint
- **Structured Diagnosis** — Every AI response includes: Assessment, Likely Diagnosis, Medications (with dosage), Tests, Red Flags, Care Instructions, and Clinic Visit guidance (only if physical exam is needed)
- **RAG over PDFs** — FAISS vector store retrieves relevant chunks from uploaded medical documents for context-aware responses
- **Persistent Patient Memory** — Past consultation summaries are stored in MongoDB and injected into every new AI prompt

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         React Frontend (Vite)                   │
│   ┌──────────────────┐           ┌───────────────────────────┐  │
│   │  Patient Portal  │           │    Doctor Dashboard       │  │
│   │  (React UI)      │           │  (Approve / Edit / Reject)│  │
│   └────────┬─────────┘           └────────────┬──────────────┘  │
└────────────┼────────────────────────────────── ┼ ───────────────┘
             │           REST API (JSON)         │
     ┌───────▼──────────────────────────────────▼───────┐
     │                  FastAPI Backend                 │
     │  routes_patient.py │  routes_doctor.py           │
     │  chat_utils.py     │  mongo_utils.py  │ pdf_utils│
     └────────┬─────────────────┬──────────────┬────────┘
              │                 │              │
     ┌────────▼──────┐  ┌───────▼─────┐ ┌────▼──────────┐
     │  EURI AI API  │  │  MongoDB    │ │  FAISS        │
     │  GPT-4.1-nano │  │  Atlas      │ │  (per-session │
     │  (text+vision)│  │  (persist.) │ │   vector DB)  │
     └───────────────┘  └─────────────┘ └───────────────┘
```

### Human-in-the-Loop Workflow

```
Patient submits complaint + photos
            ↓
    AI generates diagnosis
    (vision model if photos present)
            ↓
   Saved to MongoDB as "pending"
            ↓
   Doctor reviews in dashboard
            ↓
     Approve / Edit / Reject
            ↓
   Patient sees ONLY doctor-verified response
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React, Vite |
| **Backend** | FastAPI (Python) |
| **AI Model** | GPT-4.1-nano via EURI AI (OpenAI-compatible API) |
| **Vision AI** | Multimodal GPT-4.1-nano (base64 image input) |
| **Embeddings** | `sentence-transformers/all-mpnet-base-v2` (HuggingFace) |
| **Vector Store** | FAISS (per-session isolated indexes) |
| **Database** | MongoDB Atlas |
| **PDF Processing** | pypdf |
| **LLM Framework** | LangChain |

---

## 📁 Project Structure

```
medichat_pro/
├── ai_service/                # FastAPI Backend
│   ├── app/
│   │   ├── chat_utils.py      # AI model, vision model, prompts
│   │   ├── mongo_utils.py     # MongoDB CRUD operations
│   │   ├── vectorstore_utils.py # FAISS index management
│   │   └── pdf_utils.py       # PDF text extraction
│   ├── main.py                # FastAPI app & routing
│   ├── routes_doctor.py
│   ├── routes_patient.py
│   └── requirements.txt
├── frontend/                  # React Frontend
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── sample_data/               # Sample medical history PDFs
└── README.md                  # Project documentation
```

---

## ⚡ Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/medichat-pro.git
cd medichat-pro
```

### 2. Configure Environment Variables
In the `ai_service` directory, create a `.env` file:
```env
OPENAI_API_KEY=your-euri-api-key
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/
```

### 3. Start the Backend (FastAPI)
```bash
cd ai_service
pip install -r requirements.txt
python main.py
# Backend will run on http://localhost:8000
```

### 4. Start the Frontend (React)
Open a new terminal window:
```bash
cd frontend
npm install
npm run dev
# Frontend will run on http://localhost:5173
```

---

## 🔑 Environment Variables

| Key | Description | Where to get |
|---|---|---|
| `OPENAI_API_KEY` | EURI AI API key for GPT-4.1-nano | [euri.ai](https://euri.ai) |
| `MONGO_URI` | MongoDB Atlas connection string | [mongodb.com/atlas](https://mongodb.com/atlas) |

---

## 📊 MongoDB Collections

| Collection | Purpose |
|---|---|
| `patients` | Patient records (name, DOB, patient_id) |
| `conversation_summaries` | Clinical summaries per session (used for AI context) |
| `pending_reviews` | Full consultation records including AI response, images, status |
| `doctors` | Hashed doctor credentials |

---

## 🔒 Security Notes

- Patient identity is verified by name + date of birth combination
- Doctor passwords are stored as SHA-256 hashes in MongoDB
- Patients **never** see raw AI output — all responses are doctor-verified first
- Per-session FAISS indexes are automatically cleaned up

---

## 📈 Future Improvements (Scaling)

- [ ] OTP-based patient authentication
- [ ] Migrate from local FAISS to managed Vector DB (e.g., Pinecone)
- [ ] Add Redis caching for session data and summaries
- [ ] Message queue (Celery/RabbitMQ) for async LLM generation
- [ ] Migrate image/PDF storage to AWS S3
- [ ] Containerize and deploy via Docker/Kubernetes
- [ ] Unit and integration tests

---

## 👨‍💻 Author

Built with ❤️ as a portfolio project demonstrating full-stack AI development with real-world healthcare workflows.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

> ⚠️ **Disclaimer:** MediChat Pro is a portfolio/demonstration project. It is not a licensed medical device and should not be used for real medical diagnosis or treatment decisions.
