import os
import json
import uuid
import time
import math
import csv
from io import StringIO
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, session, Response, redirect, url_for
from utils.interaction_checker import (
    check_interactions,
    get_drug_database,
    DRUG_DATABASE,
    INTERACTION_RULES,
    get_prescribed_regimen
)

# Define Blueprint
health_suite_bp = Blueprint('health_suite', __name__)

DATA_DIR = "data"
PREVENTIVE_FILE = os.path.join(DATA_DIR, "preventive_records.json")
MONITORING_FILE = os.path.join(DATA_DIR, "monitoring_vitals.json")
WORKFLOWS_FILE = os.path.join(DATA_DIR, "workflow_cases.json")
WELLBEING_FILE = os.path.join(DATA_DIR, "wellbeing_records.json")
REPORTS_FILE = os.path.join(DATA_DIR, "reports.json")

os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Storage Helpers
# ---------------------------------------------------------------------------
def _load_json(filepath, default_val=None):
    if default_val is None:
        default_val = []
    if not os.path.exists(filepath):
        return default_val
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_val

def _save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_patient_list():
    reports = _load_json(REPORTS_FILE, [])
    patients = {}
    for r in reports:
        pid = str(r.get("patient_id", "")).strip()
        pname = str(r.get("patient_name", "")).strip()
        if pid and pid not in patients:
            patients[pid] = {
                "patient_id": pid,
                "patient_name": pname or f"Patient {pid}",
                "age": r.get("patient_age", "N/A"),
                "gender": r.get("patient_gender", "N/A"),
                "cancer_type": (r.get("cancer_type") or "lung").lower(),
                "stage": r.get("stage", "Stage I"),
                "label": r.get("label", "Malignancy"),
                "report_id": r.get("report_id", ""),
                "risk": r.get("risk", "Low"),
                "last_visit_date": r.get("last_visit_date", ""),
                "next_visit_date": r.get("next_visit_date", "")
            }
    return list(patients.values())

# ---------------------------------------------------------------------------
# 1. CANCER PREVENTIVE HEALTHCARE ENGINE (Brain, Breast, Lung, Skin Only)
# ---------------------------------------------------------------------------

CANCER_GUIDELINES = {
    "lung": {
        "cancer_name": "Lung Cancer",
        "primary_modality": "Low-Dose CT (LDCT) Screening",
        "guideline_org": "USPSTF & American Cancer Society (ACS 2024)",
        "target_group": "Adults aged 50–80 with ≥20 pack-year smoking history or heavy occupational carcinogen exposure.",
        "interval": "Annual Low-Dose Chest CT scan without contrast.",
        "mortality_benefit": "Reduces lung cancer mortality by 20% to 24% by identifying stage IA nodules before metastasis.",
        "key_risk_factors": [
            "Cigarette/tobacco smoking pack-years",
            "Residential radon gas exposure (>4 pCi/L)",
            "Occupational asbestos, silica, arsenic or diesel exhaust",
            "Underlying COPD, emphysema, or pulmonary fibrosis scarring",
            "First-degree family history of lung carcinoma"
        ],
        "early_warning_signs": [
            "Nagging cough or hoarseness persisting >3 weeks",
            "Hemoptysis (coughing up any amount of blood or rust-colored sputum)",
            "Unexplained pleuritic chest, shoulder, or back pain that worsens with deep breathing",
            "Recurrent episodes of bronchitis or pneumonia in the same lung segment",
            "New-onset wheezing, dyspnea on mild exertion, or unexplained weight loss"
        ]
    },
    "breast": {
        "cancer_name": "Breast Cancer",
        "primary_modality": "3D Digital Breast Tomosynthesis (Mammography) & Contrast MRI",
        "guideline_org": "USPSTF & American College of Radiology (ACR)",
        "target_group": "Females aged 40–74 (Biennial/Annual); High-risk females with BRCA/dense breasts starting at 25–30.",
        "interval": "Annual 3D mammogram; Add annual Breast MRI with contrast for >20% lifetime risk.",
        "mortality_benefit": "Lowers breast cancer mortality by over 25% by catching non-palpable microcalcifications and in-situ DCIS.",
        "key_risk_factors": [
            "Germline BRCA1, BRCA2, PALB2, or TP53 gene mutations",
            "First-degree relative (mother, sister, daughter) diagnosed with breast cancer",
            "Heterogeneously or extremely dense breast tissue (BI-RADS Category C/D)",
            "Prolonged hormonal exposure (early menarche, late menopause, nulliparity, postmenopausal HRT)",
            "Personal history of atypical ductal hyperplasia (ADH) or lobular neoplasia (LCIS)"
        ],
        "early_warning_signs": [
            "Hard, painless, solitary lump or thickening in breast or axillary lymph nodes",
            "Nipple inversion, flattening, or spontaneous unilateral serosanguinous/bloody discharge",
            "Peau d'orange (orange-peel texture), persistent erythema, or dimpling of breast skin",
            "Unexplained change in the size, contour, or symmetry of one breast",
            "Scaly, eczematous erosion of the nipple (Paget's disease of the breast)"
        ]
    },
    "skin": {
        "cancer_name": "Skin Cancer & Malignant Melanoma",
        "primary_modality": "Full-Body Digital Dermoscopy & Sequential Digital Dermoscopy Imaging (SDDI)",
        "guideline_org": "American Academy of Dermatology (AAD) & Skin Cancer Foundation",
        "target_group": "Adults with atypical mole syndrome, fair skin (Fitzpatrick I-II), history of blistering sunburns.",
        "interval": "Annual full-body dermatologist dermoscopy exam + Monthly ABCDE self-surveillance.",
        "mortality_benefit": ">98% 5-year survival when melanoma is excised in situ before Breslow vertical invasion.",
        "key_risk_factors": [
            "Fitzpatrick skin phototype I or II (fair skin, red/blond hair, blue eyes, easy burning)",
            "Presence of >50 total melanocytic nevi or >5 clinically atypical/dysplastic moles",
            "History of severe blistering sunburns during childhood or cumulative high UV tanning bed use",
            "Familial atypical multiple mole melanoma (FAMMM) syndrome or CDKN2A mutation",
            "Immunosuppression (organ transplant, chronic biologics, lymphoma history)"
        ],
        "early_warning_signs": [
            "A - Asymmetry: One half of the pigmented lesion does not match the other half",
            "B - Border: Irregular, scalloped, notched, or poorly defined border margins",
            "C - Color: Varied shades of brown, black, tan, white, red, or blue within one lesion",
            "D - Diameter: Lesion diameter greater than 6 mm (size of a pencil eraser)",
            "E - Evolving: Any rapid change in size, shape, color, elevation, bleeding, or itching (The Ugly Duckling sign)"
        ]
    },
    "brain": {
        "cancer_name": "Brain Tumor & CNS Malignancy (Glioma / Meningioma)",
        "primary_modality": "High-Resolution Cranial MRI with Gadolinium Contrast & Neurological Baseline",
        "guideline_org": "National Comprehensive Cancer Network (NCCN) & WHO CNS Guidelines",
        "target_group": "Patients with prior therapeutic cranial radiation, genetic cancer syndromes, or unremitting nocturnal neuro-symptoms.",
        "interval": "Diagnostic contrast-enhanced 3T Brain MRI upon symptom presentation; Surveillance q3-6m for diagnosed lesions.",
        "mortality_benefit": "Enables early neurosurgical gross total resection and stereotactic radiosurgery before brainstem herniation.",
        "key_risk_factors": [
            "Prior therapeutic ionizing radiation to the head, neck, or cranium in childhood",
            "Genetic tumor syndromes (Neurofibromatosis Type 1 or 2, Li-Fraumeni, Tuberous Sclerosis, Turcot)",
            "Occupational exposure to organic solvents, vinyl chloride, or petrochemicals",
            "High-grade glioma familial clustering",
            "Immunodeficiency associated with Primary CNS Lymphoma risk"
        ],
        "early_warning_signs": [
            "Persistent morning headaches that wake patient from sleep and worsen with bending, coughing, or straining",
            "New-onset adult seizures (focal or generalized tonic-clonic) with no prior epileptic history",
            "Progressive focal motor weakness, hemiparesis, sensory loss, or clumsiness on one side of body",
            "Unexplained projectile nausea or vomiting without gastrointestinal etiology (raised intracranial pressure)",
            "Subtle progressive cognitive decline, aphasia, visual field cuts (bitemporal hemianopsia), or personality shifts"
        ]
    }
}

def calculate_cancer_risk(data):
    """
    Computes strict oncology vulnerability indices for Brain, Breast, Lung, and Skin cancers.
    """
    target_cancer = str(data.get("cancer_type", "all")).lower().strip()
    age = int(data.get("age", 45))
    gender = str(data.get("gender", "Female")).capitalize()
    
    # Cancer-specific factor extraction
    smoking_status = str(data.get("smoking_status", "never")).lower()
    pack_years = float(data.get("pack_years", 0))
    family_history = [str(f).lower() for f in data.get("family_history", [])]
    sun_exposure_hours = float(data.get("sun_exposure_hours", 1))
    sunburn_history = str(data.get("sunburn_history", "rare")).lower()
    fitzpatrick_skin = str(data.get("fitzpatrick_skin", "type2")).lower()
    atypical_moles_count = int(data.get("atypical_moles_count", 0))
    brca_mutation = str(data.get("brca_mutation", "negative")).lower()
    breast_density = str(data.get("breast_density", "average")).lower()
    cranial_radiation = bool(data.get("cranial_radiation", False))
    neuro_headaches = bool(data.get("neuro_headaches", False))
    radon_occupational = bool(data.get("radon_occupational", False))

    # Base baseline scores (0-100 scale)
    lung_score = 6
    skin_score = 6
    breast_score = 6 if gender == "Female" else 1
    brain_score = 5

    # 1. Lung Cancer Model
    if smoking_status == "current":
        lung_score += min(50, pack_years * 2.0) + 22
    elif smoking_status == "former":
        lung_score += min(28, pack_years * 1.1) + 8
    if radon_occupational:
        lung_score += 24
    if "lung" in family_history:
        lung_score += 18
    if age >= 50:
        lung_score += min(15, (age - 50) * 0.7)

    # 2. Breast Cancer Model (if female)
    if gender == "Female":
        if brca_mutation in ("brca1", "brca2", "positive"):
            breast_score += 48
        if "breast" in family_history:
            breast_score += 24
        if breast_density in ("dense", "extremely_dense", "category_d"):
            breast_score += 18
        if age >= 40:
            breast_score += min(20, (age - 40) * 0.8)

    # 3. Skin Cancer (Melanoma) Model
    if sunburn_history == "frequent":
        skin_score += 32
    elif sunburn_history == "occasional":
        skin_score += 16
    if fitzpatrick_skin in ("type1", "type2"):
        skin_score += 20
    if atypical_moles_count >= 5:
        skin_score += 25
    elif atypical_moles_count > 0:
        skin_score += 12
    if "skin" in family_history or "melanoma" in family_history:
        skin_score += 22

    # 4. Brain Cancer (CNS) Model
    if cranial_radiation:
        brain_score += 45
    if "brain" in family_history or "li_fraumeni" in family_history or "neurofibromatosis" in family_history:
        brain_score += 35
    if neuro_headaches:
        brain_score += 25
    if age > 55:
        brain_score += min(12, (age - 55) * 0.6)

    # Clamp scores (0 to 98)
    lung_score = min(98, max(4, round(lung_score)))
    skin_score = min(98, max(4, round(skin_score)))
    breast_score = min(98, max(1, round(breast_score)))
    brain_score = min(98, max(4, round(brain_score)))

    # Determine Active Focus
    if target_cancer == "lung":
        primary_score = lung_score
        cancer_key = "lung"
    elif target_cancer == "breast" and gender == "Female":
        primary_score = breast_score
        cancer_key = "breast"
    elif target_cancer == "skin":
        primary_score = skin_score
        cancer_key = "skin"
    elif target_cancer == "brain":
        primary_score = brain_score
        cancer_key = "brain"
    else:
        # Aggregate across all 4 project cancers
        active_list = [lung_score, skin_score, brain_score]
        if gender == "Female":
            active_list.append(breast_score)
        primary_score = round(sum(active_list) / len(active_list))
        cancer_key = "all"

    if primary_score < 28:
        risk_level = "Low"
        badge_class = "badge-success"
    elif primary_score < 58:
        risk_level = "Moderate"
        badge_class = "badge-warning"
    elif primary_score < 78:
        risk_level = "Elevated"
        badge_class = "badge-danger"
    else:
        risk_level = "High"
        badge_class = "badge-danger"

    # Targeted Modifiable Oncologic Interventions
    oncology_actions = []
    reduction_potential = 0

    if smoking_status == "current":
        oncology_actions.append({
            "action": "Complete Tobacco Carcinogen Cessation Protocol",
            "impact": "-50% Lung Cancer Oncogenesis Risk",
            "cancer_type": "Lung Cancer",
            "clinical_rationale": "Ceases exposure to polycyclic aromatic hydrocarbons and tobacco-specific nitrosamines (NNK), permitting bronchial epithelial DNA repair."
        })
        reduction_potential += 50
    if sunburn_history in ("occasional", "frequent") or fitzpatrick_skin in ("type1", "type2"):
        oncology_actions.append({
            "action": "Broad-Spectrum SPF 50+ & UV Pyrimidine-Dimer Barrier",
            "impact": "-42% Malignant Melanoma Incidence",
            "cancer_type": "Skin Cancer",
            "clinical_rationale": "Prevents solar UVB/UVA radiation-induced DNA thymine cross-linking and p53 gene mutations in epidermal melanocytes."
        })
        reduction_potential += 35
    if gender == "Female" and breast_score >= 35:
        oncology_actions.append({
            "action": "High-Risk Breast Surveillance & Genetic Counseling (BRCA1/2)",
            "impact": "-38% Late-Stage Breast Cancer Diagnosis",
            "cancer_type": "Breast Cancer",
            "clinical_rationale": "Initiating high-risk alternating 3D mammography and contrast-enhanced breast MRI detects node-negative Stage 0/I lesions."
        })
        reduction_potential += 30
    if brain_score >= 35:
        oncology_actions.append({
            "action": "Neurological Consultation & Baseline 3T Contrast Brain MRI",
            "impact": "Early Detection Prior to Mass Effect",
            "cancer_type": "Brain Tumor",
            "clinical_rationale": "Evaluation for focal seizure activity and optic disc fundoscopy rules out elevated intracranial pressure and low-grade glioma progression."
        })
        reduction_potential += 25

    reduction_potential = min(68, max(15, reduction_potential))

    # Compile Screening Roadmaps for the 4 project cancers
    active_guidelines = []
    if cancer_key in ("lung", "all"):
        g = CANCER_GUIDELINES["lung"]
        urgency = "priority" if lung_score >= 45 else "standard"
        status = "Screening Strongly Indicated (LDCT)" if lung_score >= 45 else "Eligible at Age 50+"
        active_guidelines.append({**g, "id": "lung", "status": status, "urgency": urgency, "score": lung_score})
    
    if cancer_key in ("breast", "all") and gender == "Female":
        g = CANCER_GUIDELINES["breast"]
        urgency = "priority" if breast_score >= 40 else "standard"
        status = "Annual Mammogram + MRI Recommended" if breast_score >= 40 else "Biennial Mammogram Standard (Ages 40-74)"
        active_guidelines.append({**g, "id": "breast", "status": status, "urgency": urgency, "score": breast_score})

    if cancer_key in ("skin", "all"):
        g = CANCER_GUIDELINES["skin"]
        urgency = "priority" if skin_score >= 38 else "standard"
        status = "Dermoscopy & Full-Body Mapping Due" if skin_score >= 38 else "Annual Dermatologist Skin Exam"
        active_guidelines.append({**g, "id": "skin", "status": status, "urgency": urgency, "score": skin_score})

    if cancer_key in ("brain", "all"):
        g = CANCER_GUIDELINES["brain"]
        urgency = "priority" if brain_score >= 40 else "standard"
        status = "Diagnostic Cranial MRI Indicated" if brain_score >= 40 else "Clinical Surveillance Standard"
        active_guidelines.append({**g, "id": "brain", "status": status, "urgency": urgency, "score": brain_score})

    return {
        "cancer_context": cancer_key,
        "overall_index": primary_score,
        "risk_level": risk_level,
        "badge_class": badge_class,
        "organ_scores": {
            "lung": lung_score,
            "skin": skin_score,
            "breast": breast_score if gender == "Female" else None,
            "brain": brain_score
        },
        "modifiable_reduction_potential": reduction_potential,
        "lifestyle_action_plan": oncology_actions,
        "screenings": active_guidelines,
        "warning_signs": CANCER_GUIDELINES.get(cancer_key, CANCER_GUIDELINES["lung"])["early_warning_signs"] if cancer_key != "all" else (
            CANCER_GUIDELINES["brain"]["early_warning_signs"][:2] +
            CANCER_GUIDELINES["breast"]["early_warning_signs"][:2] +
            CANCER_GUIDELINES["lung"]["early_warning_signs"][:2] +
            CANCER_GUIDELINES["skin"]["early_warning_signs"][:2]
        ),
        "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

# ---------------------------------------------------------------------------
# 2. CANCER MONITORING ENGINE (Oncology Telemetry, Tumor Markers & Toxicity)
# ---------------------------------------------------------------------------

ONCOLOGY_BIOMARKER_RANGES = {
    "cea": {"min": 0.0, "max": 3.0, "unit": "ng/mL", "label": "CEA (Lung Carcinoma Marker)", "cancer": "Lung"},
    "ca15_3": {"min": 0.0, "max": 30.0, "unit": "U/mL", "label": "CA 15-3 (Breast Tumor Marker)", "cancer": "Breast"},
    "s100b": {"min": 0.0, "max": 0.10, "unit": "μg/L", "label": "S100B (Melanoma Marker)", "cancer": "Skin"},
    "ldh": {"min": 140, "max": 280, "unit": "U/L", "label": "Serum LDH (Melanoma Burden)", "cancer": "Skin"},
    "kps_score": {"min": 80, "max": 100, "unit": "%", "label": "Karnofsky Score (Brain Tumor KPS)", "cancer": "Brain"},
    "wbc": {"min": 4.0, "max": 11.0, "unit": "x10³/μL", "label": "WBC (Chemo Neutropenia Watch)", "cancer": "All Oncology"},
    "platelets": {"min": 150, "max": 450, "unit": "x10³/μL", "label": "Platelets (Chemo Thrombocytopenia)", "cancer": "All Oncology"},
    "spo2": {"min": 95, "max": 100, "unit": "%", "label": "SpO2 (Radiation Pneumonitis Watch)", "cancer": "Lung"},
    "pain_score": {"min": 0, "max": 3, "unit": "/10", "label": "Cancer Pain Visual Analog", "cancer": "All Oncology"}
}

def evaluate_cancer_vitals_alert(entry):
    """
    Evaluates vital reading strictly against critical oncology and chemotherapy toxicity thresholds.
    """
    alerts = []
    
    # 1. Febrile Neutropenia Alert (MEDICAL EMERGENCY in Oncology)
    temp = entry.get("temperature")
    wbc = entry.get("wbc")
    if temp is not None and temp >= 100.4:
        if wbc is not None and wbc < 2.5:
            alerts.append({
                "type": "febrile_neutropenia",
                "severity": "critical",
                "title": "ONCOLOGY EMERGENCY: Febrile Neutropenia",
                "message": f"Core temperature is {temp}°F with critical leukopenia (WBC {wbc} x10³/μL). Impaired immune defense risks rapid septic shock.",
                "action": "Immediate emergency oncology admission, stat blood cultures, and empiric broad-spectrum IV antibiotic infusion protocol."
            })
        else:
            alerts.append({
                "type": "oncology_fever",
                "severity": "warning",
                "title": "Oncology Fever / Suspected Infection",
                "message": f"Temperature is {temp}°F. Potential early opportunistic post-chemo infection.",
                "action": "Evaluate absolute neutrophil count (ANC) and monitor temperature every 2 hours."
            })

    # 2. Lung Cancer / Radiation Pneumonitis Hypoxia
    spo2 = entry.get("spo2")
    if spo2 is not None:
        if spo2 < 92:
            alerts.append({
                "type": "radiation_pneumonitis",
                "severity": "critical",
                "title": "Critical Hypoxia / Radiation Pneumonitis Flag",
                "message": f"SpO2 reading of {spo2}% indicates severe respiratory desaturation in lung cancer patient.",
                "action": "High-flow supplemental oxygen; emergent high-resolution chest CT to rule out radiation pneumonitis, pulmonary embolism, or pleural effusion."
            })
        elif spo2 < 95:
            alerts.append({
                "type": "lung_desaturation",
                "severity": "warning",
                "title": "Subacute Pulmonary Desaturation",
                "message": f"SpO2 is {spo2}%. Monitor ambulation and evaluate for post-radiation bronchial compromise.",
                "action": "Repeat pulse oximetry and assess dyspnea scale."
            })

    # 3. Brain Tumor / Elevated Intracranial Pressure / Seizure Risk
    kps = entry.get("kps_score")
    if kps is not None and kps < 60:
        alerts.append({
            "type": "brain_herniation_risk",
            "severity": "critical",
            "title": "Severe Neurological Decline (KPS < 60%)",
            "message": f"Patient Karnofsky Performance Score has dropped to {kps}%. Significant neurological deficit or mass effect suspected.",
            "action": "Stat cranial CT/MRI with contrast; administer dexamethasone for vasogenic edema reduction; neurology consult."
        })

    # 4. Chemotherapy-Induced Severe Thrombocytopenia (Bleeding Risk)
    platelets = entry.get("platelets")
    if platelets is not None and platelets < 50:
        alerts.append({
            "type": "severe_thrombocytopenia",
            "severity": "critical",
            "title": "Critical Thrombocytopenia (Platelets < 50k)",
            "message": f"Platelet count is {platelets} x10³/μL. Severe spontaneous hemorrhage risk.",
            "action": "Hold chemotherapy and anticoagulants; prepare prophylactic platelet transfusion."
        })

    # 5. Tumor Biomarker Elevation (Disease Progression)
    cea = entry.get("cea")
    if cea is not None and cea > 5.0:
        alerts.append({
            "type": "cea_spike",
            "severity": "warning",
            "title": "CEA Tumor Marker Elevation",
            "message": f"CEA level elevated to {cea} ng/mL (Normal <3.0). Suggests potential lung adenocarcinoma activity.",
            "action": "Correlate with restaging PET-CT and thoracic oncology consult."
        })

    ca15 = entry.get("ca15_3")
    if ca15 is not None and ca15 > 35.0:
        alerts.append({
            "type": "ca15_spike",
            "severity": "warning",
            "title": "CA 15-3 Breast Tumor Marker Surge",
            "message": f"CA 15-3 level is {ca15} U/mL (Normal <30.0). Correlate with breast cancer treatment response.",
            "action": "Order breast/axillary ultrasound or bone scan to assess metastatic surveillance."
        })

    # 6. Severe Breakthrough Cancer Pain
    pain = entry.get("pain_score")
    if pain is not None and pain >= 7:
        alerts.append({
            "type": "cancer_breakthrough_pain",
            "severity": "warning",
            "title": "Severe Breakthrough Cancer Pain Flare",
            "message": f"Visual analog pain score reported as {pain}/10.",
            "action": "Review palliative analgesia protocol (WHO 3-step analgesic ladder) and breakthrough opioid titration."
        })

    return alerts

def seed_cancer_monitoring_data():
    records = _load_json(MONITORING_FILE, [])
    if records:
        return
    
    seed_records = []
    now = datetime.now()

    # Pre-populate realistic oncology telemetry for 4 cancer types
    cancer_patients = [
        {"patient_id": "468", "patient_name": "Meenakshi", "cancer_type": "brain", "risk": "Low"},
        {"patient_id": "756", "patient_name": "ASD Patient", "cancer_type": "lung", "risk": "High"},
        {"patient_id": "48451654", "patient_name": "Pretty", "cancer_type": "breast", "risk": "Low"},
        {"patient_id": "902", "patient_name": "Marcus Aurelius", "cancer_type": "skin", "risk": "Moderate"}
    ]

    for p in cancer_patients:
        pid = p["patient_id"]
        pname = p["patient_name"]
        ctype = p["cancer_type"]
        is_high = (p["risk"] == "High")

        for days_ago in [28, 21, 14, 7, 0]:
            entry_time = now - timedelta(days=days_ago)
            noise = (days_ago % 3) * 0.3

            # Cancer-specific biomarkers
            cea_val = round(6.8 + noise, 1) if ctype == "lung" and is_high else (1.2 if ctype == "lung" else None)
            ca15_val = round(38.4 + noise, 1) if ctype == "breast" and is_high else (18.2 if ctype == "breast" else None)
            s100_val = round(0.18 + noise * 0.02, 2) if ctype == "skin" and is_high else (0.04 if ctype == "skin" else None)
            kps_val = 60 if ctype == "brain" and is_high and days_ago == 0 else (90 if ctype == "brain" else None)

            spo2_val = 93 if (ctype == "lung" and is_high and days_ago <= 7) else 98
            temp_val = 100.6 if (is_high and days_ago == 0) else 98.4
            wbc_val = 2.1 if (is_high and days_ago == 0) else 6.2
            platelets_val = 85 if (is_high and days_ago == 0) else 240
            pain_val = 7 if (is_high and days_ago == 0) else (2 if not is_high else 4)

            entry = {
                "id": str(uuid.uuid4())[:8],
                "patient_id": pid,
                "patient_name": pname,
                "cancer_type": ctype,
                "timestamp": int(entry_time.timestamp() * 1000),
                "recorded_at": entry_time.strftime("%Y-%m-%d %H:%M"),
                "systolic_bp": 138 if is_high else 118,
                "diastolic_bp": 86 if is_high else 78,
                "heart_rate": 108 if (is_high and days_ago == 0) else 74,
                "spo2": spo2_val,
                "temperature": temp_val,
                "cea": cea_val,
                "ca15_3": ca15_val,
                "s100b": s100_val,
                "kps_score": kps_val,
                "wbc": wbc_val,
                "platelets": platelets_val,
                "pain_score": pain_val,
                "ecog_status": 2 if is_high else 0,
                "notes": f"Oncology cycle review for {ctype.title()} cancer."
            }
            entry["alerts"] = evaluate_cancer_vitals_alert(entry)
            seed_records.append(entry)

    _save_json(MONITORING_FILE, seed_records)

# ---------------------------------------------------------------------------
# 3. CANCER WORKFLOWS ENGINE (MDT Tumor Board for Brain, Breast, Lung, Skin)
# ---------------------------------------------------------------------------

WORKFLOW_STAGES = [
    {"id": "intake", "name": "Intake & AI Pre-Screened", "color": "#3b82f6", "icon": "fa-dna"},
    {"id": "radiology", "name": "Radiology & Scan Review", "color": "#8b5cf6", "icon": "fa-x-ray"},
    {"id": "pathology", "name": "Biopsy & Histopathology", "color": "#ec4899", "icon": "fa-microscope"},
    {"id": "tumor_board", "name": "MDT Tumor Board Review", "color": "#f59e0b", "icon": "fa-users-viewfinder"},
    {"id": "treatment", "name": "Active Treatment Protocol", "color": "#10b981", "icon": "fa-syringe"},
    {"id": "surveillance", "name": "Remission & Surveillance", "color": "#06b6d4", "icon": "fa-shield-halved"}
]

def calculate_cancer_staging(cancer_type, params):
    """
    Cancer-specific staging algorithms:
    - Breast / Lung: AJCC 8th Edition TNM Staging
    - Brain: WHO Central Nervous System (CNS) Histopathological Grading (Grade 1-4)
    - Skin Melanoma: Breslow Vertical Thickness & Ulceration Staging
    """
    ctype = str(cancer_type).lower().strip()
    
    if ctype == "brain":
        who_grade = str(params.get("who_grade", "grade2")).lower()
        if who_grade in ("grade4", "gbm", "glioblastoma"):
            stage = "WHO Grade 4 (Glioblastoma Multiforme - GBM)"
            summary = "Highest-grade malignant astrocytoma. Standard Stupp Protocol: Maximal surgical resection followed by concurrent temozolomide (TMZ) and focal radiotherapy."
            pathway = "Maximal Safe Surgical Resection + Concurrent Chemoradiation (Stupp Protocol)"
        elif who_grade in ("grade3", "anaplastic"):
            stage = "WHO Grade 3 (Anaplastic Glioma / Meningioma)"
            summary = "Malignant, highly proliferative astrocytoma/oligodendroglioma. Surgical resection followed by radiotherapy and adjuvant PCV/temozolomide."
            pathway = "Surgical Resection + Adjuvant Radiotherapy & Alkylating Chemotherapy"
        elif who_grade in ("grade2", "low_grade"):
            stage = "WHO Grade 2 (Low-Grade Diffuse Glioma / Meningioma)"
            summary = "Slow-growing infiltrative lesion. Molecular profiling (IDH1/IDH2 mutation and 1p/19q codeletion) required for targeted surveillance vs early resection."
            pathway = "Neurosurgical Excision / Serial 3T MRI Surveillance"
        else:
            stage = "WHO Grade 1 (Benign / Pilocytic Astrocytoma / Meningioma)"
            summary = "Well-circumscribed benign lesion with low proliferative potential. Complete surgical excision is typically curative."
            pathway = "Definitive Complete Surgical Resection"

        return {"stage": stage, "summary": summary, "pathway": pathway, "system": "WHO CNS 2021"}

    elif ctype == "skin":
        breslow = float(params.get("breslow_mm", 1.0))
        ulcerated = bool(params.get("ulcerated", False))
        nodal = str(params.get("nodal_spread", "N0")).upper()

        if nodal in ("N1", "N2", "N3"):
            stage = "Stage III (Locoregional Nodal Melanoma)"
            summary = "Melanoma has spread to regional lymph nodes. Wide local excision + Complete lymph node dissection (CLND) + Adjuvant immunotherapy (Pembrolizumab/Nivolumab)."
            pathway = "Wide Local Excision + Lymphadenectomy + PD-1 Checkpoint Inhibitor Immunotherapy"
        elif breslow > 4.0:
            stage = "Stage IIB / IIC (High-Risk Deep Melanoma)"
            summary = "Deep vertical invasion (>4.0 mm). High risk of micrometastasis. Wide local excision with 2 cm margins + Sentinel Lymph Node Biopsy (SLNB)."
            pathway = "2 cm Margin Excision + Sentinel Lymph Node Biopsy (SLNB)"
        elif breslow >= 1.0 or (breslow >= 0.8 and ulcerated):
            stage = "Stage IB / IIA (Intermediate-Risk Melanoma)"
            summary = "Breslow depth 1.0–4.0 mm. SLNB indicated to evaluate sentinel node drainage."
            pathway = "1–2 cm Margin Excision + Sentinel Lymph Node Biopsy"
        else:
            stage = "Stage IA (Early Superficial Melanoma)"
            summary = "Thin melanoma (<0.8 mm without ulceration). 1 cm margin wide local excision is curative in >98% of cases."
            pathway = "Wide Local Excision with 1 cm Negative Margins"

        return {"stage": stage, "summary": summary, "pathway": pathway, "system": "AJCC 8th Ed. Melanoma"}

    else:
        # Breast or Lung Cancer TNM Staging
        t = str(params.get("t", "T1")).upper()
        n = str(params.get("n", "N0")).upper()
        m = str(params.get("m", "M0")).upper()

        if m == "M1":
            stage = "Stage IV (Metastatic Carcinoma)"
            summary = f"Distant metastatic disease in {ctype.title()} cancer. Systemic therapy (Targeted kinase inhibitors, Immune checkpoint blockade, systemic chemotherapy) indicated."
            pathway = "Systemic Targeted Therapy & Palliative Multimodal Care"
        elif t in ("TIS", "TX") and n == "N0" and m == "M0":
            stage = "Stage 0 (Carcinoma In Situ / DCIS)"
            summary = f"Pre-invasive in-situ lesion. Complete breast-conserving lumpectomy or surgical wedge excision is curative."
            pathway = "Breast-Conserving Surgery (BCS) or Local Excision"
        elif t in ("T1", "T1A", "T1B", "T1C") and n == "N0" and m == "M0":
            stage = "Stage I (Early Localized)"
            summary = f"Early primary tumor (≤2 cm) without regional lymph node involvement. Definitive surgical resection followed by stage-appropriate adjuvant therapy."
            pathway = "Primary Curative Surgical Resection + Adjuvant Radiation"
        elif (t in ("T2", "T2A", "T2B") and n == "N0") or (t in ("T1", "T2") and n == "N1"):
            stage = "Stage II (Locally Advancing)"
            summary = f"Tumor 2–5 cm or limited regional nodal spread. Neoadjuvant therapy or surgery followed by systemic chemotherapy."
            pathway = "Multimodal Neoadjuvant Therapy + Curative Resection"
        elif t in ("T3", "T4") or n in ("N2", "N3"):
            stage = "Stage III (Locoregionally Advanced)"
            summary = f"Extensive primary tumor (>5 cm or chest wall invasion) or bulky nodal disease. MDT Tumor Board review for definitive chemoradiation."
            pathway = "Definitive Concurrent Chemoradiotherapy & Immunotherapy"
        else:
            stage = "Stage I / Early Indeterminate"
            summary = "Surgical pathology confirmation required."
            pathway = "Definitive Resection Protocol"

        return {"stage": stage, "summary": summary, "pathway": pathway, "system": f"AJCC 8th Ed. {ctype.title()} TNM"}

def seed_cancer_workflow_cases():
    cases = _load_json(WORKFLOWS_FILE, [])
    if cases:
        return

    reports = _load_json(REPORTS_FILE, [])
    seed_cases = []
    
    stages_pool = ["intake", "radiology", "pathology", "tumor_board", "treatment", "surveillance"]

    for i, r in enumerate(reports):
        pid = r.get("patient_id", f"P-{1000+i}")
        pname = r.get("patient_name", f"Patient {i+1}")
        ctype = (r.get("cancer_type") or "lung").lower()
        risk = r.get("risk", "Moderate")

        if risk == "High":
            stage_idx = 3 # Tumor board
            priority = "Stat / Urgent Oncology"
        elif risk == "Moderate":
            stage_idx = 1 # Radiology
            priority = "Priority"
        else:
            stage_idx = 5 if i % 2 == 0 else 0
            priority = "Routine Surveillance"

        stage_id = stages_pool[stage_idx]
        staging_info = calculate_cancer_staging(ctype, {"t": "T2", "n": "N1", "m": "M0"})

        # Cancer-specific clinical order
        if ctype == "brain":
            order_title = "Stereotactic Neuronavigation Brain Biopsy"
            order_desc = "Frameless stereotactic needle biopsy with intraoperative frozen section and IDH1/IDH2 mutation profiling."
        elif ctype == "breast":
            order_title = "Core Needle Breast Biopsy & ER/PR/HER2"
            order_desc = "Ultrasound-guided automated core needle biopsy with ER, PR, HER2-neu, and Ki-67 immunohistochemical staining."
        elif ctype == "skin":
            order_title = "Wide Local Excision & Sentinel Lymph Node Biopsy"
            order_desc = "Excision with 1.5 cm margins + Technetium-99m lymphoscintigraphy sentinel node mapping."
        else:
            order_title = "CT-Guided Percutaneous Transthoracic Lung Biopsy"
            order_desc = "Coaxial core needle biopsy with NGS panel testing (EGFR, ALK, ROS1, KRAS, PD-L1 expression)."

        case = {
            "case_id": f"ONC-{uuid.uuid4().hex[:6].upper()}",
            "report_id": r.get("report_id", ""),
            "patient_id": pid,
            "patient_name": pname,
            "cancer_type": ctype,
            "cancer_label": r.get("label", ctype.title()),
            "risk": risk,
            "priority": priority,
            "current_stage": stage_id,
            "lead_oncologist": "Dr. Sarah Jenkins, MD (Medical Oncology)",
            "radiologist": "Dr. R. Chen, MD (Diagnostic Radiology)",
            "pathologist": "Dr. E. Thorne, MD (Surgical Pathology)",
            "staging": staging_info,
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "clinical_orders": [
                {
                    "order_id": f"ORD-{uuid.uuid4().hex[:6].upper()}",
                    "order_type": order_title,
                    "status": "Completed" if stage_idx > 2 else "Pending",
                    "target_organ": ctype.title(),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "instructions": order_desc
                }
            ],
            "tumor_board_notes": [
                {
                    "author": "Dr. Sarah Jenkins, MD",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "note": f"MediScan AI analysis for {ctype.title()} Cancer indicated {r.get('label', ctype.title())} with {r.get('confidence_pct', 95)}% confidence. Coordinated with Tumor Board for {staging_info['pathway']}."
                }
            ]
        }
        seed_cases.append(case)

    _save_json(WORKFLOWS_FILE, seed_cases)

# ---------------------------------------------------------------------------
# 4. PSYCHO-ONCOLOGY MENTAL WELLBEING ENGINE
# ---------------------------------------------------------------------------

PSYCHO_ONCOLOGY_KNOWLEDGE = {
    "scanxiety": {
        "title": "Coping with 'Scanxiety' (Awaiting Cancer CT/MRI & Biopsy Results)",
        "cancer_relevance": "Universal across Brain, Breast, Lung, and Skin Cancer patients",
        "content": (
            "Scanxiety is the acute anticipatory dread, sleeplessness, and visceral distress experienced while "
            "waiting for follow-up oncologic CT scans, brain MRIs, mammograms, or biopsy histopathology results.\n\n"
            "Evidence-Based Psycho-Oncology Coping Strategies:\n"
            "1. **Cognitive Compartmentalization ('Worry Window')**: Allocate exactly 15 minutes at 4:00 PM for cancer worry. When fear intrudes outside this window, mentally note: 'I have dedicated time to process this at 4:00 PM.'\n"
            "2. **Vagal Reset via Box Breathing**: Inhale 4s, hold 4s, exhale 4s, hold 4s. Activates parasympathetic cardiac deceleration within 120 seconds.\n"
            "3. **Segregate Uncontrollable from Controllable**: You cannot alter cellular histology today, but you can control your hydration, sleep ergonomics, and gentle walks.\n"
            "4. **Information Boundary**: Stop late-night algorithmic search spirals. Write down questions for your oncologist."
        )
    },
    "brain": {
        "title": "Coping with Brain Tumor Cognitive Shifts & Living with Uncertainty",
        "cancer_relevance": "Brain Cancer (Glioma, Meningioma, Pituitary)",
        "content": (
            "A brain tumor diagnosis evokes unique vulnerability because it touches memory, personality, and autonomy.\n\n"
            "Empathetic Guidance:\n"
            "1. **Acknowledge 'Brain Fog' Compassionately**: Subtle word-finding hesitation or fatigue is neurological strain, not failure of will.\n"
            "2. **Externalize Memory Supports**: Use phone reminders and color-coded medication dispensers to minimize cognitive anxiety.\n"
            "3. **Expressive Journaling**: When verbal processing feels taxing, write or record thoughts in short audio notes."
        )
    },
    "breast": {
        "title": "Navigating Breast Cancer Surgery, Body Image & Hormone Therapy",
        "cancer_relevance": "Breast Cancer (Lumpectomy, Mastectomy, Endocrine Therapy)",
        "content": (
            "Surviving breast cancer involves complex emotional transitions regarding femininity, scars, and long-term tamoxifen/aromatase inhibitors.\n\n"
            "Empathetic Guidance:\n"
            "1. **Grief for Your Pre-Diagnosis Body**: It is healthy and necessary to mourn changes in physical sensation, hair, and breast contours.\n"
            "2. **Intimacy at Your Own Pace**: Communicate openly with your partner that emotional safety precedes physical intimacy.\n"
            "3. **Connect with Breast Cancer Navigators**: Speaking with women who have completed reconstruction provides grounded reassurance."
        )
    },
    "lung": {
        "title": "Coping with Lung Cancer Stigma, Breathlessness & Treatment Anxiety",
        "cancer_relevance": "Lung Cancer (Adenocarcinoma, Squamous Cell)",
        "content": (
            "Lung cancer patients frequently grapple with unearned guilt, smoking stigma, or acute respiratory anxiety.\n\n"
            "Empathetic Guidance:\n"
            "1. **Shed False Guilt**: Cancer is a cellular aberration. No human deserves an oncologic illness regardless of smoking history.\n"
            "2. **Pacing Respiratory Breathlessness**: Use the 'Pursed-Lip Exhale' technique to prevent panic during dyspnea flares.\n"
            "3. **Energy Conservation**: Prioritize essential daily activities and rest without self-reproach."
        )
    },
    "skin": {
        "title": "Managing Melanoma Recurrence Fear, Sun Anxiety & Surgical Scars",
        "cancer_relevance": "Skin Cancer (Malignant Melanoma)",
        "content": (
            "Following melanoma excision, patients often develop 'heliophobia' (morbid fear of natural daylight) and constant hypervigilant mole checking.\n\n"
            "Empathetic Guidance:\n"
            "1. **Replace Fear with Regulated Protection**: Broad-spectrum SPF 50+ and sun-protective clothing restore safe outdoor enjoyment.\n"
            "2. **Limit Skin Self-Checks to Once a Month**: Checking moles daily triggers obsessive scanning. Monthly ABCDE checks are clinically optimal.\n"
            "3. **Trust Digital Dermoscopy**: High-resolution dermatologic imaging tracks millimeter shifts with precision."
        )
    },
    "chemo_fatigue": {
        "title": "Cancer Treatment Fatigue & Overcoming Chemotherapy Exhaustion",
        "cancer_relevance": "Chemotherapy & Radiation Oncology Patients",
        "content": (
            "Cancer-related fatigue is distinct from ordinary tiredness—it stems from cytokine cascade and mitochondrial depletion.\n\n"
            "Management Protocols:\n"
            "1. **The 4 P's**: Prioritize, Plan, Pace, and Position.\n"
            "2. **Micro-Dosed Movement**: 5 minutes of gentle walking stimulates mitochondrial ATP regeneration better than 8 hours of continuous bed rest.\n"
            "3. **Hydration & Electrolyte Support**: Maintain fluid volume to support renal clearance of cytotoxic byproducts."
        )
    }
}

SUPPORT_HELPLINES = [
    {
        "region": "United States & Canada",
        "name": "988 Suicide & Crisis Lifeline",
        "contact": "Call or Text 988 (Free, 24/7, Confidential)",
        "badge": "24/7 Crisis"
    },
    {
        "region": "United States",
        "name": "Cancer Support Community Helpline",
        "contact": "1-888-793-9355 (Licensed Oncology Social Workers)",
        "badge": "Psycho-Oncology"
    },
    {
        "region": "United States",
        "name": "American Cancer Society 24/7 Support",
        "contact": "1-800-227-2345 (24/7 Oncology Navigators)",
        "badge": "Navigator"
    },
    {
        "region": "United Kingdom",
        "name": "Macmillan Cancer Support Helpline",
        "contact": "0808 808 00 00 (7 days a week, 8am-8pm)",
        "badge": "UK Support"
    },
    {
        "region": "India",
        "name": "Indian Cancer Society Helpline",
        "contact": "1800-22-1951 (Free Counseling & Guidance)",
        "badge": "Counseling"
    },
    {
        "region": "India",
        "name": "Vandrevala Foundation Mental Health Support",
        "contact": "+91 9999 666 555 (24/7 Multilingual Support)",
        "badge": "24/7 Crisis"
    },
    {
        "region": "Australia",
        "name": "Cancer Council Australia Helpline",
        "contact": "13 11 20 (Specialized Oncology Health Workers)",
        "badge": "Australia"
    }
]

def psycho_oncology_ai_response(user_query):
    query_lower = user_query.lower()
    
    if any(k in query_lower for k in ["brain", "glioma", "meningioma", "headache", "memory", "head"]):
        return {
            "category": "brain",
            "title": PSYCHO_ONCOLOGY_KNOWLEDGE["brain"]["title"],
            "response": PSYCHO_ONCOLOGY_KNOWLEDGE["brain"]["content"]
        }
    elif any(k in query_lower for k in ["breast", "mastectomy", "lumpectomy", "hair", "body image"]):
        return {
            "category": "breast",
            "title": PSYCHO_ONCOLOGY_KNOWLEDGE["breast"]["title"],
            "response": PSYCHO_ONCOLOGY_KNOWLEDGE["breast"]["content"]
        }
    elif any(k in query_lower for k in ["lung", "cough", "breath", "breathing", "stigma", "smoking"]):
        return {
            "category": "lung",
            "title": PSYCHO_ONCOLOGY_KNOWLEDGE["lung"]["title"],
            "response": PSYCHO_ONCOLOGY_KNOWLEDGE["lung"]["content"]
        }
    elif any(k in query_lower for k in ["skin", "melanoma", "mole", "sun", "sunlight"]):
        return {
            "category": "skin",
            "title": PSYCHO_ONCOLOGY_KNOWLEDGE["skin"]["title"],
            "response": PSYCHO_ONCOLOGY_KNOWLEDGE["skin"]["content"]
        }
    elif any(k in query_lower for k in ["fatigue", "tired", "exhausted", "chemo", "energy"]):
        return {
            "category": "chemo_fatigue",
            "title": PSYCHO_ONCOLOGY_KNOWLEDGE["chemo_fatigue"]["title"],
            "response": PSYCHO_ONCOLOGY_KNOWLEDGE["chemo_fatigue"]["content"]
        }
    elif any(k in query_lower for k in ["scan", "waiting", "result", "mri", "biopsy", "anxiety", "scanxiety", "fear"]):
        return {
            "category": "scanxiety",
            "title": PSYCHO_ONCOLOGY_KNOWLEDGE["scanxiety"]["title"],
            "response": PSYCHO_ONCOLOGY_KNOWLEDGE["scanxiety"]["content"]
        }
    else:
        return {
            "category": "general",
            "title": "Compassionate Oncology Emotional Support",
            "response": (
                "Navigating cancer diagnostics, whether brain, breast, lung, or skin, evokes profound emotional transitions. "
                "Everything you are feeling—uncertainty, grief, or fatigue—is a natural physiological and emotional reaction.\n\n"
                "• **Pace Yourself**: You do not need to solve the entire cancer trajectory today. Focus only on the immediate next appointment.\n"
                "• **Somatic Grounding**: Use our Mindful Breath Pacer to complete 3 minutes of Box Breathing before medical exams.\n"
                "• **24/7 Support**: The Cancer Support Community Helpline (1-888-793-9355) and 988 are available around the clock."
            )
        }

# ===========================================================================
# FLASK ROUTE HANDLERS
# ===========================================================================

# Initialize seed data
seed_cancer_monitoring_data()
seed_cancer_workflow_cases()

# ----------------- 1. Preventive Healthcare Routes -----------------
@health_suite_bp.route("/preventive")
def preventive_page():
    patients = get_patient_list()
    active_cancer = request.args.get("cancer_type", "all").lower()
    return render_template("preventive.html", patients=patients, guidelines=CANCER_GUIDELINES, active_cancer=active_cancer)

@health_suite_bp.route("/api/preventive/assess", methods=["POST"])
def api_preventive_assess():
    data = request.get_json() or {}
    result = calculate_cancer_risk(data)
    
    pid = data.get("patient_id")
    if pid:
        history = _load_json(PREVENTIVE_FILE, [])
        record = {
            "id": str(uuid.uuid4())[:8],
            "patient_id": pid,
            "patient_name": data.get("patient_name", "Anonymous"),
            "cancer_type": data.get("cancer_type", "all"),
            "data": data,
            "result": result,
            "timestamp": int(time.time() * 1000)
        }
        history.insert(0, record)
        _save_json(PREVENTIVE_FILE, history[:100])

    return jsonify({"success": True, "assessment": result})

@health_suite_bp.route("/api/preventive/guidelines")
def api_preventive_guidelines():
    cancer_type = request.args.get("cancer_type")
    if cancer_type and cancer_type in CANCER_GUIDELINES:
        return jsonify({"guidelines": [CANCER_GUIDELINES[cancer_type]]})
    return jsonify({"guidelines": list(CANCER_GUIDELINES.values())})

# ----------------- 2. Oncology Health Monitoring Routes -----------------
@health_suite_bp.route("/monitoring")
def monitoring_page():
    patients = get_patient_list()
    vitals = _load_json(MONITORING_FILE, [])
    selected_cancer = request.args.get("cancer_type", "").lower()
    selected_patient = request.args.get("patient_id", "")
    return render_template(
        "monitoring.html",
        patients=patients,
        vitals=vitals,
        ranges=ONCOLOGY_BIOMARKER_RANGES,
        selected_cancer=selected_cancer,
        selected_patient=selected_patient
    )

@health_suite_bp.route("/api/monitoring/vitals", methods=["GET"])
def api_monitoring_get_vitals():
    patient_id = request.args.get("patient_id")
    cancer_type = request.args.get("cancer_type")
    vitals = _load_json(MONITORING_FILE, [])
    
    if patient_id:
        vitals = [v for v in vitals if str(v.get("patient_id")) == str(patient_id)]
    if cancer_type and cancer_type != "all":
        vitals = [v for v in vitals if str(v.get("cancer_type", "")).lower() == cancer_type.lower()]

    vitals = sorted(vitals, key=lambda x: x.get("timestamp", 0))
    return jsonify({"success": True, "vitals": vitals})

@health_suite_bp.route("/api/monitoring/add_vital", methods=["POST"])
def api_monitoring_add_vital():
    data = request.get_json() or {}
    patient_id = data.get("patient_id")
    if not patient_id:
        return jsonify({"error": "Patient ID is required"}), 400

    now = datetime.now()
    entry = {
        "id": str(uuid.uuid4())[:8],
        "patient_id": str(patient_id),
        "patient_name": data.get("patient_name", f"Patient {patient_id}"),
        "cancer_type": data.get("cancer_type", "lung").lower(),
        "timestamp": int(now.timestamp() * 1000),
        "recorded_at": now.strftime("%Y-%m-%d %H:%M"),
        "systolic_bp": int(data["systolic_bp"]) if data.get("systolic_bp") else 120,
        "diastolic_bp": int(data["diastolic_bp"]) if data.get("diastolic_bp") else 80,
        "heart_rate": int(data["heart_rate"]) if data.get("heart_rate") else 72,
        "spo2": int(data["spo2"]) if data.get("spo2") else 98,
        "temperature": float(data["temperature"]) if data.get("temperature") else 98.6,
        "cea": float(data["cea"]) if data.get("cea") else None,
        "ca15_3": float(data["ca15_3"]) if data.get("ca15_3") else None,
        "s100b": float(data["s100b"]) if data.get("s100b") else None,
        "kps_score": int(data["kps_score"]) if data.get("kps_score") else None,
        "wbc": float(data["wbc"]) if data.get("wbc") else None,
        "platelets": int(data["platelets"]) if data.get("platelets") else None,
        "pain_score": int(data["pain_score"]) if data.get("pain_score") is not None else 0,
        "ecog_status": int(data.get("ecog_status", 0)),
        "notes": data.get("notes", "")
    }

    entry["alerts"] = evaluate_cancer_vitals_alert(entry)

    vitals = _load_json(MONITORING_FILE, [])
    vitals.append(entry)
    _save_json(MONITORING_FILE, vitals)

    return jsonify({"success": True, "entry": entry, "alerts": entry["alerts"]})

@health_suite_bp.route("/api/monitoring/export_csv", methods=["GET"])
def api_monitoring_export_csv():
    patient_id = request.args.get("patient_id")
    vitals = _load_json(MONITORING_FILE, [])
    if patient_id:
        vitals = [v for v in vitals if str(v.get("patient_id")) == str(patient_id)]

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Entry ID", "Patient ID", "Patient Name", "Cancer Type", "Recorded At",
        "Systolic BP", "Diastolic BP", "Heart Rate", "SpO2 (%)", "Temp (°F)",
        "CEA (Lung)", "CA 15-3 (Breast)", "S100B (Skin)", "KPS % (Brain)",
        "WBC (k/uL)", "Platelets (k/uL)", "Pain Score", "ECOG Status", "Oncology Alerts"
    ])

    for v in vitals:
        alert_titles = "; ".join(a.get("title", "") for a in v.get("alerts", []))
        writer.writerow([
            v.get("id"), v.get("patient_id"), v.get("patient_name"), v.get("cancer_type", ""), v.get("recorded_at"),
            v.get("systolic_bp"), v.get("diastolic_bp"), v.get("heart_rate"), v.get("spo2"), v.get("temperature"),
            v.get("cea", ""), v.get("ca15_3", ""), v.get("s100b", ""), v.get("kps_score", ""),
            v.get("wbc", ""), v.get("platelets", ""), v.get("pain_score", ""), v.get("ecog_status", ""), alert_titles
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=MediScan_Oncology_Vitals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

# ----------------- 3. Cancer Workflows Routes -----------------
@health_suite_bp.route("/workflows")
def workflows_page():
    cases = _load_json(WORKFLOWS_FILE, [])
    patients = get_patient_list()
    active_cancer = request.args.get("cancer_type", "all").lower()
    return render_template("workflows.html", cases=cases, stages=WORKFLOW_STAGES, patients=patients, active_cancer=active_cancer)

@health_suite_bp.route("/api/workflows/cases", methods=["GET"])
def api_workflows_get_cases():
    cases = _load_json(WORKFLOWS_FILE, [])
    cancer_type = request.args.get("cancer_type")
    if cancer_type and cancer_type != "all":
        cases = [c for c in cases if str(c.get("cancer_type", "")).lower() == cancer_type.lower()]
    return jsonify({"success": True, "cases": cases, "stages": WORKFLOW_STAGES})

@health_suite_bp.route("/api/workflows/update_stage", methods=["POST"])
def api_workflows_update_stage():
    data = request.get_json() or {}
    case_id = data.get("case_id")
    new_stage = data.get("new_stage")
    
    cases = _load_json(WORKFLOWS_FILE, [])
    for c in cases:
        if c.get("case_id") == case_id:
            old_stage = c.get("current_stage")
            c["current_stage"] = new_stage
            c.setdefault("tumor_board_notes", []).append({
                "author": session.get("doctor_email", "Attending Oncologist"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "note": f"MDT Tumor Board advanced oncology stage from '{old_stage}' to '{new_stage}'."
            })
            _save_json(WORKFLOWS_FILE, cases)
            return jsonify({"success": True, "message": f"Stage updated to {new_stage}"})

    return jsonify({"error": "Case not found"}), 404

@health_suite_bp.route("/api/workflows/calculate_staging", methods=["POST"])
def api_workflows_calc_staging():
    data = request.get_json() or {}
    cancer_type = data.get("cancer_type", "lung")
    params = data.get("params", {})
    res = calculate_cancer_staging(cancer_type, params)
    return jsonify({"success": True, "staging": res})

# Backward compatibility for old call
@health_suite_bp.route("/api/workflows/calculate_tnm", methods=["POST"])
def api_workflows_calc_tnm():
    data = request.get_json() or {}
    t = data.get("t", "T1")
    n = data.get("n", "N0")
    m = data.get("m", "M0")
    res = calculate_cancer_staging("lung", {"t": t, "n": n, "m": m})
    return jsonify({"success": True, "staging": res})

@health_suite_bp.route("/api/workflows/add_note", methods=["POST"])
def api_workflows_add_note():
    data = request.get_json() or {}
    case_id = data.get("case_id")
    note_text = data.get("note")

    if not case_id or not note_text:
        return jsonify({"error": "Case ID and note text required"}), 400

    cases = _load_json(WORKFLOWS_FILE, [])
    for c in cases:
        if c.get("case_id") == case_id:
            c.setdefault("tumor_board_notes", []).append({
                "author": session.get("doctor_email", "Dr. Sarah Jenkins, MD (Medical Oncology)"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "note": note_text.strip()
            })
            _save_json(WORKFLOWS_FILE, cases)
            return jsonify({"success": True, "notes": c["tumor_board_notes"]})

    return jsonify({"error": "Case not found"}), 404

@health_suite_bp.route("/api/workflows/generate_order", methods=["POST"])
def api_workflows_generate_order():
    data = request.get_json() or {}
    case_id = data.get("case_id")
    order_type = data.get("order_type", "Biopsy Requisition")
    instructions = data.get("instructions", "Proceed with standard oncology protocol.")
    
    cases = _load_json(WORKFLOWS_FILE, [])
    for c in cases:
        if c.get("case_id") == case_id:
            new_order = {
                "order_id": f"ORD-{uuid.uuid4().hex[:6].upper()}",
                "order_type": order_type,
                "status": "Submitted / Active",
                "target_organ": c.get("cancer_type", "Oncology").title(),
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "instructions": instructions
            }
            c.setdefault("clinical_orders", []).append(new_order)
            _save_json(WORKFLOWS_FILE, cases)
            return jsonify({"success": True, "order": new_order})

    return jsonify({"error": "Case not found"}), 404

@health_suite_bp.route("/api/workflows/export_fhir/<case_id>")
def api_workflows_export_fhir(case_id):
    cases = _load_json(WORKFLOWS_FILE, [])
    for c in cases:
        if c.get("case_id") == case_id:
            patient_id = c.get("patient_id", "anonymous")
            bundle = {
                "resourceType": "Bundle",
                "id": f"bundle-mediscan-{c.get('case_id')}",
                "type": "collection",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "entry": [
                    {
                        "fullUrl": f"urn:uuid:patient-{patient_id}",
                        "resource": {
                            "resourceType": "Patient",
                            "id": patient_id,
                            "name": [{"use": "official", "text": c.get("patient_name", "Patient")}]
                        }
                    },
                    {
                        "fullUrl": f"urn:uuid:report-{c.get('case_id')}",
                        "resource": {
                            "resourceType": "DiagnosticReport",
                            "id": f"report-{c.get('case_id')}",
                            "status": "final",
                            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v2-0074", "code": "RAD", "display": "Radiation & Oncology Diagnostics"}]}],
                            "code": {"text": f"AI-Assisted {c.get('cancer_type', '').title()} Oncology Report"},
                            "subject": {"reference": f"urn:uuid:patient-{patient_id}"},
                            "effectiveDateTime": datetime.utcnow().isoformat() + "Z",
                            "conclusion": c.get("staging", {}).get("summary", "Complete MDT staging recommended."),
                            "conclusionCode": [{"text": c.get("staging", {}).get("stage", "Stage I")}]
                        }
                    }
                ]
            }
            return Response(
                json.dumps(bundle, indent=2),
                mimetype="application/json",
                headers={"Content-Disposition": f"attachment;filename=FHIR_Bundle_{case_id}.json"}
            )
    return jsonify({"error": "Case not found"}), 404

# ----------------- 4. Psycho-Oncology Wellbeing Routes -----------------
@health_suite_bp.route("/wellbeing")
def wellbeing_page():
    active_cancer = request.args.get("cancer_type", "").lower()
    return render_template("wellbeing.html", helplines=SUPPORT_HELPLINES, topics=PSYCHO_ONCOLOGY_KNOWLEDGE, active_cancer=active_cancer)

@health_suite_bp.route("/api/wellbeing/assess", methods=["POST"])
def api_wellbeing_assess():
    data = request.get_json() or {}
    score = int(data.get("distress_score", 3))
    problems = data.get("problems", [])
    
    if score >= 7:
        severity = "Severe Oncology Distress"
        badge_class = "badge-danger"
        recommendation = "Immediate referral to licensed clinical psycho-oncologist, medical social work, or palliative supportive care specialist recommended."
    elif score >= 4:
        severity = "Moderate Oncology Distress"
        badge_class = "badge-warning"
        recommendation = "Active psychosocial cancer support recommended. Schedule consultation with patient navigator or specialized cancer support group."
    else:
        severity = "Mild / Manageable"
        badge_class = "badge-success"
        recommendation = "Distress level is within expected manageable boundaries for cancer diagnostics. Continue routine mindfulness and breathing exercises."

    res = {
        "score": score,
        "severity": severity,
        "badge_class": badge_class,
        "recommendation": recommendation,
        "identified_problems": problems,
        "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    records = _load_json(WELLBEING_FILE, [])
    records.insert(0, {
        "id": str(uuid.uuid4())[:8],
        "distress_score": score,
        "problems": problems,
        "evaluation": res,
        "timestamp": int(time.time() * 1000)
    })
    _save_json(WELLBEING_FILE, records[:50])

    return jsonify({"success": True, "result": res})

@health_suite_bp.route("/api/wellbeing/chat", methods=["POST"])
def api_wellbeing_chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400

    reply = psycho_oncology_ai_response(message)
    return jsonify({"success": True, "reply": reply})

# ----------------- 5. Oncology Drug & Supplement Interaction Routes -----------------
@health_suite_bp.route("/interactions")
def interactions_page():
    patients = get_patient_list()
    active_cancer = request.args.get("cancer_type", "").lower()
    active_stage = request.args.get("stage", "")
    selected_patient = request.args.get("patient_id", "")

    # If patient is selected, extract their scanned cancer type and stage
    patient_obj = None
    if selected_patient:
        for p in patients:
            if str(p.get("patient_id")) == str(selected_patient):
                patient_obj = p
                if not active_cancer:
                    active_cancer = p.get("cancer_type", "breast")
                if not active_stage:
                    active_stage = p.get("stage", "Stage II")
                break

    if not active_cancer or active_cancer not in ["brain", "breast", "lung", "skin"]:
        active_cancer = "breast"
    if not active_stage:
        active_stage = "Stage II"

    prescription = get_prescribed_regimen(active_cancer, active_stage)

    return render_template(
        "interactions.html",
        patients=patients,
        drugs=DRUG_DATABASE,
        total_rules=len(INTERACTION_RULES),
        active_cancer=active_cancer,
        active_stage=active_stage,
        selected_patient=selected_patient,
        patient_obj=patient_obj,
        initial_prescription=prescription
    )

@health_suite_bp.route("/api/interactions/prescribe", methods=["GET", "POST"])
def api_interactions_prescribe():
    if request.method == "POST":
        data = request.get_json() or {}
        cancer_type = data.get("cancer_type", "breast")
        stage = data.get("stage", "Stage II")
    else:
        cancer_type = request.args.get("cancer_type", "breast")
        stage = request.args.get("stage", "Stage II")

    prescription = get_prescribed_regimen(cancer_type, stage)
    return jsonify({"success": True, "prescription": prescription})

@health_suite_bp.route("/api/interactions/check", methods=["POST"])
def api_interactions_check():
    data = request.get_json() or {}
    items = data.get("items", [])
    if not isinstance(items, list):
        return jsonify({"error": "Items must be an array of drug or supplement IDs"}), 400

    analysis = check_interactions(items)
    return jsonify({"success": True, "analysis": analysis})

@health_suite_bp.route("/api/interactions/database", methods=["GET"])
def api_interactions_database():
    q = request.args.get("q", "")
    category = request.args.get("category", "")
    items = get_drug_database(search_query=q, category=category)
    return jsonify({"success": True, "items": items, "count": len(items)})


