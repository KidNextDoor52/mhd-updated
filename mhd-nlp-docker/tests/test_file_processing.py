import pytest
import builtins
import spacy
from app.file_processor import extracted_medical_entities, process_uploaded_file

# ---------- 1. BASIC FUNCTIONALITY ----------
def test_extracted_medical_entities_basic():
    text = "Patient has diabetes and hypertension."
    entities = extracted_medical_entities(text)

    # Must return list of dicts with text + label
    assert isinstance(entities, list)
    assert all("text" in e and "label" in e for e in entities)


# ---------- 2. STRUCTURE OF METADATA ----------
def test_process_uploaded_file_structure():
    fake_file = b"John Doe was diagnosed with asthma."

    metadata = process_uploaded_file(fake_file)

    # Validate structure
    assert isinstance(metadata, dict)
    for key in ["athlete_id", "document_type", "upload_date", "tags", "nlp_entities"]:
        assert key in metadata


# ---------- 3. ENTITY EXTRACTION ----------
def test_process_uploaded_file_entities_extraction():
    fake_file = b"Athlete has torn ACL and shoulder pain."
    metadata = process_uploaded_file(fake_file)

    entities = metadata["nlp_entities"]
    assert isinstance(entities, list)

    # At least one entity should match expected terms
    assert any("ACL" in e["text"] or "shoulder" in e["text"] for e in entities)


# ---------- 4. FALLBACK BEHAVIOR ----------
def test_fallback_model(monkeypatch):
    """
    Simulate failure of scispaCy model load.
    Force fallback to en_core_web_sm.
    """

    def fake_load(name):
        if name == "en_core_sci_sm":
            raise OSError("Model not found!")  # simulate missing model
        return spacy.blank("en")

    monkeypatch.setattr(spacy, "load", fake_load)

    text = "Patient suffers from asthma."
    entities = extracted_medical_entities(text)

    assert isinstance(entities, list)  # Should still return list even if fallback
