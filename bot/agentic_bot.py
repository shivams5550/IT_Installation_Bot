# bot/agentic_bot.py
import os
import json
from typing import TypedDict, Optional, Literal

from fuzzywuzzy import process
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from .tools import list_software, install_request


# ---- Graph State ----
class BotState(TypedDict, total=False):
    user_text: str
    user_name: str
    intent: Literal["install", "list_all", "other"]
    software: Optional[str]
    response_text: Optional[str]
    response_card: Optional[dict]


# ---- Helper: build Adaptive Card ----
def build_adaptive_card(softwares):
    actions = [{"type": "Action.Submit", "title": s["name"], "data": {"software": s["name"]}} for s in softwares]
    card = {
        "type": "AdaptiveCard",
        "body": [{"type": "TextBlock", "text": "Select software to install:", "weight": "Bolder"}],
        "actions": actions,
        "version": "1.4"
    }
    return card


# ---- Agentic Bot (LangGraph) ----
class AgenticBot:
    def __init__(self, groq_api_key: Optional[str] = None):
        api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set.")

        # LLM used for (a) intent classification JSON and (b) general IT answers
        self.llm = ChatGroq(model="gemma2-9b-it", api_key=api_key)

        # Preload catalog for fuzzy-match context
        self.catalog = list_software()
        self.catalog_names = [s["name"] for s in self.catalog]

        # Build graph
        graph = StateGraph(BotState)
        graph.add_node("classify", self._classify_node)
        graph.add_node("handle_install", self._handle_install_node)
        graph.add_node("handle_list_all", self._handle_list_all_node)
        graph.add_node("handle_other", self._handle_other_node)

        # Edges
        graph.set_entry_point("classify")
        graph.add_conditional_edges("classify", self._route_from_intent, {
            "install": "handle_install",
            "list_all": "handle_list_all",
            "other": "handle_other",
        })
        graph.add_edge("handle_install", END)
        graph.add_edge("handle_list_all", END)
        graph.add_edge("handle_other", END)

        self.app = graph.compile()

    # ---- Public: handle one message ----
    async def handle_message(self, text: str, user_name: str):
        state: BotState = {"user_text": text, "user_name": user_name}
        final = self.app.invoke(state)
        # Prefer card if present
        if final.get("response_card"):
            return final["response_card"]
        return final.get("response_text", "Sorry, something went wrong.")

    # ---- Node: classify intent & extract software (LLM + fuzzy fallback) ----
    def _classify_node(self, state: BotState) -> BotState:
        user_text = state["user_text"]

        system = SystemMessage(
            content=(
                "You are an IT assistant that classifies user messages. "
                "Return strict JSON with keys: intent and software.\n"
                "intents:\n"
                "- 'list_all' when user asks what software can be installed.\n"
                "- 'install' when user requests installing a specific software.\n"
                "- 'other' for general IT support.\n"
                "For 'install', set 'software' to the software name (best guess) else ''. "
                "Respond ONLY with JSON and nothing else."
            )
        )
        human = HumanMessage(content=f"User message: {user_text}\nAvailable software: {', '.join(self.catalog_names)}")

        try:
            out = self.llm.invoke([system, human])
            txt = (out.content or "").strip()
            data = json.loads(txt) if txt.startswith("{") else {}
            intent = data.get("intent", "other")
            software = data.get("software") or ""
        except Exception:
            # If LLM parse fails, rule-based fallback
            lt = user_text.lower()
            if "what" in lt and "software" in lt and ("can i install" in lt or "available" in lt or "list" in lt):
                intent, software = "list_all", ""
            elif any(k in lt for k in ["install", "setup", "download"]):
                intent, software = "install", ""
            else:
                intent, software = "other", ""

        # Fuzzy match if we think it's an install and software is present/guessable
        if intent == "install":
            guess = None
            if software:
                match, score = process.extractOne(software, self.catalog_names)
                guess = match if score >= 70 else None
            else:
                # try to find any catalog name mentioned inside the text
                match, score = process.extractOne(user_text, self.catalog_names)
                guess = match if score >= 70 else None
            software = guess or software or ""

        state["intent"] = intent  # type: ignore
        if software:
            state["software"] = software  # type: ignore
        return state

    # ---- Router ----
    def _route_from_intent(self, state: BotState):
        return state.get("intent", "other")

    # ---- Node: handle install ----
    def _handle_install_node(self, state: BotState) -> BotState:
        sw = state.get("software", "")
        if sw:
            # Direct install request (no card)
            msg = install_request(user_name=state["user_name"], software_name=sw)
            state["response_text"] = msg
            return state

        # No software extracted: ask user OR show list? We’ll ask, to keep UX simple.
        state["response_text"] = "Which software would you like to install?"
        return state

    # ---- Node: list all (Adaptive Card) ----
    def _handle_list_all_node(self, state: BotState) -> BotState:
        card = build_adaptive_card(self.catalog)
        state["response_card"] = card
        return state

    # ---- Node: general IT answers (LLM) ----
    def _handle_other_node(self, state: BotState) -> BotState:
        system = SystemMessage(
            content=(
                "You are a helpful IT assistant. "
                "Answer clearly and concisely. "
                "Do NOT offer to list software unless the user asks."
            )
        )
        human = HumanMessage(content=state["user_text"])
        try:
            out = self.llm.invoke([system, human])
            state["response_text"] = out.content or "Sorry, I couldn't formulate a response."
        except Exception as e:
            state["response_text"] = f"Error from Groq LLM: {e}"
        return state
