#!/usr/bin/env python3
import requests
from pathlib import Path

# Test with a breast cancer image
p = Path('dataset/Breast_Clean/benign/benign (1).png')
print(f'Testing file: {p.name}')
print(f'Exists: {p.exists()}')

if p.exists():
    with open(p, 'rb') as fp:
        r = requests.post(
            'http://127.0.0.1:5000/predict',
            files={'image': ('breast.png', fp, 'image/png')},
            data={'cancer_type': 'auto', 'patient_name': 'Test Patient'}
        )
    
    print(f'Status: {r.status_code}')
    data = r.json()
    print(f"Cancer Type: {data.get('cancer_type')}")
    print(f"Auto Type: {data.get('auto_type')}")
    print(f"Ensemble Type: {data.get('ensemble_type')}")
    print(f"Label: {data.get('label')}")
    print(f"Confidence: {data.get('confidence_pct')}%")
    print(f"Consensus: {data.get('consensus')}")
    print(f"Risk: {data.get('risk')}")
else:
    print("Test image not found")
