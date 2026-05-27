from openai import OpenAI

MODEL         = "gpt-4o-mini"   # Supports vision + text, cheap and fast
TEMPERATURE   = 0.7
OPENAI_BASE   = "https://api.openai.com/v1"


def get_openai_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


# ── Core call helpers ─────────────────────────────────────────────────────────

def ask_text(api_key: str, prompt: str) -> str:
    """Simple text-only call."""
    client = get_openai_client(api_key)
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=TEMPERATURE,
    )
    return resp.choices[0].message.content


def ask_vision(api_key: str, prompt: str, images: list) -> str:
    """
    Multimodal call: text + base64 images.
    images: list of dicts with 'data' (base64 str) and 'mime_type'.
    Falls back to text-only if images list is empty.
    """
    client = get_openai_client(api_key)

    if not images:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE,
        )
        return resp.choices[0].message.content

    # Build multimodal message
    content = [{"type": "text", "text": prompt}]
    for img in images:
        mime = img.get("mime_type", "image/jpeg")
        data = img["data"]
        content.append({
            "type": "image_url",
            "image_url": {
                "url":    f"data:{mime};base64,{data}",
                "detail": "low",   # 85 tokens/image — cheapest, fine for medical photos
            },
        })

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": content}],
        temperature=TEMPERATURE,
    )
    return resp.choices[0].message.content


# ── Kept for backward compatibility with main.py ──────────────────────────────
def get_chat_model(api_key: str):
    """Legacy shim — returns api_key so main.py doesn't need changes."""
    return api_key


def ask_chat_model(chat_model, prompt: str) -> str:
    """Legacy shim — chat_model is now just the api_key string."""
    return ask_text(chat_model, prompt)


# ── Patient History Report ────────────────────────────────────────────────────

def generate_patient_history_report(
    api_key: str,
    patient_name: str,
    past_summaries: list,
) -> str:
    """
    Synthesize past visit summaries into a structured Patient History Report.
    Shown to the patient and used as AI context.
    """
    if not past_summaries:
        return (
            "**No previous visit records found.**\n\n"
            "This appears to be your first consultation with us. "
            "Please proceed to describe your current symptoms below."
        )

    visits_text = "\n\n".join(
        f"**Visit {i + 1}:** {s}" for i, s in enumerate(past_summaries)
    )
    prompt = f"""You are a medical AI reviewing patient history for: {patient_name}

PAST VISIT RECORDS (chronological):
{visits_text}

Write a structured **Patient Medical History Report** with these sections:
1. **Summary** – 2-3 sentence holistic overview
2. **Known Conditions** – diagnosed or ongoing issues
3. **Medications & Treatments** – any mentioned
4. **Recurring Symptoms** – patterns across visits
5. **Important Flags** – allergies, red flags, or critical notes

Be concise, clinically accurate, and formatted in markdown.
Do not number visits in the output — write it as a unified report."""

    return ask_text(api_key, prompt)


# ── AI Diagnostic Response ────────────────────────────────────────────────────

def generate_ai_diagnosis(
    api_key:           str,
    patient_name:      str,
    past_summaries:    list,
    current_complaint: str,
    medical_context:   str  = "",
    images:            list = None,
) -> str:
    """
    Generate a diagnostic AI response. Uses vision when images are provided.
    Sent to doctor for review before being shared with the patient.
    """
    history_text = (
        "\n\n".join(f"Visit {i + 1}: {s}" for i, s in enumerate(past_summaries))
        if past_summaries
        else "No previous visit records on file."
    )
    context_section = (
        f"\n\nRELEVANT UPLOADED MEDICAL DOCUMENTS:\n{medical_context}"
        if medical_context else ""
    )
    image_note = (
        f"\n\nVISUAL CONTEXT: The patient has uploaded {len(images)} photo(s) of their condition. "
        "Analyse the image(s) carefully — describe what you observe visually and factor it into your assessment."
        if images else ""
    )

    prompt = f"""You are MediChat Pro, a clinical medical AI assistant. Provide a clear, direct, and well-structured response.

PATIENT: {patient_name}

PATIENT HISTORY:
{history_text}{context_section}{image_note}

CURRENT COMPLAINT:
{current_complaint}

---

Respond using EXACTLY this structure. Be concise and direct — no filler sentences.

## 🩺 Assessment
One clear paragraph: what is most likely going on, considering the patient's history, current complaint{', and the uploaded photo(s)' if images else ''}.

## 🔍 Likely Diagnosis
List the top 1–3 probable diagnoses in order of likelihood. One line each.

## 💊 Medications
List specific medications with dosage and duration where applicable. Format:
- **[Drug name]** – [dose] – [frequency] – [duration]
Only recommend OTC or standard treatments; flag anything requiring a prescription.

## 🧪 Tests / Investigations
Only include if genuinely needed. List specific tests. If none needed, say "None required at this stage."

## ⚠️ Red Flags — Seek Immediate Help If:
Bullet list of specific warning signs that require urgent care or ER visit.

## 📋 Care Instructions
2–4 short, actionable self-care steps the patient should follow at home.

## 🏥 Clinic Visit
ONLY include this section if a physical examination is truly necessary for diagnosis or treatment.
If not needed, OMIT this section entirely.
If needed, write: "Please visit the clinic for a physical evaluation — [brief reason why]."

---

IMPORTANT: This response will be reviewed by a licensed doctor before reaching the patient.
Be medically precise, direct, and use clear markdown formatting. Avoid vague advice."""

    if images:
        return ask_vision(api_key, prompt, images)
    return ask_text(api_key, prompt)


# ── Conversation Summary (for MongoDB storage) ────────────────────────────────

def generate_conversation_summary(
    api_key:            str,
    patient_name:       str,
    complaint:          str,
    finalized_response: str,
) -> str:
    """
    Create a concise clinical note to store as a past-visit summary.
    Used in future consultations for context.
    """
    prompt = f"""Create a concise clinical visit summary for medical records.

Patient: {patient_name}
Chief Complaint: {complaint}
Clinical Response Provided: {finalized_response}

Write a 3–5 sentence clinical summary covering:
- Chief complaint and context
- Key clinical assessment
- Recommendations or treatment plan
- Any important flags or follow-up actions

Write in plain text, third person, no markdown, no bullet points."""

    return ask_text(api_key, prompt)

# ── Document Q&A (Doctor Dashboard) ──────────────────────────────────────────

def answer_doctor_question(api_key: str, question: str, context: str) -> str:
    """
    Answer a doctor's question based strictly on the retrieved PDF context.
    """
    if not context:
        return "I could not find any relevant information in the attached documents regarding your question."

    prompt = f"""You are a medical AI assistant helping a doctor review a patient's uploaded medical documents.

RELEVANT DOCUMENT EXCERPTS:
{context}

DOCTOR'S QUESTION:
{question}

Based strictly on the excerpts above, provide a precise, concise, and clinically relevant answer to the doctor. 
If the answer is not in the text, state that explicitly. Do not make up information."""

    return ask_text(api_key, prompt)