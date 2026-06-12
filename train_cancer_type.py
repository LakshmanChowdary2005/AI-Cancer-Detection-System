import os
import tensorflow as tf

from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.applications.efficientnet import preprocess_input
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.layers import Dense, Dropout, GlobalAveragePooling2D
from tensorflow.keras.models import Model
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

# =====================================================
# CONFIGURATION
# =====================================================

DATASET_DIR = "dataset/cancer_type"

IMG_SIZE = (224, 224)
BATCH_SIZE = 16
EPOCHS = 10

MODEL_PATH = "models/cancer_type_model.keras"

# =====================================================
# CHECK DATASET
# =====================================================

if not os.path.exists(DATASET_DIR):
    print(f"ERROR: Folder not found -> {DATASET_DIR}")
    exit()

# =====================================================
# DATA GENERATORS
# =====================================================

train_datagen = ImageDataGenerator(
    preprocessing_function=preprocess_input,
    validation_split=0.2,
    rotation_range=15,
    zoom_range=0.15,
    width_shift_range=0.1,
    height_shift_range=0.1,
    horizontal_flip=True
)

train_gen = train_datagen.flow_from_directory(
    DATASET_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    subset="training",
    shuffle=True
)

val_gen = train_datagen.flow_from_directory(
    DATASET_DIR,
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    subset="validation",
    shuffle=False
)

print("\n==========================")
print("CLASS MAPPING")
print("==========================")
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

output = Dense(4, activation="softmax")(x)

model = Model(
    inputs=base_model.input,
    outputs=output
)

model.compile(
    optimizer="adam",
    loss="categorical_crossentropy",
    metrics=["accuracy"]
)

model.summary()

# =====================================================
# CALLBACKS
# =====================================================

callbacks = [

    EarlyStopping(
        monitor="val_loss",
        patience=3,
        restore_best_weights=True,
        verbose=1
    ),

    ModelCheckpoint(
        MODEL_PATH,
        monitor="val_accuracy",
        save_best_only=True,
        verbose=1
    )
]

# =====================================================
# TRAIN
# =====================================================

print("\n==========================")
print("STARTING TRAINING")
print("==========================")

history = model.fit(
    train_gen,
    validation_data=val_gen,
    epochs=EPOCHS,
    callbacks=callbacks
)

# =====================================================
# EVALUATE
# =====================================================

loss, accuracy = model.evaluate(val_gen)

print("\n==========================")
print("FINAL RESULTS")
print("==========================")
print(f"Validation Accuracy: {accuracy * 100:.2f}%")

# =====================================================
# SAVE MODEL
# =====================================================

model.save(MODEL_PATH)

print("\n==========================")
print("MODEL SAVED SUCCESSFULLY")
print("==========================")
print(f"Saved as: {MODEL_PATH}")