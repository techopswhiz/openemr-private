# AI-generated: Claude Code (claude.ai/code) — domain-specific verification layer
from langchain_core.messages import AIMessage, ToolMessage


def verify_interactions(messages: list) -> list[str]:
    """Scan tool results for high-severity drug interactions and return warnings.

    This is the domain-specific verification check required by the MVP.
    It inspects tool call results for drug interaction data and flags
    anything that needs provider attention.
    """
    warnings: list[str] = []

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        if msg.name != "drug_interaction_check":
            continue

        content = msg.artifact if hasattr(msg, "artifact") and msg.artifact else None
        if content is None:
            # Parse from string content if needed
            try:
                import json
                content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
            except (json.JSONDecodeError, TypeError):
                continue

        if not isinstance(content, dict):
            continue

        interactions = content.get("interactions", [])
        for interaction in interactions:
            severity = interaction.get("severity", "").lower()
            drugs = interaction.get("drugs", [])
            desc = interaction.get("description", "")
            drug_str = " + ".join(drugs) if drugs else "unknown drugs"

            if severity in ("high", "severe"):
                warnings.append(
                    f"HIGH SEVERITY INTERACTION: {drug_str} — {desc}"
                )
            elif severity in ("moderate",):
                warnings.append(
                    f"MODERATE INTERACTION: {drug_str} — {desc}"
                )

        unresolved = content.get("unresolved_drugs", [])
        if unresolved:
            warnings.append(
                f"WARNING: Could not verify the following drugs: {', '.join(unresolved)}. "
                "Interaction data may be incomplete."
            )

    return warnings


def verify_allergy_conflicts(messages: list) -> list[str]:
    """Scan tool results for allergy-drug conflicts and return warnings."""
    warnings: list[str] = []

    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        if msg.name != "allergy_drug_cross_check":
            continue

        content = msg.artifact if hasattr(msg, "artifact") and msg.artifact else None
        if content is None:
            try:
                import json
                content = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
            except (json.JSONDecodeError, TypeError):
                continue

        if not isinstance(content, dict):
            continue

        if content.get("has_conflict"):
            for conflict in content.get("conflicts", []):
                allergy = conflict.get("allergy", "unknown")
                drug = conflict.get("proposed_drug", "unknown")
                reason = conflict.get("reason", "")
                warnings.append(
                    f"ALLERGY CONFLICT: {drug} vs allergy '{allergy}' — {reason}"
                )

    return warnings


def verify_response(ai_message: AIMessage, all_messages: list) -> list[str]:
    """Run all verification checks on the agent's final response."""
    warnings = verify_interactions(all_messages)
    warnings.extend(verify_allergy_conflicts(all_messages))

    # Check for unsourced clinical claims in the response
    response_text = ai_message.content if isinstance(ai_message.content, str) else ""
    risky_phrases = [
        "you should take",
        "i recommend",
        "start taking",
        "stop taking",
        "discontinue",
        "increase the dose",
        "decrease the dose",
    ]
    for phrase in risky_phrases:
        if phrase in response_text.lower():
            warnings.append(
                "SCOPE WARNING: Response may contain prescriptive language. "
                "This tool provides information only — clinical decisions must be made by providers."
            )
            break

    return warnings
# end AI-generated
