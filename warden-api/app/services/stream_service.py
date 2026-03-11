import logging

import httpx
from fastapi import HTTPException, Request, status

from app.config import settings
from app.models import Camera
from app.services import go2rtc_service

logger = logging.getLogger(__name__)


def get_stream_camera(camera_id: int, db) -> Camera:
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    if not camera.stream_path:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Camera stream not configured")
    return camera


async def proxy_webrtc(camera_id: int, request: Request, db) -> httpx.Response:
    """
    Proxy a WebRTC SDP offer to go2rtc and return the SDP answer.
    The Flutter app never communicates with go2rtc directly.
    """
    camera = get_stream_camera(camera_id, db)

    try:
        username, password = go2rtc_service.get_credentials(db)
    except RuntimeError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stream service unavailable")

    body = await request.body()
    content_type = request.headers.get("content-type", "application/sdp")

    try:
        async with httpx.AsyncClient(auth=(username, password), timeout=30.0) as client:
            resp = await client.post(
                f"{settings.go2rtc_url}/api/webrtc",
                params={"src": camera.stream_path},
                content=body,
                headers={"Content-Type": content_type},
            )
    except httpx.ConnectError:
        logger.error("go2rtc unreachable at %s", settings.go2rtc_url)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stream service unavailable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Stream service timed out")

    if not resp.is_success:
        logger.warning("go2rtc returned %s for stream %s", resp.status_code, camera.stream_path)
        raise HTTPException(status_code=resp.status_code, detail="Stream service error")

    return resp
