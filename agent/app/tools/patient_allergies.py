# AI-generated: Claude Code (claude.ai/code) — patient allergy list tool
import logging

from langchain_core.tools import tool

from app.tools._openemr_client import OpenEMRApiError, openemr_api

logger = logging.getLogger(__name__)


@tool
async def patient_allergy_list(
    patient_uuid: str,
) -> dict:
    """Get the allergy list for a patient.

    Returns all recorded allergies including title, dates, and diagnosis codes.
    Requires the patient UUID — use patient_lookup first to find it.

    Args:
        patient_uuid: The UUID of the patient (from patient_lookup results)
    """
    try:
        data = await openemr_api(
            "GET", f"/api/patient/{patient_uuid}/allergy"
        )
        allergies = data if data else []
        return {
            "patient_uuid": patient_uuid,
            "allergies": allergies,
        }
    except OpenEMRApiError as e:
        logger.error("Allergy list failed for %s: %s", patient_uuid, e)
        return {
            "error": f"OpenEMR API error ({e.status_code}): {e.detail}",
            "patient_uuid": patient_uuid,
            "allergies": [],
        }
# end AI-generated
