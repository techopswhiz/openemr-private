# AI-generated: Claude Code (claude.ai/code) — drug interaction tool
# Uses curated interaction DB + OpenFDA label cross-reference + NLM RxNorm for drug resolution
import logging
import re

import httpx
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"
OPENFDA_BASE = "https://api.fda.gov/drug/label.json"

# Curated interaction database — clinically significant drug pairs.
# Source: FDA drug labeling, clinical pharmacology references, ONCHigh priority list.
# Keyed by frozenset of lowercased generic drug names.
# ~100 high-priority pairs covering the most commonly prescribed interacting combinations.
KNOWN_INTERACTIONS: dict[frozenset[str], dict] = {
    # === Anticoagulants (warfarin) ===
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
    frozenset({"warfarin", "metronidazole"}): {
        "severity": "high",
        "description": "Metronidazole inhibits warfarin metabolism, significantly increasing anticoagulant effect and bleeding risk.",
        "source": "FDA Drug Label",
    },
    frozenset({"warfarin", "trimethoprim"}): {
        "severity": "high",
        "description": "Trimethoprim inhibits CYP2C9, increasing warfarin effect and bleeding risk.",
        "source": "FDA Drug Label",
    },
    frozenset({"warfarin", "sulfamethoxazole"}): {
        "severity": "high",
        "description": "Sulfamethoxazole inhibits CYP2C9, increasing warfarin levels. Monitor INR closely when starting TMP-SMX.",
        "source": "FDA Drug Label",
    },
    frozenset({"warfarin", "ciprofloxacin"}): {
        "severity": "moderate",
        "description": "Ciprofloxacin may increase warfarin effect by altering gut flora and CYP1A2 inhibition. Monitor INR.",
        "source": "FDA Drug Label",
    },
    frozenset({"warfarin", "erythromycin"}): {
        "severity": "moderate",
        "description": "Erythromycin inhibits CYP3A4 and may increase warfarin levels. Monitor INR.",
        "source": "FDA Drug Label",
    },
    frozenset({"warfarin", "phenytoin"}): {
        "severity": "high",
        "description": "Phenytoin and warfarin mutually affect each other's metabolism. Complex bidirectional interaction.",
        "source": "FDA Drug Label",
    },
    frozenset({"warfarin", "carbamazepine"}): {
        "severity": "high",
        "description": "Carbamazepine induces CYP enzymes, reducing warfarin effectiveness. Higher warfarin doses may be needed.",
        "source": "FDA Drug Label",
    },
    frozenset({"warfarin", "rifampin"}): {
        "severity": "high",
        "description": "Rifampin is a potent CYP inducer that dramatically reduces warfarin levels. May need 2-5x warfarin dose increase.",
        "source": "FDA Drug Label",
    },
    frozenset({"warfarin", "vitamin k"}): {
        "severity": "high",
        "description": "Vitamin K directly antagonizes warfarin. Large or variable intake reduces anticoagulant effect.",
        "source": "FDA Drug Label",
    },

    # === Antiplatelet (clopidogrel) ===
    frozenset({"clopidogrel", "omeprazole"}): {
        "severity": "high",
        "description": "Omeprazole reduces the antiplatelet effect of clopidogrel by inhibiting CYP2C19 activation. Avoid combination.",
        "source": "FDA Drug Label",
    },
    frozenset({"clopidogrel", "esomeprazole"}): {
        "severity": "high",
        "description": "Esomeprazole inhibits CYP2C19, reducing clopidogrel activation. Use pantoprazole instead.",
        "source": "FDA Drug Label",
    },
    frozenset({"clopidogrel", "aspirin"}): {
        "severity": "moderate",
        "description": "Dual antiplatelet therapy increases bleeding risk. Often intentional post-ACS but requires monitoring.",
        "source": "FDA Drug Label",
    },

    # === Statins ===
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
    frozenset({"amlodipine", "simvastatin"}): {
        "severity": "moderate",
        "description": "Amlodipine increases simvastatin exposure. Limit simvastatin to 20mg/day with amlodipine.",
        "source": "FDA Drug Label",
    },
    frozenset({"atorvastatin", "clarithromycin"}): {
        "severity": "high",
        "description": "Clarithromycin inhibits CYP3A4, significantly increasing statin levels and risk of myopathy.",
        "source": "FDA Drug Label",
    },
    frozenset({"simvastatin", "clarithromycin"}): {
        "severity": "high",
        "description": "Clarithromycin inhibits CYP3A4. Contraindicated with simvastatin due to rhabdomyolysis risk.",
        "source": "FDA Drug Label",
    },
    frozenset({"lovastatin", "clarithromycin"}): {
        "severity": "high",
        "description": "Clarithromycin inhibits CYP3A4. Contraindicated with lovastatin due to rhabdomyolysis risk.",
        "source": "FDA Drug Label",
    },
    frozenset({"simvastatin", "erythromycin"}): {
        "severity": "high",
        "description": "Erythromycin inhibits CYP3A4, increasing simvastatin levels. Risk of rhabdomyolysis.",
        "source": "FDA Drug Label",
    },
    frozenset({"atorvastatin", "erythromycin"}): {
        "severity": "high",
        "description": "Erythromycin inhibits CYP3A4, increasing atorvastatin levels. Risk of myopathy.",
        "source": "FDA Drug Label",
    },
    frozenset({"simvastatin", "itraconazole"}): {
        "severity": "high",
        "description": "Itraconazole is a potent CYP3A4 inhibitor. Contraindicated with simvastatin.",
        "source": "FDA Drug Label",
    },
    frozenset({"simvastatin", "ketoconazole"}): {
        "severity": "high",
        "description": "Ketoconazole is a potent CYP3A4 inhibitor. Contraindicated with simvastatin.",
        "source": "FDA Drug Label",
    },
    frozenset({"atorvastatin", "cyclosporine"}): {
        "severity": "high",
        "description": "Cyclosporine significantly increases statin exposure. Avoid atorvastatin >10mg or use alternatives.",
        "source": "FDA Drug Label",
    },
    frozenset({"simvastatin", "diltiazem"}): {
        "severity": "moderate",
        "description": "Diltiazem inhibits CYP3A4, increasing simvastatin levels. Limit simvastatin to 10mg/day.",
        "source": "FDA Drug Label",
    },
    frozenset({"simvastatin", "verapamil"}): {
        "severity": "moderate",
        "description": "Verapamil inhibits CYP3A4, increasing simvastatin levels. Limit simvastatin to 10mg/day.",
        "source": "FDA Drug Label",
    },
    frozenset({"rosuvastatin", "gemfibrozil"}): {
        "severity": "high",
        "description": "Gemfibrozil increases rosuvastatin exposure 2-fold. Limit rosuvastatin to 10mg/day.",
        "source": "FDA Drug Label",
    },
    frozenset({"simvastatin", "gemfibrozil"}): {
        "severity": "high",
        "description": "Gemfibrozil inhibits statin metabolism. Contraindicated with simvastatin due to rhabdomyolysis risk.",
        "source": "FDA Drug Label",
    },

    # === ACE inhibitors / ARBs ===
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
    frozenset({"enalapril", "spironolactone"}): {
        "severity": "moderate",
        "description": "Both ACE inhibitors and spironolactone increase potassium. Combined use raises hyperkalemia risk.",
        "source": "FDA Drug Label",
    },
    frozenset({"lisinopril", "losartan"}): {
        "severity": "high",
        "description": "Dual RAAS blockade (ACE + ARB) increases risk of hypotension, hyperkalemia, and renal impairment. Generally avoid.",
        "source": "FDA Drug Label",
    },
    frozenset({"enalapril", "losartan"}): {
        "severity": "high",
        "description": "Dual RAAS blockade (ACE + ARB) increases risk of hypotension, hyperkalemia, and renal impairment. Generally avoid.",
        "source": "FDA Drug Label",
    },
    frozenset({"lisinopril", "aliskiren"}): {
        "severity": "high",
        "description": "Dual RAAS blockade increases adverse events. Contraindicated in patients with diabetes or GFR <60.",
        "source": "FDA Drug Label",
    },
    frozenset({"lisinopril", "ibuprofen"}): {
        "severity": "moderate",
        "description": "NSAIDs reduce the antihypertensive effect of ACE inhibitors and increase renal impairment risk.",
        "source": "FDA Drug Label",
    },
    frozenset({"lisinopril", "naproxen"}): {
        "severity": "moderate",
        "description": "NSAIDs reduce the antihypertensive effect of ACE inhibitors and increase renal impairment risk.",
        "source": "FDA Drug Label",
    },

    # === Metformin ===
    frozenset({"metformin", "alcohol"}): {
        "severity": "high",
        "description": "Alcohol potentiates the effect of metformin on lactate metabolism, increasing the risk of lactic acidosis.",
        "source": "FDA Drug Label",
    },
    frozenset({"metformin", "contrast dye"}): {
        "severity": "high",
        "description": "Iodinated contrast media with metformin may cause lactic acidosis. Hold metformin before and 48h after contrast.",
        "source": "FDA Drug Label / ACR Guidelines",
    },

    # === Serotonin syndrome ===
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
    frozenset({"paroxetine", "tramadol"}): {
        "severity": "high",
        "description": "Paroxetine + tramadol increases serotonin syndrome risk. Both have serotonergic activity.",
        "source": "FDA Drug Label",
    },
    frozenset({"citalopram", "tramadol"}): {
        "severity": "high",
        "description": "Citalopram + tramadol increases serotonin syndrome risk. Both have serotonergic activity.",
        "source": "FDA Drug Label",
    },
    frozenset({"escitalopram", "tramadol"}): {
        "severity": "high",
        "description": "Escitalopram + tramadol increases serotonin syndrome risk. Both have serotonergic activity.",
        "source": "FDA Drug Label",
    },
    frozenset({"fluoxetine", "linezolid"}): {
        "severity": "high",
        "description": "Linezolid is a non-selective MAO inhibitor. Combined with SSRIs, serotonin syndrome risk is high.",
        "source": "FDA Drug Label",
    },
    frozenset({"sertraline", "linezolid"}): {
        "severity": "high",
        "description": "Linezolid is a non-selective MAO inhibitor. Combined with SSRIs, serotonin syndrome risk is high.",
        "source": "FDA Drug Label",
    },
    frozenset({"fluoxetine", "selegiline"}): {
        "severity": "high",
        "description": "MAO-B inhibitor + SSRI increases serotonin syndrome risk. Requires 5-week washout after fluoxetine.",
        "source": "FDA Drug Label",
    },
    frozenset({"sertraline", "selegiline"}): {
        "severity": "high",
        "description": "MAO-B inhibitor + SSRI increases serotonin syndrome risk. Requires 2-week washout.",
        "source": "FDA Drug Label",
    },
    frozenset({"fluoxetine", "sumatriptan"}): {
        "severity": "moderate",
        "description": "Triptans + SSRIs may increase serotonin syndrome risk. Monitor for symptoms.",
        "source": "FDA Drug Label",
    },
    frozenset({"sertraline", "sumatriptan"}): {
        "severity": "moderate",
        "description": "Triptans + SSRIs may increase serotonin syndrome risk. Monitor for symptoms.",
        "source": "FDA Drug Label",
    },

    # === QT prolongation ===
    frozenset({"amiodarone", "ciprofloxacin"}): {
        "severity": "high",
        "description": "Both drugs prolong QT interval. Combined use increases risk of Torsades de Pointes.",
        "source": "FDA Drug Label / ONCHigh",
    },
    frozenset({"amiodarone", "levofloxacin"}): {
        "severity": "high",
        "description": "Both drugs prolong QT interval. Combined use increases risk of Torsades de Pointes.",
        "source": "FDA Drug Label / ONCHigh",
    },
    frozenset({"amiodarone", "azithromycin"}): {
        "severity": "high",
        "description": "Both drugs prolong QT interval. Combined use increases risk of Torsades de Pointes.",
        "source": "FDA Drug Label / ONCHigh",
    },
    frozenset({"citalopram", "amiodarone"}): {
        "severity": "high",
        "description": "Both drugs prolong QT interval. Citalopram max 20mg/day with amiodarone.",
        "source": "FDA Drug Label",
    },
    frozenset({"methadone", "ciprofloxacin"}): {
        "severity": "high",
        "description": "Both drugs prolong QT interval. Combined use increases risk of fatal arrhythmia.",
        "source": "FDA Drug Label / ONCHigh",
    },
    frozenset({"ondansetron", "amiodarone"}): {
        "severity": "moderate",
        "description": "Both drugs prolong QT interval. Use with caution and ECG monitoring.",
        "source": "FDA Drug Label",
    },

    # === Fluoroquinolones ===
    frozenset({"ciprofloxacin", "tizanidine"}): {
        "severity": "high",
        "description": "Ciprofloxacin inhibits CYP1A2, causing dramatic increases in tizanidine levels. Contraindicated.",
        "source": "FDA Drug Label",
    },
    frozenset({"ciprofloxacin", "theophylline"}): {
        "severity": "high",
        "description": "Ciprofloxacin inhibits CYP1A2, increasing theophylline levels and toxicity risk (seizures, arrhythmias).",
        "source": "FDA Drug Label",
    },
    frozenset({"ciprofloxacin", "warfarin"}): {
        "severity": "moderate",
        "description": "Ciprofloxacin may increase warfarin effect. Monitor INR closely.",
        "source": "FDA Drug Label",
    },

    # === Methotrexate ===
    frozenset({"methotrexate", "ibuprofen"}): {
        "severity": "high",
        "description": "NSAIDs reduce renal clearance of methotrexate, increasing toxicity risk (pancytopenia, renal failure).",
        "source": "FDA Drug Label",
    },
    frozenset({"methotrexate", "naproxen"}): {
        "severity": "high",
        "description": "NSAIDs reduce renal clearance of methotrexate, increasing toxicity risk.",
        "source": "FDA Drug Label",
    },
    frozenset({"methotrexate", "trimethoprim"}): {
        "severity": "high",
        "description": "Both are folate antagonists. Combined use significantly increases bone marrow suppression risk.",
        "source": "FDA Drug Label",
    },

    # === Lithium ===
    frozenset({"lithium", "ibuprofen"}): {
        "severity": "high",
        "description": "NSAIDs reduce renal lithium clearance, causing elevated lithium levels and potential toxicity.",
        "source": "FDA Drug Label",
    },
    frozenset({"lithium", "naproxen"}): {
        "severity": "high",
        "description": "NSAIDs reduce renal lithium clearance, causing elevated lithium levels and potential toxicity.",
        "source": "FDA Drug Label",
    },
    frozenset({"lithium", "lisinopril"}): {
        "severity": "high",
        "description": "ACE inhibitors reduce lithium clearance, increasing lithium levels. Monitor levels closely.",
        "source": "FDA Drug Label",
    },
    frozenset({"lithium", "hydrochlorothiazide"}): {
        "severity": "high",
        "description": "Thiazide diuretics reduce lithium clearance by 25%. Risk of lithium toxicity.",
        "source": "FDA Drug Label",
    },

    # === Digoxin ===
    frozenset({"digoxin", "amiodarone"}): {
        "severity": "high",
        "description": "Amiodarone increases digoxin levels by 70-100%. Reduce digoxin dose by 50% when starting amiodarone.",
        "source": "FDA Drug Label",
    },
    frozenset({"digoxin", "verapamil"}): {
        "severity": "high",
        "description": "Verapamil increases digoxin levels by 50-75%. Reduce digoxin dose and monitor levels.",
        "source": "FDA Drug Label",
    },
    frozenset({"digoxin", "clarithromycin"}): {
        "severity": "high",
        "description": "Clarithromycin increases digoxin absorption by inhibiting gut P-glycoprotein. Monitor digoxin levels.",
        "source": "FDA Drug Label",
    },
    frozenset({"digoxin", "quinidine"}): {
        "severity": "high",
        "description": "Quinidine doubles digoxin levels via P-glycoprotein inhibition. Reduce digoxin dose by 50%.",
        "source": "FDA Drug Label",
    },

    # === Potassium / diuretics ===
    frozenset({"furosemide", "gentamicin"}): {
        "severity": "high",
        "description": "Both are ototoxic and nephrotoxic. Combined use increases risk of irreversible hearing loss and renal damage.",
        "source": "FDA Drug Label",
    },
    frozenset({"spironolactone", "potassium"}): {
        "severity": "high",
        "description": "Spironolactone is a potassium-sparing diuretic. Added potassium causes hyperkalemia risk.",
        "source": "FDA Drug Label",
    },

    # === Opioids ===
    frozenset({"oxycodone", "benzodiazepine"}): {
        "severity": "high",
        "description": "Combined CNS depression from opioids + benzodiazepines. FDA black box warning for respiratory depression and death.",
        "source": "FDA Drug Label / FDA Black Box Warning",
    },
    frozenset({"hydrocodone", "alprazolam"}): {
        "severity": "high",
        "description": "Combined CNS depression from opioids + benzodiazepines. FDA black box warning for respiratory depression and death.",
        "source": "FDA Drug Label / FDA Black Box Warning",
    },
    frozenset({"oxycodone", "alprazolam"}): {
        "severity": "high",
        "description": "Combined CNS depression from opioids + benzodiazepines. FDA black box warning for respiratory depression and death.",
        "source": "FDA Drug Label / FDA Black Box Warning",
    },
    frozenset({"morphine", "diazepam"}): {
        "severity": "high",
        "description": "Combined CNS depression from opioids + benzodiazepines. FDA black box warning for respiratory depression and death.",
        "source": "FDA Drug Label / FDA Black Box Warning",
    },
    frozenset({"fentanyl", "alprazolam"}): {
        "severity": "high",
        "description": "Combined CNS depression from opioids + benzodiazepines. FDA black box warning for respiratory depression and death.",
        "source": "FDA Drug Label / FDA Black Box Warning",
    },
    frozenset({"methadone", "diazepam"}): {
        "severity": "high",
        "description": "Combined CNS depression. Methadone also prolongs QT. Very high overdose risk.",
        "source": "FDA Drug Label / FDA Black Box Warning",
    },

    # === Thyroid ===
    frozenset({"levothyroxine", "calcium"}): {
        "severity": "moderate",
        "description": "Calcium reduces levothyroxine absorption. Separate doses by at least 4 hours.",
        "source": "FDA Drug Label",
    },
    frozenset({"levothyroxine", "iron"}): {
        "severity": "moderate",
        "description": "Iron reduces levothyroxine absorption. Separate doses by at least 4 hours.",
        "source": "FDA Drug Label",
    },
    frozenset({"levothyroxine", "omeprazole"}): {
        "severity": "moderate",
        "description": "PPIs reduce gastric acid, impairing levothyroxine absorption. May need dose adjustment.",
        "source": "FDA Drug Label",
    },

    # === Diabetes ===
    frozenset({"glipizide", "fluconazole"}): {
        "severity": "high",
        "description": "Fluconazole inhibits CYP2C9, increasing sulfonylurea levels and risk of severe hypoglycemia.",
        "source": "FDA Drug Label",
    },
    frozenset({"glyburide", "fluconazole"}): {
        "severity": "high",
        "description": "Fluconazole inhibits CYP2C9, increasing sulfonylurea levels and risk of severe hypoglycemia.",
        "source": "FDA Drug Label",
    },
    frozenset({"insulin", "fluoxetine"}): {
        "severity": "moderate",
        "description": "SSRIs may enhance hypoglycemic effect of insulin. Monitor blood glucose more frequently.",
        "source": "FDA Drug Label",
    },

    # === Phenytoin ===
    frozenset({"phenytoin", "fluconazole"}): {
        "severity": "high",
        "description": "Fluconazole inhibits CYP2C9, increasing phenytoin levels. Monitor levels and adjust dose.",
        "source": "FDA Drug Label",
    },
    frozenset({"phenytoin", "valproic acid"}): {
        "severity": "high",
        "description": "Complex bidirectional interaction. Valproic acid displaces phenytoin from protein binding and inhibits metabolism.",
        "source": "FDA Drug Label",
    },
    frozenset({"phenytoin", "carbamazepine"}): {
        "severity": "moderate",
        "description": "Both are CYP inducers. May decrease each other's levels. Monitor levels of both drugs.",
        "source": "FDA Drug Label",
    },

    # === Miscellaneous high-priority ===
    frozenset({"sildenafil", "nitrate"}): {
        "severity": "high",
        "description": "PDE5 inhibitors + nitrates cause severe hypotension. Contraindicated.",
        "source": "FDA Drug Label",
    },
    frozenset({"sildenafil", "nitroglycerin"}): {
        "severity": "high",
        "description": "PDE5 inhibitors + nitrates cause severe hypotension. Contraindicated.",
        "source": "FDA Drug Label",
    },
    frozenset({"tadalafil", "nitroglycerin"}): {
        "severity": "high",
        "description": "PDE5 inhibitors + nitrates cause severe hypotension. Contraindicated.",
        "source": "FDA Drug Label",
    },
    frozenset({"clonidine", "metoprolol"}): {
        "severity": "high",
        "description": "Beta-blockers + clonidine: abrupt clonidine withdrawal may cause rebound hypertensive crisis.",
        "source": "FDA Drug Label",
    },
    frozenset({"potassium", "amiloride"}): {
        "severity": "high",
        "description": "Amiloride is potassium-sparing. Added potassium supplements risk dangerous hyperkalemia.",
        "source": "FDA Drug Label",
    },
    frozenset({"fluoxetine", "tamoxifen"}): {
        "severity": "high",
        "description": "Fluoxetine inhibits CYP2D6, reducing tamoxifen activation to endoxifen. May reduce cancer treatment efficacy.",
        "source": "FDA Drug Label",
    },
    frozenset({"paroxetine", "tamoxifen"}): {
        "severity": "high",
        "description": "Paroxetine inhibits CYP2D6, reducing tamoxifen activation. Avoid this combination.",
        "source": "FDA Drug Label",
    },
    frozenset({"carbamazepine", "erythromycin"}): {
        "severity": "high",
        "description": "Erythromycin inhibits CYP3A4, increasing carbamazepine levels and toxicity risk (ataxia, nystagmus).",
        "source": "FDA Drug Label",
    },
    frozenset({"theophylline", "erythromycin"}): {
        "severity": "high",
        "description": "Erythromycin inhibits CYP3A4 and CYP1A2, increasing theophylline levels. Seizure risk.",
        "source": "FDA Drug Label",
    },
    frozenset({"cyclosporine", "ketoconazole"}): {
        "severity": "high",
        "description": "Ketoconazole inhibits CYP3A4, significantly increasing cyclosporine levels and nephrotoxicity risk.",
        "source": "FDA Drug Label",
    },
    frozenset({"colchicine", "clarithromycin"}): {
        "severity": "high",
        "description": "Clarithromycin inhibits CYP3A4 and P-gp, increasing colchicine levels. Fatal toxicity reported.",
        "source": "FDA Drug Label",
    },
}


async def _resolve_rxcui(drug_name: str) -> str | None:
    """Resolve a drug name to an RxCUI using the NLM RxNorm API."""
    try:
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
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.warning("RxNorm lookup failed for '%s': %s", drug_name, e)
    return None


async def _get_fda_interaction_text(drug_name: str) -> str | None:
    """Fetch drug interaction section from OpenFDA label data."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
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
    except (httpx.HTTPError, httpx.TimeoutException, KeyError, IndexError) as e:
        logger.warning("OpenFDA lookup failed for '%s': %s", drug_name, e)
    return None


async def _cross_reference_fda_labels(drug_a: str, drug_b: str) -> dict | None:
    """Check if drug_b is mentioned in drug_a's FDA interaction section (and vice versa).

    Returns an interaction dict if a cross-reference is found, None otherwise.
    """
    for primary, secondary in [(drug_a, drug_b), (drug_b, drug_a)]:
        text = await _get_fda_interaction_text(primary)
        if text is None:
            continue
        # Check if the secondary drug name appears in the interaction text
        if re.search(re.escape(secondary), text, re.IGNORECASE):
            # Extract the relevant sentence(s) mentioning the drug
            sentences = text.split(".")
            relevant = [
                s.strip() for s in sentences
                if secondary.lower() in s.lower()
            ]
            description = ". ".join(relevant[:2]) if relevant else text[:300]
            return {
                "drugs": [drug_a, drug_b],
                "severity": "moderate",  # FDA label mentions are at least moderate
                "description": description,
                "source": f"OpenFDA Drug Label ({primary})",
            }
    return None


def _check_known_interactions(drug_names: list[str]) -> tuple[list[dict], set[tuple[str, str]]]:
    """Check the curated interaction database for known drug pairs.

    Returns (interactions, checked_pairs) where checked_pairs is the set of
    pairs that were found in the curated DB (so we skip them in FDA lookup).
    """
    interactions = []
    found_pairs: set[tuple[str, str]] = set()
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
                found_pairs.add((normalized[i], normalized[j]))
    return interactions, found_pairs


@tool
async def drug_interaction_check(medications: list[str]) -> dict:
    """Check for drug-drug interactions between a list of medication names.

    Uses a curated clinical interaction database (~100 high-priority pairs) and
    cross-references OpenFDA drug label data for additional interactions.
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
    interactions, found_pairs = _check_known_interactions(medications)

    # Cross-reference FDA labels for pairs NOT in the curated DB
    normalized = [d.lower().strip() for d in medications]
    fda_interactions: list[dict] = []
    for i in range(len(normalized)):
        for j in range(i + 1, len(normalized)):
            if (normalized[i], normalized[j]) in found_pairs:
                continue
            if (normalized[j], normalized[i]) in found_pairs:
                continue
            fda_result = await _cross_reference_fda_labels(medications[i], medications[j])
            if fda_result is not None:
                fda_interactions.append(fda_result)

    all_interactions = interactions + fda_interactions

    return {
        "error": None,
        "interactions": all_interactions,
        "interaction_count": len(all_interactions),
        "curated_matches": len(interactions),
        "fda_label_matches": len(fda_interactions),
        "resolved_drugs": {k: v for k, v in resolved.items() if v},
        "unresolved_drugs": unresolved,
        "checked_drug_count": len(medications),
    }
# end AI-generated
