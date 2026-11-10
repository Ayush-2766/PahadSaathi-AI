from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IntelligenceRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    description: str = Field(min_length=5, max_length=5000)
    category: str | None = Field(default=None, max_length=64)
    village_name: str | None = Field(default=None, max_length=160)
    district: str | None = Field(default=None, max_length=120)
    submitted_at: datetime | None = None
    report_id: str | None = Field(default=None, max_length=64)


class ClassificationResult(BaseModel):
    predicted_category: str
    confidence_score: float
    matched_keywords: list[str]


class SeverityResult(BaseModel):
    recommended_severity: str
    explanation: str
    evidence: list[str]
    human_verification_required: bool = True


class DuplicateMatch(BaseModel):
    report_id: str
    similarity_score: float
    reason: str


class IntelligenceResponse(BaseModel):
    classification: ClassificationResult
    severity: SeverityResult
    potential_duplicates: list[DuplicateMatch]


class ReportIntelligenceResult(IntelligenceResponse):
    report_id: str
    village_name: str
    district: str
    description: str


class VillageImpact(BaseModel):
    village_name: str
    total_incidents: int
    category_distribution: dict[str, int]
    severity_distribution: dict[str, int]
    potentially_duplicated_reports: int
