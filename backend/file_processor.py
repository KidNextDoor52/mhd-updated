import fitz  # PyMuPDF
import os
from datetime import datetime
import uuid

def extract_text_from_pdf(file_path):
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def process_uploaded_file(file, upload_dir="uploads"):
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}.pdf"
    file_path = os.path.join(upload_dir, filename)

    with open(file_path, "wb") as f:
        f.write(file)

    extracted_text = extract_text_from_pdf(file_path)

    return {
        "document_id": str(uuid.uuid4()),
        "athlete_id": "athlete-123",
        "file_path": file_path,
        "upload_date": datetime.utcnow().isoformat(),
        "document_type": "Medical History",
        "text": extracted_text
    }
