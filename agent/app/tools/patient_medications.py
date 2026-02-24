# AI-generated: Claude Code (claude.ai/code) — patient medication list tool
from langchain_core.tools import tool

from app.config import settings
from app.tools._openemr_client import openemr_api

# Demo medication data keyed by patient UUID
DEMO_MEDICATIONS: dict[str, list[dict]] = {
    # John Smith — on warfarin + lisinopril + metformin
    "946da619-c631-4285-a2c4-2a35eec3f1f4": [
        {
            "drug": "Warfarin",
            "rxnorm_code": "11289",
            "dosage": "5mg",
            "frequency": "once daily",
            "status": "active",
            "start_date": "2024-01-15",
        },
        {
            "drug": "Lisinopril",
            "rxnorm_code": "29046",
            "dosage": "10mg",
            "frequency": "once daily",
            "status": "active",
            "start_date": "2023-06-01",
        },
        {
            "drug": "Metformin",
            "rxnorm_code": "6809",
            "dosage": "500mg",
            "frequency": "twice daily",
            "status": "active",
            "start_date": "2023-03-10",
        },
    ],
    # Maria Garcia — on omeprazole + atorvastatin
    "a27b5f38-7d1e-4c93-b22a-8f1e6d3a9c05": [
        {
            "drug": "Omeprazole",
            "rxnorm_code": "7646",
            "dosage": "20mg",
            "frequency": "once daily",
            "status": "active",
            "start_date": "2024-02-20",
        },
        {
            "drug": "Atorvastatin",
            "rxnorm_code": "83367",
            "dosage": "40mg",
            "frequency": "once daily",
            "status": "active",
            "start_date": "2023-09-15",
        },
    ],
    # Robert Johnson — on amlodipine + hydrochlorothiazide + aspirin
    "b83c4e29-1f5a-4d87-a63b-9e2f7c4b8d16": [
        {
            "drug": "Amlodipine",
            "rxnorm_code": "17767",
            "dosage": "5mg",
            "frequency": "once daily",
            "status": "active",
            "start_date": "2022-11-01",
        },
        {
            "drug": "Hydrochlorothiazide",
            "rxnorm_code": "5487",
            "dosage": "25mg",
            "frequency": "once daily",
            "status": "active",
            "start_date": "2022-11-01",
        },
        {
            "drug": "Aspirin",
            "rxnorm_code": "1191",
            "dosage": "81mg",
            "frequency": "once daily",
            "status": "active",
            "start_date": "2020-05-15",
        },
    ],
}


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
    if settings.demo_mode:
        meds = DEMO_MEDICATIONS.get(patient_uuid, [])
        return {
            "mode": "demo",
            "patient_uuid": patient_uuid,
            "medications": meds,
            "active_count": sum(1 for m in meds if m["status"] == "active"),
        }

    data = await openemr_api(
        "GET", f"/api/patient/{patient_uuid}/medication"
    )
    meds = data if data else []
    return {
        "mode": "live",
        "patient_uuid": patient_uuid,
        "medications": meds,
        "active_count": len(meds),
    }
# end AI-generated
