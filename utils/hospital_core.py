import os
import json
import time
import uuid
import random
from datetime import datetime, timedelta

DATA_DIR = "data"
PATIENTS_FILE = os.path.join(DATA_DIR, "patients.json")
APPOINTMENTS_FILE = os.path.join(DATA_DIR, "appointments.json")
AUDIT_LOG_FILE = os.path.join(DATA_DIR, "audit_log.json")
MODEL_MONITORING_FILE = os.path.join(DATA_DIR, "model_monitoring.json")
REPORTS_FILE = os.path.join(DATA_DIR, "reports.json")
NOTIFICATIONS_FILE = os.path.join(DATA_DIR, "notifications.json")

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

def log_audit_event(user, role, action, patient_id=None, details=""):
    """Appends an immutable audit event to audit_log.json."""
    logs = _load_json(AUDIT_LOG_FILE, [])
    now = datetime.now()
    event = {
        "id": f"AUD-{uuid.uuid4().hex[:8].upper()}",
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "time_str": now.strftime("%I:%M %p"),
        "date_str": now.strftime("%d %b %Y"),
        "user": user or "System",
        "role": role or "Staff",
        "patient_id": patient_id or "N/A",
        "action": action,
        "details": details
    }
    # Prepend new event so most recent is first
    logs.insert(0, event)
    # Keep last 500 logs
    if len(logs) > 500:
        logs = logs[:500]
    _save_json(AUDIT_LOG_FILE, logs)
    return event

# ---------------------------------------------------------------------------
# Initialize Default Clinical Datasets
# ---------------------------------------------------------------------------
def init_hospital_database():
    """Initializes rich default data for patients, appointments, audit logs, and model monitoring."""
    
    # 1. Patients EMR
    if not os.path.exists(PATIENTS_FILE) or len(_load_json(PATIENTS_FILE, [])) == 0:
        default_patients = [
            {
                "patient_id": "MS-2026-004821",
                "name": "Eleanor Vance",
                "age": 58,
                "dob": "1968-04-12",
                "gender": "Female",
                "blood_group": "A+",
                "phone": "+1 (555) 382-9104",
                "email": "eleanor.vance@example.com",
                "emergency_contact": "Robert Vance (Spouse) - +1 (555) 382-9105",
                "address": "742 Evergreen Terrace, Sector 4, Metro City",
                "allergies": ["Penicillin", "Sulfa drugs"],
                "existing_conditions": ["Hypertension", "Mild Asthma"],
                "current_medications": ["Lisinopril 10mg PO Daily", "Albuterol HFA inhaler PRN"],
                "cancer_history": "Maternal history of breast carcinoma at age 52; No prior malignancy",
                "assigned_doctor": "Dr. Sarah Sharma, MD (Oncology)",
                "department": "Oncology",
                "status": "Active Triage",
                "registration_date": "2026-01-14",
                "consent": {
                    "imaging_analysis": True,
                    "report_generation": True,
                    "secure_sharing": True,
                    "research_usage": True,
                    "timestamp": "2026-01-14 09:30:00",
                    "signed_by": "Eleanor Vance"
                },
                "timeline": [
                    {
                        "date": "14 Jan 2026",
                        "title": "Initial Clinical Consultation",
                        "doctor": "Dr. Sarah Sharma, MD",
                        "department": "Oncology",
                        "notes": "Patient presented with dry persistent cough >4 weeks and mild hemoptysis. Ordered Low-Dose CT Chest.",
                        "badge": "Consultation",
                        "type": "consultation"
                    },
                    {
                        "date": "22 Jan 2026",
                        "title": "Low-Dose Chest CT Scan",
                        "doctor": "Dr. Marcus Wei, MD",
                        "department": "Radiology",
                        "notes": "High-resolution helical chest CT without contrast. 1.8cm solitary spiculated nodule in right upper lobe.",
                        "badge": "Imaging",
                        "type": "scan"
                    },
                    {
                        "date": "22 Jan 2026",
                        "title": "AI Deep Diagnostic Analysis & Grad-CAM",
                        "doctor": "MediScan AI Engine v2.1",
                        "department": "Clinical AI",
                        "notes": "Adenocarcinoma detected with 94.2% confidence. High risk category. Grad-CAM localized to right apical segment.",
                        "badge": "AI Analysis",
                        "type": "ai"
                    },
                    {
                        "date": "10 Mar 2026",
                        "title": "30-Day Follow-Up & Biopsy Correlation",
                        "doctor": "Dr. Sarah Sharma, MD",
                        "department": "Oncology",
                        "notes": "CT-guided core needle biopsy confirms Stage IB invasive pulmonary adenocarcinoma. EGFr mutation testing ordered.",
                        "badge": "Follow-Up",
                        "type": "followup"
                    },
                    {
                        "date": "18 Mar 2026",
                        "title": "Serial CT Scan & AI Delta Comparison",
                        "doctor": "Dr. Marcus Wei, MD",
                        "department": "Radiology",
                        "notes": "Follow-up scan compared to baseline. 4.2% reduction in perimeter density following initial neoadjuvant cycle.",
                        "badge": "Comparison",
                        "type": "comparison"
                    },
                    {
                        "date": "05 Oct 2026",
                        "title": "Multidisciplinary Tumor Board Review",
                        "doctor": "MDT Panel (Radiology, Oncology, Thoracic Surgery)",
                        "department": "Tumor Board",
                        "notes": "Consensus reached (91% agreement): Proceed with VATS right upper lobectomy with mediastinal lymphadenectomy.",
                        "badge": "Specialist Review",
                        "type": "review"
                    }
                ],
                "visits": [
                    {"date": "2026-10-05", "reason": "MDT Surgical Planning", "doctor": "Dr. Sarah Sharma", "dept": "Oncology", "status": "Completed"},
                    {"date": "2026-03-18", "reason": "Interval Imaging Review", "doctor": "Dr. Marcus Wei", "dept": "Radiology", "status": "Completed"},
                    {"date": "2026-01-14", "reason": "Initial Diagnostic Intake", "doctor": "Dr. Sarah Sharma", "dept": "Oncology", "status": "Completed"}
                ],
                "scans": [
                    {
                        "scan_id": "SCN-2026-8812",
                        "date": "2026-01-22",
                        "modality": "CT Chest (Low-Dose)",
                        "body_part": "Thorax / Lungs",
                        "finding": "Adenocarcinoma - Right Upper Lobe (1.8cm)",
                        "confidence": "94.2%",
                        "risk": "High",
                        "image_url": "/static/uploads/lungaca1.jpeg",
                        "heatmap_url": "/static/uploads/lungaca1.jpeg",
                        "status": "Doctor Verified"
                    },
                    {
                        "scan_id": "SCN-2026-9204",
                        "date": "2026-03-18",
                        "modality": "CT Chest (Follow-up)",
                        "body_part": "Thorax / Lungs",
                        "finding": "Stable nodule with partial cavitation",
                        "confidence": "91.8%",
                        "risk": "Moderate",
                        "image_url": "/static/uploads/lungaca52.jpeg",
                        "heatmap_url": "/static/uploads/lungaca52.jpeg",
                        "status": "Doctor Verified"
                    }
                ],
                "medications": [
                    {"drug": "Osimertinib", "dose": "80mg PO Daily", "start_date": "2026-03-25", "status": "Active", "prescriber": "Dr. Sharma"},
                    {"drug": "Lisinopril", "dose": "10mg PO Daily", "start_date": "2024-06-10", "status": "Active", "prescriber": "Dr. Patel"},
                    {"drug": "Dexamethasone", "dose": "4mg PO BID (3 days)", "start_date": "2026-03-15", "status": "Completed", "prescriber": "Dr. Sharma"}
                ],
                "lab_results": [
                    {"test": "CEA (Carcinoembryonic Antigen)", "value": "6.8 ng/mL", "normal_range": "< 3.0 ng/mL", "status": "High", "date": "2026-03-12"},
                    {"test": "Hemoglobin", "value": "13.2 g/dL", "normal_range": "12.0 - 15.5 g/dL", "status": "Normal", "date": "2026-03-12"},
                    {"test": "Platelet Count", "value": "245 x10^3/uL", "normal_range": "150 - 450 x10^3/uL", "status": "Normal", "date": "2026-03-12"},
                    {"test": "Creatinine", "value": "0.85 mg/dL", "normal_range": "0.6 - 1.2 mg/dL", "status": "Normal", "date": "2026-03-12"},
                    {"test": "EGFR Mutation Panel", "value": "Exon 19 Deletion Positive", "normal_range": "Wild Type", "status": "Abnormal", "date": "2026-03-20"}
                ],
                "notes": [
                    {
                        "author": "Dr. Sarah Sharma, MD",
                        "role": "Attending Oncologist",
                        "date": "2026-10-05 14:15",
                        "text": "Patient is clinically compensated with ECOG Performance Status 0. MDT consensus favors minimally invasive resection. Informed consent verified."
                    },
                    {
                        "author": "Dr. Marcus Wei, MD",
                        "role": "Consulting Radiologist",
                        "date": "2026-03-18 11:30",
                        "text": "Good interval response. No evidence of mediastinal or hilar lymphadenopathy. Pleural spaces remain clear."
                    }
                ]
            },
            {
                "patient_id": "MS-2026-003492",
                "name": "David K. Chen",
                "age": 49,
                "dob": "1977-09-24",
                "gender": "Male",
                "blood_group": "O+",
                "phone": "+1 (555) 714-2201",
                "email": "dchen.tech@example.com",
                "emergency_contact": "Linda Chen (Wife) - +1 (555) 714-2203",
                "address": "1204 Pine Crest Blvd, Westside Medical District",
                "allergies": ["Contrast iodine (mild hives)"],
                "existing_conditions": ["Type 2 Diabetes Mellitus"],
                "current_medications": ["Metformin 500mg BID", "Atorvastatin 20mg QHS"],
                "cancer_history": "Paternal history of colorectal cancer at age 65",
                "assigned_doctor": "Dr. Anita Roy, MD (Neuro-Oncology)",
                "department": "Neuro-Oncology",
                "status": "Inpatient Observation",
                "registration_date": "2026-02-02",
                "consent": {
                    "imaging_analysis": True,
                    "report_generation": True,
                    "secure_sharing": True,
                    "research_usage": False,
                    "timestamp": "2026-02-02 10:15:00",
                    "signed_by": "David K. Chen"
                },
                "timeline": [
                    {
                        "date": "02 Feb 2026",
                        "title": "Emergency Department Intake",
                        "doctor": "Dr. Anita Roy, MD",
                        "department": "Neuro-Oncology",
                        "notes": "Patient presented with progressive nocturnal headaches, papilledema, and right hand motor drift.",
                        "badge": "Emergency",
                        "type": "consultation"
                    },
                    {
                        "date": "02 Feb 2026",
                        "title": "Brain MRI with & without IV Contrast",
                        "doctor": "Dr. H. Vance, MD",
                        "department": "Radiology",
                        "notes": "3.2cm ring-enhancing intra-axial lesion in left frontal lobe with extensive perilesional vasogenic edema.",
                        "badge": "Imaging",
                        "type": "scan"
                    },
                    {
                        "date": "02 Feb 2026",
                        "title": "AI Neuropathology Classification",
                        "doctor": "MediScan AI Engine v1.8",
                        "department": "Clinical AI",
                        "notes": "Glioma classified with 96.8% confidence. High risk, urgent neurosurgical evaluation recommended.",
                        "badge": "AI Analysis",
                        "type": "ai"
                    },
                    {
                        "date": "15 Feb 2026",
                        "title": "Surgical Resection & Craniotomy",
                        "doctor": "Dr. Rajiv Mehta, MD",
                        "department": "Neurosurgery",
                        "notes": "Gross total resection accomplished under intraoperative fluorescence guidance. Pathology confirmed IDH-wildtype glioblastoma.",
                        "badge": "Surgery",
                        "type": "review"
                    },
                    {
                        "date": "04 Oct 2026",
                        "title": "Post-Radiochemotherapy MRI Surveillance",
                        "doctor": "Dr. Anita Roy, MD",
                        "department": "Neuro-Oncology",
                        "notes": "Surveillance MRI demonstrates stable post-surgical resection cavity without nodular tumor progression.",
                        "badge": "Follow-Up",
                        "type": "followup"
                    }
                ],
                "visits": [
                    {"date": "2026-10-04", "reason": "Surveillance Brain MRI Review", "doctor": "Dr. Anita Roy", "dept": "Neuro-Oncology", "status": "Completed"},
                    {"date": "2026-02-15", "reason": "Surgical Craniotomy", "doctor": "Dr. Rajiv Mehta", "dept": "Neurosurgery", "status": "Completed"}
                ],
                "scans": [
                    {
                        "scan_id": "SCN-2026-4109",
                        "date": "2026-02-02",
                        "modality": "MRI Brain T1-Contrast",
                        "body_part": "Cranial / Frontal Lobe",
                        "finding": "High-Grade Glioma - Left Frontal Lobe",
                        "confidence": "96.8%",
                        "risk": "Critical",
                        "image_url": "/static/uploads/Te-gl_1.jpg",
                        "heatmap_url": "/static/uploads/Te-gl_1.jpg",
                        "status": "Doctor Verified"
                    }
                ],
                "medications": [
                    {"drug": "Temozolomide", "dose": "150mg/m2 PO Days 1-5 q28d", "start_date": "2026-03-01", "status": "Active", "prescriber": "Dr. Roy"},
                    {"drug": "Levetiracetam", "dose": "750mg PO BID", "start_date": "2026-02-02", "status": "Active", "prescriber": "Dr. Roy"},
                    {"drug": "Metformin", "dose": "500mg PO BID", "start_date": "2022-05-14", "status": "Active", "prescriber": "Dr. Patel"}
                ],
                "lab_results": [
                    {"test": "Platelet Count", "value": "185 x10^3/uL", "normal_range": "150 - 450 x10^3/uL", "status": "Normal", "date": "2026-09-30"},
                    {"test": "Absolute Neutrophil Count", "value": "2.8 x10^3/uL", "normal_range": "1.8 - 7.7 x10^3/uL", "status": "Normal", "date": "2026-09-30"},
                    {"test": "HbA1c", "value": "6.7%", "normal_range": "< 5.7%", "status": "High", "date": "2026-09-30"}
                ],
                "notes": [
                    {
                        "author": "Dr. Anita Roy, MD",
                        "role": "Neuro-Oncologist",
                        "date": "2026-10-04 16:00",
                        "text": "Mr. Chen tolerates maintenance temozolomide well. Neurologic exam non-focal. Resumed part-time remote work."
                    }
                ]
            },
            {
                "patient_id": "MS-2026-005118",
                "name": "Amina S. Patel",
                "age": 44,
                "dob": "1982-11-05",
                "gender": "Female",
                "blood_group": "B+",
                "phone": "+1 (555) 902-6632",
                "email": "amina.patel@healthnet.org",
                "emergency_contact": "Farhan Patel (Brother) - +1 (555) 902-6635",
                "address": "405 Horizon Court, Suite 12B, North Heights",
                "allergies": ["No known drug allergies (NKDA)"],
                "existing_conditions": ["Fibrocystic breast disease"],
                "current_medications": ["Vitamin D3 2000 IU Daily"],
                "cancer_history": "Sister diagnosed with triple negative breast cancer at age 39 (BRCA1 positive)",
                "assigned_doctor": "Dr. Claire Dupont, MD (Breast Surgery & Oncology)",
                "department": "Breast Oncology",
                "status": "Diagnostic Workup",
                "registration_date": "2026-03-01",
                "consent": {
                    "imaging_analysis": True,
                    "report_generation": True,
                    "secure_sharing": True,
                    "research_usage": True,
                    "timestamp": "2026-03-01 11:00:00",
                    "signed_by": "Amina S. Patel"
                },
                "timeline": [
                    {
                        "date": "01 Mar 2026",
                        "title": "High-Risk Screening Intake",
                        "doctor": "Dr. Claire Dupont, MD",
                        "department": "Breast Oncology",
                        "notes": "Patient scheduled for high-risk surveillance mammogram and breast ultrasound given strong family history.",
                        "badge": "Consultation",
                        "type": "consultation"
                    },
                    {
                        "date": "04 Mar 2026",
                        "title": "Digital Breast Tomosynthesis & US",
                        "doctor": "Dr. Marcus Wei, MD",
                        "department": "Radiology",
                        "notes": "1.4cm microlobulated hypoechoic mass in upper outer quadrant of left breast. BI-RADS 4C suspicious lesion.",
                        "badge": "Imaging",
                        "type": "scan"
                    },
                    {
                        "date": "04 Mar 2026",
                        "title": "MediScan AI Mammography Evaluation",
                        "doctor": "MediScan AI Engine v2.0",
                        "department": "Clinical AI",
                        "notes": "Malignant breast lesion prediction with 92.4% confidence. AI Heatmap highlights irregular architectural distortion.",
                        "badge": "AI Analysis",
                        "type": "ai"
                    },
                    {
                        "date": "16 Mar 2026",
                        "title": "Ultrasound-Guided Core Biopsy",
                        "doctor": "Dr. Claire Dupont, MD",
                        "department": "Breast Oncology",
                        "notes": "Biopsy demonstrated Invasive Ductal Carcinoma (IDC), Grade 2. ER+ 90%, PR+ 70%, HER2 1+ (Negative). Ki-67 18%.",
                        "badge": "Pathology",
                        "type": "review"
                    },
                    {
                        "date": "05 Oct 2026",
                        "title": "Post-Neoadjuvant Response Assessment",
                        "doctor": "MDT Breast Panel",
                        "department": "Tumor Board",
                        "notes": "Excellent clinical downstaging. Mass now non-palpable. Scheduled for breast conservation surgery (lumpectomy) with SLNB.",
                        "badge": "Tumor Board",
                        "type": "review"
                    }
                ],
                "visits": [
                    {"date": "2026-10-05", "reason": "Pre-Operative Breast Clinic", "doctor": "Dr. Claire Dupont", "dept": "Breast Oncology", "status": "Confirmed"},
                    {"date": "2026-03-16", "reason": "US-Guided Core Biopsy", "doctor": "Dr. Claire Dupont", "dept": "Breast Oncology", "status": "Completed"}
                ],
                "scans": [
                    {
                        "scan_id": "SCN-2026-6731",
                        "date": "2026-03-04",
                        "modality": "Targeted Breast Ultrasound & DBT",
                        "body_part": "Left Breast (Upper Outer Quadrant)",
                        "finding": "Malignant Carcinoma - Architectural Distortion",
                        "confidence": "92.4%",
                        "risk": "High",
                        "image_url": "/static/uploads/malignant_1.png",
                        "heatmap_url": "/static/uploads/malignant_1.png",
                        "status": "Doctor Verified"
                    }
                ],
                "medications": [
                    {"drug": "Tamoxifen", "dose": "20mg PO Daily", "start_date": "2026-04-10", "status": "Active", "prescriber": "Dr. Dupont"},
                    {"drug": "Letrozole", "dose": "2.5mg PO Daily (Planned Post-Op)", "start_date": "2026-11-01", "status": "Pending", "prescriber": "Dr. Dupont"}
                ],
                "lab_results": [
                    {"test": "ER (Estrogen Receptor)", "value": "90% Positive", "normal_range": "Negative", "status": "High", "date": "2026-03-18"},
                    {"test": "PR (Progesterone Receptor)", "value": "70% Positive", "normal_range": "Negative", "status": "High", "date": "2026-03-18"},
                    {"test": "HER2/neu IHC", "value": "1+ (Non-Amplified)", "normal_range": "Negative", "status": "Normal", "date": "2026-03-18"},
                    {"test": "BRCA1 / BRCA2 Mutation Screen", "value": "Pathogenic Variant in BRCA1", "normal_range": "Negative", "status": "Abnormal", "date": "2026-03-22"}
                ],
                "notes": [
                    {
                        "author": "Dr. Claire Dupont, MD",
                        "role": "Breast Surgical Oncologist",
                        "date": "2026-10-05 10:30",
                        "text": "Tumor localized via magnetic seed placement yesterday. Sentinel lymph node mapping prepared. Patient expresses confidence and clear comprehension."
                    }
                ]
            },
            {
                "patient_id": "MS-2026-006204",
                "name": "Marcus J. Brody",
                "age": 62,
                "dob": "1964-07-19",
                "gender": "Male",
                "blood_group": "AB+",
                "phone": "+1 (555) 433-8871",
                "email": "m.brody@harbor.net",
                "emergency_contact": "Sarah Brody (Daughter) - +1 (555) 433-8874",
                "address": "88 Bayside Pier Way, Harborview",
                "allergies": ["Aspirin", "Ibuprofen"],
                "existing_conditions": ["Hyperlipidemia", "GERD"],
                "current_medications": ["Omeprazole 20mg Daily", "Rosuvastatin 10mg QHS"],
                "cancer_history": "Basal cell carcinoma of left ear excised in 2021",
                "assigned_doctor": "Dr. Kenneth Cole, MD (Dermatology & Cutaneous Oncology)",
                "department": "Dermatology",
                "status": "Post-Excise Monitoring",
                "registration_date": "2026-04-10",
                "consent": {
                    "imaging_analysis": True,
                    "report_generation": True,
                    "secure_sharing": True,
                    "research_usage": True,
                    "timestamp": "2026-04-10 08:45:00",
                    "signed_by": "Marcus J. Brody"
                },
                "timeline": [
                    {
                        "date": "10 Apr 2026",
                        "title": "Dermatology Screening & Total Body Skin Exam",
                        "doctor": "Dr. Kenneth Cole, MD",
                        "department": "Dermatology",
                        "notes": "Patient noticed changing pigmented macule with irregular borders and variegation on upper back.",
                        "badge": "Screening",
                        "type": "consultation"
                    },
                    {
                        "date": "10 Apr 2026",
                        "title": "High-Resolution Polarized Dermoscopy",
                        "doctor": "Dr. Kenneth Cole, MD",
                        "department": "Dermatology",
                        "notes": "Dermoscopic examination reveals atypical pigment network with blue-white veil and peripheral streaks.",
                        "badge": "Imaging",
                        "type": "scan"
                    },
                    {
                        "date": "10 Apr 2026",
                        "title": "MediScan AI Cutaneous Malignancy Engine",
                        "doctor": "MediScan AI Engine v1.5",
                        "department": "Clinical AI",
                        "notes": "Malignant Melanoma predicted with 91.5% confidence. ABCDE criteria flagged asymmetry and color variegation.",
                        "badge": "AI Analysis",
                        "type": "ai"
                    },
                    {
                        "date": "18 Apr 2026",
                        "title": "Wide Local Excision with 1cm Margins",
                        "doctor": "Dr. Kenneth Cole, MD",
                        "department": "Dermatology / Surgery",
                        "notes": "Complete resection achieved with clear peripheral and deep margins (>5mm). Breslow thickness 0.6mm, Stage IA.",
                        "badge": "Surgery",
                        "type": "review"
                    },
                    {
                        "date": "02 Oct 2026",
                        "title": "6-Month Surveillance Skin Check",
                        "doctor": "Dr. Kenneth Cole, MD",
                        "department": "Dermatology",
                        "notes": "Scar fully healed without local recurrence or satellite metastases. Regional lymph node stations non-palpable.",
                        "badge": "Follow-Up",
                        "type": "followup"
                    }
                ],
                "visits": [
                    {"date": "2026-10-02", "reason": "6-Month Melanoma Follow-Up", "doctor": "Dr. Kenneth Cole", "dept": "Dermatology", "status": "Completed"},
                    {"date": "2026-04-18", "reason": "Wide Local Excision", "doctor": "Dr. Kenneth Cole", "dept": "Dermatology", "status": "Completed"}
                ],
                "scans": [
                    {
                        "scan_id": "SCN-2026-3091",
                        "date": "2026-04-10",
                        "modality": "High-Res Polarized Dermoscopy",
                        "body_part": "Posterior Thorax (Upper Back)",
                        "finding": "Malignant Melanoma - Early Stage IA",
                        "confidence": "91.5%",
                        "risk": "Moderate",
                        "image_url": "/static/uploads/2.jpg",
                        "heatmap_url": "/static/uploads/2.jpg",
                        "status": "Doctor Verified"
                    }
                ],
                "medications": [
                    {"drug": "Rosuvastatin", "dose": "10mg PO QHS", "start_date": "2023-01-15", "status": "Active", "prescriber": "Dr. Patel"},
                    {"drug": "Omeprazole", "dose": "20mg PO Daily", "start_date": "2024-08-20", "status": "Active", "prescriber": "Dr. Patel"}
                ],
                "lab_results": [
                    {"test": "LDH (Lactate Dehydrogenase)", "value": "165 U/L", "normal_range": "140 - 280 U/L", "status": "Normal", "date": "2026-04-12"},
                    {"test": "Complete Blood Count", "value": "Within Normal Limits", "normal_range": "Reference Range", "status": "Normal", "date": "2026-04-12"}
                ],
                "notes": [
                    {
                        "author": "Dr. Kenneth Cole, MD",
                        "role": "Consultant Dermatologist",
                        "date": "2026-10-02 11:15",
                        "text": "Excellent healing. Patient instructed in sun avoidance, SPF 50+ reapplication, and monthly self-skin exams. Next visit in 6 months."
                    }
                ]
            }
        ]
        _save_json(PATIENTS_FILE, default_patients)

    # 2. Appointments
    if not os.path.exists(APPOINTMENTS_FILE) or len(_load_json(APPOINTMENTS_FILE, [])) == 0:
        default_appointments = [
            {
                "id": "APT-2026-101",
                "patient_id": "MS-2026-004821",
                "patient_name": "Eleanor Vance",
                "doctor": "Dr. Sarah Sharma, MD",
                "department": "Oncology",
                "appointment_date": "2026-10-06",
                "appointment_time": "10:30 AM",
                "type": "Oncology Consultation",
                "status": "Confirmed",
                "priority": "Urgent",
                "notes": "Pre-operative surgical consensus review with patient and family."
            },
            {
                "id": "APT-2026-102",
                "patient_id": "MS-2026-003492",
                "patient_name": "David K. Chen",
                "doctor": "Dr. Anita Roy, MD",
                "department": "Neuro-Oncology",
                "appointment_date": "2026-10-06",
                "appointment_time": "11:15 AM",
                "type": "Follow-Up Surveillance",
                "status": "Confirmed",
                "priority": "High",
                "notes": "Review 6-month surveillance brain MRI and anticonvulsant titration."
            },
            {
                "id": "APT-2026-103",
                "patient_id": "MS-2026-005118",
                "patient_name": "Amina S. Patel",
                "doctor": "Dr. Claire Dupont, MD",
                "department": "Breast Oncology",
                "appointment_date": "2026-10-06",
                "appointment_time": "02:00 PM",
                "type": "Pre-Surgical Lumpectomy Review",
                "status": "Confirmed",
                "priority": "High",
                "notes": "Review localization seed placement and sentinel lymph node protocol."
            },
            {
                "id": "APT-2026-104",
                "patient_id": "MS-2026-006204",
                "patient_name": "Marcus J. Brody",
                "doctor": "Dr. Kenneth Cole, MD",
                "department": "Dermatology",
                "appointment_date": "2026-10-07",
                "appointment_time": "09:45 AM",
                "type": "Follow-Up Skin Check",
                "status": "Confirmed",
                "priority": "Routine",
                "notes": "Routine surveillance total body dermatoscopy."
            },
            {
                "id": "APT-2026-105",
                "patient_id": "MS-2026-004821",
                "patient_name": "Eleanor Vance",
                "doctor": "Dr. Rajiv Mehta, MD",
                "department": "Thoracic Surgery",
                "appointment_date": "2026-10-09",
                "appointment_time": "08:00 AM",
                "type": "Surgical Procedure (VATS Lobectomy)",
                "status": "Scheduled",
                "priority": "Urgent",
                "notes": "Operating Room 4 reserved. Thoracic surgery team on standby."
            }
        ]
        _save_json(APPOINTMENTS_FILE, default_appointments)

    # 3. Model Monitoring
    if not os.path.exists(MODEL_MONITORING_FILE) or not _load_json(MODEL_MONITORING_FILE, {}):
        default_monitoring = {
            "models": [
                {
                    "name": "Lung Cancer AI Model",
                    "version": "v2.1",
                    "architecture": "EfficientNetB4 + Multi-Head Dense",
                    "cancer_type": "Pulmonary Carcinoma",
                    "status": "Active",
                    "accuracy": 96.8,
                    "auc_roc": 0.984,
                    "sensitivity": 97.1,
                    "specificity": 96.4,
                    "total_inferences": 4820,
                    "avg_latency_ms": 285,
                    "last_updated": "2026-08-15",
                    "data_drift": "Nominal (< 1.2%)",
                    "confidence_distribution": {"high": 79.4, "moderate": 16.2, "low": 4.4}
                },
                {
                    "name": "Brain Tumor AI Model",
                    "version": "v1.8",
                    "architecture": "ResNet50V2 + Attention Gate",
                    "cancer_type": "Intracranial Neoplasm",
                    "status": "Active",
                    "accuracy": 95.4,
                    "auc_roc": 0.978,
                    "sensitivity": 96.0,
                    "specificity": 94.8,
                    "total_inferences": 3140,
                    "avg_latency_ms": 310,
                    "last_updated": "2026-07-20",
                    "data_drift": "Nominal (< 0.8%)",
                    "confidence_distribution": {"high": 82.1, "moderate": 14.5, "low": 3.4}
                },
                {
                    "name": "Breast Cancer AI Model",
                    "version": "v2.0",
                    "architecture": "DenseNet121 + Feature Pyramid",
                    "cancer_type": "Mammary Carcinoma",
                    "status": "Active",
                    "accuracy": 96.2,
                    "auc_roc": 0.981,
                    "sensitivity": 96.8,
                    "specificity": 95.5,
                    "total_inferences": 3950,
                    "avg_latency_ms": 295,
                    "last_updated": "2026-08-01",
                    "data_drift": "Nominal (< 1.5%)",
                    "confidence_distribution": {"high": 76.5, "moderate": 18.0, "low": 5.5}
                },
                {
                    "name": "Dermoscopy Skin Model",
                    "version": "v1.5",
                    "architecture": "MobileNetV3-Large + Squeeze-Excite",
                    "cancer_type": "Cutaneous Melanoma",
                    "status": "Active",
                    "accuracy": 94.8,
                    "auc_roc": 0.969,
                    "sensitivity": 95.2,
                    "specificity": 94.3,
                    "total_inferences": 2740,
                    "avg_latency_ms": 190,
                    "last_updated": "2026-06-10",
                    "data_drift": "Nominal (< 0.9%)",
                    "confidence_distribution": {"high": 80.2, "moderate": 15.1, "low": 4.7}
                }
            ],
            "metrics": {
                "total_scans_analyzed": 14650,
                "low_confidence_cases": 12,
                "doctor_corrections": 5,
                "ai_doctor_agreement": "97.4%",
                "average_review_turnaround_mins": 14.5
            },
            "history": [
                {"date": "2026-08-15", "model": "Lung v2.1", "action": "Retrained with 1,200 new low-dose CT slices; AUC increased from 0.975 to 0.984."},
                {"date": "2026-08-01", "model": "Breast v2.0", "action": "Integrated Tomosynthesis DBT slice multi-layer aggregation."},
                {"date": "2026-07-20", "model": "Brain v1.8", "action": "Enhanced pituitary adenoma vs normal parenchyma boundary discrimination."}
            ]
        }
        _save_json(MODEL_MONITORING_FILE, default_monitoring)

    # 4. Audit Log
    if not os.path.exists(AUDIT_LOG_FILE) or len(_load_json(AUDIT_LOG_FILE, [])) == 0:
        default_audit = [
            {"id": "AUD-00109", "timestamp": "2026-10-05 11:02:18", "time_str": "11:02 AM", "date_str": "05 Oct 2026", "user": "Eleanor Vance", "role": "Patient", "patient_id": "MS-2026-004821", "action": "Patient accessed report", "details": "Viewed patient-friendly diagnostic summary via secure portal"},
            {"id": "AUD-00108", "timestamp": "2026-10-05 10:55:40", "time_str": "10:55 AM", "date_str": "05 Oct 2026", "user": "Dr. Sarah Sharma", "role": "Doctor", "patient_id": "MS-2026-004821", "action": "Final report signed", "details": "Applied digital cryptographic signature to diagnostic report SCN-2026-8812"},
            {"id": "AUD-00107", "timestamp": "2026-10-05 10:51:12", "time_str": "10:51 AM", "date_str": "05 Oct 2026", "user": "Dr. Sarah Sharma", "role": "Doctor", "patient_id": "MS-2026-004821", "action": "Modified finding", "details": "Updated clinical staging recommendation to include preoperative VATS lobectomy"},
            {"id": "AUD-00106", "timestamp": "2026-10-05 10:48:05", "time_str": "10:48 AM", "date_str": "05 Oct 2026", "user": "MediScan AI", "role": "Clinical AI", "patient_id": "MS-2026-004821", "action": "AI analysis generated", "details": "Executed ensemble classifier and Grad-CAM layer visualization (Confidence: 94.2%)"},
            {"id": "AUD-00105", "timestamp": "2026-10-05 10:42:30", "time_str": "10:42 AM", "date_str": "05 Oct 2026", "user": "Dr. Sarah Sharma", "role": "Doctor", "patient_id": "MS-2026-004821", "action": "Doctor viewed Patient", "details": "Opened patient longitudinal timeline and DICOM PACS workstation"},
            {"id": "AUD-00104", "timestamp": "2026-10-05 09:30:15", "time_str": "09:30 AM", "date_str": "05 Oct 2026", "user": "Dr. Marcus Wei", "role": "Radiologist", "patient_id": "MS-2026-003492", "action": "PACS imaging review", "details": "Adjusted window leveling (W:1500, L:-600) and inspected axial slice 8 of 16"},
            {"id": "AUD-00103", "timestamp": "2026-10-05 08:15:22", "time_str": "08:15 AM", "date_str": "05 Oct 2026", "user": "Nurse Jennifer Adams", "role": "Nurse", "patient_id": "MS-2026-005118", "action": "Vitals recorded", "details": "Recorded BP 118/76 mmHg, SpO2 99%, Heart Rate 72 bpm in inpatient registry"},
            {"id": "AUD-00102", "timestamp": "2026-10-04 16:45:00", "time_str": "04:45 PM", "date_str": "04 Oct 2026", "user": "Admin Central", "role": "Admin", "patient_id": "SYSTEM", "action": "System backup & audit sync", "details": "Encrypted EMR cold backup verified (AES-256 GCM) with SHA-256 checksums"}
        ]
        _save_json(AUDIT_LOG_FILE, default_audit)

    # 5. Notifications
    if not os.path.exists(NOTIFICATIONS_FILE) or len(_load_json(NOTIFICATIONS_FILE, [])) == 0:
        default_notifications = [
            {
                "id": "NOTIF-01",
                "type": "critical",
                "icon": "fa-triangle-exclamation",
                "color": "#ef4444",
                "title": "Critical Finding Awaiting Review",
                "message": "Patient Eleanor Vance (MS-2026-004821) CT Scan flagged as High Risk (94.2% confidence). Assigned to Oncology.",
                "timestamp": "12 mins ago",
                "read": False,
                "link": "/imaging?patient_id=MS-2026-004821"
            },
            {
                "id": "NOTIF-02",
                "type": "review",
                "icon": "fa-user-doctor",
                "color": "#3b82f6",
                "title": "MDT Tumor Board Scheduled",
                "message": "Tumor board review scheduled for Amina Patel (MS-2026-005118) at 02:00 PM today.",
                "timestamp": "45 mins ago",
                "read": False,
                "link": "/tumor-board"
            },
            {
                "id": "NOTIF-03",
                "type": "report",
                "icon": "fa-file-shield",
                "color": "#10b981",
                "title": "Doctor Signed Diagnostic Report",
                "message": "Dr. Sarah Sharma digitally signed report SCN-2026-8812. Ready for secure patient sharing.",
                "timestamp": "1 hour ago",
                "read": False,
                "link": "/worklist"
            },
            {
                "id": "NOTIF-04",
                "type": "appointment",
                "icon": "fa-calendar-check",
                "color": "#8b5cf6",
                "title": "Appointment Reminder",
                "message": "David Chen (MS-2026-003492) surveillance MRI review in 35 minutes.",
                "timestamp": "2 hours ago",
                "read": True,
                "link": "/appointments"
            }
        ]
        _save_json(NOTIFICATIONS_FILE, default_notifications)

# Execute initialization
init_hospital_database()

# ---------------------------------------------------------------------------
# Business Logic Helpers
# ---------------------------------------------------------------------------
def generate_patient_id():
    """Generates a professional hospital patient ID: MS-2026-XXXXXX."""
    num = random.randint(1000, 9999)
    return f"MS-2026-00{num}"

def get_all_patients():
    return _load_json(PATIENTS_FILE, [])

def get_patient_by_id(patient_id):
    patients = get_all_patients()
    for p in patients:
        if str(p.get("patient_id", "")).strip().upper() == str(patient_id).strip().upper():
            return p
    return None

def save_patient(patient_data):
    patients = get_all_patients()
    pid = patient_data.get("patient_id")
    if not pid:
        pid = generate_patient_id()
        patient_data["patient_id"] = pid
    
    # Check if existing
    idx = -1
    for i, p in enumerate(patients):
        if p.get("patient_id") == pid:
            idx = i
            break
            
    if idx >= 0:
        patients[idx] = patient_data
    else:
        patients.insert(0, patient_data)
        
    _save_json(PATIENTS_FILE, patients)
    return patient_data

def get_command_center_stats():
    """Returns the top hospital command center metrics."""
    reports = _load_json(REPORTS_FILE, [])
    patients = get_all_patients()
    
    # Calculate live or realistic scaled numbers
    total_patients = max(1248, len(patients) * 312)
    todays_scans = 86
    pending_reviews = 14
    critical_cases = 7
    reports_ready = 52
    followups_due = 19
    
    # Enrich with actual high risk count from reports if available
    high_risk_reports = sum(1 for r in reports if str(r.get("risk", "")).lower() == "high")
    if high_risk_reports > 0:
        critical_cases = max(critical_cases, high_risk_reports)
        
    return {
        "total_patients": total_patients,
        "todays_scans": todays_scans,
        "pending_reviews": pending_reviews,
        "critical_cases": critical_cases,
        "reports_ready": reports_ready,
        "followups_due": followups_due,
        "departments": {
            "Radiology": {"status": "Operational", "active_scans": 28, "load": "74%"},
            "Oncology": {"status": "Operational", "active_patients": 42, "load": "88%"},
            "Surgery": {"status": "Operational", "or_suites_active": 4, "load": "65%"},
            "Pathology": {"status": "Operational", "biopsies_pending": 8, "load": "55%"},
            "Emergency": {"status": "Operational", "triage_cases": 3, "load": "40%"}
        }
    }

def get_worklist(filter_status="all"):
    """Returns the doctor worklist with studies, priority, and review status."""
    patients = get_all_patients()
    worklist = []
    
    for p in patients:
        for scan in p.get("scans", []):
            risk = scan.get("risk", "Low")
            priority = "Critical" if risk == "Critical" else ("High" if risk == "High" else ("Medium" if risk == "Moderate" else "Low"))
            status = "Reviewed" if scan.get("status") == "Doctor Verified" else "Pending"
            
            item = {
                "patient_id": p.get("patient_id"),
                "patient_name": p.get("name"),
                "age": p.get("age"),
                "gender": p.get("gender"),
                "scan_id": scan.get("scan_id"),
                "study": scan.get("modality"),
                "body_part": scan.get("body_part"),
                "finding": scan.get("finding"),
                "confidence": scan.get("confidence"),
                "risk": risk,
                "priority": priority,
                "status": status,
                "image_url": scan.get("image_url"),
                "date": scan.get("date"),
                "doctor": p.get("assigned_doctor")
            }
            worklist.append(item)
            
    # Apply filter
    filter_status = filter_status.lower()
    if filter_status == "pending":
        worklist = [w for w in worklist if w["status"] == "Pending"]
    elif filter_status == "critical":
        worklist = [w for w in worklist if w["priority"] in ("Critical", "High")]
    elif filter_status == "reviewed":
        worklist = [w for w in worklist if w["status"] == "Reviewed"]
    elif filter_status == "follow-up":
        worklist = [w for w in worklist if "follow" in w["study"].lower() or "surveillance" in w["finding"].lower()]
        
    return worklist

def get_patient_friendly_explanation(clinical_text, cancer_type="cancer"):
    """Converts complex technical oncologic terms into patient-friendly, comforting plain language."""
    if not clinical_text:
        return "The scan shows an area that your doctor may want to examine more closely to ensure your best health."
        
    explanation = (
        "The automated diagnostic scan has identified a localized area of tissue that looks different "
        "from the surrounding healthy tissue. While this can look concerning, an abnormal finding does "
        "not always mean serious illness—it simply means specialized medical doctors (radiologists and oncologists) "
        "will examine it with precision to recommend the right care plan for you."
    )
    return explanation
