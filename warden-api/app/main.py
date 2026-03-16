from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import SessionLocal
from app.models import Camera
from app.routers import health, auth, cameras, streams, pairing, devices, users, commands
from app.services import go2rtc_service, keepalive_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        go2rtc_service.bootstrap(db)
        # Start keepalive for always-on cameras
        try:
            username, password = go2rtc_service.get_credentials(db)
            always_on = [
                c.stream_path for c in db.query(Camera).filter(
                    Camera.always_on == True, Camera.stream_path != None
                ).all()
            ]
            if always_on:
                keepalive_service.start(always_on, username, password)
        except Exception:
            pass
    finally:
        db.close()
    yield
    keepalive_service.stop()


app = FastAPI(title="Warden API", lifespan=lifespan)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(cameras.router)
app.include_router(streams.router)
app.include_router(pairing.router)
app.include_router(devices.router)
app.include_router(commands.router)
app.include_router(users.router)
