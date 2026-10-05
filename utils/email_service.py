import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication


def _resolve_smtp_config():
    """Resolve SMTP connection settings from the environment.

    Returns (host, port, user, password, use_ssl) or None if not configured.
    Environment variables supported:
      - GMAIL_USER / GMAIL_APP_PASSWORD           (convenience for Gmail App Password)
      - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_TLS
    """
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", 0)) if os.environ.get("SMTP_PORT") else None
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    smtp_use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

    gmail_user = os.environ.get("GMAIL_USER")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD")

    if smtp_host and smtp_user and smtp_password:
        return smtp_host, (smtp_port or 587), smtp_user, smtp_password, False
    if gmail_user and gmail_password:
        return "smtp.gmail.com", 465, gmail_user, gmail_password, True
    return None


def _send_raw_email(recipient_email, subject, html_content, pdf_path=None, use_ssl=False,
                    host=None, port=None, user=None, password=None, smtp_use_tls=True):
    """Send a raw HTML email (with optional PDF attachment) over SMTP.

    Returns a dict: {sent: bool, recipient, message, error?}
    """
    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = recipient_email

        msg.attach(MIMEText(html_content, "html", _charset="utf-8"))

        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_att = MIMEApplication(f.read(), _subtype="pdf")
                pdf_att.add_header("Content-Disposition", "attachment", filename=os.path.basename(pdf_path))
                msg.attach(pdf_att)

        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=20)
            server.login(user, password)
        else:
            server = smtplib.SMTP(host, port or 587, timeout=20)
            server.ehlo()
            if smtp_use_tls:
                server.starttls()
                server.ehlo()
            server.login(user, password)

        server.sendmail(user, [recipient_email], msg.as_string())
        server.quit()

        return {"sent": True, "recipient": recipient_email, "message": "Email successfully dispatched."}
    except Exception as e:
        err = str(e)
        print(f"Email dispatch error: {err}")
        return {"sent": False, "recipient": recipient_email, "error": err, "message": "Email dispatch failed."}


def send_email_notification(report_data, pdf_path=None):
    """Send email with configurable SMTP settings.

    Environment variables supported:
      - GMAIL_USER / GMAIL_APP_PASSWORD           (convenience for Gmail App Password)
      - SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_TLS

    Returns dict: {sent: bool, simulated: bool, recipient, message, error?}
    """
    recipient_email = (report_data or {}).get("patient_email")
    if not recipient_email or "@" not in recipient_email:
        return {"sent": False, "message": "No valid patient email provided.", "recipient": None}

    resolved = _resolve_smtp_config()
    if not resolved:
        # No credentials available — simulate and return a helpful message
        msg = "Email credentials not configured in environment. Report generated & saved locally."
        print(msg)
        return {"sent": False, "simulated": True, "recipient": recipient_email, "message": msg}

    host, port, user, password, use_ssl = resolved

    patient_name = report_data.get("patient_name", "Patient")
    cancer_type = str(report_data.get("cancer_type", "Scan")).upper()
    label = report_data.get("label", "Diagnostic Scan")
    confidence_pct = report_data.get("confidence_pct", 0)
    risk = report_data.get("risk", "Low")
    report_id = report_data.get("report_id", "N/A")

    is_emergency = (risk == "High")
    subject = f"[{'EMERGENCY ALERT - ' if is_emergency else ''}MediScan AI Report] {cancer_type} Results for {patient_name}"

    # Minimal, safe HTML body
    html_content = f"""
    <html><body>
    <p>Dear <b>{patient_name}</b>,</p>
    <p>Your MediScan AI diagnostic results are ready.</p>
    <ul>
      <li><b>Scan area:</b> {cancer_type}</li>
      <li><b>Result:</b> {label}</li>
      <li><b>Confidence:</b> {confidence_pct}%</li>
      <li><b>Risk:</b> {risk}</li>
      <li><b>Report ID:</b> {report_id}</li>
    </ul>
    <p>Please consult your physician for interpretation and next steps.</p>
    </body></html>
    """

    return _send_raw_email(
        recipient_email, subject, html_content, pdf_path=pdf_path,
        use_ssl=use_ssl, host=host, port=port, user=user, password=password
    )


def send_visit_reminder_email(report_data, days_left):
    """Send a visit reminder email to a patient whose next appointment is coming soon.

    days_left should be 1, 2 or 3. Reuses the same SMTP credential resolution as the
    report notification email. Returns dict: {sent, simulated, recipient, message, error?}
    """
    recipient_email = (report_data or {}).get("patient_email")
    if not recipient_email or "@" not in recipient_email:
        return {"sent": False, "message": "No valid patient email provided.", "recipient": None}

    resolved = _resolve_smtp_config()
    if not resolved:
        msg = "Email credentials not configured in environment. Visit reminder simulated."
        print(msg)
        return {"sent": False, "simulated": True, "recipient": recipient_email, "message": msg}

    host, port, user, password, use_ssl = resolved

    patient_name = report_data.get("patient_name", "Patient")
    next_visit = report_data.get("next_visit_date", "N/A")
    report_language = str(report_data.get("report_language", "en") or "en").lower().strip()

    days_left = max(1, int(days_left))
    day_word = {1: "tomorrow", 2: "in 2 days", 3: "in 3 days"}.get(days_left, f"in {days_left} days")

    # Localized day-word for the subject/body (best effort for major languages)
    local_day = {
        "hi": {1: "कल", 2: "2 दिनों में", 3: "3 दिनों में"},
        "te": {1: "రేపు", 2: "2 రోజులలో", 3: "3 రోజులలో"},
        "ta": {1: "நாளை", 2: "2 நாட்களில்", 3: "3 நாட்களில்"},
        "bn": {1: "আগামীকাল", 2: "2 দিনের মধ্যে", 3: "3 দিনের মধ্যে"},
        "es": {1: "mañana", 2: "en 2 días", 3: "en 3 días"},
        "fr": {1: "demain", 2: "dans 2 jours", 3: "dans 3 jours"},
        "de": {1: "morgen", 2: "in 2 Tagen", 3: "in 3 Tagen"},
    }.get(report_language, {}).get(days_left, day_word)

    subject = f"⏰ Reminder: Your MediScan follow-up visit is {day_word} ({next_visit})"

    html_content = f"""
    <html><body>
    <p>Dear <b>{patient_name}</b>,</p>
    <p>This is a friendly reminder from <b>MediScan AI</b>.</p>
    <p>Your scheduled follow-up consultation is coming up <b>{day_word}</b> on <b>{next_visit}</b>.</p>
    <p style="padding: 14px; background: #fff3cd; border-left: 4px solid #f5a623; color:#333; border-radius:6px;">
      <b>Kindly consult your doctor in {days_left} day{'s' if days_left != 1 else ''}.</b>
    </p>
    <p>It is important to keep your appointment so your physician can monitor your progress.</p>
    <p>Thank you,<br/>MediScan AI Team</p>
    </body></html>
    """

    return _send_raw_email(
        recipient_email, subject, html_content,
        use_ssl=use_ssl, host=host, port=port, user=user, password=password
    )
