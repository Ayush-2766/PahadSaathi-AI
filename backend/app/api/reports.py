from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.citizen_report import CitizenReport
from app.schemas.citizen_report import CitizenReportCreate, CitizenReportResponse, CitizenReportStatusUpdate

router = APIRouter(tags=["citizen reports"])

MAX_PHOTO_SIZE = 5 * 1024 * 1024
ALLOWED_PHOTO_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
PHOTO_DIRECTORY = Path("storage/photos")


async def save_photo(photo: UploadFile | None) -> str | None:
    if photo is None or not photo.filename:
        return None
    suffix = ALLOWED_PHOTO_TYPES.get(photo.content_type or "")
    if suffix is None:
        raise HTTPException(status_code=422, detail="Photo must be a JPEG, PNG, or WebP image")
    contents = await photo.read(MAX_PHOTO_SIZE + 1)
    if len(contents) > MAX_PHOTO_SIZE:
        raise HTTPException(status_code=422, detail="Photo must be 5 MB or smaller")
    PHOTO_DIRECTORY.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4()}{suffix}"
    path = PHOTO_DIRECTORY / filename
    path.write_bytes(contents)
    return str(path)


@router.post("/reports", response_model=CitizenReportResponse, status_code=status.HTTP_201_CREATED)
async def create_citizen_report(
    category: str = Form(...),
    village_name: str = Form(...),
    district: str = Form(...),
    description: str = Form(...),
    photo: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
) -> CitizenReportResponse:
    try:
        payload = CitizenReportCreate.model_validate({
            "category": category,
            "village_name": village_name,
            "district": district,
            "description": description,
        })
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail={"message": "Request validation failed", "errors": exc.errors()}) from exc

    photo_path = await save_photo(photo)
    try:
        report = CitizenReport(
            category=payload.category.value,
            village_name=payload.village_name,
            district=payload.district,
            description=payload.description,
            photo_path=photo_path,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
    except Exception:
        db.rollback()
        if photo_path:
            Path(photo_path).unlink(missing_ok=True)
        raise
    return CitizenReportResponse(report_id=report.public_id, status=report.status)


@router.patch("/reports/{report_id}/status", response_model=CitizenReportResponse)
def update_citizen_report_status(
    report_id: str,
    payload: CitizenReportStatusUpdate,
    db: Session = Depends(get_db),
) -> CitizenReportResponse:
    report = db.scalar(select(CitizenReport).where(CitizenReport.public_id == report_id))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = payload.status.value
    db.commit()
    db.refresh(report)
    return CitizenReportResponse(report_id=report.public_id, status=report.status)


@router.get("/reports/{report_id}/photo")
def get_citizen_report_photo(
    report_id: str,
    db: Session = Depends(get_db),
) -> FileResponse:
    report = db.scalar(select(CitizenReport).where(CitizenReport.public_id == report_id))
    if not report or not report.photo_path:
        raise HTTPException(status_code=404, detail="Photo not found")
    path = Path(report.photo_path)
    if not path.is_file():
        # Check relative to backend directory or photo directory
        candidates = [
            Path("backend") / path,
            PHOTO_DIRECTORY / path.name,
            Path("backend") / PHOTO_DIRECTORY / path.name,
        ]
        found = next((candidate for candidate in candidates if candidate.is_file()), None)
        if found:
            path = found
        else:
            raise HTTPException(status_code=404, detail="Photo file not found on disk")
    return FileResponse(path)
