import asyncio
import json
import logging
import urllib.parse
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Camera
from app.schemas.camera import CameraCreate, CameraUpdate, CameraTestResponse, CameraOrderItem
from app.services import go2rtc_service, keepalive_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def list_cameras(db: Session) -> list[Camera]:
    return db.query(Camera).order_by(Camera.display_order, Camera.id).all()


def get_camera(camera_id: int, db: Session) -> Camera:
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")
    return camera



def _sync_keepalive(db: Session) -> None:
    try:
        username, password = go2rtc_service.get_credentials(db)
        always_on = [
            c.stream_path for c in db.query(Camera).filter(
                Camera.always_on == True, Camera.stream_path != None
            ).all()
        ]
        keepalive_service.sync(always_on, username, password)
    except Exception:
        pass


def create_camera(data: CameraCreate, db: Session) -> Camera:
    camera = Camera(
        name=data.name,
        ip_address=data.ip_address,
        rtsp_url=data.rtsp_url,
        sub_rtsp_url=data.sub_rtsp_url,
        use_ffmpeg=data.use_ffmpeg,
        use_sub_stream=data.use_sub_stream,
        always_on=data.always_on,
        display_order=data.display_order,
    )
    db.add(camera)
    db.flush()
    camera.stream_path = f"camera_{camera.id}"
    if data.stream_metadata:
        camera.stream_metadata = data.stream_metadata
    db.commit()
    db.refresh(camera)

    go2rtc_service.write_config(db)
    go2rtc_service.sync_streams(db)
    _sync_keepalive(db)

    return camera


def update_camera(camera_id: int, data: CameraUpdate, db: Session) -> Camera:
    camera = get_camera(camera_id, db)

    if data.name is not None:
        camera.name = data.name
    if data.ip_address is not None:
        camera.ip_address = data.ip_address
    if data.rtsp_url is not None:
        camera.rtsp_url = data.rtsp_url
    if data.sub_rtsp_url is not None:
        camera.sub_rtsp_url = data.sub_rtsp_url
    if data.use_ffmpeg is not None:
        camera.use_ffmpeg = data.use_ffmpeg
    if data.use_sub_stream is not None:
        camera.use_sub_stream = data.use_sub_stream
    if data.always_on is not None:
        camera.always_on = data.always_on
    if data.display_order is not None:
        camera.display_order = data.display_order

    db.commit()
    db.refresh(camera)

    go2rtc_service.write_config(db)
    go2rtc_service.sync_streams(db)
    _sync_keepalive(db)

    return camera


def reorder_cameras(items: list[CameraOrderItem], db: Session) -> None:
    id_map = {item.id: item.display_order for item in items}
    cameras = db.query(Camera).filter(Camera.id.in_(id_map.keys())).all()
    for camera in cameras:
        camera.display_order = id_map[camera.id]
    db.commit()


def delete_camera(camera_id: int, db: Session) -> None:
    camera = get_camera(camera_id, db)
    db.delete(camera)
    db.commit()

    go2rtc_service.write_config(db)
    go2rtc_service.sync_streams(db)
    _sync_keepalive(db)


# ---------------------------------------------------------------------------
# Connection test (quick reachability check)
# ---------------------------------------------------------------------------

async def test_connection(rtsp_url: str) -> CameraTestResponse:
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-rtsp_transport", "tcp",
            "-timeout", "8000000",
            rtsp_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        except asyncio.TimeoutError:
            proc.kill()
            return CameraTestResponse(reachable=False, message="Connection timed out")

        if proc.returncode != 0:
            return CameraTestResponse(reachable=False, message="ffprobe could not open stream — check URL and credentials")

        data = json.loads(stdout)
        streams = data.get("streams", [])
        video = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

        return CameraTestResponse(
            reachable=True,
            message="Stream reachable",
            video_codec=video.get("codec_name") if video else None,
            audio_codec=audio.get("codec_name") if audio else None,
        )

    except FileNotFoundError:
        logger.warning("ffprobe not found, falling back to TCP check")
        return await _tcp_check(rtsp_url)
    except Exception as e:
        logger.warning("ffprobe error: %s", e)
        return CameraTestResponse(reachable=False, message=f"Probe error: {e}")


async def _tcp_check(rtsp_url: str) -> CameraTestResponse:
    try:
        parsed = urllib.parse.urlparse(rtsp_url)
        host = parsed.hostname
        port = parsed.port or 554
        if not host:
            return CameraTestResponse(reachable=False, message="Could not parse host from URL")
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=5)
        writer.close()
        await writer.wait_closed()
        return CameraTestResponse(reachable=True, message=f"Host reachable at {host}:{port} (ffprobe not installed)")
    except asyncio.TimeoutError:
        return CameraTestResponse(reachable=False, message="Connection timed out")
    except Exception as e:
        return CameraTestResponse(reachable=False, message=str(e))


# ---------------------------------------------------------------------------
# Stream metadata probing
# ---------------------------------------------------------------------------

async def probe_camera(camera_id: int, db: Session) -> dict:
    """
    Probe main + sub streams. Tries Reolink HTTP API first (parses
    credentials from the RTSP URL), then falls back to ffprobe.
    Saves result to camera.stream_metadata.
    """
    camera = get_camera(camera_id, db)

    parsed = urllib.parse.urlparse(camera.rtsp_url)
    host = parsed.hostname
    username = parsed.username
    password = parsed.password

    metadata: dict = {"probed_at": datetime.now(timezone.utc).isoformat()}

    # Try Reolink API
    if host and username and password:
        reolink = await _probe_reolink(host, username, password)
        if reolink:
            metadata.update(reolink)
            camera.stream_metadata = metadata
            db.commit()
            return metadata

    # Fall back to ffprobe
    metadata["source"] = "ffprobe"

    main = await _ffprobe_stream(camera.rtsp_url)
    if main:
        metadata["main"] = main

    if camera.sub_rtsp_url:
        sub = await _ffprobe_stream(camera.sub_rtsp_url)
        if sub:
            metadata["sub"] = sub

    camera.stream_metadata = metadata
    db.commit()
    return metadata


async def _probe_reolink(host: str, username: str, password: str) -> dict | None:
    """
    Query the Reolink HTTP API for encoding settings.
    Returns a metadata dict with main/sub stream info, or None if unreachable/not Reolink.
    Tries HTTP first, then HTTPS (newer Reolink cameras require HTTPS).
    Credentials are parsed from the RTSP URL and never logged.
    """
    def parse_reolink_stream(s: dict) -> dict:
        result: dict = {}
        size = s.get("size", "")
        if "*" in size:
            parts = size.split("*")
            try:
                result["width"] = int(parts[0])
                result["height"] = int(parts[1])
            except ValueError:
                pass
        codec = s.get("vType", "")
        if codec:
            result["codec"] = codec.lower().replace("h265", "hevc").replace("h264", "h264")
        if s.get("frameRate") is not None:
            result["fps"] = s["frameRate"]
        if s.get("bitRate") is not None:
            result["bitrate_kbps"] = s["bitRate"]
        return result

    for scheme in ("http", "https"):
        base = f"{scheme}://{host}"
        try:
            async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
                # Login
                resp = await client.post(
                    f"{base}/api.cgi?cmd=Login",
                    json=[{"cmd": "Login", "action": 0, "param": {
                        "User": {"userName": username, "password": password}
                    }}],
                )
                logger.warning("Reolink login %s status=%s", base, resp.status_code)
                if not resp.is_success:
                    logger.warning("Reolink login failed for %s: HTTP %s — %s", base, resp.status_code, resp.text[:200])
                    continue

                try:
                    login_data = resp.json()
                except Exception:
                    logger.warning("Reolink login response not JSON for %s: %s", base, resp.text[:200])
                    continue

                # Token may be at login_data[0]["value"]["Token"]["name"]
                token = None
                try:
                    token = login_data[0].get("value", {}).get("Token", {}).get("name")
                except (IndexError, AttributeError, TypeError) as e:
                    logger.warning("Reolink token parse error for %s: %s — raw: %s", base, e, str(login_data)[:200])

                if not token:
                    logger.warning("Reolink: no token in login response for %s: %s", base, str(login_data)[:200])
                    continue

                # GetEnc
                resp = await client.post(
                    f"{base}/api.cgi?cmd=GetEnc&token={token}",
                    json=[{"cmd": "GetEnc", "action": 0, "param": {"channel": 0}}],
                )
                if not resp.is_success:
                    logger.warning("Reolink GetEnc failed for %s: HTTP %s", base, resp.status_code)
                    continue

                try:
                    enc_data = resp.json()
                except Exception:
                    logger.warning("Reolink GetEnc response not JSON for %s", base)
                    continue

                enc = enc_data[0].get("value", {}).get("Enc", {})
                logger.warning("Reolink Enc keys for %s: %s", base, list(enc.keys()))

            metadata: dict = {"source": "reolink_api"}
            if "mainStream" in enc:
                metadata["main"] = parse_reolink_stream(enc["mainStream"])
            if "subStream" in enc:
                metadata["sub"] = parse_reolink_stream(enc["subStream"])

            if "main" in metadata or "sub" in metadata:
                return metadata

            logger.warning("Reolink: Enc has no mainStream/subStream for %s: %s", base, list(enc.keys()))

        except httpx.ConnectError as e:
            logger.warning("Reolink %s connect error: %s", base, e)
        except httpx.TimeoutException as e:
            logger.warning("Reolink %s timeout: %s", base, e)
        except Exception as e:
            logger.warning("Reolink API error for %s: %s", base, e)

    return None


async def _ffprobe_stream(rtsp_url: str) -> dict | None:
    """Run ffprobe on an RTSP URL and return stream metadata dict."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-rtsp_transport", "tcp",
            "-timeout", "8000000",
            rtsp_url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=12)
        except asyncio.TimeoutError:
            proc.kill()
            return None

        if proc.returncode != 0:
            return None

        data = json.loads(stdout)
        streams = data.get("streams", [])
        video = next((s for s in streams if s.get("codec_type") == "video"), None)
        if not video:
            return None

        result: dict = {
            "width": video.get("width"),
            "height": video.get("height"),
            "codec": video.get("codec_name"),
        }

        # Parse fps from rational string e.g. "15/1" or "30000/1001"
        r_fps = video.get("r_frame_rate", "")
        if "/" in r_fps:
            try:
                num, den = r_fps.split("/")
                fps = round(int(num) / int(den), 2)
                result["fps"] = fps
            except (ValueError, ZeroDivisionError):
                pass

        # Bitrate in kbps
        raw_bitrate = video.get("bit_rate")
        if raw_bitrate:
            try:
                result["bitrate_kbps"] = int(raw_bitrate) // 1000
            except ValueError:
                pass

        return result

    except FileNotFoundError:
        logger.warning("ffprobe not installed")
        return None
    except Exception as e:
        logger.warning("ffprobe stream error: %s", e)
        return None


async def discover_camera(ip: str, username: str, password: str) -> dict:
    """
    Probe a camera by IP + credentials. Tries Reolink API first to determine
    stream capabilities and codec, then constructs the correct RTSP URLs.
    Credentials are kept as-is (not URL-encoded) so special characters like @
    in passwords remain intact for ffmpeg/go2rtc compatibility.
    Credentials are never logged.
    """
    reolink = await _probe_reolink(ip, username, password)

    if reolink:
        main_meta = reolink.get("main", {})
        codec = main_meta.get("codec", "hevc")
        # Reolink main stream path depends on the configured codec
        main_prefix = "h265" if codec in ("hevc", "h265") else "h264"
        main_url = f"rtsp://{username}:{password}@{ip}:554/{main_prefix}Preview_01_main"
        # Reolink cameras always have a sub stream (H.264 low-res)
        sub_url = f"rtsp://{username}:{password}@{ip}:554/h264Preview_01_sub"
        return {
            "is_reolink": True,
            "main_rtsp_url": main_url,
            "sub_rtsp_url": sub_url,
            "metadata": reolink,
        }

    # Not a Reolink camera — return a template the user can fill in
    return {
        "is_reolink": False,
        "main_rtsp_url": f"rtsp://{username}:{password}@{ip}:554/",
        "sub_rtsp_url": None,
        "metadata": None,
    }


async def probe_url(rtsp_url: str) -> dict | None:
    """Run ffprobe on a bare RTSP URL and return stream metadata, or None on failure."""
    stream = await _ffprobe_stream(rtsp_url)
    if not stream:
        return None
    from datetime import datetime, timezone
    return {
        "source": "ffprobe",
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "main": stream,
    }
