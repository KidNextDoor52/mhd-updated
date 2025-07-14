from pymongo import MongoClient
import settings

#making the connections to the database
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]

#Database Collections

