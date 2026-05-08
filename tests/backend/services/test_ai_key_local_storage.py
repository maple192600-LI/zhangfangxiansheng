import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from core.security import decrypt_key, encrypt_key
from database import Base
from db.tables import AIConfig
from services import ai_config_service


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_key_helpers_encrypt_local_storage_value():
    encrypted = encrypt_key("sk-local-test")

    assert encrypted != "sk-local-test"
    assert decrypt_key(encrypted) == "sk-local-test"
    assert decrypt_key("sk-local-test") == "sk-local-test"


def test_ai_config_stores_key_in_local_plain_field():
    db = _session()

    created = ai_config_service.create_ai_config(db, {
        "provider": "zhipu",
        "display_name": "智谱",
        "api_key": "sk-local-test",
        "model_name": "glm",
    })

    row = db.query(AIConfig).filter(AIConfig.id == created["id"]).one()
    assert row.api_key_local != "sk-local-test"
    assert decrypt_key(row.api_key_local) == "sk-local-test"
    assert not hasattr(row, "api_key_encrypted")
