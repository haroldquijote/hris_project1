"""Verify ZK9500 connects and captures a fingerprint."""
from pyzkfp import ZKFP2

zkfp2 = ZKFP2()
zkfp2.Init()

device_count = zkfp2.GetDeviceCount()
print(f"{device_count} device(s) found")

if device_count == 0:
    print("ERROR: No device detected. Check USB connection and SDK install.")
    zkfp2.Terminate()
    exit()

zkfp2.OpenDevice(0)
print("Device opened successfully")
print("Place your finger on the scanner...")

while True:
    capture = zkfp2.AcquireFingerprint()
    if capture:
        tmp, img = capture
        print(f"Fingerprint captured! Template size: {len(tmp)} bytes")
        break

zkfp2.CloseDevice()
zkfp2.Terminate()
print("Test complete")