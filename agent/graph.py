"""
agent/graph.py — LangGraph ReAct agent.

Sistem prompt'u tamamen PDF'ten çıkarılan business_profile'e göre dinamik oluşturulur.
Hiçbir iş mantığı burada hardcode değil.
"""
import json
import time
import uuid
from typing import Annotated, Any, Dict, List, Optional, TypedDict

import structlog
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import (
    AIMessage, HumanMessage, SystemMessage, ToolMessage, BaseMessage
)
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from config import settings
from agent.tools import ALL_TOOLS, set_tool_context
from agent.business_profile import get_business_profile, profile_to_system_rules
from db.client import save_message, write_audit_log

logger = structlog.get_logger("agent.graph")


# --------------------------------------------------------------------------- #
#  Agent State
# --------------------------------------------------------------------------- #
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    session_id: str
    business_id: str
    business_name: str
    iteration_count: int


# --------------------------------------------------------------------------- #
#  Dinamik sistem prompt — tamamen PDF profilinden üretilir
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT_BASE = """You are a helpful AI assistant for {business_name}.

=== BUSINESS RULES (extracted from business PDF) ===
{business_rules}

=== YOUR TOOLS ===
You have these tools available. Use them intelligently:

INFORMATION TOOLS (always use before answering factual questions):
- get_business_info(query): Search PDF for any business info
- search_items_or_services(term): Look up specific items/services and prices
- get_pricing_rules(): Get tax, delivery fees, minimums from PDF
- get_scheduling_rules(): Get appointment rules, durations from PDF

ORDER TOOLS (use when customer wants to buy something):
- create_order_draft(): Start a new order
- add_item_to_order(): Add item (always verify price from PDF first)
- remove_item_from_order(): Remove item when customer changes mind
- set_order_fulfillment(): Set delivery/pickup + add delivery fee
- get_order_summary(): Show current cart to customer
- confirm_order(): Finalize (only after customer confirms)
- cancel_order(): Cancel an order

APPOINTMENT TOOLS (use when customer wants to book time):
- check_appointment_availability(): Check slots from PDF rules
- book_appointment(): Create appointment
- reschedule_appointment(): Move to new time
- cancel_appointment(): Cancel appointment

CUSTOMER TOOL:
- save_customer_info(): Save name/phone/email/address

=== CRITICAL BEHAVIOR RULES ===
1. NEVER guess prices, hours, or availability — always use tools to retrieve from PDF.
2. NEVER add tax unless get_pricing_rules confirms a tax rate exists.
3. NEVER assume a delivery fee — check get_pricing_rules first.
4. NEVER hardcode business logic — all rules come from the PDF.
5. When a customer changes their mind, use remove_item_from_order.
6. Always show full summary before confirming orders or appointments.
7. For multi-intent messages (question + order + appointment), handle ALL intents.
8. Ask for missing required info proactively based on the business rules above.
9. Be conversational and concise.

SESSION: {session_id}
"""


def build_system_prompt(state: AgentState) -> str:
    """PDF profilinden dinamik sistem prompt'u oluştur."""
    profile = get_business_profile(
        business_id=state["business_id"],
        business_name=state["business_name"],
    )
    business_rules = profile_to_system_rules(profile)

    logger.debug(
        "system_prompt.built",
        business=state["business_name"],
        profile_type=profile.get("business_type"),
        tax_rate=profile.get("tax_rate"),
        capabilities=profile.get("capabilities"),
    )

    return SYSTEM_PROMPT_BASE.format(
        business_name=state["business_name"],
        business_rules=business_rules,
        session_id=state["session_id"],
    )


# --------------------------------------------------------------------------- #
#  LLM
# --------------------------------------------------------------------------- #
def get_llm():
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=settings.TEMPERATURE,
        convert_system_message_to_human=True,
    )
    return llm.bind_tools(ALL_TOOLS)


# --------------------------------------------------------------------------- #
#  Nodes
# --------------------------------------------------------------------------- #
def agent_node(state: AgentState) -> Dict:
    """Ana LLM düğümü — ne yapacağına karar verir."""
    t0 = time.time()
    session_id = state["session_id"]
    business_id = state["business_id"]
    iteration = state.get("iteration_count", 0)

    logger.info(
        "🤖 AGENT_NODE",
        session_id=session_id,
        iteration=iteration,
        messages=len(state["messages"]),
    )

    # PDF profili yükle ve tool context'e set et
    profile = get_business_profile(
        business_id=business_id,
        business_name=state["business_name"],
    )
    set_tool_context(business_id, session_id, profile)

    system_msg = SystemMessage(content=build_system_prompt(state))
    llm = get_llm()

    try:
        response = llm.invoke([system_msg] + state["messages"])
        duration_ms = int((time.time() - t0) * 1000)

        tool_calls = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_calls = [tc["name"] for tc in response.tool_calls]

        logger.info(
            "💬 LLM_RESPONSE",
            session_id=session_id,
            content_preview=str(response.content)[:200],
            tool_calls=tool_calls,
            duration_ms=duration_ms,
        )

        write_audit_log(
            event_type="llm_request",
            session_id=session_id,
            business_id=business_id,
            input_data={
                "iteration": iteration,
                "messages_count": len(state["messages"]),
                "last_user_msg": str(state["messages"][-1].content)[:300] if state["messages"] else "",
                "profile_type": profile.get("business_type"),
            },
            output_data={
                "content": str(response.content)[:1000],
                "tool_calls": tool_calls,
            },
            duration_ms=duration_ms,
        )

        if tool_calls:
            logger.info("🔧 TOOLS_PLANNED", tools=tool_calls, session_id=session_id)

        save_message(
            session_id=session_id,
            role="assistant",
            content=str(response.content),
            tool_input={"planned_tools": tool_calls} if tool_calls else None,
        )

        return {
            "messages": [response],
            "iteration_count": iteration + 1,
        }

    except Exception as e:
        duration_ms = int((time.time() - t0) * 1000)
        logger.error("❌ AGENT_NODE_ERROR", error=str(e), session_id=session_id)
        write_audit_log(
            event_type="error",
            session_id=session_id,
            business_id=business_id,
            error_msg=str(e),
            duration_ms=duration_ms,
            log_level="ERROR",
        )
        raise


def tool_execution_node(state: AgentState) -> Dict:
    """Tool çağrılarını çalıştırır."""
    logger.info("⚙️ TOOL_EXECUTION_NODE", session_id=state["session_id"])

    tool_node = ToolNode(ALL_TOOLS)
    result = tool_node.invoke(state)

    for msg in result.get("messages", []):
        if isinstance(msg, ToolMessage):
            logger.info(
                "🔩 TOOL_RESULT",
                tool_call_id=msg.tool_call_id,
                preview=str(msg.content)[:200],
                session_id=state["session_id"],
            )
            save_message(
                session_id=state["session_id"],
                role="tool",
                content=str(msg.content),
                tool_name=getattr(msg, "name", ""),
                tool_output={"result": str(msg.content)[:2000]},
            )

    return result


# --------------------------------------------------------------------------- #
#  Routing
# --------------------------------------------------------------------------- #
def should_continue(state: AgentState) -> str:
    messages = state["messages"]
    last = messages[-1]
    iteration = state.get("iteration_count", 0)

    if iteration >= settings.MAX_ITERATIONS:
        logger.warning("⚠️ MAX_ITERATIONS", count=iteration)
        return END

    if hasattr(last, "tool_calls") and last.tool_calls:
        logger.info("➡️ ROUTE_TO_TOOLS", tools=[tc["name"] for tc in last.tool_calls])
        return "tools"

    logger.info("🏁 ROUTE_TO_END")
    return END


# --------------------------------------------------------------------------- #
#  Graph build
# --------------------------------------------------------------------------- #
def build_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_execution_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


_compiled_graph = None

def get_agent_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_agent_graph()
        logger.info("agent.graph_compiled")
    return _compiled_graph


# --------------------------------------------------------------------------- #
#  Ana giriş noktası
# --------------------------------------------------------------------------- #
def run_agent_turn(
    user_message: str,
    session_id: str,
    business_id: str,
    business_name: str,
    conversation_history: List[Dict] = None,
) -> Dict:
    """
    Bir kullanıcı mesajını agent graph'tan geçirir.
    business_context artık parametre değil — her turn'de PDF'ten otomatik yüklenir.
    """
    t0 = time.time()
    logger.info(
        "🚀 AGENT_TURN_START",
        session_id=session_id,
        business=business_name,
        msg=user_message[:150],
    )

    # Tool context'i hazırla
    profile = get_business_profile(business_id=business_id, business_name=business_name)
    set_tool_context(business_id, session_id, profile)

    save_message(session_id=session_id, role="user", content=user_message)

    # Mesaj geçmişini oluştur
    messages: List[BaseMessage] = []
    if conversation_history:
        for msg in conversation_history[-20:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=user_message))

    initial_state: AgentState = {
        "messages": messages,
        "session_id": session_id,
        "business_id": business_id,
        "business_name": business_name,
        "iteration_count": 0,
    }

    graph = get_agent_graph()
    final_state = graph.invoke(initial_state)

    last_msg = final_state["messages"][-1]
    
    # Handle both string and list content (multimodal/new format)
    content = getattr(last_msg, "content", "")
    if isinstance(content, list):
        # Extract text parts from list
        text_parts = [part["text"] for part in content if isinstance(part, dict) and "text" in part]
        response_text = "".join(text_parts) if text_parts else str(content)
    else:
        response_text = str(content)
    duration_ms = int((time.time() - t0) * 1000)

    # Extract tool calls and citations for structured response
    tool_calls_list = []
    citations_list = []
    
    for msg in final_state["messages"]:
        # Extract Tool Calls from AI messages
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_list.append({
                    "id": tc.get("id", str(uuid.uuid4())),
                    "name": tc["name"],
                    "status": "success", # Default to success if we reached here
                    "duration": "0.5s", # Mock duration for now
                    "input": json.dumps(tc["args"], ensure_ascii=False)
                })
        
        # Extract RAG results (citations) from Tool messages
        if isinstance(msg, ToolMessage) and msg.name == "get_business_info":
            # get_business_info format: [Kaynak 1 | skor=0.9 | sayfa=2]\nContent...
            import re
            content = str(msg.content)
            matches = re.finditer(r"\[Kaynak (\d+) \| skor=([\d.]+) \| sayfa=(\d+)\]\n(.*?)(?=\n\n---\n\n|$)", content, re.DOTALL)
            for m in matches:
                citations_list.append({
                    "source": f"Kaynak {m.group(1)}",
                    "page": int(m.group(3)),
                    "text": m.group(4).strip(),
                    "score": float(m.group(2))
                })

    return {
        "response": response_text,
        "session_id": session_id,
        "iterations": final_state.get("iteration_count", 0),
        "duration_ms": duration_ms,
        "tool_calls": tool_calls_list,
        "citations": citations_list,
        "business_type": profile.get("business_type"),
    }
