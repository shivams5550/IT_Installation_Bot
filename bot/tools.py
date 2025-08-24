# bot/tools.py
from . import db
from .mcp_agent import create_incident_for_request
from .rundeck_client import trigger_install_job
import asyncio

def list_software():
    """
    Return the software list (as Python list of dicts).
    Each item: {"name": str, "winget_id": str}
    """
    return db.get_software_list()


async def install_request(user_name: str, software_name: str) -> str:
    """
    Log an install request, create ServiceNow incident, and trigger Rundeck job.
    """
    software_list = db.get_software_list()
    match = next((s for s in software_list if s["name"].lower() == software_name.lower()), None)
    if not match:
        return f"Software '{software_name}' not found."

    # Log request in DB
    req_id = db.log_request(user_name=user_name, software_name=match["name"], winget_id=match["winget_id"])

    # Create ServiceNow ticket
    try:
        await create_incident_for_request(req_id, user_name, match["name"])
    except Exception as e:
        return f"Request logged, but failed to create ServiceNow ticket: {e}"

    # Trigger Rundeck job
    result = trigger_install_job(req_id, match["name"], match["winget_id"])
    if not result["success"]:
        return f"ServiceNow ticket created, but failed to trigger installation job: {result['message']}"

    return f"Install request for {match['name']} logged. Installation in progress..."
