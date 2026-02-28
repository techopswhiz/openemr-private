# AI-generated: Claude Code (claude.ai/code) — tool registry
from app.tools.allergy_drug_cross import allergy_drug_cross_check
from app.tools.drug_interactions import drug_interaction_check
from app.tools.patient_allergies import patient_allergy_list
from app.tools.patient_appointments import patient_appointments
from app.tools.patient_lookup import patient_lookup
from app.tools.patient_medications import patient_medication_list
from app.tools.patient_problems import patient_problem_list
from app.tools.patient_vitals import patient_vitals

all_tools = [
    patient_lookup,
    patient_medication_list,
    patient_allergy_list,
    patient_problem_list,
    patient_vitals,
    patient_appointments,
    drug_interaction_check,
    allergy_drug_cross_check,
]
# end AI-generated
