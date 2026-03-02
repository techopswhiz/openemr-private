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
        parts = search_term.strip().split()

        if len(parts) >= 2:
            # "John Smith" -> try fname+lname together first
            fname_part = parts[0]
            lname_part = parts[-1]
            data = await openemr_api(
                "GET", "/api/patient",
                params={"fname": fname_part, "lname": lname_part},
            )
            patients = data.get("data", []) if isinstance(data, dict) else (data or [])
            if patients:
                return {"patients": patients, "total": len(patients)}

            # Try last name alone (handles "Gregory Jacobson" -> "Jacobson")
            data = await openemr_api(
                "GET", "/api/patient", params={"lname": lname_part}
            )
            patients = data.get("data", []) if isinstance(data, dict) else (data or [])
            if patients:
                return {"patients": patients, "total": len(patients)}

            # Try first name alone
            data = await openemr_api(
                "GET", "/api/patient", params={"fname": fname_part}
            )
            patients = data.get("data", []) if isinstance(data, dict) else (data or [])
            if patients:
                return {"patients": patients, "total": len(patients)}
        else:
            # Single term: try last name, then first name
            data = await openemr_api(
                "GET", "/api/patient", params={"lname": search_term}
            )
            patients = data.get("data", []) if isinstance(data, dict) else (data or [])
            if patients:
                return {"patients": patients, "total": len(patients)}

            data = await openemr_api(
                "GET", "/api/patient", params={"fname": search_term}
            )
            patients = data.get("data", []) if isinstance(data, dict) else (data or [])
            if patients:
                return {"patients": patients, "total": len(patients)}

        return {"patients": [], "total": 0}
    except OpenEMRApiError as e:
        logger.error("Patient lookup failed: %s", e)
        return {
            "error": f"OpenEMR API error ({e.status_code}): {e.detail}",
            "patients": [],
            "total": 0,
        }
# end AI-generated
