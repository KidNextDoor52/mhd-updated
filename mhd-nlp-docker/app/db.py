from pymongo import MongoClient
from . import settings

#making the connections to the database
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]


#Database Collections
athletes = db["athletes"]
documents = db["documents"]
users = db["users"]
permissions = db["permissions"]
medical_history = db["medical_history"]
physical_exam = db["physical_exam"]
shared_links = db["shared_links"]

#Dashboard Collections
equipment = db["equipment"]
training = db["training"]
training_flags = db["training_flags"]
uploads = db["uploads"]
uplaod_flags = db["upload_flags"]
weightroom = db["weightroom"]

activity_logs = db["activity_logs"]

#additions
connections = db.connections
metrics_daily = db.metrics_daily
workouts = db.workouts
fhir_raw = db.fhir_raw
clinical_snapshot = db.clinical_snapshot
risk_flags = db.risk_flags
forms = db.forms
form_answers = db.form_answers
events = db.events
audit_trail = db.audit_trail
education = db.education