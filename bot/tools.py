# bot/tools.py
from . import db
from .mcp_agent import create_incident_for_request, resolve_request_in_servicenow
from .rundeck_client import trigger_install_job, poll_rundeck_execution
import asyncio

def list_software():
    return db.get_software_list()

async def install_request(user_name: str, software_name: str) -> str:
    software_list = db.get_software_list()
    match = next((s for s in software_list if s["name"].lower() == software_name.lower()), None)
    if not match:
        return f"Software '{software_name}' not found."

    req_id = db.log_request(user_name=user_name, software_name=match["name"], winget_id=match["winget_id"])

    # 1️⃣ Create ServiceNow ticket
    try:
        resp = await create_incident_for_request(req_id, user_name, match["name"])
        if not resp.get("success"):
            return f"Request logged, but failed to create ServiceNow ticket: {resp.get('message')}"
        ticket_id = resp.get("incident_id")
    except Exception as e:
        return f"Request logged, but failed to create ServiceNow ticket: {e}"

    # 2️⃣ Trigger Rundeck installation
    result = trigger_install_job(req_id, match["name"], match["winget_id"])
    if not result["success"]:
        return f"ServiceNow ticket created, but failed to trigger installation job: {result['message']}"
    execution_id = result["execution_id"]

    # 3️⃣ Poll Rundeck until job finishes
    loop = asyncio.get_event_loop()
    poll_result = await loop.run_in_executor(None, poll_rundeck_execution, execution_id)
    if not poll_result["success"]:
        db.update_request_status(req_id, "failed")
        return f"Installation job failed on Rundeck (status: {poll_result.get('status')})."

    # 4️⃣ Resolve ServiceNow ticket
    try:
        await resolve_request_in_servicenow(req_id, ticket_id, user_name)
    except Exception as e:
        return f"Installation completed, but failed to resolve ServiceNow ticket: {e}"

    # 5️⃣ Update DB status
    db.update_request_status(req_id, "installed")

    return f"Installation of {match['name']} completed and ServiceNow ticket resolved."
