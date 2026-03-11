## Project: Warden — Flutter RTSP Camera Stream Viewer + Platform Backend

### System Overview
Warden is a multi-component platform:
- **FastAPI backend** — config authority, auth, pairing, user management, go2rtc proxy
- **React admin panel** (shadcn/ui) — camera setup, user management, device authorization
- **Flutter app** (TV/tablet/mobile) — thin streaming client, activated via pairing
- **go2rtc** — internal-only stream relay, config written and managed by the backend

All components run via Docker Compose:
```yaml
services:
  go2rtc:        # Internal Docker network only — never exposed to LAN
  warden-api:    # :8484 — only externally exposed service (besides admin panel)
  warden-admin:  # :3000
```

---

### go2rtc Security Model

go2rtc is **never accessible outside Docker**. It has no published ports.

- Port `1984` exists only on the internal Docker network
- warden-api is the **only** entity that communicates with go2rtc
- go2rtc basic auth credentials are **auto-generated** by warden-api on first boot
- Credentials are stored in the DB and written into go2rtc's config file
- Credentials are never exposed to the Flutter app, admin panel, or any external client
- Flutter app streams video via `warden-api/streams/{id}` — warden-api proxies WebRTC
  signaling to go2rtc internally, then the video stream flows directly (but authorized)

**Defense in depth**: even if someone reached the internal Docker network, go2rtc still
requires basic auth credentials that only warden-api knows.
```
Flutter App (LAN)
      │
      ▼ device token validated
warden-api :8484 (exposed)
      │
      ▼ internal Docker network only
go2rtc :1984 (never exposed) ← basic auth credentials from warden-api
```

---

### Backend (FastAPI) — `warden-api/`

**Database**: SQLite via SQLAlchemy + Alembic migrations.
Never use SQLite-specific syntax — must be Postgres-compatible for future migration.

**Core tables**:
| Table | Purpose |
|---|---|
| `users` | id, email, hashed_password, role_id, is_active, created_at |
| `roles` | id, name, permissions (JSON array of strings) |
| `cameras` | id, name, ip_address, rtsp_url, stream metadata fields |
| `app_devices` | id, user_id, device_name, device_token, paired_at, revoked |
| `pairing_codes` | id, code, user_id, status, expires_at, created_at |
| `system_config` | id, key, value — stores go2rtc credentials and system settings |

**Auth**:
- Admin panel: email/password → JWT access token (15min) + refresh token (7 days)
- Flutter app: pairing code → long-lived device token (not a JWT, not user credentials)
- Device token is independent — revoking it never affects the user account
- User can view and revoke all authorized devices from the admin panel

**Roles & Permissions** (JSON permission list per role):
| Role | Permissions |
|---|---|
| `admin` | Full access — users, cameras, devices, config |
| `operator` | Manage cameras and go2rtc config, cannot manage users |
| `viewer` | View streams only, read-only |

**Configuration ownership**:
- Cameras configured in admin panel → stored in backend DB
- Backend writes go2rtc config as a side effect of camera changes
- Backend generates and manages go2rtc basic auth credentials
- Flutter app fetches camera config from backend API using device token
- go2rtc is not aware of users, roles, devices, or credentials beyond its own basic auth

**go2rtc interaction** (internal only):
- warden-api writes go2rtc config file via shared Docker volume
- warden-api signals go2rtc to reload config after changes
- warden-api proxies WebRTC signaling: `GET /streams/{id}/webrtc` → go2rtc internally
- All go2rtc API calls from warden-api include the stored basic auth credentials

**Pairing flow**:
1. Flutter app calls `POST /pair/request` → receives `code` + QR payload + expiry
2. Code displayed on TV/tablet (format: `W7X2-K4P9`, 5min expiry, single-use)
3. Admin logs into admin panel → "Authorize Device" → enters code or scans QR
4. Backend validates code → creates device token → marks code used
5. Flutter app polls `GET /pair/status?code=...` → receives device token + camera list
6. Stream URLs in camera list point to `warden-api/streams/{id}` — never to go2rtc directly
7. Flutter app stores device token, skips setup wizard on all future launches

---

### Admin Panel (React + shadcn/ui) — `warden-admin/`

- Single-page React app, served as static files
- Communicates with warden-api only — never talks to go2rtc directly
- Sections: Dashboard, Cameras, Users, Devices (authorized apps), Settings
- Camera config here replaces the Flutter setup wizard entirely

---

### Flutter App — `lib/`

The Flutter app is a **thin streaming client** after pairing.

**Simplified responsibilities**:
- `settings_repository.dart` — stores device token + warden-api server URL only
- `metadata_capture_service.dart` — syncs camera list from backend API using device token
- `connection_manager.dart` — unchanged, handles WebRTC connections
- `network_scanner.dart` — deprecated; server URL comes from QR/pairing
- `pairing_service.dart` — new SSoT for all pairing API calls

Stream URLs received from the backend point to `warden-api/streams/{id}`.
The Flutter app never constructs or knows go2rtc URLs.

---

### Flutter SSoT Files
| File | Authority Over |
|---|---|
| `lib/metadata.dart` | `AppMetadata`, `CameraDevice` models, `appMetadataProvider` |
| `lib/connection_manager.dart` | Connection lifecycle, pooling, reconnect logic |
| `lib/settings_repository.dart` | All Flutter-side persistence (device token, server URL) |
| `lib/app_reset_manager.dart` | Only entity allowed to trigger full app reset |
| `lib/metadata_capture_service.dart` | Only entity allowed to create/update/remove camera metadata |
| `lib/error_handler.dart` | `AppError`, `Result<T>` — check before implementing any error handling |
| `lib/theme_utils.dart` | Material 3 theming — never hardcode colors or TextStyles |
| `lib/animation_mixin.dart` | All animation controllers and transitions |
| `lib/validation_utils.dart` | Input validation, URL normalization |
| `lib/pairing_service.dart` | All pairing API calls — new SSoT |

---

### Code Rules (apply to all components)

**Flutter**:
- Prefer editing existing files over creating new ones
- Artifact name = file path (e.g. `lib/pairing_service.dart`)
- For existing files: provide only the block to add/modify/remove with explicit location
- Do not over-engineer — keep it simple and direct
- No duplication of SSoT logic
- Check `error_handler.dart` before implementing any error handling
- Never call `ref.read` inside `build()` — use `ref.watch`

**Backend**:
- Artifact name = file path (e.g. `warden-api/routers/pairing.py`)
- One router per domain: `auth`, `cameras`, `pairing`, `users`, `devices`, `streams`
- Never put business logic in routers — use service layer
- All DB access through SQLAlchemy models, never raw SQL
- Alembic for all schema changes — never modify DB schema manually
- go2rtc credentials never leave the backend — not in API responses, not in logs

**General**:
- Do not build ahead — implement only what is currently scoped
- Do not over-engineer

---

### Build Plan

#### Phase 1 — Project Scaffold & Database

**Step 1: Project structure + Docker Compose**
Create `warden-api/` folder structure, `Dockerfile`, and `docker-compose.yml` with three
services. go2rtc has no published ports — internal Docker network only. warden-api and
warden-admin are the only externally accessible services. Include a health check endpoint
at `GET /health`.

**Step 2: Database models + Alembic**
SQLAlchemy models: `users`, `roles`, `cameras`, `app_devices`, `pairing_codes`,
`system_config`. First Alembic migration generates the SQLite schema. Never use
SQLite-specific syntax.

**Step 3: Seed data**
Seed script creates default `admin`, `operator`, `viewer` roles and a first `admin` user
on clean install.

---

#### Phase 2 — Authentication

**Step 4: Auth endpoints**
`POST /auth/login` → JWT access token (15min) + refresh token (7 days).
`POST /auth/refresh` → new access token from refresh token.
`POST /auth/logout` → invalidates refresh token.

**Step 5: Auth middleware + permission guards**
JWT validation dependency. Role-based permission decorator
(`require_permission("cameras:write")`). Applied to all protected routes.

---

#### Phase 3 — go2rtc Security + Camera Management

**Step 6: go2rtc credential bootstrap**
On first boot, warden-api generates random basic auth credentials, stores them in
`system_config`, and writes them into go2rtc's config file via shared Docker volume.
go2rtc is signaled to reload. Credentials used internally for all go2rtc API calls —
never exposed externally. Never logged.

**Step 7: Camera CRUD endpoints**
`GET/POST /cameras`, `GET/PUT/DELETE /cameras/{id}`.
Writing or updating a camera triggers go2rtc config sync as a side effect.

**Step 8: go2rtc config sync service**
Service layer that writes the current camera list from DB into go2rtc's config file
(including the stored basic auth block) and signals go2rtc to reload. Called by all
camera write operations.

---

#### Phase 4 — Stream Proxy

**Step 9: Stream proxy endpoints**
`GET /streams/{id}/webrtc` — validates device token, checks camera permission, proxies
WebRTC signaling to go2rtc internally using stored credentials. Flutter app never knows
go2rtc exists. All stream URLs returned to Flutter point to warden-api, never go2rtc.

---

#### Phase 5 — Pairing Flow

**Step 10: Pairing endpoints**
`POST /pair/request` — Flutter app receives `code` + QR payload + expiry.
`GET /pair/status?code=...` — Flutter polls; returns `pending`, `approved` (with device
token + camera list using warden-api stream URLs), or `expired`.
`POST /pair/activate` — Admin panel approves a code and assigns user config.

**Step 11: Device token management**
`GET /devices` — admin lists all authorized devices for their account.
`DELETE /devices/{id}` — revokes a device token immediately.

---

#### Phase 6 — Flutter App Updates

**Step 12: `lib/pairing_service.dart`**
New SSoT. Implements `requestCode`, `pollStatus`, `activate`. Handles polling with
exponential backoff. Uses existing `Result<T>` and `AppError` from `error_handler.dart`.

**Step 13: Replace setup wizard with pairing screen**
Single screen: displays generated code + QR, shows polling status
("Waiting for authorization..."), transitions to camera grid on success. Removes
dependency on `network_scanner.dart`.

**Step 14: Update `settings_repository.dart`**
Store device token + warden-api server URL. Remove go2rtc URL and camera credentials
that were stored previously.

**Step 15: Update `metadata_capture_service.dart`**
Sync camera list from backend API using device token. Stream URLs come from backend —
no go2rtc URL construction in Flutter.

---

#### Phase 7 — Integration & Testing

**Step 16: End-to-end pairing test**
Full flow: app requests code → admin panel activates → app receives token → camera list
loaded from backend → streams play via warden-api proxy.

**Step 17: Docker Compose full-stack test**
`docker-compose up` from scratch: go2rtc credentials auto-generated, go2rtc unreachable
from outside Docker (verified), seed data present, pairing flow works end-to-end.