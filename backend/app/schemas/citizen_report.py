from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class IncidentCategory(str, Enum):
    landslide = "landslide"
    road_blockage = "road_blockage"
    flood = "flood"
    cloudburst = "cloudburst"
    building_damage = "building_damage"
    heavy_rainfall = "heavy_rainfall"
    water_shortage = "water_shortage"
    electricity_disruption = "electricity_disruption"
    medical_emergency = "medical_emergency"
    other = "other"


class ReportStatus(str, Enum):
    submitted = "submitted"
    verified = "verified"
    in_progress = "in_progress"
    resolved = "resolved"
    dismissed = "dismissed"


class CitizenReportCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    category: IncidentCategory
    village_name: str = Field(min_length=2, max_length=160)
    district: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=5, max_length=5000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class CitizenReportStatusUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: ReportStatus


class CitizenReportResponse(BaseModel):
    report_id: str
    status: str
