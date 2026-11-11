from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api import reports as reports_api
from app.core.database import Base, get_db
from app.main import app
from app.models.citizen_report import CitizenReport
from app.api.intelligence import analyze_report, get_incident_briefs, get_village_impacts
from app.schemas.intelligence import IntelligenceRequest
from app.services.intelligence import (
    CATEGORY_PRIORITY,
    build_incident_briefs,
    classify_incident,
    find_potential_duplicates,
    normalise_place_name,
    recommend_severity,
    village_impacts,
)


def test_place_normalisation_groups_variants_without_mutating_source_reports() -> None:
    reports = [
        CitizenReport(public_id="a", category="other", village_name="  seraghat ", district=" almora ", description="स्थिति सामान्य है", submitted_at=datetime.utcnow()),
        CitizenReport(public_id="b", category="other", village_name="SERAGHAT", district="ALMORA", description="स्थिति सामान्य है", submitted_at=datetime.utcnow()),
    ]
    impacts = village_impacts(reports)
    assert normalise_place_name(reports[0].village_name) == "Seraghat"
    assert reports[0].village_name == "  seraghat "
    assert len(impacts) == 1
    assert impacts[0]["village_name"] == "Seraghat"


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


def test_incident_fusion_builds_an_explainable_response_brief() -> None:
    submitted_at = datetime.utcnow()
    reports = [
        CitizenReport(public_id="fusion-1", category="landslide", village_name="Joshimath", district="Chamoli", description="Heavy rain caused a landslide and debris fell near homes", submitted_at=submitted_at),
        CitizenReport(public_id="fusion-2", category="landslide", village_name="Joshimath", district="Chamoli", description="Landslide debris fell near homes after heavy rain", submitted_at=submitted_at + timedelta(hours=2)),
    ]
    briefs = build_incident_briefs(reports)
    assert len(briefs) == 1
    brief = briefs[0]
    assert {report["report_id"] for report in brief["contributing_reports"]} == {"fusion-1", "fusion-2"}
    assert brief["affected_villages"] == ["Joshimath"]
    assert brief["highest_recommended_severity"] == "HIGH"
    assert brief["detected_facts"]
    assert any("same reported village" in item for item in brief["inferred_relationships"])
    assert "not a confirmed incident" in brief["situation_summary"]
    assert brief["recommended_verification_steps"]
    assert brief["prioritized_authority_actions"][0]["priority"] == 1
    assert [action["priority"] for action in brief["prioritized_authority_actions"]] == list(range(1, len(brief["prioritized_authority_actions"]) + 1))


def test_incident_fusion_does_not_group_unrelated_reports() -> None:
    submitted_at = datetime.utcnow()
    reports = [
        CitizenReport(public_id="landslide", category="landslide", village_name="Joshimath", district="Chamoli", description="Landslide debris on the road", submitted_at=submitted_at),
        CitizenReport(public_id="water", category="water_shortage", village_name="Joshimath", district="Chamoli", description="Drinking water supply has stopped", submitted_at=submitted_at + timedelta(hours=1)),
        CitizenReport(public_id="old", category="landslide", village_name="Joshimath", district="Chamoli", description="Landslide debris on the road", submitted_at=submitted_at + timedelta(days=3)),
    ]
    assert build_incident_briefs(reports) == []


def test_incident_fusion_endpoint_returns_briefs(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'fusion.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        now = datetime.utcnow()
        db.add_all([
            CitizenReport(public_id="api-1", category="road_blockage", village_name="Seraghat", district="Almora", description="road block due to landslide debris", submitted_at=now),
            CitizenReport(public_id="api-2", category="road_blockage", village_name="Seraghat", district="Almora", description="road blocked because landslide debris fell", submitted_at=now + timedelta(hours=1)),
        ])
        db.commit()
    with Session() as db:
        briefs = get_incident_briefs(db)
        assert len(briefs) == 1
        assert briefs[0].incident_id.startswith("potential-")


def test_cloudburst_never_receives_low_severity() -> None:
    # Default severity for cloudburst must be CRITICAL
    res1 = recommend_severity("cloudburst", "गांव में बादल फटा है", ["बादल फटा"])
    assert res1["recommended_severity"] == "CRITICAL"

    # Even with minimal or no keywords, cloudburst must never be LOW
    res2 = recommend_severity("cloudburst", "सामान्य स्थिति है", [])
    assert res2["recommended_severity"] == "CRITICAL"
    assert res2["recommended_severity"] != "LOW"

    # Cloudburst with severe weather descriptions must remain CRITICAL
    res3 = recommend_severity("cloudburst", "बादल फटा, भारी तबाही", ["बादल फटा"])
    assert res3["recommended_severity"] == "CRITICAL"
    assert res3["recommended_severity"] != "LOW"


def test_building_damage_never_receives_low_severity() -> None:
    # Default severity for building damage is HIGH
    res1 = recommend_severity("building_damage", "मकान टूट गया है", ["मकान टूट गया"])
    assert res1["recommended_severity"] == "HIGH"
    assert res1["recommended_severity"] != "LOW"

    # Minimal evidence building damage must still be HIGH, never LOW
    res2 = recommend_severity("building_damage", "दीवार में दरार आ गई है", [])
    assert res2["recommended_severity"] == "HIGH"
    assert res2["recommended_severity"] != "LOW"

    # CRITICAL when explicit life-threatening evidence exists
    res3 = recommend_severity("building_damage", "मकान ढह गया, लोग फंसे हैं", ["घर ढह गया", "लोग फंसे"])
    assert res3["recommended_severity"] == "CRITICAL"

    res4 = recommend_severity("building_damage", "house collapsed, life threatening situation", ["house collapsed", "life threatening"])
    assert res4["recommended_severity"] == "CRITICAL"

    res5 = recommend_severity("building_damage", "मकान टूट गया, कई घायल हैं", ["मकान टूट गया", "कई घायल"])
    assert res5["recommended_severity"] == "CRITICAL"


def test_medical_emergency_receives_appropriate_severity() -> None:
    # HIGH by default (without critical risk evidence)
    res1 = recommend_severity("medical_emergency", "मरीज को तुरंत अस्पताल ले जाना है", ["मरीज", "अस्पताल"])
    assert res1["recommended_severity"] == "HIGH"
    assert res1["recommended_severity"] != "LOW"

    res2 = recommend_severity("medical_emergency", "एक व्यक्ति घायल है", ["घायल"])
    assert res2["recommended_severity"] == "HIGH"

    # CRITICAL when critical risk evidence exists
    res3 = recommend_severity("medical_emergency", "मरीज की हालत गंभीर है, जान का खतरा है", ["मरीज", "जान का खतरा"])
    assert res3["recommended_severity"] == "CRITICAL"

    res4 = recommend_severity("medical_emergency", "हादसे में कई घायल हैं, बचाओ", ["घायल", "कई घायल", "बचाओ"])
    assert res4["recommended_severity"] == "CRITICAL"

    res5 = recommend_severity("medical_emergency", "people trapped and injured after accident", ["injured", "people trapped"])
    assert res5["recommended_severity"] == "CRITICAL"


def test_classification_ties_resolved_explicitly_without_overriding_stronger_evidence() -> None:
    # Life-safety ties: medical_emergency beats landslide when evidence count is equal (1 vs 1)
    tie1 = classify_incident("सड़क पर भूस्खलन हुआ है और एक व्यक्ति घायल है")
    assert tie1["predicted_category"] == "medical_emergency"
    assert len(tie1["matched_keywords"]) == 1

    # Life-safety ties: cloudburst beats heavy_rainfall when evidence count is equal (1 vs 1)
    tie2 = classify_incident("गांव में बादल फटा है और लगातार बारिश हो रही है")
    assert tie2["predicted_category"] == "cloudburst"
    assert len(tie2["matched_keywords"]) == 1

    # Life-safety ties: building_damage beats heavy_rainfall when evidence count is equal (1 vs 1)
    tie3 = classify_incident("तेज बारिश में मकान टूट गया है")
    assert tie3["predicted_category"] == "building_damage"
    assert len(tie3["matched_keywords"]) == 1

    # Stronger evidence is NOT overridden by lower priority:
    # heavy_rainfall (2 keywords) beats cloudburst (1 keyword)
    stronger_evidence = classify_incident("तेज बारिश और लगातार बारिश के कारण बादल फटा जैसा माहौल है")
    assert stronger_evidence["predicted_category"] == "heavy_rainfall"
    assert len(stronger_evidence["matched_keywords"]) == 2

    # Verify priority mapping reflects life-safety hierarchy
    assert CATEGORY_PRIORITY["medical_emergency"] > CATEGORY_PRIORITY["landslide"]
    assert CATEGORY_PRIORITY["cloudburst"] > CATEGORY_PRIORITY["heavy_rainfall"]
    assert CATEGORY_PRIORITY["building_damage"] > CATEGORY_PRIORITY["heavy_rainfall"]


def test_both_new_categories_can_be_submitted_through_api(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'new_categories.db'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(reports_api, "PHOTO_DIRECTORY", tmp_path / "photos")

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            # 1. Submit cloudburst
            res_cloudburst = client.post(
                "/api/v1/reports",
                data={
                    "category": "cloudburst",
                    "village_name": "धाराचूला",
                    "district": "पिथौरागढ़",
                    "description": "पहाड़ी पर बादल फटा है और मलबा नीचे आ रहा है",
                },
            )
            assert res_cloudburst.status_code == 201
            payload_cloudburst = res_cloudburst.json()
            assert payload_cloudburst["status"] == "submitted"
            assert payload_cloudburst["report_id"]

            # 2. Submit building_damage
            res_building = client.post(
                "/api/v1/reports",
                data={
                    "category": "building_damage",
                    "village_name": "जोशीमठ",
                    "district": "चमोली",
                    "description": "भूधंसाव के कारण मकान टूट गया है और दीवारें ढह गई हैं",
                },
            )
            assert res_building.status_code == 201
            payload_building = res_building.json()
            assert payload_building["status"] == "submitted"
            assert payload_building["report_id"]

        with Session() as db:
            cb_report = db.scalar(select(CitizenReport).where(CitizenReport.category == "cloudburst"))
            assert cb_report is not None
            assert cb_report.village_name == "धाराचूला"

            bd_report = db.scalar(select(CitizenReport).where(CitizenReport.category == "building_damage"))
            assert bd_report is not None
            assert bd_report.village_name == "जोशीमठ"
    finally:
        app.dependency_overrides.clear()
