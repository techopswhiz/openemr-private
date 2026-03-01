# AI-generated: Claude Code (claude.ai/code) — patient lookup tool
import logging

from langchain_core.tools import tool

from app.tools._openemr_client import OpenEMRApiError, openemr_api

logger = logging.getLogger(__name__)


@tool
async def patient_lookup(
    search_term: str,
) -> dict:
    """Search for a patient by name in OpenEMR.

    Returns matching patient demographics including name, DOB, sex, and allergies.
    Use this to find a patient before checking their medications.

    Args:
        search_term: Patient name or partial name to search for (e.g., "Smith" or "John Smith")
    """
    try:
        # Try last name first (most common search pattern)
        data = await openemr_api(
            "GET", "/api/patient", params={"lname": search_term}
        )
        patients = data.get("data", []) if isinstance(data, dict) else (data or [])

        if not patients:
            # Fall back to first name search
            data = await openemr_api(
                "GET", "/api/patient", params={"fname": search_term}
            )
            patients = data.get("data", []) if isinstance(data, dict) else (data or [])

        return {
            "patients": patients,
            "total": len(patients),
        }
    except OpenEMRApiError as e:
        logger.error("Patient lookup failed: %s", e)
        return {
            "error": f"OpenEMR API error ({e.status_code}): {e.detail}",
            "patients": [],
            "total": 0,
        }
# end AI-generated
