import logging
import secrets

import httpx
import yaml
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Camera, SystemConfig

logger = logging.getLogger(__name__)

_USER_KEY = "go2rtc_username"
_PASS_KEY = "go2rtc_password"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get(key: str, db: Session) -> str | None:
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    return row.value if row else None


def _set(key: str, value: str, db: Session) -> None:
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if row:
        row.value = value
    else:
        db.add(SystemConfig(key=key, value=value))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _stream_source(cam: Camera) -> str:
    """Return the go2rtc source string for a camera.

    Preference order:
    1. sub_rtsp_url — native H264 from the camera, no transcoding needed.
    2. rtsp_url + ffmpeg — transcode main stream (e.g. H265→H264) when use_ffmpeg=True.
    3. rtsp_url — pass through as-is.
    """
    if cam.sub_rtsp_url and cam.use_sub_stream:
        return cam.sub_rtsp_url
    if cam.use_ffmpeg:
        return f"ffmpeg:{cam.rtsp_url}#video=h264#audio=aac"
    return cam.rtsp_url


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_credentials(db: Session) -> tuple[str, str]:
    username = _get(_USER_KEY, db)
    password = _get(_PASS_KEY, db)
    if not username or not password:
        raise RuntimeError("go2rtc credentials not initialised")
    return username, password


def bootstrap(db: Session) -> None:
    """Called once on app startup. Generates credentials if absent, then writes config."""
    if not _get(_USER_KEY, db):
        username = "warden"
        password = secrets.token_urlsafe(32)
        _set(_USER_KEY, username, db)
        _set(_PASS_KEY, password, db)
        db.commit()
        logger.info("go2rtc credentials generated")

    write_config(db)
    sync_streams(db)


def write_config(db: Session) -> None:
    """Write the full go2rtc YAML config (auth + all streams) to the shared volume."""
    try:
        username, password = get_credentials(db)
    except RuntimeError:
        logger.warning("go2rtc credentials missing — skipping config write")
        return

    cameras = db.query(Camera).all()

    config: dict = {
        "api": {
            "listen": ":1984",
            "username": username,
            "password": password,
        },
        "streams": {
            cam.stream_path: [_stream_source(cam)]
            for cam in cameras
            if cam.stream_path
        },
    }

    try:
        with open(settings.go2rtc_config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        logger.info("go2rtc config written to %s", settings.go2rtc_config_path)
    except OSError as e:
        logger.warning("Could not write go2rtc config: %s", e)


def sync_streams(db: Session) -> None:
    """
    Sync cameras to go2rtc via its REST API (no restart required).
    Failures are non-fatal — go2rtc may not be reachable in dev mode.
    """
    try:
        username, password = get_credentials(db)
    except RuntimeError:
        return

    cameras = db.query(Camera).all()
    auth = (username, password)

    try:
        with httpx.Client(auth=auth, timeout=5.0) as client:
            # Fetch current streams
            resp = client.get(f"{settings.go2rtc_url}/api/streams")
            existing: set[str] = set(resp.json().keys()) if resp.is_success else set()

            active: set[str] = set()
            for cam in cameras:
                if not cam.stream_path:
                    continue
                src = _stream_source(cam)
                client.put(
                    f"{settings.go2rtc_url}/api/streams",
                    params={"src": src, "name": cam.stream_path},
                )
                active.add(cam.stream_path)

            # Remove stale streams
            for name in existing - active:
                client.delete(f"{settings.go2rtc_url}/api/streams", params={"name": name})

        logger.info("go2rtc streams synced (%d cameras)", len(active))

    except Exception as e:
        logger.warning("go2rtc stream sync failed (non-fatal): %s", e)
