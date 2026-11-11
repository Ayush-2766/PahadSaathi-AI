from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.api import reports as reports_api
from app.core.database import Base, get_db
from app.main import app
from app.models.citizen_report import CitizenReport


def report_form() -> dict[str, str]:
    return {"category": "landslide", "village_name": "जोशीमठ", "district": "चमोली", "description": "बारिश के बाद पहाड़ी से मलबा सड़क पर आ गया है"}


def test_citizen_report_submission_validation_persistence_and_photo(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'reports.db'}"
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
            response = client.post("/api/v1/reports", data=report_form(), files={"photo": ("road.png", b"png-data", "image/png")})
            assert response.status_code == 201
            payload = response.json()
            assert payload["status"] == "submitted"
            assert payload["report_id"]

            invalid = client.post("/api/v1/reports", data={"category": "flood", "village_name": "", "district": "चमोली", "description": "छोटा"})
            assert invalid.status_code == 422
            assert client.get("/api/v1/health").json() == {"status": "ok", "database": "ok"}

        with Session() as db:
            saved = db.scalar(select(CitizenReport))
            assert saved is not None
            assert saved.village_name == "जोशीमठ"
            assert saved.photo_path is not None
            assert (tmp_path / "photos").joinpath(saved.photo_path.split("/")[-1]).read_bytes() == b"png-data"
    finally:
        app.dependency_overrides.clear()


def test_citizen_report_status_transitions_and_persistence(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'status_tests.db'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            # 1. Create initial report
            create_res = client.post("/api/v1/reports", data=report_form())
            assert create_res.status_code == 201
            report_id = create_res.json()["report_id"]
            assert create_res.json()["status"] == "submitted"

            # 2. Transition sequence: submitted -> verified -> in_progress -> resolved -> dismissed -> submitted
            transitions = ["verified", "in_progress", "resolved", "dismissed", "submitted"]
            for target_status in transitions:
                patch_res = client.patch(
                    f"/api/v1/reports/{report_id}/status",
                    json={"status": target_status},
                )
                assert patch_res.status_code == 200
                payload = patch_res.json()
                assert payload["report_id"] == report_id
                assert payload["status"] == target_status

                # Verify persistence in database
                with Session() as db:
                    row = db.scalar(select(CitizenReport).where(CitizenReport.public_id == report_id))
                    assert row is not None
                    assert row.status == target_status
    finally:
        app.dependency_overrides.clear()


def test_citizen_report_status_update_validation_and_errors(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'status_errors.db'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            create_res = client.post("/api/v1/reports", data=report_form())
            assert create_res.status_code == 201
            report_id = create_res.json()["report_id"]

            # Invalid status string rejected with 422
            invalid_status_res = client.patch(
                f"/api/v1/reports/{report_id}/status",
                json={"status": "invalid_status_name"},
            )
            assert invalid_status_res.status_code == 422

            # Missing status payload rejected with 422
            missing_status_res = client.patch(
                f"/api/v1/reports/{report_id}/status",
                json={},
            )
            assert missing_status_res.status_code == 422

            # Non-existent report returns 404
            not_found_res = client.patch(
                "/api/v1/reports/00000000-0000-0000-0000-000000000000/status",
                json={"status": "verified"},
            )
            assert not_found_res.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_citizen_report_photo_retrieval_and_intelligence_exposure(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'photos_test.db'}"
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
            # 1. Report with photo
            res_photo = client.post(
                "/api/v1/reports",
                data=report_form(),
                files={"photo": ("damage.jpg", b"jpeg-bytes-content", "image/jpeg")},
            )
            assert res_photo.status_code == 201
            photo_report_id = res_photo.json()["report_id"]

            # 2. Report without photo
            res_no_photo = client.post("/api/v1/reports", data=report_form())
            assert res_no_photo.status_code == 201
            no_photo_report_id = res_no_photo.json()["report_id"]

            # 3. Retrieve photo endpoint
            get_photo_res = client.get(f"/api/v1/reports/{photo_report_id}/photo")
            assert get_photo_res.status_code == 200
            assert get_photo_res.content == b"jpeg-bytes-content"

            # 4. Photo 404 for report without photo and non-existent report
            assert client.get(f"/api/v1/reports/{no_photo_report_id}/photo").status_code == 404
            assert client.get("/api/v1/reports/missing-uuid/photo").status_code == 404

            # 5. Check GET /api/v1/intelligence/reports exposes status, submitted_at, and photo_url
            intel_res = client.get("/api/v1/intelligence/reports")
            assert intel_res.status_code == 200
            reports_data = intel_res.json()
            assert len(reports_data) >= 2

            with_photo = next(r for r in reports_data if r["report_id"] == photo_report_id)
            assert with_photo["status"] == "submitted"
            assert with_photo["submitted_at"] is not None
            assert with_photo["photo_url"] == f"/api/v1/reports/{photo_report_id}/photo"

            without_photo = next(r for r in reports_data if r["report_id"] == no_photo_report_id)
            assert without_photo["status"] == "submitted"
            assert without_photo["submitted_at"] is not None
            assert without_photo["photo_url"] is None
    finally:
        app.dependency_overrides.clear()
