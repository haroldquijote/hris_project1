"""
Register an employee's fingerprint.

Usage:
    python biometric_enroll.py <company_id> <finger_id>

Example:
    python biometric_enroll.py EMP001 1
"""
import os
import sys
import base64
import requests
from pyzkfp import ZKFP2

API_BASE = os.environ.get('HRIS_API_BASE', 'http://localhost:8000')
TOKEN = os.environ.get('HRIS_TOKEN')

if len(sys.argv) < 3:
    print("Usage: python biometric_enroll.py <company_id> <finger_id>")
    sys.exit(1)

company_id = sys.argv[1]
finger_id = int(sys.argv[2])

if not TOKEN:
    print("ERROR: HRIS_TOKEN environment variable not set.")
    sys.exit(1)

zkfp2 = ZKFP2()
zkfp2.Init()

if zkfp2.GetDeviceCount() == 0:
    print("ERROR: No ZK9500 device found.")
    zkfp2.Terminate()
    sys.exit(1)

zkfp2.OpenDevice(0)
print(f"Enrolling: employee={company_id}, finger_id={finger_id}")
print("Scan the SAME finger 3 times.\n")

templates = []
for i in range(3):
    print(f"Scan {i + 1} of 3 — place your finger...")
    while True:
        capture = zkfp2.AcquireFingerprint()
        if capture:
            tmp, img = capture
            templates.append(tmp)
            print(f"  Captured ({len(tmp)} bytes)")
            break

regTemp, regTempLen = zkfp2.DBMerge(*templates)
print(f"\nMerged template: {regTempLen} bytes")

template_b64 = base64.b64encode(bytes(regTemp)).decode('utf-8')

response = requests.post(
    f"{API_BASE}/api/employees/fingerprints/",
    headers={
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json',
    },
    json={
        'company_id': company_id,
        'finger_id': finger_id,
        'template': template_b64,
    },
)

if response.status_code in (200, 201):
    print("Fingerprint registered successfully.")
    print("Response:", response.json())
else:
    print(f"ERROR {response.status_code}: {response.text}")

zkfp2.CloseDevice()
zkfp2.Terminate()