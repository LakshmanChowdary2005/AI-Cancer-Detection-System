# 🩺 MediScan AI — Hospital Clinical Cancer Detection & Diagnostic Triage System

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Framework-Flask_3.0-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![TensorFlow 2.18](https://img.shields.io/badge/Deep_Learning-TensorFlow_2.18-FF6F00?logo=tensorflow&logoColor=white)](https://tensorflow.org)
[![Explainable AI](https://img.shields.io/badge/XAI-Grad--CAM-4CAF50)](https://arxiv.org/abs/1610.02391)
[![Languages](https://img.shields.io/badge/i18n-11_Languages-0ea5e9)](https://github.com/LakshmanChowdary2005/AI-Cancer-Detection-System)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An enterprise-grade hospital decision-support platform designed for real-time cancer detection, radiological triage, and multi-disciplinary care management. MediScan AI evaluates imaging across four major cancer modalities—**Brain MRI**, **Breast Ultrasound/Mammography**, **Chest CT/Lung X-Ray**, and **Cutaneous Dermoscopy**—in under 2 seconds, providing Grad-CAM visual heatmaps, clinical severity scoring, stage-specific guidance, and automated multi-agent AI tumor board consensus.

---

## 🌟 Key Features

### 1. Multi-Organ Deep Ensemble Classification
- **Brain Glioma & Intracranial Tumors:** Evaluates axial MRI slices for glioma, meningioma, and pituitary tumors.
- **Breast Carcinoma:** Analyzes ultrasound and mammographic density to distinguish benign lesions from invasive carcinoma.
- **Pulmonary Neoplasms:** Evaluates thoracic CT and chest X-rays to detect adenocarcinoma, squamous cell, and large cell carcinoma.
- **Cutaneous Malignancies:** Analyzes polarized dermoscopy images to identify malignant melanoma versus benign nevi and basal cell carcinoma.

### 2. Explainable AI (Grad-CAM Visual Verification)
- Computes Gradient-weighted Class Activation Mapping (Grad-CAM) to highlight the exact visual features driving neural predictions.
- Offers interactive side-by-side comparison between raw scans and colorized activation heatmaps.

### 3. Multi-Agent AI Tumor Board Consensus
Simulates a multi-disciplinary hospital tumor board by generating synchronized clinical perspectives:
- **Diagnostic Radiologist:** Margin sharpness, radiological density, and slice anatomy.
- **Medical Oncologist:** Staging implications, systemic therapy regimens, and surveillance cadence.
- **Surgical Oncologist:** Resectability assessment, operative margins, and biopsy recommendations.

### 4. Stage-Tailored Supportive Remedies & Nutrition
- Estimates clinical staging from **Stage 0 (Benign / In-Situ)** to **Stage IV (Systemic Metastatic)**.
- Automatically generates stage-appropriate supportive remedies, daily health habits, clinical nutrition, and precautions to avoid.

### 5. Integrated Cancer Care Pathways
Direct clinical links and tailored workflows for 5 oncology tracks:
- **Preventive Care:** Lifestyle guidance, risk reduction, and screening vigilance.
- **Treatment Monitoring:** Therapy milestones and tumor response tracking.
- **Clinical Workflows:** Multi-disciplinary case review and triage prioritization.
- **Integrative Wellbeing:** Pain management, mental wellness, and holistic recovery.
- **Drug Interactions:** Oncology medication reconciliation and safety alerts.

### 6. Dual-Gateway Role-Based Authentication (RBAC)
- **Physician & Clinical Staff Gateway (`/doctor/login`):**
  - Dedicated access for **Doctor**, **Radiologist**, **Oncologist**, **Surgeon**, **Nurse**, and **Admin**.
  - Access to Hospital Command Center, PACS Workstation, and Digital Diagnostic Sign-Off.
  - *Demo credentials:* `doctor@mediscan.ai` / `password123` (or quick 1-click clinical pass).
- **Personal Patient Health Portal (`/patient/login`):**
  - Compassionate, plain-English medical summaries, longitudinal health timeline, and appointment manager.
  - *Demo credentials:* Patient ID `MS-2026-004821` / password `password123` (Eleanor Vance).

### 7. Whole-Webpage Lossless Multi-Language Engine
- Client-side DOM TextNode TreeWalker translating every navigation item, form input, clinical finding, care pathway, and stage remedy across **11 languages**:
  - 🌐 English (`en`)
  - 🇮🇳 Hindi (`hi`)
  - 🇮🇳 Telugu (`te`)
  - 🇮🇳 Tamil (`ta`)
  - 🇮🇳 Kannada (`kn`)
  - 🇮🇳 Malayalam (`ml`)
  - 🇮🇳 Bengali (`bn`)
  - 🇪🇸 Spanish (`es`)
  - 🇫🇷 French (`fr`)
  - 🇩🇪 German (`de`)
  - 🇸🇦 Arabic (`ar` with RTL layout)

---

## 🏗️ System Architecture

```
AI-Cancer-Detection-System/
├── app.py                     # Main Flask Application & API Routes
├── utils/
│   ├── hospital_core.py       # EMR Patient Database, Audit Logs & Telemetry
│   ├── hospital_routes.py     # Hospital Command Center & Clinical Blueprints
│   ├── health_suite.py        # Care Pathways (Preventive, Monitoring, Workflows)
│   ├── health_guidance.py     # Stage-Specific Supportive Remedies & Nutrition
│   ├── multi_agent.py         # Multi-Agent Tumor Board LLM Simulation
│   ├── translator.py          # Multi-Language Translation Service & Caching
│   ├── pdf_generator.py       # Clinical Diagnostic PDF Report Generator
│   ├── email_service.py       # Automated Visit Reminders & Patient Alerts
│   └── google_drive_service.py# Cloud Storage & Diagnostic Backup Service
├── templates/
│   ├── index.html             # Diagnostic Intake & Real-time Analysis Console
│   ├── hospital_header.html   # Unified Navigation Header with RBAC & i18n
│   ├── hospital_dashboard.html# Hospital Command Center & Telemetry
│   ├── patients.html          # Longitudinal Patient EMR Registry
│   ├── imaging.html           # Multi-Slice PACS DICOM Workstation
│   ├── tumor_board.html       # MDT Tumor Board Collaboration Room
│   ├── worklist.html          # Clinical Review Worklist & Triage
│   ├── appointments.html      # Inpatient / Outpatient Appointment Manager
│   ├── patient_portal.html    # Patient-Friendly Health Portal
│   ├── patient_login.html     # Dedicated Patient Login Gateway
│   ├── doctor_login.html      # Dedicated Physician & Staff Gateway
│   ├── analytics.html         # AI Model Monitoring & Data Drift Telemetry
│   └── security.html          # HIPAA Immutable Audit Trail & Logs
├── static/
│   ├── css/                   # Glassmorphic Clinical Design System
│   ├── js/
│   │   ├── hospital_translate.js # Whole-Webpage 11-Language Translation Engine
│   │   └── hospital_system.js    # Interactive PACS, Timeline & Live Feeds
│   └── uploads/               # Sample Diagnostic Scans & Radiology Presets
├── requirements.txt           # Python Dependencies
├── Procfile                   # Cloud Deployment Configuration
└── README.md                  # Project Documentation
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+ (Recommended: Python 3.12)
- Virtual Environment tool (`venv`)
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/LakshmanChowdary2005/AI-Cancer-Detection-System.git
   cd AI-Cancer-Detection-System
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows PowerShell:
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS:
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the Clinical Server:**
   ```bash
   python app.py
   ```

5. **Access MediScan AI:**
   - **Diagnostic Workstation:** `http://localhost:5000/`
   - **Doctor & Staff Gateway:** `http://localhost:5000/doctor/login`
   - **Patient Health Portal:** `http://localhost:5000/patient/login`
   - **Hospital Command Center:** `http://localhost:5000/dashboard`

---

## 🔐 Default Access Passports (Demo Mode)

| Role | Login Gateway | Credentials | Access Scope |
| :--- | :--- | :--- | :--- |
| **Doctor / Physician** | `/doctor/login` | `doctor@mediscan.ai` / `password123` | Full clinical triage, PACS, prescriptions, and digital certification |
| **Radiologist** | `/doctor/login` | Click **Radiologist** Pass | PACS slice windowing, biopsy planning, DICOM viewing |
| **Oncologist** | `/doctor/login` | Click **Oncologist** Pass | Tumor staging, systemic therapy, tumor board consensus |
| **Surgeon** | `/doctor/login` | Click **Surgeon** Pass | Operative clearance, margin analysis, surgical review |
| **Nurse** | `/doctor/login` | Click **Nurse** Pass | Vital signs intake, longitudinal timeline, appointments |
| **Admin** | `/doctor/login` | Click **Admin** Pass | System telemetry, model monitoring, HIPAA audit trail |
| **Patient (Eleanor Vance)** | `/patient/login` | `MS-2026-004821` / `password123` | Plain-English summary, appointments, care team chat |

---

## 🛡️ Clinical Disclaimer
**MediScan AI** is an artificial intelligence clinical decision-support system intended to augment and assist certified medical practitioners. It is not an autonomous diagnostic device and should not replace definitive histopathological confirmation or licensed clinician evaluation.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
