#!/usr/bin/env python3
"""
Warden API — End-to-End Integration Test
Covers: health, auth, cameras, pairing flow, device management, go2rtc credential storage.
Run with: python test_e2e.py (server must be running on localhost:8484)
"""
import sys
import httpx

BASE = "http://localhost:8484"
PASS_MARK = "✓"
FAIL_MARK = "✗"
_failures = []


def check(condition: bool, name: str) -> None:
    if condition:
        print(f"  {PASS_MARK} {name}")
    else:
        print(f"  {FAIL_MARK} {name}")
        _failures.append(name)


# ---------------------------------------------------------------------------
# Test groups
# ---------------------------------------------------------------------------

def test_health() -> None:
    print("\n[Health]")
    r = httpx.get(f"{BASE}/health")
    check(r.status_code == 200, "GET /health → 200")
    check(r.json().get("status") == "ok", "status == ok")


def test_auth() -> str:
    print("\n[Auth]")

    # Valid login
    r = httpx.post(f"{BASE}/auth/login",
                   json={"email": "admin@warden.local", "password": "warden-admin"})
    check(r.status_code == 200, "POST /auth/login → 200")
    tokens = r.json()
    check("access_token" in tokens, "access_token present")
    check("refresh_token" in tokens, "refresh_token present")
    check(tokens.get("token_type") == "bearer", "token_type == bearer")
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]

    # Refresh
    r = httpx.post(f"{BASE}/auth/refresh", json={"refresh_token": refresh})
    check(r.status_code == 200, "POST /auth/refresh → 200")
    new_access = r.json()["access_token"]

    # Wrong password
    r = httpx.post(f"{BASE}/auth/login",
                   json={"email": "admin@warden.local", "password": "wrong"})
    check(r.status_code == 401, "Wrong password → 401")

    # Logout
    r = httpx.post(f"{BASE}/auth/logout", json={"refresh_token": refresh})
    check(r.status_code == 204, "POST /auth/logout → 204")

    # Refresh after logout must fail
    r = httpx.post(f"{BASE}/auth/refresh", json={"refresh_token": refresh})
    check(r.status_code == 401, "Refresh after logout → 401")

    return new_access


def test_cameras(access_token: str) -> tuple[int, str]:
    print("\n[Cameras]")
    auth = {"Authorization": f"Bearer {access_token}"}

    # No auth
    r = httpx.get(f"{BASE}/cameras")
    check(r.status_code == 403, "GET /cameras without token → 403")

    # Create
    r = httpx.post(f"{BASE}/cameras",
                   json={"name": "Front Door",
                         "ip_address": "192.168.1.100",
                         "rtsp_url": "rtsp://192.168.1.100:554/stream"},
                   headers=auth)
    check(r.status_code == 201, "POST /cameras → 201")
    cam = r.json()
    check(cam.get("stream_path") == "camera_1", "stream_path == camera_1")
    cam_id: int = cam["id"]

    # List
    r = httpx.get(f"{BASE}/cameras", headers=auth)
    check(r.status_code == 200, "GET /cameras → 200")
    check(len(r.json()) == 1, "One camera in list")

    # Get by id
    r = httpx.get(f"{BASE}/cameras/{cam_id}", headers=auth)
    check(r.status_code == 200, "GET /cameras/{id} → 200")

    # Update
    r = httpx.put(f"{BASE}/cameras/{cam_id}",
                  json={"name": "Front Door Updated"}, headers=auth)
    check(r.status_code == 200, "PUT /cameras/{id} → 200")
    check(r.json().get("name") == "Front Door Updated", "Name updated correctly")

    # Not found
    r = httpx.get(f"{BASE}/cameras/9999", headers=auth)
    check(r.status_code == 404, "GET /cameras/9999 → 404")

    return cam_id, access_token


def test_pairing(access_token: str, cam_id: int) -> str:
    print("\n[Pairing Flow]")
    auth = {"Authorization": f"Bearer {access_token}"}

    # Request code (no auth needed)
    r = httpx.post(f"{BASE}/pair/request")
    check(r.status_code == 200, "POST /pair/request → 200")
    pair = r.json()
    code: str = pair.get("code", "")
    check(len(code) == 9 and code[4] == "-", f"Code format XXXX-XXXX (got {code!r})")
    check("expires_at" in pair, "expires_at present")
    check("qr_payload" in pair, "qr_payload present")

    # Poll — should be pending
    r = httpx.get(f"{BASE}/pair/status", params={"code": code})
    check(r.status_code == 200, "GET /pair/status → 200")
    check(r.json().get("status") == "pending", "Status == pending before activation")

    # Activate (admin)
    r = httpx.post(f"{BASE}/pair/activate",
                   json={"code": code, "device_name": "Living Room TV"},
                   headers=auth)
    check(r.status_code == 200, "POST /pair/activate → 200")
    check("device_token" in r.json(), "device_token in activation response")

    # Poll — should be approved with camera list
    r = httpx.get(f"{BASE}/pair/status", params={"code": code})
    check(r.status_code == 200, "GET /pair/status after activation → 200")
    status = r.json()
    check(status.get("status") == "approved", "Status == approved")
    check(status.get("device_token") is not None, "device_token present in status")
    cameras = status.get("cameras", [])
    check(len(cameras) == 1, "One camera in approved response")
    check(
        cameras[0].get("stream_url") == f"/streams/{cam_id}/webrtc",
        f"stream_url == /streams/{cam_id}/webrtc",
    )

    # Duplicate activation must fail
    r = httpx.post(f"{BASE}/pair/activate",
                   json={"code": code, "device_name": "Dup"}, headers=auth)
    check(r.status_code == 400, "Duplicate activation → 400")

    # Unknown code
    r = httpx.get(f"{BASE}/pair/status", params={"code": "XXXX-XXXX"})
    check(r.status_code == 404, "Unknown code → 404")

    return status["device_token"]


def test_device_management(access_token: str, device_token: str, cam_id: int) -> None:
    print("\n[Device Management]")
    auth = {"Authorization": f"Bearer {access_token}"}
    dev_auth = {"Authorization": f"Bearer {device_token}"}

    # List devices
    r = httpx.get(f"{BASE}/devices", headers=auth)
    check(r.status_code == 200, "GET /devices → 200")
    devices = r.json()
    check(
        any(d.get("device_name") == "Living Room TV" for d in devices),
        "Living Room TV device present",
    )
    device_id = next(d["id"] for d in devices if d.get("device_name") == "Living Room TV")

    # App camera list using device token
    r = httpx.get(f"{BASE}/streams/cameras", headers=dev_auth)
    check(r.status_code == 200, "GET /streams/cameras with device token → 200")
    app_cameras = r.json()
    check(len(app_cameras) == 1, "One camera in device camera list")
    check(
        app_cameras[0].get("stream_url") == f"/streams/{cam_id}/webrtc",
        "stream_url correct in device camera list",
    )

    # Bad device token
    r = httpx.get(f"{BASE}/streams/cameras",
                  headers={"Authorization": "Bearer bad-token"})
    check(r.status_code == 401, "Bad device token → 401")

    # Stream proxy with device token — go2rtc not running → 503
    r = httpx.post(
        f"{BASE}/streams/{cam_id}/webrtc",
        content=b"v=0",
        headers={**dev_auth, "Content-Type": "application/sdp"},
    )
    check(r.status_code == 503, "Stream proxy with go2rtc down → 503")

    # Revoke device
    r = httpx.delete(f"{BASE}/devices/{device_id}", headers=auth)
    check(r.status_code == 204, "DELETE /devices/{id} → 204")

    # Revoked token must be rejected immediately
    r = httpx.get(f"{BASE}/streams/cameras", headers=dev_auth)
    check(r.status_code == 401, "Revoked token → 401")


def test_go2rtc_credentials() -> None:
    print("\n[go2rtc Credential Storage]")
    import os
    os.environ.setdefault("DB_PATH", "./warden_dev.db")
    from app.database import SessionLocal
    from app.models import SystemConfig

    db = SessionLocal()
    try:
        username_row = db.query(SystemConfig).filter(
            SystemConfig.key == "go2rtc_username").first()
        password_row = db.query(SystemConfig).filter(
            SystemConfig.key == "go2rtc_password").first()

        check(username_row is not None, "go2rtc_username stored in system_config")
        check(password_row is not None, "go2rtc_password stored in system_config")
        if password_row:
            check(len(password_row.value) >= 32,
                  "go2rtc_password length >= 32 chars")
    finally:
        db.close()


def test_permission_enforcement(access_token: str) -> None:
    print("\n[Permission Enforcement]")
    auth = {"Authorization": f"Bearer {access_token}"}

    # Verify admin can access all protected routes
    r = httpx.get(f"{BASE}/cameras", headers=auth)
    check(r.status_code == 200, "Admin can GET /cameras")

    r = httpx.get(f"{BASE}/devices", headers=auth)
    check(r.status_code == 200, "Admin can GET /devices")

    # Tampered token must fail
    r = httpx.get(f"{BASE}/cameras",
                  headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.fake.sig"})
    check(r.status_code == 401, "Tampered JWT → 401")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 52)
    print("  Warden API — End-to-End Integration Test")
    print("=" * 52)

    test_health()
    access_token = test_auth()

    # Re-login (previous token was used for logout test)
    r = httpx.post(f"{BASE}/auth/login",
                   json={"email": "admin@warden.local", "password": "warden-admin"})
    access_token = r.json()["access_token"]

    cam_id, access_token = test_cameras(access_token)
    device_token = test_pairing(access_token, cam_id)
    test_device_management(access_token, device_token, cam_id)
    test_go2rtc_credentials()
    test_permission_enforcement(access_token)

    print("\n" + "=" * 52)
    if _failures:
        print(f"  {len(_failures)} test(s) FAILED:")
        for f in _failures:
            print(f"    {FAIL_MARK} {f}")
        sys.exit(1)
    else:
        total = sum(1 for line in open(__file__) if "check(" in line)
        print(f"  All {total} checks passed!")
    print("=" * 52)
