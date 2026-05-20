"""
Point d'entrée FastAPI — déploiement hybride Vercel + VM (Tailscale/HAProxy).
"""
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import engine, Base, check_database_connection
from app.api.v1 import api_router
from app.api.v1.websocket import websocket_endpoint
from app.services.storage_service import storage_health

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

logger.info("SUPFile démarrage — mode=%s stockage=%s", settings.DEPLOYMENT_MODE, settings.STORAGE_BACKEND)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="SUPFile — stockage cloud hybride (Vercel + infra privée)",
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return JSONResponse(
        content={
            "status": "healthy",
            "service": settings.APP_NAME,
            "version": "1.0.0",
            "deployment": settings.DEPLOYMENT_MODE,
        }
    )


def _parse_network_health(request: Request) -> dict:
    headers = request.headers
    x_real_ip = headers.get("x-real-ip")
    x_forwarded_for = headers.get("x-forwarded-for")
    x_forwarded_proto = headers.get("x-forwarded-proto")
    host = headers.get("host", "").lower()

    return {
        "tailscale": ".ts.net" in host or ".ts.net" in settings.BACKEND_PUBLIC_URL.lower(),
        "haproxy": bool(x_real_ip or x_forwarded_for or x_forwarded_proto),
        "proxy_headers": {
            "x_real_ip": bool(x_real_ip),
            "x_forwarded_for": bool(x_forwarded_for),
            "x_forwarded_proto": bool(x_forwarded_proto),
        },
    }


@app.get("/health")
async def health_check(request: Request):
    db_status = check_database_connection()
    storage_status = storage_health()
    network_status = _parse_network_health(request)
    overall = (
        db_status.get("status") == "connected"
        and storage_status.get("status") == "ok"
    )
    return JSONResponse(
        content={
            "status": "healthy" if overall else "degraded",
            "service": settings.APP_NAME,
            "datacenter": settings.PRIMARY_DC.lower(),
            "deployment": settings.DEPLOYMENT_MODE,
            "database": db_status,
            "storage": storage_status,
            "security": {
                "wazuh": settings.WAZUH,
                "suricata": settings.SURICATA,
                "fail2ban": settings.FAIL2BAN,
            },
            "network": {
                "tailscale": network_status["tailscale"],
                "haproxy": network_status["haproxy"],
                "headers": network_status["proxy_headers"],
            },
            "datacenters": {
                "primary": settings.PRIMARY_DC,
                "failover": settings.FAILOVER_DC,
                "active_active": settings.ACTIVE_ACTIVE,
            },
        }
    )


app.include_router(api_router, prefix="/api/v1")
app.websocket("/api/v1/ws")(websocket_endpoint)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
