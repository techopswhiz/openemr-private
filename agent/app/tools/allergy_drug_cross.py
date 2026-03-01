# AI-generated: Claude Code (claude.ai/code) — allergy-drug cross-check tool
import logging

from langchain_core.tools import tool

from app.tools._openemr_client import OpenEMRApiError, openemr_api

logger = logging.getLogger(__name__)

# Drug-class mappings for cross-referencing allergies against proposed drugs.
# Keys are allergy keywords (lowercased), values are lists of drug names in that class.
DRUG_CLASS_MAP: dict[str, list[str]] = {
    "penicillin": [
        "amoxicillin", "ampicillin", "penicillin", "piperacillin",
        "nafcillin", "oxacillin", "dicloxacillin", "augmentin",
        "amoxicillin/clavulanate", "ampicillin/sulbactam",
    ],
    "sulfa": [
        "sulfamethoxazole", "trimethoprim/sulfamethoxazole", "bactrim",
        "sulfasalazine", "sulfadiazine", "dapsone",
    ],
    "cephalosporin": [
        "cephalexin", "cefazolin", "ceftriaxone", "cefdinir",
        "cefuroxime", "cefepime", "ceftazidime", "cefpodoxime",
    ],
    "nsaid": [
        "ibuprofen", "naproxen", "aspirin", "meloxicam", "diclofenac",
        "indomethacin", "ketorolac", "piroxicam", "celecoxib",
    ],
    "statin": [
        "atorvastatin", "simvastatin", "rosuvastatin", "pravastatin",
        "lovastatin", "fluvastatin", "pitavastatin",
    ],
    "ace inhibitor": [
        "lisinopril", "enalapril", "ramipril", "benazepril",
        "captopril", "fosinopril", "quinapril", "trandolapril",
    ],
    "opioid": [
        "morphine", "oxycodone", "hydrocodone", "fentanyl",
        "codeine", "tramadol", "methadone", "hydromorphone",
    ],
    "fluoroquinolone": [
        "ciprofloxacin", "levofloxacin", "moxifloxacin",
        "ofloxacin", "norfloxacin",
    ],
    "macrolide": [
        "azithromycin", "clarithromycin", "erythromycin",
    ],
    "tetracycline": [
        "doxycycline", "tetracycline", "minocycline",
    ],
}


def _find_class_conflicts(allergy_title: str, proposed_drug: str) -> list[dict]:
    """Check if a proposed drug conflicts with a recorded allergy via drug-class mapping."""
    conflicts = []
    allergy_lower = allergy_title.lower()
    drug_lower = proposed_drug.lower()

    for class_name, drugs_in_class in DRUG_CLASS_MAP.items():
        # Check if the allergy mentions this drug class or any drug in the class
        allergy_matches_class = (
            class_name in allergy_lower
            or any(drug in allergy_lower for drug in drugs_in_class)
        )
        # Check if the proposed drug is in this class
        drug_in_class = drug_lower in drugs_in_class

        if allergy_matches_class and drug_in_class:
            conflicts.append({
                "allergy": allergy_title,
                "drug_class": class_name,
                "proposed_drug": proposed_drug,
                "reason": f"Patient has '{allergy_title}' allergy; "
                          f"'{proposed_drug}' is in the {class_name} class.",
            })

    # Direct name match (allergy title contains the drug name or vice versa)
    if drug_lower in allergy_lower or allergy_lower in drug_lower:
        conflicts.append({
            "allergy": allergy_title,
            "drug_class": "direct match",
            "proposed_drug": proposed_drug,
            "reason": f"Patient has '{allergy_title}' allergy; "
                      f"direct match with proposed drug '{proposed_drug}'.",
        })

    return conflicts


@tool
async def allergy_drug_cross_check(
    patient_uuid: str,
    proposed_drug: str,
) -> dict:
    """Check if a proposed drug conflicts with a patient's recorded allergies.

    Cross-references the patient's allergy list against drug-class mappings
    to identify potential allergic reactions. Use before prescribing.

    Args:
        patient_uuid: The UUID of the patient (from patient_lookup results)
        proposed_drug: The drug name to check against allergies (e.g., "amoxicillin")
    """
    try:
        data = await openemr_api(
            "GET", f"/api/patient/{patient_uuid}/allergy"
        )
        allergies = data if data else []
    except OpenEMRApiError as e:
        logger.error("Allergy cross-check failed for %s: %s", patient_uuid, e)
        return {
            "error": f"OpenEMR API error ({e.status_code}): {e.detail}",
            "patient_uuid": patient_uuid,
            "checked_drug": proposed_drug,
            "has_conflict": False,
            "conflicts": [],
            "allergies_checked": 0,
        }

    all_conflicts = []
    for allergy in allergies:
        title = allergy.get("title", "")
        if not title:
            continue
        conflicts = _find_class_conflicts(title, proposed_drug)
        all_conflicts.extend(conflicts)

    return {
        "patient_uuid": patient_uuid,
        "checked_drug": proposed_drug,
        "has_conflict": len(all_conflicts) > 0,
        "conflicts": all_conflicts,
        "allergies_checked": len(allergies),
    }
# end AI-generated
