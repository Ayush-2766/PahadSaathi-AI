from app.api.health import health_check
from app.core.database import get_db


def test_health_check_returns_ok() -> None:
    db = next(get_db())
    try:
        assert health_check(db) == {"status": "ok", "database": "ok"}
    finally:
        db.close()

