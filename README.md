# 🩺 MediScan AI — Medical Image Cancer Detection

A deep learning web app that detects cancer in medical images using
**MobileNetV2 transfer learning** and explains predictions with **Grad-CAM**.

---

## 📁 Project File Structure

```
cancer_detection/
│
├── app.py               ← Flask backend (AI model + API)
├── train_model.py       ← Script to train the model on your dataset
├── requirements.txt     ← Python packages to install
├── cancer_model.h5      ← Saved model (created after training)
│
├── templates/
│   └── index.html       ← Frontend web interface
│
└── dataset/             ← YOUR dataset goes here (see below)
    ├── train/
    │   ├── benign/
    │   └── malignant/
    └── val/
        ├── benign/
        └── malignant/
```

---

## ⚙️ Setup — Step by Step

### Step 1: Install Python
Download Python 3.10 from https://www.python.org/downloads/
✅ Check "Add Python to PATH" during installation.

### Step 2: Open the project in VS Code
```
File → Open Folder → select the cancer_detection folder
```

### Step 3: Open the VS Code Terminal
```
View → Terminal  (or press Ctrl + `)
```

### Step 4: Install required packages
```bash
pip install -r requirements.txt
```
This may take 5–10 minutes (TensorFlow is large).

### Step 5: Run the app (Demo Mode)
```bash
python app.py
```
Then open your browser at: **http://localhost:5000**

For doctor review and report management, visit **http://localhost:5000/dashboard**.

You can upload any image and see the interface — predictions will be
random in demo mode until you train the model.

---

## 🏋️ Training the Model (Optional but recommended)

### Get a dataset
Download a free cancer image dataset from Kaggle:
- Skin lesion: https://www.kaggle.com/datasets/andrewmvd/skin-lesion-images-for-melanoma-classification
- Chest X-ray: https://www.kaggle.com/datasets/paultimothymooney/chest-xray-pneumonia
- Breast histopathology: https://www.kaggle.com/datasets/paultimothymooney/breast-histopathology-images

### Organise the images
Place images into this folder structure:
```
dataset/train/benign/      ← benign images for training
dataset/train/malignant/   ← malignant images for training
dataset/val/benign/        ← benign images for validation
dataset/val/malignant/     ← malignant images for validation
```
Aim for at least 200 images per class for decent results.

### Start training
```bash
python train_model.py
```
This will create `cancer_model.h5`. Training takes 20–60 minutes
depending on your computer. A GPU speeds this up dramatically.

### Restart the app
```bash
python app.py
```
Now your model makes real predictions!

---

## 🖥️ How to Use the App

1. Open http://localhost:5000 in your browser
2. Drag & drop or click to upload a medical image
3. Click **Analyse Image**
4. View:
   - ✅ Malignant / Benign classification
   - 📊 Probability percentages
   - 🗺️ Grad-CAM heatmap showing suspicious regions
   - ⚠️ Risk level (Low / Moderate / High)

---

## 🧠 How It Works (For Your Report)

| Component          | Technology                  |
|--------------------|-----------------------------|
| Backend            | Python + Flask              |
| Deep Learning      | TensorFlow / Keras          |
| Model Architecture | MobileNetV2 (Transfer Learning) |
| Explainability     | Grad-CAM                    |
| Frontend           | HTML + CSS + JavaScript     |
| Image Processing   | OpenCV + Pillow             |

### Model Pipeline
```
Input Image → Resize (224×224) → MobileNetV2 Feature Extraction
→ Dense Layers → Sigmoid Output → Malignant/Benign + Confidence
                                        ↓
                               Grad-CAM Heatmap Overlay
```

---

## ⚠️ Disclaimer

This project is for **educational purposes only**.
It is NOT a certified medical device.
Always consult a qualified doctor for real medical diagnosis.
