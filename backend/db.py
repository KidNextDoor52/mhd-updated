from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]

athletes = db["athletes"]
documents = db["documents"]
users = db["users"]
permissions = db["permissions"]
medical_history = db["medical_history"]
physical_exam = db["physical_exam"]
