# app.py
import os
from fastapi import FastAPI, Request
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity, Attachment
from dotenv import load_dotenv

from bot.agentic_bot import AgenticBot
from bot.db import get_software_list, log_request

load_dotenv()
app = FastAPI()

# Bot Adapter
APP_ID = os.getenv("MICROSOFT_APP_ID", "")
APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD", "")
adapter_settings = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
adapter = BotFrameworkAdapter(adapter_settings)

# Agent (LangGraph + Groq)
BOT = AgenticBot()  # uses GROQ_API_KEY

# Preload software list for card submissions
SOFTWARE_LIST = get_software_list()

def get_winget_id(software_name: str):
    for s in SOFTWARE_LIST:
        if s["name"] == software_name:
            return s["winget_id"]
    return None

# Adaptive Card helper (optional, for manual building)
def build_adaptive_card(softwares):
    actions = [{"type": "Action.Submit", "title": s["name"], "data": {"software": s["name"]}} for s in softwares]
    return {
        "type": "AdaptiveCard",
        "body": [{"type": "TextBlock", "text": "Select software to install:", "weight": "Bolder"}],
        "actions": actions,
        "version": "1.4"
    }

# ---- Handlers ----
async def on_message(turn_context: TurnContext):
    text = turn_context.activity.text or ""
    user_name = turn_context.activity.from_property.name

    # Handle Adaptive Card submission
    if turn_context.activity.value:
        data = turn_context.activity.value
        software_name = data.get("software")
        if software_name:
            winget_id = get_winget_id(software_name)
            log_request(user_name=user_name, software_name=software_name, winget_id=winget_id)
            await turn_context.send_activity(f"Install request for {software_name} has been logged.")
        else:
            await turn_context.send_activity("No software selected.")
        return

    # Route through LangGraph bot
    result = await BOT.handle_message(text, user_name)

    if isinstance(result, dict) and result.get("type") == "AdaptiveCard":
        attachment = Attachment(
            content_type="application/vnd.microsoft.card.adaptive",
            content=result
        )
        reply = Activity(type="message", attachments=[attachment])
        await turn_context.send_activity(reply)
    else:
        await turn_context.send_activity(result)


async def on_conversation_update(turn_context: TurnContext):
    """
    Handle new conversation start.
    Right now: do NOT send catalog. Optionally send a short greeting.
    """
    if turn_context.activity.members_added:
        for member in turn_context.activity.members_added:
            if member.id != turn_context.activity.recipient.id:
                # 🔹 Only greeting, no catalog
                await turn_context.send_activity("👋 Hi! I’m your IT assistant. How can I help you today?")

# ---- Endpoint ----
@app.post("/api/messages")
async def messages(req: Request):
    body = await req.json()
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    if activity.type == "message":
        await adapter.process_activity(activity, auth_header, on_message)
    elif activity.type == "conversationUpdate":
        await adapter.process_activity(activity, auth_header, on_conversation_update)
    # ignore other event types

    return {}

# ---- Local run ----
if __name__ == "__main__":
    import uvicorn
    print("🚀 Bot server running at http://127.0.0.1:3978/api/messages")
    uvicorn.run("app:app", host="127.0.0.1", port=3978, reload=True)
