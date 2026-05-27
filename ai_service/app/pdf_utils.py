from pypdf import PdfReader


def extract_text_from_pdf(file) -> str:
    """
    Extract and concatenate text from all pages of a PDF.
    Returns an empty string if extraction fails or PDF has no text.
    """
    reader = PdfReader(file)
    pages_text = []
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            pages_text.append(extracted)
    return "\n".join(pages_text)