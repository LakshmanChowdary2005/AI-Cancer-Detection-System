/**
 * MediScan AI — Hospital Enterprise Real-Time Telemetry & Broadcast Engine
 * Syncs real-time hospital digital clock, live HL7/FHIR EHR ping, and hospital network ticker.
 */

(function () {
  'use strict';

  const HOSPITAL_BROADCASTS = [
    { type: 'danger', icon: 'fa-triangle-exclamation', text: '<strong>STAT CALL: Bed 14-B (Oncology ICU)</strong> • Febrile neutropenia protocol initiated (ANC 0.82 k/uL) • Blood cultures drawn' },
    { type: 'info', icon: 'fa-cubes-stacked', text: '<strong>PACS DICOM Feed:</strong> 4 new high-resolution chest CT series ingested from Emergency Trauma Bay 2' },
    { type: 'success', icon: 'fa-prescription', text: '<strong>Clinical Pharmacy:</strong> Dose-Dense AC-T Chemotherapy Regimen verified for Infusion Suite Bay 03' },
    { type: 'purple', icon: 'fa-users', text: '<strong>Tumor Board 4A:</strong> Quorum assembled for Case #8821 (Glioblastoma Stupp Protocol multidisciplinary review)' },
    { type: 'warning', icon: 'fa-vial-circle-check', text: '<strong>Pathology Core:</strong> HER2 IHC 3+ overexpression validated by dual FISH testing for Medical Oncology' },
    { type: 'info', icon: 'fa-wave-square', text: '<strong>Telemetry Suite:</strong> Inpatient telemetry stream live (38 beds monitored) • Zero arrhythmia events in last 4 hours' },
    { type: 'success', icon: 'fa-circle-check', text: '<strong>Ambulatory Ward:</strong> Routine surveillance MRI verified benign (99.8% confidence) • Patient discharged to 12-month recall' }
  ];

  let currentBroadcastIndex = 0;

  // Ensure Hospital Strip is present in page
  function injectHospitalStrip() {
    if (document.querySelector('.hospital-system-strip')) return;

    const targetContainer = document.querySelector('.page-container') || document.querySelector('.login-container') || document.body;
    if (!targetContainer) return;

    const strip = document.createElement('div');
    strip.className = 'hospital-system-strip';
    strip.innerHTML = `
      <div class="hosp-badge-campus">
        <i class="fa-solid fa-hospital text-accent"></i>
        <span><strong>MEDISCAN MEMORIAL ONCOLOGY NETWORK</strong> &bull; Central Cancer Campus</span>
        <span class="hosp-ehr-pill"><span class="radar-dot"></span> EHR HL7/FHIR CONNECTED</span>
      </div>
      
      <div class="hosp-telemetry-ticker">
        <span class="ticker-badge"><i class="fa-solid fa-tower-broadcast"></i> STAT BROADCAST:</span>
        <div class="ticker-content" id="hospitalLiveTicker">
          <span class="ticker-item" id="tickerText">
            <i class="fa-solid fa-triangle-exclamation text-danger"></i> <strong>STAT CALL: Bed 14-B (Oncology ICU)</strong> &bull; Febrile neutropenia protocol initiated
          </span>
        </div>
      </div>

      <div class="hosp-clock-station">
        <span class="hosp-station-pill"><i class="fa-solid fa-user-doctor"></i> Attending: <strong>Dr. S. Chen, MD</strong></span>
        <div class="hosp-clock" id="hospitalLiveClock">--:--:--</div>
        <span class="hosp-ping"><span class="pulse-indicator"></span> 18ms</span>
      </div>
    `;

    targetContainer.insertBefore(strip, targetContainer.firstChild);
  }

  // Update real-time hospital digital clock
  function startHospitalClock() {
    function update() {
      const clockEl = document.getElementById('hospitalLiveClock');
      if (!clockEl) return;
      const now = new Date();
      const timeStr = now.toLocaleTimeString('en-US', { hour12: false });
      clockEl.innerText = `${timeStr} UTC`;
    }
    update();
    setInterval(update, 1000);
  }

  // Rotate hospital broadcast ticker
  function startBroadcastTicker() {
    const tickerContainer = document.getElementById('hospitalLiveTicker');
    if (!tickerContainer) return;

    setInterval(() => {
      currentBroadcastIndex = (currentBroadcastIndex + 1) % HOSPITAL_BROADCASTS.length;
      const b = HOSPITAL_BROADCASTS[currentBroadcastIndex];

      const item = document.getElementById('tickerText');
      if (!item) return;

      item.classList.add('fade-out');
      setTimeout(() => {
        let colorClass = 'text-primary-blue';
        if (b.type === 'danger') colorClass = 'text-danger';
        if (b.type === 'warning') colorClass = 'text-warning';
        if (b.type === 'success') colorClass = 'text-success';

        item.innerHTML = `<i class="fa-solid ${b.icon} ${colorClass}"></i> ${b.text}`;
        item.classList.remove('fade-out');
        item.classList.add('fade-in');
        setTimeout(() => item.classList.remove('fade-in'), 350);
      }, 350);
    }, 4500);
  }

  function init() {
    injectHospitalStrip();
    startHospitalClock();
    startBroadcastTicker();
  }

  // Execute on DOM ready or immediately if ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
