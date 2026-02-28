# AI-generated: Claude Code (claude.ai/code) — patient vitals tool
from langchain_core.tools import tool

from app.tools._openemr_client import openemr_api


@tool
async def patient_vitals(
    patient_uuid: str,
) -> dict:
    """Get the most recent vitals for a patient.

    Finds the patient's latest encounter and retrieves vitals from it.
    Returns blood pressure, temperature, pulse, respiration, weight, height, BMI, and O2 sat.
    Requires the patient UUID — use patient_lookup first to find it.

    Args:
        patient_uuid: The UUID of the patient (from patient_lookup results)
    """
    # Get encounters for this patient (sorted by date desc by default)
    encounters = await openemr_api(
        "GET", f"/api/patient/{patient_uuid}/encounter"
    )
    if not encounters:
        return {
            "patient_uuid": patient_uuid,
            "vitals": [],
        }

    # Get the pid from the first encounter and iterate encounters for vitals
    all_vitals = []
    for enc in encounters[:5]:  # Check up to 5 most recent encounters
        pid = enc.get("pid")
        eid = enc.get("eid")
        if pid is None or eid is None:
            continue
        vitals_data = await openemr_api(
            "GET", f"/api/patient/{pid}/encounter/{eid}/vital"
        )
        if vitals_data:
            all_vitals.extend(vitals_data if isinstance(vitals_data, list) else [vitals_data])
            break  # Found vitals, stop looking

    return {
        "patient_uuid": patient_uuid,
        "vitals": all_vitals,
    }
# end AI-generated
