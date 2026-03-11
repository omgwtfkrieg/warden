from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import httpx

from app.config import settings
from app.database import get_db
from app.dependencies import require_permission
from app.models import Camera
from app.services.go2rtc_service import get_credentials

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.get("/health/detail")
def health_detail(
    db: Session = Depends(get_db),
    _=Depends(require_permission("cameras:read")),
):
    """
    Returns live status of the API, go2rtc, and each camera stream.
    Used by the admin panel dashboard only — never called by the Flutter app.
    go2rtc credentials never leave the backend.
    """
    go2rtc_online = False
    active_streams: set[str] = set()

    try:
        username, password = get_credentials(db)
        with httpx.Client(auth=(username, password), timeout=3.0) as client:
            resp = client.get(f"{settings.go2rtc_url}/api/streams")
            if resp.is_success:
                go2rtc_online = True
                for name, info in resp.json().items():
                    # go2rtc marks a stream as active when it has producers
                    if info.get("producers"):
                        active_streams.add(name)
    except Exception:
        pass

    cameras = db.query(Camera).order_by(Camera.display_order, Camera.id).all()
    camera_statuses = []
    for cam in cameras:
        if not go2rtc_online:
            stream_status = "unknown"
        elif not cam.stream_path:
            stream_status = "unconfigured"
        elif cam.stream_path in active_streams:
            stream_status = "active"
        else:
            stream_status = "inactive"

        camera_statuses.append({
            "id": cam.id,
            "name": cam.name,
            "stream_path": cam.stream_path,
            "status": stream_status,
        })

    return {
        "api": "online",
        "go2rtc": "online" if go2rtc_online else "offline",
        "cameras": camera_statuses,
    }
