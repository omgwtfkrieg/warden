# Warden

A self-hosted RTSP camera monitoring platform for Android TV, tablets, and mobile devices. Warden streams live camera feeds through a secure backend proxy — the Flutter app never communicates with cameras directly.

## Architecture

```
Flutter App (Android TV / Tablet / Mobile)
      │
      ▼  device token
warden-api :8484  ──────────────────────────────────────────┐
      │                                                      │
      ▼  internal Docker network only                        │
go2rtc :1984 (never exposed externally)                     │
      │                                                      │
      ▼                                                 warden-admin :3000
   RTSP Cameras                                        (React admin panel)
```

| Service | Port | Description |
|---|---|---|
| `warden-api` | 8484 | FastAPI backend — only externally exposed service |
| `warden-admin` | 3000 | React admin panel served via nginx |
| `go2rtc` | internal only | RTSP stream relay, never reachable from outside Docker |

## Features

### Flutter App
- **Android TV / Google TV / tablet / mobile** support
- **Pairing flow** — displays a short code (e.g. `W7X2-K4P9`) and QR; admin approves from the panel
- **WebRTC live streams** — low-latency video via warden-api proxy
- **Auto-reconnect** — exponential backoff on Android (5 → 10 → 20 → 40 → 60s, 5 attempts); indefinite retry on Linux kiosk
- **Frozen frame detection** — polls WebRTC `framesDecoded` every 5s; shows a toast if no new frames for 10s, dismisses automatically on recovery
- **Manual reconnect** — kebab menu "Reconnect all" forces immediate reconnection of all streams
- **Remote commands** — admin panel can send `reconnect`, `reload`, or `refresh` to any device; Flutter polls `/commands/pending` every 30s
- **Stream failure diagnostics** — per-camera overlay shows failure reason (signaling error, network error, ICE failure) with countdown and manual retry
- **Server health banner** — unobtrusive banner appears after 2 consecutive health check failures; clears immediately when any camera reconnects
- **Branded splash screen** — native splash for standard Android; Flutter-side splash (TV-aware delay) for Google TV / leanback devices
- **Device deduplication** — hardware ID captured at pairing so the same physical device never creates duplicate entries
- **Platform reporting** — device platform (Android, Linux, iOS, Windows, macOS) reported at pairing time and shown in admin panel

### Backend (FastAPI)
- **JWT auth** — 15-minute access tokens + 7-day refresh tokens for the admin panel
- **Device tokens** — long-lived, independent tokens for Flutter app pairing; revoking never affects the user account
- **Role-based permissions** — `admin`, `operator`, `viewer` roles with JSON permission arrays
- **Camera CRUD** — add, edit, reorder, and delete cameras; each write syncs go2rtc config automatically
- **go2rtc credential bootstrap** — random basic auth credentials auto-generated on first boot, stored in DB, written into go2rtc config; never exposed in API responses or logs
- **WebRTC stream proxy** — `GET /streams/{id}/webrtc` validates device token and proxies signaling to go2rtc internally
- **Health endpoint** — `GET /health/detail` reports API status, go2rtc reachability, and per-camera stream status
- **Alembic migrations** — full schema version history, Postgres-compatible syntax throughout
- **Seed data** — default `admin` / `operator` / `viewer` roles and first admin user on clean install

### Admin Panel (React + MUI)
- **Dashboard** — service status cards for API, go2rtc, and each camera feed
- **Cameras** — add/edit/delete cameras, set display order, sub-stream toggle
- **Devices** — list all authorized Flutter app devices with:
  - Platform icon (Android, Linux, Windows, macOS, iOS) shown next to device name
  - Auth Status (Active / Revoked) and Device Status (Online / Offline / Never seen) columns
  - Rename (pencil icon, pre-filled dialog)
  - Remote commands per device: reconnect streams, reload app, refresh camera list
  - Revoke access (blocks the device token immediately)
  - Delete permanently (only enabled after revocation)
  - Device model shown as subtitle (captured from hardware at pairing)
- **Users** — create and manage user accounts with role assignment
- **Pairing** — enter or scan a pairing code to authorize a Flutter app device
- **Favicon + tab title** — branded with Warden logo

## Security Model

- go2rtc has **no published ports** — only reachable on the internal Docker network
- go2rtc basic auth credentials are **auto-generated**, stored only in the DB, and used only by warden-api internally
- The Flutter app receives **stream URLs pointing to warden-api** — it never knows go2rtc exists
- Device tokens are **not JWTs** and are independent of user credentials
- Revoking a device token takes effect immediately on the next request

## Getting Started

### Prerequisites
- Docker + Docker Compose

### Run

```bash
# Clone the repo
git clone <repo-url>
cd warden

# Configure environment
cp .env.example .env
# Edit .env and set a secure SECRET_KEY

# Build and start all services
docker compose up --build -d
```

Access:
- **Admin panel**: `http://<host>:3000`
- **API docs**: `http://<host>:8484/docs`

Default admin credentials (created by seed on first boot):
- Email: `admin@warden.local`
- Password: `warden-admin` — **change this immediately after first login**

### Flutter App

Build and install the APK:

```bash
flutter pub get
flutter build apk --release
adb install build/app/outputs/flutter-apk/app-release.apk
```

On first launch, the app displays a pairing code. Log into the admin panel → **Devices** → **Authorize Device** and enter the code.

## Development (without Docker)

> Node.js is managed via [nvm](https://github.com/nvm-sh/nvm). The go2rtc binary lives in the project root.

**Terminal 1 — go2rtc**
```bash
~/Documents/flutter_projects/warden/go2rtc -config ~/Documents/flutter_projects/warden/warden-api/go2rtc_dev.yaml
```

Or add it to your PATH once:
```bash
sudo ln -s ~/Documents/flutter_projects/warden/go2rtc /usr/local/bin/go2rtc
```
Then simply: `go2rtc -config warden-api/go2rtc_dev.yaml`

**Terminal 2 — warden-api**
```bash
cd ~/Documents/flutter_projects/warden/warden-api
source venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8484
```

> `--host 0.0.0.0` is required so devices on the LAN (e.g. Android tablet) can reach the API.

**Terminal 3 — warden-admin**
```bash
cd ~/Documents/flutter_projects/warden/warden-admin
source ~/.nvm/nvm.sh && npm run dev
```

**Terminal 4 — Flutter (on device via ADB)**
```bash
cd ~/Documents/flutter_projects/warden
flutter run -d <device-ip>:<adb-port>
```

Example (Samsung tablet over ADB wireless):
```bash
flutter run -d 192.168.10.108:37009
```

Set the server URL in the app to `http://<host-ip>:8484` when pairing (e.g. `http://192.168.10.121:8484`).

To find your host IP:
```bash
ip route get 1 | awk '{print $7; exit}'
```

### First-time setup
```bash
cd warden-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python seed.py
```

## Stack

| Layer | Technology |
|---|---|
| Flutter app | Flutter 3, Riverpod, flutter_webrtc, device_info_plus |
| Backend | FastAPI, SQLAlchemy, Alembic, SQLite (Postgres-ready) |
| Stream relay | go2rtc |
| Admin panel | React, MUI, TanStack Query, Vite |
| Serving | nginx (admin), uvicorn (API) |
| Deployment | Docker Compose |
