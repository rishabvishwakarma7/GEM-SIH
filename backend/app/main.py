"""
FastAPI application entrypoint.
Run with: uvicorn app.main:app --reload
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.logging_config import configure_logging, logger

from app.api.routes import (
    auth,
    users,
    tenders,
    bidders,
    documents,
    verification,
    compliance,
    reports,
    audit,
    dashboard,
    notifications,
)
# Upgrade routes
from app.api.routes import document_risk, risk, alerts, reviews

configure_logging()

app = FastAPI(
    title="GeM Bid Compliance Verification Platform",
    description="AI-powered bid compliance verification for GeM procurement (CPCL / MoPNG - SIH 2026, PS ID 26100)",
    version="0.1.0",
)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Global error handlers ----
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.warning(f"HTTPException: {exc.status_code} {exc.detail} | path={request.url.path}")
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"ValidationError: {exc.errors()} | path={request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc} | path={request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ---- Routers ----
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tenders.router)
app.include_router(bidders.router)
# document_risk MUST come before documents — static /duplicates route beats /{id}
app.include_router(document_risk.router)
app.include_router(documents.router)
app.include_router(verification.router)
app.include_router(compliance.router)
app.include_router(reports.router)
app.include_router(audit.router)
app.include_router(dashboard.router)
app.include_router(notifications.router)
# Upgrade routers
app.include_router(risk.router)
app.include_router(alerts.router)
app.include_router(reviews.router)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "gem-compliance-backend", "environment": settings.ENVIRONMENT}


@app.get("/api/health", tags=["health"])
def health_check():
    return {"status": "healthy"}
