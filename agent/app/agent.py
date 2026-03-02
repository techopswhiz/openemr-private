# AI-generated: Claude Code (claude.ai/code) — LangGraph agent definition
import json
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import settings
from app.memory import get_history, save_history
from app.models import Citation, Finding, ReasoningStep, StructuredResponse
from app.tools import all_tools
from app.verification import verify_response

SYSTEM_PROMPT = """You are a clinical decision support assistant integrated with OpenEMR.
You help healthcare providers with medication management, patient lookups, and drug interaction checking.

CAPABILITIES:
- Look up patients by name
- Retrieve a patient's active medication list
- Retrieve a patient's allergy list
- Retrieve a patient's medical problem list
- Retrieve a patient's most recent vitals
- Retrieve a patient's appointments
- Check drug-drug interactions between medications using the NIH NLM database
- Cross-check a proposed drug against a patient's allergies

RULES:
1. When asked about a patient, always look them up first using patient_lookup.
2. When checking interactions, get the patient's current medications first, then check all of them together.
3. Always report interaction severity levels clearly.
4. Before suggesting a new medication, use allergy_drug_cross_check to verify safety.
5. NEVER make treatment recommendations. Provide information — the provider decides.
6. If you cannot find a drug or patient, say so clearly. Do not guess.
7. Cite the NLM/NIH as the source for drug interaction data.
8. When multiple interactions are found, list each one with its severity.

REASONING:
Think step by step. For each action you take, explain WHY you are doing it.
When you present your final answer:
- Summarize the key finding first
- List each discrete finding with its severity
- Cite the source for every clinical claim (NLM RxNorm, FDA Drug Label, OpenEMR patient record)
- Be explicit about what you checked and what you did NOT check"""


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    verification_warnings: list[str]
    tool_calls_log: list[dict]
    structured: dict | None


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


def format_node(state: AgentState) -> dict:
    """Extract structured data from the conversation: reasoning steps, findings, citations."""
    messages = state["messages"]
    tool_log = state.get("tool_calls_log") or []
    warnings = state.get("verification_warnings") or []

    # Build reasoning steps from tool call log
    reasoning: list[dict] = []
    for call in tool_log:
        tool_name = call.get("tool", "")
        args = call.get("args", {})

        if tool_name == "patient_lookup":
            action = f"Searched for patient matching '{args.get('name', '')}'"
        elif tool_name == "patient_medication_list":
            action = "Retrieved patient's medication list"
        elif tool_name == "patient_allergy_list":
            action = "Retrieved patient's allergy list"
        elif tool_name == "patient_problem_list":
            action = "Retrieved patient's problem list"
        elif tool_name == "patient_vitals":
            action = "Retrieved patient's recent vitals"
        elif tool_name == "patient_appointments":
            action = "Retrieved patient's appointments"
        elif tool_name == "drug_interaction_check":
            meds = args.get("medications", [])
            action = f"Checked drug interactions between: {', '.join(meds)}"
        elif tool_name == "allergy_drug_cross_check":
            action = f"Checked allergy conflict for '{args.get('proposed_drug', '')}'"
        else:
            action = f"Called {tool_name}"

        # Find the corresponding ToolMessage result
        result_summary = ""
        for msg in messages:
            if hasattr(msg, "name") and msg.name == tool_name:
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                # Truncate long results
                result_summary = content[:200] + "..." if len(content) > 200 else content

        reasoning.append(ReasoningStep(action=action, result=result_summary).model_dump())

    # Extract findings from tool results
    findings: list[dict] = []
    citations: list[dict] = []

    for msg in messages:
        if not hasattr(msg, "name"):
            continue

        if msg.name == "drug_interaction_check":
            try:
                content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                if not isinstance(content, dict):
                    continue
                for interaction in content.get("interactions", []):
                    drugs = interaction.get("drugs", [])
                    findings.append(Finding(
                        category="interaction",
                        severity=interaction.get("severity"),
                        summary=f"{' + '.join(drugs)}: {interaction.get('description', '')[:100]}",
                        details=interaction.get("description", ""),
                    ).model_dump())
                    citations.append(Citation(
                        claim=f"{' + '.join(drugs)} interaction",
                        source=interaction.get("source", "FDA Drug Label"),
                    ).model_dump())
                for drug in content.get("unresolved_drugs", []):
                    findings.append(Finding(
                        category="warning",
                        severity="low",
                        summary=f"Could not verify drug: {drug}",
                    ).model_dump())
            except (json.JSONDecodeError, TypeError):
                pass

        elif msg.name == "allergy_drug_cross_check":
            try:
                content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
                if not isinstance(content, dict):
                    continue
                for conflict in content.get("conflicts", []):
                    findings.append(Finding(
                        category="allergy_conflict",
                        severity="high",
                        summary=f"Allergy conflict: {conflict.get('proposed_drug', '')} vs {conflict.get('allergy', '')}",
                        details=conflict.get("reason", ""),
                    ).model_dump())
                    citations.append(Citation(
                        claim=f"{conflict.get('proposed_drug', '')} allergy conflict",
                        source="OpenEMR patient allergy record",
                    ).model_dump())
            except (json.JSONDecodeError, TypeError):
                pass

    # Add verification warnings as findings
    for warning in warnings:
        severity = "high" if "HIGH SEVERITY" in warning or "ALLERGY CONFLICT" in warning else "moderate"
        findings.append(Finding(
            category="warning",
            severity=severity,
            summary=warning,
        ).model_dump())

    # Build the final AI response summary
    ai_messages = [m for m in messages if isinstance(m, AIMessage) and not m.tool_calls]
    response_text = ai_messages[-1].content if ai_messages else ""

    # Use first sentence of the LLM response as summary, full text as-is
    summary = response_text.split(".")[0] + "." if "." in response_text else response_text
    if len(summary) > 200:
        summary = summary[:197] + "..."

    structured = StructuredResponse(
        summary=summary,
        reasoning=[ReasoningStep(**r) for r in reasoning],
        findings=[Finding(**f) for f in findings],
        citations=[Citation(**c) for c in citations],
    ).model_dump()

    return {"structured": structured}


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
    graph.add_node("format", format_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "log_calls", "verify": "verify"})
    graph.add_edge("log_calls", "tools")
    graph.add_edge("tools", "agent")
    graph.add_edge("verify", "format")
    graph.add_edge("format", END)

    return graph.compile()


# Singleton compiled graph
agent_graph = build_graph()


async def run_agent(message: str, session_id: str = "default") -> dict:
    """Run the agent with conversation history."""
    history = get_history(session_id)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + history + [HumanMessage(content=message)]

    import uuid as _uuid
    run_id = str(_uuid.uuid4())

    result = await agent_graph.ainvoke(
        {
            "messages": messages,
            "verification_warnings": [],
            "tool_calls_log": [],
            "structured": None,
        },
        config={"run_id": run_id},
    )

    # Save updated history (skip system prompt)
    save_history(session_id, result["messages"][1:])

    # Extract final response
    ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and not m.tool_calls]
    response_text = ai_messages[-1].content if ai_messages else "I could not generate a response."

    return {
        "response": response_text,
        "structured": result.get("structured"),
        "session_id": session_id,
        "tool_calls": result.get("tool_calls_log", []),
        "verification_warnings": result.get("verification_warnings", []),
        "run_id": run_id,
    }
# end AI-generated
