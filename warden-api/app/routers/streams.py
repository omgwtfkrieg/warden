from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_device
from app.models import AppDevice, Camera
from app.services import stream_service

router = APIRouter(prefix="/streams", tags=["streams"])


def _aspect_ratio(c: Camera) -> float:
    meta = c.stream_metadata or {}
    if c.use_sub_stream and c.sub_rtsp_url:
        stream = meta.get("sub") or {}
    else:
        stream = meta.get("main") or {}
    w, h = stream.get("width"), stream.get("height")
    if w and h and h > 0:
        return round(w / h, 4)
    return round(16 / 9, 4)


@router.get("/cameras")
def app_camera_list(
    db: Session = Depends(get_db),
    device: AppDevice = Depends(get_device),
):
    """Returns the camera list for a paired Flutter app device. Device token required."""
    cameras = db.query(Camera).order_by(Camera.display_order, Camera.id).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "stream_url": f"/streams/{c.id}/webrtc",
            "use_sub_stream": c.use_sub_stream,
            "display_order": c.display_order,
            "aspect_ratio": _aspect_ratio(c),
        }
        for c in cameras
    ]


@router.post("/{camera_id}/webrtc")
async def proxy_webrtc(
    camera_id: int,
    request: Request,
    db: Session = Depends(get_db),
    device: AppDevice = Depends(get_device),
):
    """
    Proxy WebRTC signaling to go2rtc on behalf of the Flutter app.
    Accepts an SDP offer, returns an SDP answer.
    Device token required — go2rtc credentials are never exposed to the client.
    """
    resp = await stream_service.proxy_webrtc(camera_id, request, db)
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/sdp"),
    )
