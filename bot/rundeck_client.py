# bot/rundeck_client.py
import os
import requests
from dotenv import load_dotenv

from .db import update_request_status

load_dotenv()

RUNDECK_URL = os.getenv("RUNDECK_URL")  # e.g. http://localhost:4440
RUNDECK_TOKEN = os.getenv("RUNDECK_API_TOKEN")
RUNDECK_JOB_ID = os.getenv("RUNDECK_JOB_ID")  # the UUID of your Rundeck Job

HEADERS = {
    "X-Rundeck-Auth-Token": RUNDECK_TOKEN,
    "Content-Type": "application/json"
}


def trigger_install_job(request_id: int, software_name: str, winget_id: str) -> dict:
    """
    Trigger the Rundeck job to install the software.
    """
    url = f"{RUNDECK_URL}/api/41/job/{RUNDECK_JOB_ID}/run"
    payload = {
        "options": {
            "winget_id": winget_id
        }
    }

    try:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        execution_id = data.get("id")
        update_request_status(request_id, "in_progress")
        return {"success": True, "execution_id": execution_id}
    except Exception as e:
        update_request_status(request_id, "failed")
        return {"success": False, "message": str(e)}
