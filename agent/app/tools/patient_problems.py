# AI-generated: Claude Code (claude.ai/code) — patient problem list tool
from langchain_core.tools import tool

from app.tools._openemr_client import openemr_api


@tool
async def patient_problem_list(
    patient_uuid: str,
) -> dict:
    """Get the medical problem list for a patient.

    Returns all recorded medical problems / conditions including title, dates, and diagnosis codes.
    Requires the patient UUID — use patient_lookup first to find it.

    Args:
        patient_uuid: The UUID of the patient (from patient_lookup results)
    """
    data = await openemr_api(
        "GET", f"/api/patient/{patient_uuid}/medical_problem"
    )
    problems = data if data else []
    return {
        "patient_uuid": patient_uuid,
        "problems": problems,
    }
# end AI-generated
