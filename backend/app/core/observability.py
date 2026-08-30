import logging
import time

from fastapi import Request, HTTPException
from fastapi.responses import Response, JSONResponse
from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Histogram,
                               generate_latest)
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("verifield.observability")

# Prometheus Metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP Requests", ["method", "endpoint", "http_status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP Request Latency", ["method", "endpoint"]
)

DB_QUERY_COUNT = Counter(
    "db_queries_total", "Total Database Queries", ["domain", "operation"]
)

ACTIVE_SESSIONS = Counter(
    "active_websocket_sessions", "Total Active WebSocket Sessions", ["stream"]
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to intercept all requests and track their latency and status
    codes for Prometheus monitoring.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            from app.domains.observability.api import NEXUS_REQUESTS_TOTAL
            NEXUS_REQUESTS_TOTAL.inc()
        except Exception:
            pass

        method = request.method
        endpoint = request.url.path.split("/")[0:4]
        endpoint_str = "/".join(endpoint)

        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=method, endpoint=endpoint_str, http_status=response.status_code
            ).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint_str).observe(
                duration
            )
            return response
        except HTTPException as exc:
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=method, endpoint=endpoint_str, http_status=exc.status_code
            ).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint_str).observe(
                duration
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
                headers=getattr(exc, "headers", None),
            )
        except Exception as e:
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=method, endpoint=endpoint_str, http_status=500
            ).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint_str).observe(
                duration
            )
            logger.error(f"Unhandled exception in request pipeline: {type(e).__name__}: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Internal server error: {type(e).__name__}: {str(e)}"},
            )


def metrics_endpoint():
    """
    Exposes the /metrics endpoint for Prometheus scrapers.
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def setup_observability(app):
    """
    Wires the observability engine into the FastAPI application.
    """
    app.add_middleware(PrometheusMiddleware)
    app.add_route("/metrics", metrics_endpoint, methods=["GET"])
    logger.info("Observability Engine: Prometheus tracing initialized")
