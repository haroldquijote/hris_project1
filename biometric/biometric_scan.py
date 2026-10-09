"""
Scan finger, match, and clock in.

Usage:
    python biometric_scan.py
"""
import os
import time
import base64
import requests
from datetime import datetime
from pyzkfp import ZKFP2

API_BASE = os.environ.get('HRIS_API_BASE', 'http://localhost:8000')
TOKEN = os.environ.get('HRIS_TOKEN')
SCAN_COOLDOWN_SECONDS = 10

if not TOKEN:
    print("ERROR: HRIS_TOKEN environment variable not set.")
    exit(1)

print("Loading fingerprints from server...")
resp = requests.get(
    f"{API_BASE}/api/employees/fingerprints/",
    headers={'Authorization': f'Bearer {TOKEN}'},
)
resp.raise_for_status()
all_fps = resp.json()
print(f"Loaded {len(all_fps)} fingerprint(s).")

if not all_fps:
    print("No fingerprints registered. Run biometric_enroll.py first.")
    exit(1)

zkfp2 = ZKFP2()
zkfp2.Init()

if zkfp2.GetDeviceCount() == 0:
    print("ERROR: No ZK9500 device found.")
    zkfp2.Terminate()
    exit(1)

zkfp2.OpenDevice(0)

finger_map = {}
for entry in all_fps:
    fid = entry['finger_id']
    raw = base64.b64decode(entry['template'])
    zkfp2.DBAdd(fid, bytes(raw))
    finger_map[fid] = entry['company_id']
    print(f"  Loaded finger {fid} → {entry['company_id']}")

print(f"\nReady. Place your finger to clock in. Ctrl+C to stop.\n")

last_scan_time = {}

try:
    while True:
        capture = zkfp2.AcquireFingerprint()
        if not capture:
            continue

        tmp, img = capture
        finger_id, score = zkfp2.DBIdentify(bytes(tmp))

        if finger_id == -1 or score < 50:
            print(f"No match (score={score})")
            continue

        # Client-side cooldown
        now = time.time()
        if finger_id in last_scan_time:
            elapsed = now - last_scan_time[finger_id]
            if elapsed < SCAN_COOLDOWN_SECONDS:
                remaining = SCAN_COOLDOWN_SECONDS - int(elapsed)
                print(f"Cooldown: wait {remaining}s before scanning again")
                time.sleep(1)
                continue

        company_id = finger_map.get(finger_id)
        if not company_id:
            print(f"Finger {finger_id} matched but not mapped")
            continue

        print(f"MATCH: {company_id} (score={score})")

        response = requests.post(
            f"{API_BASE}/api/attendance/biometric/",
            headers={
                'Authorization': f'Bearer {TOKEN}',
                'Content-Type': 'application/json',
            },
            json={
                'company_id': company_id,
                'timestamp': datetime.now().isoformat(),
                'device_id': 'ZK9500-DEMO',
            },
        )

        if response.status_code in (200, 201):
            print("  Attendance recorded:", response.json())
            last_scan_time[finger_id] = now  # only cooldown on success
        else:
            print(f"  ERROR {response.status_code}: {response.text}")

        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopping...")

zkfp2.CloseDevice()
zkfp2.Terminate()