# AI-generated: Claude Code (claude.ai/code) — tool unit tests
"""
Tool unit tests for drug interaction checking (uses external APIs, no OpenEMR needed).
Patient lookup and medication tests moved to evals (require live OpenEMR).
"""
import pytest
from app.tools.drug_interactions import drug_interaction_check, _resolve_rxcui


class TestDrugInteractionCheck:
    """Drug interaction tool returns structured results."""

    async def test_known_interaction_warfarin_aspirin(self):
        """Warfarin + Aspirin should return interactions."""
        result = await drug_interaction_check.ainvoke(
            {"medications": ["warfarin", "aspirin"]}
        )
        assert result["error"] is None
        assert result["interaction_count"] > 0
        assert result["checked_drug_count"] == 2
        assert result["interactions"][0]["severity"] == "high"
        assert "bleeding" in result["interactions"][0]["description"].lower()

    async def test_needs_two_drugs_minimum(self):
        """Single drug returns helpful message, not an error."""
        result = await drug_interaction_check.ainvoke(
            {"medications": ["metformin"]}
        )
        assert result["error"] is None
        assert result["interactions"] == []
        assert "Need at least 2" in result["message"]

    async def test_unresolved_drug_flagged(self):
        """Nonsense drug name is flagged as unresolved."""
        result = await drug_interaction_check.ainvoke(
            {"medications": ["warfarin", "xyznotadrug123"]}
        )
        assert "xyznotadrug123" in result.get("unresolved_drugs", [])


class TestRxCuiResolution:
    """RxCUI resolution works for common drugs."""

    async def test_resolve_common_drug(self):
        """'metformin' resolves to an RxCUI."""
        rxcui = await _resolve_rxcui("metformin")
        assert rxcui is not None
        assert rxcui.isdigit()
# end AI-generated
