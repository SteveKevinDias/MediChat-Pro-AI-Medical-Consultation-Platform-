import streamlit as st
import uuid
import base64
from datetime import date, datetime

from app.mongo_utils import (
    find_or_create_patient,
    get_patient_summaries,
    get_patient_approved_reviews,
    save_pending_review,
    get_pending_reviews,
    get_review_by_session,
    update_review,
    verify_doctor,
    seed_doctors,
    save_summary,
)
from app.chat_utils import (
    get_chat_model,
    generate_patient_history_report,
    generate_ai_diagnosis,
    generate_conversation_summary,
)
from app.pdf_utils import extract_text_from_pdf
from app.vectorstore_utils import create_faiss_index, retrieve_similar_documents, cleanup_session_index
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MediChat Pro",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

* {
    box-sizing: border-box;
}

/* Base font application without breaking Streamlit icons */
html, body, div, span, p, h1, h2, h3, h4, h5, h6, li, button, input, label {
    font-family: 'Inter', sans-serif;
}

/* Ensure Material Symbols (which Streamlit uses for icons) use their correct font */
.material-symbols-rounded, [data-testid="stIconMaterial"], [class*="stIcon"] {
    font-family: 'Material Symbols Rounded' !important;
}

/* ─ Background ─ */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #060b18 0%, #0d1b2a 60%, #07101f 100%) !important;
    min-height: 100vh;
}
[data-testid="stHeader"]  { background: transparent !important; }
[data-testid="stSidebar"] { display: none !important; }
section.main > div { padding-top: 0.5rem !important; }

/* ─ Fix Streamlit column gap so content doesn't bleed ─ */
[data-testid="stColumns"] { gap: 1.25rem !important; align-items: flex-start !important; }
[data-testid="stColumn"]  { min-width: 0 !important; }

/* ─ Global text wrapping for typography only ─ */
p, h1, h2, h3, h4, li {
    word-break: break-word;
    white-space: pre-wrap;
}

/* ─ Brand topbar ─ */
.topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 1rem 2rem;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 1rem;
}
.brand {
    font-size: 1.8rem; font-weight: 800;
    background: linear-gradient(135deg, #00d4ff, #a855f7);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    white-space: nowrap;
    text-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
    letter-spacing: -0.02em;
}

/* ─ Hero ─ */
div[data-testid="stMarkdownContainer"] .hero { text-align: center; padding: 3.5rem 1rem 2.5rem; }
div[data-testid="stMarkdownContainer"] .hero h1 {
    font-size: clamp(3.5rem, 8vw, 6rem) !important;
    font-weight: 900 !important; line-height: 1.1 !important;
    background: linear-gradient(135deg, #00d4ff 20%, #a855f7 80%) !important;
    -webkit-background-clip: text !important; -webkit-text-fill-color: transparent !important; background-clip: text !important;
    margin: 0 0 1rem 0 !important;
    text-shadow: 0 0 40px rgba(168, 85, 247, 0.4) !important;
    letter-spacing: -0.04em !important;
}
div[data-testid="stMarkdownContainer"] .hero p { font-size: 1.4rem !important; color: #94a3b8 !important; margin: 0 !important; line-height: 1.6 !important; }

/* ─ Portal Cards ─ */
.portal-card {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 24px; padding: clamp(1.5rem, 4vw, 3rem) clamp(1.5rem, 4vw, 2.5rem); text-align: center;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); backdrop-filter: blur(20px);
}
.portal-card.p-card:hover { border-color: rgba(0,212,255,0.45); box-shadow: 0 0 50px rgba(0,212,255,0.1); transform: translateY(-5px); }
.portal-card.d-card:hover { border-color: rgba(168,85,247,0.45); box-shadow: 0 0 50px rgba(168,85,247,0.1); transform: translateY(-5px); }
.portal-icon  { font-size: 4rem; margin-bottom: 1rem; display: block; }
.portal-title { font-size: 1.5rem; font-weight: 700; color: #f1f5f9; margin-bottom: 0.75rem; }
.portal-desc  { font-size: 0.925rem; color: #64748b; line-height: 1.7; }

/* ─ Step Indicator ─ */
.steps {
    display: flex; align-items: center; justify-content: center;
    gap: 0; padding: 1.25rem 0.5rem 1.5rem; flex-wrap: wrap; row-gap: 0.75rem;
}
.step-col  { display: flex; flex-direction: column; align-items: center; }
.step-dot  {
    width: 34px; height: 34px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.8rem; font-weight: 700; border: 2px solid;
    transition: all 0.3s; flex-shrink: 0;
}
.step-dot.done   { background: #10b981; border-color: #10b981; color: white; }
.step-dot.active { background: rgba(0,212,255,0.15); border-color: #00d4ff; color: #00d4ff; }
.step-dot.todo   { background: transparent; border-color: #1e293b; color: #475569; }
.step-label { font-size: 0.72rem; color: #64748b; margin-top: 0.3rem; white-space: nowrap; }
.step-line  { width: 48px; height: 2px; background: #1e293b; margin: 0 2px; flex-shrink: 0; }
.step-line.done { background: #10b981; }

/* ─ Content Cards ─ */
.card {
    background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px; padding: 1.5rem; margin-bottom: 1.25rem;
}
.card-cyan   { border-color: rgba(0,212,255,0.25);  background: rgba(0,212,255,0.04); }
.card-purple { border-color: rgba(168,85,247,0.25); background: rgba(168,85,247,0.04); }
.card-green  { border-color: rgba(16,185,129,0.25); background: rgba(16,185,129,0.04); }
.card-orange { border-color: rgba(245,158,11,0.25); background: rgba(245,158,11,0.04); }
.card-red    { border-color: rgba(239,68,68,0.25);  background: rgba(239,68,68,0.04); }

.card h3 {
    font-size: 0.85rem; font-weight: 600; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 0.08em;
    margin-bottom: 0.75rem; margin-top: 0;
}

/* ─ Fix markdown heading colors inside cards ─ */
div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3 {
    color: #e2e8f0 !important;
    margin-top: 1rem !important;
    margin-bottom: 0.5rem !important;
    line-height: 1.4 !important;
    font-size: 1rem !important;
}
div[data-testid="stMarkdownContainer"] h2 { font-size: 1.05rem !important; }
div[data-testid="stMarkdownContainer"] p  { color: #cbd5e1; line-height: 1.7; }
div[data-testid="stMarkdownContainer"] li { color: #cbd5e1; line-height: 1.7; margin-bottom: 0.25rem; }
div[data-testid="stMarkdownContainer"] strong { color: #f1f5f9 !important; }

/* ─ Badges ─ */
.badge {
    display: inline-flex; align-items: center;
    border-radius: 20px; padding: 0.25rem 0.85rem;
    font-size: 0.78rem; font-weight: 600;
    white-space: nowrap; flex-shrink: 0;
}
.badge-pending  { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }
.badge-approved { background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.3); }
.badge-rejected { background: rgba(239,68,68,0.15);  color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }

/* ─ Review Cards ─ */
.review-card {
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px; padding: 1.25rem 1.5rem;
    margin-bottom: 1rem; transition: border-color 0.2s;
}
.review-card:hover { border-color: rgba(255,255,255,0.12); }
.review-meta {
    font-size: 0.82rem; color: #64748b;
    margin-bottom: 0.6rem; line-height: 1.5;
    word-break: break-word;
}
.review-header {
    display: flex; justify-content: space-between; align-items: flex-start;
    gap: 0.75rem; margin-bottom: 0.75rem; flex-wrap: wrap;
}
.review-patient-info { min-width: 0; flex: 1; }
.review-patient-name { font-size: 1.05rem; font-weight: 700; color: #f1f5f9; display: block; }
.review-dob          { font-size: 0.82rem; color: #64748b; display: block; margin-top: 0.1rem; }
.review-complaint {
    color: #e2e8f0; font-size: 0.95rem; line-height: 1.65;
    margin-bottom: 0.75rem; word-break: break-word;
}

/* ─ Streamlit form + input overrides ─ */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stDateInput > div > div > input {
    -webkit-appearance: none !important;
    -moz-appearance: none !important;
    appearance: none !important;
    background: rgba(255,255,255,0.05) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 10px !important;
    color: #f1f5f9 !important;
    padding: 0.6rem 0.85rem !important;
    line-height: 1.5 !important;
}
.stButton > button {
    border-radius: 10px !important; font-weight: 600 !important;
    transition: all 0.2s !important; border: none !important;
    white-space: normal !important; word-wrap: break-word !important;
    height: auto !important; padding: 0.55rem 1rem !important;
    line-height: 1.4 !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #00d4ff, #0099cc) !important;
    color: #060b18 !important;
}
[data-testid="stForm"]   { background: transparent !important; border: none !important; }
.stSuccess, .stInfo, .stWarning, .stError {
    border-radius: 10px !important;
    word-wrap: break-word !important;
}

/* ─ Expander content ─ */
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    color: #e2e8f0 !important;
}
[data-testid="stExpander"] > div {
    padding: 1rem 0.75rem !important;
    overflow-wrap: break-word !important;
}

/* ─ Metric boxes ─ */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px; padding: 1rem !important;
}
[data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 0.82rem !important; }
[data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 1.6rem !important; }

/* ─ Tab labels ─ */
[data-testid="stTabs"] [role="tab"] {
    color: #94a3b8 !important; font-weight: 600 !important;
    font-size: 0.88rem !important;
    white-space: nowrap !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] { color: #00d4ff !important; }
</style>
""", unsafe_allow_html=True)


# ── Resources ──────────────────────────────────────────────────────────────────
def get_api_key():
    return st.secrets["OPENAI_API_KEY"]


@st.cache_resource
def _dummy_init():
    return True  # keeps cache_resource pattern for doctor seeding


@st.cache_resource
def init_doctors():
    try:
        docs = {k: v for k, v in st.secrets.get("doctors", {}).items()}
        if docs:
            seed_doctors(docs)
    except Exception:
        pass


init_doctors()
_dummy_init()
chat_model = get_api_key()  # now just the API key string


# ── Session State Defaults ─────────────────────────────────────────────────────
_defaults = {
    "mode":           "landing",    # landing | patient | doctor
    "p_step":         "identify",   # patient sub-steps
    "patient_id":     None,
    "patient_name":   None,
    "patient_dob":    None,
    "is_new":         False,
    "summaries":      [],
    "hist_report":    None,
    "session_id":     None,
    "review_id":      None,
    "vectorstore":    None,
    "patient_images": [],           # base64-encoded images from patient
    "doc_in":         False,        # doctor logged in
    "doc_user":       None,
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Helpers ────────────────────────────────────────────────────────────────────
def go(mode, reset_patient=False):
    st.session_state.mode = mode
    if reset_patient:
        for k, v in _defaults.items():
            if k not in ("doc_in", "doc_user"):
                st.session_state[k] = v
        st.session_state.mode = mode
    st.rerun()


def step_indicator(current):
    steps = [
        ("1", "Identify",      "identify"),
        ("2", "History",       "history"),
        ("3", "Consultation",  "consultation"),
        ("4", "Status",        "submitted"),
    ]
    order = [s[2] for s in steps]
    cur_i = order.index(current) if current in order else 0

    cols_items = []
    for i, (num, label, key) in enumerate(steps):
        if i < cur_i:
            cls = "done"; sym = "✓"
        elif i == cur_i:
            cls = "active"; sym = num
        else:
            cls = "todo"; sym = num

        cols_items.append(
            f'<div class="step-col">'
            f'<div class="step-dot {cls}">{sym}</div>'
            f'<div class="step-label">{label}</div>'
            f'</div>'
        )
        if i < len(steps) - 1:
            line_cls = "done" if i < cur_i else ""
            cols_items.append(f'<div class="step-line {line_cls}" style="margin-bottom:18px"></div>')

    st.markdown(
        f'<div class="steps">{"".join(cols_items)}</div>',
        unsafe_allow_html=True,
    )


def topbar(back_label="← Back", back_mode="landing", show_back=True):
    c1, c2 = st.columns([1, 5])
    with c1:
        if show_back and st.button(back_label, key="topbar_back"):
            go(back_mode, reset_patient=(back_mode == "landing"))
    with c2:
        st.markdown('<div class="brand">🏥 MediChat Pro</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  LANDING PAGE
# ══════════════════════════════════════════════════════════════════════════════
def show_landing():
    st.markdown("""
    <div class="hero">
        <h1>MediChat Pro</h1>
        <p>Intelligent medical consultations with doctor-verified AI responses</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="portal-card p-card">
            <span class="portal-icon">🧑‍⚕️</span>
            <div class="portal-title">Patient Portal</div>
            <div class="portal-desc">
                Access your medical history, describe your symptoms, and receive
                AI-generated assessments reviewed by a licensed doctor.
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Enter Patient Portal →", key="btn_patient", use_container_width=True):
            go("patient")

    with col2:
        st.markdown("""
        <div class="portal-card d-card">
            <span class="portal-icon">👨‍⚕️</span>
            <div class="portal-title">Doctor Dashboard</div>
            <div class="portal-desc">
                Review pending AI-generated patient assessments, approve or edit
                responses, and manage your patient queue.
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Doctor Login →", key="btn_doctor", use_container_width=True):
            go("doctor")

    st.markdown("""
    <div style="text-align:center;padding:2rem 0 1rem;color:#1e293b;font-size:0.85rem;">
        Powered by Euri AI · Secured with MongoDB · Human-in-the-Loop
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PATIENT PORTAL
# ══════════════════════════════════════════════════════════════════════════════
def show_patient():
    topbar("← Home", "landing")
    step_indicator(st.session_state.p_step)

    step = st.session_state.p_step
    if step == "identify":
        patient_identify()
    elif step == "history":
        patient_history()
    elif step == "consultation":
        patient_consultation()
    elif step == "submitted":
        patient_submitted()


# ─── Step 1 : Identify ────────────────────────────────────────────────────────
def patient_identify():
    st.markdown("## 👤 Identify Yourself")
    st.markdown('<p style="color:#64748b">We use your name and date of birth to securely retrieve your medical history.</p>', unsafe_allow_html=True)

    with st.form("identify_form"):
        name = st.text_input("Full Name", placeholder="e.g. Priya Sharma")
        dob  = st.date_input(
            "Date of Birth",
            value=date(1990, 1, 1),
            min_value=date(1900, 1, 1),
            max_value=date.today(),
        )
        submitted = st.form_submit_button("Continue →", use_container_width=True)

    if submitted:
        if not name.strip():
            st.error("Please enter your full name.")
            return
        with st.spinner("Looking up your records…"):
            pid, is_new = find_or_create_patient(name.strip(), str(dob))
            summaries   = get_patient_summaries(pid)

        st.session_state.patient_id   = pid
        st.session_state.patient_name = name.strip().title()
        st.session_state.patient_dob  = str(dob)
        st.session_state.is_new       = is_new
        st.session_state.summaries    = summaries
        st.session_state.session_id   = str(uuid.uuid4())
        st.session_state.hist_report  = None   # will be generated in next step
        st.session_state.p_step       = "history"
        st.rerun()


# ─── Step 2 : History ─────────────────────────────────────────────────────────
def patient_history():
    name = st.session_state.patient_name
    st.markdown(f"## 👋 Welcome, {name}")

    # Generate AI history report once and cache in session
    if st.session_state.hist_report is None:
        with st.spinner("Generating your medical history report…"):
            report = generate_patient_history_report(
                st.secrets["OPENAI_API_KEY"],
                name,
                st.session_state.summaries,
            )
        st.session_state.hist_report = report

    if st.session_state.is_new:
        st.info("🆕 **New Patient** — No previous records found. Your history will be built after your first consultation.")
    else:
        n = len(st.session_state.summaries)
        st.success(f"✅ **Returning Patient** — {n} previous consultation(s) found.")

    # ── AI-synthesised history report ──────────────────────────────────────────
    st.markdown('<div class="card card-cyan">', unsafe_allow_html=True)
    st.markdown("### 📋 Your Medical History Report")
    st.markdown(st.session_state.hist_report)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Previous doctor-approved consultations (directly visible) ──────────────
    if not st.session_state.is_new:
        past_reviews = get_patient_approved_reviews(st.session_state.patient_id)
        if past_reviews:
            st.markdown("---")
            st.markdown("### 📂 Previous Consultations")
            st.caption("All past consultations reviewed and approved by a licensed doctor.")

            for i, rev in enumerate(past_reviews):
                reviewed_at = rev.get("reviewed_at")
                date_str = reviewed_at.strftime("%d %b %Y") if reviewed_at else "Date unknown"
                doctor   = rev.get("doctor_username", "Doctor")
                final    = rev.get("finalized_response") or rev.get("ai_response", "")
                notes    = rev.get("doctor_notes", "")
                snippet  = rev['complaint'][:80] + ("..." if len(rev['complaint']) > 80 else "")

                with st.expander(
                    f"📅  {date_str}  ·  Dr. {doctor}  ·  \"{snippet}\"",
                    expanded=(i == 0),   # most recent open by default
                ):
                    col_a, col_b = st.columns([3, 1])

                    with col_b:
                        st.markdown(
                            f'<div class="card card-green" style="text-align:center;padding:1rem">'
                            f'<div style="font-size:2rem">✅</div>'
                            f'<div style="color:#10b981;font-weight:700;margin-top:0.5rem">Doctor Approved</div>'
                            f'<div style="color:#64748b;font-size:0.8rem;margin-top:0.3rem">{date_str}</div>'
                            f'<div style="color:#64748b;font-size:0.8rem">Dr. {doctor}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

                    with col_a:
                        st.markdown("**Chief Complaint:**")
                        st.markdown(
                            f'<div class="card" style="padding:0.9rem;margin-bottom:1rem;color:#cbd5e1">'
                            f'{rev["complaint"]}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown("**Doctor-Verified Response:**")
                        st.markdown(final)

                        if notes:
                            st.markdown(
                                f'<div class="card card-orange" style="padding:0.9rem;margin-top:0.75rem">'
                                f'🗒️ <strong>Doctor\'s Note:</strong> {notes}'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

    st.markdown("---")
    if st.button("Proceed to New Consultation →", use_container_width=True):
        st.session_state.p_step = "consultation"
        st.rerun()


# ─── Step 3 : Consultation ────────────────────────────────────────────────────
def patient_consultation():
    st.markdown("## 💬 Describe Your Symptoms")

    col1, col2 = st.columns([2, 1])

    with col2:
        st.markdown('<div class="card card-purple">', unsafe_allow_html=True)
        st.markdown("### 📁 Upload Medical Documents *(optional)*")
        st.caption("X-rays, lab reports, prescriptions, etc.")
        uploaded = st.file_uploader(
            "Upload PDFs",
            type=["pdf"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="pdf_upload",
        )
        if uploaded and st.button("⚙️ Process Documents", key="process_docs"):
            with st.spinner("Extracting text…"):
                texts = [extract_text_from_pdf(f) for f in uploaded]
                splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                chunks = []
                for t in texts:
                    chunks.extend(splitter.split_text(t))
                st.session_state.vectorstore = create_faiss_index(chunks, st.session_state.session_id)
            st.success(f"✅ {len(uploaded)} document(s) processed")
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Image Upload ───────────────────────────────────────────────────
        st.markdown('<div class="card card-cyan" style="margin-top:1rem">', unsafe_allow_html=True)
        st.markdown("### 📸 Upload Photos *(optional)*")
        st.caption("Rash, wound, swelling, skin condition — anything visible the doctor should see.")
        img_files = st.file_uploader(
            "Upload images",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="img_upload",
        )
        if img_files:
            st.success(f"📷 {len(img_files)} photo(s) ready to submit")
            preview_cols = st.columns(min(len(img_files), 3))
            for i, img in enumerate(img_files):
                with preview_cols[i % 3]:
                    st.image(img, use_container_width=True, caption=img.name)
        st.markdown("</div>", unsafe_allow_html=True)

    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### ✍️ Your Current Complaint")
        complaint = st.text_area(
            "Describe your symptoms, concerns, or questions in detail:",
            height=220,
            placeholder=(
                "e.g. I've been experiencing chest pain for the past 3 days, "
                "especially when climbing stairs. I also feel slightly breathless..."
            ),
            label_visibility="collapsed",
            key="complaint_input",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("🚀 Submit for Doctor Review", key="submit_consult", use_container_width=True):
            if not complaint.strip():
                st.error("Please describe your symptoms before submitting.")
                return

            # Encode uploaded images FIRST (needed by both AI call and MongoDB save)
            encoded_images = []
            if img_files:
                for img in img_files:
                    img.seek(0)
                    encoded_images.append({
                        "filename":  img.name,
                        "mime_type": img.type,
                        "data":      base64.b64encode(img.read()).decode("utf-8"),
                    })

            with st.spinner("🤖 AI is analyzing your case…"):
                # Build PDF context if vectorstore exists
                med_context = ""
                if st.session_state.vectorstore:
                    docs = retrieve_similar_documents(st.session_state.vectorstore, complaint, k=4)
                    med_context = "\n\n".join(d.page_content for d in docs)

                ai_resp = generate_ai_diagnosis(
                    st.secrets["OPENAI_API_KEY"],
                    st.session_state.patient_name,
                    st.session_state.summaries,
                    complaint,
                    med_context,
                    images  = encoded_images,
                )

            with st.spinner("📤 Sending to doctor queue…"):

                rid = save_pending_review(
                    patient_id     = st.session_state.patient_id,
                    patient_name   = st.session_state.patient_name,
                    dob            = st.session_state.patient_dob,
                    session_id     = st.session_state.session_id,
                    complaint      = complaint,
                    ai_response    = ai_resp,
                    history_report = st.session_state.hist_report or "",
                    images         = encoded_images,
                )
            st.session_state.review_id    = rid
            st.session_state.patient_images = []

            # Clean up per-session FAISS index now that submission is done
            cleanup_session_index(st.session_state.session_id)
            st.session_state.vectorstore = None

            st.session_state.p_step = "submitted"
            st.rerun()


# ─── Step 4 : Submitted / Status ─────────────────────────────────────────────
def patient_submitted():
    st.markdown(f"## 📬 Consultation Status — {st.session_state.patient_name}")

    review = get_review_by_session(st.session_state.session_id)

    if not review:
        st.error("Could not find your submission. Please try again.")
        return

    status = review.get("status", "pending")

    if status == "pending":
        st.markdown("""
        <div class="card card-orange">
            <h3>⏳ Awaiting Doctor Review</h3>
            <p style="color:#e2e8f0">Your consultation has been submitted and is in the doctor's queue.
            A licensed physician will review the AI-generated assessment and either approve or adjust it
            before you receive your response. Please check back shortly.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔄 Refresh Status", key="refresh_status"):
            st.rerun()

    elif status == "approved":
        st.markdown("""
        <div class="card card-green">
            <h3>✅ Doctor Reviewed & Approved</h3>
        </div>
        """, unsafe_allow_html=True)

        final_resp = review.get("finalized_response") or review.get("ai_response", "")
        doc_user   = review.get("doctor_username", "Doctor")
        reviewed_at = review.get("reviewed_at")
        time_str    = reviewed_at.strftime("%d %b %Y, %H:%M") if reviewed_at else ""

        st.markdown(f'<p style="color:#64748b;font-size:0.85rem">Reviewed by Dr. {doc_user} · {time_str}</p>', unsafe_allow_html=True)

        st.markdown('<div class="card card-cyan">', unsafe_allow_html=True)
        st.markdown("### 📄 Doctor-Verified Medical Response")
        st.markdown(final_resp)
        st.markdown("</div>", unsafe_allow_html=True)

        if review.get("doctor_notes"):
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 🗒️ Doctor's Note")
            st.markdown(review["doctor_notes"])
            st.markdown("</div>", unsafe_allow_html=True)

    elif status == "rejected":
        st.markdown("""
        <div class="card card-red">
            <h3>❌ Consultation Returned</h3>
            <p style="color:#e2e8f0">The doctor has returned this consultation. Please start a new one with additional details.</p>
        </div>
        """, unsafe_allow_html=True)
        if review.get("doctor_notes"):
            st.info(f"**Doctor's note:** {review['doctor_notes']}")

    st.divider()
    if st.button("🔁 Start New Consultation", key="new_consult"):
        st.session_state.p_step         = "consultation"
        st.session_state.session_id     = str(uuid.uuid4())
        st.session_state.review_id      = None
        st.session_state.vectorstore    = None
        st.session_state.patient_images = []
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  DOCTOR PORTAL
# ══════════════════════════════════════════════════════════════════════════════
def show_doctor():
    if not st.session_state.doc_in:
        doctor_login()
    else:
        doctor_dashboard()


def doctor_login():
    topbar("← Home", "landing")
    st.markdown("## 🔐 Doctor Login")

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown('<div class="card card-purple">', unsafe_allow_html=True)
        with st.form("doctor_login_form"):
            username = st.text_input("Username", placeholder="e.g. dr_smith")
            password = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Login →", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if login_btn:
        with st.spinner("Verifying credentials…"):
            ok = verify_doctor(username.strip(), password)
        if ok:
            st.session_state.doc_in   = True
            st.session_state.doc_user = username.strip()
            st.rerun()
        else:
            st.error("❌ Invalid username or password.")


def doctor_dashboard():
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("← Logout", key="doc_logout"):
            st.session_state.doc_in   = False
            st.session_state.doc_user = None
            go("landing")
    with c2:
        st.markdown(
            f'<div class="brand">🏥 MediChat Pro &nbsp;·&nbsp; '
            f'<span style="font-size:0.9rem;color:#64748b;font-weight:400">'
            f'Dr. {st.session_state.doc_user}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("## 📋 Patient Review Dashboard")

    # Counts
    all_reviews     = get_pending_reviews()
    pending_list    = [r for r in all_reviews if r["status"] == "pending"]
    approved_list   = [r for r in all_reviews if r["status"] == "approved"]
    rejected_list   = [r for r in all_reviews if r["status"] == "rejected"]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Reviews",    len(all_reviews))
    m2.metric("⏳ Pending",       len(pending_list))
    m3.metric("✅ Approved",      len(approved_list))
    m4.metric("❌ Rejected",      len(rejected_list))

    if st.button("🔄 Refresh", key="refresh_dash"):
        st.rerun()

    tab_pending, tab_approved, tab_rejected = st.tabs([
        f"⏳ Pending ({len(pending_list)})",
        f"✅ Approved ({len(approved_list)})",
        f"❌ Rejected ({len(rejected_list)})",
    ])

    with tab_pending:
        if not pending_list:
            st.info("🎉 No pending reviews — all caught up!")
        for rev in pending_list:
            render_review_card(rev, allow_actions=True)

    with tab_approved:
        if not approved_list:
            st.info("No approved reviews yet.")
        for rev in approved_list:
            render_review_card(rev, allow_actions=False)

    with tab_rejected:
        if not rejected_list:
            st.info("No rejected reviews.")
        for rev in rejected_list:
            render_review_card(rev, allow_actions=False)


def render_review_card(rev: dict, allow_actions: bool):
    rid      = rev["review_id"]
    status   = rev["status"]
    ts       = rev.get("created_at")
    ts_str   = ts.strftime("%d %b %Y  %H:%M") if ts else ""
    badge_cls = f"badge-{status}"

    with st.container():
        st.markdown(f"""
        <div class="review-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem">
                <div>
                    <span style="font-size:1.1rem;font-weight:700;color:#f1f5f9">{rev['patient_name']}</span>
                    &nbsp;<span style="color:#64748b;font-size:0.85rem">DOB: {rev['dob']}</span>
                </div>
                <span class="badge {badge_cls}">{status.capitalize()}</span>
            </div>
            <div class="review-meta">Submitted: {ts_str} &nbsp;|&nbsp; Session: {rev['session_id'][:8]}…</div>
            <div style="color:#94a3b8;font-size:0.8rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;margin-bottom:0.3rem">Chief Complaint</div>
            <div class="review-complaint">{rev['complaint']}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📄 View AI Response & History Report"):
            st.markdown("**AI-Generated Response:**")
            st.markdown(rev.get("ai_response", "—"))
            if rev.get("history_report"):
                st.divider()
                st.markdown("**Patient History Report (context used by AI):**")
                st.markdown(rev["history_report"])

        # ── Patient Photos ─────────────────────────────────────────────────
        images = rev.get("images", [])
        if images:
            with st.expander(f"📸 Patient Photos ({len(images)} uploaded)", expanded=True):
                st.caption("Photos submitted by the patient for your visual assessment.")
                img_cols = st.columns(min(len(images), 3))
                for i, img_data in enumerate(images):
                    try:
                        raw = base64.b64decode(img_data["data"])
                        with img_cols[i % 3]:
                            st.image(
                                raw,
                                caption=img_data.get("filename", f"Photo {i+1}"),
                                use_container_width=True,
                            )
                    except Exception:
                        st.warning(f"Could not render image: {img_data.get('filename', '')}")

        if status == "approved" and rev.get("finalized_response"):
            with st.expander("✅ View Finalized Response"):
                st.markdown(rev["finalized_response"])
                if rev.get("doctor_notes"):
                    st.info(f"Doctor's note: {rev['doctor_notes']}")

        if allow_actions:
            col1, col2, col3 = st.columns(3)

            # ── Approve ──────────────────────────────────────────────────────
            with col1:
                if st.button("✅ Approve As-Is", key=f"approve_{rid}", use_container_width=True):
                    with st.spinner("Approving…"):
                        update_review(
                            review_id          = rid,
                            status             = "approved",
                            finalized_response = rev["ai_response"],
                            doctor_username    = st.session_state.doc_user,
                        )
                        _save_post_approval_summary(rev, rev["ai_response"])
                    st.success("✅ Approved and saved.")
                    st.rerun()

            # ── Edit & Approve ────────────────────────────────────────────────
            with col2:
                edit_key = f"edit_mode_{rid}"
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = False

                if st.button("✏️ Edit & Approve", key=f"editbtn_{rid}", use_container_width=True):
                    st.session_state[edit_key] = True

                if st.session_state[edit_key]:
                    edited = st.text_area(
                        "Edit the AI response below:",
                        value=rev.get("ai_response", ""),
                        height=300,
                        key=f"edit_text_{rid}",
                    )
                    notes = st.text_input("Doctor's note (optional):", key=f"edit_note_{rid}")
                    if st.button("💾 Save & Approve", key=f"save_edit_{rid}", use_container_width=True):
                        with st.spinner("Saving…"):
                            update_review(
                                review_id          = rid,
                                status             = "approved",
                                finalized_response = edited,
                                doctor_username    = st.session_state.doc_user,
                                doctor_notes       = notes or None,
                            )
                            _save_post_approval_summary(rev, edited)
                        st.session_state[edit_key] = False
                        st.success("✅ Edited response approved and saved.")
                        st.rerun()

            # ── Reject ───────────────────────────────────────────────────────
            with col3:
                reject_key = f"reject_mode_{rid}"
                if reject_key not in st.session_state:
                    st.session_state[reject_key] = False

                if st.button("❌ Reject", key=f"rejectbtn_{rid}", use_container_width=True):
                    st.session_state[reject_key] = True

                if st.session_state[reject_key]:
                    reason = st.text_input("Reason for rejection:", key=f"reject_reason_{rid}")
                    if st.button("Confirm Reject", key=f"confirm_reject_{rid}"):
                        update_review(
                            review_id       = rid,
                            status          = "rejected",
                            doctor_username = st.session_state.doc_user,
                            doctor_notes    = reason or None,
                        )
                        st.session_state[reject_key] = False
                        st.warning("❌ Consultation rejected.")
                        st.rerun()

        st.markdown("---")


def _save_post_approval_summary(rev: dict, finalized_response: str):
    """Generate and persist a conversation summary after doctor approval."""
    try:
        summary = generate_conversation_summary(
            st.secrets["OPENAI_API_KEY"],
            patient_name       = rev["patient_name"],
            complaint          = rev["complaint"],
            finalized_response = finalized_response,
        )
        save_summary(
            patient_id = rev["patient_id"],
            session_id = rev["session_id"],
            summary    = summary,
        )
    except Exception:
        pass   # Don't block the approval if summary fails


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════════════════════════════
mode = st.session_state.mode
if mode == "landing":
    show_landing()
elif mode == "patient":
    show_patient()
elif mode == "doctor":
    show_doctor()
