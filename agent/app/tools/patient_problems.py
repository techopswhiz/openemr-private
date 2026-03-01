# AI-generated: Claude Code (claude.ai/code) — patient problem list tool
import logging

from langchain_core.tools import tool

from app.tools._openemr_client import OpenEMRApiError, openemr_api

logger = logging.getLogger(__name__)


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
    try:
        data = await openemr_api(
            "GET", f"/api/patient/{patient_uuid}/medical_problem"
        )
        problems = data.get("data", []) if isinstance(data, dict) else (data or [])
        return {
            "patient_uuid": patient_uuid,
            "problems": problems,
        }
    except OpenEMRApiError as e:
        logger.error("Problem list failed for %s: %s", patient_uuid, e)
        return {
            "error": f"OpenEMR API error ({e.status_code}): {e.detail}",
            "patient_uuid": patient_uuid,
            "problems": [],
        }
# end AI-generated
