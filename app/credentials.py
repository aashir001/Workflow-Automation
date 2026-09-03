"""Encrypted credential storage. See app/main.py for usage via API."""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from cryptography.fernet import Fernet, InvalidToken

DATABASE_URL = "sqlite:///./workflow_automation.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Credential(Base):
    __tablename__ = "credentials"
    key = Column(String, primary_key=True)
    encrypted_value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_credentials_table():
    Base.metadata.create_all(bind=engine)


_ephemeral_key_cache = None


def _get_fernet() -> Fernet:
    global _ephemeral_key_cache
    key = os.environ.get("CREDENTIAL_ENCRYPTION_KEY")
    if not key:
        if _ephemeral_key_cache is None:
            _ephemeral_key_cache = Fernet.generate_key().decode()
            print(
                "\n⚠️  No CREDENTIAL_ENCRYPTION_KEY set. Generated a temporary "
                f"one for this session:\n    {_ephemeral_key_cache}\n"
                "Set this in .env to keep saved credentials readable across restarts.\n"
            )
        key = _ephemeral_key_cache
    return Fernet(key.encode() if isinstance(key, str) else key)


def set_credential(key: str, value: str):
    init_credentials_table()
    fernet = _get_fernet()
    encrypted = fernet.encrypt(value.encode()).decode()
    db = SessionLocal()
    try:
        existing = db.query(Credential).filter(Credential.key == key).first()
        if existing:
            existing.encrypted_value = encrypted
        else:
            db.add(Credential(key=key, encrypted_value=encrypted))
        db.commit()
    finally:
        db.close()


def get_credential(key: str) -> str | None:
    init_credentials_table()
    db = SessionLocal()
    try:
        record = db.query(Credential).filter(Credential.key == key).first()
    finally:
        db.close()
    if record:
        try:
            fernet = _get_fernet()
            return fernet.decrypt(record.encrypted_value.encode()).decode()
        except InvalidToken:
            print(f"⚠️  Could not decrypt credential '{key}' - key may have changed.")
    return os.environ.get(key)


def list_credential_keys() -> list:
    init_credentials_table()
    db = SessionLocal()
    try:
        return [c.key for c in db.query(Credential).all()]
    finally:
        db.close()


def delete_credential(key: str):
    init_credentials_table()
    db = SessionLocal()
    try:
        record = db.query(Credential).filter(Credential.key == key).first()
        if record:
            db.delete(record)
            db.commit()
    finally:
        db.close()
