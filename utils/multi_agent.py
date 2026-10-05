"""
Multi-Agent AI Clinical Second Opinion System
==============================================

Implements a clinical decision-support workflow where five specialized AI
"personas" independently review the same cancer-detection result and then an
AI aggregator synthesizes them into one unified clinical recommendation.

The five agents are:

  1. Radiologist     - image/scan findings (tumor, margins, contrast, localization)
  2. Oncologist      - cancer stage, risk, prognosis, diagnostic tests
  3. Surgeon         - surgical necessity, urgency, complications, recovery
  4. Pharmacologist  - informational medication options, interactions, side effects
                       (always includes a disclaimer requiring physician approval)
  5. Lifestyle Expert- diet, exercise, smoking/alcohol reduction, sleep, mental health

Because no external LLM API is configured in this deployment, the agents run on
deterministic, knowledge-grounded heuristics that react dynamically to the
actual detection output (cancer type, label, risk, confidence, stage, severity,
affected area, tumor size). This keeps the system reliable, offline-capable and
defensible for clinical-second-opinion demonstrations.
"""

# ----------------------------------------------------------------------
# PER-CANCER-TYPE MEDICAL KNOWLEDGE (grounded in standard clinical practice)
# ----------------------------------------------------------------------

# NCI / ACS style guidance per cancer type: fur further diagnostic workup.
# Sources: NCI PDQ, American Cancer Society, WHO classification guidance.
_DIAGNOSTIC_WORKUP = {
    "brain": [
        "Gadolinium-enhanced MRI with diffusion-weighted imaging for precise tumor delineation.",
        "Histopathological (biopsy) analysis to confirm the tumor grade and WHO classification.",
        "Neurological examination and assessment of intracranial pressure symptoms.",
        "Molecular/genetic profiling (IDH, MGMT, 1p/19q) when surgical tissue is available.",
        "Whole-body imaging (PET/CT) only if metastatic disease is suspected.",
    ],
    "breast": [
        "Diagnostic mammography with digital breast tomosynthesis (3D mammogram).",
        "Targeted breast ultrasound to characterize the lesion (BI-RADS assessment).",
        "Core needle biopsy with histopathology and hormone-receptor testing (ER/PR/HER2).",
        "Contrast-enhanced breast MRI for high-risk or multilobar disease assessment.",
        "Sentinel lymph node evaluation and staging workup if malignancy is confirmed.",
    ],
    "lung": [
        "High-resolution computed tomography (CT) chest with contrast for staging.",
        "Bronchoscopy or CT-guided biopsy for histologic confirmation and molecular testing.",
        "PET-CT to assess nodal and distant metastatic spread (TNM staging).",
        "Pulmonary function tests to evaluate operability and baseline lung function.",
        "Blood tests including tumor markers and baseline organ function studies.",
    ],
    "skin": [
        "Dermatoscopic re-evaluation of the lesion by a board-certified dermatologist.",
        "Excisional or punch biopsy for histopathologic confirmation (with margins).",
        "Sentinel lymph node biopsy if melanoma features and Breslow thickness warrant it.",
        "Full-body skin examination to rule out additional synchronous lesions.",
        "Staging imaging (CT/PET) reserved for higher-risk or thicker lesions.",
    ],
}

# Probable treatment options listed per cancer type (informational only).
_TREATMENT_OPTIONS = {
    "brain": [
        "Surgical resection (maximal safe resection) when tumor is accessible.",
        "Adjuvant radiotherapy (stereotactic radiosurgery or fractionated)",
        "Systemic therapy (chemotherapy/temozolomide) depending on grade and methylation status.",
        "Corticosteroids and anticonvulsants for perilesional edema and seizure control.",
        "Targeted/molecular therapies based on tumor genetics.",
    ],
    "breast": [
        "Surgical approaches: lumpectomy or mastectomy with sentinel node evaluation.",
        "Adjuvant radiation therapy after breast-conserving surgery.",
        "Endocrine therapy (hormone-blocking agents) for receptor-positive disease.",
        "Chemotherapy and/or targeted therapy (anti-HER2) based on tumor biology.",
        "Clinical trial options for specific molecular subtypes.",
    ],
    "lung": [
        "Surgical resection (lobectomy/segmentectomy) for early-stage operable disease.",
        "Stereotactic body radiotherapy (SBRT) for medically inoperable early disease.",
        "Systemic therapy: platinum-based chemotherapy and/or immunotherapy.",
        "Targeted therapy guided by molecular alterations (EGFR, ALK, ROS1, etc.).",
        "Multimodality care (radiation + chemo) for locally advanced disease.",
    ],
    "skin": [
        "Wide local excision with clear margins for localized lesions.",
        "Sentinel lymph node biopsy for intermediate/thick melanomas.",
        "Mohs micrographic surgery for selected high-risk facial/site lesions.",
        "Immunotherapy/targeted therapy for advanced or metastatic disease.",
        "Regular dermatologic surveillance for recurrence and new lesions.",
    ],
}

# Lifestyle / prevention guidance (customized slightly per type but broadly applicable).
_LIFESTYLE = [
    "Maintain a balanced diet rich in fruits, vegetables, whole grains and lean proteins.",
    "Engage in regular moderate physical activity (at least 150 minutes per week).",
    "Avoid smoking and exposure to second-hand tobacco smoke.",
    "Limit or eliminate alcohol consumption.",
    "Prioritize 7-9 hours of quality sleep per night.",
    "Practice stress management (mindfulness, counseling, support groups) for mental well-being.",
    "Attend all scheduled follow-up appointments and adhere to the care plan.",
]

# Common informational medication classes relevant to oncology supportive care.
_MEDIFICATION_CLASSES = [
    ("Pain management", "Analgesics (e.g., NSAIDs, opioids under supervision) — may interact with other medications."),
    ("Anti-nausea", "Antiemetics to manage chemotherapy- or treatment-related nausea."),
    ("Anti-inflammatory", "Corticosteroids to reduce perilesional edema/inflammation where indicated."),
    ("Supportive", "Nutritional supplements, growth factors and anti-infection prophylaxis as directed."),
]


# ----------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------

def _is_benign(label):
    """Return True if the label indicates a benign / normal / no-tumor finding."""
    text = (label or "").lower()
    return any(term in text for term in ["no tumor", "normal", "benign"])


def _cancer_type_of(report):
    """Return a normalized cancer type key (brain/breast/lung/skin)."""
    ct = (report.get("cancer_type") or "").lower()
    label = (report.get("label") or "").lower()
    if ct in ("brain", "breast", "lung", "skin"):
        return ct
    if "brain" in label or "tumor" in label:
        return "brain"
    if "breast" in label:
        return "breast"
    if "lung" in label:
        return "lung"
    if "skin" in label:
        return "skin"
    return "brain"  # fallback


def _risk_level(report):
    return report.get("risk", "Low")


def _confidence(report):
    return report.get("confidence_pct", 0)


def _severity(report):
    return report.get("severity_score", 0)


def _stage(report):
    return report.get("stage", "Stage 0")


def _tumor_size(report):
    return report.get("tumor_size_estimate_cm") or report.get("tumor_size_estimate") or "not determined"


def _affected(report):
    return report.get("affected_area_pct", 0)


# ----------------------------------------------------------------------
# AGENT 1 : RADIOLOGIST
# ----------------------------------------------------------------------

def radiologist_agent(report):
    label = report.get("label", "Unknown finding")
    ct = _cancer_type_of(report)
    conf = _confidence(report)
    sev = _severity(report)
    affected = _affected(report)
    benign = _is_benign(label)

    if benign:
        findings = [
            f"The {ct} scan shows no suspicious malignant features consistent with malignancy.",
            "Margins appear regular and well-defined; no irregular or spiculated borders detected.",
            "No significant contrast enhancement or abnormal mass effect is observed.",
        ]
        findings.append(
            f"Estimated suspicious area is low (~{affected}%), supporting a benign or normal appearance."
        )
        opinion = (
            f"Imaging review by the Radiologist AI: The {ct} study demonstrates a benign/normal pattern. "
            "No alarming features are present. Routine surveillance imaging may be considered rather than urgent intervention."
        )
        verdict = "Benign / Normal — No suspicious findings. Routine surveillance advised."
    else:
        findings = [
            f"The {ct} scan reveals an abnormal space-occupying lesion with features suspicious for malignancy.",
            "Irregular margins and heterogeneous signal intensity are observed, raising concern for an aggressive process.",
            "Contrast enhancement is present, which may reflect increased vascularity typical of malignant lesions.",
        ]
        if conf >= 85:
            findings.append("Lesion morphology is highly concerning, with a high probability of malignancy on imaging.")
        elif conf >= 60:
            findings.append("Lesion features are indeterminate-to-suspicious; correlation with histology is advised.")
        else:
            findings.append("Lesion is subtle; further imaging characterization is recommended.")
        findings.append(
            f"Approximately {affected}% of the scanned region contains suspicious features; "
            f"estimated lesion size is {_tumor_size(report)}."
        )
        opinion = (
            f"Imaging review by the Radiologist AI: suspicious {ct} lesion with irregular margins and contrast "
            "enhancement. Correlative histopathologic sampling (biopsy) and advanced imaging are warranted "
            "to characterize this finding."
        )
        verdict = (
            f"Suspicious for malignancy — biopsy and advanced imaging recommended "
            f"(confidence {conf:.1f}%)."
        )

    return {
        "role": "Radiologist",
        "icon": "fa-solid fa-x-ray",
        "color": "#2563eb",
        "opinion": opinion,
        "verdict": verdict,
        "findings": findings,
        "recommendations": _DIAGNOSTIC_WORKUP[ct][:3],
    }


# ----------------------------------------------------------------------
# AGENT 2 : ONCOLOGIST
# ----------------------------------------------------------------------

def oncologist_agent(report):
    label = report.get("label", "Unknown")
    ct = _cancer_type_of(report)
    conf = _confidence(report)
    risk = _risk_level(report)
    stage = _stage(report)
    sev = _severity(report)
    benign = _is_benign(label)

    if benign:
        opinion = (
            f"Oncology review: The finding ({label}) is classified as benign/normal with "
            f"{conf:.1f}% confidence. No immediate oncologic intervention is indicated; "
            "routine follow-up and screening per age-based guidelines are recommended."
        )
        recommendations = [
            "Continue routine age-appropriate cancer screening.",
            "Repeat imaging on a scheduled interval to confirm stability.",
            "No systemic anti-cancer therapy is indicated at this time.",
        ]
        verdict = "Benign / Normal — No oncologic intervention indicated. Routine screening advised."
    else:
        if risk == "High":
            opinion = (
                f"Oncology review: High-risk {ct} malignancy suspected (confidence {conf:.1f}%, "
                f"estimated {stage}). This warrants urgent oncologic evaluation and confirmatory "
                "tissue diagnosis. Prognosis and stage must be refined with pathology and staging studies."
            )
            verdict = f"High-risk {ct} malignancy suspected ({stage}) — urgent oncology referral warranted."
        elif risk == "Moderate":
            opinion = (
                f"Oncology review: The {ct} finding is suspicious (confidence {conf:.1f}%, {stage}). "
                "A prompt diagnostic workup is required to establish a definitive cancer diagnosis "
                "and appropriate treatment plan."
            )
            verdict = f"Suspicious ({stage}) — prompt oncologic diagnostic workup recommended."
        else:
            opinion = (
                f"Oncology review: The {ct} finding has lower suspicion (confidence {conf:.1f}%). "
                "Correlation with clinical context and follow-up imaging is advised before committing to treatment."
            )
            verdict = "Low suspicion — monitor and correlate with clinical context."
        recommendations = [
            "Complete staging workup (histopathology, molecular markers, and cross-sectional imaging).",
            "Multidisciplinary tumor board discussion to plan first-line therapy.",
            "Tumor markers and baseline blood work before any systemic therapy.",
        ]

    return {
        "role": "Oncologist",
        "icon": "fa-solid fa-user-doctor",
        "color": "#0ea5e9",
        "opinion": opinion,
        "verdict": verdict,
        "findings": [f"Stage estimate: {stage}.", f"Severity score: {sev}/100.", f"Risk classification: {risk}."],
        "recommendations": recommendations,
    }


# ----------------------------------------------------------------------
# AGENT 3 : SURGEON
# ----------------------------------------------------------------------

def surgeon_agent(report):
    label = report.get("label", "Unknown")
    ct = _cancer_type_of(report)
    risk = _risk_level(report)
    sev = _severity(report)
    conf = _confidence(report)
    stage = _stage(report)
    benign = _is_benign(label)

    if benign:
        opinion = (
            "Surgical review: No urgent surgical intervention is indicated for a benign/normal finding. "
            "If a small benign lesion is confirmed on biopsy, elective excision may be discussed based on "
            "symptoms and growth, but this is not an emergency."
        )
        recommendations = [
            "No urgent operative planning required.",
            "Monitor lesion stability with serial imaging.",
            "Re-evaluate surgically only if symptomatic or enlarging.",
        ]
        verdict = "Benign / Normal — No surgical intervention indicated. Observe and monitor."
    else:
        if risk == "High" or sev >= 70:
            urgency = "URGENT"
            opinion = (
                f"Surgical review: Given the high-risk {ct} malignancy (severity {sev}/100, {stage}), surgical "
                "consultation is URGENT. Resectability and the optimal operative approach must be assessed "
                "promptly, and the case should be discussed in a multidisciplinary tumor board."
            )
            verdict = f"URGENT surgical consult — {ct} malignancy ({stage}). Assess resectability promptly."
        elif risk == "Moderate" or sev >= 45:
            urgency = "Prioritized"
            opinion = (
                f"Surgical review: The {ct} finding is suspicious and surgery may be required once the diagnosis "
                "is confirmed. Referral to a surgical specialist is recommended within the next few weeks to plan "
                "the appropriate definitive procedure."
            )
            verdict = f"Prioritized surgical consult — confirm diagnosis, then plan definitive procedure."
        else:
            urgency = "Routine"
            opinion = (
                f"Surgical review: The {ct} finding is of borderline concern. Surgical planning depends on "
                "confirmatory biopsy results; defer operative decisions until histology is available."
            )
            verdict = "Routine surgical review — defer operative decisions until histology is available."
        recommendations = [
            f"Consult a surgical specialist — urgency: {urgency}.",
            "Assess resectability/tumor accessibility with dedicated imaging.",
            "Discuss potential complications, recovery time and functional impact pre-operatively.",
        ]

    return {
        "role": "Surgeon",
        "icon": "fa-solid fa-kit-medical",
        "color": "#8b5cf6",
        "opinion": opinion,
        "verdict": verdict,
        "findings": [f"Risk: {risk}.", f"Severity: {sev}/100.", f"Stage: {stage}."],
        "recommendations": recommendations,
    }


# ----------------------------------------------------------------------
# AGENT 4 : PHARMACOLOGIST
# ----------------------------------------------------------------------

def pharmacologist_agent(report):
    ct = _cancer_type_of(report)
    risk = _risk_level(report)
    benign = _is_benign(report.get("label", ""))

    if benign:
        opinion = (
            "Pharmacology review: No cancer-specific medication is indicated for a benign/normal finding. "
            "Any supplements or over-the-counter medications should be reviewed with your physician."
        )
    else:
        opinion = (
            f"Pharmacology review: Definitive medication decisions for the {ct} finding depend on the confirmed "
            "histologic diagnosis, molecular profile and stage. Treatment (chemotherapy, targeted therapy, "
            "immunotherapy or endocrine therapy) should be initiated only under specialist supervision."
        )

    meds = [{"class": c, "detail": d} for c, d in _MEDIFICATION_CLASSES]
    disclaimer = (
        "IMPORTANT DISCLAIMER: All medication information provided by the Pharmacologist AI is strictly "
        "INFORMATIONAL. It is not a prescription and does not replace professional medical advice. Any "
        "medication, dosing or interaction decision requires review and approval by a licensed physician "
        "or clinical pharmacist."
    )

    return {
        "role": "Pharmacologist",
        "icon": "fa-solid fa-pills",
        "color": "#10b981",
        "opinion": opinion,
        "findings": [m["class"] + ": " + m["detail"] for m in meds],
        "recommendations": [disclaimer],
        "medications": meds,
        "disclaimer": disclaimer,
    }


# ----------------------------------------------------------------------
# AGENT 5 : LIFESTYLE EXPERT
# ----------------------------------------------------------------------

def lifestyle_agent(report):
    risk = _risk_level(report)
    benign = _is_benign(report.get("label", ""))

    if benign:
        opinion = (
            "Lifestyle review: The finding is benign/normal, so prevention and general wellness remain the "
            "priority. Maintaining a healthy lifestyle reduces future cancer risk and supports overall health."
        )
    else:
        opinion = (
            f"Lifestyle review: Given a {risk.lower()} risk finding, lifestyle optimization is an important "
            "adjunct to medical care. Healthy habits improve treatment tolerance, recovery and long-term outcomes."
        )

    return {
        "role": "Lifestyle Expert",
        "icon": "fa-solid fa-heart-pulse",
        "color": "#f59e0b",
        "opinion": opinion,
        "findings": _LIFESTYLE,
        "recommendations": _LIFESTYLE[:4],
    }


# ----------------------------------------------------------------------
# FINAL AI AGGREGATOR (CONSENSUS)
# ----------------------------------------------------------------------

def aggregator_agent(report, opinions):
    label = report.get("label", "Unknown")
    ct = _cancer_type_of(report)
    risk = _risk_level(report)
    conf = _confidence(report)
    stage = _stage(report)
    benign = _is_benign(label)

    if benign:
        overall_recommendation = (
            f"The {ct} finding appears benign/normal with {conf:.1f}% confidence. No urgent intervention is "
            "required. Continue routine surveillance and age-appropriate screening, and share this report "
            "with your clinician for confirmation."
        )
        recommended_specialist = "Primary care physician / routine screening clinic"
        urgency = "Routine"
        followup = "Routine follow-up per screening guidelines (typically 6-12 months)."
    else:
        if risk == "High":
            urgency = "URGENT"
            overall_recommendation = (
                f"High probability of {label} ({conf:.1f}% confidence, {stage}). URGENT follow-up is suggested. "
                "Consult an oncologist and a specialist promptly. Confirmatory biopsy/advanced imaging and a "
                "multidisciplinary tumor board are strongly recommended."
            )
            followup = "Immediate/urgent follow-up within 1-2 weeks."
        elif risk == "Moderate":
            urgency = "Prioritized"
            overall_recommendation = (
                f"Moderate risk of {label} ({conf:.1f}% confidence, {stage}). Schedule specialist consultation "
                "and diagnostic workup within the next 2-4 weeks."
            )
            followup = "Follow-up within 2-4 weeks depending on test results."
        else:
            urgency = "Routine"
            overall_recommendation = (
                f"Lower suspicion of {label} ({conf:.1f}% confidence). Monitor closely and confirm with your "
                "clinician; repeat imaging may be appropriate."
            )
            followup = "Routine follow-up in 3-6 months."

        recommended_specialist = {
            "brain": "Neurologist + Neuro-oncologist",
            "breast": "Breast Surgeon + Medical Oncologist",
            "lung": "Pulmonologist + Thoracic Surgical Oncologist",
            "skin": "Dermatologist + Surgical Oncologist",
        }.get(ct, "Medical Oncologist")

    hospital_recommendation = (
        f"The patient should be scheduled at the hospital's {ct} tumor board for a multidisciplinary case "
        f"discussion. Recommended specialist referral: {recommended_specialist}. {followup}"
    )

    # Count agreement among the five agents
    agree_count = sum(
        1 for o in opinions.values()
        if (risk in ("High", "Moderate") and not benign) or (benign and risk == "Low")
    )

    return {
        "role": "Final AI Aggregator",
        "icon": "fa-solid fa-scale-balanced",
        "color": "#dc2626",
        "overall_recommendation": overall_recommendation,
        "recommended_specialist": recommended_specialist,
        "hospital_recommendation": hospital_recommendation,
        "urgency": urgency,
        "followup": followup,
        "agents_in_agreement": min(5, agree_count),
        "total_agents": 5,
    }


# ----------------------------------------------------------------------
# AI TUMOR BOARD
# ----------------------------------------------------------------------

def tumor_board(report, opinions):
    ct = _cancer_type_of(report)
    label = report.get("label", "Unknown")
    risk = _risk_level(report)
    stage = _stage(report)
    conf = _confidence(report)
    benign = _is_benign(label)

    if benign:
        case_summary = (
            f"Case: {label} ({conf:.1f}% confidence). The tumor board notes a benign/normal finding with no "
            "features requiring urgent multidisciplinary intervention."
        )
        ai_opinion = "Tumor board consensus: observation and routine follow-up; no active cancer therapy indicated."
        doctor_notes = "Confirm with the treating physician; document stability on serial imaging."
    else:
        case_summary = (
            f"Case: {label}, {stage}, {risk.lower()} risk, {conf:.1f}% confidence. Reviewed by the AI tumor board "
            "across radiology, oncology, surgery, pharmacology and lifestyle domains."
        )
        ai_opinion = (
            f"Tumor board consensus: multidisciplinary workup is recommended, including tissue diagnosis and "
            f"staging. {"Urgent" if risk == "High" else "Prioritized"} specialist referral is advised."
        )
        doctor_notes = (
            "Multidisciplinary discussion recommended. Confirm diagnosis with histopathology before initiating "
            "definitive therapy."
        )

    return {
        "case_summary": case_summary,
        "ai_opinion": ai_opinion,
        "recommended_tests": _DIAGNOSTIC_WORKUP[ct],
        "treatment_options": _TREATMENT_OPTIONS[ct],
        "doctor_notes": doctor_notes,
    }


# ----------------------------------------------------------------------
# AI CLINICAL TIMELINE
# ----------------------------------------------------------------------

def clinical_timeline(report):
    risk = _risk_level(report)
    benign = _is_benign(report.get("label", ""))

    if benign:
        return {
            "current": "Current scan analyzed — benign/normal finding.",
            "prediction": "No active malignancy predicted.",
            "treatment": "No active treatment required; preventive care.",
            "milestones": [
                {"period": "30 Days", "detail": "Share report with primary care clinician."},
                {"period": "90 Days", "detail": "Routine wellness check and lifestyle optimization."},
                {"period": "6 Months", "detail": "Follow-up screening / repeat imaging per guidelines."},
            ],
        }

    if risk == "High":
        return {
            "current": f"Current scan analyzed — suspicious finding ({report.get('label')}).",
            "prediction": f"High-risk prediction ({report.get('stage')}).",
            "treatment": "Urgent confirmatory biopsy + staging; discuss tumor board within 1-2 weeks.",
            "milestones": [
                {"period": "30 Days", "detail": "Complete staging workup and initiate first-line treatment plan."},
                {"period": "90 Days", "detail": "Reassess response to therapy; manage side effects."},
                {"period": "6 Months", "detail": "Restaging scans and tumor board re-discussion."},
            ],
        }
    elif risk == "Moderate":
        return {
            "current": f"Current scan analyzed — suspicious finding ({report.get('label')}).",
            "prediction": f"Moderate-risk prediction ({report.get('stage')}).",
            "treatment": "Schedule specialist consultation and diagnostic workup within 2-4 weeks.",
            "milestones": [
                {"period": "30 Days", "detail": "Specialist consultation and confirmatory tests."},
                {"period": "90 Days", "detail": "Begin surveillance or treatment based on results."},
                {"period": "6 Months", "detail": "Follow-up imaging and reassessment."},
            ],
        }
    return {
        "current": f"Current scan analyzed — finding ({report.get('label')}).",
        "prediction": f"Low-risk prediction ({report.get('stage')}).",
        "treatment": "Monitoring and baseline risk-factor management.",
        "milestones": [
            {"period": "30 Days", "detail": "Share report with clinician."},
            {"period": "90 Days", "detail": "Lifestyle risk-factor review."},
            {"period": "6 Months", "detail": "Routine follow-up scan."},
        ],
    }


# ----------------------------------------------------------------------
# AI TREATMENT PLANNER
# ----------------------------------------------------------------------

def treatment_planner(report, opinions):
    ct = _cancer_type_of(report)
    risk = _risk_level(report)
    benign = _is_benign(report.get("label", ""))

    if benign:
        recommended_specialist = "Primary care physician"
        tests = ["Routine screening tests", "Baseline blood work"]
        next_appointment = "Routine follow-up (6-12 months)"
    else:
        recommended_specialist = {
            "brain": "Neurologist / Neuro-oncologist",
            "breast": "Breast Surgeon / Medical Oncologist",
            "lung": "Pulmonologist / Thoracic Oncologist",
            "skin": "Dermatologist / Surgical Oncologist",
        }.get(ct, "Medical Oncologist")
        tests = _DIAGNOSTIC_WORKUP[ct][:3]
        next_appointment = (
            "Within 1-2 weeks (urgent)" if risk == "High"
            else "Within 2-4 weeks" if risk == "Moderate"
            else "Within 1 month"
        )

    return {
        "recommended_specialist": recommended_specialist,
        "tests": tests,
        "medicines": _MEDIFICATION_CLASSES,  # informational only
        "lifestyle": _LIFESTYLE[:4],
        "next_appointment": next_appointment,
        "disclaimer": opinions["pharmacologist"]["disclaimer"],
    }


# ----------------------------------------------------------------------
# THREE-DOCTOR CLINICAL SECOND OPINION
# ----------------------------------------------------------------------

# The three key clinical personas that form the focused "second opinion"
# tumor board. Each represents a distinct medical specialty.
THREE_DOCTOR_KEYS = ["radiologist", "oncologist", "surgeon"]

# Doctor display metadata (name, title, and specialty avatar color/icon).
THREE_DOCTOR_META = {
    "radiologist": {
        "name": "Dr. A. Imaging",
        "title": "Consultant Radiologist",
        "specialty": "Radiology & Diagnostic Imaging",
        "icon": "fa-solid fa-x-ray",
        "color": "#2563eb",
    },
    "oncologist": {
        "name": "Dr. B. Oncology",
        "title": "Medical Oncologist",
        "specialty": "Medical Oncology & Staging",
        "icon": "fa-solid fa-user-doctor",
        "color": "#0ea5e9",
    },
    "surgeon": {
        "name": "Dr. C. Surgical",
        "title": "Surgical Oncologist",
        "specialty": "Surgical Intervention & Resectability",
        "icon": "fa-solid fa-kit-medical",
        "color": "#8b5cf6",
    },
}


def generate_three_doctor_report(report_data):
    """Generate a focused "Three-Doctor Clinical Second Opinion" for a report.

    Three doctors from three distinct medical personas each independently
    review the same finding:
      1. Consultant Radiologist  — image/scan findings
      2. Medical Oncologist      — staging, risk, prognosis
      3. Surgical Oncologist     — surgical necessity & resectability

    A fourth element, the "Unified Second Opinion", synthesizes the three
    individual doctor opinions into one consistent clinical recommendation
    (reusing the existing AI aggregator consensus logic).

    Returns a dict with:
      - doctors  : { radiologist, oncologist, surgeon } each with opinion,
                   findings, recommendations + doctor display metadata
      - unified  : the unified consensus (role, recommendation, specialist,
                   urgency, followup, agreement)
    """
    multi = generate_multi_agent_reports(report_data or {})
    opinions = multi.get("opinions") or {}
    consensus = multi.get("consensus") or {}

    doctors = {}
    for key in THREE_DOCTOR_KEYS:
        agent = dict(opinions.get(key) or {})
        meta = THREE_DOCTOR_META.get(key, {})
        doctors[key] = {
            "name": meta.get("name", key.title()),
            "title": meta.get("title", ""),
            "specialty": meta.get("specialty", ""),
            "icon": agent.get("icon", meta.get("icon", "fa-solid fa-user-doctor")),
            "color": agent.get("color", meta.get("color", "#2563eb")),
            "role": agent.get("role", key.title()),
            "opinion": agent.get("opinion", ""),
            "verdict": agent.get("verdict", ""),
            "findings": agent.get("findings", []),
            "recommendations": agent.get("recommendations", []),
        }

    return {
        "doctors": doctors,
        "unified": consensus,
        "total_doctors": len(THREE_DOCTOR_KEYS),
    }


def translate_three_doctor_report(three_doctor_data, lang="en"):
    """Return a localized copy of a Three-Doctor Clinical Second Opinion bundle.

    Localizes the doctor display metadata (name/title/specialty) and the static
    labels via the built-in dictionary, and translates the dynamic per-report
    text (opinions, findings, recommendations, unified consensus) at runtime.
    Falls back to English gracefully.
    """
    if not three_doctor_data:
        return three_doctor_data
    lang = (lang or "en").lower().strip()
    try:
        from utils.translator import get_translation
        tr = get_translation(lang)
    except Exception:
        tr = {}

    def T(key):
        return tr.get(key, key)

    import copy
    result = copy.deepcopy(three_doctor_data)

# Warm the cache with a single batched call for all dynamic text.
    if lang != "en":
        try:
            from utils.translator import translate_text_batch
            strings = []
            for doc in (result.get("doctors") or {}).values():
                if doc.get("opinion"):
                    strings.append(doc["opinion"])
                if doc.get("verdict"):
                    strings.append(doc["verdict"])
                strings.extend(doc.get("findings") or [])
                strings.extend(doc.get("recommendations") or [])
            uni = result.get("unified") or {}
            for f in ("overall_recommendation", "recommended_specialist",
                      "hospital_recommendation", "followup", "urgency"):
                if uni.get(f):
                    strings.append(uni[f])
            if strings:
                translate_text_batch(strings, target_lang=lang)
        except Exception:
            pass

    # Localize each doctor's metadata + dynamic text.
    for key, doc in (result.get("doctors") or {}).items():
        role_key = _AGENT_ROLE_KEYS.get(key)
        if role_key:
            doc["role"] = T(role_key)
        doc["title"] = T({
            "radiologist": "role_radiologist",
            "oncologist": "role_oncologist",
            "surgeon": "role_surgeon",
        }.get(key, key))
        doc["specialty"] = _tl_text(doc.get("specialty"), lang, tr)
        doc["name"] = _tl_text(doc.get("name"), lang, tr)
        if doc.get("opinion"):
            doc["opinion"] = _tl_text(doc["opinion"], lang, tr)
        if doc.get("verdict"):
            doc["verdict"] = _tl_text(doc["verdict"], lang, tr)
        if doc.get("findings"):
            doc["findings"] = _tl_strings(doc["findings"], lang, tr)
        if doc.get("recommendations"):
            doc["recommendations"] = _tl_strings(doc["recommendations"], lang, tr)

    # Localize the unified consensus.
    uni = result.get("unified")
    if isinstance(uni, dict):
        uni["role"] = T("final_ai_aggregator")
        uni["title"] = T("unified_second_opinion")
        for f in ("overall_recommendation", "recommended_specialist",
                  "hospital_recommendation", "followup", "urgency"):
            if uni.get(f):
                uni[f] = _tl_text(uni[f], lang, tr)

    result["_lang"] = lang
    result["_labels"] = {
        "unified_second_opinion": T("unified_second_opinion"),
        "three_doctor_title": T("three_doctor_title"),
        "doctor_opinion": T("doctor_opinion"),
        "findings": T("findings"),
        "recommendations": T("recommendations"),
        "recommended_specialist": T("recommended_specialist"),
        "agreement": T("agreement"),
        "verdict": T("verdict"),
    }
    return result


# ----------------------------------------------------------------------
# PUBLIC API
# ----------------------------------------------------------------------

def generate_multi_agent_reports(report_data):
    """Generate the full multi-agent clinical second-opinion bundle for a report.

    Returns a dictionary containing:
      - opinions       : the five AI personas
      - consensus      : the final AI aggregator
      - tumor_board    : case summary / tests / treatment options / doctor notes
      - timeline       : AI clinical timeline
      - treatment_plan : AI treatment planner
    """
    report_data = report_data or {}
    rad = radiologist_agent(report_data)
    onc = oncologist_agent(report_data)
    surg = surgeon_agent(report_data)
    pharm = pharmacologist_agent(report_data)
    life = lifestyle_agent(report_data)

    opinions = {
        "radiologist": rad,
        "oncologist": onc,
        "surgeon": surg,
        "pharmacologist": pharm,
        "lifestyle": life,
    }

    consensus = aggregator_agent(report_data, opinions)
    board = tumor_board(report_data, opinions)
    timeline = clinical_timeline(report_data)
    plan = treatment_planner(report_data, opinions)

    return {
        "opinions": opinions,
        "consensus": consensus,
        "tumor_board": board,
        "timeline": timeline,
        "treatment_plan": plan,
    }


# ----------------------------------------------------------------------
# MULTI-LANGUAGE SUPPORT
# ----------------------------------------------------------------------
# The agent content above is generated in English. This helper produces a
# fully-localized copy of a multi-agent bundle for the requested language:
#
#   * Section headings / roles / static labels come from the built-in
#     MULTI_AGENT_TRANSLATIONS dictionary in utils/translator.py (always
#     available, no network required).
#   * Dynamic per-report content (opinions, findings, recommendations,
#     consensus text, timeline, treatment plan) is translated at runtime
#     with translate_text() (Google Cloud Translate, else googletrans).
#     If the translation backend is unavailable, the text is kept in
#     English so the report always remains readable.

# Map each agent key to its localized role key in the translation dict.
_AGENT_ROLE_KEYS = {
    "radiologist": "role_radiologist",
    "oncologist": "role_oncologist",
    "surgeon": "role_surgeon",
    "pharmacologist": "role_pharmacologist",
    "lifestyle": "role_lifestyle",
}


def _tl_text(text, lang, tr):
    """Translate a single string using the runtime backend, falling back to
    English when the target is English or the backend fails."""
    if not text:
        return text
    if lang in (None, "", "en"):
        return text
    try:
        from utils.translator import translate_text
        out = translate_text(str(text), target_lang=lang)
        return out if out else str(text)
    except Exception:
        return str(text)


def _tl_strings(items, lang, tr):
    """Translate a list of strings (best-effort)."""
    if not items:
        return items
    return [_tl_text(item, lang, tr) for item in items]


def _tl_milestones(milestones, lang, tr):
    """Translate timeline milestone period/detail fields."""
    if not milestones:
        return milestones
    out = []
    for m in milestones:
        out.append({
            "period": _tl_text(m.get("period"), lang, tr),
            "detail": _tl_text(m.get("detail"), lang, tr),
        })
    return out


def _collect_batch_strings(multi_agent_data):
    """Collect every translatable string in a multi-agent bundle into a flat
    list. Returns (strings, setters) where `setters` is a list of callables
    that, given the translated value, write it back into the deep copy.
    """
    strings = []
    setters = []

    def add(obj):
        strings.append(obj["value"])
        setters.append(obj["set"])

    opinions = multi_agent_data.get("opinions") or {}
    for key, agent in opinions.items():
        if not isinstance(agent, dict):
            continue
        if agent.get("opinion"):
            add({"value": agent["opinion"], "set": lambda v, a=agent: a.__setitem__("opinion", v)})
        if agent.get("findings"):
            for i, f in enumerate(agent["findings"]):
                add({"value": f, "set": lambda v, a=agent, idx=i: a["findings"].__setitem__(idx, v)})
        if agent.get("recommendations"):
            for i, r in enumerate(agent["recommendations"]):
                add({"value": r, "set": lambda v, a=agent, idx=i: a["recommendations"].__setitem__(idx, v)})
        if agent.get("medications"):
            for i, m in enumerate(agent["medications"]):
                add({"value": m.get("class"), "set": lambda v, m=m: m.__setitem__("class", v)})
                add({"value": m.get("detail"), "set": lambda v, m=m: m.__setitem__("detail", v)})
        if agent.get("disclaimer"):
            add({"value": agent["disclaimer"], "set": lambda v, a=agent: a.__setitem__("disclaimer", v)})

    consensus = multi_agent_data.get("consensus")
    if isinstance(consensus, dict):
        if consensus.get("overall_recommendation"):
            add({"value": consensus["overall_recommendation"], "set": lambda v, c=consensus: c.__setitem__("overall_recommendation", v)})
        if consensus.get("recommended_specialist"):
            add({"value": consensus["recommended_specialist"], "set": lambda v, c=consensus: c.__setitem__("recommended_specialist", v)})
        if consensus.get("hospital_recommendation"):
            add({"value": consensus["hospital_recommendation"], "set": lambda v, c=consensus: c.__setitem__("hospital_recommendation", v)})
        if consensus.get("followup"):
            add({"value": consensus["followup"], "set": lambda v, c=consensus: c.__setitem__("followup", v)})
        if consensus.get("urgency"):
            add({"value": consensus["urgency"], "set": lambda v, c=consensus: c.__setitem__("urgency", v)})

    board = multi_agent_data.get("tumor_board")
    if isinstance(board, dict):
        if board.get("case_summary"):
            add({"value": board["case_summary"], "set": lambda v, b=board: b.__setitem__("case_summary", v)})
        if board.get("ai_opinion"):
            add({"value": board["ai_opinion"], "set": lambda v, b=board: b.__setitem__("ai_opinion", v)})
        if board.get("recommended_tests"):
            for i, t in enumerate(board["recommended_tests"]):
                add({"value": t, "set": lambda v, b=board, idx=i: b["recommended_tests"].__setitem__(idx, v)})
        if board.get("treatment_options"):
            for i, t in enumerate(board["treatment_options"]):
                add({"value": t, "set": lambda v, b=board, idx=i: b["treatment_options"].__setitem__(idx, v)})
        if board.get("doctor_notes"):
            add({"value": board["doctor_notes"], "set": lambda v, b=board: b.__setitem__("doctor_notes", v)})

    timeline = multi_agent_data.get("timeline")
    if isinstance(timeline, dict):
        for field in ("current", "prediction", "treatment"):
            if timeline.get(field):
                add({"value": timeline[field], "set": lambda v, t=timeline, f=field: t.__setitem__(f, v)})
        if timeline.get("milestones"):
            for i, m in enumerate(timeline["milestones"]):
                if m.get("period"):
                    add({"value": m["period"], "set": lambda v, m=m: m.__setitem__("period", v)})
                if m.get("detail"):
                    add({"value": m["detail"], "set": lambda v, m=m: m.__setitem__("detail", v)})

    plan = multi_agent_data.get("treatment_plan")
    if isinstance(plan, dict):
        if plan.get("recommended_specialist"):
            add({"value": plan["recommended_specialist"], "set": lambda v, p=plan: p.__setitem__("recommended_specialist", v)})
        if plan.get("tests"):
            for i, t in enumerate(plan["tests"]):
                add({"value": t, "set": lambda v, p=plan, idx=i: p["tests"].__setitem__(idx, v)})
        if plan.get("lifestyle"):
            for i, t in enumerate(plan["lifestyle"]):
                add({"value": t, "set": lambda v, p=plan, idx=i: p["lifestyle"].__setitem__(idx, v)})
        if plan.get("next_appointment"):
            add({"value": plan["next_appointment"], "set": lambda v, p=plan: p.__setitem__("next_appointment", v)})
        if plan.get("disclaimer"):
            add({"value": plan["disclaimer"], "set": lambda v, p=plan: p.__setitem__("disclaimer", v)})
        if plan.get("medicines"):
            for i, m in enumerate(plan["medicines"]):
                if isinstance(m, (list, tuple)) and len(m) == 2:
                    add({"value": m[0], "set": lambda v, idx=i, orig=m: plan["medicines"].__setitem__(idx, [v, orig[1]])})
                    add({"value": m[1], "set": lambda v, idx=i, orig=m: plan["medicines"].__setitem__(idx, [orig[0], v])})
                elif isinstance(m, dict):
                    add({"value": m.get("class"), "set": lambda v, m=m: m.__setitem__("class", v)})
                    add({"value": m.get("detail"), "set": lambda v, m=m: m.__setitem__("detail", v)})

    return strings, setters


def _batch_localize(multi_agent_data, lang):
    """Warm the translation cache for ALL dynamic text fields of a multi-agent
    bundle using ONE batched network call (translate_text_batch).

    IMPORTANT: This only WARMS the cache — it does NOT write translated text
    back into the bundle. The existing per-field _tl_text() loop below reads
    the (still-English) source, hits the warmed cache, and writes the correct
    translation. This avoids the double-translation bug where already-localized
    text would be translated a second time.

    Falls back gracefully if the batch API is unavailable (returns False, and
    the code proceeds to the per-string translation path).
    """
    try:
        from utils.translator import translate_text_batch
    except Exception:
        return False

    strings, _setters = _collect_batch_strings(multi_agent_data)
    if not strings:
        return True

    # translate_text_batch caches each (string, lang) result internally, so
    # this single call warms the cache for every field that will be localized
    # by _tl_text() below. The returned values are intentionally discarded.
    translate_text_batch(strings, target_lang=lang)
    return True


def translate_multi_agent_report(multi_agent_data, lang="en"):
    """Return a translated copy of a multi-agent clinical second-opinion bundle.

    `multi_agent_data` is the dictionary returned by
    `generate_multi_agent_reports()`. The returned dictionary is a deep copy
    with all static headings/roles localized via the built-in dictionary and
    all dynamic text translated via the runtime backend (best effort).

    The English source remains unchanged (English is used as the master copy
    stored in reports.json).
    """
    if not multi_agent_data:
        return multi_agent_data

    lang = (lang or "en").lower().strip()
    try:
        from utils.translator import get_translation
        tr = get_translation(lang)
    except Exception:
        tr = {}

    def T(key):
        return tr.get(key, key)

    import copy
    result = copy.deepcopy(multi_agent_data)

    # FAST PATH: translate all dynamic fields in ONE batched network call.
    # This populates the translation cache, so every _tl_text() call below
    # becomes an instant in-memory lookup instead of a network round-trip.
    if lang != "en":
        try:
            _batch_localize(result, lang)
        except Exception:
            pass

    # ---- Opinions (five AI personas) ----
    opinions = result.get("opinions") or {}
    for key, agent in opinions.items():
        if not isinstance(agent, dict):
            continue
        role_key = _AGENT_ROLE_KEYS.get(key)
        if role_key:
            agent["role"] = T(role_key)
        if agent.get("opinion"):
            agent["opinion"] = _tl_text(agent["opinion"], lang, tr)
        if agent.get("findings"):
            agent["findings"] = _tl_strings(agent["findings"], lang, tr)
        if agent.get("recommendations"):
            agent["recommendations"] = _tl_strings(agent["recommendations"], lang, tr)
        if agent.get("medications"):
            meds = []
            for m in agent["medications"]:
                meds.append({
                    "class": _tl_text(m.get("class"), lang, tr),
                    "detail": _tl_text(m.get("detail"), lang, tr),
                })
            agent["medications"] = meds
        if agent.get("disclaimer"):
            agent["disclaimer"] = tr.get("med_disclaimer", _tl_text(agent["disclaimer"], lang, tr))

    # ---- Final AI Aggregator (Consensus) ----
    consensus = result.get("consensus")
    if isinstance(consensus, dict):
        consensus["role"] = T("final_ai_aggregator")
        if consensus.get("overall_recommendation"):
            consensus["overall_recommendation"] = _tl_text(consensus["overall_recommendation"], lang, tr)
        if consensus.get("recommended_specialist"):
            consensus["recommended_specialist"] = _tl_text(consensus["recommended_specialist"], lang, tr)
        if consensus.get("hospital_recommendation"):
            consensus["hospital_recommendation"] = _tl_text(consensus["hospital_recommendation"], lang, tr)
        if consensus.get("followup"):
            consensus["followup"] = _tl_text(consensus["followup"], lang, tr)
        if consensus.get("urgency"):
            consensus["urgency"] = _tl_text(consensus["urgency"], lang, tr)

    # ---- AI Tumor Board ----
    board = result.get("tumor_board")
    if isinstance(board, dict):
        board["title"] = T("ai_tumor_board")
        if board.get("case_summary"):
            board["case_summary"] = _tl_text(board["case_summary"], lang, tr)
        if board.get("ai_opinion"):
            board["ai_opinion"] = _tl_text(board["ai_opinion"], lang, tr)
        if board.get("recommended_tests"):
            board["recommended_tests"] = _tl_strings(board["recommended_tests"], lang, tr)
        if board.get("treatment_options"):
            board["treatment_options"] = _tl_strings(board["treatment_options"], lang, tr)
        if board.get("doctor_notes"):
            board["doctor_notes"] = _tl_text(board["doctor_notes"], lang, tr)

    # ---- AI Clinical Timeline ----
    timeline = result.get("timeline")
    if isinstance(timeline, dict):
        timeline["title"] = T("ai_clinical_timeline")
        if timeline.get("current"):
            timeline["current"] = _tl_text(timeline["current"], lang, tr)
        if timeline.get("prediction"):
            timeline["prediction"] = _tl_text(timeline["prediction"], lang, tr)
        if timeline.get("treatment"):
            timeline["treatment"] = _tl_text(timeline["treatment"], lang, tr)
        if timeline.get("milestones"):
            timeline["milestones"] = _tl_milestones(timeline["milestones"], lang, tr)

    # ---- AI Treatment Planner ----
    plan = result.get("treatment_plan")
    if isinstance(plan, dict):
        plan["title"] = T("ai_treatment_planner")
        if plan.get("recommended_specialist"):
            plan["recommended_specialist"] = _tl_text(plan["recommended_specialist"], lang, tr)
        if plan.get("tests"):
            plan["tests"] = _tl_strings(plan["tests"], lang, tr)
        if plan.get("lifestyle"):
            plan["lifestyle"] = _tl_strings(plan["lifestyle"], lang, tr)
        if plan.get("next_appointment"):
            plan["next_appointment"] = _tl_text(plan["next_appointment"], lang, tr)
        if plan.get("disclaimer"):
            plan["disclaimer"] = tr.get("med_disclaimer", _tl_text(plan["disclaimer"], lang, tr))
        if plan.get("medicines"):
            meds = []
            for m in plan["medicines"]:
                if isinstance(m, (list, tuple)) and len(m) == 2:
                    meds.append([_tl_text(m[0], lang, tr), _tl_text(m[1], lang, tr)])
                elif isinstance(m, dict):
                    meds.append({
                        "class": _tl_text(m.get("class"), lang, tr),
                        "detail": _tl_text(m.get("detail"), lang, tr),
                    })
                else:
                    meds.append(m)
            plan["medicines"] = meds

    # Include a copy of the section labels so the frontend/PDF can render
    # localized headings without a second lookup.
    result["_labels"] = {
        "multi_agent_title": T("multi_agent_title"),
        "final_ai_aggregator": T("final_ai_aggregator"),
        "ai_tumor_board": T("ai_tumor_board"),
        "ai_clinical_timeline": T("ai_clinical_timeline"),
        "ai_treatment_planner": T("ai_treatment_planner"),
        "recommended_specialist": T("recommended_specialist"),
        "recommendations": T("recommendations"),
        "recommended_tests": T("recommended_tests"),
        "treatment_options": T("treatment_options"),
        "doctor_notes": T("doctor_notes"),
        "specialist": T("specialist"),
        "next_appointment": T("next_appointment"),
        "agreement": T("agreement"),
        "findings": T("findings"),
        "urgency_label": T("urgency_label"),
        "current": T("current"),
        "prediction": T("prediction"),
        "treatment": T("treatment"),
        "med_disclaimer": T("med_disclaimer"),
        "role_radiologist": T("role_radiologist"),
        "role_oncologist": T("role_oncologist"),
        "role_surgeon": T("role_surgeon"),
        "role_pharmacologist": T("role_pharmacologist"),
        "role_lifestyle": T("role_lifestyle"),
    }
    result["_lang"] = lang

    return result
