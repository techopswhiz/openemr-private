# AI-generated: Claude Code (claude.ai/code) — tool unit tests
"""
MVP eval: 5+ test cases with expected outcomes.
These test tool execution directly, verifying structured results.
"""
import pytest
from app.tools.drug_interactions import drug_interaction_check, _resolve_rxcui
from app.tools.patient_lookup import patient_lookup
from app.tools.patient_medications import patient_medication_list


class TestDrugInteractionCheck:
    """Eval case 1-3: Drug interaction tool returns structured results."""

    async def test_known_interaction_warfarin_aspirin(self):
        """Eval case 1: Warfarin + Aspirin should return interactions."""
        result = await drug_interaction_check.ainvoke(
            {"medications": ["warfarin", "aspirin"]}
        )
        assert result["error"] is None
        assert result["interaction_count"] > 0
        assert result["checked_drug_count"] == 2
        # Warfarin + aspirin is a well-known high-severity interaction
        assert result["interactions"][0]["severity"] == "high"
        assert "bleeding" in result["interactions"][0]["description"].lower()

    async def test_needs_two_drugs_minimum(self):
        """Eval case 2: Single drug returns helpful message, not an error."""
        result = await drug_interaction_check.ainvoke(
            {"medications": ["metformin"]}
        )
        assert result["error"] is None
        assert result["interactions"] == []
        assert "Need at least 2" in result["message"]

    async def test_unresolved_drug_flagged(self):
        """Eval case 3: Nonsense drug name is flagged as unresolved."""
        result = await drug_interaction_check.ainvoke(
            {"medications": ["warfarin", "xyznotadrug123"]}
        )
        assert "xyznotadrug123" in result.get("unresolved_drugs", [])


class TestPatientLookup:
    """Eval case 4: Patient lookup returns structured demographics."""

    async def test_find_patient_by_last_name(self):
        """Eval case 4: Searching 'Smith' finds John Smith with correct fields."""
        result = await patient_lookup.ainvoke({"search_term": "Smith"})
        assert result["mode"] == "demo"
        assert result["total"] >= 1
        patient = result["patients"][0]
        assert patient["fname"] == "John"
        assert patient["lname"] == "Smith"
        assert "uuid" in patient
        assert "DOB" in patient
        assert "allergies" in patient

    async def test_no_match_returns_empty(self):
        """Eval case 5: Non-existent patient returns empty, not error."""
        result = await patient_lookup.ainvoke({"search_term": "Zzzznotaname"})
        assert result["total"] == 0
        assert result["patients"] == []


class TestPatientMedications:
    """Eval case 6: Medication list returns structured prescription data."""

    async def test_get_medications_for_known_patient(self):
        """Eval case 6: John Smith has 3 active medications."""
        uuid = "946da619-c631-4285-a2c4-2a35eec3f1f4"
        result = await patient_medication_list.ainvoke({"patient_uuid": uuid})
        assert result["mode"] == "demo"
        assert result["active_count"] == 3
        drug_names = [m["drug"] for m in result["medications"]]
        assert "Warfarin" in drug_names
        assert "Metformin" in drug_names

    async def test_unknown_patient_returns_empty(self):
        """Eval case 7: Unknown UUID returns empty list, not error."""
        result = await patient_medication_list.ainvoke(
            {"patient_uuid": "00000000-0000-0000-0000-000000000000"}
        )
        assert result["medications"] == []
        assert result["active_count"] == 0


class TestRxCuiResolution:
    """Eval case 8: RxCUI resolution works for common drugs."""

    async def test_resolve_common_drug(self):
        """Eval case 8: 'metformin' resolves to an RxCUI."""
        rxcui = await _resolve_rxcui("metformin")
        assert rxcui is not None
        assert rxcui.isdigit()
# end AI-generated
