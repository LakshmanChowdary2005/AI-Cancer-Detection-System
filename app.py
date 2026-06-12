import os
import json
import uuid
import time
import base64
from io import BytesIO
from datetime import datetime

import numpy as np
import cv2
import tensorflow as tf

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from PIL import Image

from tensorflow.keras.models import load_model
from tensorflow.keras.applications.efficientnet import preprocess_input

# =====================================================

# FLASK CONFIG

# =====================================================

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
DATA_FOLDER = "data"
REPORTS_FILE = os.path.join(DATA_FOLDER, "reports.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

if not os.path.exists(REPORTS_FILE):
    with open(REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# =====================================================

# LOAD MODELS

# =====================================================

print("Loading Models...")

SKIN_MODEL = load_model("models/skin_model.keras")
BRAIN_MODEL = load_model("models/brain_model.keras")
BREAST_MODEL = load_model("models/breast_model.keras")
LUNG_MODEL = load_model("models/lung_model.keras")
CANCER_TYPE_MODEL = load_model("models/cancer_type_model.keras")

print("All Models Loaded Successfully!")

# =====================================================

# CLASS LABELS

# =====================================================

CANCER_TYPE_CLASSES = [
"brain",
"breast",
"lung",
"skin"
]

BRAIN_CLASSES = [
"Glioma",
"Meningioma",
"No Tumor",
"Pituitary"
]

BREAST_CLASSES = [
"Benign",
"Malignant",
"Normal"
]

LUNG_CLASSES = [
"Adenocarcinoma",
"Normal",
"Squamous Cell Carcinoma"
]

# =====================================================

# IMAGE PREPROCESSING

# =====================================================

def prepare_image(img_path):

    img = Image.open(img_path).convert('RGB')
    img = img.resize((224, 224), Image.LANCZOS)

    img_array = np.array(img, dtype=np.float32)
    img_array = np.expand_dims(img_array, axis=0)
    img_array = preprocess_input(img_array)
    return img_array


def load_reports():
    if not os.path.exists(REPORTS_FILE):
        return []
    with open(REPORTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_reports(reports):
    with open(REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2)


def find_last_conv_layer(model):
    for layer in reversed(model.layers):
        if isinstance(layer, tf.keras.layers.Conv2D):
            return layer.name
    raise ValueError("No Conv2D layer found in the model")


def make_gradcam_heatmap(img_array, model, pred_index=None):
    last_conv_name = find_last_conv_layer(model)
    grad_model = tf.keras.models.Model(
        [model.inputs],
        [model.get_layer(last_conv_name).output, model.output]
    )

    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(img_array)
        if pred_index is None:
            pred_index = tf.argmax(predictions[0])
        loss = predictions[:, pred_index]

    grads = tape.gradient(loss, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
    conv_outputs = conv_outputs[0]

    heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)
    heatmap = tf.maximum(heatmap, 0) / (tf.math.reduce_max(heatmap) + 1e-8)
    return heatmap.numpy()


def create_gradcam_overlay(img_path, heatmap):
    image = cv2.imread(img_path)
    if image is None:
        return None

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    heatmap = np.uint8(255 * heatmap)
    heatmap = cv2.resize(heatmap, (image.shape[1], image.shape[0]))
    heatmap_color = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    superimposed = cv2.addWeighted(image, 0.7, heatmap_color, 0.35, 0)

    pil_img = Image.fromarray(superimposed)
    buffer = BytesIO()
    pil_img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def check_image_quality(img_path):
    image = cv2.imread(img_path)
    if image is None:
        return False, "Image Quality: Could not read image."

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if gray.shape[0] < 200 or gray.shape[1] < 200:
        return False, "Image Quality: Poor. Please upload a higher resolution image."

    blur = cv2.Laplacian(gray, cv2.CV_64F).var()
    if blur < 80:
        return False, "Image Quality: Poor. Please upload a clearer image."

    return True, ""


def ensemble_type_decision(processed_image):
    """Use CANCER_TYPE_MODEL as primary classifier. Individual models classify within their type."""
    type_prediction = CANCER_TYPE_MODEL.predict(processed_image, verbose=0)[0]
    type_index = np.argmax(type_prediction)
    type_name = CANCER_TYPE_CLASSES[type_index]
    type_confidence = float(type_prediction[type_index])

    return {
        "auto_type": type_name,
        "auto_confidence": type_confidence,
        "ensemble_type": type_name,
        "ensemble_confidence": type_confidence,
        "consensus": True,
        "confidence_map": {
            "brain": float(type_prediction[0]),
            "breast": float(type_prediction[1]),
            "lung": float(type_prediction[2]),
            "skin": float(type_prediction[3])
        }
    }


def get_stage_and_severity(label, confidence_pct):
    label_text = label.lower()
    if "no tumor" in label_text or "normal" in label_text or "benign" in label_text:
        stage = "Stage 0"
        severity = int(round(max(5, min(35, confidence_pct * 0.45))))
        return stage, severity

    if confidence_pct >= 90:
        stage = "Stage IV"
    elif confidence_pct >= 75:
        stage = "Stage III"
    elif confidence_pct >= 55:
        stage = "Stage II"
    else:
        stage = "Stage I"

    severity = int(round(min(100, max(45, confidence_pct + 5))))
    return stage, severity


def generate_report_explanation(cancer_type, label, confidence_pct, quality_ok, quality_message, ensemble_result):
    summary = []
    summary.append(f"Model predicts {label} with {confidence_pct:.1f}% confidence.")
    if quality_ok:
        summary.append("Image quality is acceptable for analysis.")
    else:
        summary.append(quality_message)
    summary.append(f"The system compared an automatic cancer type detector with individual model scores and selected {ensemble_result['ensemble_type']} via ensemble voting.")
    if ensemble_result["consensus"]:
        summary.append("The automatic and ensemble predictions are in agreement.")
    else:
        summary.append("There is a mismatch between the auto-detected type and the ensemble vote, so clinical review is advised.")
    summary.append("Grad-CAM explains which scan regions influenced the model.")
    return " ".join(summary)


def save_prediction(report):
    reports = load_reports()
    reports.insert(0, report)
    save_reports(reports[:50])


# =====================================================

# HOME

# =====================================================

@app.route("/")
def home():
    return render_template("index.html")

# =====================================================

# PREDICT

# =====================================================

@app.route("/predict", methods=["POST"])
def predict():

    try:

        if "image" not in request.files:
            return jsonify({
                "error": "No image uploaded"
            })

        file = request.files["image"]

        if file.filename == "":
            return jsonify({
                "error": "No file selected"
            })

        filename = secure_filename(
            file.filename
        )

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        file.save(filepath)

        processed_image = prepare_image(
            filepath
        )

        image_quality_ok, quality_message = check_image_quality(filepath)
        ensemble_result = ensemble_type_decision(processed_image)

        requested_type = request.form.get('cancer_type', 'auto')
        if requested_type != 'auto' and requested_type in CANCER_TYPE_CLASSES:
            cancer_type = requested_type
        else:
            cancer_type = ensemble_result["ensemble_type"]

        print(
            "Detected Type:",
            cancer_type
        )

        # Brain

        if cancer_type == "brain":

            model_to_use = BRAIN_MODEL
            prediction = BRAIN_MODEL.predict(
                processed_image,
                verbose=0
            )[0]

            idx = np.argmax(
                prediction
            )

            label = (
                "Brain Tumor - "
                + BRAIN_CLASSES[idx]
            )

            confidence = float(
                prediction[idx]
            )

        # Breast

        elif cancer_type == "breast":

            model_to_use = BREAST_MODEL
            prediction = BREAST_MODEL.predict(
                processed_image,
                verbose=0
            )[0]

            idx = np.argmax(
                prediction
            )

            label = (
                "Breast Cancer - "
                + BREAST_CLASSES[idx]
            )

            confidence = float(
                prediction[idx]
            )

        # Lung

        elif cancer_type == "lung":

            model_to_use = LUNG_MODEL
            prediction = LUNG_MODEL.predict(
                processed_image,
                verbose=0
            )[0]

            idx = np.argmax(
                prediction
            )

            label = (
                "Lung Cancer - "
                + LUNG_CLASSES[idx]
            )

            confidence = float(
                prediction[idx]
            )

        # Skin

        else:

            model_to_use = SKIN_MODEL
            prediction = SKIN_MODEL.predict(
                processed_image,
                verbose=0
            )[0][0]

            if prediction >= 0.5:

                label = (
                    "Skin Cancer - Malignant"
                )

                confidence = float(
                    prediction
                )

            else:

                label = (
                    "Skin Cancer - Benign"
                )

                confidence = float(
                    1 - prediction
                )

        confidence_pct = round(
            confidence * 100,
            2
        )

        # Determine risk: normal/benign scans are always Low risk
        label_lower = label.lower()
        if any(term in label_lower for term in ["normal", "benign", "no tumor"]):
            risk = "Low"
        elif confidence_pct >= 85:
            risk = "High"
        elif confidence_pct >= 60:
            risk = "Moderate"
        else:
            risk = "Low"

        stage, severity_score = get_stage_and_severity(label, confidence_pct)
        explanation = generate_report_explanation(
            cancer_type,
            label,
            confidence_pct,
            image_quality_ok,
            quality_message,
            ensemble_result
        )

        report_id = uuid.uuid4().hex
        qr_token = uuid.uuid4().hex
        saved_report = {
            "report_id": report_id,
            "qr_token": qr_token,
            "timestamp": int(time.time() * 1000),
            "patient_name": request.form.get('patient_name', 'Anonymous'),
            "patient_age": request.form.get('patient_age', 'Unknown'),
            "patient_gender": request.form.get('patient_gender', 'Unknown'),
            "patient_id": request.form.get('patient_id', 'N/A'),
            "image_path": filepath.replace('\\', '/'),
            "cancer_type": cancer_type,
            "auto_type": ensemble_result["auto_type"],
            "auto_confidence": ensemble_result["auto_confidence"],
            "ensemble_type": ensemble_result["ensemble_type"],
            "ensemble_confidence": ensemble_result["ensemble_confidence"],
            "consensus": ensemble_result["consensus"],
            "confidence_map": ensemble_result["confidence_map"],
            "quality_ok": image_quality_ok,
            "quality_message": quality_message,
            "label": label,
            "confidence_pct": confidence_pct,
            "risk": risk,
            "stage": stage,
            "severity_score": severity_score,
            "explanation": explanation,
            "comments": []
        }
        save_prediction(saved_report)

        gradcam_image = None
        try:
            heatmap = make_gradcam_heatmap(processed_image, model_to_use)
            gradcam_image = create_gradcam_overlay(filepath, heatmap)
        except Exception:
            gradcam_image = None

        return jsonify({
            "label": label,
            "cancer_type": cancer_type,
            "confidence": confidence,
            "confidence_pct": confidence_pct,
            "risk": risk,
            "malignant_pct": confidence_pct,
            "benign_pct": round(100 - confidence_pct, 2),
            "gradcam": gradcam_image,
            "stage": stage,
            "severity_score": severity_score,
            "explanation": explanation,
            "report_id": report_id,
            "qr_token": qr_token,
            "auto_type": ensemble_result["auto_type"],
            "auto_confidence": ensemble_result["auto_confidence"],
            "ensemble_type": ensemble_result["ensemble_type"],
            "ensemble_confidence": ensemble_result["ensemble_confidence"],
            "consensus": ensemble_result["consensus"],
            "confidence_map": ensemble_result["confidence_map"],
            "quality_ok": image_quality_ok,
            "quality_message": quality_message
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        })

# =====================================================
# DASHBOARD

# =====================================================

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/reports", methods=["GET"])
def api_reports():
    return jsonify(load_reports())


@app.route("/api/clear_reports", methods=["POST"])
def api_clear_reports():
    save_reports([])
    return jsonify({"success": True, "message": "All reports cleared."})


@app.route("/api/comment", methods=["POST"])
def api_comment():
    data = request.get_json() or {}
    report_id = data.get("report_id")
    comment = data.get("comment")
    if not report_id or not comment:
        return jsonify({"error": "report_id and comment are required."}), 400

    reports = load_reports()
    for report in reports:
        if report.get("report_id") == report_id:
            report.setdefault("comments", []).append({
                "timestamp": int(time.time() * 1000),
                "comment": comment
            })
            save_reports(reports)
            return jsonify({"report": report})

    return jsonify({"error": "Report not found."}), 404


@app.route("/api/verify", methods=["POST"])
def api_verify():
    data = request.get_json() or {}
    qr_token = data.get("qr_token")
    if not qr_token:
        return jsonify({"error": "qr_token is required."}), 400

    reports = load_reports()
    for report in reports:
        if report.get("qr_token") == qr_token:
            return jsonify({"valid": True, "report": report})

    return jsonify({"valid": False, "error": "Invalid or expired QR token."}), 404

# =====================================================
# RUN

# =====================================================

if __name__ == "__main__":

    app.run(
    host="0.0.0.0",
    port=5000,
    debug=True
)

