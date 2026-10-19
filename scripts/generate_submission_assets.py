import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

DOCS_DIR = os.path.abspath("docs")
os.makedirs(DOCS_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# 1. CREATE ARCHITECTURE DIAGRAM (PNG + PDF)
# -----------------------------------------------------------------------------
def generate_architecture_diagram():
    fig, ax = plt.subplots(figsize=(16, 9), dpi=300)
    fig.patch.set_facecolor('#0B1329')
    ax.set_facecolor('#0B1329')
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Title & Header
    ax.text(50, 96, "AI CANCER DETECTION SYSTEM — END-TO-END CLINICAL ARCHITECTURE",
            ha='center', va='center', color='#FFFFFF', fontsize=18, fontweight='bold', fontfamily='sans-serif')
    ax.text(50, 92.5, "Hospital-Grade Multi-Organ AI Triage, Explainable XAI (Grad-CAM), & Multi-Agent Tumor Board",
            ha='center', va='center', color='#38BDF8', fontsize=12, fontfamily='sans-serif')
    ax.text(50, 89.5, "Team: kavuriruthikachowdary | Prasad V Potluri Siddhartha Institute of Technology",
            ha='center', va='center', color='#94A3B8', fontsize=10, fontfamily='sans-serif')

    # Helper function for stylish boxes
    def draw_layer_box(x, y, w, h, title, subtitle, bg_color, border_color):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=1,rounding_size=1.5",
                                     facecolor=bg_color, edgecolor=border_color, linewidth=2)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h - 3, title, ha='center', va='center', color='#FFFFFF', fontsize=11, fontweight='bold')
        if subtitle:
            ax.text(x + w/2, y + h - 6, subtitle, ha='center', va='center', color='#94A3B8', fontsize=8.5)

    def draw_component_card(x, y, w, h, title, items, bg_color, border_color):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.8,rounding_size=1",
                                     facecolor=bg_color, edgecolor=border_color, linewidth=1.5)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h - 2.8, title, ha='center', va='center', color='#38BDF8', fontsize=9.5, fontweight='bold')
        for i, item in enumerate(items):
            ax.text(x + 1.5, y + h - 5.5 - (i * 2.8), f"• {item}", ha='left', va='center', color='#E2E8F0', fontsize=8)

    # 4 Main Columns / Stages
    # Column 1: Client & Clinical Gateways (x: 2 to 24)
    draw_layer_box(2, 6, 22, 79, "1. CLINICAL CLIENT GATEWAYS", "Role-Based Access & Ingestion", "#131C35", "#1E293B")
    draw_component_card(3.5, 63, 19, 18, "Physician & Staff Workstation", ["Doctor / Radiologist Login", "PACS DICOM Multi-Slice Viewer", "Clinical Diagnostic Intake", "Interactive XAI Inspection"], "#1E293B", "#3B82F6")
    draw_component_card(3.5, 41, 19, 19, "Patient Health Portal", ["Patient Self-Service Access", "Plain-Language Diagnosis", "Stage Nutrition & Remedies", "Interactive Care Team Chat"], "#1E293B", "#10B981")
    draw_component_card(3.5, 10, 19, 28, "Global Accessibility & UI", ["DOM TreeWalker i18n Engine", "11 Languages (En, Hi, Te, Ta...)", "Glassmorphic Responsive UI", "HIPAA Consent & Safety Alerts"], "#1E293B", "#8B5CF6")

    # Column 2: Application & Orchestration Backend (x: 27 to 49)
    draw_layer_box(27, 6, 22, 79, "2. CORE APPLICATION ENGINE", "Flask 3.0 & Clinical Blueprints", "#131C35", "#1E293B")
    draw_component_card(28.5, 63, 19, 18, "Flask Web Service & REST API", ["app.py Routing & Middlewares", "RBAC Authentication Sessions", "Secure DICOM/Image Ingest", "Synchronous Triage Response"], "#1E293B", "#EC4899")
    draw_component_card(28.5, 41, 19, 19, "Clinical Intelligence Suite", ["hospital_core.py EMR Tracking", "health_suite.py Care Pathways", "health_guidance.py Staging", "Stage 0 to Stage IV Regimens"], "#1E293B", "#F59E0B")
    draw_component_card(28.5, 10, 19, 28, "Integration & Reporting", ["pdf_generator.py ReportLab", "email_service.py Patient Alerts", "google_drive_service.py Backup", "HIPAA Immutable Audit Trail"], "#1E293B", "#06B6D4")

    # Column 3: AI Inference & Explainability (x: 52 to 74)
    draw_layer_box(52, 6, 22, 79, "3. DEEP LEARNING & XAI", "TensorFlow / Keras 2.18 Ensembles", "#131C35", "#1E293B")
    draw_component_card(53.5, 63, 19, 18, "EfficientNet-B0 Ensembles", ["224x224x3 Input Normalization", "Global Average Pooling 2D", "Dense(256) + Dropout(0.4)", "Softmax Multi-Class Scoring"], "#1E293B", "#EF4444")
    draw_component_card(53.5, 41, 19, 19, "Multi-Organ Detection Models", ["Brain MRI (Glioma/Meningioma)", "Breast US (Benign/Malignant)", "Lung CT/X-Ray (Pulmonary)", "Skin Dermoscopy (Melanoma)"], "#1E293B", "#14B8A6")
    draw_component_card(53.5, 10, 19, 28, "Explainability (Grad-CAM)", ["Gradient-Class Activation Mapping", "Convolutional Feature Extraction", "Heatmap Overlay & Thresholding", "Visual Sanity & Trust Checks"], "#1E293B", "#6366F1")

    # Column 4: Multi-Agent Consensus & Output (x: 77 to 98)
    draw_layer_box(77, 6, 21, 79, "4. MULTI-AGENT TUMOR BOARD", "LLM Consensus & Diagnostics", "#131C35", "#1E293B")
    draw_component_card(78.5, 63, 18, 18, "Diagnostic Radiologist", ["Radiological Density Scan", "Margin Definition & Spiculation", "Anatomical Slice Landmarks", "Calcification Analysis"], "#1E293B", "#38BDF8")
    draw_component_card(78.5, 41, 18, 19, "Medical Oncologist", ["TNM Staging Assessment", "Systemic Regimen Suggestions", "Biomarker & Genomic Advice", "Surveillance Cadence"], "#1E293B", "#F97316")
    draw_component_card(78.5, 10, 18, 28, "Surgical Oncologist", ["Resectability Assessment", "Operative Clearance & Margins", "Biopsy & Lymph Node Protocol", "Digital Report Certification"], "#1E293B", "#A855F7")

    # Connectors / Arrows between layers
    arrow_props = dict(arrowstyle="->,head_width=0.4,head_length=0.6", color="#38BDF8", lw=2)
    ax.annotate("", xy=(27, 72), xytext=(24, 72), arrowprops=arrow_props)
    ax.annotate("", xy=(27, 50), xytext=(24, 50), arrowprops=arrow_props)
    ax.annotate("", xy=(52, 72), xytext=(49, 72), arrowprops=arrow_props)
    ax.annotate("", xy=(52, 50), xytext=(49, 50), arrowprops=arrow_props)
    ax.annotate("", xy=(77, 72), xytext=(74, 72), arrowprops=arrow_props)
    ax.annotate("", xy=(77, 50), xytext=(74, 50), arrowprops=arrow_props)

    plt.tight_layout()
    png_path = os.path.join(DOCS_DIR, "Architecture_Diagram.png")
    pdf_path = os.path.join(DOCS_DIR, "Architecture_Diagram.pdf")
    plt.savefig(png_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.savefig(pdf_path, facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"Generated: {png_path}")
    print(f"Generated: {pdf_path}")

# -----------------------------------------------------------------------------
# 2. CREATE ARCHITECTURE DIAGRAM PPTX
# -----------------------------------------------------------------------------
def generate_architecture_pptx():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)

    # Background
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = RGBColor(11, 19, 41)
    bg.line.fill.background()

    # Insert generated image
    png_path = os.path.join(DOCS_DIR, "Architecture_Diagram.png")
    if os.path.exists(png_path):
        slide.shapes.add_picture(png_path, Inches(0.5), Inches(0.4), width=Inches(12.333))

    pptx_path = os.path.join(DOCS_DIR, "Architecture_Diagram.pptx")
    prs.save(pptx_path)
    print(f"Generated: {pptx_path}")

# -----------------------------------------------------------------------------
# 3. CREATE FULL PRESENTATION PPTX (12 SLIDES)
# -----------------------------------------------------------------------------
def generate_project_presentation_pptx():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    DARK_BG = RGBColor(11, 19, 41)
    CARD_BG = RGBColor(22, 33, 62)
    ACCENT_BLUE = RGBColor(56, 189, 248)
    TEXT_WHITE = RGBColor(255, 255, 255)
    TEXT_MUTED = RGBColor(148, 163, 184)
    ACCENT_GREEN = RGBColor(52, 211, 153)

    slides_data = [
        {
            "title": "AI CANCER DETECTION SYSTEM (MEDISCAN AI)",
            "subtitle": "Hospital Clinical Multi-Organ Cancer Detection, Diagnostic Triage & Multi-Agent Tumor Board",
            "type": "title",
            "content": [
                ("Team Name", "kavuriruthikachowdary"),
                ("Team Leader", "Kavuri Ruthika"),
                ("Team Members", "Jonnalagadda Lakshman Chowdary, Ande Likhith"),
                ("College", "Prasad V Potluri Siddhartha Institute of Technology"),
                ("Demo Video", "https://youtu.be/NgW5yDUKYds?si=jAp0tfBpSQ2vhutp"),
                ("Open-Source License", "MIT License")
            ]
        },
        {
            "title": "Executive Summary & Clinical Motivation",
            "subtitle": "Bridging Diagnostic Latency with AI Precision in Hospital Oncology",
            "type": "bullets",
            "cards": [
                {
                    "title": "The Global Challenge",
                    "items": [
                        "Over 19.3 million new cancer cases occur annually worldwide.",
                        "Radiologist shortages lead to backlogs, delayed staging, and diagnosis burnout.",
                        "Early detection significantly increases 5-year survival rates by up to 90%."
                    ]
                },
                {
                    "title": "Our Innovation: MediScan AI",
                    "items": [
                        "Real-time multi-organ detection: Brain MRI, Breast Ultrasound, Lung CT, Cutaneous Skin.",
                        "Explainable AI (XAI) using Grad-CAM heatmaps for transparent clinical verification.",
                        "Multi-Agent AI Tumor Board consensus simulating cross-specialty clinical review."
                    ]
                },
                {
                    "title": "Patient & Clinical Impact",
                    "items": [
                        "Reduces radiological preliminary screening time from hours to under 2 seconds.",
                        "11-language translation engine eliminates communication barriers for patients.",
                        "Automated clinical staging, nutrition protocols, and digital diagnostic reports."
                    ]
                }
            ]
        },
        {
            "title": "Problem Statement & Clinical Need",
            "subtitle": "Critical Gaps in Current Healthcare Imaging Workflows",
            "type": "bullets",
            "cards": [
                {
                    "title": "Diagnostic Bottlenecks",
                    "items": [
                        "High scan volumes create critical turnaround delays for acute oncology patients.",
                        "Subtle micro-calcifications and early malignant lesions are easily overlooked in fatigue."
                    ]
                },
                {
                    "title": "The AI 'Black-Box' Trust Deficit",
                    "items": [
                        "Traditional deep neural networks provide raw classifications without spatial rationale.",
                        "Clinicians cannot ethically or legally act on unverified AI predictions without explainability."
                    ]
                },
                {
                    "title": "Fragmented Tumor Board Care",
                    "items": [
                        "Coordinating physical multi-disciplinary tumor boards takes weeks.",
                        "Patients often receive complex medical jargon without supportive lifestyle or diet guidance."
                    ]
                }
            ]
        },
        {
            "title": "Healthcare Use Cases & Clinical Pathways",
            "subtitle": "End-to-End Decision Support Across 4 Primary Cancer Modalities",
            "type": "bullets",
            "cards": [
                {
                    "title": "Brain MRI Triage",
                    "items": [
                        "Differentiates Glioma, Meningioma, and Pituitary adenomas from healthy axial slices.",
                        "Provides mass margin localization to support neurosurgical planning."
                    ]
                },
                {
                    "title": "Breast Sonography / Mammography",
                    "items": [
                        "Evaluates lesion borders, acoustic shadows, and tissue density (Benign vs Malignant).",
                        "Aligns with BI-RADS assessment protocols for biopsy recommendation."
                    ]
                },
                {
                    "title": "Thoracic CT & Cutaneous Dermoscopy",
                    "items": [
                        "Detects Pulmonary Adenocarcinoma, Squamous Cell, and Large Cell carcinomas.",
                        "Screens dermoscopic lesions for malignant melanoma vs benign melanocytic nevi."
                    ]
                }
            ]
        },
        {
            "title": "System Architecture Overview",
            "subtitle": "Modular, Secure, Multi-Tier Hospital Architecture",
            "type": "bullets",
            "cards": [
                {
                    "title": "Tier 1: Clinical Gateways",
                    "items": [
                        "Dual Gateway: Physician/Staff Workstation and Patient Self-Service Portal.",
                        "PACS Workstation for multi-slice DICOM inspection and radiological windowing.",
                        "Client-side 11-language TreeWalker engine for seamless multilingual localization."
                    ]
                },
                {
                    "title": "Tier 2: Backend Application",
                    "items": [
                        "Flask 3.0 REST application server with secure session token authentication.",
                        "EMR longitudinal record tracking, appointment scheduler, and HIPAA audit trail.",
                        "ReportLab clinical PDF generator and automated patient alert dispatcher."
                    ]
                },
                {
                    "title": "Tier 3: AI & XAI Pipeline",
                    "items": [
                        "TensorFlow 2.18 / Keras deep neural ensemble pipeline.",
                        "Grad-CAM visual heatmap generator computed directly on feature activation layers.",
                        "Multi-Agent LLM simulation: Radiologist, Medical Oncologist, Surgical Oncologist."
                    ]
                }
            ]
        },
        {
            "title": "Deep Learning Models & Framework Details",
            "subtitle": "State-of-the-Art Convolutional Neural Ensembles with EfficientNet-B0",
            "type": "bullets",
            "cards": [
                {
                    "title": "Backbone & Transfer Learning",
                    "items": [
                        "Pre-trained EfficientNet-B0 backbone utilizing ImageNet feature representations.",
                        "Compound scaling coefficients optimized for high-resolution medical imaging.",
                        "Custom classification head: GlobalAveragePooling2D, Dense(256), Dropout(0.4)."
                    ]
                },
                {
                    "title": "Training & Optimization",
                    "items": [
                        "Input dimensions: 224x224x3 with modality-specific normalization.",
                        "Loss: Categorical Cross-Entropy, Optimizer: Adam (lr=1e-4 with ReduceLROnPlateau).",
                        "Data Augmentation: Random rotations, zooms, shifts, and horizontal flips."
                    ]
                },
                {
                    "title": "Evaluation Callbacks",
                    "items": [
                        "ModelCheckpoint tracking validation accuracy to store best weight checkpoints.",
                        "EarlyStopping with patience=3 to prevent overfitting on clinical training subsets."
                    ]
                }
            ]
        },
        {
            "title": "Explainable AI (XAI) & Grad-CAM Heatmaps",
            "subtitle": "Transparent Clinical Rationale Behind Neural Network Predictions",
            "type": "bullets",
            "cards": [
                {
                    "title": "Mathematical Foundation",
                    "items": [
                        "Computes gradients of target class score with respect to feature activation maps.",
                        "Weights each channel by its pooled gradient to capture spatial importance.",
                        "Applies ReLU activation to retain features that positively correlate with the diagnosis."
                    ]
                },
                {
                    "title": "Clinical Radiologist Benefit",
                    "items": [
                        "Validates whether AI is focusing on actual tumor mass vs scanner artifacts or bone.",
                        "Interactive side-by-side scan vs heatmap overlay gives immediate visual trust.",
                        "Identifies peripheral infiltrating borders for targeted surgical resection."
                    ]
                },
                {
                    "title": "HIPAA & Ethical Compliance",
                    "items": [
                        "Measures against algorithmic bias and false positive hallucination.",
                        "Provides auditable visual evidence attached directly to the patient's EMR record."
                    ]
                }
            ]
        },
        {
            "title": "Multi-Agent AI Tumor Board Simulation",
            "subtitle": "Simulated Multidisciplinary Team (MDT) Clinical Consensus",
            "type": "bullets",
            "cards": [
                {
                    "title": "Diagnostic Radiologist Agent",
                    "items": [
                        "Evaluates radiological density, margin circumscription, and calcifications.",
                        "Reports on lesion slice dimensions, surrounding edema, and anatomical displacement."
                    ]
                },
                {
                    "title": "Medical Oncologist Agent",
                    "items": [
                        "Determines estimated TNM clinical stage (Stage 0 to Stage IV).",
                        "Formulates systemic chemotherapy, immunotherapy, and targeted molecular therapies.",
                        "Establishes longitudinal follow-up intervals and surveillance imaging cadence."
                    ]
                },
                {
                    "title": "Surgical Oncologist Agent",
                    "items": [
                        "Assesses anatomical resectability and surgical clearance margins.",
                        "Formulates stereotactic biopsy, sentinel lymph node dissection, and operative clearance."
                    ]
                }
            ]
        },
        {
            "title": "Hospital Command Center & Role-Based Workflows",
            "subtitle": "Dual-Gateway Authentication & Comprehensive EMR Infrastructure",
            "type": "bullets",
            "cards": [
                {
                    "title": "Physician & Staff Gateway",
                    "items": [
                        "Role-Based Access Control (RBAC): Doctor, Radiologist, Oncologist, Surgeon, Nurse, Admin.",
                        "PACS DICOM workstation with window leveling, zoom, invert, and multi-slice navigation.",
                        "Digital diagnostic sign-off and instant certified PDF report export."
                    ]
                },
                {
                    "title": "Patient Health Portal",
                    "items": [
                        "Patient-friendly login with simple Medical Record Number (MRN).",
                        "Plain-English diagnostic summary explaining findings without alarming terminology.",
                        "Stage-specific dietary habits, supportive herbal remedies, and precautions to avoid."
                    ]
                },
                {
                    "title": "Audit & Telemetry",
                    "items": [
                        "Immutable HIPAA audit logging tracking every access, inference, and modification.",
                        "Real-time operational telemetry monitoring system latency and throughput."
                    ]
                }
            ]
        },
        {
            "title": "Global Accessibility & Multilingual Inclusivity",
            "subtitle": "Democratizing Advanced Oncology Guidance Across 11 Languages",
            "type": "bullets",
            "cards": [
                {
                    "title": "Lossless Client-Side Translation",
                    "items": [
                        "Custom DOM TextNode TreeWalker translates entire application in real time.",
                        "Preserves dynamic medical values, numeric measurements, and form inputs flawlessly.",
                        "Supports right-to-left (RTL) formatting automatically for Arabic."
                    ]
                },
                {
                    "title": "Supported Languages",
                    "items": [
                        "English, Hindi, Telugu, Tamil, Kannada, Malayalam, Bengali, Spanish, French, German, Arabic.",
                        "Enables rural and non-English speaking patients to understand their diagnosis clearly."
                    ]
                },
                {
                    "title": "Health Literacy Impact",
                    "items": [
                        "Empowers patients and families with localized stage-specific lifestyle guidance.",
                        "Reduces miscommunication in treatment compliance and follow-up adherence."
                    ]
                }
            ]
        },
        {
            "title": "Project Outcomes, Results & Validation",
            "subtitle": "Quantitative Performance & Clinical Validation Summary",
            "type": "bullets",
            "cards": [
                {
                    "title": "Inference Speed & Efficiency",
                    "items": [
                        "Sub-2 second end-to-end response time for multi-organ image classification & Grad-CAM.",
                        "Lightweight model footprint (~21 MB per model) deployable on standard hospital hardware."
                    ]
                },
                {
                    "title": "Classification Robustness",
                    "items": [
                        "High diagnostic precision across Brain MRI, Breast Ultrasound, Lung CT, and Dermoscopy.",
                        "Robust generalization achieved via aggressive data augmentation and transfer learning."
                    ]
                },
                {
                    "title": "Deliverables Summary",
                    "items": [
                        "Fully working web application running on Flask 3.0 with PACS workstation.",
                        "Unlisted 15-20 min comprehensive video demonstration on YouTube.",
                        "Publicly accessible Architecture Diagram and Presentation files in PDF/PPT format."
                    ]
                }
            ]
        },
        {
            "title": "Team Details, Acknowledgements & License",
            "subtitle": "Open-Source Healthcare Innovation Under MIT License",
            "type": "bullets",
            "cards": [
                {
                    "title": "Project Team",
                    "items": [
                        "Team Name: kavuriruthikachowdary",
                        "Team Leader: Kavuri Ruthika",
                        "Team Members: Jonnalagadda Lakshman Chowdary, Ande Likhith",
                        "Institution: Prasad V Potluri Siddhartha Institute of Technology"
                    ]
                },
                {
                    "title": "Project Links",
                    "items": [
                        "Demo Video: https://youtu.be/NgW5yDUKYds?si=jAp0tfBpSQ2vhutp",
                        "GitHub Repo: https://github.com/LakshmanChowdary2005/AI-Cancer-Detection-System",
                        "Architecture Diagram: docs/Architecture_Diagram.pdf",
                        "Project Presentation: docs/AI_Cancer_Detection_System_Presentation.pdf"
                    ]
                },
                {
                    "title": "Open-Source License",
                    "items": [
                        "Released under the MIT License.",
                        "Open for clinical research, non-commercial benchmarking, and academic collaboration.",
                        "Clinical decision-support disclaimer: Intended to augment certified medical professionals."
                    ]
                }
            ]
        }
    ]

    for s_idx, data in enumerate(slides_data):
        slide = prs.slides.add_slide(blank_layout)

        # Background
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = DARK_BG
        bg.line.fill.background()

        if data.get("type") == "title":
            # Title Slide
            tb = slide.shapes.add_textbox(Inches(1.0), Inches(1.2), Inches(11.333), Inches(2.2))
            tf = tb.text_frame
            tf.word_wrap = True
            
            p = tf.paragraphs[0]
            p.text = data["title"]
            p.font.size = Pt(36)
            p.font.bold = True
            p.font.color.rgb = ACCENT_BLUE
            p.alignment = PP_ALIGN.CENTER

            p2 = tf.add_paragraph()
            p2.text = data["subtitle"]
            p2.font.size = Pt(16)
            p2.font.color.rgb = TEXT_WHITE
            p2.alignment = PP_ALIGN.CENTER

            # Team Details Card
            card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.2), Inches(3.6), Inches(8.933), Inches(3.2))
            card.fill.solid()
            card.fill.fore_color.rgb = CARD_BG
            card.line.color.rgb = ACCENT_BLUE
            card.line.width = Pt(1.5)

            ctb = slide.shapes.add_textbox(Inches(2.5), Inches(3.8), Inches(8.333), Inches(2.8))
            ctf = ctb.text_frame
            ctf.word_wrap = True

            for idx, (label, val) in enumerate(data["content"]):
                cp = ctf.add_paragraph() if idx > 0 else ctf.paragraphs[0]
                run1 = cp.add_run()
                run1.text = f"{label}: "
                run1.font.bold = True
                run1.font.size = Pt(14)
                run1.font.color.rgb = ACCENT_BLUE

                run2 = cp.add_run()
                run2.text = val
                run2.font.size = Pt(14)
                run2.font.color.rgb = TEXT_WHITE
        else:
            # Header
            tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.733), Inches(1.2))
            tf = tb.text_frame
            tf.word_wrap = True
            
            p = tf.paragraphs[0]
            p.text = data["title"]
            p.font.size = Pt(24)
            p.font.bold = True
            p.font.color.rgb = ACCENT_BLUE

            p2 = tf.add_paragraph()
            p2.text = data["subtitle"]
            p2.font.size = Pt(13)
            p2.font.color.rgb = TEXT_MUTED

            # 3 Cards Layout
            card_w = Inches(3.7)
            card_h = Inches(5.0)
            card_y = Inches(1.8)
            card_xs = [Inches(0.8), Inches(4.8), Inches(8.8)]

            for c_idx, card_data in enumerate(data.get("cards", [])):
                cx = card_xs[c_idx]
                box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, card_y, card_w, card_h)
                box.fill.solid()
                box.fill.fore_color.rgb = CARD_BG
                box.line.color.rgb = ACCENT_BLUE if c_idx == 1 else RGBColor(51, 65, 85)
                box.line.width = Pt(1.5)

                ctb = slide.shapes.add_textbox(cx + Inches(0.2), card_y + Inches(0.25), card_w - Inches(0.4), card_h - Inches(0.5))
                ctf = ctb.text_frame
                ctf.word_wrap = True

                title_p = ctf.paragraphs[0]
                title_p.text = card_data["title"]
                title_p.font.size = Pt(15)
                title_p.font.bold = True
                title_p.font.color.rgb = ACCENT_GREEN

                spacer_p = ctf.add_paragraph()
                spacer_p.text = ""
                spacer_p.font.size = Pt(6)

                for item in card_data["items"]:
                    ip = ctf.add_paragraph()
                    ip.text = f"• {item}"
                    ip.font.size = Pt(12)
                    ip.font.color.rgb = TEXT_WHITE
                    ip.space_after = Pt(8)

    pptx_path = os.path.join(DOCS_DIR, "AI_Cancer_Detection_System_Presentation.pptx")
    prs.save(pptx_path)
    print(f"Generated: {pptx_path}")

# -----------------------------------------------------------------------------
# 4. CREATE FULL PRESENTATION PDF (REPORTLAB)
# -----------------------------------------------------------------------------
def generate_project_presentation_pdf():
    pdf_path = os.path.join(DOCS_DIR, "AI_Cancer_Detection_System_Presentation.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=landscape(letter),
                            leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#0F172A'),
        alignment=1,
        spaceAfter=10
    )
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#3B82F6'),
        alignment=1,
        spaceAfter=20
    )
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=4
    )
    section_sub = ParagraphStyle(
        'SectionSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=15
    )
    card_title = ParagraphStyle(
        'CardTitle',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0284C7'),
        spaceAfter=6
    )
    body_text = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )

    story = []

    # Slide 1: Cover
    story.append(Spacer(1, 40))
    story.append(Paragraph("AI CANCER DETECTION SYSTEM (MEDISCAN AI)", title_style))
    story.append(Paragraph("Hospital Clinical Multi-Organ Cancer Detection, Diagnostic Triage & Multi-Agent Tumor Board", subtitle_style))
    story.append(Spacer(1, 20))

    meta_data = [
        [Paragraph("<b>Team Name:</b>", body_text), Paragraph("kavuriruthikachowdary", body_text)],
        [Paragraph("<b>Team Leader:</b>", body_text), Paragraph("Kavuri Ruthika", body_text)],
        [Paragraph("<b>Team Members:</b>", body_text), Paragraph("Jonnalagadda Lakshman Chowdary, Ande Likhith", body_text)],
        [Paragraph("<b>College / Institution:</b>", body_text), Paragraph("Prasad V Potluri Siddhartha Institute of Technology", body_text)],
        [Paragraph("<b>Project Demo Video:</b>", body_text), Paragraph("<a href='https://youtu.be/NgW5yDUKYds?si=jAp0tfBpSQ2vhutp' color='blue'>https://youtu.be/NgW5yDUKYds?si=jAp0tfBpSQ2vhutp</a>", body_text)],
        [Paragraph("<b>Open-Source License:</b>", body_text), Paragraph("MIT License (Publicly Available)", body_text)]
    ]
    t = Table(meta_data, colWidths=[180, 480])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#0284C7')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(t)
    story.append(PageBreak())

    # Pages 2-6: Content Pages with 3-column table
    pages_content = [
        {
            "title": "1. Problem Statement & Healthcare Use Case",
            "sub": "Addressing Diagnostic Turnaround Time, Clinical Burnout, and Diagnostic Confidence",
            "cols": [
                ("The Global Diagnostic Crisis", [
                    "<b>Delayed Detection:</b> High scan volume leads to specialist fatigue and prolonged reporting cycles.",
                    "<b>Specialist Shortage:</b> Severe shortage of expert radiologists in rural and tertiary healthcare setups.",
                    "<b>Early Intervention:</b> Catching tumors at Stage I elevates 5-year survival rates by up to 90%."
                ]),
                ("Healthcare Use Cases", [
                    "<b>Multi-Organ Triage:</b> Automated intake for Brain MRI, Breast Ultrasound, Lung CT, Cutaneous Skin.",
                    "<b>Emergency Prioritization:</b> Flagging acute suspected malignancies to the top of physician review worklists.",
                    "<b>PACS DICOM Viewer:</b> Native radiological slice viewing with brightness and contrast windowing."
                ]),
                ("Patient Empowerment", [
                    "<b>Plain-Language Summaries:</b> Translating complex radiologic jargon into patient-friendly findings.",
                    "<b>Stage-Specific Care:</b> Automatic guidance on clinical nutrition, lifestyle adaptations, and remedies.",
                    "<b>11-Language Access:</b> Ensuring native language comprehension for all patients."
                ])
            ]
        },
        {
            "title": "2. System Architecture & Technical Stack",
            "sub": "Modular Microservice-Ready Architecture with Role-Based Security",
            "cols": [
                ("Frontend & Workstation Tier", [
                    "<b>Glassmorphic UI:</b> Clean, high-contrast clinical interface built with HTML5, CSS3, JavaScript.",
                    "<b>Dual-Gateway Authentication:</b> Distinct portals for Physicians (/doctor/login) and Patients (/patient/login).",
                    "<b>PACS Multi-Slice Engine:</b> Smooth client-side inspection of radiological image sets."
                ]),
                ("Application & Business Tier", [
                    "<b>Flask 3.0 Framework:</b> High-throughput Python microservices handling REST API contracts.",
                    "<b>Longitudinal EMR:</b> Persistent patient registry, audit logs, and appointment management.",
                    "<b>Automated PDF Reporting:</b> Instant clinical diagnostic certificate compilation with ReportLab."
                ]),
                ("Deep Learning & AI Pipeline", [
                    "<b>TensorFlow 2.18 / Keras:</b> Optimized neural model inference in under 2 seconds.",
                    "<b>Grad-CAM Explainability:</b> Class activation maps pinpointing pathological regions.",
                    "<b>Multi-Agent Tumor Board:</b> Multi-disciplinary synthetic consultation (Radiology, Oncology, Surgery)."
                ])
            ]
        },
        {
            "title": "3. AI/ML Model Architectures & Explainability (Grad-CAM)",
            "sub": "High-Accuracy EfficientNet-B0 Convolutional Neural Ensembles with Spatial Transparency",
            "cols": [
                ("Neural Backbone Architecture", [
                    "<b>EfficientNet-B0 Base:</b> Compound-scaled CNN pre-trained on ImageNet for superior spatial transfer.",
                    "<b>Input Pipeline:</b> 224x224x3 tensors processed with modality-specific normalization.",
                    "<b>Classification Head:</b> GlobalAveragePooling2D + Dense(256, ReLU) + Dropout(0.4) + Softmax."
                ]),
                ("Explainable AI (Grad-CAM)", [
                    "<b>Gradient Flow:</b> Computes feature map gradients corresponding to predicted malignant class.",
                    "<b>Visual Verification:</b> Colorized heatmap overlay highlights tumor boundaries and microcalcifications.",
                    "<b>Clinical Trust:</b> Eradicates the 'black-box' dilemma, enabling physicians to verify AI focus."
                ]),
                ("Training & Optimization", [
                    "<b>Optimization:</b> Adam optimizer with ReduceLROnPlateau and EarlyStopping callbacks.",
                    "<b>Data Augmentation:</b> Random rotations (20 deg), zoom (0.2), shear, and horizontal flips.",
                    "<b>Loss Function:</b> Categorical cross-entropy with balanced class weighting."
                ])
            ]
        },
        {
            "title": "4. Multi-Agent AI Tumor Board & Hospital Workflows",
            "sub": "Synchronized Multi-Disciplinary Consensus Mimicking Hospital MDT Panels",
            "cols": [
                ("Diagnostic Radiologist Agent", [
                    "Analyzes radiological tissue density and lesion margins (spiculated vs circumscribed).",
                    "Examines slice depth, anatomical landmarks, and internal calcification patterns.",
                    "Provides structural imaging observations directly into the review worklist."
                ]),
                ("Medical Oncologist Agent", [
                    "Synthesizes staging assessment from Stage 0 (Benign/In-Situ) to Stage IV (Metastatic).",
                    "Formulates targeted systemic chemotherapy and immunotherapy protocols.",
                    "Establishes surveillance cadence and longitudinal tumor response monitoring."
                ]),
                ("Surgical Oncologist Agent", [
                    "Assesses resectability and surgical clearance margins.",
                    "Recommends biopsy approach (core needle vs excision) and lymph node mapping.",
                    "Completes final multidisciplinary consensus and sign-off."
                ])
            ]
        },
        {
            "title": "5. Project Outcomes, Validation & Compliance",
            "sub": "Sub-2s Latency, 11-Language Global Access, and Open-Source MIT Release",
            "cols": [
                ("Performance Outcomes", [
                    "<b>Real-Time Speed:</b> Inference and Grad-CAM generation complete in under 2 seconds.",
                    "<b>Modality Coverage:</b> Validated on Brain MRI, Breast Ultrasound, Lung CT, Cutaneous Skin.",
                    "<b>Compact Storage:</b> ~21 MB per model allows edge deployment in remote clinic workstations."
                ]),
                ("Regulatory & Security Standards", [
                    "<b>HIPAA Audit Logging:</b> Immutable event recording for logins, scans, and report downloads.",
                    "<b>Role-Based Access:</b> Granular permission separation for doctors, nurses, and patients.",
                    "<b>Clinical Disclaimer:</b> Clearly structured as assistive decision support, requiring clinician sign-off."
                ]),
                ("Public Deliverables", [
                    "<b>Demo Video:</b> 15-20 min comprehensive walkthrough uploaded to YouTube.",
                    "<b>Direct Artifacts:</b> Architecture Diagram and Slides in both PDF and PPT formats.",
                    "<b>Public Accessibility:</b> All links, files, and repositories open without extra permissions."
                ])
            ]
        }
    ]

    for p_data in pages_content:
        story.append(Paragraph(p_data["title"], section_title))
        story.append(Paragraph(p_data["sub"], section_sub))
        
        col_cells = []
        for col_title, items in p_data["cols"]:
            cell_elements = [
                Paragraph(col_title, card_title),
                Spacer(1, 4)
            ]
            for item in items:
                cell_elements.append(Paragraph(f"• {item}", body_text))
                cell_elements.append(Spacer(1, 4))
            col_cells.append(cell_elements)

        t_content = Table([col_cells], colWidths=[230, 230, 230])
        t_content.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(t_content)
        story.append(PageBreak())

    doc.build(story)
    print(f"Generated: {pdf_path}")

if __name__ == "__main__":
    generate_architecture_diagram()
    generate_architecture_pptx()
    generate_project_presentation_pptx()
    generate_project_presentation_pdf()
    print("All submission assets generated successfully!")
