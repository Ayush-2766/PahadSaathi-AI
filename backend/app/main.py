from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.api.health import router as health_router
from app.api.reports import router as reports_router
from app.api.intelligence import router as intelligence_router
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://pahadsaathi-ai-1.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(intelligence_router, prefix="/api/v1")

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": "Request validation failed", "errors": exc.errors()})


@app.exception_handler(Exception)
async def unexpected_exception_handler(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "An unexpected server error occurred"})

