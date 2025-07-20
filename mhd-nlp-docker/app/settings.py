#
#from dotenv import load_dotenv
#import os
#
## Ensure .env.dev is loaded
#env_path = os.path.join(os.path.dirname(__file__), '.env.dev')
#load_dotenv(dotenv_path=env_path)
#
## Now read environment variables
#MONGO_URI = os.getenv("MONGO_URI")
#MONGO_DB = os.getenv("MONGO_DB")
#SECRET_KEY = os.getenv("SECRET_KEY")

import os
from dotenv import load_dotenv

# Load .env.dev manually (in case of local dev, optional)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env.dev"))

# Fetch from OS env (Docker runtime injects this way)
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

print(f"MONGO_DB = {MONGO_DB}")  # <-- useful debug to verify it loaded