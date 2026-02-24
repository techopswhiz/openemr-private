# AI-generated: Claude Code (claude.ai/code) — drug interaction tool
# Uses curated interaction DB + OpenFDA label data + NLM RxNorm for drug resolution
import httpx
from langchain_core.tools import tool

RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"
OPENFDA_BASE = "https://api.fda.gov/drug/label.json"

# Curated interaction database — common clinically significant drug pairs.
# Source: FDA drug labeling, clinical pharmacology references.
# Keyed by frozenset of lowercased generic drug names.
KNOWN_INTERACTIONS: dict[frozenset[str], dict] = {
    frozenset({"warfarin", "aspirin"}): {
        "severity": "high",
        "description": "Increased risk of bleeding. Aspirin inhibits platelet aggregation and may potentiate the anticoagulant effect of warfarin.",
        "source": "FDA Drug Label",
    },
    frozenset({"warfarin", "ibuprofen"}): {
        "severity": "high",
        "description": "NSAIDs including ibuprofen increase risk of GI bleeding and may enhance the anticoagulant effect of warfarin.",
        "source": "FDA Drug Label",
    },
    frozenset({"warfarin", "naproxen"}): {
        "severity": "high",
        "description": "NSAIDs including naproxen increase risk of GI bleeding and may enhance the anticoagulant effect of warfarin.",
        "source": "FDA Drug Label",
    },
    frozenset({"warfarin", "omeprazole"}): {
        "severity": "moderate",
        "description": "Omeprazole may inhibit CYP2C19 and increase warfarin levels. Monitor INR closely.",
        "source": "FDA Drug Label",
    },
    frozenset({"warfarin", "fluconazole"}): {
        "severity": "high",
        "description": "Fluconazole inhibits CYP2C9, significantly increasing warfarin levels and bleeding risk.",
        "source": "FDA Drug Label",
    },
    frozenset({"warfarin", "amiodarone"}): {
        "severity": "high",
        "description": "Amiodarone inhibits CYP2C9, significantly increasing warfarin effect. Reduce warfarin dose by 33-50%.",
        "source": "FDA Drug Label",
    },
    frozenset({"metformin", "alcohol"}): {
        "severity": "high",
        "description": "Alcohol potentiates the effect of metformin on lactate metabolism, increasing the risk of lactic acidosis.",
        "source": "FDA Drug Label",
    },
    frozenset({"lisinopril", "potassium"}): {
        "severity": "moderate",
        "description": "ACE inhibitors increase serum potassium. Concomitant potassium supplements may cause hyperkalemia.",
        "source": "FDA Drug Label",
    },
    frozenset({"lisinopril", "spironolactone"}): {
        "severity": "moderate",
        "description": "Both ACE inhibitors and spironolactone increase potassium. Combined use raises hyperkalemia risk.",
        "source": "FDA Drug Label",
    },
    frozenset({"metformin", "contrast dye"}): {
        "severity": "high",
        "description": "Iodinated contrast media with metformin may cause lactic acidosis. Hold metformin before and 48h after contrast.",
        "source": "FDA Drug Label / ACR Guidelines",
    },
    frozenset({"simvastatin", "amiodarone"}): {
        "severity": "high",
        "description": "Amiodarone increases simvastatin levels. Max simvastatin dose 20mg/day when combined. Risk of rhabdomyolysis.",
        "source": "FDA Drug Label",
    },
    frozenset({"simvastatin", "amlodipine"}): {
        "severity": "moderate",
        "description": "Amlodipine increases simvastatin exposure. Max simvastatin dose 20mg/day when combined.",
        "source": "FDA Drug Label",
    },
    frozenset({"atorvastatin", "clarithromycin"}): {
        "severity": "high",
        "description": "Clarithromycin inhibits CYP3A4, significantly increasing statin levels and risk of myopathy.",
        "source": "FDA Drug Label",
    },
    frozenset({"clopidogrel", "omeprazole"}): {
        "severity": "high",
        "description": "Omeprazole reduces the antiplatelet effect of clopidogrel by inhibiting CYP2C19 activation. Avoid combination.",
        "source": "FDA Drug Label",
    },
    frozenset({"methotrexate", "ibuprofen"}): {
        "severity": "high",
        "description": "NSAIDs reduce renal clearance of methotrexate, increasing toxicity risk (pancytopenia, renal failure).",
        "source": "FDA Drug Label",
    },
    frozenset({"lithium", "ibuprofen"}): {
        "severity": "high",
        "description": "NSAIDs reduce renal lithium clearance, causing elevated lithium levels and potential toxicity.",
        "source": "FDA Drug Label",
    },
    frozenset({"ssri", "tramadol"}): {
        "severity": "high",
        "description": "Combined serotonergic drugs increase risk of serotonin syndrome. Monitor for agitation, tremor, hyperthermia.",
        "source": "FDA Drug Label",
    },
    frozenset({"fluoxetine", "tramadol"}): {
        "severity": "high",
        "description": "Fluoxetine + tramadol increases serotonin syndrome risk. Both have serotonergic activity.",
        "source": "FDA Drug Label",
    },
    frozenset({"sertraline", "tramadol"}): {
        "severity": "high",
        "description": "Sertraline + tramadol increases serotonin syndrome risk. Both have serotonergic activity.",
        "source": "FDA Drug Label",
    },
    frozenset({"ciprofloxacin", "tizanidine"}): {
        "severity": "high",
        "description": "Ciprofloxacin inhibits CYP1A2, causing dramatic increases in tizanidine levels. Contraindicated.",
        "source": "FDA Drug Label",
    },
    frozenset({"warfarin", "metronidazole"}): {
        "severity": "high",
        "description": "Metronidazole inhibits warfarin metabolism, significantly increasing anticoagulant effect and bleeding risk.",
        "source": "FDA Drug Label",
    },
    frozenset({"amlodipine", "simvastatin"}): {
        "severity": "moderate",
        "description": "Amlodipine increases simvastatin exposure. Limit simvastatin to 20mg/day with amlodipine.",
        "source": "FDA Drug Label",
    },
}


async def _resolve_rxcui(drug_name: str) -> str | None:
    """Resolve a drug name to an RxCUI using the NLM RxNorm API (still active)."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{RXNORM_BASE}/rxcui.json",
            params={"name": drug_name, "search": 2},
        )
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("idGroup", {}).get("rxnormId")
        if candidates:
            return candidates[0]

        # Try approximate match as fallback
        resp = await client.get(
            f"{RXNORM_BASE}/approximateTerm.json",
            params={"term": drug_name, "maxEntries": 1},
        )
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("approximateGroup", {}).get("candidate", [])
        if candidates:
            return candidates[0].get("rxcui")
    return None


async def _get_fda_interaction_text(drug_name: str) -> str | None:
    """Fetch drug interaction section from OpenFDA label data."""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                OPENFDA_BASE,
                params={
                    "search": f'openfda.generic_name:"{drug_name}"',
                    "limit": 1,
                },
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            results = data.get("results", [])
            if results:
                sections = results[0].get("drug_interactions", [])
                return sections[0] if sections else None
        except (httpx.HTTPError, KeyError, IndexError):
            return None
    return None


def _check_known_interactions(drug_names: list[str]) -> list[dict]:
    """Check the curated interaction database for known drug pairs."""
    interactions = []
    normalized = [d.lower().strip() for d in drug_names]

    for i in range(len(normalized)):
        for j in range(i + 1, len(normalized)):
            pair = frozenset({normalized[i], normalized[j]})
            if pair in KNOWN_INTERACTIONS:
                info = KNOWN_INTERACTIONS[pair]
                interactions.append({
                    "drugs": [drug_names[i], drug_names[j]],
                    "severity": info["severity"],
                    "description": info["description"],
                    "source": info["source"],
                })
    return interactions


@tool
async def drug_interaction_check(medications: list[str]) -> dict:
    """Check for drug-drug interactions between a list of medication names.

    Uses a curated clinical interaction database and OpenFDA drug label data.
    Drug names are validated via the NLM RxNorm API.
    Pass 2 or more medication names to check for interactions between them.

    Args:
        medications: List of medication names (e.g., ["warfarin", "aspirin", "metformin"])
    """
    if len(medications) < 2:
        return {
            "error": None,
            "interactions": [],
            "resolved_drugs": {},
            "message": "Need at least 2 medications to check interactions.",
        }

    # Validate drug names via RxNorm
    resolved: dict[str, str | None] = {}
    for med in medications:
        resolved[med] = await _resolve_rxcui(med)

    unresolved = [name for name, cui in resolved.items() if cui is None]

    # Check curated interaction database (works with drug names directly)
    interactions = _check_known_interactions(medications)

    # Supplement with FDA label data for the first drug
    fda_context = None
    if medications:
        fda_context = await _get_fda_interaction_text(medications[0])

    return {
        "error": None,
        "interactions": interactions,
        "interaction_count": len(interactions),
        "resolved_drugs": {k: v for k, v in resolved.items() if v},
        "unresolved_drugs": unresolved,
        "checked_drug_count": len(medications),
        "fda_label_excerpt": fda_context[:500] if fda_context else None,
    }
# end AI-generated
