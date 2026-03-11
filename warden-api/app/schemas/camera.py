from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CameraCreate(BaseModel):
    name: str
    ip_address: str | None = None
    rtsp_url: str
    sub_rtsp_url: str | None = None
    use_ffmpeg: bool = False
    use_sub_stream: bool = True
    always_on: bool = False
    display_order: int = 0
    stream_metadata: dict | None = None


class CameraUpdate(BaseModel):
    name: str | None = None
    ip_address: str | None = None
    rtsp_url: str | None = None
    sub_rtsp_url: str | None = None
    use_ffmpeg: bool | None = None
    use_sub_stream: bool | None = None
    always_on: bool | None = None
    display_order: int | None = None


class CameraResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    ip_address: str | None
    rtsp_url: str
    sub_rtsp_url: str | None
    use_ffmpeg: bool
    use_sub_stream: bool
    always_on: bool
    display_order: int
    stream_path: str | None
    stream_metadata: dict | None
    created_at: datetime
    updated_at: datetime


class CameraOrderItem(BaseModel):
    id: int
    display_order: int


class CameraReorderRequest(BaseModel):
    cameras: list[CameraOrderItem]


class CameraTestRequest(BaseModel):
    rtsp_url: str


class CameraTestResponse(BaseModel):
    reachable: bool
    message: str
    video_codec: str | None = None
    audio_codec: str | None = None


class ProbeResponse(BaseModel):
    camera_id: int
    metadata: dict


class CameraDiscoverRequest(BaseModel):
    ip: str
    username: str
    password: str


class CameraDiscoverResponse(BaseModel):
    is_reolink: bool
    main_rtsp_url: str
    sub_rtsp_url: str | None
    metadata: dict | None


class ProbeUrlRequest(BaseModel):
    rtsp_url: str


class ProbeUrlResponse(BaseModel):
    metadata: dict | None
