from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_permission
from app.schemas.camera import (
    CameraCreate, CameraUpdate, CameraResponse,
    CameraTestRequest, CameraTestResponse, ProbeResponse,
    CameraDiscoverRequest, CameraDiscoverResponse,
    ProbeUrlRequest, ProbeUrlResponse,
    CameraReorderRequest,
)
from app.services import camera_service

router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("", response_model=list[CameraResponse])
def list_cameras(
    db: Session = Depends(get_db),
    _=Depends(require_permission("cameras:read")),
):
    return camera_service.list_cameras(db)


@router.post("/discover", response_model=CameraDiscoverResponse)
async def discover_camera(
    payload: CameraDiscoverRequest,
    _=Depends(require_permission("cameras:read")),
):
    return await camera_service.discover_camera(payload.ip, payload.username, payload.password)


@router.post("/test", response_model=CameraTestResponse)
async def test_camera_connection(
    payload: CameraTestRequest,
    _=Depends(require_permission("cameras:read")),
):
    return await camera_service.test_connection(payload.rtsp_url)


@router.post("/probe-url", response_model=ProbeUrlResponse)
async def probe_url(
    payload: ProbeUrlRequest,
    _=Depends(require_permission("cameras:read")),
):
    metadata = await camera_service.probe_url(payload.rtsp_url)
    return ProbeUrlResponse(metadata=metadata)


@router.post("", response_model=CameraResponse, status_code=201)
def create_camera(
    payload: CameraCreate,
    db: Session = Depends(get_db),
    _=Depends(require_permission("cameras:write")),
):
    return camera_service.create_camera(payload, db)


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("cameras:read")),
):
    return camera_service.get_camera(camera_id, db)


@router.put("/{camera_id}", response_model=CameraResponse)
def update_camera(
    camera_id: int,
    payload: CameraUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_permission("cameras:write")),
):
    return camera_service.update_camera(camera_id, payload, db)


@router.delete("/{camera_id}", status_code=204)
def delete_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("cameras:write")),
):
    camera_service.delete_camera(camera_id, db)


@router.post("/reorder", status_code=204)
def reorder_cameras(
    payload: CameraReorderRequest,
    db: Session = Depends(get_db),
    _=Depends(require_permission("cameras:write")),
):
    camera_service.reorder_cameras(payload.cameras, db)


@router.post("/{camera_id}/probe", response_model=ProbeResponse)
async def probe_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_permission("cameras:write")),
):
    metadata = await camera_service.probe_camera(camera_id, db)
    return ProbeResponse(camera_id=camera_id, metadata=metadata)
