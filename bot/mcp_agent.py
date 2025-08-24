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
            # Only incident-related tools
            self.tools = {t.name: t for t in tools if t.name in ("create_incident", "update_incident", "resolve_incident")}
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

    async def resolve_request(self, request_id: int, ticket_id: str, resolver_name: str):
        await self.load_tools()
        resolve_tool = self.tools.get("resolve_incident")
        if not resolve_tool:
            return {"success": False, "message": "resolve_incident tool not available."}

        try:
            # ✅ Match your working sn_client_test_fixed.py call
            resp = await resolve_tool.ainvoke({
                "incident_id": ticket_id,
                "resolution_code": "Resolved by caller",        # dummy value for validation
                "resolution_notes": f"Resolved via bot by {resolver_name}"
            })
            if isinstance(resp, str):
                resp = json.loads(resp)

            update_request_status(request_id, "installed")
            return {"success": True, "response": resp}
        except Exception as e:
            return {"success": False, "message": str(e)}


# ---- Helpers ----
async def create_incident_for_request(request_id, user_name, software_name):
    agent = ServiceNowAgent()
    return await agent.handle_request(request_id, user_name, software_name)

async def resolve_request_in_servicenow(request_id, ticket_id, resolver_name):
    agent = ServiceNowAgent()
    return await agent.resolve_request(request_id, ticket_id, resolver_name)
