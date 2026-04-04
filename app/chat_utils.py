from euriai.langchain import create_chat_model
from openai import OpenAI

MODEL       = "gpt-4.1-nano"
TEMPERATURE = 0.7
EURI_BASE_URL = "https://api.euron.one/api/v1/euri"


def get_chat_model(api_key: str):
    return create_chat_model(api_key=api_key, model=MODEL, temperature=TEMPERATURE)


def ask_chat_model(chat_model, prompt: str) -> str:
    return chat_model.invoke(prompt).content


def get_vision_client(api_key: str) -> OpenAI:
    """OpenAI-compatible client pointed at EURI's endpoint for multimodal calls."""
    return OpenAI(api_key=api_key, base_url=EURI_BASE_URL)


def ask_vision_model(api_key: str, prompt: str, images: list) -> str:
    """
    Send a text prompt + list of base64 images to gpt-4.1-nano via EURI.
    Falls back to text-only if vision is not supported by the endpoint.
    """
    client = get_vision_client(api_key)

    if not images:
        # No images — text-only call
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE,
        )
        return resp.choices[0].message.content

    # Build multimodal content: text + images
    content = [{"type": "text", "text": prompt}]
    for img in images:
        mime = img.get("mime_type", "image/jpeg")
        data = img["data"]
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime};base64,{data}",
                "detail": "low",
            },
        })

    try:
        # Attempt vision (multimodal) call
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": content}],
            temperature=TEMPERATURE,
        )
        return resp.choices[0].message.content
    except Exception:
        # Vision not supported by this endpoint — fall back to text-only
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE,
        )
        return resp.choices[0].message.content


# ── Patient History Report ────────────────────────────────────────────────────

def generate_patient_history_report(
    chat_model,
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

    return ask_chat_model(chat_model, prompt)


# ── AI Diagnostic Response ────────────────────────────────────────────────────

def generate_ai_diagnosis(
    chat_model,
    patient_name:      str,
    past_summaries:    list,
    current_complaint: str,
    medical_context:   str  = "",
    images:            list = None,
    api_key:           str  = "",
) -> str:
    """
    Generate a diagnostic AI response. Uses vision model when patient
    has uploaded photos; falls back to text-only otherwise.
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
ONLY include this section if a physical examination is truly necessary for diagnosis or treatment (e.g., wound assessment, prescription-only medication, ambiguous physical symptoms).
If not needed, OMIT this section entirely.
If needed, write: "Please visit the clinic for a physical evaluation — [brief reason why]."

---

IMPORTANT: This response will be reviewed by a licensed doctor before reaching the patient.
Be medically precise, direct, and use clear markdown formatting. Avoid vague advice."""

    # Use vision model if images are present, otherwise fallback to text chat
    if images and api_key:
        return ask_vision_model(api_key, prompt, images)
    return ask_chat_model(chat_model, prompt)


# ── Conversation Summary (for MongoDB storage) ────────────────────────────────

def generate_conversation_summary(
    chat_model,
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

    return ask_chat_model(chat_model, prompt)