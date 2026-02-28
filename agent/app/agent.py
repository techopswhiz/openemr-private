# AI-generated: Claude Code (claude.ai/code) — LangGraph agent definition
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import settings
from app.memory import get_history, save_history
from app.tools import all_tools
from app.verification import verify_response

SYSTEM_PROMPT = """You are a clinical decision support assistant integrated with OpenEMR.
You help healthcare providers with medication management, patient lookups, and drug interaction checking.

CAPABILITIES:
- Look up patients by name
- Retrieve a patient's active medication list
- Check drug-drug interactions between medications using the NIH NLM database

RULES:
1. When asked about a patient, always look them up first using patient_lookup.
2. When checking interactions, get the patient's current medications first, then check all of them together.
3. Always report interaction severity levels clearly.
4. NEVER make treatment recommendations. Provide information — the provider decides.
5. If you cannot find a drug or patient, say so clearly. Do not guess.
6. Cite the NLM/NIH as the source for drug interaction data.
7. When multiple interactions are found, list each one with its severity."""


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    verification_warnings: list[str]
    tool_calls_log: list[dict]


def _build_llm():
    return ChatOpenAI(
        model=settings.xai_model,
        api_key=settings.xai_api_key,
        base_url=settings.xai_base_url,
        temperature=0,
    )


def agent_node(state: AgentState) -> dict:
    """Call the LLM with tools bound."""
    llm = _build_llm().bind_tools(all_tools)
    response = llm.invoke(state["messages"])
    return {"messages": [response]}


def verification_node(state: AgentState) -> dict:
    """Run domain-specific verification on the final response."""
    messages = state["messages"]
    last = messages[-1]
    warnings: list[str] = []
    if isinstance(last, AIMessage) and not last.tool_calls:
        warnings = verify_response(last, messages)
    return {"verification_warnings": warnings}


def log_tool_calls(state: AgentState) -> dict:
    """Extract tool call info for observability."""
    messages = state["messages"]
    last = messages[-1]
    calls: list[dict] = list(state.get("tool_calls_log") or [])
    if isinstance(last, AIMessage) and last.tool_calls:
        for tc in last.tool_calls:
            calls.append({"tool": tc["name"], "args": tc["args"]})
    return {"tool_calls_log": calls}


def should_continue(state: AgentState) -> str:
    """Route after agent node: continue to tools or verify and finish."""
    result = tools_condition(state)
    if result == END:
        return "verify"
    return "tools"


def build_graph() -> StateGraph:
    tool_node = ToolNode(all_tools)

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("log_calls", log_tool_calls)
    graph.add_node("tools", tool_node)
    graph.add_node("verify", verification_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "log_calls", "verify": "verify"})
    graph.add_edge("log_calls", "tools")
    graph.add_edge("tools", "agent")
    graph.add_edge("verify", END)

    return graph.compile()


# Singleton compiled graph
agent_graph = build_graph()


async def run_agent(message: str, session_id: str = "default") -> dict:
    """Run the agent with conversation history."""
    history = get_history(session_id)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + history + [HumanMessage(content=message)]

    result = await agent_graph.ainvoke({
        "messages": messages,
        "verification_warnings": [],
        "tool_calls_log": [],
    })

    # Save updated history (skip system prompt)
    save_history(session_id, result["messages"][1:])

    # Extract final response
    ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and not m.tool_calls]
    response_text = ai_messages[-1].content if ai_messages else "I could not generate a response."

    return {
        "response": response_text,
        "session_id": session_id,
        "tool_calls": result.get("tool_calls_log", []),
        "verification_warnings": result.get("verification_warnings", []),
    }
# end AI-generated
