from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.citizen_report import CitizenReport
from app.schemas.intelligence import IntelligenceRequest, IntelligenceResponse, ReportIntelligenceResult, VillageImpact
from app.services.intelligence import classify_incident, find_potential_duplicates, recommend_severity, village_impacts

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.post("/analyze", response_model=IntelligenceResponse)
def analyze_report(payload: IntelligenceRequest, db: Session = Depends(get_db)) -> IntelligenceResponse:
    classification = classify_incident(payload.description, payload.category)
    severity = recommend_severity(classification["predicted_category"], payload.description, classification["matched_keywords"])
    reports = list(db.scalars(select(CitizenReport)))
    duplicates = find_potential_duplicates(payload.model_dump(), reports, classification["predicted_category"])
    return IntelligenceResponse(classification=classification, severity=severity, potential_duplicates=duplicates)


@router.get("/reports", response_model=list[ReportIntelligenceResult])
def get_report_analyses(db: Session = Depends(get_db)) -> list[ReportIntelligenceResult]:
    reports = list(db.scalars(select(CitizenReport).order_by(CitizenReport.submitted_at.desc())))
    results = []
    for report in reports:
        payload = IntelligenceRequest(
            report_id=report.public_id, category=report.category, village_name=report.village_name,
            district=report.district, description=report.description, submitted_at=report.submitted_at,
        )
        analysis = analyze_report(payload, db)
        results.append(ReportIntelligenceResult(
            report_id=report.public_id, village_name=report.village_name, district=report.district,
            description=report.description, **analysis.model_dump(),
        ))
    return results


@router.get("/villages", response_model=list[VillageImpact])
def get_village_impacts(db: Session = Depends(get_db)) -> list[VillageImpact]:
    return [VillageImpact(**impact) for impact in village_impacts(list(db.scalars(select(CitizenReport))))]
