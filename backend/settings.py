import os
from dotenv import load_dotenv

#this allows to switch environments using the "MHD_ENV" variable

env = os.getenv("MHD_ENV", "dev")
env_file = f".env.{env}"
load_dotenv(env_file)

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
SECRET_KEY = os.getenv("SECRET_KEY")