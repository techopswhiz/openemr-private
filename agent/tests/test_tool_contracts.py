# AI-generated: Claude Code (claude.ai/code) — tool contract tests
"""
Tool contract tests: verify each tool returns the correct response shape,
key presence, and types against a live OpenEMR instance.
Skipped when OPENEMR_CLIENT_ID is not set.
"""
import os
import pathlib

import pytest
import yaml

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENEMR_CLIENT_ID"),
    reason="OPENEMR_CLIENT_ID not set — skipping tool contract tests",
)

from app.tools.drug_interactions import drug_interaction_check
from app.tools.patient_lookup import patient_lookup
from app.tools.patient_medications import patient_medication_list

# New tools — imported when available, None otherwise
try:
    from app.tools.patient_allergies import patient_allergy_list
except ImportError:
    patient_allergy_list = None
try:
    from app.tools.patient_problems import patient_problem_list
except ImportError:
    patient_problem_list = None
try:
    from app.tools.patient_vitals import patient_vitals
except ImportError:
    patient_vitals = None
try:
    from app.tools.patient_appointments import patient_appointments
except ImportError:
    patient_appointments = None
try:
    from app.tools.allergy_drug_cross import allergy_drug_cross_check
except ImportError:
    allergy_drug_cross_check = None

TOOL_MAP = {
    "patient_lookup": patient_lookup,
    "patient_medication_list": patient_medication_list,
    "drug_interaction_check": drug_interaction_check,
    "patient_allergy_list": patient_allergy_list,
    "patient_problem_list": patient_problem_list,
    "patient_vitals": patient_vitals,
    "patient_appointments": patient_appointments,
    "allergy_drug_cross_check": allergy_drug_cross_check,
}

TYPE_MAP = {
    "list": list,
    "int": int,
    "str": str,
    "bool": bool,
    "float": float,
}

GOLDEN_DIR = pathlib.Path(__file__).parent / "golden_sets"


def _load_all_cases():
    """Load all YAML golden sets and yield (file_stem, tool_name, case) tuples."""
    cases = []
    for yaml_file in sorted(GOLDEN_DIR.glob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        tool_name = data["tool"]
        for case in data["cases"]:
            cases.append(pytest.param(
                tool_name, case,
                id=f"{yaml_file.stem}::{case['id']}",
            ))
    return cases


_cached_uuid: str | None = None
_uuid_resolved = False


async def _get_first_patient_uuid() -> str | None:
    """Resolve a real patient UUID by searching for 'a' (broad match).

    Cached across calls to avoid repeated API hits.
    """
    global _cached_uuid, _uuid_resolved
    if _uuid_resolved:
        return _cached_uuid

    try:
        result = await patient_lookup.ainvoke({"search_term": "a"})
        patients = result.get("patients", [])
        if patients:
            _cached_uuid = patients[0]["uuid"]
    except Exception:
        _cached_uuid = None

    _uuid_resolved = True
    return _cached_uuid


def _needs_uuid(args: dict) -> bool:
    """Check if any arg value requires UUID resolution."""
    return any(
        isinstance(v, str) and v == "__FIRST_PATIENT_UUID__"
        for v in args.values()
    )


async def _resolve_args(args: dict) -> dict:
    """Replace __FIRST_PATIENT_UUID__ placeholders with a real UUID."""
    resolved = {}
    uuid = None
    for k, v in args.items():
        if isinstance(v, str) and v == "__FIRST_PATIENT_UUID__":
            if uuid is None:
                uuid = await _get_first_patient_uuid()
            if uuid is None:
                pytest.skip("No patients in OpenEMR — cannot resolve UUID")
            resolved[k] = uuid
        else:
            resolved[k] = v
    return resolved


@pytest.mark.parametrize("tool_name,case", _load_all_cases())
async def test_golden_case(tool_name, case):
    tool_fn = TOOL_MAP.get(tool_name)
    if tool_fn is None:
        pytest.skip(f"Tool {tool_name} not yet implemented")

    args = await _resolve_args(case["args"])

    # Invoke the tool
    result = await tool_fn.ainvoke(args)

    # 1. must_contain_keys
    if "must_contain_keys" in case:
        for key in case["must_contain_keys"]:
            assert key in result, f"Missing key '{key}' in result: {list(result.keys())}"

    # 2. field_types
    if "field_types" in case:
        for key, expected_type_name in case["field_types"].items():
            assert key in result, f"Missing key '{key}' for type check"
            expected_type = TYPE_MAP[expected_type_name]
            assert isinstance(result[key], expected_type), (
                f"Expected {key} to be {expected_type_name}, got {type(result[key]).__name__}"
            )

    # 3. result_list_field + item_must_contain_keys
    if "result_list_field" in case and "item_must_contain_keys" in case:
        items = result[case["result_list_field"]]
        if len(items) > 0:
            first_item = items[0]
            for key in case["item_must_contain_keys"]:
                assert key in first_item, (
                    f"Missing key '{key}' in list item: {list(first_item.keys())}"
                )

    # 4. must_not_error
    if case.get("must_not_error"):
        error_val = result.get("error")
        assert error_val is None, f"Unexpected error: {error_val}"

    # 5. expect_total_zero
    if case.get("expect_total_zero"):
        assert result.get("total") == 0, f"Expected total=0, got {result.get('total')}"

    # 6. expect_empty_list_field
    if "expect_empty_list_field" in case:
        field = case["expect_empty_list_field"]
        assert result[field] == [], f"Expected {field} to be empty, got {result[field]}"

    # 7. expect_list_nonempty
    if case.get("expect_list_nonempty") and "result_list_field" in case:
        field = case["result_list_field"]
        assert len(result[field]) > 0, f"Expected {field} to be non-empty"

    # 8. must_contain_substring
    if "must_contain_substring" in case:
        for key, substring in case["must_contain_substring"].items():
            assert substring.lower() in str(result.get(key, "")).lower(), (
                f"Expected '{substring}' in {key}, got: {result.get(key)}"
            )

    # 9. expect_list_contains
    if "expect_list_contains" in case:
        for key, value in case["expect_list_contains"].items():
            assert value in result.get(key, []), (
                f"Expected '{value}' in {key}, got: {result.get(key)}"
            )

    # 10. expect_field_value
    if "expect_field_value" in case:
        for key, expected_val in case["expect_field_value"].items():
            assert result[key] == expected_val, (
                f"Expected {key}={expected_val}, got {result[key]}"
            )
# end AI-generated
