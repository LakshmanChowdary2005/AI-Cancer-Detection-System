import os
import numpy as np
import tensorflow as tf

from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.applications.efficientnet import preprocess_input
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout, BatchNormalization
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from sklearn.utils.class_weight import compute_class_weight

# =====================================================
# CONFIGURATION
# =====================================================

DATASET_DIR = "data"
MODEL_OUTPUT = "cancer_model.keras"

IMG_SIZE = (224, 224)
BATCH_SIZE = 16
EPOCHS = 20

# =====================================================
# DATA GENERATORS
# =====================================================

train_datagen = ImageDataGenerator(
    preprocessing_function=preprocess_input,
    rotation_range=20,
    width_shift_range=0.2,
    height_shift_range=0.2,
    zoom_range=0.2,
    horizontal_flip=True,
    fill_mode="nearest"
)

val_datagen = ImageDataGenerator(
    preprocessing_function=preprocess_input
)

# =====================================================
# LOAD DATA
# =====================================================

train_gen = train_datagen.flow_from_directory(
    os.path.join(DATASET_DIR, "train"),
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="binary",
    shuffle=True
)

val_gen = val_datagen.flow_from_directory(
    os.path.join(DATASET_DIR, "val"),
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="binary",
    shuffle=False
)

test_gen = val_datagen.flow_from_directory(
    os.path.join(DATASET_DIR, "test"),
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="binary",
    shuffle=False
)

print("\nClass Mapping:")
print(train_gen.class_indices)

# =====================================================
# CLASS WEIGHTS
# =====================================================

class_weights = compute_class_weight(
    class_weight="balanced",
    classes=np.unique(train_gen.classes),
    y=train_gen.classes
)

class_weights = dict(enumerate(class_weights))

print("\nClass Weights:")
print(class_weights)

# =====================================================
# BUILD MODEL
# =====================================================

base_model = EfficientNetB0(
    weights="imagenet",
    include_top=False,
    input_shape=(224, 224, 3)
)

base_model.trainable = False

x = base_model.output
x = GlobalAveragePooling2D()(x)
x = BatchNormalization()(x)

x = Dense(256, activation="relu")(x)
x = Dropout(0.5)(x)

x = Dense(128, activation="relu")(x)
x = Dropout(0.3)(x)

predictions = Dense(1, activation="sigmoid")(x)

model = Model(
    inputs=base_model.input,
    outputs=predictions
)

# =====================================================
# COMPILE MODEL
# =====================================================

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
    loss="binary_crossentropy",
    metrics=[
        "accuracy",
        tf.keras.metrics.Precision(name="precision"),
        tf.keras.metrics.Recall(name="recall"),
        tf.keras.metrics.AUC(name="auc")
    ]
)

model.summary()

# =====================================================
# CALLBACKS
# =====================================================

callbacks = [
    ModelCheckpoint(
        MODEL_OUTPUT,
        monitor="val_accuracy",
        save_best_only=True,
        verbose=1
    ),

    EarlyStopping(
        monitor="val_loss",
        patience=5,
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
# TRAIN MODEL
# =====================================================

print("\nStarting Training...\n")

history = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=EPOCHS,
    class_weight=class_weights,
    callbacks=callbacks
)

# =====================================================
# EVALUATE MODEL
# =====================================================

print("\nEvaluating on Test Data...\n")

results = model.evaluate(test_gen)

print("\n==============================")
print("TEST RESULTS")
print("==============================")
print(f"Accuracy : {results[1] * 100:.2f}%")
print(f"Precision: {results[2] * 100:.2f}%")
print(f"Recall   : {results[3] * 100:.2f}%")
print(f"AUC      : {results[4] * 100:.2f}%")

# =====================================================
# SAVE MODEL
# =====================================================

model.save(MODEL_OUTPUT)

print("\nTraining Complete")
print(f"Model Saved As: {MODEL_OUTPUT}")