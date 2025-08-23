# sn_client_test_fixed.py
import os
import asyncio
import json
from dotenv import load_dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

async def main():
    # ---- Initialize MCP client ----
    client = MultiServerMCPClient({
        "servicenow": {
            "url": "http://127.0.0.1:8000/sse",
            "transport": "sse",
        }
    })

    tools = await client.get_tools()
    #print("Loaded tools:", [t.name for t in tools])

    # Filter incident-related tools
    incident_tools = [t for t in tools if t.name.startswith("create_incident") or t.name.startswith("update_incident") or t.name.startswith("resolve_incident") or t.name.startswith("list_incidents")]
    print("Incident tools available:", [t.name for t in incident_tools])

    # Get individual tools
    create_tool = next(t for t in tools if t.name == "create_incident")
    update_tool = next(t for t in tools if t.name == "update_incident")
    resolve_tool = next(t for t in tools if t.name == "resolve_incident")
    list_tool = next(t for t in tools if t.name == "list_incidents")

    # ---- 1️⃣ Create an incident ----
    create_response = await create_tool.ainvoke({
        "short_description": "Test Incident from MCP client",
        "description": "This incident is created for testing MCP integration",
        "caller": "admin"   # ✅ Explicitly set caller
    })

    # Parse JSON if returned as string
    if isinstance(create_response, str):
        create_response = json.loads(create_response)

    print("Create Incident Response:", create_response)
    sys_id = create_response.get("incident_id")  # MCP key
    incident_number = create_response.get("incident_number")
    print("Created Incident sys_id:", sys_id, "number:", incident_number)

    # ---- 2️⃣ Update the incident ----
    update_response = await update_tool.ainvoke({
        "incident_id": sys_id,
        "short_description": "Updated via MCP client",
        "description": "This incident description was updated via client"
    })
    if isinstance(update_response, str):
        update_response = json.loads(update_response)
    print("Update Incident Response:", update_response)

    # ---- 3️⃣ Resolve the incident ----
    resolve_response = await resolve_tool.ainvoke({
        "incident_id": sys_id,
        "resolution_code": "Resolved by caller",       # dummy value to pass validation
        "resolution_notes": "Resolved via MCP client test"  # dummy value to pass validation
    })
    if isinstance(resolve_response, str):
        resolve_response = json.loads(resolve_response)
    print("Resolve Incident Response:", resolve_response)

    # # ---- 4️⃣ List incidents to confirm ----
    # list_response = await list_tool.ainvoke({})
    # if isinstance(list_response, str):
    #     list_response = json.loads(list_response)
    # print("List Incidents Response:", list_response)

# Run
asyncio.run(main())
