from app.db import users


def get_user_by_username(username: str):
    """
    Synchronous helper using PyMongo.
    """
    return users.find_one({"username": username})
