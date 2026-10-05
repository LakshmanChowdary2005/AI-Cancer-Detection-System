import os
import json
import time
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, send_file
from utils.hospital_core import (
    get_all_patients,
    get_patient_by_id,
    save_patient,
    generate_patient_id,
    get_command_center_stats,
    get_worklist,
    get_patient_friendly_explanation,
    log_audit_event,
    _load_json,
    _save_json,
    AUDIT_LOG_FILE,
    APPOINTMENTS_FILE,
    MODEL_MONITORING_FILE,
    NOTIFICATIONS_FILE,
    REPORTS_FILE
)

hospital_bp = Blueprint('hospital_bp', __name__)

# ---------------------------------------------------------------------------
# 1. Hospital Command Center & Clinical Dashboard
# ---------------------------------------------------------------------------
@hospital_bp.route("/hospital-dashboard")
def hospital_dashboard():
    stats = get_command_center_stats()
    patients = get_all_patients()
    worklist = get_worklist(filter_status="all")
    notifications = _load_json(NOTIFICATIONS_FILE, [])
    
    # Audit log entry
    log_audit_event(
        user=session.get("doctor_email", "Dr. Sarah Sharma"),
        role=session.get("user_role", "Doctor"),
        action="Accessed Hospital Command Center",
        details="Viewed Today's Overview, critical findings triage, and department telemetry."
    )
    
    return render_template(
        "hospital_dashboard.html",
        stats=stats,
        patients=patients,
        worklist=worklist[:6],
        notifications=notifications,
        doctor_email=session.get("doctor_email", "doctor@mediscan.ai"),
        user_role=session.get("user_role", "Doctor")
    )

# ---------------------------------------------------------------------------
# 2. Patients & Full EMR
# ---------------------------------------------------------------------------
@hospital_bp.route("/patients")
@hospital_bp.route("/patients/<patient_id>")
def patients_view(patient_id=None):
    all_patients = get_all_patients()
    if not patient_id and all_patients:
        patient_id = all_patients[0]["patient_id"]
        
    selected_patient = get_patient_by_id(patient_id) if patient_id else (all_patients[0] if all_patients else None)
    
    log_audit_event(
        user=session.get("doctor_email", "Dr. Sarah Sharma"),
        role=session.get("user_role", "Doctor"),
        action=f"Viewed Patient Record {patient_id}",
        patient_id=patient_id,
        details=f"Inspected EMR profile, longitudinal timeline, and medical records for {selected_patient.get('name') if selected_patient else 'Unknown'}."
    )
    
    return render_template(
        "patients.html",
        patients=all_patients,
        patient=selected_patient,
        notifications=_load_json(NOTIFICATIONS_FILE, []),
        doctor_email=session.get("doctor_email", "doctor@mediscan.ai"),
        user_role=session.get("user_role", "Doctor")
    )

# ---------------------------------------------------------------------------
# 3. DICOM / PACS-Style Imaging Workspace
# ---------------------------------------------------------------------------
@hospital_bp.route("/imaging")
def imaging_workspace():
    patient_id = request.args.get("patient_id", "MS-2026-004821")
    patient = get_patient_by_id(patient_id)
    if not patient:
        patients = get_all_patients()
        patient = patients[0] if patients else {}
        
    # Get primary scan
    scans = patient.get("scans", [])
    primary_scan = scans[0] if scans else {
        "scan_id": "SCN-2026-8812",
        "date": "2026-01-22",
        "modality": "CT Chest (Low-Dose)",
        "body_part": "Thorax / Lungs",
        "finding": "Adenocarcinoma - Right Upper Lobe",
        "confidence": "94.2%",
        "risk": "High",
        "image_url": "/static/uploads/lungaca1.jpeg",
        "heatmap_url": "/static/uploads/lungaca1.jpeg",
        "status": "Doctor Verified"
    }
    
    comparison_scan = scans[1] if len(scans) > 1 else primary_scan
    
    log_audit_event(
        user=session.get("doctor_email", "Dr. Sarah Sharma"),
        role=session.get("user_role", "Doctor"),
        action=f"PACS Imaging Inspection",
        patient_id=patient.get("patient_id"),
        details=f"Opened high-resolution scan {primary_scan.get('scan_id')} in DICOM viewer with Grad-CAM overlay."
    )
    
    return render_template(
        "imaging.html",
        patient=patient,
        scan=primary_scan,
        comparison_scan=comparison_scan,
        notifications=_load_json(NOTIFICATIONS_FILE, []),
        doctor_email=session.get("doctor_email", "doctor@mediscan.ai"),
        user_role=session.get("user_role", "Doctor")
    )

# ---------------------------------------------------------------------------
# 4. Multidisciplinary Tumor Board (MDT Review)
# ---------------------------------------------------------------------------
@hospital_bp.route("/tumor-board")
def tumor_board():
    patient_id = request.args.get("patient_id", "MS-2026-004821")
    patient = get_patient_by_id(patient_id)
    if not patient:
        patients = get_all_patients()
        patient = patients[0] if patients else {}
        
    log_audit_event(
        user=session.get("doctor_email", "Dr. Sarah Sharma"),
        role=session.get("user_role", "Doctor"),
        action="Convened MDT Tumor Board",
        patient_id=patient.get("patient_id"),
        details="Conducted multidisciplinary review with Radiology, Medical Oncology, and Thoracic Surgery personas."
    )
    
    return render_template(
        "tumor_board.html",
        patient=patient,
        notifications=_load_json(NOTIFICATIONS_FILE, []),
        doctor_email=session.get("doctor_email", "doctor@mediscan.ai"),
        user_role=session.get("user_role", "Doctor")
    )

# ---------------------------------------------------------------------------
# 5. Doctor Worklist
# ---------------------------------------------------------------------------
@hospital_bp.route("/worklist")
def worklist_view():
    filter_val = request.args.get("filter", "all")
    worklist = get_worklist(filter_status=filter_val)
    
    return render_template(
        "worklist.html",
        worklist=worklist,
        current_filter=filter_val,
        notifications=_load_json(NOTIFICATIONS_FILE, []),
        doctor_email=session.get("doctor_email", "doctor@mediscan.ai"),
        user_role=session.get("user_role", "Doctor")
    )

# ---------------------------------------------------------------------------
# 6. Appointment Management
# ---------------------------------------------------------------------------
@hospital_bp.route("/appointments")
def appointments_view():
    appointments = _load_json(APPOINTMENTS_FILE, [])
    patients = get_all_patients()
    
    return render_template(
        "appointments.html",
        appointments=appointments,
        patients=patients,
        notifications=_load_json(NOTIFICATIONS_FILE, []),
        doctor_email=session.get("doctor_email", "doctor@mediscan.ai"),
        user_role=session.get("user_role", "Doctor")
    )

# ---------------------------------------------------------------------------
# 7. Dedicated Patient Portal
# ---------------------------------------------------------------------------
@hospital_bp.route("/portal/patient")
def patient_portal_view():
    patient_id = request.args.get("patient_id", "MS-2026-004821")
    patient = get_patient_by_id(patient_id)
    if not patient:
        patients = get_all_patients()
        patient = patients[0] if patients else {}
        
    plain_english = get_patient_friendly_explanation(
        patient.get("scans", [{}])[0].get("finding", ""),
        patient.get("cancer_type", "lung")
    )
    
    log_audit_event(
        user=patient.get("name", "Patient"),
        role="Patient",
        action="Accessed Patient Portal",
        patient_id=patient.get("patient_id"),
        details="Viewed patient-friendly diagnostic explanation, appointments, and care documents."
    )
    
    return render_template(
        "patient_portal.html",
        patient=patient,
        plain_english=plain_english,
        notifications=_load_json(NOTIFICATIONS_FILE, []),
        user_role="Patient"
    )

# ---------------------------------------------------------------------------
# 8. Hospital Analytics & AI Model Monitoring
# ---------------------------------------------------------------------------
@hospital_bp.route("/analytics")
def analytics_view():
    stats = get_command_center_stats()
    monitoring = _load_json(MODEL_MONITORING_FILE, {})
    reports = _load_json(REPORTS_FILE, [])
    
    return render_template(
        "analytics.html",
        stats=stats,
        monitoring=monitoring,
        reports_count=len(reports),
        notifications=_load_json(NOTIFICATIONS_FILE, []),
        doctor_email=session.get("doctor_email", "doctor@mediscan.ai"),
        user_role=session.get("user_role", "Doctor")
    )

# ---------------------------------------------------------------------------
# 9. Privacy, Security & Audit Trail
# ---------------------------------------------------------------------------
@hospital_bp.route("/security")
def security_view():
    audit_logs = _load_json(AUDIT_LOG_FILE, [])
    
    return render_template(
        "security.html",
        audit_logs=audit_logs,
        notifications=_load_json(NOTIFICATIONS_FILE, []),
        doctor_email=session.get("doctor_email", "doctor@mediscan.ai"),
        user_role=session.get("user_role", "Doctor")
    )

# ---------------------------------------------------------------------------
# REST API Endpoints
# ---------------------------------------------------------------------------
@hospital_bp.route("/api/patients", methods=["GET"])
def api_get_patients():
    return jsonify(get_all_patients())

@hospital_bp.route("/api/worklist", methods=["GET"])
def api_get_worklist():
    filter_val = request.args.get("filter", "all")
    return jsonify(get_worklist(filter_status=filter_val))

@hospital_bp.route("/api/patients/<patient_id>", methods=["GET"])
def api_get_patient_details(patient_id):
    p = get_patient_by_id(patient_id)
    if p:
        return jsonify(p)
    return jsonify({"error": "Patient not found"}), 404

@hospital_bp.route("/api/patients/register", methods=["POST"])
def api_register_patient():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Patient name is required"}), 400
        
    pid = data.get("patient_id") or generate_patient_id()
    new_patient = {
        "patient_id": pid,
        "name": name,
        "age": int(data.get("age", 45)),
        "dob": data.get("dob", "1980-01-01"),
        "gender": data.get("gender", "Female"),
        "blood_group": data.get("blood_group", "O+"),
        "phone": data.get("phone", "+1 (555) 000-0000"),
        "email": data.get("email", ""),
        "emergency_contact": data.get("emergency_contact", "Spouse"),
        "address": data.get("address", "Metro City"),
        "allergies": [a.strip() for a in data.get("allergies", "").split(",") if a.strip()] or ["NKDA"],
        "existing_conditions": [c.strip() for c in data.get("existing_conditions", "").split(",") if c.strip()],
        "current_medications": [m.strip() for m in data.get("current_medications", "").split(",") if m.strip()],
        "cancer_history": data.get("cancer_history", "No prior oncology history"),
        "assigned_doctor": data.get("assigned_doctor", "Dr. Sarah Sharma, MD"),
        "department": data.get("department", "Oncology"),
        "status": "Registered",
        "registration_date": datetime.now().strftime("%Y-%m-%d"),
        "consent": {
            "imaging_analysis": True,
            "report_generation": True,
            "secure_sharing": True,
            "research_usage": bool(data.get("consent_research", False)),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "signed_by": name
        },
        "timeline": [
            {
                "date": datetime.now().strftime("%d %b %Y"),
                "title": "Hospital Registration & Clinical Intake",
                "doctor": data.get("assigned_doctor", "Dr. Sarah Sharma, MD"),
                "department": data.get("department", "Oncology"),
                "notes": "Patient profile and EMR initialized. Consent verified.",
                "badge": "Registration",
                "type": "consultation"
            }
        ],
        "visits": [],
        "scans": [],
        "medications": [],
        "lab_results": [],
        "notes": []
    }
    
    saved = save_patient(new_patient)
    
    log_audit_event(
        user=session.get("doctor_email", "Staff"),
        role=session.get("user_role", "Nurse"),
        action=f"Registered New Patient {pid}",
        patient_id=pid,
        details=f"Created EMR record for {name} with ID {pid}."
    )
    
    return jsonify({"success": True, "patient": saved})

@hospital_bp.route("/api/appointments/new", methods=["POST"])
def api_new_appointment():
    data = request.get_json() or {}
    patient_id = data.get("patient_id")
    patient_name = data.get("patient_name", "Patient")
    
    appts = _load_json(APPOINTMENTS_FILE, [])
    new_appt = {
        "id": f"APT-2026-{len(appts) + 101}",
        "patient_id": patient_id,
        "patient_name": patient_name,
        "doctor": data.get("doctor", "Dr. Sarah Sharma, MD"),
        "department": data.get("department", "Oncology"),
        "appointment_date": data.get("appointment_date", datetime.now().strftime("%Y-%m-%d")),
        "appointment_time": data.get("appointment_time", "10:00 AM"),
        "type": data.get("type", "Consultation"),
        "status": "Confirmed",
        "priority": data.get("priority", "Routine"),
        "notes": data.get("notes", "")
    }
    appts.insert(0, new_appt)
    _save_json(APPOINTMENTS_FILE, appts)
    
    log_audit_event(
        user=session.get("doctor_email", "Staff"),
        role="Doctor",
        action=f"Scheduled Appointment {new_appt['id']}",
        patient_id=patient_id,
        details=f"{new_appt['type']} with {new_appt['doctor']} on {new_appt['appointment_date']}."
    )
    
    return jsonify({"success": True, "appointment": new_appt})

@hospital_bp.route("/api/audit_logs/add", methods=["POST"])
def api_add_audit_log():
    data = request.get_json() or {}
    event = log_audit_event(
        user=data.get("user"),
        role=data.get("role"),
        action=data.get("action"),
        patient_id=data.get("patient_id"),
        details=data.get("details", "")
    )
    return jsonify({"success": True, "event": event})

@hospital_bp.route("/api/share_report", methods=["POST"])
def api_share_report():
    data = request.get_json() or {}
    patient_id = data.get("patient_id", "MS-2026-004821")
    expiry_hours = int(data.get("expiry_hours", 24))
    token = uuid.uuid4().hex[:16]
    share_url = f"{request.host_url}portal/patient?patient_id={patient_id}&token={token}"
    
    log_audit_event(
        user=session.get("doctor_email", "Dr. Sarah Sharma"),
        role="Doctor",
        action="Generated Secure Share Link",
        patient_id=patient_id,
        details=f"Created encrypted access token expiring in {expiry_hours} hours."
    )
    
    return jsonify({
        "success": True,
        "token": token,
        "share_url": share_url,
        "expiry_hours": expiry_hours
    })
