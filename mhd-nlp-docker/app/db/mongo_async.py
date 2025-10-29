import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DB", "mhd_dev")

_client = AsyncIOMotorClient(MONGO_URI)
db = _client[MONGO_DB]

# collections your code expects
users = db["users"]
ingests = db["ingests"]