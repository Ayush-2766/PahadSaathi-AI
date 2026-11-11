from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.citizen_report import CitizenReport
from app.api.intelligence import analyze_report, get_village_impacts
from app.schemas.intelligence import IntelligenceRequest
from app.services.intelligence import classify_incident, find_potential_duplicates, recommend_severity


def test_classification_and_severity_are_explainable() -> None:
    classification = classify_incident("भारी बारिश के बाद भूस्खलन हुआ, लोग फंसे हैं")
    assert classification["predicted_category"] == "landslide"
    assert "भूस्खलन" in classification["matched_keywords"]
    severity = recommend_severity(classification["predicted_category"], "भारी बारिश के बाद भूस्खलन हुआ, लोग फंसे हैं", classification["matched_keywords"])
    assert severity["recommended_severity"] == "CRITICAL"
    assert severity["human_verification_required"] is True
    assert "सिफारिश" in severity["explanation"]


def test_duplicate_detection_requires_meaningful_signal() -> None:
    report = CitizenReport(public_id="existing", category="landslide", village_name="जोशीमठ", district="चमोली", description="बारिश के बाद सड़क पर मलबा और भूस्खलन है", submitted_at=datetime.utcnow())
    matches = find_potential_duplicates({"description": "बारिश के बाद सड़क पर मलबा और भूस्खलन हुआ है", "village_name": "जोशीमठ", "submitted_at": datetime.utcnow()}, [report], "landslide")
    assert matches[0]["report_id"] == "existing"
    assert matches[0]["similarity_score"] >= 0.78
    no_matches = find_potential_duplicates({"description": "गांव में पीने के पानी की कमी है", "village_name": "जोशीमठ", "submitted_at": datetime.utcnow() + timedelta(days=3)}, [report], "water_shortage")
    assert no_matches == []


def test_duplicate_detection_normalises_seraghat_road_blockage_variants() -> None:
    submitted_at = datetime.utcnow()
    road_blockage = CitizenReport(
        public_id="seraghat-1", category="road_blockage", village_name="Seraghat", district="Almora",
        description="rod block ho gyi hai yha", submitted_at=submitted_at,
    )
    matches = find_potential_duplicates({
        "report_id": "seraghat-2", "description": "Road block ho gaya hai, malba sadak par gira hai aur vehicles nahi ja pa rahe hain.",
        "village_name": "Seraghat", "submitted_at": submitted_at + timedelta(hours=1),
    }, [road_blockage], "road_blockage")
    assert matches[0]["report_id"] == "seraghat-1"
    assert "shared incident keywords: road blockage" in matches[0]["reason"]


def test_duplicate_detection_keeps_self_village_and_relevance_guards() -> None:
    submitted_at = datetime.utcnow()
    road_blockage = CitizenReport(public_id="same", category="road_blockage", village_name="Seraghat", district="Almora", description="road block ho gaya hai", submitted_at=submitted_at)
    unrelated = CitizenReport(public_id="water", category="water_shortage", village_name="Seraghat", district="Almora", description="पेयजल की गंभीर कमी है", submitted_at=submitted_at)
    other_village = CitizenReport(public_id="other-village", category="road_blockage", village_name="Dhaulchina", district="Almora", description="road blockage hai", submitted_at=submitted_at)
    incoming = {"report_id": "same", "description": "road block ho gaya hai", "village_name": "Seraghat", "submitted_at": submitted_at}
    assert find_potential_duplicates(incoming, [road_blockage], "road_blockage") == []
    assert find_potential_duplicates(incoming, [unrelated], "road_blockage") == []
    assert find_potential_duplicates(incoming, [other_village], "road_blockage") == []


def test_intelligence_api_response_and_village_aggregation(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'intelligence.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        db.add_all([
            CitizenReport(public_id="r1", category="landslide", village_name="जोशीमठ", district="चमोली", description="बारिश के बाद भूस्खलन से सड़क बंद है", submitted_at=datetime.utcnow()),
            CitizenReport(public_id="r2", category="landslide", village_name="जोशीमठ", district="चमोली", description="बारिश के बाद भूस्खलन से सड़क बंद है", submitted_at=datetime.utcnow()),
        ])
        db.commit()

    with Session() as db:
        analysis = analyze_report(IntelligenceRequest(category="other", village_name="जोशीमठ", district="चमोली", description="बारिश के बाद भूस्खलन से सड़क बंद है"), db)
        assert analysis.classification.predicted_category == "landslide"
        assert analysis.severity.human_verification_required is True
        assert {item.report_id for item in analysis.potential_duplicates} == {"r1", "r2"}
        villages = get_village_impacts(db)
        impact = villages[0]
        assert impact.total_incidents == 2
        assert impact.category_distribution["landslide"] == 2
        assert impact.potentially_duplicated_reports == 2
