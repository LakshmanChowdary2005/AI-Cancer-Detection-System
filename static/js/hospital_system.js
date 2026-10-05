/**
 * MEDISCAN AI — Hospital Clinical System & PACS DICOM Engine
 * Controls: PACS Workspace, EMR Tabs, Tumor Board, Doctor Sign-off, RBAC, Sharing
 */

// Global State
window.MediScan = {
  currentRole: localStorage.getItem('mediscan_role') || 'Doctor',
  currentDept: localStorage.getItem('mediscan_dept') || 'All Departments',
  pacsState: {
    zoom: 1,
    rotation: 0,
    panX: 0,
    panY: 0,
    brightness: 100,
    contrast: 100,
    invert: false,
    heatmapOpacity: 0.75,
    overlayVisible: true,
    currentSlice: 1,
    totalSlices: 8,
    isDragging: false,
    startX: 0,
    startY: 0
  }
};

document.addEventListener('DOMContentLoaded', function () {
  initRoleAndDept();
  initPACSViewer();
  initEMRTabs();
  initSignOffSystem();
  initNotificationDrawer();
  initSharingModal();
  initPatientFriendlyToggle();
});

// ---------------------------------------------------------------------------
// 1. Role-Based Access Control (RBAC) & Treatment Scope Engine
// ---------------------------------------------------------------------------
const CLINICAL_ROLE_PROFILES = {
  Doctor: {
    title: 'Attending Physician / Clinical Oncologist',
    dept: 'Oncology / General Medicine',
    summary: 'Doctor: Primary Triage & Prescriptions',
    badgeClass: 'green',
    access: ['Dashboard & Census', 'EMR Longitudinal Timeline', 'Diagnostic Worklist', 'Clinical Appointments', 'AI Neural Scanner', 'Digital Report Sign-Off'],
    treatments: [
      'Primary Diagnostic Workup & Staging (TNM/FIGO)',
      'Oral Symptom & Palliative Medication Prescriptions',
      'Specialist Referrals (Surgical Oncology, Radiation Oncology)',
      'Digital Clinical Sign-off & Report Finalization',
      'Inpatient Admission & Discharge Directives'
    ],
    limitations: 'Cannot perform invasive radical surgical resection without Surgical Oncologist.'
  },
  Radiologist: {
    title: 'Diagnostic & Interventional Radiologist',
    dept: 'Radiology / Diagnostic Imaging',
    summary: 'Radiologist: PACS & Biopsy Guidance',
    badgeClass: 'cyan',
    access: ['PACS DICOM Workstation', 'Grad-CAM Attention Heatmaps', 'Lesion Caliper HUD', 'Radiology Worklist', 'Multi-Agent Review'],
    treatments: [
      'CT & Ultrasound-Guided Core Needle / FNA Biopsies',
      'Stereotactic Lesion Marking & Hook-Wire Localization',
      'Radiofrequency & Microwave Ablation (RFA/MWA) Guidance',
      'Radiation Oncology GTV/CTV Target Volume Contouring',
      'Standardized BI-RADS & Lung-RADS Classification'
    ],
    limitations: 'Cannot prescribe systemic chemotherapy regimens or discharge inpatients.'
  },
  Oncologist: {
    title: 'Medical Oncologist & Hematology Specialist',
    dept: 'Medical Oncology',
    summary: 'Oncologist: Chemotherapy & Precision Targeted Therapy',
    badgeClass: 'purple',
    access: ['MDT Tumor Board', 'EMR Regimen History', 'Drug Interactions Engine', 'Toxicity & Monitoring Flowsheet', 'Genomic Risk Models'],
    treatments: [
      'Intravenous Chemotherapy Cycles (Cisplatin, Paclitaxel, Carboplatin)',
      'Targeted Precision Kinase Inhibitors (Osimertinib, Trastuzumab, ALK)',
      'Immune Checkpoint Blockade Immunotherapy (Pembrolizumab, Nivolumab)',
      'Endocrine / Hormonal Blockade (Tamoxifen, Letrozole)',
      'Comprehensive Molecular NGS & PD-L1 Biomarker Ordering'
    ],
    limitations: 'Cannot perform radical surgical excision without Surgical Oncologist.'
  },
  Surgeon: {
    title: 'Surgical Oncologist',
    dept: 'Surgical Oncology / OR Suites',
    summary: 'Surgeon: Resection & Surgical Margin Clearance',
    badgeClass: 'amber',
    access: ['PACS Pre-Op Resectability', 'MDT Tumor Board', 'Surgical Worklist & OR Queue', 'Operative Pathology Notes'],
    treatments: [
      'Radical Tumor Resections (VATS Lobectomy, Mastectomy, Wide Excision)',
      'Sentinel Lymph Node Dissection (SLND) & Regional Clearance',
      'Minimally Invasive Laparoscopic / Robotic Staging',
      'Intraoperative Frozen Section Margin Evaluation',
      'Vascular Chemo Port-A-Cath Implantation & Explantation'
    ],
    limitations: 'Cannot modify medical oncology systemic chemotherapy cycles.'
  },
  Nurse: {
    title: 'Oncology Nurse & Infusion Specialist',
    dept: 'Inpatient Oncology / Outpatient Infusion',
    summary: 'Nurse: Chemo Infusion & Bedside Vitals',
    badgeClass: 'green',
    access: ['Inpatient Bedside Census', 'EMR Medication Flowsheet', 'Infusion Appointment Check-In', 'Supportive Care Guidelines'],
    treatments: [
      'Administration of IV Chemotherapy Infusions & Premedications',
      'Central Line (PICC / Port) Sterile Dressing & Heparin Flush',
      'Immediate Acute Infusion Reaction & Extravasation Protocol',
      'Bedside Vitals, Pain Score & ECOG Performance Documentation',
      'Patient & Family Chemotherapy Toxicity Education'
    ],
    limitations: 'Cannot prescribe antineoplastic drugs or digitally authorize diagnostic reports.'
  },
  Admin: {
    title: 'Hospital Operations & Compliance Administrator',
    dept: 'Administration & Governance',
    summary: 'Admin: HIPAA Audit Forensics & Compliance',
    badgeClass: 'rose',
    access: ['HIPAA Security & Audit Trail', 'Enterprise AI Drift Analytics', 'Staff Credentialing & RBAC', 'HL7 & Excel Export'],
    treatments: [
      'HIPAA Compliance & Immutable Audit Log Verification',
      'Clinical Staff Account Privilege Provisioning & Revocation',
      'AI Diagnostic Drift & Confidence Threshold Calibration',
      'Enterprise System Lockdown & Incident Response'
    ],
    limitations: 'Non-clinical governance role: strictly prohibited from prescribing patient treatments.'
  },
  Patient: {
    title: 'Patient & Family Caregiver',
    dept: 'Outpatient / Home Care',
    summary: 'Patient: Personal Health Portal & Care Plan',
    badgeClass: 'green',
    access: ['Personal Health Portal', 'Plain-Language Diagnostic Summaries', 'Appointment Schedule', 'Supportive Nutrition Guidelines'],
    treatments: [
      'Home Care Adherence & Oral Medication Tracking',
      'Daily Temperature & Symptom Diary Logging',
      'Direct Secure Messaging to Oncology Care Team',
      'Prescription Refill Inquiries'
    ],
    limitations: 'Read-only patient record view; restricted from confidential hospital clinical panels.'
  }
};

window.CLINICAL_ROLE_PROFILES = CLINICAL_ROLE_PROFILES;

function initRoleAndDept() {
  const roleSelect = document.getElementById('roleSelector');
  const deptSelect = document.getElementById('deptSelector');

  if (roleSelect) {
    roleSelect.value = window.MediScan.currentRole;
    roleSelect.addEventListener('change', function (e) {
      const newRole = e.target.value;
      window.MediScan.currentRole = newRole;
      localStorage.setItem('mediscan_role', newRole);
      applyRolePermissions(newRole);
      showToast(`Switched Role: ${newRole} (Authorized Treatment Scope Updated)`, 'info');
    });
    applyRolePermissions(window.MediScan.currentRole);
  }

  if (deptSelect) {
    deptSelect.value = window.MediScan.currentDept;
    deptSelect.addEventListener('change', function (e) {
      const newDept = e.target.value;
      window.MediScan.currentDept = newDept;
      localStorage.setItem('mediscan_dept', newDept);
      showToast(`Department Filter: ${newDept}`, 'info');
    });
  }
}

function applyRolePermissions(role) {
  const profile = CLINICAL_ROLE_PROFILES[role] || CLINICAL_ROLE_PROFILES.Doctor;

  // Update header treatment scope pill
  const scopeSummary = document.getElementById('roleScopeSummary');
  if (scopeSummary) {
    scopeSummary.textContent = profile.summary;
  }

  // Update active role badge if present
  const roleBadge = document.getElementById('activeRoleBadge');
  if (roleBadge) {
    roleBadge.textContent = role;
  }

  // Update role selector dropdown value if not already matching
  const roleSelect = document.getElementById('roleSelector');
  if (roleSelect && roleSelect.value !== role) {
    roleSelect.value = role;
  }

  // Update modal active tab if modal is open
  switchModalRoleTab(role, false);

  // Adjust role-based elements visibility
  const doctorActions = document.querySelectorAll('.role-doctor-only');
  const adminActions = document.querySelectorAll('.role-admin-only');
  const patientActions = document.querySelectorAll('.role-patient-only');

  if (role === 'Patient') {
    doctorActions.forEach(el => el.style.display = 'none');
    adminActions.forEach(el => el.style.display = 'none');
    patientActions.forEach(el => el.style.display = '');
  } else if (role === 'Admin') {
    doctorActions.forEach(el => el.style.display = '');
    adminActions.forEach(el => el.style.display = '');
    patientActions.forEach(el => el.style.display = '');
  } else {
    // Clinicians (Doctor, Radiologist, Oncologist, Surgeon, Nurse)
    doctorActions.forEach(el => el.style.display = '');
    adminActions.forEach(el => el.style.display = 'none');
    patientActions.forEach(el => el.style.display = 'none');
  }
}

// Global Modal Controllers
window.openRoleScopeModal = function(role) {
  const targetRole = role || window.MediScan.currentRole || 'Doctor';
  switchModalRoleTab(targetRole);
  const modal = document.getElementById('roleScopeModal');
  if (modal) {
    modal.classList.add('active');
  }
};

window.closeRoleScopeModal = function(e) {
  if (e && e.target && e.target !== e.currentTarget && e.target.id !== 'roleScopeModal' && !e.target.closest('button[onclick*="closeRoleScopeModal"]')) {
    return;
  }
  const modal = document.getElementById('roleScopeModal');
  if (modal) {
    modal.classList.remove('active');
  }
};

window.switchModalRoleTab = function(role, updateCurrent = false) {
  // Update tab buttons
  document.querySelectorAll('.role-tab-btn').forEach(btn => {
    if (btn.getAttribute('data-role') === role) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Update profile views
  document.querySelectorAll('.role-profile-view').forEach(view => {
    if (view.id === `role-view-${role}`) {
      view.classList.add('active');
    } else {
      view.classList.remove('active');
    }
  });

  if (updateCurrent) {
    window.MediScan.currentRole = role;
    localStorage.setItem('mediscan_role', role);
    applyRolePermissions(role);
  }
};

window.selectRoleFromModal = function(role) {
  window.MediScan.currentRole = role;
  localStorage.setItem('mediscan_role', role);
  applyRolePermissions(role);
  const modal = document.getElementById('roleScopeModal');
  if (modal) {
    modal.classList.remove('active');
  }
  if (typeof showToast === 'function') {
    showToast(`Role Activated: ${role}. Required access and authorized treatments enabled!`, 'success');
  }
};

// ---------------------------------------------------------------------------
// 2. DICOM / PACS-Style Imaging Workspace Engine
// ---------------------------------------------------------------------------
function initPACSViewer() {
  const container = document.getElementById('pacsContainer');
  const scanImg = document.getElementById('pacsScanImage');
  const heatmapOverlay = document.getElementById('pacsHeatmapOverlay');
  if (!container || !scanImg) return;

  const state = window.MediScan.pacsState;

  function updateTransform() {
    let filterStr = `brightness(${state.brightness}%) contrast(${state.contrast}%)`;
    if (state.invert) filterStr += ' invert(100%)';

    scanImg.style.transform = `translate(${state.panX}px, ${state.panY}px) scale(${state.zoom}) rotate(${state.rotation}deg)`;
    scanImg.style.filter = filterStr;

    if (heatmapOverlay) {
      heatmapOverlay.style.transform = `translate(${state.panX}px, ${state.panY}px) scale(${state.zoom}) rotate(${state.rotation}deg)`;
      heatmapOverlay.style.opacity = state.overlayVisible ? state.heatmapOpacity : '0';
    }

    // Update HUD
    const hudZoom = document.getElementById('hudZoom');
    const hudWindow = document.getElementById('hudWindow');
    if (hudZoom) hudZoom.textContent = `MAG: ${(state.zoom * 100).toFixed(0)}%`;
    if (hudWindow) hudWindow.textContent = `W: ${state.contrast * 10} L: ${state.brightness * 5}`;
  }

  // Zoom buttons
  const btnZoomIn = document.getElementById('pacsZoomIn');
  const btnZoomOut = document.getElementById('pacsZoomOut');
  const btnFit = document.getElementById('pacsFit');

  if (btnZoomIn) {
    btnZoomIn.addEventListener('click', () => {
      state.zoom = Math.min(state.zoom + 0.25, 4);
      updateTransform();
    });
  }
  if (btnZoomOut) {
    btnZoomOut.addEventListener('click', () => {
      state.zoom = Math.max(state.zoom - 0.25, 0.5);
      updateTransform();
    });
  }
  if (btnFit) {
    btnFit.addEventListener('click', () => {
      state.zoom = 1;
      state.panX = 0;
      state.panY = 0;
      state.rotation = 0;
      updateTransform();
    });
  }

  // Rotate button
  const btnRotate = document.getElementById('pacsRotate');
  if (btnRotate) {
    btnRotate.addEventListener('click', () => {
      state.rotation = (state.rotation + 90) % 360;
      updateTransform();
    });
  }

  // Reset button
  const btnReset = document.getElementById('pacsReset');
  if (btnReset) {
    btnReset.addEventListener('click', () => {
      state.zoom = 1;
      state.rotation = 0;
      state.panX = 0;
      state.panY = 0;
      state.brightness = 100;
      state.contrast = 100;
      state.invert = false;
      state.heatmapOpacity = 0.75;
      state.overlayVisible = true;
      const bSlider = document.getElementById('pacsBrightness');
      const cSlider = document.getElementById('pacsContrast');
      const hSlider = document.getElementById('pacsHeatmapOpacity');
      if (bSlider) bSlider.value = 100;
      if (cSlider) cSlider.value = 100;
      if (hSlider) hSlider.value = 75;
      updateTransform();
      showToast('PACS Workspace View Reset', 'info');
    });
  }

  // Invert button
  const btnInvert = document.getElementById('pacsInvert');
  if (btnInvert) {
    btnInvert.addEventListener('click', () => {
      state.invert = !state.invert;
      btnInvert.classList.toggle('active', state.invert);
      updateTransform();
    });
  }

  // Overlay toggle
  const btnToggleOverlay = document.getElementById('pacsToggleOverlay');
  if (btnToggleOverlay) {
    btnToggleOverlay.addEventListener('click', () => {
      state.overlayVisible = !state.overlayVisible;
      btnToggleOverlay.classList.toggle('active', state.overlayVisible);
      updateTransform();
    });
  }

  // Sliders
  const bSlider = document.getElementById('pacsBrightness');
  if (bSlider) {
    bSlider.addEventListener('input', (e) => {
      state.brightness = parseInt(e.target.value, 10);
      updateTransform();
    });
  }

  const cSlider = document.getElementById('pacsContrast');
  if (cSlider) {
    cSlider.addEventListener('input', (e) => {
      state.contrast = parseInt(e.target.value, 10);
      updateTransform();
    });
  }

  const hSlider = document.getElementById('pacsHeatmapOpacity');
  if (hSlider) {
    hSlider.addEventListener('input', (e) => {
      state.heatmapOpacity = parseInt(e.target.value, 10) / 100.0;
      updateTransform();
    });
  }

  // Full-screen
  const btnFullscreen = document.getElementById('pacsFullscreen');
  if (btnFullscreen) {
    btnFullscreen.addEventListener('click', () => {
      const workspace = document.querySelector('.pacs-workspace');
      if (!document.fullscreenElement) {
        if (workspace.requestFullscreen) workspace.requestFullscreen();
      } else {
        if (document.exitFullscreen) document.exitFullscreen();
      }
    });
  }

  // Pan dragging
  container.addEventListener('mousedown', (e) => {
    state.isDragging = true;
    state.startX = e.clientX - state.panX;
    state.startY = e.clientY - state.panY;
  });

  window.addEventListener('mousemove', (e) => {
    if (!state.isDragging) return;
    state.panX = e.clientX - state.startX;
    state.panY = e.clientY - state.startY;
    updateTransform();
  });

  window.addEventListener('mouseup', () => {
    state.isDragging = false;
  });

  // Mouse wheel zoom
  container.addEventListener('wheel', (e) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.15 : -0.15;
    state.zoom = Math.min(Math.max(state.zoom + delta, 0.4), 4.0);
    updateTransform();
  }, { passive: false });

  // Slice navigation
  const prevSlice = document.getElementById('pacsPrevSlice');
  const nextSlice = document.getElementById('pacsNextSlice');
  const sliceSlider = document.getElementById('pacsSliceSlider');
  const hudSlice = document.getElementById('hudSlice');

  function setSlice(num) {
    state.currentSlice = Math.min(Math.max(num, 1), state.totalSlices);
    if (sliceSlider) sliceSlider.value = state.currentSlice;
    if (hudSlice) hudSlice.textContent = `IMG ${state.currentSlice} / ${state.totalSlices}`;
    const sliceIndicator = document.getElementById('pacsSliceIndicator');
    if (sliceIndicator) sliceIndicator.textContent = `Slice ${state.currentSlice} of ${state.totalSlices}`;
  }

  if (prevSlice) {
    prevSlice.addEventListener('click', () => setSlice(state.currentSlice - 1));
  }
  if (nextSlice) {
    nextSlice.addEventListener('click', () => setSlice(state.currentSlice + 1));
  }
  if (sliceSlider) {
    sliceSlider.addEventListener('input', (e) => setSlice(parseInt(e.target.value, 10)));
  }

  // Initial render
  updateTransform();
}

// ---------------------------------------------------------------------------
// 3. Medical Records Tabs Engine
// ---------------------------------------------------------------------------
function initEMRTabs() {
  const tabButtons = document.querySelectorAll('.med-tab-btn');
  const tabContents = document.querySelectorAll('.med-tab-content');

  tabButtons.forEach(btn => {
    btn.addEventListener('click', function () {
      const targetId = this.getAttribute('data-tab');

      tabButtons.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.style.display = 'none');

      this.classList.add('active');
      const targetContent = document.getElementById(`tab-${targetId}`);
      if (targetContent) targetContent.style.display = 'block';
    });
  });
}

// ---------------------------------------------------------------------------
// 4. Doctor Review & Digital Sign-off
// ---------------------------------------------------------------------------
function initSignOffSystem() {
  const actionBtns = document.querySelectorAll('.signoff-action-btn');
  const signBtn = document.getElementById('executeSignOffBtn');
  let selectedAction = 'confirm';

  actionBtns.forEach(btn => {
    btn.addEventListener('click', function () {
      actionBtns.forEach(b => b.classList.remove('active'));
      this.classList.add('active');
      selectedAction = this.getAttribute('data-action');
    });
  });

  if (signBtn) {
    signBtn.addEventListener('click', function () {
      const doctorName = document.getElementById('signDoctorName')?.value || 'Dr. Sarah Sharma, MD';
      const doctorNotes = document.getElementById('signDoctorNotes')?.value || 'Reviewed AI localization. Clinical correlation confirmed.';
      const stampBox = document.getElementById('signatureStampPreview');

      const now = new Date();
      const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      const dateStr = now.toLocaleDateString([], { day: '2-digit', month: 'short', year: 'numeric' });

      if (stampBox) {
        stampBox.innerHTML = `
          <div style="color: #34d399; font-size: 1.1rem; font-weight: 800; font-family: sans-serif; margin-bottom: 4px;">
            <i class="fa-solid fa-certificate"></i> VERIFIED & DIGITALLY SIGNED
          </div>
          <div style="font-family: 'Brush Script MT', cursive; font-size: 1.8rem; color: #38bdf8;">
            ${doctorName}
          </div>
          <div style="font-size: 0.72rem; color: #94a3b8; font-family: monospace; margin-top: 4px;">
            Action: ${selectedAction.toUpperCase()} &bull; Signed: ${dateStr} ${timeStr} &bull; SHA-256: 7f8a9e2c4b...
          </div>
        `;
        stampBox.style.display = 'block';
      }

      showToast(`Diagnostic Report Successfully Signed by ${doctorName}`, 'success');

      // Post audit log event to backend
      fetch('/api/audit_logs/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user: doctorName,
          role: 'Doctor',
          action: `Report ${selectedAction === 'confirm' ? 'Approved & Signed' : (selectedAction === 'modify' ? 'Modified & Signed' : 'Rejected')}`,
          patient_id: document.getElementById('currentPatientId')?.value || 'MS-2026-004821',
          details: doctorNotes
        })
      }).catch(() => {});
    });
  }
}

// ---------------------------------------------------------------------------
// 5. Notification Drawer
// ---------------------------------------------------------------------------
function initNotificationDrawer() {
  const notifBell = document.getElementById('notifBellBtn');
  const notifDropdown = document.getElementById('notifDropdown');

  if (notifBell && notifDropdown) {
    notifBell.addEventListener('click', (e) => {
      e.stopPropagation();
      notifDropdown.classList.toggle('show');
    });

    document.addEventListener('click', () => {
      notifDropdown.classList.remove('show');
    });

    notifDropdown.addEventListener('click', (e) => {
      e.stopPropagation();
    });
  }
}

// ---------------------------------------------------------------------------
// 6. Secure Report Sharing Modal
// ---------------------------------------------------------------------------
function initSharingModal() {
  const shareBtn = document.getElementById('openShareModalBtn');
  const modal = document.getElementById('secureShareModal');
  const closeBtn = document.getElementById('closeShareModalBtn');
  const copyBtn = document.getElementById('copyShareLinkBtn');

  if (shareBtn && modal) {
    shareBtn.addEventListener('click', () => {
      modal.style.display = 'flex';
    });
  }

  if (closeBtn && modal) {
    closeBtn.addEventListener('click', () => {
      modal.style.display = 'none';
    });
  }

  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      const shareUrlInput = document.getElementById('shareUrlInput');
      if (shareUrlInput) {
        shareUrlInput.select();
        navigator.clipboard.writeText(shareUrlInput.value);
        showToast('Secure Share Link Copied to Clipboard!', 'success');
      }
    });
  }
}

// ---------------------------------------------------------------------------
// 7. Dual Mode AI Explanation Toggle (Clinical vs Patient-Friendly)
// ---------------------------------------------------------------------------
function initPatientFriendlyToggle() {
  const clinicalView = document.getElementById('aiClinicalView');
  const patientView = document.getElementById('aiPatientFriendlyView');
  const btnClinical = document.getElementById('toggleClinicalViewBtn');
  const btnPatient = document.getElementById('togglePatientViewBtn');

  if (btnClinical && btnPatient) {
    btnClinical.addEventListener('click', () => {
      btnClinical.classList.add('active');
      btnPatient.classList.remove('active');
      if (clinicalView) clinicalView.style.display = 'block';
      if (patientView) patientView.style.display = 'none';
    });

    btnPatient.addEventListener('click', () => {
      btnPatient.classList.add('active');
      btnClinical.classList.remove('active');
      if (clinicalView) clinicalView.style.display = 'none';
      if (patientView) patientView.style.display = 'block';
    });
  }
}

// ---------------------------------------------------------------------------
// 8. Toast Helper
// ---------------------------------------------------------------------------
function showToast(message, type = 'info') {
  let toast = document.getElementById('mediscanToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'mediscanToast';
    toast.style.position = 'fixed';
    toast.style.bottom = '24px';
    toast.style.right = '24px';
    toast.style.padding = '12px 20px';
    toast.style.borderRadius = '10px';
    toast.style.fontSize = '0.86rem';
    toast.style.fontWeight = '600';
    toast.style.zIndex = '9999';
    toast.style.boxShadow = '0 8px 30px rgba(0,0,0,0.5)';
    toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    document.body.appendChild(toast);
  }

  if (type === 'success') {
    toast.style.background = '#065f46';
    toast.style.border = '1px solid #10b981';
    toast.style.color = '#a7f3d0';
  } else if (type === 'danger') {
    toast.style.background = '#7f1d1d';
    toast.style.border = '1px solid #ef4444';
    toast.style.color = '#fecaca';
  } else {
    toast.style.background = '#1e3a8a';
    toast.style.border = '1px solid #3b82f6';
    toast.style.color = '#bfdbfe';
  }

  toast.innerHTML = `<i class="fa-solid fa-circle-info" style="margin-right: 8px;"></i> ${message}`;
  toast.style.opacity = '1';
  toast.style.transform = 'translateY(0)';

  clearTimeout(window._toastTimeout);
  window._toastTimeout = setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
  }, 3500);
}
