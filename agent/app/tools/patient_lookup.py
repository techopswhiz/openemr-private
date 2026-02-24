# AI-generated: Claude Code (claude.ai/code) — patient lookup tool
from langchain_core.tools import tool

from app.config import settings
from app.tools._openemr_client import openemr_api

# Demo data for when OpenEMR is not available
DEMO_PATIENTS = [
    {
        "uuid": "946da619-c631-4285-a2c4-2a35eec3f1f4",
        "pid": 1,
        "fname": "John",
        "lname": "Smith",
        "DOB": "1965-03-15",
        "sex": "Male",
        "allergies": "Penicillin",
        "phone_home": "555-0101",
    },
    {
        "uuid": "a27b5f38-7d1e-4c93-b22a-8f1e6d3a9c05",
        "pid": 2,
        "fname": "Maria",
        "lname": "Garcia",
        "DOB": "1978-11-22",
        "sex": "Female",
        "allergies": "Sulfa drugs",
        "phone_home": "555-0102",
    },
    {
        "uuid": "b83c4e29-1f5a-4d87-a63b-9e2f7c4b8d16",
        "pid": 3,
        "fname": "Robert",
        "lname": "Johnson",
        "DOB": "1952-07-08",
        "sex": "Male",
        "allergies": "None",
        "phone_home": "555-0103",
    },
]


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
    if settings.demo_mode:
        term = search_term.lower()
        matches = [
            p for p in DEMO_PATIENTS
            if term in p["fname"].lower()
            or term in p["lname"].lower()
            or term in f"{p['fname']} {p['lname']}".lower()
        ]
        return {
            "mode": "demo",
            "patients": matches,
            "total": len(matches),
        }

    data = await openemr_api(
        "GET", "/api/patient", params={"fname": search_term}
    )
    if data is None:
        # Try last name
        data = await openemr_api(
            "GET", "/api/patient", params={"lname": search_term}
        )
    return {
        "mode": "live",
        "patients": data if data else [],
        "total": len(data) if data else 0,
    }
# end AI-generated
