# bot/mcp_agent.py
import os
import json
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq
from .db import update_request_servicenow, update_request_status

load_dotenv()


class ServiceNowAgent:
    def __init__(self):
        self.client = MultiServerMCPClient({
            "servicenow": {
                "url": os.getenv("MCP_URL", "http://127.0.0.1:8000/sse"),
                "transport": "sse",
            }
        })
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set for MCP agent.")
        self.llm = ChatGroq(model=os.getenv("MCP_GROQ_MODEL", "qwen-qwq-32b"), api_key=api_key)
        self.tools = None

    async def load_tools(self):
        if self.tools is None:
            tools = await self.client.get_tools()
            self.tools = {t.name: t for t in tools if t.name in ("create_incident", "update_incident")}
        return self.tools

    async def handle_request(self, request_id: int, user_name: str, software_name: str) -> dict:
        await self.load_tools()
        create_tool = self.tools.get("create_incident")
        if not create_tool:
            return {"success": False, "message": "create_incident tool not available."}

        try:
            resp = await create_tool.ainvoke({
                "short_description": f"Installation request: {software_name}",
                "description": f"User '{user_name}' requested installation of {software_name}.",
                "caller": user_name
            })
            if isinstance(resp, str):
                resp = json.loads(resp)

            incident_id = resp.get("incident_id")
            incident_number = resp.get("incident_number")
            update_request_servicenow(request_id, incident_id, incident_number)
            return {"success": True, "incident_id": incident_id, "incident_number": incident_number}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def approve_request(self, request_id: int, ticket_id: str, supervisor_name: str):
        await self.load_tools()
        update_tool = self.tools.get("update_incident")
        if not update_tool:
            return {"success": False, "message": "update_incident tool not available."}
        try:
            await update_tool.ainvoke({"incident_id": ticket_id, "fields": {"state": "2", "comments": f"Approved by {supervisor_name}"}})
            update_request_status(request_id, "approved")
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def reject_request(self, request_id: int, ticket_id: str, supervisor_name: str):
        await self.load_tools()
        update_tool = self.tools.get("update_incident")
        if not update_tool:
            return {"success": False, "message": "update_incident tool not available."}
        try:
            await update_tool.ainvoke({"incident_id": ticket_id, "fields": {"state": "7", "comments": f"Rejected by {supervisor_name}"}})
            update_request_status(request_id, "rejected")
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}


# ---- Helpers ----
async def create_incident_for_request(request_id, user_name, software_name):
    agent = ServiceNowAgent()
    return await agent.handle_request(request_id, user_name, software_name)

async def approve_request_in_servicenow(request_id, ticket_id, supervisor_name):
    agent = ServiceNowAgent()
    return await agent.approve_request(request_id, ticket_id, supervisor_name)

async def reject_request_in_servicenow(request_id, ticket_id, supervisor_name):
    agent = ServiceNowAgent()
    return await agent.reject_request(request_id, ticket_id, supervisor_name)

