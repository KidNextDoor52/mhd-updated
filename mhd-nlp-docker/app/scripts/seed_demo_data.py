from datetime import datetime, timedelta, timezone
import random
from app.utils.slugify import ensure_form_slug

from pymongo import MongoClient

"""
Seed demo data for MHD:

- 8 demo athletes (users)
- 2 weeks of sessions per athlete (with notes + fake NLP flags)
- Training room logs / injuries
- ML-like predictions in `predictions`:
    - use_case = "injury_risk"
    - use_case = "session_quality"
- Pending medical forms in `forms`

Run inside backend container:
    docker compose -f docker-compose.dev.yml exec backend bash
    python scripts/seed_demo_data.py
"""

UTC = timezone.utc

client = MongoClient("mongo", 27017)  # docker service name for Mongo
db = client["mhd_dev"]

users_coll = db["users"]
sessions_coll = db["sessions"]
training_coll = db["training"]
predictions_coll = db["predictions"]
forms_coll = db["forms"]
org_records_coll = db["org_records"]

ATHLETE_USERNAMES = [
    "demo_rb1",
    "demo_wr1",
    "demo_db1",
    "demo_cb1",
    "demo_qb1",
    "demo_te1",
    "demo_de1",
    "demo_s1",
    "demo_lb1",
    "demo_fb1",
    "demo_ot1",
    "demo_nt1",
]

POSITIONS = [
    "RB",
    "WR",
    "DB",
    "CB",
    "QB",
    "TE",
    "DE",
    "S",
    "LB",
    "FB",
    "OT",
    "NT",
]

NOTES_TEMPLATES = [
    "Felt great today, lots of energy.",
    "Ankle a bit sore after cutting drills.",
    "Slept only 4 hours, pretty tired.",
    "Knee bothering me, but finished all sets.",
    "Low energy, rough day mentally.",
    "Missed last session, making it up today.",
]


def _rand_note():
    return random.choice(NOTES_TEMPLATES)


def _nlp_flags_from_note(note: str) -> dict:
    """
    Very dumb NLP emulation.
    In production, you'd call your real NLP pipeline.
    """
    text = note.lower()
    has_pain = any(x in text for x in ["sore", "bothering", "pain", "ankle", "knee"])
    sleep_poor = ("slept only" in text) or ("only" in text and "hours" in text)
    fatigue = "tired" in text or "low energy" in text
    mood_neg = "rough day" in text or "down" in text
    compliance_issue = "missed last session" in text

    return {
        "nlp_pain_any": int(has_pain),
        "nlp_sleep_poor": int(sleep_poor),
        "nlp_fatigue": int(fatigue),
        "nlp_mood_neg": int(mood_neg),
        "nlp_compliance_issue": int(compliance_issue),
    }

def seed_org_records():
    print("[seed] creating org/industry demo records...")
    org_records_coll.delete_many({"demo": True})

    now = datetime.now(UTC)

    # --- Oil & Gas: incidents, permits, trainings ---
    oil_org = "org_oil_001"
    for i in range(8):
        org_records_coll.insert_one({
            "demo": True,
            "org_id": oil_org,
            "vertical": "oil_gas",
            "type": random.choice(["incident", "permit", "training"]),
            "title": f"Rig incident #{i+1}",
            "status": random.choice(["open", "closed", "in_review"]),
            "created_at": now - timedelta(days=random.randint(0, 30)),
            "updated_at": now - timedelta(days=random.randint(0, 10)),
        })

    # --- Financial: KYC, approvals, high-risk accounts ---
    fin_org = "org_fin_001"
    for i in range(10):
        org_records_coll.insert_one({
            "demo": True,
            "org_id": fin_org,
            "vertical": "financial",
            "type": random.choice(["kyc", "approval", "account_review"]),
            "title": f"Client {i+1} KYC",
            "status": random.choice(["pending", "approved", "rejected"]),
            "created_at": now - timedelta(days=random.randint(0, 30)),
            "updated_at": now - timedelta(days=random.randint(0, 10)),
            "risk_score": round(random.uniform(0.1, 0.95), 2),
        })

    # --- Law: matters, deadlines, signatures ---
    law_org = "org_law_001"
    for i in range(7):
        org_records_coll.insert_one({
            "demo": True,
            "org_id": law_org,
            "vertical": "law",
            "type": random.choice(["matter", "deadline", "signature"]),
            "title": f"Matter #{100+i}",
            "status": random.choice(["open", "closed", "awaiting_signature"]),
            "created_at": now - timedelta(days=random.randint(0, 45)),
            "updated_at": now - timedelta(days=random.randint(0, 15)),
        })

    print("[seed] org records done.")


def seed_users():
    print("[seed] creating demo athletes...")
    for uname, pos in zip(ATHLETE_USERNAMES, POSITIONS):
        existing = users_coll.find_one({"username": uname})
        if existing:
            continue
        users_coll.insert_one({
            "username": uname,
            "email": f"{uname}@demo.mhd",
            "password": None,
            "role": "athlete",
            "position": pos,
            "created_at": datetime.now(UTC),
            "demo": True,
        })
    print("[seed] users done.")


def seed_sessions_and_training():
    print("[seed] creating sessions + training logs...")

    # wipe old demo data for repeatability
    sessions_coll.delete_many({"demo": True})
    training_coll.delete_many({"demo": True})

    today = datetime.now(UTC).date()
    start_day = today - timedelta(days=13)

    for uname in ATHLETE_USERNAMES:
        for d in range(14):
            day = start_day + timedelta(days=d)
            ts = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
            note = _rand_note()
            flags = _nlp_flags_from_note(note)

            # simple load pattern: later days get heavier
            sets = random.randint(3, 6)
            reps = random.randint(4, 10)
            rpe = random.randint(5, 9)
            completed_pct = random.choice([0.8, 0.9, 1.0])
            rest_s = random.choice([60, 90, 120])

            sessions_coll.insert_one({
                "demo": True,
                "athlete_id": uname,
                "org_id": "org_train_001",
                "ts": ts,
                "sets": sets,
                "reps": reps,
                "rpe": rpe,
                "rest_s": rest_s,
                "completed_pct": completed_pct,
                "notes": note,
                **flags,
            })

            # occasional training room entry to mimic injuries
            if flags["nlp_pain_any"] and random.random() < 0.3:
                training_coll.insert_one({
                    "demo": True,
                    "username": uname,
                    "injury": "ankle sprain (mild)",
                    "details": f"Reported pain after session on {day.isoformat()}",
                    "created_at": ts + timedelta(hours=1),
                })

    print("[seed] sessions + training logs done.")


def seed_predictions_and_forms():
    print("[seed] creating predictions + forms for trainer dashboard...")

    # wipe old demo predictions/forms
    predictions_coll.delete_many({"demo": True})
    forms_coll.delete_many({"demo": True})

    now = datetime.now(UTC)
    start = now - timedelta(days=14)

    # --- injury_risk predictions (2 weeks) ---
    for uname in ATHLETE_USERNAMES:
        for d in range(14):
            ts = start + timedelta(days=d, hours=random.randint(6, 20))
            base = random.uniform(0.2, 0.9)

            meta = {
                "athlete_username": uname,
                "recent_injury_flag": base > 0.75 and random.random() < 0.5,
                "high_load_flag": base > 0.7 and random.random() < 0.7,
                "nlp_pain_any": base > 0.6 and random.random() < 0.4,
            }

            predictions_coll.insert_one({
                "demo": True,
                "use_case": "injury_risk",
                "athlete_id": uname,
                "org_id": "org_train_001",
                "score": round(base, 3),
                "ts": ts,
                "meta": meta,
            })

    # --- session_quality predictions (last week) ---
    for uname in ATHLETE_USERNAMES:
        for i in range(8):
            ts = now - timedelta(days=random.randint(0, 7),
                                 hours=random.randint(0, 23))
            score = random.uniform(2.5, 4.9)

            predictions_coll.insert_one({
                "demo": True,
                "use_case": "session_quality",
                "org_id": "org_train_001",
                "athlete_id": uname,
                "score": round(score, 2),
                "ts": ts,
            })

    # --- pending / flagged forms for trainer view ---
    form_types = ["Physical", "Concussion", "PT clearance"]

    # just give first 4 demo athletes some paperwork
    for uname in ATHLETE_USERNAMES[:4]:
        for ftype in form_types:
            created_at = now - timedelta(days=random.randint(0, 10))
            updated_at = created_at + timedelta(hours=random.randint(1, 48))

            # simple fake flags
            flags = {
                "nlp_pain_any": random.choice([0, 1]),
                "nlp_sleep_poor": random.choice([0, 1]),
                "nlp_fatigue": random.choice([0, 1]),
                "nlp_mood_neg": random.choice([0, 1]),
            }

            # more “flagged” if pain/fatigue is high
            if flags["nlp_pain_any"] or flags["nlp_fatigue"]:
                status = random.choice(["flagged", "pending"])
            else:
                status = random.choice(["pending", "cleared"])

            form_doc = {
                "demo": True,
                "athlete_id": uname,
                "type": "medical_clearance",
                "status": status,
                "created_at": created_at,
                "updated_at": updated_at,
                "flags": flags,
                "name": f"{ftype} – {uname}",
            }

            # make sure slug is unique + non-null
            form_doc = ensure_form_slug(form_doc, prefix="clearance")
            forms_coll.insert_one(form_doc)

    print("[seed] predictions + forms done.")



if __name__ == "__main__":
    seed_users()
    seed_sessions_and_training()
    seed_predictions_and_forms()
    print("[seed] complete.")
