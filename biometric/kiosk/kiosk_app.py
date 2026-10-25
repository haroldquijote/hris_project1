import os
import sys
import time
import threading
from flask import Flask, render_template, jsonify, request, session, redirect
from dotenv import load_dotenv

# ── Force UTF-8 stdout/stderr ──────────────────────────────────────
# Windows default cp1252 codepage can't encode ✓ ✗ ⚠ → and crashes the
# scanner thread with UnicodeEncodeError. This fixes it and enables line
# buffering so logs appear immediately in kiosk.log.

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

load_dotenv()
app = Flask(__name__)

app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-only-change-in-env')
ENROLL_PIN = os.environ.get('ENROLL_PIN', '1234')


def _enroll_authorized():
    return session.get('enroll_authorized', False)

API_BASE = os.environ.get('HRIS_API_BASE', 'https://hris-project1.onrender.com')
REFRESH_TOKEN = os.environ.get('HRIS_REFRESH_TOKEN')

# ==================== State ====================
scan_state = {
    'status': 'idle',
    'employee': None,
    'message': None,
    'event_id': 0,
}

enroll_state = {
    'active': False,
    'company_id': None,
    'finger_id': None,
    'scan_count': 0,
    'status': 'idle',
    'message': None,
    'employee_name': None,
    'templates': [],
    'event_id': 0,
}

enroll_lock = threading.Lock()
finger_map = {}
finger_map_lock = threading.Lock()

# ==================== Token ====================
_access_token = None
_access_expires_at = 0


def get_access_token(force=False):
    global _access_token, _access_expires_at
    if force or not _access_token or time.time() >= _access_expires_at - 60:
        import requests
        r = requests.post(
            f"{API_BASE}/api/auth/refresh/",
            json={'refresh': REFRESH_TOKEN},
            timeout=60,
        )
        r.raise_for_status()
        _access_token = r.json()['access']
        _access_expires_at = time.time() + 3600
        print(f"[{time.strftime('%H:%M:%S')}] Token refreshed")
    return _access_token


def api(method, url, **kwargs):
    import requests
    token = get_access_token()
    headers = kwargs.pop('headers', {})
    headers['Authorization'] = f'Bearer {token}'
    r = requests.request(method, url, headers=headers, timeout=60, **kwargs)
    if r.status_code == 401:
        token = get_access_token(force=True)
        headers['Authorization'] = f'Bearer {token}'
        r = requests.request(method, url, headers=headers, timeout=60, **kwargs)
    return r


def api_get_list(url):
    r = api('GET', url)
    data = r.json()
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    return data


# ==================== State helpers ====================
def update_scan_state(status, employee=None, message=None):
    scan_state.update({
        'status': status,
        'employee': employee,
        'message': message,
        'event_id': scan_state['event_id'] + 1,
    })
    print(f"  → scan {status}: {employee} — {message}")


def update_enroll_state(**kwargs):
    with enroll_lock:
        enroll_state.update(kwargs)
        enroll_state['event_id'] += 1


def get_enroll_snapshot():
    with enroll_lock:
        return {k: v for k, v in enroll_state.items() if k != 'templates'}


# ==================== Device loader (the critical function) ====================
def load_all_fingerprints_into_device(zkfp2):
    """
    Fetch ALL fingerprints from server, dedupe, and load into device.
    Updates global finger_map atomically.
    Returns True if at least one template was loaded successfully.
    """
    import base64

    print("  [load] Fetching fingerprints from server...")
    try:
        fps = api_get_list(f"{API_BASE}/api/employees/fingerprints/")
    except Exception as e:
        print(f"  [load] FAILED to fetch: {e}")
        return False

    print(f"  [load] Server returned {len(fps)} record(s)")

    # Build dedupe map: newest per finger_id
    by_fid = {}
    for e in fps:
        fid = e.get('finger_id')
        template = e.get('template', '')
        company_id = e.get('company_id', '?')
        created = e.get('created_at', '') or ''

        if fid is None or not template:
            print(f"  [load] SKIP fid={fid} emp={company_id}: missing data")
            continue

        try:
            raw = base64.b64decode(template)
        except Exception:
            print(f"  [load] SKIP fid={fid} emp={company_id}: bad base64")
            continue

        if len(raw) < 256:
            print(f"  [load] SKIP fid={fid} emp={company_id}: too small ({len(raw)}B)")
            continue

        existing = by_fid.get(fid)
        if existing is None or created > existing['created']:
            if existing:
                print(f"  [load] DUPLICATE fid={fid}: replacing {existing['company_id']} with {company_id}")
            by_fid[fid] = {
                'raw': raw,
                'company_id': company_id,
                'created': created,
            }
        else:
            print(f"  [load] DUPLICATE fid={fid}: keeping {existing['company_id']}, discarding {company_id}")

    print(f"  [load] {len(by_fid)} unique finger_id(s) to load")

    # Clear device memory
    try:
        zkfp2.DBClear()
        print("  [load] Device memory cleared")
    except Exception as e:
        print(f"  [load] DBClear warning: {e}")

    # Add each template, track per-template result
    new_map = {}
    for fid in sorted(by_fid.keys()):
        data = by_fid[fid]
        try:
            zkfp2.DBAdd(fid, bytes(data['raw']))
            new_map[fid] = data['company_id']
            print(f"  [load] + fid={fid} emp={data['company_id']}")
        except Exception as e:
            print(f"  [load] FAILED fid={fid} emp={data['company_id']}: {e}")

    # Atomically update global finger_map
    with finger_map_lock:
        finger_map.clear()
        finger_map.update(new_map)

    print(f"  [load] DONE: {len(new_map)}/{len(by_fid)} loaded. Keys: {sorted(new_map.keys())}")
    return len(new_map) > 0


# ==================== Scanner loop ====================
def scanner_loop():
    import base64
    from pyzkfp import ZKFP2

    zkfp2 = ZKFP2()
    zkfp2.Init()
    if zkfp2.GetDeviceCount() == 0:
        print("ERROR: No ZK9500 found.")
        return
    zkfp2.OpenDevice(0)

    # ── Retry fingerprint loading (Render may be cold-starting) ──────
    print("=== Startup: loading fingerprints ===")
    loaded_ok = False
    for attempt in range(1, 4):
        print(f"  Attempt {attempt}/3...")
        loaded_ok = load_all_fingerprints_into_device(zkfp2)
        if loaded_ok:
            break
        if attempt < 3:
            print(f"  Retrying in 5 seconds (Render may be waking up)...")
            time.sleep(5)

    if not loaded_ok:
        print("=== WARNING: Could not load fingerprints from server. ===")
        print("=== Device is running but no scans will match until restart. ===")
    else:
        print("=== Ready. Waiting for scans... ===\n")

    last_scan = {}
    SCAN_COOLDOWN = 10
    last_enroll_capture = [0.0]

    while True:
        capture = zkfp2.AcquireFingerprint()
        if not capture:
            time.sleep(0.05)
            continue

        tmp, img = capture

        with enroll_lock:
            is_enroll = enroll_state['active'] and enroll_state['status'] == 'capturing'
            company_id = enroll_state['company_id']
            finger_id = enroll_state['finger_id']

        if is_enroll:
            now = time.time()
            if now - last_enroll_capture[0] < 2.0:
                continue
            last_enroll_capture[0] = now
            handle_enroll_capture(zkfp2, tmp, company_id, finger_id)
        else:
            handle_scan_capture(zkfp2, tmp, last_scan, SCAN_COOLDOWN)

def handle_scan_capture(zkfp2, tmp, last_scan, cooldown):
    finger_id, score = zkfp2.DBIdentify(bytes(tmp))
    if finger_id == -1 or score < 50:
        return

    now = time.time()
    if finger_id in last_scan and now - last_scan[finger_id] < cooldown:
        return

    with finger_map_lock:
        company_id = finger_map.get(finger_id)
        available = sorted(finger_map.keys())

    if not company_id:
        print(f"  ⚠ Finger {finger_id} matched (score={score}) but NOT in finger_map!")
        print(f"  ⚠ Available keys: {available}")
        return

    last_scan[finger_id] = now
    print(f"[{time.strftime('%H:%M:%S')}] MATCH: {company_id} (finger_id={finger_id}, score={score})")

    # ── POST attendance with retry on network errors ──────────────
    last_error = None
    for attempt in range(1, 3):  # 2 attempts
        try:
            r = api('POST', f"{API_BASE}/api/attendance/biometric/",
                    json={'company_id': company_id, 'device_id': 'ZK9500-KIOSK'})
            data = r.json()

            if r.status_code in (200, 201):
                action = data.get('action')
                if action == 'clock_in':
                    t = data.get('clock_in', '')[:19].split('T')[-1]
                    update_scan_state('success', data.get('employee'), f'Clocked in at {t}')
                elif action == 'clock_out':
                    t = data.get('clock_out', '')[:19].split('T')[-1]
                    update_scan_state('success', data.get('employee'), f'Clocked out at {t}')
                elif action == 'too_soon_for_clock_out':
                    update_scan_state('warning', data.get('employee'), data.get('message'))
                elif action == 'already_complete':
                    update_scan_state('warning', data.get('employee'), 'Already clocked out')
                else:
                    update_scan_state('success', data.get('employee'), 'Recorded')
                return  # success — done

            else:
                # Backend returned 4xx/5xx — no point retrying
                err_msg = data.get('error', 'Not recognized')
                update_scan_state('error', None, err_msg)
                print(f"  ✗ Attendance rejected: {err_msg}")
                return

        except Exception as e:
            last_error = str(e)
            print(f"  Attempt {attempt}/2 failed: {e}")
            if attempt < 2:
                print(f"  Retrying in 3s (Render may be cold)...")
                time.sleep(3)

    # Both attempts failed
    print(f"  ✗ POST error after 2 attempts: {last_error}")
    update_scan_state('error', None, 'Server unreachable — please try again')


def handle_enroll_capture(zkfp2, tmp, company_id, finger_id):
    with enroll_lock:
        scan_count = enroll_state['scan_count']
        if scan_count >= 3:
            return
        enroll_state['templates'].append(bytes(tmp))
        new_count = scan_count + 1
        enroll_state['scan_count'] = new_count
        enroll_state['event_id'] += 1
        enroll_state['message'] = f'Scan {new_count} of 3 captured'
        if new_count == 3:
            enroll_state['status'] = 'merging'
            enroll_state['message'] = 'Merging templates...'
            enroll_state['event_id'] += 1
            templates = list(enroll_state['templates'])
            enroll_state['templates'] = []
        else:
            templates = None

    print(f"  enroll scan {new_count}/3")
    if templates:
        merge_and_save(zkfp2, templates, company_id, finger_id)


def merge_and_save(zkfp2, templates, company_id, finger_id):
    import base64
    print("  Merging...")
    try:
        reg_temp, reg_len = zkfp2.DBMerge(*templates)
        template_b64 = base64.b64encode(bytes(reg_temp)).decode('utf-8')
        print(f"  Merged: {reg_len} bytes")
    except Exception as e:
        update_enroll_state(status='error', message=f'Merge failed: {e}', active=False)
        print(f"  ✗ Merge error: {e}")
        return

    try:
        r = api('POST', f"{API_BASE}/api/employees/fingerprints/",
                json={
                    'company_id': company_id,
                    'finger_id': finger_id,
                    'template': template_b64,
                })

        if r.status_code not in (200, 201):
            err = r.json().get('error', r.text)
            update_enroll_state(status='error', message=err, active=False)
            print(f"  ✗ Enroll failed: {err}")
            return

        # Get employee_name BEFORE releasing lock
        with enroll_lock:
            employee_name = enroll_state.get('employee_name') or company_id

        print(f"  ✓ Saved to server. Reloading device memory...")

        # FULL RELOAD — this guarantees device state matches server
        success = load_all_fingerprints_into_device(zkfp2)

        if not success:
            update_enroll_state(
                status='error',
                message='Saved to server but device reload failed. Restart kiosk.',
                active=False,
            )
            print("  ✗ Device reload failed. Kiosk must be restarted.")
            return

        with finger_map_lock:
            count = len(finger_map)

        update_enroll_state(
            active=False,
            status='success',
            message=f'Finger {finger_id} registered. {count} template(s) loaded.',
            employee_name=employee_name,
            scan_count=0,
        )
        print(f"  ✓ Enroll complete. finger_map has {count} entries.")

    except Exception as e:
        update_enroll_state(status='error', message=f'Server error: {e}', active=False)
        print(f"  ✗ Enroll error: {e}")


# ==================== Flask routes ====================
@app.route('/')
def kiosk():
    return render_template('kiosk.html')


@app.route('/api/last-scan')
def last_scan_route():
    return jsonify(scan_state)


@app.route('/enroll')
def enroll_page():
    if not _enroll_authorized():
        return redirect('/')
    return render_template('enroll.html')


@app.route('/api/enroll/status')
def enroll_status():
    if not _enroll_authorized():
        return jsonify({'error': 'Enroll authorization required'}), 403
    return jsonify(get_enroll_snapshot())


@app.route('/api/enroll/start', methods=['POST'])
def enroll_start():
    if not _enroll_authorized():
        return jsonify({'error': 'Enroll authorization required'}), 403
    data = request.get_json() or {}
    company_id = (data.get('company_id') or '').strip()
    finger_id = data.get('finger_id')

    if not company_id or not finger_id:
        return jsonify({'error': 'company_id and finger_id are required'}), 400

    try:
        finger_id = int(finger_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'finger_id must be an integer'}), 400

    try:
        employees = api_get_list(f"{API_BASE}/api/employees/")
        employee = next((e for e in employees if e.get('company_id') == company_id), None)
        if not employee:
            return jsonify({'error': f'Employee {company_id} not found'}), 404

        employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip() or company_id

        existing_fps = api_get_list(f"{API_BASE}/api/employees/fingerprints/")
        for fp in existing_fps:
            if fp.get('finger_id') == finger_id and fp.get('company_id') != company_id:
                return jsonify({
                    'error': f'Finger {finger_id} is already enrolled for {fp.get("company_id")}. '
                             f'Choose a different finger number.'
                }), 409

        already_enrolled = any(
            fp.get('finger_id') == finger_id and fp.get('company_id') == company_id
            for fp in existing_fps
        )
    except Exception as e:
        return jsonify({'error': f'Could not reach server: {e}'}), 502

    with enroll_lock:
        enroll_state.update({
            'active': True,
            'company_id': company_id,
            'finger_id': finger_id,
            'scan_count': 0,
            'status': 'capturing',
            'message': (
                'Overwriting existing enrollment for this finger'
                if already_enrolled
                else 'Place your finger on the scanner'
            ),
            'employee_name': employee_name,
            'templates': [],
            'event_id': enroll_state['event_id'] + 1,
        })

    print(f"Enrollment started: {company_id} ({employee_name}) finger {finger_id}")
    return jsonify({
        'ok': True,
        'company_id': company_id,
        'employee_name': employee_name,
        'finger_id': finger_id,
        'overwrite': already_enrolled,
    })


@app.route('/api/enroll/reset', methods=['POST'])
def enroll_reset():
    if not _enroll_authorized():
        return jsonify({'error': 'Enroll authorization required'}), 403
    with enroll_lock:
        enroll_state.update({
            'active': False,
            'company_id': None,
            'finger_id': None,
            'scan_count': 0,
            'status': 'idle',
            'message': None,
            'employee_name': None,
            'templates': [],
            'event_id': enroll_state['event_id'] + 1,
        })
    return jsonify({'ok': True})

@app.route('/api/enroll/verify-pin', methods=['POST'])
def enroll_verify_pin():
    data = request.get_json() or {}
    pin = str(data.get('pin', '')).strip()
    if pin and pin == ENROLL_PIN:
        session['enroll_authorized'] = True
        return jsonify({'ok': True})
    return jsonify({'error': 'Invalid PIN'}), 401


@app.route('/api/enroll/logout', methods=['POST'])
def enroll_logout():
    session.pop('enroll_authorized', None)
    return jsonify({'ok': True})


# ==================== Main ====================
if __name__ == '__main__':
    if not REFRESH_TOKEN:
        print("ERROR: HRIS_REFRESH_TOKEN not set in .env")
        exit(1)

    try:
        get_access_token()
        print("Token OK.")
    except Exception as e:
        print(f"Token error: {e}")
        exit(1)

    threading.Thread(target=scanner_loop, daemon=True).start()
    print("Kiosk:        http://localhost:5000")
    print("Enroll (HR):  http://localhost:5000/enroll")
    app.run(host='0.0.0.0', port=5000, debug=False)