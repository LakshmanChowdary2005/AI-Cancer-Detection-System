import os
import time
import io
from datetime import datetime
from utils.translator import get_translation

# ----------------------------------------------------------------------
# UNICODE FONT REGISTRATION
# ----------------------------------------------------------------------
# ReportLab's built-in Helvetica font only supports Latin-1 characters. When a
# report is generated for a non-Latin Unicode script (Telugu, Hindi/Devanagari,
# Tamil, Malayalam, Bengali, Kannada, Arabic), Helvetica cannot encode those
# code points, which makes doc.build() throw and forces the plain-text fallback.
#
# These helpers register the bundled Noto Sans fonts (per-script when available)
# so every supported language renders a valid, searchable Unicode PDF.

_FONT_REGISTERED = set()
_FONT_CACHE = {}


def _font_path(rel):
    """Return the absolute path to a bundled font file, or None if missing."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "fonts", rel) if rel else None


def _register_ttf(name, path):
    """Register a TTF font with ReportLab if it exists and hasn't been registered."""
    if not path or not os.path.exists(path):
        return False
    if name in _FONT_REGISTERED:
        return True
    try:
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfbase import pdfmetrics
        pdfmetrics.registerFont(TTFont(name, path))
        _FONT_REGISTERED.add(name)
        return True
    except Exception as e:
        print(f"Font registration failed for {name}: {e}")
        return False


# Map a language code to (regular_font_name, bold_font_name, ttf_regular_path, ttf_bold_path).
# The generic NotoSans-Regular/Bold covers Latin + Arabic + broad coverage; the
# per-script fonts give the best rendering for their native scripts.
_FONT_MAP = {
    "en": ("NotoSans", "NotoSans-Bold",
           "Noto_Sans/static/NotoSans-Regular.ttf", "Noto_Sans/static/NotoSans-Bold.ttf"),
    "es": ("NotoSans", "NotoSans-Bold",
           "Noto_Sans/static/NotoSans-Regular.ttf", "Noto_Sans/static/NotoSans-Bold.ttf"),
    "fr": ("NotoSans", "NotoSans-Bold",
           "Noto_Sans/static/NotoSans-Regular.ttf", "Noto_Sans/static/NotoSans-Bold.ttf"),
    "de": ("NotoSans", "NotoSans-Bold",
           "Noto_Sans/static/NotoSans-Regular.ttf", "Noto_Sans/static/NotoSans-Bold.ttf"),
    "hi": ("NotoDeva", "NotoDeva-Bold",
           "Noto_Sans_Devanagari/static/NotoSansDevanagari-Regular.ttf",
           "Noto_Sans_Devanagari/static/NotoSansDevanagari-Bold.ttf"),
    "te": ("NotoTelugu", "NotoTelugu-Bold",
           "Noto_Sans_Telugu/static/NotoSansTelugu-Regular.ttf",
           "Noto_Sans_Telugu/static/NotoSansTelugu-Bold.ttf"),
    "ta": ("NotoTamil", "NotoTamil-Bold",
           "Noto_Sans_Tamil/static/NotoSansTamil-Regular.ttf",
           "Noto_Sans_Tamil/static/NotoSansTamil-Bold.ttf"),
    "bn": ("NotoBengali", "NotoBengali-Bold",
           "Noto_Sans_Bengali/static/NotoSansBengali-Regular.ttf",
           "Noto_Sans_Bengali/static/NotoSansBengali-Bold.ttf"),
    "kn": ("NotoKannada", "NotoKannada-Bold",
           "Noto_Sans_Kannada/static/NotoSansKannada-Regular.ttf",
           "Noto_Sans_Kannada/static/NotoSansKannada-Bold.ttf"),
    "ml": ("NotoMalayalam", "NotoMalayalam-Bold",
           "Noto_Sans_Malayalam/static/NotoSansMalayalam-Regular.ttf",
           "Noto_Sans_Malayalam/static/NotoSansMalayalam-Bold.ttf"),
    "ar": ("NotoSans", "NotoSans-Bold",
           "Noto_Sans/static/NotoSans-Regular.ttf", "Noto_Sans/static/NotoSans-Bold.ttf"),
}


def get_report_fonts(lang_code):
    """Return (regular_font, bold_font) for a given language, registering the
    underlying TTF fonts with ReportLab on first use. Falls back to Helvetica
    if the TTF cannot be loaded."""
    lang = (lang_code or "en").lower().strip()
    reg, bold, reg_path, bold_path = _FONT_MAP.get(lang, _FONT_MAP["en"])

    # Try the language-specific fonts first.
    ok = _register_ttf(reg, _font_path(reg_path))
    if ok and bold_path:
        _register_ttf(bold, _font_path(bold_path))

    if ok:
        bold_ok = bold in _FONT_REGISTERED
        return (reg, bold if bold_ok else reg)

    # Fallback: register/broad Noto Sans for the language.
    g_reg, g_bold, g_reg_path, g_bold_path = _FONT_MAP["en"]
    g_ok = _register_ttf(g_reg, _font_path(g_reg_path))
    if g_ok and g_bold_path:
        _register_ttf(g_bold, _font_path(g_bold_path))
    if g_ok:
        return (g_reg, g_bold if g_bold in _FONT_REGISTERED else g_reg)

    # Last resort: Helvetica built-ins.
    return ("Helvetica", "Helvetica-Bold")

def generate_qr_image(qr_token):
    """Generate a QR code PNG (as bytes) encoding the report URL.
    Returns a BytesIO object with the PNG, or None on failure.
    """
    try:
        import qrcode
        from PIL import Image
        base_url = os.environ.get("PUBLIC_BASE_URL", "http://localhost:5000")
        report_url = f"{base_url.rstrip('/')}/report/{qr_token}"
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=6, border=2)
        qr.add_data(report_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"QR generation error: {e}")
        return None

def generate_pdf_report(report_data, output_folder="static/reports_pdf", language="en"):
    """
    Generates a professional multi-language PDF diagnostic report for MediScan AI.
    Supports English, Spanish, French, German, Hindi, Telugu, Tamil, and Arabic.
    Returns the filepath of the generated PDF file.
    """
    os.makedirs(output_folder, exist_ok=True)
    report_id = report_data.get("report_id", "report")
    lang_code = (language or report_data.get("language") or "en").lower().strip()
    pdf_filename = f"MediScan_Report_{report_id[:8]}_{lang_code}.pdf"
    pdf_path = os.path.join(output_folder, pdf_filename)

    tr = get_translation(lang_code)

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch

        # Select the Unicode fonts for this report's language so non-Latin scripts
        # (Telugu, Hindi, Tamil, Arabic, etc.) render correctly instead of crashing.
        MAIN_FONT, BOLD_FONT = get_report_fonts(lang_code)

        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName=BOLD_FONT,
            fontSize=20,
            leading=24,
            textColor=colors.HexColor('#0f172a')
        )
        subtitle_style = ParagraphStyle(
            'DocSubTitle',
            parent=styles['Normal'],
            fontName=MAIN_FONT,
            fontSize=10,
            leading=12,
            textColor=colors.HexColor('#64748b')
        )
        h2_style = ParagraphStyle(
            'SectionH2',
            parent=styles['Heading2'],
            fontName=BOLD_FONT,
            fontSize=12,
            leading=15,
            textColor=colors.HexColor('#1e293b'),
            spaceBefore=10,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'BodyDark',
            parent=styles['Normal'],
            fontName=MAIN_FONT,
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor('#334155')
        )
        alert_style = ParagraphStyle(
            'AlertText',
            parent=styles['Normal'],
            fontName=BOLD_FONT,
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor('#991b1b')
        )

        # Header Title
        story.append(Paragraph(tr["title"], title_style))
        story.append(Paragraph(tr["subtitle"], subtitle_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceBefore=2, spaceAfter=12))

        # Patient Info Table
        timestamp_ms = report_data.get("timestamp", int(time.time() * 1000))
        formatted_date = datetime.fromtimestamp(timestamp_ms / 1000.0).strftime('%B %d, %Y - %I:%M %p')

        patient_info_data = [
            [
                Paragraph(f"<b>{tr['patient_name']}:</b> " + str(report_data.get("patient_name", "N/A")), body_style),
                Paragraph(f"<b>{tr['patient_id']}:</b> " + str(report_data.get("patient_id", "N/A")), body_style)
            ],
            [
                Paragraph(f"<b>{tr['age_gender']}:</b> " + f"{report_data.get('patient_age', 'N/A')} / {report_data.get('patient_gender', 'N/A')}", body_style),
                Paragraph(f"<b>{tr['patient_email']}:</b> " + str(report_data.get("patient_email", "N/A")), body_style)
            ],
            [
                Paragraph(f"<b>{tr['last_visit']}:</b> " + str(report_data.get("last_visit_date", "N/A")), body_style),
                Paragraph(f"<b>{tr['next_visit']}:</b> <font color='#2563eb'><b>" + str(report_data.get("next_visit_date", "N/A")) + "</b></font>", body_style)
            ],
            [
                Paragraph(f"<b>{tr['report_id']}:</b> " + report_id, body_style),
                Paragraph(f"<b>{tr['generated_on']}:</b> " + formatted_date, body_style)
            ]
        ]
        info_table = Table(patient_info_data, colWidths=[3.6 * inch, 3.6 * inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 12))

        # Diagnostic Findings Header
        story.append(Paragraph(tr["findings_header"], h2_style))
        
        risk = str(report_data.get("risk", "Low"))
        risk_color = "#dc2626" if risk == "High" else "#d97706" if risk == "Moderate" else "#16a34a"
        risk_text_translated = tr.get("risk_high" if risk == "High" else ("risk_moderate" if risk == "Moderate" else "risk_low"), f"{risk.upper()} RISK")

        findings_data = [
            [
                Paragraph(f"<b>{tr['scan_type']}:</b>", body_style),
                Paragraph(str(report_data.get("cancer_type", "N/A")).upper(), body_style)
            ],
            [
                Paragraph(f"<b>{tr['classification']}:</b>", body_style),
                Paragraph(f"<b>{report_data.get('label', 'N/A')}</b>", body_style)
            ],
            [
                Paragraph(f"<b>{tr['confidence']}:</b>", body_style),
                Paragraph(f"<b>{report_data.get('confidence_pct', 0)}%</b>", body_style)
            ],
            [
                Paragraph(f"<b>{tr['risk_level']}:</b>", body_style),
                Paragraph(f"<font color='{risk_color}'><b>{risk_text_translated}</b></font>", body_style)
            ],
[
                Paragraph(f"<b>{tr['stage_severity']}:</b>", body_style),
                Paragraph(f"{report_data.get('stage', 'Stage 0')} (Severity Score: {report_data.get('severity_score', 0)}/100)", body_style)
            ],
            [
                Paragraph(f"<b>{tr.get('priority_queue', 'AI Priority Queue')}:</b>", body_style),
                Paragraph(f"<b>{report_data.get('priority_queue', 'Routine Review')}</b> (Score: {report_data.get('priority_score', 0)}/100)", body_style)
            ]
        ]

        findings_table = Table(findings_data, colWidths=[2.8 * inch, 4.4 * inch])
        findings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ffffff')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#f1f5f9')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(findings_table)
        story.append(Spacer(1, 12))

        # High Risk Alert Box if High Risk
        if risk == "High":
            alert_box_data = [[
                Paragraph(tr["high_risk_alert"], alert_style)
            ]]
            alert_table = Table(alert_box_data, colWidths=[7.2 * inch])
            alert_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fef2f2')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#fca5a5')),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(alert_table)
            story.append(Spacer(1, 12))

# Explanation Section
        story.append(Paragraph(tr["explanation_header"], h2_style))
        story.append(Paragraph(str(report_data.get("explanation", "No detailed summary available.")), body_style))
        story.append(Spacer(1, 12))

# Multi-Agent AI Clinical Second Opinion
        multi_agent = report_data.get("multi_agent")
        if multi_agent:
            # Try to use the server-side translated bundle, if available.
            ma_lang = lang_code
            translated_ma = report_data.get("multi_agent_translated")
            if translated_ma and translated_ma.get("_lang") == ma_lang:
                ma = translated_ma
            else:
                # Fallback: translate on the fly
                try:
                    from utils.multi_agent import translate_multi_agent_report
                    ma = translate_multi_agent_report(multi_agent, ma_lang)
                except Exception:
                    ma = multi_agent

            story.append(Paragraph(tr.get("multi_agent_title", "Multi-Agent AI Tumor Board — Clinical Second Opinion"), h2_style))

            consensus = ma.get("consensus") or {}
            opinions = ma.get("opinions") or {}
            board = ma.get("tumor_board") or {}
            timeline = ma.get("timeline") or {}
            plan = ma.get("treatment_plan") or {}
            labels = ma.get("_labels") or {}

            def L(key, fallback):
                return labels.get(key, tr.get(key, fallback))

            if consensus.get("overall_recommendation"):
                story.append(Paragraph(
                    f"<b>{L('final_ai_aggregator', 'Final AI Aggregator — Consensus')}"
                    + (f" ({consensus.get('urgency')})" if consensus.get("urgency") else "")
                    + ":</b> " + str(consensus["overall_recommendation"]),
                    body_style
                ))
                if consensus.get("recommended_specialist"):
                    story.append(Paragraph(
                        f"<b>{L('recommended_specialist', 'Recommended Specialist')}:</b> {consensus['recommended_specialist']}", body_style
                    ))
                if consensus.get("hospital_recommendation"):
                    story.append(Paragraph(str(consensus["hospital_recommendation"]), body_style))
                if consensus.get("agents_in_agreement") is not None:
                    story.append(Paragraph(
                        f"{L('agreement', 'Agreement')}: {consensus['agents_in_agreement']} / {consensus.get('total_agents', 5)} agents", body_style
                    ))
                story.append(Spacer(1, 8))

            for key in ["radiologist", "oncologist", "surgeon", "pharmacologist", "lifestyle"]:
                agent = opinions.get(key)
                if not agent:
                    continue
                agent_block = []
                if agent.get("opinion"):
                    agent_block.append(str(agent["opinion"]))
                if agent.get("findings"):
                    agent_block.append(f"{L('findings', 'Findings')}: " + " | ".join(str(f) for f in agent["findings"]))
                if agent.get("recommendations"):
                    agent_block.append(f"{L('recommendations', 'Recommendations')}: " + " | ".join(str(r) for r in agent["recommendations"]))
                if agent_block:
                    story.append(Paragraph(
                        f"<b>{agent.get('role', key)}:</b> " + " ".join(agent_block), body_style
                    ))
                    story.append(Spacer(1, 6))

            if board.get("case_summary") or board.get("treatment_options"):
                board_block = []
                if board.get("case_summary"):
                    board_block.append(str(board["case_summary"]))
                if board.get("ai_opinion"):
                    board_block.append(str(board["ai_opinion"]))
                if board.get("recommended_tests"):
                    board_block.append(f"{L('recommended_tests', 'Recommended Tests')}: " + " | ".join(str(t) for t in board["recommended_tests"]))
                if board.get("treatment_options"):
                    board_block.append(f"{L('treatment_options', 'Treatment Options (informational)')}: " + " | ".join(str(t) for t in board["treatment_options"]))
                if board.get("doctor_notes"):
                    board_block.append(f"{L('doctor_notes', 'Doctor Notes')}: {board['doctor_notes']}")
                if board_block:
                    story.append(Paragraph(f"<b>{L('ai_tumor_board', 'AI Tumor Board')}:</b> " + " ".join(board_block), body_style))
                    story.append(Spacer(1, 6))

            if timeline.get("current") or timeline.get("milestones"):
                tl_block = []
                for field in ["current", "prediction", "treatment"]:
                    if timeline.get(field):
                        tl_block.append(str(timeline[field]))
                for m in timeline.get("milestones") or []:
                    tl_block.append(f"{m.get('period')}: {m.get('detail')}")
                if tl_block:
                    story.append(Paragraph(f"<b>{L('ai_clinical_timeline', 'AI Clinical Timeline')}:</b> " + " ".join(tl_block), body_style))
                    story.append(Spacer(1, 6))

            if plan.get("recommended_specialist") or plan.get("next_appointment"):
                plan_block = []
                if plan.get("recommended_specialist"):
                    plan_block.append(f"{L('specialist', 'Specialist')}: {plan['recommended_specialist']}")
                if plan.get("next_appointment"):
                    plan_block.append(f"{L('next_appointment', 'Next Appointment')}: {plan['next_appointment']}")
                if plan.get("disclaimer"):
                    plan_block.append(f"{L('med_disclaimer', 'Disclaimer')}: {plan['disclaimer']}")
                if plan_block:
                    story.append(Paragraph(f"<b>{L('ai_treatment_planner', 'AI Treatment Planner')}:</b> " + " ".join(plan_block), body_style))
                    story.append(Spacer(1, 6))

            story.append(Spacer(1, 6))

        # Stage-Based Remedies & Health Habits
        try:
            from utils.health_guidance import get_stage_guidance
            stage_guidance = report_data.get("stage_guidance")
            if not stage_guidance or stage_guidance.get("_lang") != lang_code:
                stage_guidance = get_stage_guidance(
                    report_data.get("stage", "Stage 0"),
                    report_data.get("cancer_type", "general"),
                    language=lang_code
                )

            if stage_guidance:
                story.append(Paragraph(
                    tr.get("stage_guidance_title", "Stage-Based Supportive Remedies & Health Habits"),
                    h2_style
                ))
                story.append(Paragraph(
                    f"<b>{stage_guidance.get('stage_title', '')}</b> — {stage_guidance.get('clinical_goal', '')}",
                    body_style
                ))
                story.append(Spacer(1, 6))

                # Remedies block
                remedy_items = []
                for r in stage_guidance.get("remedies", []):
                    remedy_items.append(f"• <b>{r['title']}:</b> {r['desc']}")
                if remedy_items:
                    story.append(Paragraph(
                        f"<b>{tr.get('supportive_remedies', 'Supportive Remedies')}:</b><br/>" + "<br/>".join(remedy_items),
                        body_style
                    ))
                    story.append(Spacer(1, 6))

                # Habits block
                habit_items = []
                for h in stage_guidance.get("health_habits", []):
                    habit_items.append(f"• <b>{h['title']}:</b> {h['desc']}")
                if habit_items:
                    story.append(Paragraph(
                        f"<b>{tr.get('daily_health_habits', 'Daily Health Habits')}:</b><br/>" + "<br/>".join(habit_items),
                        body_style
                    ))
                    story.append(Spacer(1, 6))

                # Nutrition block
                nutri_items = []
                for n in stage_guidance.get("nutrition", []):
                    nutri_items.append(f"• <b>{n['title']}:</b> {n['desc']}")
                if nutri_items:
                    story.append(Paragraph(
                        f"<b>{tr.get('nutrition_hydration', 'Nutrition & Hydration')}:</b><br/>" + "<br/>".join(nutri_items),
                        body_style
                    ))
                    story.append(Spacer(1, 6))

                # Precautions block
                prec_items = []
                for p in stage_guidance.get("precautions", []):
                    prec_items.append(f"• <b>{p['title']}:</b> {p['desc']}")
                if prec_items:
                    story.append(Paragraph(
                        f"<b>{tr.get('precautions_avoid', 'Precautions & Habits to Strictly Avoid')}:</b><br/>" + "<br/>".join(prec_items),
                        body_style
                    ))
                    story.append(Spacer(1, 6))

                # Organ specific block if present
                org = stage_guidance.get("organ_specific")
                if org and org.get("guidance"):
                    org_items = [f"• {g}" for g in org["guidance"]]
                    story.append(Paragraph(
                        f"<b>{org.get('title', 'Organ-Specific Guidance')}:</b><br/>" + "<br/>".join(org_items),
                        body_style
                    ))
                    story.append(Spacer(1, 6))

                # Disclaimer
                if stage_guidance.get("disclaimer"):
                    story.append(Paragraph(f"<i>{stage_guidance['disclaimer']}</i>", alert_style))
                    story.append(Spacer(1, 8))
        except Exception as ge:
            print(f"Error appending stage guidance to PDF: {ge}")
        image_path = report_data.get("image_path")
        if image_path and os.path.exists(image_path):
            try:
                story.append(Paragraph(tr["scan_attachment"], h2_style))
                rl_img = RLImage(image_path, width=2.5*inch, height=2.5*inch)
                story.append(rl_img)
                story.append(Spacer(1, 12))
            except Exception:
                pass

# Footer & Disclaimer
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cbd5e1'), spaceBefore=10, spaceAfter=8))
        story.append(Paragraph(tr["disclaimer"], subtitle_style))

        # Verification QR Code (scannable to open the digital report)
        qr_token = report_data.get("qr_token")
        if qr_token:
            qr_buffer = generate_qr_image(qr_token)
            if qr_buffer:
                try:
                    qr_heading = Paragraph(
                        f"<b>{tr.get('report_id', 'Report ID')}</b>",
                        ParagraphStyle('QrHeading', parent=styles['Normal'], fontName=BOLD_FONT, fontSize=10, leading=13, textColor=colors.HexColor('#0f172a'), spaceBefore=12, spaceAfter=6)
                    )
                    story.append(qr_heading)
                    qr_table = Table(
                        [[RLImage(qr_buffer, width=1.4 * inch, height=1.4 * inch)]],
                        colWidths=[1.6 * inch], rowHeights=[1.6 * inch]
                    )
                    qr_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    story.append(qr_table)
                except Exception as qr_err:
                    print(f"QR embed error: {qr_err}")

        doc.build(story)
        print(f"PDF Diagnostic Report [{lang_code}] successfully generated at {pdf_path}")
        return pdf_path

    except Exception as e:
        print(f"ReportLab PDF generation error: {e}. Writing standard HTML/Text report fallback.")
        with open(pdf_path, "w", encoding="utf-8") as f:
            f.write(f"MediScan AI Diagnostic Report [{lang_code}]\nReport ID: {report_id}\nPatient: {report_data.get('patient_name')}\nResult: {report_data.get('label')}\nRisk: {report_data.get('risk')}\nNext Visit: {report_data.get('next_visit_date')}")
        return pdf_path
