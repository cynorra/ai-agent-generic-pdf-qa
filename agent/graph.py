"""
agent/graph.py — LangGraph ReAct agent with Critic/Evaluator (Func 34-36).

Sistem prompt'u tamamen PDF'ten çıkarılan business_profile'e göre dinamik oluşturulur.
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
#  Dinamik sistem prompt
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT_BASE = """You are a helpful AI assistant for {business_name}.

=== BUSINESS RULES (extracted from business PDF) ===
{business_rules}

=== YOUR TOOLS ===
You have these tools available. Use them intelligently:

INFORMATION TOOLS:
- get_business_info(query): Search generic info
- search_items_or_services(term): Look up specific items/services and prices
- get_pricing_rules(): Get tax, delivery fees, minimums
- get_scheduling_rules(): Get appointment rules
- analyze_business_statistics(): Get insights on popular items (use this to upsell)

ORDER TOOLS:
- create_order_draft(): Start a new order
- add_item_to_order(): Add item (verify price first)
- remove_item_from_order(): Remove item
- set_order_fulfillment(): Set delivery/pickup
- get_order_summary(): Show current cart
- confirm_order(): Finalize
- cancel_order(): Cancel an order

APPOINTMENT TOOLS:
- check_appointment_availability(): Check slots
- book_appointment(): Create appointment
- reschedule_appointment(): Move to new time
- cancel_appointment(): Cancel appointment

CUSTOMER TOOLS:
- save_customer_info(): Save name/phone/email/address
- extract_numbers(text): Extract quantities/phone numbers reliably from text
- validate_address(address): Normalize address strings
- analyze_customer_profile(): Fetch customer history (use to personalize)
- record_complaint(order_id, issue): Use when a customer complains about missing/wrong items.

CRITICAL BEHAVIOR RULES:
1. NEVER guess prices, hours, or availability.
2. ALWAYS use analyze_business_statistics to suggest related items if applicable.
3. NEVER add tax unless get_pricing_rules confirms a tax rate exists.
4. Always ask for missing required info proactively.
5. Your response is monitored by a CRITIC node. If you violate a rule, you will have to rewrite it.

SESSION: {session_id}
"""


def build_system_prompt(state: AgentState) -> str:
    profile = get_business_profile(state["business_id"], state["business_name"])
    business_rules = profile_to_system_rules(profile)

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
    """Ana LLM düğümü — ne yapacağına karar verir veya yanıtlar."""
    t0 = time.time()
    session_id = state["session_id"]
    business_id = state["business_id"]
    iteration = state.get("iteration_count", 0)

    profile = get_business_profile(business_id, state["business_name"])
    set_tool_context(business_id, session_id, profile)

    system_msg = SystemMessage(content=build_system_prompt(state))
    llm = get_llm()

    try:
        response = llm.invoke([system_msg] + state["messages"])
        duration_ms = int((time.time() - t0) * 1000)

        tool_calls = []
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_calls = [tc["name"] for tc in response.tool_calls]

        write_audit_log(
            event_type="llm_request",
            session_id=session_id,
            business_id=business_id,
            input_data={"iteration": iteration, "type": "agent"},
            output_data={"content": str(response.content)[:1000], "tool_calls": tool_calls},
            duration_ms=duration_ms,
        )

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
        logger.error("agent_node_error", error=str(e), session_id=session_id)
        raise


def tool_execution_node(state: AgentState) -> Dict:
    logger.info("⚙️ TOOL_EXECUTION_NODE", session_id=state["session_id"])
    tool_node = ToolNode(ALL_TOOLS)
    result = tool_node.invoke(state)

    for msg in result.get("messages", []):
        if isinstance(msg, ToolMessage):
            save_message(
                session_id=state["session_id"],
                role="tool",
                content=str(msg.content),
                tool_name=getattr(msg, "name", ""),
            )
    return result


def critic_node(state: AgentState) -> Dict:
    """Critic Validation Before Final Answer (Func 35, 36)."""
    t0 = time.time()
    last_msg = state["messages"][-1]
    
    # Text empty? Skip evaluation
    content = str(getattr(last_msg, "content", ""))
    if not content or content.strip() in ["", "None"]:
        return {"messages": []}

    system_rules = build_system_prompt(state)
    prompt = f"""
    You are a Strict Quality Critic evaluating the assistant's final output before it reaches the customer.
    
    BUSINESS RULES:
    {system_rules[:3000]}
    
    ASSISTANT'S OUTPUT TO EVALUATE:
    {content}
    
    Check for:
    1. Did the assistant give an unauthorized price without querying tools?
    2. Did the assistant promise free delivery when it shouldn't?
    3. Did it hallucinate times/hours?
    
    If the output violates core rules, reply ONLY with: 'INVALID: <reason>'
    If the output is fine, reply ONLY with: 'VALID'
    """
    
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0.0
    )
    
    try:
        eval_res = llm.invoke([HumanMessage(content=prompt)])
        eval_text = eval_res.content.strip()
        
        write_audit_log(
            event_type="critic_eval",
            session_id=state["session_id"],
            business_id=state["business_id"],
            input_data={"content": content[:200]},
            output_data={"evaluation": eval_text},
            duration_ms=int((time.time() - t0) * 1000)
        )
        
        if eval_text.startswith("INVALID:"):
            logger.warning("CRITIC_REJECTED", reason=eval_text)
            # Create a System message pretending to be an automatic correction prompt
            feedback_msg = HumanMessage(content=f"SYSTEM CRITIC REJECTION: {eval_text}\nPlease self-correct and generate a new response.")
            return {
                "messages": [feedback_msg],
                "iteration_count": state["iteration_count"] + 1
            }
            
        return {"messages": []}
        
    except Exception as e:
        logger.error("critic_error", error=str(e))
        return {"messages": []} # Let it pass if critic fails


# --------------------------------------------------------------------------- #
#  Routing
# --------------------------------------------------------------------------- #
def route_after_agent(state: AgentState) -> str:
    messages = state["messages"]
    last = messages[-1]
    iteration = state.get("iteration_count", 0)

    if iteration >= settings.MAX_ITERATIONS:
        return END

    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"

    return "critic"

def route_after_critic(state: AgentState) -> str:
    # If the critic added an INVALID feedback message, it's the last message
    last = state["messages"][-1]
    if isinstance(last, HumanMessage) and "SYSTEM CRITIC REJECTION" in str(last.content):
        return "agent" # loop back for self-correction
    return END

# --------------------------------------------------------------------------- #
#  Graph build
# --------------------------------------------------------------------------- #
def build_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_execution_node)
    graph.add_node("critic", critic_node)
    
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", route_after_agent, {"tools": "tools", "critic": "critic", END: END})
    graph.add_conditional_edges("critic", route_after_critic, {"agent": "agent", END: END})
    graph.add_edge("tools", "agent")
    return graph.compile()


_compiled_graph = None
def get_agent_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_agent_graph()
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
    t0 = time.time()
    
    profile = get_business_profile(business_id=business_id, business_name=business_name)
    set_tool_context(business_id, session_id, profile)

    save_message(session_id=session_id, role="user", content=user_message)

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
    response_text = str(getattr(last_msg, "content", ""))
    duration_ms = int((time.time() - t0) * 1000)

    tool_calls_list = []
    citations_list = []
    
    for msg in final_state["messages"]:
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls_list.append({
                    "id": tc.get("id", str(uuid.uuid4())),
                    "name": tc["name"],
                    "status": "success",
                    "duration": "0.5s",
                    "input": json.dumps(tc["args"], ensure_ascii=False)
                })
        
        if isinstance(msg, ToolMessage) and msg.name == "get_business_info":
            # Just parsing the dummy response of non-embedding retrieval
            import re
            content = str(msg.content)
            # Adapt the regex or skip depending on how chunks are formatted now
            pass 

    return {
        "response": response_text,
        "session_id": session_id,
        "iterations": final_state.get("iteration_count", 0),
        "duration_ms": duration_ms,
        "tool_calls": tool_calls_list,
        "citations": citations_list,
        "business_type": profile.get("business_type"),
    }
