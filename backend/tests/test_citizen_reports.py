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
