# bot/tools.py
from . import db
from .mcp_agent import create_incident_for_request
import asyncio

def list_software():
    """
    Return the software list (as Python list of dicts).
    Each item: {"name": str, "winget_id": str}
    """
    return db.get_software_list()  # keep synchronous for init

async def install_request(user_name: str, software_name: str) -> str:
    """
    Log an install request to DB and trigger ServiceNow incident creation via MCP agent.
    """
    software_list = db.get_software_list()
    match = next((s for s in software_list if s["name"].lower() == software_name.lower()), None)
    if not match:
        return f"Software '{software_name}' not found."

    # Log request in DB
    db.log_request(user_name=user_name, software_name=match["name"], winget_id=match["winget_id"])

    # Fetch request ID (last inserted)
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM requests WHERE user_name=%s AND software_name=%s ORDER BY created_at DESC LIMIT 1",
        (user_name, match["name"])
    )
    req_id = cursor.fetchone()[0]
    cursor.close()
    conn.close()

    # Trigger ServiceNow via MCP LLM
    try:
        await create_incident_for_request(req_id, user_name, match["name"])
    except Exception as e:
        return f"Install request logged, but failed to create ServiceNow ticket: {e}"

    return f"Install request logged and ServiceNow ticket created for: {match['name']}"
