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
