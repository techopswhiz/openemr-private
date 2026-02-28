# AI-generated: Claude Code (claude.ai/code) — patient medication list tool
from langchain_core.tools import tool

from app.tools._openemr_client import openemr_api


@tool
async def patient_medication_list(
    patient_uuid: str,
) -> dict:
    """Get the active medication list for a patient.

    Returns all current prescriptions including drug name, dosage, frequency, and status.
    Requires the patient UUID — use patient_lookup first to find it.

    Args:
        patient_uuid: The UUID of the patient (from patient_lookup results)
    """
    data = await openemr_api(
        "GET", f"/api/patient/{patient_uuid}/medication"
    )
    meds = data if data else []
    return {
        "patient_uuid": patient_uuid,
        "medications": meds,
        "active_count": len(meds),
    }
# end AI-generated
