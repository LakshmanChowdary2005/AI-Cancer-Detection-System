from pathlib import Path
import numpy as np
from tensorflow.keras.models import load_model

BASE = Path(__file__).resolve().parents[1]
models = {
    'skin': BASE / 'models' / 'skin_model.keras',
    'brain': BASE / 'models' / 'brain_model.keras',
    'breast': BASE / 'models' / 'breast_model.keras',
    'lung': BASE / 'models' / 'lung_model.keras',
    'type': BASE / 'models' / 'cancer_type_model.keras'
}

for name, path in models.items():
    print('\n===', name, '===')
    print('path exists:', path.exists())
    if not path.exists():
        continue
    try:
        model = load_model(str(path))
    except Exception as e:
        print('load error:', e)
        continue
    try:
        print('output_shape:', model.output_shape)
    except Exception as e:
        print('output_shape error:', e)
    try:
        dummy = np.zeros((1,224,224,3), dtype=np.float32)
        pred = model.predict(dummy, verbose=0)
        print('pred.shape:', getattr(pred, 'shape', type(pred)))
        print('pred sample:', pred if isinstance(pred, (list, tuple)) else (pred if pred.shape[0] < 5 else pred[0]))
    except Exception as e:
        print('predict error:', e)
