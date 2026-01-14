# app/db/__init__.py
import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DB", "mhd_dev")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

# --- Collections (one source of truth) ---
athletes = db["athletes"]
documents = db["documents"]
users = db["users"]
permissions = db["permissions"]
medical_history = db["medical_history"]
physical_exam = db["physical_exam"]
shared_links = db["shared_links"]

equipment = db["equipment"]
training = db["training"]
training_flags = db["training_flags"]
uploads = db["uploads"]
upload_flags = db["upload_flags"]
weightroom = db["weightroom"]
activity_logs = db["activity_logs"]

connections = db["connections"]
metrics_daily = db["metrics_daily"]
workouts = db["workouts"]
fhir_raw = db["fhir_raw"]
clinical_snapshot = db["clinical_snapshot"]
risk_flags = db["risk_flags"]
forms = db["forms"]
form_answers = db["form_answers"]
events = db["events"]
audit_trail = db["audit_trail"]
education = db["education"]
profile = db["profile"]
