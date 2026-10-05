/**
 * MediScan AI — Universal Accessibility (A11y) Engine
 * Features:
 * - Text-To-Speech (Web Speech API) Multilingual Screen Reader
 * - Colorblind Vision Simulation & Compensation (Protanopia, Deuteranopia, Tritanopia, Grayscale)
 * - WCAG AAA High-Contrast Dark & Light modes
 * - Dyslexia-Friendly Typography
 * - Dynamic Text Size Scaling (100% - 150%)
 * - Interactive Reading Guide Ruler
 * - Keyboard Navigation Shortcuts (Alt+A, Alt+S, Alt+T, Alt+1..6)
 * - LocalStorage state persistence
 */

(function () {
  'use strict';

  // Injected SVG Colorblind Filters for SVG feColorMatrix
  function injectSVGFilters() {
    if (document.getElementById('a11y-svg-filters')) return;
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.id = "a11y-svg-filters";
    svg.style.display = "none";

    svg.innerHTML = `
      <defs>
        <!-- Protanopia (Red-Blind) -->
        <filter id="protanopia-filter">
          <feColorMatrix type="matrix" values="
            0.567, 0.433, 0,     0, 0
            0.558, 0.442, 0,     0, 0
            0,     0.242, 0.758, 0, 0
            0,     0,     0,     1, 0" />
        </filter>
        <!-- Deuteranopia (Green-Blind) -->
        <filter id="deuteranopia-filter">
          <feColorMatrix type="matrix" values="
            0.625, 0.375, 0,   0, 0
            0.7,   0.3,   0,   0, 0
            0,     0.3,   0.7, 0, 0
            0,     0,     0,   1, 0" />
        </filter>
        <!-- Tritanopia (Blue-Blind) -->
        <filter id="tritanopia-filter">
          <feColorMatrix type="matrix" values="
            0.95, 0.05,  0,     0, 0
            0,    0.433, 0.567, 0, 0
            0,    0.475, 0.525, 0, 0
            0,    0,     0,     1, 0" />
        </filter>
      </defs>
    `;
    document.body.appendChild(svg);
  }

  // Inject Accessibility Modal and Floating Trigger Button
  function injectA11yUI() {
    if (document.getElementById('a11y-trigger-btn')) return;

    // Floating Button
    const btn = document.createElement('button');
    btn.id = 'a11y-trigger-btn';
    btn.type = 'button';
    btn.setAttribute('aria-label', 'Open Universal Accessibility Toolbar');
    btn.innerHTML = `<i class="fa-solid fa-universal-access" style="font-size: 1.2rem;"></i> <span>A11y Hub</span>`;
    document.body.appendChild(btn);

    // Reading Ruler
    const ruler = document.createElement('div');
    ruler.id = 'a11y-reading-ruler';
    document.body.appendChild(ruler);

    // Accessibility Modal
    const modal = document.createElement('div');
    modal.className = 'a11y-modal-overlay';
    modal.id = 'a11y-modal';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-labelledby', 'a11y-modal-title');

    modal.innerHTML = `
      <div class="a11y-modal-content">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 id="a11y-modal-title" style="font-size: 1.25rem; display: flex; align-items: center; gap: 10px; margin: 0;">
            <i class="fa-solid fa-universal-access text-accent"></i> Universal Accessibility Suite
          </h3>
          <button id="a11y-close-btn" type="button" class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.85rem;" aria-label="Close Accessibility Menu">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <!-- 1. Text-To-Speech (Screen Reader) -->
        <div class="a11y-section">
          <h4><i class="fa-solid fa-volume-high"></i> Screen Reader / Audio Narration</h4>
          <p style="font-size: 0.82rem; color: var(--muted-light); margin-bottom: 10px;">
            Listen to clinical findings, explanations, and advice read aloud with high-fidelity speech.
          </p>
          <div class="a11y-btn-group" style="margin-bottom: 10px;">
            <button class="a11y-opt-btn" id="tts-read-page"><i class="fa-solid fa-play"></i> Read Main Content</button>
            <button class="a11y-opt-btn" id="tts-pause"><i class="fa-solid fa-pause"></i> Pause</button>
            <button class="a11y-opt-btn" id="tts-stop"><i class="fa-solid fa-stop"></i> Stop</button>
          </div>
          <div style="display: flex; gap: 12px; align-items: center; font-size: 0.82rem;">
            <label>Speed:</label>
            <button class="a11y-opt-btn tts-speed active" data-speed="1.0">1.0x</button>
            <button class="a11y-opt-btn tts-speed" data-speed="0.8">0.8x Slow</button>
            <button class="a11y-opt-btn tts-speed" data-speed="1.25">1.25x Fast</button>
          </div>
        </div>

        <!-- 2. Vision & Colorblind Modes -->
        <div class="a11y-section">
          <h4><i class="fa-solid fa-eye"></i> Vision & Colorblind Modes</h4>
          <div class="a11y-btn-group">
            <button class="a11y-opt-btn a11y-filter-btn active" data-filter="none">Default Vision</button>
            <button class="a11y-opt-btn a11y-filter-btn" data-filter="protanopia">Protanopia (Red-Blind)</button>
            <button class="a11y-opt-btn a11y-filter-btn" data-filter="deuteranopia">Deuteranopia (Green-Blind)</button>
            <button class="a11y-opt-btn a11y-filter-btn" data-filter="tritanopia">Tritanopia (Blue-Blind)</button>
            <button class="a11y-opt-btn a11y-filter-btn" data-filter="achromatopsia">Monochrome / Grayscale</button>
          </div>
        </div>

        <!-- 3. High Contrast Themes -->
        <div class="a11y-section">
          <h4><i class="fa-solid fa-circle-half-stroke"></i> High Contrast Modes (WCAG AAA)</h4>
          <div class="a11y-btn-group">
            <button class="a11y-opt-btn a11y-contrast-btn active" data-contrast="default">System Default</button>
            <button class="a11y-opt-btn a11y-contrast-btn" data-contrast="dark">High Contrast Dark</button>
            <button class="a11y-opt-btn a11y-contrast-btn" data-contrast="light">High Contrast Light</button>
          </div>
        </div>

        <!-- 4. Typography & Font Scaling -->
        <div class="a11y-section">
          <h4><i class="fa-solid fa-text-height"></i> Text Size & Readability</h4>
          <div class="a11y-btn-group" style="margin-bottom: 10px;">
            <button class="a11y-opt-btn a11y-scale-btn active" data-scale="100">Normal 100%</button>
            <button class="a11y-opt-btn a11y-scale-btn" data-scale="115">Large 115%</button>
            <button class="a11y-opt-btn a11y-scale-btn" data-scale="130">X-Large 130%</button>
            <button class="a11y-opt-btn a11y-scale-btn" data-scale="150">Jumbo 150%</button>
          </div>
          <div class="a11y-btn-group">
            <button class="a11y-opt-btn" id="toggle-dyslexia"><i class="fa-solid fa-font"></i> Dyslexia-Friendly Font</button>
            <button class="a11y-opt-btn" id="toggle-reading-ruler"><i class="fa-solid fa-ruler-horizontal"></i> Reading Guide Ruler</button>
          </div>
        </div>

        <!-- 5. Keyboard Navigation Guide -->
        <div class="a11y-section" style="border-bottom: none;">
          <h4><i class="fa-solid fa-keyboard"></i> Quick Keyboard Shortcuts</h4>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px; font-size: 0.78rem;">
            <div style="background: rgba(255,255,255,0.03); padding: 6px 10px; border-radius: 6px;">
              <kbd style="background: #334155; padding: 2px 6px; border-radius: 4px;">Alt + A</kbd> A11y Menu
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 6px 10px; border-radius: 6px;">
              <kbd style="background: #334155; padding: 2px 6px; border-radius: 4px;">Alt + S</kbd> Read Aloud
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 6px 10px; border-radius: 6px;">
              <kbd style="background: #334155; padding: 2px 6px; border-radius: 4px;">Alt + 1</kbd> Diagnostic
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 6px 10px; border-radius: 6px;">
              <kbd style="background: #334155; padding: 2px 6px; border-radius: 4px;">Alt + 2</kbd> Preventive
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 6px 10px; border-radius: 6px;">
              <kbd style="background: #334155; padding: 2px 6px; border-radius: 4px;">Alt + 3</kbd> Monitoring
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 6px 10px; border-radius: 6px;">
              <kbd style="background: #334155; padding: 2px 6px; border-radius: 4px;">Alt + 4</kbd> Workflows
            </div>
            <div style="background: rgba(255,255,255,0.03); padding: 6px 10px; border-radius: 6px;">
              <kbd style="background: #334155; padding: 2px 6px; border-radius: 4px;">Alt + 5</kbd> Wellbeing
            </div>
          </div>
        </div>

        <div style="margin-top: 20px; text-align: right;">
          <button class="btn btn-secondary" id="a11y-reset-all" type="button" style="font-size: 0.8rem; padding: 8px 16px;">
            <i class="fa-solid fa-arrow-rotate-left"></i> Reset to Default
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);
  }

  // State Management
  const state = {
    filter: localStorage.getItem('a11y_filter') || 'none',
    contrast: localStorage.getItem('a11y_contrast') || 'default',
    scale: localStorage.getItem('a11y_scale') || '100',
    dyslexia: localStorage.getItem('a11y_dyslexia') === 'true',
    ruler: false,
    ttsSpeed: 1.0,
    isSpeaking: false
  };

  function applyPreferences() {
    const body = document.body;

    // 1. Color Filters
    body.classList.remove('protanopia-filter', 'deuteranopia-filter', 'tritanopia-filter', 'achromatopsia-filter');
    if (state.filter !== 'none') {
      body.classList.add(`${state.filter}-filter`);
    }

    // 2. High Contrast
    body.classList.remove('high-contrast-dark', 'high-contrast-light');
    if (state.contrast === 'dark') body.classList.add('high-contrast-dark');
    if (state.contrast === 'light') body.classList.add('high-contrast-light');

    // 3. Text Scale
    body.classList.remove('text-scale-115', 'text-scale-130', 'text-scale-150');
    if (state.scale !== '100') {
      body.classList.add(`text-scale-${state.scale}`);
    }

    // 4. Dyslexia Font
    if (state.dyslexia) {
      body.classList.add('dyslexia-font');
    } else {
      body.classList.remove('dyslexia-font');
    }

    // Sync button active states in modal
    document.querySelectorAll('.a11y-filter-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.filter === state.filter);
    });
    document.querySelectorAll('.a11y-contrast-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.contrast === state.contrast);
    });
    document.querySelectorAll('.a11y-scale-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.scale === state.scale);
    });
    const dyslexiaBtn = document.getElementById('toggle-dyslexia');
    if (dyslexiaBtn) dyslexiaBtn.classList.toggle('active', state.dyslexia);
  }

  // Text To Speech Screen Reader
  function speakText(text) {
    if (!('speechSynthesis' in window)) {
      alert("Text-to-speech is not supported by your browser.");
      return;
    }
    window.speechSynthesis.cancel();
    if (!text || text.trim() === '') return;

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = state.ttsSpeed;
    utterance.pitch = 1.0;

    // Detect language or match document lang
    const lang = document.documentElement.lang || 'en-US';
    utterance.lang = lang;

    utterance.onstart = () => {
      state.isSpeaking = true;
      const readBtn = document.getElementById('tts-read-page');
      if (readBtn) readBtn.classList.add('speech-active');
    };
    utterance.onend = utterance.onerror = () => {
      state.isSpeaking = false;
      const readBtn = document.getElementById('tts-read-page');
      if (readBtn) readBtn.classList.remove('speech-active');
    };

    window.speechSynthesis.speak(utterance);
  }

  function readCurrentPageContent() {
    // Read heading, clinical explanations, or main text
    let textToRead = "";
    const mainHeading = document.querySelector('h1, h2');
    if (mainHeading) textToRead += mainHeading.innerText + ". ";

    // Read clinical explanation if available
    const explanationEl = document.getElementById('clinical-explanation-text') || document.querySelector('.panel-subtext');
    if (explanationEl) textToRead += explanationEl.innerText + ". ";

    // Read diagnosis label if present
    const labelEl = document.getElementById('stat-label');
    if (labelEl && labelEl.innerText) {
      textToRead += "Diagnostic assessment indicates: " + labelEl.innerText + ". ";
    }

    if (!textToRead.trim()) {
      textToRead = document.body.innerText.slice(0, 500);
    }

    speakText(textToRead);
  }

  function bindEvents() {
    const triggerBtn = document.getElementById('a11y-trigger-btn');
    const modal = document.getElementById('a11y-modal');
    const closeBtn = document.getElementById('a11y-close-btn');

    if (triggerBtn && modal) {
      triggerBtn.addEventListener('click', () => modal.classList.add('open'));
      if (closeBtn) closeBtn.addEventListener('click', () => modal.classList.remove('open'));
      modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('open');
      });
    }

    // Colorblind Filters
    document.querySelectorAll('.a11y-filter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        state.filter = btn.dataset.filter;
        localStorage.setItem('a11y_filter', state.filter);
        applyPreferences();
      });
    });

    // Contrast
    document.querySelectorAll('.a11y-contrast-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        state.contrast = btn.dataset.contrast;
        localStorage.setItem('a11y_contrast', state.contrast);
        applyPreferences();
      });
    });

    // Font Scale
    document.querySelectorAll('.a11y-scale-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        state.scale = btn.dataset.scale;
        localStorage.setItem('a11y_scale', state.scale);
        applyPreferences();
      });
    });

    // Dyslexia
    const dyslexiaBtn = document.getElementById('toggle-dyslexia');
    if (dyslexiaBtn) {
      dyslexiaBtn.addEventListener('click', () => {
        state.dyslexia = !state.dyslexia;
        localStorage.setItem('a11y_dyslexia', state.dyslexia);
        applyPreferences();
      });
    }

    // Reading Ruler
    const rulerBtn = document.getElementById('toggle-reading-ruler');
    const rulerEl = document.getElementById('a11y-reading-ruler');
    if (rulerBtn && rulerEl) {
      rulerBtn.addEventListener('click', () => {
        state.ruler = !state.ruler;
        rulerEl.style.display = state.ruler ? 'block' : 'none';
        rulerBtn.classList.toggle('active', state.ruler);
      });

      document.addEventListener('mousemove', (e) => {
        if (state.ruler) {
          rulerEl.style.top = (e.clientY - 18) + 'px';
        }
      });
    }

    // Screen Reader Buttons
    const readPageBtn = document.getElementById('tts-read-page');
    if (readPageBtn) readPageBtn.addEventListener('click', readCurrentPageContent);

    const pauseBtn = document.getElementById('tts-pause');
    if (pauseBtn) {
      pauseBtn.addEventListener('click', () => {
        if ('speechSynthesis' in window) {
          if (window.speechSynthesis.paused) {
            window.speechSynthesis.resume();
          } else {
            window.speechSynthesis.pause();
          }
        }
      });
    }

    const stopBtn = document.getElementById('tts-stop');
    if (stopBtn) {
      stopBtn.addEventListener('click', () => {
        if ('speechSynthesis' in window) window.speechSynthesis.cancel();
        if (readPageBtn) readPageBtn.classList.remove('speech-active');
      });
    }

    // Speech Speed
    document.querySelectorAll('.tts-speed').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tts-speed').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.ttsSpeed = parseFloat(btn.dataset.speed);
      });
    });

    // Reset All
    const resetBtn = document.getElementById('a11y-reset-all');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        state.filter = 'none';
        state.contrast = 'default';
        state.scale = '100';
        state.dyslexia = false;
        state.ruler = false;
        if (rulerEl) rulerEl.style.display = 'none';
        localStorage.removeItem('a11y_filter');
        localStorage.removeItem('a11y_contrast');
        localStorage.removeItem('a11y_scale');
        localStorage.removeItem('a11y_dyslexia');
        if ('speechSynthesis' in window) window.speechSynthesis.cancel();
        applyPreferences();
      });
    }

    // Keyboard Shortcuts
    document.addEventListener('keydown', (e) => {
      if (e.altKey) {
        if (e.key.toLowerCase() === 'a') {
          e.preventDefault();
          modal.classList.toggle('open');
        } else if (e.key.toLowerCase() === 's') {
          e.preventDefault();
          readCurrentPageContent();
        } else if (e.key === '1') {
          e.preventDefault(); window.location.href = '/';
        } else if (e.key === '2') {
          e.preventDefault(); window.location.href = '/preventive';
        } else if (e.key === '3') {
          e.preventDefault(); window.location.href = '/monitoring';
        } else if (e.key === '4') {
          e.preventDefault(); window.location.href = '/workflows';
        } else if (e.key === '5') {
          e.preventDefault(); window.location.href = '/wellbeing';
        } else if (e.key === '6') {
          e.preventDefault(); window.location.href = '/dashboard';
        }
      }
    });

    // Wire up any .speak-text-btn on the page
    document.addEventListener('click', (e) => {
      const btn = e.target.closest('.speak-text-btn');
      if (btn) {
        const textTarget = btn.dataset.text || btn.getAttribute('aria-label');
        if (textTarget) speakText(textTarget);
      }
    // Universal Theme Toggle Wiring
    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn && !themeBtn.dataset.wired) {
      themeBtn.dataset.wired = 'true';
      const updateThemeUI = (isLight) => {
        themeBtn.innerHTML = isLight ? '<i class="fa-solid fa-sun"></i> <span>Light</span>' : '<i class="fa-solid fa-moon"></i> <span>Dark</span>';
      };
      const savedTheme = localStorage.getItem('appTheme');
      if (savedTheme === 'light') {
        document.body.classList.add('light-mode');
        updateThemeUI(true);
      } else {
        updateThemeUI(false);
      }
      themeBtn.addEventListener('click', () => {
        const isLight = document.body.classList.toggle('light-mode');
        updateThemeUI(isLight);
        localStorage.setItem('appTheme', isLight ? 'light' : 'dark');
      });
    }
  }

  // Initialization
  document.addEventListener('DOMContentLoaded', () => {
    injectSVGFilters();
    injectA11yUI();
    applyPreferences();
    bindEvents();
  });
})();
