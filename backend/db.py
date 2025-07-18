from pymongo import MongoClient
import settings

#making the connections to the database
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]

#Database Collections
athletes = db["athletes"]
documents = db["documents"]
users = db["users"]
permissions = db["permissions"]
medical_history = ["medical_history"]
physical_exam = db["physical_exam"]
shared_links = db["shared_links"]

"""
RUNNING ENVIRONMENTS 

🛠️ Dev:
(bash)
export MHD_ENV=dev
docker-compose -f docker/docker-compose.dev.yml up -d
uvicorn main:app --reload

🧪 Test:
(bash)
export MHD_ENV=test
docker-compose -f docker/docker-compose.test.yml up -d
uvicorn main:app --reload

Each environment now has:
Its own isolated MongoDB
Its own .env config
Runtime switching with MHD_ENV

🧪 Future Option: Add pytest/test automation
Once test env is running, you can add test scripts like:
(bash)
pytest tests/ --env=test
"""