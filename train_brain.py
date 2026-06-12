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

DATASET_DIR = "dataset/brain"

IMG_SIZE = (224, 224)
BATCH_SIZE = 16
EPOCHS = 15

MODEL_PATH = "models/brain_model.keras"

# =====================================================
# DATA GENERATORS
# =====================================================

train_datagen = ImageDataGenerator(
    preprocessing_function=preprocess_input,
    rotation_range=15,
    zoom_range=0.15,
    width_shift_range=0.1,
    height_shift_range=0.1,
    horizontal_flip=True
)

test_datagen = ImageDataGenerator(
    preprocessing_function=preprocess_input
)

train_gen = train_datagen.flow_from_directory(
    os.path.join(DATASET_DIR, "Training"),
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical"
)

test_gen = test_datagen.flow_from_directory(
    os.path.join(DATASET_DIR, "Testing"),
    target_size=IMG_SIZE,
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    shuffle=False
)

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

model = Model(inputs=base_model.input, outputs=output)

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
        restore_best_weights=True
    ),

    ModelCheckpoint(
        MODEL_PATH,
        save_best_only=True,
        monitor="val_accuracy"
    )
]

# =====================================================
# TRAIN
# =====================================================

history = model.fit(
    train_gen,
    validation_data=test_gen,
    epochs=EPOCHS,
    callbacks=callbacks
)

# =====================================================
# EVALUATE
# =====================================================

loss, accuracy = model.evaluate(test_gen)

print("\n========================")
print("Brain Tumor Accuracy")
print("========================")
print(f"Accuracy: {accuracy * 100:.2f}%")

model.save(MODEL_PATH)

print(f"\nModel Saved: {MODEL_PATH}")