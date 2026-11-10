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


class CitizenReportCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    category: IncidentCategory
    village_name: str = Field(min_length=2, max_length=160)
    district: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=5, max_length=5000)


class CitizenReportResponse(BaseModel):
    report_id: str
    status: str
