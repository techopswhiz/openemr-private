# AI-generated: Claude Code (claude.ai/code) — patient appointments tool
import logging

from langchain_core.tools import tool

from app.tools._openemr_client import OpenEMRApiError, openemr_api

logger = logging.getLogger(__name__)


@tool
async def patient_appointments(
    patient_uuid: str,
) -> dict:
    """Get appointments for a patient.

    Returns all scheduled appointments including date, time, status, and provider.
    Requires the patient UUID — use patient_lookup first to find it.

    Args:
        patient_uuid: The UUID of the patient (from patient_lookup results)
    """
    try:
        data = await openemr_api(
            "GET", f"/api/patient/{patient_uuid}/appointment"
        )
        appointments = data if data else []
        return {
            "patient_uuid": patient_uuid,
            "appointments": appointments,
        }
    except OpenEMRApiError as e:
        logger.error("Appointments retrieval failed for %s: %s", patient_uuid, e)
        return {
            "error": f"OpenEMR API error ({e.status_code}): {e.detail}",
            "patient_uuid": patient_uuid,
            "appointments": [],
        }
# end AI-generated
