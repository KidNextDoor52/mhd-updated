from app.db import db

def ensure_indexes():
    # uploads / shares
    db.uploads.create_index([("username", 1), ("upload_date", -1)])
    db.shared_links.create_index("token", unique=True)
    db.shared_links.create_index("expires_at")

    # activity / audit
    db.activity_logs.create_index([("user_id", 1), ("timestamp", -1)])
    db.audit_trail.create_index([("user", 1), ("ts", -1)])

    # forms
    db.forms.create_index("slug", unique=True)
    db.form_answers.create_index([("user", 1), ("form_slug", 1), ("submitted_at", -1)])

    # events / connections
    db.events.create_index([("user", 1), ("date", -1)])
    db.connections.create_index([("user", 1), ("provider", 1)], unique=True)

    # wellness & workouts
    db.metrics_daily.create_index([("user", 1), ("date", -1)], unique=True)
    db.workouts.create_index([("user", 1), ("start", -1)])

    # FHIR/raw
    db.fhir_raw.create_index([("user", 1), ("resourceType", 1), ("resourceId", 1)], unique=True)

    # snapshot & risk flags
    db.clinical_snapshot.create_index("user", unique=True)
    db.risk_flags.create_index([("user", 1), ("date", -1), ("severity", -1)])

    db.weightroom.create_index("username", unique=True)
    db.equipment.create_index("username", unique=True)
    db.medical_history.create_index("username", unique=True)