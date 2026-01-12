import re
from typing import Optional
from app.db import db

forms = db["forms"]

def slugify(label: str, prefix: str = "form") -> str:
    """
    Simple slug generator, unique within 'forms.slug'.
    """
    label = (label or "").strip().lower()
    base = re.sub(r"[^a-z0-9]+", "-", label).strip("-") or prefix

    slug = base
    i = 1
    # ensure uniqueness against existing forms

    while forms.find_one({"slug": slug}):
        slug = f"{base}-{i}"
        i += 1
    return slug


def ensure_form_slug(doc: dict, prefix: str = "form") -> dict:
    """
    Ensure 'doc["slug"]' exists and is non-null/unique.
    """
    if not doc.get("slug"):
        # prefer a human label if present
        label = doc.get("name") or doc.get("title") or prefix
        doc["slug"] = slugify(label, prefix=prefix)
    return doc
