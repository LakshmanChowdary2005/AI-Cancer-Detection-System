import requests
from pathlib import Path

# Test with a malignant case to ensure High risk still works
test_image = "dataset/skin/test/malignant/1.jpg"

if Path(test_image).exists():
    with open(test_image, 'rb') as f:
        files = {'image': f}
        data = {
            'patient_name': 'Test Patient',
            'patient_age': '45',
            'scan_type': 'skin'
        }
        response = requests.post('http://localhost:5000/predict', files=files, data=data)
        
    print(f"Testing file: malignant (cancer case)")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Cancer Type: {result.get('cancer_type')}")
        print(f"Label: {result.get('label')}")
        print(f"Confidence: {result.get('confidence')}%")
        print(f"Risk: {result.get('risk')}")
else:
    print(f"File not found: {test_image}")
