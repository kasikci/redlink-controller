import logging
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles

from .config import DEFAULT_CONFIG_PATH, ensure_config, update_config
from .service import HysteresisService

logger = logging.getLogger(__name__)


def create_app(config_path: str) -> FastAPI:
    app = FastAPI(title="Redlink Controller")
    service = HysteresisService(config_path)

    app.state.service = service

    @app.on_event("startup")
    def _startup() -> None:
        ensure_config(config_path)
        service.start()

    @app.on_event("shutdown")
    def _shutdown() -> None:
        service.stop()

    @app.get("/api/health")
    def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/status")
    def status() -> Dict[str, Any]:
        return service.get_snapshot()

    @app.get("/api/config")
    def get_config() -> Dict[str, Any]:
        snapshot = service.get_snapshot()
        return snapshot.get("config") or {}

    @app.post("/api/config")
    async def set_config(request: Request) -> Dict[str, Any]:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="config payload must be JSON object")
        updated = update_config(config_path, payload)
        logger.info(
            "Config updated via API: control_mode=%s "
            "enable_heat=%s enable_cool=%s heat_on_below=%s "
            "heat_off_at=%s cool_on_above=%s cool_off_at=%s hold_minutes=%s "
            "poll_interval_seconds=%s",
            updated.control_mode,
            updated.enable_heat,
            updated.enable_cool,
            updated.heat_on_below,
            updated.heat_off_at,
            updated.cool_on_above,
            updated.cool_off_at,
            updated.hold_minutes,
            updated.poll_interval_seconds,
        )
        return updated.to_public_dict()

    @app.post("/api/command")
    async def command(request: Request) -> Dict[str, Any]:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="command payload must be JSON object")
        action = payload.get("action")
        if action not in ("heat", "cool", "fan", "cancel"):
            raise HTTPException(status_code=400, detail="invalid action")
        if action in ("heat", "cool") and payload.get("setpoint") in (None, ""):
            raise HTTPException(status_code=400, detail="setpoint is required")
        if action == "fan" and payload.get("mode") in (None, ""):
            raise HTTPException(status_code=400, detail="mode is required")
        try:
            service.apply_manual_command(action, payload)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        return {"status": "ok"}

    web_root = Path(__file__).resolve().parent.parent / "web"
    app.mount("/", StaticFiles(directory=web_root, html=True), name="web")

    return app


def run_server(
    config_path: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> None:
    import uvicorn

    _configure_logging()
    path = config_path or DEFAULT_CONFIG_PATH
    config = ensure_config(path)
    bind_host = host or config.bind_host
    bind_port = port or config.bind_port

    app = create_app(path)
    uvicorn.run(app, host=bind_host, port=bind_port)


def _configure_logging() -> None:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    logging.getLogger("redlink_controller").setLevel(logging.INFO)
