# bot/tools.py
from . import db

def list_software():
    """
    Return the software list (as Python list of dicts).
    Each item: {"name": str, "winget_id": str}
    """
    return db.get_software_list()

def install_request(user_name: str, software_name: str) -> str:
    """
    Log an install request to DB. Returns a confirmation message.
    """
    software_list = db.get_software_list()
    match = next((s for s in software_list if s["name"].lower() == software_name.lower()), None)
    if not match:
        return f"Software '{software_name}' not found."

    db.log_request(user_name=user_name, software_name=match["name"], winget_id=match["winget_id"])
    return f"Install request logged for: {match['name']}"
