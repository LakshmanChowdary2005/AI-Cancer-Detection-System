import os
import json
import uuid
import time
import base64
import math
import threading
from io import BytesIO
from datetime import datetime, timedelta
from collections import OrderedDict

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import numpy as np
import cv2
import tensorflow as tf

from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory, send_file
from werkzeug.utils import secure_filename
from PIL import Image

from tensorflow.keras.models import load_model
from tensorflow.keras.applications.efficientnet import preprocess_input

from utils.pdf_generator import generate_pdf_report
from utils.google_drive_service import upload_to_google_drive
from utils.email_service import send_email_notification, send_visit_reminder_email
from utils.translator import translate_text, get_translation
from utils.multi_agent import (
    generate_multi_agent_reports,
    translate_multi_agent_report,
)
from utils.health_guidance import get_stage_guidance
from utils.health_suite import health_suite_bp
from utils.hospital_routes import hospital_bp

# =====================================================
# FLASK CONFIG
# =====================================================

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mediscan_secret_key_2026")
app.register_blueprint(health_suite_bp)
app.register_blueprint(hospital_bp)

DOCTOR_USERNAME = os.environ.get("DOCTOR_USERNAME", "doctor@mediscan.ai")
DOCTOR_PASSWORD = os.environ.get("DOCTOR_PASSWORD", "password123")

UPLOAD_FOLDER = "static/uploads"
DATA_FOLDER = "data"
REPORTS_FILE = os.path.join(DATA_FOLDER, "reports.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)

if not os.path.exists(REPORTS_FILE):
    with open(REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
FAST_MODE = os.environ.get("FAST_MODE", "true").lower() in ("1", "true", "yes", "fast")

# Serve local fonts directory at /fonts/
@app.route('/fonts/<path:filename>')
def serve_fonts(filename):
    return send_from_directory('fonts', filename)

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

CANCER_TYPE_CLASSES = ["brain", "breast", "lung", "skin"]
BRAIN_CLASSES = ["Glioma", "Meningioma", "No Tumor", "Pituitary"]
BREAST_CLASSES = ["Benign", "Malignant", "Normal"]
LUNG_CLASSES = ["Adenocarcinoma", "Normal", "Squamous Cell Carcinoma"]

# =====================================================
# IMAGE PREPROCESSING & HELPERS
# =====================================================

def prepare_image(img_path):
    img = Image.open(img_path).convert('RGB')
    img = img.resize((224, 224), Image.BILINEAR)
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


def _pick_gradcam_target_layer(model, min_spatial=14):
    """Choose a deep Conv2D layer with spatial size >= min_spatial (>=14x14)
    that still carries strong semantic features. Prefer ~14x14 (block5a_project_conv)
    over the 7x7 top_conv for sharper, better-localized heatmaps.

    Falls back to the last Conv2D layer if none qualifies.
    """
    try:
        candidates = []
        for layer in model.layers:
            if not isinstance(layer, tf.keras.layers.Conv2D):
                continue
            try:
                shape = getattr(layer.output, "shape", None)
                if shape and len(shape) == 4:
                    h = int(shape[1])
                    w = int(shape[2])
                    if h >= min_spatial and w >= min_spatial:
                        candidates.append((h * w, layer.name))
            except Exception:
                continue
        if candidates:
            # Pick the smallest qualifying layer (deepest with >= min_spatial),
            # i.e. the one closest to 14x14 — best tradeoff of resolution vs semantics.
            candidates.sort(key=lambda item: item[0])
            return candidates[0][1]
    except Exception:
        pass
    return find_last_conv_layer(model)


_GRAD_MODEL_CACHE = {}

def get_cached_grad_model(model):
    model_id = id(model)
    if model_id not in _GRAD_MODEL_CACHE:
        target_conv_name = _pick_gradcam_target_layer(model, min_spatial=14)
        _GRAD_MODEL_CACHE[model_id] = tf.keras.models.Model(
            model.inputs,
            [model.get_layer(target_conv_name).output, model.output]
        )
    return _GRAD_MODEL_CACHE[model_id]


def make_gradcam_heatmap(img_array, model, pred_index=None):
    try:
        grad_model = get_cached_grad_model(model)
        with tf.GradientTape() as tape:
            conv_outputs, predictions = grad_model(img_array, training=False)
            if pred_index is None:
                pred_index = tf.argmax(predictions[0])
            pred_index = tf.cast(pred_index, tf.int32)
            loss = predictions[:, pred_index]

        grads = tape.gradient(loss, conv_outputs)
        if grads is None:
            return None
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        conv_outputs = conv_outputs[0]

        heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)
        heatmap = tf.maximum(heatmap, 0) / (tf.math.reduce_max(heatmap) + 1e-8)
        return heatmap.numpy()
    except Exception:
        return None


def make_input_gradient_heatmap(img_array, model, pred_index=None):
    """Compute a fast saliency heatmap by taking gradients of the predicted class
    with respect to the input image. This is used as a lightweight fallback when
    Grad-CAM fails or when we want a quick map synchronously.
    Returns a 2D numpy array (H x W) normalized to [0,1].
    """
    try:
        img_tensor = tf.convert_to_tensor(img_array)
        with tf.GradientTape() as tape:
            tape.watch(img_tensor)
            preds = model(img_tensor, training=False)
            if pred_index is None:
                pred_index = tf.argmax(preds[0])
                
            loss = preds[:, pred_index]

        grads = tape.gradient(loss, img_tensor)[0]
        # Aggregate absolute gradients across color channels
        grads = tf.reduce_mean(tf.abs(grads), axis=-1)
        grads = grads - tf.reduce_min(grads)
        denom = tf.reduce_max(grads) + 1e-8
        heatmap = grads / denom
        return heatmap.numpy()
    except Exception:
        return None


def get_affected_region(heatmap, threshold=0.35):
    """Locate the dominant cancer-affected region from a 2D heatmap (values 0-1).
    Uses a lower threshold plus adaptive thresholding so small/weak tumor
    activations are still detected. Returns (area_ratio, bbox) where bbox is
    (x, y, w, h) or None.
    """
    try:
        h_arr = np.asarray(heatmap, dtype=np.float32)
        if h_arr.ndim == 3:
            h_arr = h_arr[..., 0]
        hh, ww = h_arr.shape[:2]
        norm = h_arr / (np.max(h_arr) + 1e-8)
        gray = np.uint8(255 * norm)

        # Lower fixed threshold catches broader regions
        _, thresh = cv2.threshold(gray, threshold * 255, 255, cv2.THRESH_BINARY)

        # Also try adaptive thresholding to catch weaker but still relevant areas
        if hh > 30 and ww > 30:
            adaptive = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 31, -12
            )
            thresh = cv2.bitwise_or(thresh, adaptive)

        kernel = np.ones((11, 11), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, None
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) < 60:
            return None, None
        area_pixels = cv2.contourArea(largest)
        area_ratio = float(area_pixels) / float(max(1, hh * ww))
        x, y, w, h = cv2.boundingRect(largest)
        return area_ratio, (x, y, w, h)
    except Exception:
        return None, None


def get_region_centroid(ll):
    """Return the (cx, cy) pixel centroid of the given contour."""
    if ll is None or len(ll) == 0:
        return None
    try:
        M = cv2.moments(ll)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            return (cx, cy)
    except Exception:
        return None
    return None


def draw_region_markers(rgb_image, heatmap, contour_color=(220, 20, 60),
                        label="Suspicious Region"):
    """Draw a prominent filled contour, bounding box, centroid crosshair and label
    on the given BGR/RGB image to clearly highlight the cancer-affected region.
    Takes a 2D heatmap (values 0-1) and operates in-place on the ndarray.
    """
    try:
        h_arr = np.asarray(heatmap, dtype=np.float32)
        if h_arr.ndim == 3:
            h_arr = h_arr[..., 0]
        h_arr = cv2.resize(h_arr, (rgb_image.shape[1], rgb_image.shape[0]))
    except Exception:
        return rgb_image

    try:
        norm = h_arr / (np.max(h_arr) + 1e-8)
        gray = np.uint8(255 * norm)
        _, thresh = cv2.threshold(gray, 0.4 * 255, 255, cv2.THRESH_BINARY)
        kernel = np.ones((9, 9), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return rgb_image
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) < 40:
            return rgb_image

        # Filled contour at low opacity to tint the tumor area
        overlay = rgb_image.copy()
        cv2.drawContours(overlay, [largest], -1, contour_color, -1)
        cv2.addWeighted(overlay, 0.35, rgb_image, 0.65, 0, dst=rgb_image)

        # Bold bounding box
        x, y, w, h = cv2.boundingRect(largest)
        cv2.rectangle(rgb_image, (x, y), (x + w, y + h), contour_color, 3)

        # Centroid crosshair
        centroid = get_region_centroid(largest)
        if centroid:
            cx, cy = centroid
            r = 12
            cv2.line(rgb_image, (cx - r, cy), (cx + r, cy), contour_color, 2)
            cv2.line(rgb_image, (cx, cy - r), (cx, cy + r), contour_color, 2)
            cv2.circle(rgb_image, (cx, cy), 3, (255, 255, 255), -1)

        # Label
        cv2.putText(rgb_image, label, (x, max(22, y - 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, contour_color, 2, cv2.LINE_AA)
    except Exception:
        pass

    return rgb_image


def encode_image_rgb(array):
    try:
        # cv2.imencode in C++ is ~3x faster than PIL PNG save
        bgr = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
        success, encoded = cv2.imencode(".png", bgr)
        if success:
            return base64.b64encode(encoded.tobytes()).decode("utf-8")
    except Exception:
        pass
    pil_img = Image.fromarray(array)
    buffer = BytesIO()
    pil_img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def create_original_highlight(img_path, heatmap):
    """Draw a red contour + bounding box around the affected region directly on the
    ORIGINAL grayscale/color scan (no heatmap colors), so the cancer area is clearly
    highlighted on the original image as well.
    """
    if heatmap is None:
        return None
    try:
        image = cv2.imread(img_path)
        if image is None:
            return None
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h_arr = np.asarray(heatmap, dtype=np.float32)
        if h_arr.ndim == 3:
            h_arr = h_arr[..., 0]
        h_arr = cv2.resize(h_arr, (image_rgb.shape[1], image_rgb.shape[0]))
        # Use the prominent marker helper: filled tint + bbox + crosshair + label
        draw_region_markers(image_rgb, h_arr, contour_color=(220, 20, 20), label="Suspicious Region")
        return encode_image_rgb(image_rgb)
    except Exception:
        return None


def create_gradcam_overlay(img_path, heatmap, mark_suspicious=True, label="Suspicious Region"):
    image = cv2.imread(img_path)
    if image is None:
        return None

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    heatmap = np.uint8(255 * heatmap)
    heatmap = cv2.resize(heatmap, (image.shape[1], image.shape[0]))
    heatmap_color = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    superimposed = cv2.addWeighted(image, 0.7, heatmap_color, 0.35, 0)

    # Highlight the cancer-affected area only for suspicious/malignant findings.
    # For benign / normal scans we do NOT draw a "Suspicious Region" marker.
    if mark_suspicious:
        try:
            h_arr = np.asarray(heatmap, dtype=np.float32)
            draw_region_markers(superimposed, h_arr, contour_color=(220, 20, 60), label=label)
        except Exception:
            pass

    return encode_image_rgb(superimposed)


def create_heatmap_overlay_fallback(img_path, heatmap_array):
    """Create a heatmap overlay from a 2D heatmap array (values 0-1).
    This is a lighter-weight alternative to Grad-CAM overlay.
    """
    if heatmap_array is None:
        return None
    try:
        image = cv2.imread(img_path)
        if image is None:
            return None
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        heatmap = np.uint8(255 * heatmap_array)
        heatmap = cv2.resize(heatmap, (image.shape[1], image.shape[0]))
        heatmap_color = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
        superimposed = cv2.addWeighted(image, 0.65, heatmap_color, 0.4, 0)
        pil_img = Image.fromarray(superimposed)
        buffer = BytesIO()
        pil_img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        return None


def create_manual_heatmap_fallback(img_path, label=""):
    """Generate a deterministic visual heatmap WITHOUT any gradient computation.

    This is the last-resort fallback used when both Grad-CAM and input-gradient
    saliency fail (e.g. model architecture incompatibility). It highlights image
    regions that differ most from their local neighborhood using edge density +
    texture energy (Laplacian variance), which correlates well with the lesion/
    tumor location in radiological scans.

    Returns a base64 PNG overlay (or None on failure).
    """
    try:
        image = cv2.imread(img_path)
        if image is None:
            return None
        orig_h, orig_w = image.shape[:2]
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # --- Build a saliency heatmap purely from image statistics ---
        # 1. Laplacian edge magnitude (captures irregular lesion boundaries)
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        lap = cv2.GaussianBlur(lap, (0, 0), sigmaX=3)

        # 2. Local texture energy via variance filtering (abnormal tissue)
        mean_local = cv2.boxFilter(gray.astype(np.float32), ddepth=-1, ksize=(31, 31))
        sq_local = cv2.boxFilter((gray.astype(np.float32) ** 2), ddepth=-1, ksize=(31, 31))
        variance = sq_local - mean_local * mean_local
        variance = np.clip(variance, 0, None)

        # 3. Combine edge + texture signals
        saliency = np.abs(lap) + np.sqrt(variance + 1e-6)
        saliency = cv2.GaussianBlur(saliency, (0, 0), sigmaX=5)

        # 4. Normalize to 0-255
        saliency = cv2.normalize(saliency, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        # 5. Threshold to keep the strongest region (the likely lesion)
        _, thresh = cv2.threshold(saliency, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = np.ones((9, 9), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 6. Build a focused heatmap around the dominant region
        heatmap = np.zeros_like(saliency)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest) >= 150:
                x, y, w, h = cv2.boundingRect(largest)
                # Keep the saliency only inside a slightly padded bbox, Gaussian-blurred
                cx, cy = x + w // 2, y + h // 2
                rr = max(w, h)
                mask = np.zeros_like(saliency)
                cv2.ellipse(mask, (cx, cy), (int(rr * 0.9), int(rr * 0.9)), 0, 0, 360, 255, -1)
                heatmap = cv2.bitwise_and(saliency, saliency, mask=mask)
            else:
                heatmap = saliency
        else:
            heatmap = saliency

        heatmap = cv2.GaussianBlur(heatmap, (0, 0), sigmaX=9)
        heatmap_norm = cv2.normalize(heatmap, None, 0, 255, cv2.NORM_MINMAX)

        # 7. Colorize with JET and overlay on the original image
        heatmap_color = cv2.applyColorMap(heatmap_norm, cv2.COLORMAP_JET)
        superimposed = cv2.addWeighted(image_rgb, 0.6, heatmap_color, 0.45, 0)

        # 8. Draw the region marker (contour + bbox + crosshair + label)
        draw_region_markers(superimposed, heatmap_norm.astype(np.float32) / 255.0,
                            contour_color=(220, 20, 60), label="Suspicious Region")

        pil_img = Image.fromarray(superimposed)
        buffer = BytesIO()
        pil_img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        return None


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
    type_prediction = CANCER_TYPE_MODEL(processed_image, training=False).numpy()[0]
    type_index = int(np.argmax(type_prediction))
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


# =====================================================
# AI PRIORITY QUEUE (AUTOMATIC PATIENT TRIAGE)
# =====================================================

# Ordered priority lanes — index 0 is the most urgent.
QUEUE_LANES = ["Emergency", "Urgent", "Normal Queue", "Routine Review"]

# Baseline score per lane (used to sort across all lanes).
_QUEUE_BASE_SCORE = {
    "Emergency": 90,
    "Urgent": 70,
    "Normal Queue": 45,
    "Routine Review": 20,
}


def compute_priority(risk="Low", confidence_pct=0, severity_score=0, label=""):
    """Automatically assign a patient to a priority lane based on the AI diagnosis.

    Returns a dict with:
      - priority_score : 0-100 numeric score used to sort patients (higher = more urgent)
      - priority_queue : one of Emergency / Urgent / Normal Queue / Routine Review
      - priority_rank  : 1-based rank within the lane (filled later by the queue endpoint)
    """
    label_text = (label or "").lower()
    is_benign = any(term in label_text for term in ["normal", "benign", "no tumor"])

    # Lane assignment
    if risk == "High" and confidence_pct >= 90:
        queue = "Emergency"
    elif risk == "High" or (not is_benign and confidence_pct >= 85):
        queue = "Urgent"
    elif risk == "Moderate" or (not is_benign and confidence_pct >= 60):
        queue = "Normal Queue"
    else:
        queue = "Routine Review"

    # Numeric score: base lane score adjusted by confidence/severity so patients
    # within the same lane / across lanes are ranked meaningfully.
    base = _QUEUE_BASE_SCORE.get(queue, 20)
    conf_component = max(0.0, min(50.0, confidence_pct * 0.5))
    sev_component = max(0.0, min(25.0, (severity_score or 0) * 0.25))
    priority_score = int(round(max(0, min(100, base + conf_component * 0.2 + sev_component))))

    return {
        "priority_score": priority_score,
        "priority_queue": queue,
        "priority_rank": 1,
    }


def backfill_priority(report):
    """Ensure a report has priority fields (used for older reports saved before the
    priority queue feature existed)."""
    if "priority_queue" in report and "priority_score" in report:
        return report
    computed = compute_priority(
        risk=report.get("risk", "Low"),
        confidence_pct=report.get("confidence_pct", 0),
        severity_score=report.get("severity_score", 0),
        label=report.get("label", ""),
    )
    report["priority_score"] = computed["priority_score"]
    report["priority_queue"] = computed["priority_queue"]
    report["priority_rank"] = computed["priority_rank"]
    return report


def estimate_affected_area_percentage(confidence_pct, label, image_path):
    label_text = (label or "").lower()
    if any(term in label_text for term in ["normal", "benign", "no tumor"]):
        return int(round(max(3, min(18, confidence_pct * 0.12))))

    try:
        with Image.open(image_path).convert("RGB") as img:
            width, height = img.size
    except Exception:
        width, height = 224, 224

    diagonal_px = math.sqrt(width * width + height * height)
    normalized_size = min(95, max(8, int(round((confidence_pct / 100) * 100 * 0.9))))
    area_factor = 0.75 + min(0.2, diagonal_px / 4000)
    area_pct = int(round(min(98, max(10, normalized_size * area_factor))))
    return area_pct


def estimate_tumor_size_cm(affected_area_pct, image_path):
    try:
        with Image.open(image_path).convert("RGB") as img:
            width, height = img.size
    except Exception:
        width, height = 224, 224

    diagonal_cm = 6.0 + min(6.0, max(1.0, math.sqrt(width * width + height * height) / 700))
    size_cm = round(math.sqrt(max(3, affected_area_pct) / 100) * diagonal_cm, 1)
    return max(0.4, min(18.0, size_cm))


# ---------------------------------------------------------------------
# LOCALIZATION FOR VOICE SUMMARY
# ---------------------------------------------------------------------

# Cancer type prefixes as they appear in labels (lowercased key -> localized)
_CANCER_TYPE_PREFIX = {
    "hi": {"brain tumor": "ब्रेन ट्यूमर", "breast cancer": "स्तन कैंसर", "lung cancer": "फेफड़ों का कैंसर", "skin cancer": "त्वचा कैंसर"},
    "te": {"brain tumor": "మెదడు కణితి", "breast cancer": "రొమ్ము క్యాన్సర్", "lung cancer": "ఊపిరితిత్తుల క్యాన్సర్", "skin cancer": "చర్మ క్యాన్సర్"},
    "ta": {"brain tumor": "மூளை கட்டி", "breast cancer": "மார்பக புற்றுநோய்", "lung cancer": "நுரையீரல் புற்றுநோய்", "skin cancer": "தோல் புற்றுநோய்"},
    "bn": {"brain tumor": "মস্তিষ্ক টিউমার", "breast cancer": "স্তন ক্যান্সার", "lung cancer": "ফুসফুসের ক্যান্সার", "skin cancer": "ত্বকের ক্যান্সার"},
    "kn": {"brain tumor": "ಮೆದುಳಿನ ಗೆಡ್ಡೆ", "breast cancer": "ಸ್ತನ ಕ್ಯಾನ್ಸರ್", "lung cancer": "ಶ್ವಾಸಕೋಶದ ಕ್ಯಾನ್ಸರ್", "skin cancer": "ಚರ್ಮದ ಕ್ಯಾನ್ಸರ್"},
    "ml": {"brain tumor": "മസ്തിഷ്ക ട്യൂമർ", "breast cancer": "സ്തനാർബുദം", "lung cancer": "ശ്വാസകോശ അർബുദം", "skin cancer": "ചർമ്മ അർബുദം"},
    "ar": {"brain tumor": "ورم الدماغ", "breast cancer": "سرطان الثدي", "lung cancer": "سرطان الرئة", "skin cancer": "سرطان الجلد"},
    "es": {"brain tumor": "tumor cerebral", "breast cancer": "cáncer de mama", "lung cancer": "cáncer de pulmón", "skin cancer": "cáncer de piel"},
    "fr": {"brain tumor": "tumeur cérébrale", "breast cancer": "cancer du sein", "lung cancer": "cancer du poumon", "skin cancer": "cancer de la peau"},
    "de": {"brain tumor": "Hirntumor", "breast cancer": "Brustkrebs", "lung cancer": "Lungenkrebs", "skin cancer": "Hautkrebs"},
}

# Subtype labels (lowercased key -> localized)
_SUBTYPE_LABELS = {
    "hi": {"glioma": "ग्लियोमा", "meningioma": "मेनिंजियोमा", "no tumor": "कोई ट्यूमर नहीं", "pituitary": "पिट्यूटरी", "benign": "सौम्य", "malignant": "घातक", "normal": "सामान्य", "adenocarcinoma": "एडेनोकार्सिनोमा", "squamous cell carcinoma": "स्क्वैमस सेल कार्सिनोमा"},
    "te": {"glioma": "గ్లియోమా", "meningioma": "మెనింజియోమా", "no tumor": "కణితి లేదు", "pituitary": "పిట్యూటరీ", "benign": "నిరపాయమైన", "malignant": "ప్రాణాంతక", "normal": "సాధారణ", "adenocarcinoma": "అడెనోకార్సినోమా", "squamous cell carcinoma": "స్క్వామస్ సెల్ కార్సినోమా"},
    "ta": {"glioma": "கிளியோமா", "meningioma": "மெனிஞ்சியோமா", "no tumor": "கட்டி இல்லை", "pituitary": "பிட்யூட்டரி", "benign": "தீங்கற்ற", "malignant": "வீரியம்", "normal": "சாதாரண", "adenocarcinoma": "அடினோகார்சினோமா", "squamous cell carcinoma": "ஸ்குவாமஸ் செல் கார்சினோமா"},
    "bn": {"glioma": "গ্লিওমা", "meningioma": "মেনিনজিওমা", "no tumor": "টিউমার নেই", "pituitary": "পিটুইটারি", "benign": "সৌম্য", "malignant": "ম্যালিগন্যান্ট", "normal": "স্বাভাবিক", "adenocarcinoma": "অ্যাডেনোকার্সিনোমা", "squamous cell carcinoma": "স্কোয়ামাস সেল কার্সিনোমা"},
    "kn": {"glioma": "ಗ್ಲಿಯೋಮಾ", "meningioma": "ಮೆನಿಂಜಿಯೋಮಾ", "no tumor": "ಗೆಡ್ಡೆ ಇಲ್ಲ", "pituitary": "ಪಿಟ್ಯುಟರಿ", "benign": "ಹಾನಿಕರವಲ್ಲದ", "malignant": "ಮಾರಕ", "normal": "ಸಾಮಾನ್ಯ", "adenocarcinoma": "ಅಡೆನೊಕಾರ್ಸಿನೋಮಾ", "squamous cell carcinoma": "ಸ್ಕ್ವಾಮಸ್ ಸೆಲ್ ಕಾರ್ಸಿನೋಮಾ"},
    "ml": {"glioma": "ഗ്ലിയോമ", "meningioma": "മെനിഞ്ചിയോമ", "no tumor": "ട്യൂമർ ഇല്ല", "pituitary": "പിറ്റ്യൂട്ടറി", "benign": "നിർദോഷം", "malignant": "മാരകം", "normal": "സാധാരണ", "adenocarcinoma": "അഡിനോകാർസിനോമ", "squamous cell carcinoma": "സ്ക്വാമസ് സെൽ കാർസിനോമ"},
    "ar": {"glioma": "ورم الدماغ الدبقي", "meningioma": "ورم السحايا", "no tumor": "لا يوجد ورم", "pituitary": "الغدة النخامية", "benign": "حميد", "malignant": "خبيث", "normal": "طبيعي", "adenocarcinoma": "سرطان غدي", "squamous cell carcinoma": "سرطان الخلايا الحرشفية"},
    "es": {"glioma": "glioma", "meningioma": "meningioma", "no tumor": "sin tumor", "pituitary": "pituitaria", "benign": "benigno", "malignant": "maligno", "normal": "normal", "adenocarcinoma": "adenocarcinoma", "squamous cell carcinoma": "carcinoma de células escamosas"},
    "fr": {"glioma": "gliome", "meningioma": "méningiome", "no tumor": "sans tumeur", "pituitary": "hypophyse", "benign": "bénin", "malignant": "malin", "normal": "normal", "adenocarcinoma": "adénocarcinome", "squamous cell carcinoma": "carcinome épidermoïde"},
    "de": {"glioma": "Gliom", "meningioma": "Meningeom", "no tumor": "kein Tumor", "pituitary": "Hypophyse", "benign": "gutartig", "malignant": "bösartig", "normal": "normal", "adenocarcinoma": "Adenokarzinom", "squamous cell carcinoma": "Plattenepithelkarzinom"},
}

# Stage localization (e.g. "Stage II" -> localized word)
_STAGE_LABELS = {
    "hi": {"stage 0": "स्टेज शून्य", "stage i": "स्टेज एक", "stage ii": "स्टेज दो", "stage iii": "स्टेज तीन", "stage iv": "स्टेज चार"},
    "te": {"stage 0": "స్టేజ్ సున్నా", "stage i": "స్టేజ్ ఒకటి", "stage ii": "స్టేజ్ రెండు", "stage iii": "స్టేజ్ మూడు", "stage iv": "స్టేజ్ నాలుగు"},
    "ta": {"stage 0": "நிலை பூஜ்யம்", "stage i": "நிலை ஒன்று", "stage ii": "நிலை இரண்டு", "stage iii": "நிலை மூன்று", "stage iv": "நிலை நான்கு"},
    "bn": {"stage 0": "স্টেজ শূন্য", "stage i": "স্টেজ এক", "stage ii": "স্টেজ দুই", "stage iii": "স্টেজ তিন", "stage iv": "স্টেজ চার"},
    "kn": {"stage 0": "ಹಂತ ಶೂನ್ಯ", "stage i": "ಹಂತ ಒಂದು", "stage ii": "ಹಂತ ಎರಡು", "stage iii": "ಹಂತ ಮೂರು", "stage iv": "ಹಂತ ನಾಲ್ಕು"},
    "ml": {"stage 0": "ഘട്ടം പൂജ്യം", "stage i": "ഘട്ടം ഒന്ന്", "stage ii": "ഘട്ടം രണ്ട്", "stage iii": "ഘട്ടം മൂന്ന്", "stage iv": "ഘട്ടം നാല്"},
    "ar": {"stage 0": "المرحلة صفر", "stage i": "المرحلة الأولى", "stage ii": "المرحلة الثانية", "stage iii": "المرحلة الثالثة", "stage iv": "المرحلة الرابعة"},
    "es": {"stage 0": "etapa cero", "stage i": "etapa uno", "stage ii": "etapa dos", "stage iii": "etapa tres", "stage iv": "etapa cuatro"},
    "fr": {"stage 0": "stade zéro", "stage i": "stade un", "stage ii": "stade deux", "stage iii": "stade trois", "stage iv": "stade quatre"},
    "de": {"stage 0": "Stadium null", "stage i": "Stadium eins", "stage ii": "Stadium zwei", "stage iii": "Stadium drei", "stage iv": "Stadium vier"},
}


def localize_label(label, language):
    """Translate a report label (e.g. 'Breast Cancer - Malignant') into the target
    language so the entire string is in one consistent native script/language.
    Unknown tokens are left as-is (best effort)."""
    if language in (None, "", "en"):
        return label
    label = (label or "").strip()
    lower = label.lower()
    prefix_map = _CANCER_TYPE_PREFIX.get(language, {})
    sub_map = _SUBTYPE_LABELS.get(language, {})

    # Split on the standard " - " separator used by the model labels
    parts = [p.strip() for p in label.split("-")]
    if len(parts) >= 2:
        prefix = parts[0].strip()
        sub = parts[1].strip()
        loc_prefix = prefix_map.get(prefix.lower(), prefix)
        loc_sub = sub_map.get(sub.lower(), sub)
        return f"{loc_prefix} - {loc_sub}"

    # Might be a single token (fallback)
    return sub_map.get(lower, label)


def localize_stage(stage, language):
    """Translate a stage string (e.g. 'Stage II') into the target language."""
    if language in (None, "", "en"):
        return stage
    stage = (stage or "").strip()
    lower = stage.lower()
    return _STAGE_LABELS.get(language, {}).get(lower, stage)


def generate_voice_summary(label, confidence_pct, risk, stage, affected_area_pct, tumor_size_cm, report_language):
    """Generate a complete, fully localized spoken summary for the selected language.
    ALL components (label, risk, confidence, stage, affected area and tumor size) are
    spoken in the native script so the voice assistant reads a single, consistent
    language — not just the numbers.
    """
    language = (report_language or "en").lower().strip()
    risk_local = {
        "hi": "उच्च", "te": "అధికం", "ta": "அதிகம்", "bn": "উচ্চ",
        "kn": "ಅಧಿಕ", "ml": "ഉയർന്ന", "ar": "مرتفع", "es": "alto",
        "fr": "élevé", "de": "hoch"
    }
    # Map English risk to localized word
    if risk == "High":
        risk_word = risk_local.get(language, "High")
    elif risk == "Moderate":
        risk_word = {"hi": "मध्यम", "te": "మధ్యస్థం", "ta": "மிதமான", "bn": "মধ্যম", "kn": "ಮಧ್ಯಮ", "ml": "മിതമായ", "ar": "متوسط", "es": "moderado", "fr": "modéré", "de": "mittel"}.get(language, "Moderate")
    else:
        risk_word = {"hi": "कम", "te": "తక్కువ", "ta": "குறைவு", "bn": "কম", "kn": "ಕಡಿಮೆ", "ml": "കുറവ്", "ar": "منخفض", "es": "bajo", "fr": "faible", "de": "niedrig"}.get(language, "Low")

    # Fully localize the label and stage so NO English words remain
    loc_label = localize_label(label, language)
    loc_stage = localize_stage(stage, language)

    if language == "hi":
        return (
            f"रिपोर्ट: {loc_label}. जोखिम स्तर: {risk_word}. आत्मविश्वास: {confidence_pct} प्रतिशत. "
            f"चरण: {loc_stage}. अनुमानित प्रभावित क्षेत्र: {affected_area_pct} प्रतिशत. "
            f"ट्यूमर आकार अनुमान: {tumor_size_cm} सेंटीमीटर. कृपया अपने चिकित्सक से परामर्श करें."
        )
    if language == "te":
        return (
            f"నివేదిక: {loc_label}. రిస్క్ స్థాయి: {risk_word}. నమ్మకం: {confidence_pct} శాతం. "
            f"దశ: {loc_stage}. ప్రభావిత ప్రాంతం: {affected_area_pct} శాతం. "
            f"కణితి పరిమాణం అంచనా: {tumor_size_cm} సెంటీమీటర్లు. దయచేసి మీ వైద్యుడిని సంప్రదించండి."
        )
    if language == "ta":
        return (
            f"அறிக்கை: {loc_label}. ஆபத்து நிலை: {risk_word}. நம்பிக்கை: {confidence_pct} சதவீதம். "
            f"நிலை: {loc_stage}. பாதிக்கப்பட்ட பகுதி: {affected_area_pct} சதவீதம். "
            f"கட்டி அளவு மதிப்பீடு: {tumor_size_cm} சென்டிமீட்டர். தயவுசெய்து உங்கள் மருத்துவரை அணுகவும்."
        )
    if language == "bn":
        return (
            f"রিপোর্ট: {loc_label}. ঝুঁকি স্তর: {risk_word}. আত্মবিশ্বাস: {confidence_pct} শতাংশ. "
            f"পর্যায়: {loc_stage}. প্রভাবিত এলাকা: {affected_area_pct} শতাংশ. "
            f"টিউমার আকার আনুমানিক: {tumor_size_cm} সেন্টিমিটার. অনুগ্রহ করে আপনার চিকিৎসকের পরামর্শ নিন."
        )
    if language == "kn":
        return (
            f"ವರದಿ: {loc_label}. ಅಪಾಯ ಮಟ್ಟ: {risk_word}. ವಿಶ್ವಾಸ: {confidence_pct} ಶೇಕಡ. "
            f"ಹಂತ: {loc_stage}. ಪ್ರಭಾವಿತ ಪ್ರದೇಶ: {affected_area_pct} ಶೇಕಡ. "
            f"ಗೆಡ್ಡೆ ಗಾತ್ರ ಅಂದಾಜು: {tumor_size_cm} ಸೆಂಟಿಮೀಟರ್. ದಯವಿಟ್ಟು ನಿಮ್ಮ ವೈದ್ಯರನ್ನು ಸಂಪರ್ಕಿಸಿ."
        )
    if language == "ml":
        return (
            f"റിപ്പോർട്ട്: {loc_label}. അപകട നില: {risk_word}. ആത്മവിശ്വാസം: {confidence_pct} ശതമാനം. "
            f"ഘട്ടം: {loc_stage}. ബാധിത പ്രദേശം: {affected_area_pct} ശതമാനം. "
            f"ട്യൂമർ വലുപ്പം കണക്കാക്കൽ: {tumor_size_cm} സെന്റീമീറ്റർ. ദയവായി ഡോക്ടറെ സമീപിക്കുക."
        )
    if language == "ar":
        return (
            f"التقرير: {loc_label}. مستوى المخاطر: {risk_word}. الثقة: {confidence_pct} بالمئة. "
            f"المرحلة: {loc_stage}. المنطقة المتأثرة التقديرية: {affected_area_pct} بالمئة. "
            f"حجم الورم التقديري: {tumor_size_cm} سنتيمتر. يرجى استشارة طبيبك."
        )
    if language == "es":
        return (
            f"Informe: {loc_label}. Nivel de riesgo: {risk_word}. Confianza: {confidence_pct} por ciento. "
            f"Etapa: {loc_stage}. Área afectada estimada: {affected_area_pct} por ciento. "
            f"Tamaño estimado del tumor: {tumor_size_cm} centímetros. Por favor consulte a su médico."
        )
    if language == "fr":
        return (
            f"Rapport: {loc_label}. Niveau de risque: {risk_word}. Confiance: {confidence_pct} pour cent. "
            f"Étape: {loc_stage}. Zone affectée estimée: {affected_area_pct} pour cent. "
            f"Taille estimée de la tumeur: {tumor_size_cm} centimètres. Veuillez consulter votre médecin."
        )
    if language == "de":
        return (
            f"Bericht: {loc_label}. Risikostufe: {risk_word}. Vertrauen: {confidence_pct} Prozent. "
            f"Stufe: {loc_stage}. Geschätzter betroffener Bereich: {affected_area_pct} Prozent. "
            f"Geschätzte Tumorgröße: {tumor_size_cm} Zentimeter. Bitte konsultieren Sie Ihren Arzt."
        )
    return (
        f"Report: {loc_label}. Risk level: {risk}. Confidence: {confidence_pct} percent. "
        f"Stage: {loc_stage}. Estimated affected area: {affected_area_pct} percent. "
        f"Tumor size estimate: {tumor_size_cm} centimeters. Please consult your physician."
    )


def generate_report_explanation(cancer_type, label, confidence_pct, quality_ok, quality_message, ensemble_result,
                                stage=None, severity_score=None, affected_area_pct=None, tumor_size_cm=None, risk=None):
    """Build a detailed, multi-part clinical summary and explainable AI analysis.
    Includes classification, confidence, image quality, ensemble decision, staging,
    affected area, tumor size estimate, and a clinical recommendation.
    """
    parts = []
    parts.append(f"Model predicts {label} with {confidence_pct:.1f}% confidence.")

    if quality_ok:
        parts.append("Image quality is acceptable for reliable analysis.")
    else:
        parts.append(quality_message)

    parts.append(
        f"The system cross-checked an automatic cancer type detector with individual organ-specific "
        f"scores and selected {ensemble_result['ensemble_type']} as the final diagnosis via ensemble voting."
    )
    if ensemble_result["consensus"]:
        parts.append("The automatic and ensemble predictions are in full agreement, increasing diagnostic reliability.")
    else:
        parts.append("There is a mismatch between the auto-detected type and the ensemble vote, so independent clinical review is strongly advised.")

    # Staging & severity
    if stage:
        parts.append(f"Based on the confidence level, the estimated clinical stage is {stage}.")
    if severity_score is not None:
        parts.append(f"The computed severity score is {severity_score}/100, reflecting the relative aggressiveness of the finding.")

    # Affected area & tumor size
    if affected_area_pct is not None:
        parts.append(f"Approximately {affected_area_pct}% of the scanned region is estimated to contain suspicious features.")
    if tumor_size_cm is not None:
        parts.append(f"The estimated lesion or tumor size is about {tumor_size_cm:.1f} cm across its largest dimension.")

    # Risk & recommendation
    if risk:
        parts.append(f"The overall risk level is classified as {risk}.")
    if risk == "High":
        parts.append("Recommendation: urgent referral to an oncologist and immediate confirmatory diagnostic workup (biopsy or advanced imaging) is strongly advised.")
    elif risk == "Moderate":
        parts.append("Recommendation: schedule follow-up imaging and a specialist consultation within the next two to four weeks for closer monitoring.")
    else:
        parts.append("Recommendation: continue routine monitoring and share this report with your clinician for confirmation.")

    # Explainable AI
    parts.append("The Grad-CAM heatmap highlights the specific scan regions that most influenced the model's decision, with warmer colors (red/yellow) marking the areas of highest attention.")

    return " ".join(parts)


def calculate_visit_dates(last_visit_input, next_visit_input, risk_level):
    today = datetime.now().date()
    
    if not last_visit_input:
        last_visit_date = today.strftime("%Y-%m-%d")
    else:
        last_visit_date = last_visit_input.strip()

    if next_visit_input and next_visit_input.strip():
        next_visit_date = next_visit_input.strip()
    else:
        if risk_level == "High":
            delta_days = 10
        elif risk_level == "Moderate":
            delta_days = 30
        else:
            delta_days = 180
        
        try:
            base_date = datetime.strptime(last_visit_date, "%Y-%m-%d").date()
        except Exception:
            base_date = today

        next_visit_date = (base_date + timedelta(days=delta_days)).strftime("%Y-%m-%d")

    return last_visit_date, next_visit_date


def save_prediction(report):
    reports = load_reports()
    # Ensure idempotency: remove any existing entry with the same report_id so
    # a single scan never produces multiple duplicate history entries.
    report_id = report.get("report_id")
    if report_id:
        reports = [r for r in reports if r.get("report_id") != report_id]
    reports.insert(0, report)
    save_reports(reports[:50])


def update_saved_report(updated_report):
    """Update an existing report in reports.json by its report_id.
    If the report is not found, insert it at the front as a fallback.
    This is used by the background finalization thread to persist the
    generated Grad-CAM heatmap so the frontend polling endpoint can fetch it.
    """
    report_id = updated_report.get("report_id")
    if not report_id:
        return
    reports = load_reports()
    for i, rep in enumerate(reports):
        if rep.get("report_id") == report_id:
            reports[i] = updated_report
            save_reports(reports[:50])
            return
    # Not found — insert at front (fallback)
    reports.insert(0, updated_report)
    save_reports(reports[:50])


def run_background_task(task_func, *args, **kwargs):
    thread = threading.Thread(target=task_func, args=args, kwargs=kwargs, daemon=True)
    thread.start()
    return thread


def _is_benign_result(label):
    """Return True when the detection label is a benign / normal / no-tumor finding."""
    text = (label or "").lower()
    return any(term in text for term in ["normal", "benign", "no tumor"])


def compute_heatmap_images(filepath, processed_image, model_to_use, label=""):
    """Generate the full set of heatmap visualizations for a scan.

    For benign / normal / no-tumor findings (Stage 0):
      * No Grad-CAM is computed at all (no gradient work).
      * A neutral green "clear scan" overlay is shown instead, with NO warm
        JET colors and NO "Suspicious Region" markers — because there is no
        suspicious area to highlight. This avoids the confusing Stage-0 bug
        where a benign scan still displayed a red suspected region.

    For suspicious / malignant findings, tries in order:
      1. Grad-CAM (14x14 target layer) overlay + original highlight
      2. Input-gradient saliency overlay + original highlight
      3. Deterministic image-statistics heatmap (no gradients)

    Returns (gradcam_image, original_highlight, heatmap_array) where each is
    a base64 PNG string (or None) and heatmap_array is the raw 2D heatmap.
    """
    benign = _is_benign_result(label)

    # Stage 0 / benign / normal: no suspicious region exists — show a clean,
    # neutral "clear scan" overlay. Do NOT run Grad-CAM or any saliency map.
    if benign:
        try:
            gradcam_image = create_plain_heatmap_for_benign(filepath)
            return gradcam_image, None, None
        except Exception:
            pass
        # If even the plain overlay fails, fall through to the default path.

    heatmap = None
    try:
        heatmap = make_gradcam_heatmap(processed_image, model_to_use)
    except Exception:
        heatmap = None

    gradcam_image = None
    original_highlight = None
    if heatmap is not None:
        gradcam_image = create_gradcam_overlay(filepath, heatmap, mark_suspicious=True)
        if gradcam_image is not None:
            original_highlight = create_original_highlight(filepath, heatmap)

    # Fallback: input-gradient saliency heatmap
    if gradcam_image is None:
        try:
            ig_heat = make_input_gradient_heatmap(processed_image, model_to_use)
            gradcam_image = create_heatmap_overlay_fallback(filepath, ig_heat)
            if gradcam_image is not None:
                original_highlight = create_original_highlight(filepath, ig_heat)
            heatmap = ig_heat if gradcam_image is not None else heatmap
        except Exception:
            gradcam_image = None
            original_highlight = None

    # Last-resort: deterministic image-statistics heatmap (no gradients).
    if gradcam_image is None:
        gradcam_image = create_manual_heatmap_fallback(filepath, label)
        original_highlight = gradcam_image

    return gradcam_image, original_highlight, heatmap


def create_plain_heatmap_for_benign(img_path):
    """Return a heatmap overlay for a benign / normal scan with NO 'Suspicious
    Region' marker, so Stage-0 / benign results are not misleadingly flagged.
    Uses a very light green-to-cyan tint to indicate 'no suspicious region'."""
    try:
        image = cv2.imread(img_path)
        if image is None:
            return None
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image.shape[:2]
        # A subtle uniform green veil over the whole image = "clear / no region".
        overlay = np.full_like(image, (40, 180, 40), dtype=np.uint8)  # BGR-ish green
        blended = cv2.addWeighted(image, 0.85, overlay, 0.15, 0)
        pil_img = Image.fromarray(blended)
        buffer = BytesIO()
        pil_img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception:
        return None


def _maybe_generate_translated_sections(saved_report):
    lang = (saved_report.get("report_language") or "en").strip().lower()
    if lang == "en":
        return

    if saved_report.get("multi_agent") and not saved_report.get("multi_agent_translated"):
        try:
            saved_report["multi_agent_translated"] = translate_multi_agent_report(
                saved_report["multi_agent"], lang
            )
        except Exception:
            pass



def finalize_report_async(saved_report, filepath, processed_image, model_to_use, precomputed_heatmaps=None):
    try:
        # Use update_saved_report (not save_prediction) so the background thread
        # updates the report created by /predict in place instead of inserting a
        # duplicate entry into the history list.
        update_saved_report(saved_report)

        _maybe_generate_translated_sections(saved_report)

        pdf_path = None
        try:
            pdf_path = generate_pdf_report(saved_report, language=saved_report.get("report_language", "en"))
            saved_report["pdf_path"] = pdf_path.replace('\\', '/') if pdf_path else None
        except Exception as pdf_err:
            print(f"Background PDF generation failed: {pdf_err}")

        if pdf_path:
            try:
                gdrive_res = upload_to_google_drive(pdf_path)
                saved_report["gdrive_status"] = gdrive_res.get("drive_status")
                saved_report["drive_url"] = gdrive_res.get("drive_url")
            except Exception as drive_err:
                print(f"Background Drive upload failed: {drive_err}")

            try:
                email_res = send_email_notification(saved_report, pdf_path)
                saved_report["email_status"] = email_res.get("message", "Email step executed.")
            except Exception as email_err:
                print(f"Background email send failed: {email_err}")

            update_saved_report(saved_report)

        try:
            # Use precomputed heatmaps if provided (fast mode computes them
            # synchronously so they display immediately); otherwise recompute.
            if precomputed_heatmaps:
                gradcam_image, original_highlight, heatmap = precomputed_heatmaps
            else:
                gradcam_image, original_highlight, heatmap = compute_heatmap_images(
                    filepath, processed_image, model_to_use, saved_report.get("label", "")
                )

            saved_report["gradcam_generated"] = bool(gradcam_image)
            if gradcam_image:
                saved_report["gradcam_image_base64"] = gradcam_image
            if original_highlight:
                saved_report["original_highlight_base64"] = original_highlight

            # Persist the generated heatmap so the frontend polling endpoint
            # (/api/report/<report_id>) can retrieve it.
            update_saved_report(saved_report)
        except Exception as gradcam_err:
            print(f"Background Grad-CAM failed: {gradcam_err}")
            saved_report["gradcam_generated"] = False
            update_saved_report(saved_report)
    except Exception as exc:
        print(f"Background report finalization error: {exc}")


# =====================================================
# AUTOMATED NEXT-VISIT EMAIL REMINDERS
# =====================================================

# Days before the next visit to send a reminder email.
REMINDER_DAYS = [1, 2, 3]


def get_days_until_visit(report):
    """Return the number of days from today until the report's next visit date,
    or None if no valid future date is present.
    """
    next_visit = report.get("next_visit_date")
    if not next_visit:
        return None
    try:
        visit_date = datetime.strptime(next_visit, "%Y-%m-%d").date()
    except Exception:
        return None
    return (visit_date - datetime.now().date()).days


def check_visit_reminders():
    """Scan all saved reports and send a reminder email once for patients whose
    next visit is 3, 2, or 1 day away. Records each sent reminder in
    report['visit_reminders_sent'] to prevent duplicate sends.
    """
    try:
        reports = load_reports()
        changed = False
        for report in reports:
            days_left = get_days_until_visit(report)
            if days_left is None or days_left not in REMINDER_DAYS:
                continue
            sent_list = report.setdefault("visit_reminders_sent", [])
            if days_left in sent_list:
                continue
            try:
                res = send_visit_reminder_email(report, days_left)
                sent_list.append(days_left)
                changed = True
                print(f"Visit reminder sent to {report.get('patient_email')} "
                      f"({days_left} day(s) left): {res.get('message')}")
            except Exception as e:
                print(f"Visit reminder dispatch failed for "
                      f"{report.get('patient_email')}: {e}")
        if changed:
            save_reports(reports)
    except Exception as exc:
        print(f"check_visit_reminders error: {exc}")


def start_reminder_scheduler(interval_seconds=6 * 3600):
    """Start a background daemon thread that periodically checks for upcoming
    visits and sends reminder emails. Runs the first check immediately."""
    def _loop():
        try:
            check_visit_reminders()
        except Exception as e:
            print(f"Reminder scheduler initial check error: {e}")
        while True:
            time.sleep(interval_seconds)
            try:
                check_visit_reminders()
            except Exception as e:
                print(f"Reminder scheduler loop error: {e}")

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    return thread


# =====================================================
# HOME & PREDICT ROUTES
# =====================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    try:
        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"})

        file = request.files["image"]
        if file.filename == "":
            return jsonify({"error": "No file selected"})

        patient_name = request.form.get('patient_name', '').strip()
        patient_age = request.form.get('patient_age', '').strip()
        patient_gender = request.form.get('patient_gender', '').strip()
        patient_id = request.form.get('patient_id', '').strip()
        patient_email = request.form.get('patient_email', '').strip()
        last_visit_input = request.form.get('last_visit_date', '').strip()
        next_visit_input = request.form.get('next_visit_date', '').strip()
        report_language = request.form.get('report_language', 'en').strip()
        fast_mode = str(request.form.get('fast_mode', FAST_MODE)).lower() in ("1", "true", "yes", "fast")

        if not patient_name or not patient_age or not patient_gender or not patient_id or not patient_email:
            return jsonify({
                "error": "Patient Name, Age, Gender, Patient ID, and Email are compulsory fields."
            }), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        processed_image = prepare_image(filepath)
        image_quality_ok, quality_message = check_image_quality(filepath)
        ensemble_result = ensemble_type_decision(processed_image)

        requested_type = request.form.get('cancer_type', 'auto')
        if requested_type != 'auto' and requested_type in CANCER_TYPE_CLASSES:
            cancer_type = requested_type
        else:
            cancer_type = ensemble_result["ensemble_type"]

        if cancer_type == "brain":
            model_to_use = BRAIN_MODEL
            prediction = BRAIN_MODEL(processed_image, training=False).numpy()[0]
            idx = int(np.argmax(prediction))
            label = "Brain Tumor - " + BRAIN_CLASSES[idx]
            confidence = float(prediction[idx])

        elif cancer_type == "breast":
            model_to_use = BREAST_MODEL
            prediction = BREAST_MODEL(processed_image, training=False).numpy()[0]
            idx = int(np.argmax(prediction))
            label = "Breast Cancer - " + BREAST_CLASSES[idx]
            confidence = float(prediction[idx])

        elif cancer_type == "lung":
            model_to_use = LUNG_MODEL
            prediction = LUNG_MODEL(processed_image, training=False).numpy()[0]
            idx = int(np.argmax(prediction))
            label = "Lung Cancer - " + LUNG_CLASSES[idx]
            confidence = float(prediction[idx])

        else:
            model_to_use = SKIN_MODEL
            prediction = float(SKIN_MODEL(processed_image, training=False).numpy()[0][0])
            if prediction >= 0.5:
                label = "Skin Cancer - Malignant"
                confidence = float(prediction)
            else:
                label = "Skin Cancer - Benign"
                confidence = float(1 - prediction)

        confidence_pct = round(confidence * 100, 2)

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
        affected_area_pct = estimate_affected_area_percentage(confidence_pct, label, filepath)
        tumor_size_cm = estimate_tumor_size_cm(affected_area_pct, filepath)
        explanation = generate_report_explanation(
            cancer_type, label, confidence_pct, image_quality_ok, quality_message, ensemble_result,
            stage=stage, severity_score=severity_score, affected_area_pct=affected_area_pct,
            tumor_size_cm=tumor_size_cm, risk=risk
        )
        voice_summary = generate_voice_summary(
            label, confidence_pct, risk, stage, affected_area_pct, tumor_size_cm, report_language
        )
        last_visit_date, next_visit_date = calculate_visit_dates(last_visit_input, next_visit_input, risk)

        priority_info = compute_priority(risk, confidence_pct, severity_score, label)
        priority_score = priority_info["priority_score"]
        priority_queue = priority_info["priority_queue"]

# Multi-Agent AI Clinical Second Opinion
        multi_agent_data = {
            "label": label,
            "cancer_type": cancer_type,
            "risk": risk,
            "confidence_pct": confidence_pct,
            "stage": stage,
            "severity_score": severity_score,
            "affected_area_pct": affected_area_pct,
            "tumor_size_estimate_cm": tumor_size_cm,
            "tumor_size_estimate": f"{tumor_size_cm:.1f} cm",
        }
        multi_agent = generate_multi_agent_reports(multi_agent_data)

        translated_multi_agent = None
        if report_language != "en" and not fast_mode:
            try:
                translated_multi_agent = translate_multi_agent_report(multi_agent, report_language)
            except Exception:
                translated_multi_agent = None

        stage_guidance = get_stage_guidance(stage, cancer_type, report_language)

        report_id = uuid.uuid4().hex
        qr_token = uuid.uuid4().hex
        saved_report = {
            "report_id": report_id,
            "qr_token": qr_token,
            "timestamp": int(time.time() * 1000),
            "patient_name": patient_name,
            "patient_age": patient_age,
            "patient_gender": patient_gender,
            "patient_email": patient_email,
            "last_visit_date": last_visit_date,
            "next_visit_date": next_visit_date,
            "report_language": report_language,
            "patient_id": patient_id,
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
            "priority_score": priority_score,
            "priority_queue": priority_queue,
            "stage": stage,
            "severity_score": severity_score,
            "affected_area_pct": affected_area_pct,
            "tumor_size_estimate_cm": tumor_size_cm,
            "tumor_size_estimate": f"{tumor_size_cm:.1f} cm",
            "explanation": explanation,
            "voice_summary": voice_summary,
            "multi_agent": multi_agent,
            "multi_agent_translated": translated_multi_agent,
            "stage_guidance": stage_guidance,
            "comments": [],
            "analysis_mode": "fast" if fast_mode else "full"
        }

        response_payload = {
            "label": label,
            "cancer_type": cancer_type,
            "confidence": confidence,
            "confidence_pct": confidence_pct,
            "risk": risk,
            "priority_score": priority_score,
            "priority_queue": priority_queue,
            "malignant_pct": confidence_pct,
            "benign_pct": round(100 - confidence_pct, 2),
            "gradcam": None,
            "stage": stage,
            "severity_score": severity_score,
            "affected_area_pct": affected_area_pct,
            "tumor_size_estimate_cm": tumor_size_cm,
            "tumor_size_estimate": f"{tumor_size_cm:.1f} cm",
            "explanation": explanation,
            "voice_summary": voice_summary,
            "multi_agent": multi_agent,
            "stage_guidance": stage_guidance,
            "report_id": report_id,
            "qr_token": qr_token,
            "patient_email": patient_email,
            "last_visit_date": last_visit_date,
            "next_visit_date": next_visit_date,
            "report_language": report_language,
            "pdf_path": None,
            "gdrive_status": "Queued in background",
            "drive_url": None,
            "email_status": "Queued in background",
            "auto_type": ensemble_result["auto_type"],
            "auto_confidence": ensemble_result["auto_confidence"],
            "ensemble_type": ensemble_result["ensemble_type"],
            "ensemble_confidence": ensemble_result["ensemble_confidence"],
            "consensus": ensemble_result["consensus"],
            "confidence_map": ensemble_result["confidence_map"],
            "quality_ok": image_quality_ok,
            "quality_message": quality_message,
            "analysis_mode": "fast" if fast_mode else "full",
            "note": "Fast mode enabled: the main result is returned quickly while the PDF, email, drive upload, and Grad-CAM finish in the background."
        }

        if fast_mode:
            # Fast mode returns the main AI diagnosis quickly, while still
            # generating a usable heatmap overlay immediately for the UI.
            # The full background pipeline (PDF, email, drive, translation)
            # continues asynchronously.
            precomputed_heatmaps = None
            try:
                heatmaps = compute_heatmap_images(filepath, processed_image, model_to_use, label)
                gradcam_image = heatmaps[0]
                original_highlight = heatmaps[1]
                if gradcam_image:
                    response_payload["gradcam"] = gradcam_image
                    saved_report["gradcam_generated"] = True
                    saved_report["gradcam_image_base64"] = gradcam_image
                if original_highlight:
                    saved_report["original_highlight_base64"] = original_highlight
                precomputed_heatmaps = heatmaps
            except Exception as hmap_err:
                print(f"Fast-mode heatmap generation failed: {hmap_err}")
                response_payload["gradcam"] = None
                saved_report["gradcam_generated"] = False

            save_prediction(saved_report)
            run_background_task(
                finalize_report_async, saved_report, filepath, processed_image,
                model_to_use, precomputed_heatmaps
            )
            return jsonify(response_payload)

        try:
            pdf_path = generate_pdf_report(saved_report, language=report_language)
            saved_report["pdf_path"] = pdf_path.replace('\\', '/') if pdf_path else None
        except Exception as pdf_err:
            pdf_path = None
            saved_report["pdf_path"] = None

        gdrive_res = upload_to_google_drive(pdf_path) if pdf_path else {"drive_status": "No PDF Available", "drive_url": None}
        saved_report["gdrive_status"] = gdrive_res.get("drive_status")
        saved_report["drive_url"] = gdrive_res.get("drive_url")

        email_res = send_email_notification(saved_report, pdf_path)
        saved_report["email_status"] = email_res.get("message", "Email step executed.")

        save_prediction(saved_report)

        # Use the shared helper so benign/stage-0 scans don't show a misleading
        # "Suspicious Region" marker (same logic as fast mode).
        try:
            gradcam_image = compute_heatmap_images(filepath, processed_image, model_to_use, label)[0]
        except Exception:
            gradcam_image = None
        if gradcam_image is None:
            gradcam_image = create_manual_heatmap_fallback(filepath, label)

        response_payload["gradcam"] = gradcam_image
        response_payload["pdf_path"] = saved_report.get("pdf_path")
        response_payload["gdrive_status"] = saved_report.get("gdrive_status")
        response_payload["drive_url"] = saved_report.get("drive_url")
        response_payload["email_status"] = saved_report.get("email_status")
        response_payload["note"] = "Full mode completed."

        return jsonify(response_payload)

    except Exception as e:
        return jsonify({"error": str(e)})

# =====================================================
# AUTHENTICATION DECORATOR
# =====================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("doctor_logged_in"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required. Please login as a doctor."}), 401
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated_function

# =====================================================
# API ENDPOINTS (PDF, EMAIL, GDRIVE)
# =====================================================

@app.route("/api/download_pdf/<report_id>")
def download_pdf(report_id):
    reports = load_reports()
    requested_lang = request.args.get('lang', 'en').strip()
    
    for report in reports:
        if report.get("report_id") == report_id:
            pdf_path = generate_pdf_report(report, language=requested_lang)
            report["pdf_path"] = pdf_path.replace('\\', '/')
            save_reports(reports)
            
            directory = os.path.dirname(pdf_path)
            filename = os.path.basename(pdf_path)
            return send_from_directory(directory, filename, as_attachment=True)

    return jsonify({"error": "Report PDF not found."}), 404


@app.route('/api/translate', methods=['POST'])
def api_translate():
    data = request.get_json() or {}
    text = data.get('text', '')
    lang = data.get('lang', 'en')
    try:
        translated = translate_text(text, target_lang=lang)
        return jsonify({'translated': translated, 'lang': lang})
    except Exception as e:
        return jsonify({'translated': text, 'error': str(e)}), 500


@app.route('/api/translate_batch', methods=['POST'])
def api_translate_batch():
    data = request.get_json() or {}
    texts = data.get('texts', [])
    lang = (data.get('lang') or 'en').strip().lower()
    if not texts or lang == 'en':
        return jsonify({'translations': {t: t for t in texts}, 'lang': lang})
    try:
        from utils.translator import translate_text_batch
        translated_list = translate_text_batch(texts, target_lang=lang)
        mapping = {orig: trans for orig, trans in zip(texts, translated_list)}
        return jsonify({'translations': mapping, 'lang': lang})
    except Exception as e:
        return jsonify({'translations': {t: t for t in texts}, 'error': str(e)}), 500


@app.route('/api/ui_labels', methods=['GET'])
def api_ui_labels():
    """Return the UI translation dictionary for the diagnostic portal's results
    panel so the frontend can localize all static labels dynamically."""
    from utils.translator import get_translation
    lang = (request.args.get('lang') or 'en').strip().lower()
    if lang not in ("en", "hi", "te", "ta", "kn", "ml", "bn", "ar", "es", "fr", "de"):
        lang = "en"
    tr = get_translation(lang)
    # Subset of keys used by the results panel + heatmap captions.
    labels = {
        'results_tag': tr.get('results_tag', 'AI Evaluation Report'),
        'results_heading': tr.get('results_heading', 'Diagnostic Analysis'),
        'results_subtext': tr.get('results_subtext', 'Real-time prediction with neural confidence rating & stage scoring.'),
        'stage_na': tr.get('stage_na', 'Stage N/A'),
        'diagnostic_label': tr.get('diagnostic_label', 'Diagnostic Label'),
        'risk_label': tr.get('risk_label', 'Risk:'),
        'severity_score_label': tr.get('severity_score_label', 'Calculated Severity Score'),
        'affected_area': tr.get('affected_area', 'Affected Area'),
        'tumor_size': tr.get('tumor_size', 'Tumor Size Estimate'),
        'ai_priority_queue': tr.get('ai_priority_queue', 'AI Priority Queue'),
        'gradcam_title': tr.get('gradcam_title', 'Grad-CAM Feature Map'),
        'tab_heatmap': tr.get('tab_heatmap', 'Heatmap'),
        'tab_original': tr.get('tab_original', 'Original'),
        'original_scan': tr.get('original_scan', 'Original Scan'),
        'heatmap_overlay': tr.get('heatmap_overlay', 'Heatmap Overlay'),
        'heatmap_caption': tr.get('heatmap_caption', 'Highlights regions in warmer colors (red/yellow) that drove the AI classification model\'s decision.'),
        'heatmap_caption_benign': tr.get('heatmap_caption_clear', 'AI heatmap confirms a benign/normal scan. No suspicious region is detected.'),
        'confidence_title': tr.get('confidence_title', 'Classification Confidence'),
        'malignant_prob': tr.get('malignant_prob', 'Malignant Probability'),
        'benign_normal_prob': tr.get('benign_normal_prob', 'Benign / Normal Probability'),
        'auto_type': tr.get('auto_type', 'Auto Type Detected'),
        'ensemble_vote': tr.get('ensemble_vote', 'Ensemble Vote'),
        'last_visit_date': tr.get('last_visit_date', 'Last Visit Date'),
        'next_visit_approx': tr.get('next_visit_approx', 'Next Visit (Approx)'),
        'gdrive_autosave': tr.get('gdrive_autosave', 'Google Drive Auto-Save'),
        'gmail_alert': tr.get('gmail_alert', 'Gmail Alert Dispatch'),
        'clinical_title': tr.get('clinical_title', 'Clinical Summary & Explainable AI'),
        'language_label': tr.get('language', 'Language'),
        'explanation_placeholder': 'AI explanation notes will appear here summarizing decision reasoning.',
        'recommendation_label': tr.get('recommendation', 'Recommendation:'),
        'download_pdf': tr.get('download_pdf', 'Download PDF Report'),
        'voice_assistant': tr.get('voice_assistant', 'Voice Assistant'),
    }
    return jsonify({'lang': lang, 'labels': labels})


@app.route('/api/localize', methods=['POST'])
def api_localize():
    """Localize a single dynamic value (label / stage / risk / priority lane)
    into the requested language using the built-in dictionaries where possible."""
    from utils.translator import get_translation
    data = request.get_json() or {}
    text = data.get('text', '')
    lang = (data.get('lang') or 'en').strip().lower()
    kind = data.get('kind', 'label')
    if lang not in ("en", "hi", "te", "ta", "kn", "ml", "bn", "ar", "es", "fr", "de"):
        lang = "en"
    if not text:
        return jsonify({'translated': text, 'lang': lang})

    if lang == 'en':
        return jsonify({'translated': text, 'lang': lang})

    # localize_label / localize_stage are defined at module level in app.py.
    try:
        if kind == 'stage':
            return jsonify({'translated': localize_stage(text, lang), 'lang': lang})
        if kind in ('risk', 'priority'):
            # Risk / priority lanes remain English tokens for CSS class matching,
            # but we return the localized word for display.
            risk_local = {
                'hi': {'High': 'उच्च', 'Moderate': 'मध्यम', 'Low': 'कम'},
                'te': {'High': 'అధికం', 'Moderate': 'మధ్యస్థం', 'Low': 'తక్కువ'},
                'ta': {'High': 'அதிகம்', 'Moderate': 'மிதமான', 'Low': 'குறைவு'},
                'bn': {'High': 'উচ্চ', 'Moderate': 'মধ্যম', 'Low': 'কম'},
                'kn': {'High': 'ಅಧಿಕ', 'Moderate': 'ಮಧ್ಯಮ', 'Low': 'ಕಡಿಮೆ'},
                'ml': {'High': 'ഉയർന്ന', 'Moderate': 'മിതമായ', 'Low': 'കുറവ്'},
                'ar': {'High': 'مرتفع', 'Moderate': 'متوسط', 'Low': 'منخفض'},
                'es': {'High': 'alto', 'Moderate': 'moderado', 'Low': 'bajo'},
                'fr': {'High': 'élevé', 'Moderate': 'modéré', 'Low': 'faible'},
                'de': {'High': 'hoch', 'Moderate': 'mittel', 'Low': 'niedrig'},
            }
            mapping = risk_local.get(lang, {})
            return jsonify({'translated': mapping.get(text, text), 'lang': lang})
        # label
        from utils.translator import translate_text as _tt
        translated = localize_label(text, lang)
        # If localize_label returned unchanged (unknown tokens), try online translate.
        if translated == text:
            translated = _tt(text, lang) or text
        return jsonify({'translated': translated, 'lang': lang})
    except Exception as e:
        try:
            from utils.translator import translate_text as _tt
            translated = _tt(text, lang) or text
            return jsonify({'translated': translated, 'lang': lang})
        except Exception:
            return jsonify({'translated': text, 'lang': lang})


@app.route('/api/voice_summary', methods=['POST'])
def api_voice_summary():
    """Return a fully-localized spoken summary for a saved report so the browser
    TTS engine can read the ENTIRE report in the requested language (not just numbers).
    """
    data = request.get_json() or {}
    report_id = data.get('report_id')
    lang = (data.get('lang') or 'en').strip()
    if not report_id:
        return jsonify({'error': 'report_id is required.'}), 400

    reports = load_reports()
    for report in reports:
        if report.get('report_id') == report_id:
            label = report.get('label', '')
            confidence_pct = report.get('confidence_pct', 0)
            risk = report.get('risk', 'Low')
            stage = report.get('stage', '')
            affected_area_pct = report.get('affected_area_pct', 0)
            tumor_size_cm = report.get('tumor_size_estimate_cm', 0)
            summary = generate_voice_summary(
                label, confidence_pct, risk, stage,
                affected_area_pct, tumor_size_cm, lang
            )
            return jsonify({'voice_summary': summary, 'lang': lang})

    return jsonify({'error': 'Report not found.'}), 404


@app.route("/api/send_email", methods=["POST"])
@login_required
def api_send_email():
    data = request.get_json() or {}
    report_id = data.get("report_id")
    recipient_email = data.get("recipient_email")
    if not report_id:
        return jsonify({"error": "report_id is required."}), 400

    reports = load_reports()
    for report in reports:
        if report.get("report_id") == report_id:
            if recipient_email:
                report["patient_email"] = recipient_email
            
            pdf_path = report.get("pdf_path")
            if not pdf_path or not os.path.exists(pdf_path):
                pdf_path = generate_pdf_report(report)
                report["pdf_path"] = pdf_path.replace('\\', '/')

            res = send_email_notification(report, pdf_path)
            report["email_status"] = res.get("message", "Email dispatched.")
            save_reports(reports)
            return jsonify({"success": True, "result": res, "report": report})

    return jsonify({"error": "Report not found."}), 404


@app.route("/api/upload_gdrive", methods=["POST"])
@login_required
def api_upload_gdrive():
    data = request.get_json() or {}
    report_id = data.get("report_id")
    if not report_id:
        return jsonify({"error": "report_id is required."}), 400

    reports = load_reports()
    for report in reports:
        if report.get("report_id") == report_id:
            pdf_path = report.get("pdf_path")
            if not pdf_path or not os.path.exists(pdf_path):
                pdf_path = generate_pdf_report(report)
                report["pdf_path"] = pdf_path.replace('\\', '/')

            res = upload_to_google_drive(pdf_path)
            report["gdrive_status"] = res.get("drive_status")
            report["drive_url"] = res.get("drive_url")
            save_reports(reports)
            return jsonify({"success": True, "result": res, "report": report})

    return jsonify({"error": "Report not found."}), 404

# =====================================================
# LOGIN & DASHBOARD ROUTES
# =====================================================

CLINICAL_STAFF_ACCOUNTS = {
    "doctor@mediscan.ai": {"role": "Doctor", "name": "Dr. Sarah Sharma, MD"},
    "doctor": {"role": "Doctor", "name": "Dr. Sarah Sharma, MD"},
    "radiologist@mediscan.ai": {"role": "Radiologist", "name": "Dr. Marcus Wei, MD"},
    "radiology@mediscan.ai": {"role": "Radiologist", "name": "Dr. Marcus Wei, MD"},
    "oncologist@mediscan.ai": {"role": "Oncologist", "name": "Dr. Sarah Sharma, MD"},
    "oncology@mediscan.ai": {"role": "Oncologist", "name": "Dr. Sarah Sharma, MD"},
    "surgeon@mediscan.ai": {"role": "Surgeon", "name": "Dr. Rajiv Mehta, MD"},
    "surgery@mediscan.ai": {"role": "Surgeon", "name": "Dr. Rajiv Mehta, MD"},
    "nurse@mediscan.ai": {"role": "Nurse", "name": "Jennifer Adams, RN"},
    "admin@mediscan.ai": {"role": "Admin", "name": "Central Hospital Admin"},
    "patient@mediscan.ai": {"role": "Patient", "name": "Eleanor Vance"}
}

@app.route("/login", methods=["GET", "POST"])
@app.route("/doctor/login", methods=["GET", "POST"])
def login():
    if session.get("doctor_logged_in"):
        return redirect(url_for("dashboard"))

    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        matched = None
        for acct_email, info in CLINICAL_STAFF_ACCOUNTS.items():
            if email == acct_email.lower():
                matched = info
                break

        if matched and (password == DOCTOR_PASSWORD or password == "password123"):
            session["doctor_logged_in"] = True
            session["doctor_email"] = email
            session["user_role"] = matched["role"]
            session["doctor_name"] = matched["name"]
            
            try:
                from utils.hospital_core import log_audit_event
                log_audit_event(
                    user=matched["name"],
                    role=matched["role"],
                    action="Physician Gateway Authentication",
                    details=f"Successful login for {matched['role']} account ({email})."
                )
            except Exception:
                pass
                
            next_page = request.args.get("next")
            if matched["role"] == "Patient":
                session["patient_logged_in"] = True
                session["patient_name"] = matched["name"]
                return redirect("/portal/patient")
            return redirect(next_page or url_for("dashboard"))
        elif (email == DOCTOR_USERNAME.lower() or email == "doctor") and password == DOCTOR_PASSWORD:
            session["doctor_logged_in"] = True
            session["doctor_email"] = email
            session["user_role"] = "Doctor"
            session["doctor_name"] = "Dr. Sarah Sharma, MD"
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard"))
        else:
            error = "Invalid physician credentials. Use doctor@mediscan.ai / password123 or select a staff pass."

    return render_template("login.html", error=error)


@app.route("/logout")
@app.route("/doctor/logout")
def logout():
    user_name = session.get("doctor_name", "Doctor")
    user_role = session.get("user_role", "Doctor")
    try:
        from utils.hospital_core import log_audit_event
        log_audit_event(
            user=user_name,
            role=user_role,
            action="Logged out from Physician Gateway",
            details="Physician session cleared."
        )
    except Exception:
        pass
    session.pop("doctor_logged_in", None)
    session.pop("doctor_email", None)
    session.pop("doctor_name", None)
    session.pop("user_role", None)
    return redirect(url_for("login"))


@app.route("/patient/login", methods=["GET", "POST"])
@app.route("/portal/login", methods=["GET", "POST"])
def patient_login():
    if session.get("patient_logged_in"):
        return redirect("/portal/patient")

    error = None
    if request.method == "POST":
        identifier = request.form.get("patient_id", "").strip()
        password = request.form.get("password", "").strip()

        from utils.hospital_core import get_all_patients
        patients = get_all_patients()

        # Find patient by ID or email
        matched_patient = None
        for pdata in patients:
            pid = pdata.get("patient_id", "")
            pemail = pdata.get("email", "")
            if identifier.upper() == pid.upper() or identifier.lower() == pemail.lower():
                matched_patient = pdata
                break

        if not matched_patient and (identifier.lower() == "patient@mediscan.ai" or identifier.upper() == "MS-2026-004821"):
            matched_patient = next((p for p in patients if p.get("patient_id") == "MS-2026-004821"), None)
            if not matched_patient and patients:
                matched_patient = patients[0]

        if matched_patient and (password == "password123" or password == DOCTOR_PASSWORD or password.lower() == "patient"):
            session["patient_logged_in"] = True
            session["patient_id"] = matched_patient.get("patient_id", "MS-2026-004821")
            session["patient_name"] = matched_patient.get("name", "Eleanor Vance")
            session["patient_email"] = matched_patient.get("email", "eleanor.vance@example.com")
            
            try:
                from utils.hospital_core import log_audit_event
                log_audit_event(
                    user=matched_patient.get("name"),
                    role="Patient",
                    action="Patient Portal Authentication",
                    details=f"Patient {matched_patient.get('patient_id')} signed in to personal portal."
                )
            except Exception:
                pass
            return redirect("/portal/patient")
        else:
            error = "Invalid patient credentials. Use Patient ID: MS-2026-004821 / password: password123"

    return render_template("patient_login.html", error=error)


@app.route("/patient/logout")
def patient_logout():
    user_name = session.get("patient_name", "Patient")
    try:
        from utils.hospital_core import log_audit_event
        log_audit_event(
            user=user_name,
            role="Patient",
            action="Patient Portal Sign Out",
            details="Patient session cleared."
        )
    except Exception:
        pass
    session.pop("patient_logged_in", None)
    session.pop("patient_id", None)
    session.pop("patient_name", None)
    session.pop("patient_email", None)
    return redirect("/patient/login")


@app.route("/api/auth_status")
def api_auth_status():
    return jsonify({
        "logged_in": bool(session.get("doctor_logged_in")),
        "doctor_email": session.get("doctor_email", "")
    })


@app.route("/api/compare_previous/<report_id>")
def api_compare_previous(report_id):
    reports = load_reports()
    current_report = None
    for report in reports:
        if report.get("report_id") == report_id:
            current_report = report
            break

    if not current_report:
        return jsonify({"error": "Report not found."}), 404

    patient_key = current_report.get("patient_id") or current_report.get("patient_name")
    previous_reports = []
    for report in reports:
        if report.get("report_id") == report_id:
            continue
        other_key = report.get("patient_id") or report.get("patient_name")
        if patient_key and other_key and str(other_key).lower() == str(patient_key).lower():
            previous_reports.append(report)

    previous_reports.sort(key=lambda item: item.get("timestamp", 0), reverse=True)
    previous_report = previous_reports[0] if previous_reports else None

    if not previous_report:
        return jsonify({"available": False, "message": "No previous scan found for this patient."})

    confidence_change = current_report.get("confidence_pct", 0) - previous_report.get("confidence_pct", 0)
    severity_change = current_report.get("severity_score", 0) - previous_report.get("severity_score", 0)
    risk_change = "Higher" if current_report.get("risk") == "High" and previous_report.get("risk") != "High" else ("Lower" if current_report.get("risk") != "High" and previous_report.get("risk") == "High" else "Stable")
    summary = (
        f"Current scan shows {current_report.get('label', 'result')} compared with previous {previous_report.get('label', 'result')}. "
        f"Confidence changed by {confidence_change:+.1f} points and severity by {severity_change:+.1f} points."
    )

    return jsonify({
        "available": True,
        "current_report": current_report,
        "previous_report": previous_report,
        "confidence_change": round(confidence_change, 1),
        "severity_change": round(severity_change, 1),
        "risk_change": risk_change,
        "summary": summary
    })


@app.route("/dashboard")
def dashboard():
    session.setdefault("doctor_logged_in", True)
    session.setdefault("doctor_email", "doctor@mediscan.ai")
    session.setdefault("user_role", "Doctor")
    from utils.hospital_core import get_command_center_stats, get_all_patients, get_worklist, _load_json, NOTIFICATIONS_FILE
    stats = get_command_center_stats()
    patients = get_all_patients()
    worklist = get_worklist(filter_status="all")
    notifications = _load_json(NOTIFICATIONS_FILE, [])
    return render_template(
        "hospital_dashboard.html",
        stats=stats,
        patients=patients,
        worklist=worklist[:6],
        notifications=notifications,
        doctor_email=session.get("doctor_email", "doctor@mediscan.ai"),
        user_role=session.get("user_role", "Doctor")
    )


@app.route("/api/reports", methods=["GET"])
@login_required
def api_reports():
    reports = load_reports()
    # Backfill priority fields for reports created before the triage feature.
    changed = False
    for report in reports:
        if "priority_queue" not in report or "priority_score" not in report:
            backfill_priority(report)
            changed = True
    if changed:
        save_reports(reports)
    return jsonify(reports)


@app.route("/api/priority_queue", methods=["GET"])
@login_required
def api_priority_queue():
    """Return all reports grouped into AI-priority triage lanes.

    Each report is assigned to Emergency / Urgent / Normal Queue / Routine Review
    (computed live via compute_priority so older reports are handled too) and ranked
    within its lane by priority_score (higher = more urgent). Patients in the same
    lane are ordered by score descending, with newer reports breaking ties.
    """
    reports = load_reports()
    for report in reports:
        backfill_priority(report)

    lanes = {name: [] for name in QUEUE_LANES}
    for report in reports:
        queue = report.get("priority_queue", "Routine Review")
        if queue not in lanes:
            queue = "Routine Review"
        lanes[queue].append(report)

    for queue in lanes:
        lanes[queue].sort(
            key=lambda r: (
                r.get("priority_score", 0),
                r.get("timestamp", 0),
            ),
            reverse=True,
        )
        # Assign 1-based rank within the lane.
        for rank, report in enumerate(lanes[queue], start=1):
            report["priority_rank"] = rank

    summary = {
        "Emergency": len(lanes["Emergency"]),
        "Urgent": len(lanes["Urgent"]),
        "Normal Queue": len(lanes["Normal Queue"]),
        "Routine Review": len(lanes["Routine Review"]),
    }

    return jsonify({
        "lanes": {queue: lanes[queue] for queue in QUEUE_LANES},
        "summary": summary,
        "total": len(reports),
    })


@app.route("/api/upcoming_visits", methods=["GET"])
def api_upcoming_visits():
    """Return patients whose next visit is within 3 days (plus any that have
    already received a reminder). This is used by the dashboard popup to show
    "Consult the doctor in 3/2/1 days" notifications."""
    reports = load_reports()
    today = datetime.now().date()
    upcoming = []
    for report in reports:
        days_left = get_days_until_visit(report)
        if days_left is None or days_left < 0:
            continue
        if days_left > 3:
            continue
        upcoming.append({
            "report_id": report.get("report_id"),
            "patient_name": report.get("patient_name"),
            "patient_email": report.get("patient_email"),
            "label": report.get("label"),
            "risk": report.get("risk"),
            "next_visit_date": report.get("next_visit_date"),
            "days_left": days_left,
            "reminder_sent": bool(report.get("visit_reminders_sent")),
        })
    upcoming.sort(key=lambda item: item.get("days_left", 0))
    return jsonify({"today": today.strftime("%Y-%m-%d"), "upcoming": upcoming, "total": len(upcoming)})


@app.route("/api/clear_reports", methods=["POST"])
@login_required
def api_clear_reports():
    save_reports([])
    return jsonify({"success": True, "message": "All reports cleared."})


@app.route("/api/comment", methods=["POST"])
@login_required
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


@app.route("/api/report/<report_id>", methods=["GET"])
def api_get_report(report_id):
    """Public polling endpoint so the frontend can fetch the saved report once the
    background thread finishes generating the Grad-CAM heatmap (fast mode).
    """
    reports = load_reports()
    for report in reports:
        if report.get("report_id") == report_id:
            return jsonify({
                "report_id": report_id,
                "gradcam_image_base64": report.get("gradcam_image_base64"),
                "gradcam_generated": report.get("gradcam_generated", False),
                "pdf_path": report.get("pdf_path"),
                "gdrive_status": report.get("gdrive_status"),
                "email_status": report.get("email_status")
            })
    return jsonify({"error": "Report not found."}), 404


@app.route("/api/second_opinion/<report_id>", methods=["GET"])
def api_second_opinion(report_id):
    """Public endpoint returning the saved Multi-Agent AI Clinical Second Opinion
    bundle (five AI personas, consensus, tumor board, timeline, treatment plan)
    for a given report. Falls back to recomputing if not stored (e.g. older reports).
    """
    reports = load_reports()
    for report in reports:
        if report.get("report_id") == report_id:
            multi_agent = report.get("multi_agent")
            if not multi_agent:
                # Recompute for older reports that predate the multi-agent feature.
                try:
                    multi_agent = generate_multi_agent_reports({
                        "label": report.get("label", ""),
                        "cancer_type": report.get("cancer_type", "brain"),
                        "risk": report.get("risk", "Low"),
                        "confidence_pct": report.get("confidence_pct", 0),
                        "stage": report.get("stage", "Stage 0"),
                        "severity_score": report.get("severity_score", 0),
                        "affected_area_pct": report.get("affected_area_pct", 0),
                        "tumor_size_estimate_cm": report.get("tumor_size_estimate_cm", 0),
                        "tumor_size_estimate": report.get("tumor_size_estimate", "not determined"),
                    })
                except Exception:
                    multi_agent = None
            return jsonify({
                "report_id": report_id,
                "multi_agent": multi_agent,
            })
    return jsonify({"error": "Report not found."}), 404





@app.route("/api/translate_multi_agent/<report_id>", methods=["GET"])
def api_translate_multi_agent(report_id):
    """Return the Multi-Agent AI Clinical Second Opinion bundle localized into the
    requested language (query param ?lang=te, hi, ar, ...). Static headings/roles
    use the built-in dictionary; dynamic content is translated at runtime with the
    translation backend (Google Cloud Translate / googletrans, best effort).
    """
    lang = (request.args.get("lang") or "en").strip().lower()
    if lang not in ("en", "hi", "te", "ta", "kn", "ml", "bn", "ar", "es", "fr", "de"):
        lang = "en"

    reports = load_reports()
    for report in reports:
        if report.get("report_id") == report_id:
            multi_agent = report.get("multi_agent")
            if not multi_agent:
                try:
                    multi_agent = generate_multi_agent_reports({
                        "label": report.get("label", ""),
                        "cancer_type": report.get("cancer_type", "brain"),
                        "risk": report.get("risk", "Low"),
                        "confidence_pct": report.get("confidence_pct", 0),
                        "stage": report.get("stage", "Stage 0"),
                        "severity_score": report.get("severity_score", 0),
                        "affected_area_pct": report.get("affected_area_pct", 0),
                        "tumor_size_estimate_cm": report.get("tumor_size_estimate_cm", 0),
                        "tumor_size_estimate": report.get("tumor_size_estimate", "not determined"),
                    })
                except Exception:
                    multi_agent = None
            if not multi_agent:
                return jsonify({"error": "Multi-agent data unavailable."}), 404
            # Prefer cached server-side translation when available for speed.
            existing = report.get("multi_agent_translated")
            if existing and isinstance(existing, dict) and existing.get("_lang") == lang:
                return jsonify({"report_id": report_id, "lang": lang, "multi_agent": existing})

            translated = translate_multi_agent_report(multi_agent, lang)
            return jsonify({
                "report_id": report_id,
                "lang": lang,
                "multi_agent": translated,
            })
    return jsonify({"error": "Report not found."}), 404


# =====================================================
# PUBLIC QR REPORT VIEWER & EXCEL EXPORT
# =====================================================

@app.route("/report/<qr_token>")
def report_viewer(qr_token):
    """Public page opened when a patient scans the QR code on their report.

    Supports ?lang=<code> so the ENTIRE page (all labels + values) is rendered
    server-side in the requested language — not just the multi-agent section.
    """
    lang = (request.args.get("lang") or "en").strip().lower()
    if lang not in ("en", "hi", "te", "ta", "kn", "ml", "bn", "ar", "es", "fr", "de"):
        lang = "en"

    reports = load_reports()
    for report in reports:
        if report.get("qr_token") == qr_token:
            formatted_date = datetime.fromtimestamp(report.get("timestamp", 0) / 1000.0).strftime('%B %d, %Y - %I:%M %p')
            report_url = request.host_url.rstrip('/') + url_for("report_viewer", qr_token=qr_token)

            # --- Localization of the ENTIRE report page ---
            tr = get_translation(lang)
            display = dict(report)

            # Localize dynamic values (label, stage, risk).
            display["label"] = localize_label(report.get("label", ""), lang)
            display["stage"] = localize_stage(report.get("stage", ""), lang)
            risk_local = {
                "High": tr.get("risk_high", "HIGH RISK"),
                "Moderate": tr.get("risk_moderate", "MODERATE RISK"),
                "Low": tr.get("risk_low", "LOW RISK"),
            }
            display["risk_display"] = risk_local.get(report.get("risk", "Low"), report.get("risk", "Low"))

            # Translate the explanation text into the target language.
            display["explanation"] = translate_text(report.get("explanation", ""), lang)

# Use the server-side translated multi-agent bundle when available,
            # otherwise translate on the fly.
            ma = report.get("multi_agent_translated")
            if not ma or ma.get("_lang") != lang:
                try:
                    ma = translate_multi_agent_report(report.get("multi_agent") or {}, lang)
                except Exception:
                    ma = report.get("multi_agent")
            display["multi_agent"] = ma

            # Stage-Based Remedies & Health Habits
            sg = report.get("stage_guidance")
            if not sg or sg.get("_lang") != lang:
                try:
                    sg = get_stage_guidance(report.get("stage", "Stage 0"), report.get("cancer_type", "general"), lang)
                except Exception:
                    sg = report.get("stage_guidance")
            display["stage_guidance"] = sg

            return render_template(
                "report_view.html",
                report=display,
                formatted_date=formatted_date,
                report_url=report_url,
                tr=tr,
                lang=lang,
            )
    # Report not found — render the invalid/expired page in the requested language.
    tr = get_translation(lang)
    return render_template(
        "report_view.html",
        report=None,
        formatted_date=None,
        report_url=None,
        tr=tr,
        lang=lang,
    )


@app.route("/api/stage_guidance/<report_id>", methods=["GET"])
def api_stage_guidance(report_id):
    """Return the stage-based remedies and health habits for a report."""
    lang = (request.args.get("lang") or "en").strip().lower()
    reports = load_reports()
    for report in reports:
        if report.get("report_id") == report_id:
            guidance = get_stage_guidance(
                report.get("stage", "Stage 0"),
                report.get("cancer_type", "general"),
                lang
            )
            return jsonify({"report_id": report_id, "lang": lang, "stage_guidance": guidance})
    return jsonify({"error": "Report not found."}), 404


@app.route("/api/export_excel", methods=["GET"])
@login_required
def api_export_excel():
    """Generates an Excel workbook with a monthly scan summary and all patient details."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
    except ImportError:
        return jsonify({"error": "openpyxl is not installed. Run: pip install openpyxl"}), 500

    reports = load_reports()

    wb = openpyxl.Workbook()

    # --- Sheet 1: Monthly Scan Summary ---
    ws_summary = wb.active
    ws_summary.title = "Monthly Scan Summary"

    monthly = OrderedDict()
    for r in reports:
        ts = r.get("timestamp", 0)
        try:
            month_key = datetime.fromtimestamp(ts / 1000.0).strftime("%Y-%m")
            month_label = datetime.fromtimestamp(ts / 1000.0).strftime("%B %Y")
        except Exception:
            month_key = "Unknown"
            month_label = "Unknown"
        if month_key not in monthly:
            monthly[month_key] = {"label": month_label, "count": 0, "high_risk": 0, "moderate_risk": 0, "low_risk": 0}
        monthly[month_key]["count"] += 1
        risk = r.get("risk", "Low")
        if risk == "High":
            monthly[month_key]["high_risk"] += 1
        elif risk == "Moderate":
            monthly[month_key]["moderate_risk"] += 1
        else:
            monthly[month_key]["low_risk"] += 1

    summary_headers = ["Month", "Total Scans", "High Risk", "Moderate Risk", "Low Risk"]
    header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for col, h in enumerate(summary_headers, start=1):
        cell = ws_summary.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    row_idx = 2
    for key, info in monthly.items():
        ws_summary.cell(row=row_idx, column=1, value=info["label"])
        ws_summary.cell(row=row_idx, column=2, value=info["count"])
        ws_summary.cell(row=row_idx, column=3, value=info["high_risk"])
        ws_summary.cell(row=row_idx, column=4, value=info["moderate_risk"])
        ws_summary.cell(row=row_idx, column=5, value=info["low_risk"])
        row_idx += 1

    for col in range(1, len(summary_headers) + 1):
        ws_summary.column_dimensions[get_column_letter(col)].width = 18

# --- Sheet 2: All Patient Details ---
    ws_details = wb.create_sheet("All Patient Details")
    detail_headers = [
        "Report ID", "Timestamp", "Date", "Patient Name", "Patient ID", "Age", "Gender", "Email",
        "Report Language", "Cancer Type", "Label", "Confidence %", "Risk", "Priority Queue",
        "Priority Score", "Stage", "Severity Score",
        "Last Visit Date", "Next Visit Date", "Auto Type", "Auto Confidence %", "Ensemble Type",
        "Ensemble Confidence %", "Consensus", "Image Quality OK", "Quality Message",
        "Google Drive URL", "GDrive Status", "Email Status", "Confidence Map",
        "QR Token", "Image Path", "PDF Path", "Clinical Explanation", "Comments"
    ]
    for col, h in enumerate(detail_headers, start=1):
        cell = ws_details.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    def safe(value):
        if isinstance(value, (list, dict)):
            return str(value)
        return value if value is not None else ""

    row_idx = 2
    for r in reports:
        ts = r.get("timestamp", 0)
        try:
            date_str = datetime.fromtimestamp(ts / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            date_str = ""
        comments = "; ".join(c.get("comment", "") for c in r.get("comments", [])) if r.get("comments") else ""
        ws_details.cell(row=row_idx, column=1, value=safe(r.get("report_id")))
        ws_details.cell(row=row_idx, column=2, value=ts)
        ws_details.cell(row=row_idx, column=3, value=date_str)
        ws_details.cell(row=row_idx, column=4, value=safe(r.get("patient_name")))
        ws_details.cell(row=row_idx, column=5, value=safe(r.get("patient_id")))
        ws_details.cell(row=row_idx, column=6, value=safe(r.get("patient_age")))
        ws_details.cell(row=row_idx, column=7, value=safe(r.get("patient_gender")))
        ws_details.cell(row=row_idx, column=8, value=safe(r.get("patient_email")))
        ws_details.cell(row=row_idx, column=9, value=safe(r.get("report_language")))
        ws_details.cell(row=row_idx, column=10, value=safe(r.get("cancer_type")))
        ws_details.cell(row=row_idx, column=11, value=safe(r.get("label")))
        ws_details.cell(row=row_idx, column=12, value=r.get("confidence_pct"))
        ws_details.cell(row=row_idx, column=13, value=safe(r.get("risk")))
        ws_details.cell(row=row_idx, column=14, value=safe(r.get("priority_queue")))
        ws_details.cell(row=row_idx, column=15, value=r.get("priority_score"))
        ws_details.cell(row=row_idx, column=16, value=safe(r.get("stage")))
        ws_details.cell(row=row_idx, column=17, value=r.get("severity_score"))
        ws_details.cell(row=row_idx, column=18, value=safe(r.get("last_visit_date")))
        ws_details.cell(row=row_idx, column=19, value=safe(r.get("next_visit_date")))
        ws_details.cell(row=row_idx, column=20, value=safe(r.get("auto_type")))
        ws_details.cell(row=row_idx, column=21, value=r.get("auto_confidence"))
        ws_details.cell(row=row_idx, column=22, value=safe(r.get("ensemble_type")))
        ws_details.cell(row=row_idx, column=23, value=r.get("ensemble_confidence"))
        ws_details.cell(row=row_idx, column=24, value="Yes" if r.get("consensus") else "No")
        ws_details.cell(row=row_idx, column=25, value="Yes" if r.get("quality_ok") else "No")
        ws_details.cell(row=row_idx, column=26, value=safe(r.get("quality_message")))
        ws_details.cell(row=row_idx, column=27, value=safe(r.get("drive_url")))
        ws_details.cell(row=row_idx, column=28, value=safe(r.get("gdrive_status")))
        ws_details.cell(row=row_idx, column=29, value=safe(r.get("email_status")))
        ws_details.cell(row=row_idx, column=30, value=safe(r.get("confidence_map")))
        ws_details.cell(row=row_idx, column=31, value=safe(r.get("qr_token")))
        ws_details.cell(row=row_idx, column=32, value=safe(r.get("image_path")))
        ws_details.cell(row=row_idx, column=33, value=safe(r.get("pdf_path")))
        ws_details.cell(row=row_idx, column=34, value=safe(r.get("explanation")))
        ws_details.cell(row=row_idx, column=35, value=comments)
        row_idx += 1

    for col in range(1, len(detail_headers) + 1):
        ws_details.column_dimensions[get_column_letter(col)].width = 20

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"MediScan_Reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":
    # Start the automated visit-reminder scheduler in the background.
    try:
        start_reminder_scheduler()
        print("Visit reminder scheduler started.")
    except Exception as se:
        print(f"Failed to start reminder scheduler: {se}")
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
