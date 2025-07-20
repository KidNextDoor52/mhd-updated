#import fitz  # PyMuPDF
#import os
#from datetime import datetime
#import uuid
#import spacy
#
#nlp = spacy.load("en_core_sci_sm")
#
#def extract_text_from_pdf(file_path):
#    text = ""
#    with fitz.open(file_path) as doc:
#        for page in doc:
#            text += page.get_text()
#    return text
#
#KEYWORDS = ["diagnosis", "treatment", "medication", "surgery", "injury"]
#
#def extract_keywords(text):
#    found = []
#    text_lower = text.lower()
#    for kw in KEYWORDS:
#        if kw in text_lower:
#            found.append(kw)
#    return found
#
#def process_uploaded_file(file, upload_dir="uploads"):
#    os.makedirs(upload_dir, exist_ok=True)
#    filename = f"{uuid.uuid4()}.pdf"
#    file_path = os.path.join(upload_dir, filename)
#
#    with open(file_path, "wb") as f:
#        f.write(file)
#
#    extracted_text = extract_text_from_pdf(file_path)
#    tags = extract_keywords(extracted_text)
#
#
#    return {
#        "document_id": str(uuid.uuid4()),
#        "athlete_id": "athlete-123",
#        "file_path": file_path,
#        "upload_date": datetime.utcnow().isoformat(),
#        "document_type": "Medical History",
#        "text": extracted_text,
#        "tags": tags
#    }
#
import spacy
from typing import List, Dict

# Load the scispaCy model
try:
    nlp = spacy.load("en_core_sci_sm")
except:
    #fallback in case it's not available
    nlp = spacy.load("en_core_web_sm")

def extracted_medical_entities(text: str) -> List[Dict[str, str]]:
    """
    Use scispaCy (or spaCy fallback) to extract named entities from text.
    """
    doc = nlp(text)
    entities = []
    for ent in doc.ents:
        entities.append({
            "text": ent.text,
            "label": ent.label_
        })
    return entities

def process_uploaded_file(file_bytes: bytes) -> dict:
    """
    Process uploaded medical file and extract metadata + medical terms.
    """
    # simulate extrating text from the uploaded file
    text = file_bytes.decode("utf-8", errors="ignore")

    # NLP analysis
    extracted_entities = extracted_medical_entities(text)

    # Metadata stub (replace this as needed)
    metadata = {
        "athlete_id": "12345",
        "document_type": "medical_record",
        "upload_date": "2025-07-20",
        "tags": ["NLP", "entity extraction"],
        "nlp_entities": extracted_entities
    }

    return metadata
