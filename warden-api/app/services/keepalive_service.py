"""
Keepalive service — maintains persistent WebSocket connections to go2rtc for
cameras marked always_on=True, ensuring go2rtc keeps those streams warm.
"""
import asyncio
import base64
import logging

import websockets

from app.config import settings

logger = logging.getLogger(__name__)

# stream_path -> asyncio.Task
_tasks: dict[str, asyncio.Task] = {}


def _auth_header(username: str, password: str) -> dict:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


async def _keepalive_loop(stream_path: str, username: str, password: str) -> None:
    """Holds a WebSocket connection to go2rtc for one stream indefinitely."""
    ws_url = settings.go2rtc_url.replace("http://", "ws://").replace("https://", "wss://")
    url = f"{ws_url}/api/ws?src={stream_path}"
    headers = _auth_header(username, password)

    while True:
        try:
            async with websockets.connect(url, additional_headers=headers) as ws:
                logger.info("Keepalive connected: %s", stream_path)
                # Read and discard messages to keep the connection open
                async for _ in ws:
                    pass
        except asyncio.CancelledError:
            logger.info("Keepalive cancelled: %s", stream_path)
            return
        except Exception as e:
            logger.debug("Keepalive %s lost (%s), reconnecting in 10s", stream_path, e)
            await asyncio.sleep(10)


def start(stream_paths: list[str], username: str, password: str) -> None:
    """Start keepalive tasks for the given stream paths."""
    for path in stream_paths:
        if path not in _tasks or _tasks[path].done():
            _tasks[path] = asyncio.create_task(
                _keepalive_loop(path, username, password),
                name=f"keepalive:{path}",
            )
            logger.info("Keepalive started: %s", path)


def stop(stream_paths: list[str] | None = None) -> None:
    """Cancel keepalive tasks. If stream_paths is None, cancel all."""
    targets = list(_tasks.keys()) if stream_paths is None else stream_paths
    for path in targets:
        task = _tasks.pop(path, None)
        if task and not task.done():
            task.cancel()
            logger.info("Keepalive stopped: %s", path)


def sync(stream_paths: list[str], username: str, password: str) -> None:
    """Reconcile running tasks with the desired set of always-on streams."""
    desired = set(stream_paths)
    current = set(_tasks.keys())

    stop(list(current - desired))
    start(list(desired - current), username, password)
