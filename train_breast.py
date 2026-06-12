import os
import shutil
import numpy as np
import tensorflow as tf

from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.applications.efficientnet import preprocess_input
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.layers import Dense, Dropout, GlobalAveragePooling2D
from tensorflow.keras.models import Model
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau

# =====================================================
# CONFIGURATION
# =====================================================

ORIGINAL_DATASET = "dataset/Breast/Dataset_BUSI_with_GT"

CLEAN_DATASET = "dataset/Breast_Clean"

MODEL_PATH = "models/breast_model.keras"

IMG_SIZE = (224, 224)

BATCH_SIZE = 16

EPOCHS = 15

# =====================================================
# CREATE CLEAN DATASET
# REMOVE MASK FILES
# =====================================================

if os.path.exists(CLEAN_DATASET):
    shutil.rmtree(CLEAN_DATASET)

print("Creating clean dataset...")

classes = ["benign", "malignant", "normal"]

for cls in classes:

    source_folder = os.path.join(ORIGINAL_DATASET, cls)

    destination_folder = os.path.join(CLEAN_DATASET, cls)

    os.makedirs(destination_folder, exist_ok=True)

    for file in os.listdir(source_folder):

        if "_mask" not in file.lower():

            src = os.path.join(source_folder, file)

            dst = os.path.join(destination_folder, file)

            shutil.copy(src, dst)

print("Dataset Ready")

# =====================================================
# DATA GENERATORS
# =====================================================

train_datagen = ImageDataGenerator(
    preprocessing_function=preprocess_input,
    validation_split=0.2,
    rotation_range=20,
    zoom_range=0.2,
    width_shift_range=0.1,
    height_shift_range=0.1,
    horizontal_flip=True
)

train_gen = train_datagen.flow_from_directory(
    CLEAN_DATASET,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    subset="training",
    shuffle=True
)

val_gen = train_datagen.flow_from_directory(
    CLEAN_DATASET,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    subset="validation",
    shuffle=False
)

print("\nClass Mapping:")
print(train_gen.class_indices)

# =====================================================
# MODEL
# =====================================================

base_model = EfficientNetB0(
    weights="imagenet",
    include_top=False,
    input_shape=(224, 224, 3)
)

base_model.trainable = False

x = base_model.output

x = GlobalAveragePooling2D()(x)

x = Dense(256, activation="relu")(x)

x = Dropout(0.4)(x)

output = Dense(3, activation="softmax")(x)

model = Model(
    inputs=base_model.input,
    outputs=output
)

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
    loss="categorical_crossentropy",
    metrics=["accuracy"]
)

# =====================================================
# CALLBACKS
# =====================================================

callbacks = [

    ModelCheckpoint(
        MODEL_PATH,
        monitor="val_accuracy",
        save_best_only=True,
        verbose=1
    ),

    EarlyStopping(
        monitor="val_loss",
        patience=4,
        restore_best_weights=True,
        verbose=1
    ),

    ReduceLROnPlateau(
        monitor="val_loss",
        factor=0.5,
        patience=2,
        verbose=1
    )
]

# =====================================================
# TRAIN
# =====================================================

print("\nStarting Breast Cancer Training...\n")

history = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=EPOCHS,
    callbacks=callbacks
)

# =====================================================
# EVALUATE
# =====================================================

print("\nEvaluating Model...\n")

loss, accuracy = model.evaluate(val_gen)

print("\n========================")
print("BREAST CANCER RESULTS")
print("========================")
print(f"Accuracy: {accuracy * 100:.2f}%")

# =====================================================
# SAVE MODEL
# =====================================================

model.save(MODEL_PATH)

print(f"\nModel Saved: {MODEL_PATH}")