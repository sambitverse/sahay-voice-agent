import os
import logging
from pathlib import Path
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .api.v1 import health, test_audio, calls, dashboard, website
from .websocket.client_ws import handle_client_websocket
from .websocket.exotel_ws import handle_exotel_websocket
from .websocket.dashboard_ws import handle_dashboard_websocket

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("trauma_agent")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Real-Time Multimodal Voice Distress & Trauma Assessment Module for NHAA 14566."
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API Routers
app.include_router(health.router, prefix="/api/v1", tags=["System"])
app.include_router(test_audio.router, prefix="/api/v1", tags=["Testing & Diagnostics"])
app.include_router(calls.router, prefix="/api/v1", tags=["Telephony & Sessions"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["Operator Dashboard"])
app.include_router(website.router, prefix="/api/v1", tags=["Website & Citizen Portal"])

# WebSocket Endpoints
@app.websocket("/ws/client/{call_id}")
async def websocket_client_endpoint(websocket: WebSocket, call_id: str):
    """Direct Browser Microphone WebSocket endpoint (used by Dev Test Console)."""
    await handle_client_websocket(websocket, call_id)


@app.websocket("/ws/exotel")
@app.websocket("/ws/exotel/")
@app.websocket("/ws/exotel/{call_id}")
async def websocket_exotel_endpoint(websocket: WebSocket, call_id: str = "live_call"):
    """Exotel Telephony AgentStream WebSocket endpoint."""
    await handle_exotel_websocket(websocket, call_id)


@app.websocket("/ws/dashboard")
async def websocket_dashboard_endpoint(websocket: WebSocket):
    """Live Operator Triage Dashboard WebSocket stream."""
    await handle_dashboard_websocket(websocket)


# Serve Static UI Templates
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/test", response_class=HTMLResponse)
@app.get("/console", response_class=HTMLResponse)
async def get_test_console():
    """Serves the interactive live microphone test console."""
    test_console_file = STATIC_DIR / "test_console.html"
    if test_console_file.exists():
        return HTMLResponse(content=test_console_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h3>Dev test console template not found.</h3>", status_code=404)


@app.get("/dashboard", response_class=HTMLResponse)
async def get_operator_dashboard():
    """Serves the real-time Operator Triage & Live Telemetry Dashboard."""
    dashboard_file = STATIC_DIR / "dashboard.html"
    if dashboard_file.exists():
        return HTMLResponse(content=dashboard_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h3>Operator dashboard template not found.</h3>", status_code=404)


@app.get("/")
async def root():
    """Root redirect to Operator Dashboard."""
    return RedirectResponse(url="/dashboard")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
