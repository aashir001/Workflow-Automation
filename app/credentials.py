"""
Encrypted credential storage.

Instead of hardcoding a Slack webhook URL or an email password directly
into a connector file, credentials are stored encrypted in the database
and retrieved by key at runtime. This is what the "credential management
UI" resume bullet refers to - a real settings screen instead of editing
Python source to add a key.

Encryption uses Fernet (symmetric, from the `cryptography` package).
The encryption key itself lives in an environment variable
(CREDENTIAL_ENCRYPTION_KEY) - NOT in the database - since the whole
point of encrypting the credentials is defeated if the key that unlocks
them sits next to them. If this env var is missing, a new key is
generated once and printed so you can save it - the app will still run
locally without it (falling back to plain env vars for connectors),
but restarting without saving the printed key means previously
encrypted credentials become unreadable.
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from cryptography.fernet import Fernet, InvalidToken

DATABASE_URL = "sqlite:///./workflow_automation.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Credential(Base):
    __tablename__ = "credentials"
    key = Column(String, primary_key=True)  # e.g. "SLACK_WEBHOOK_URL"
    encrypted_value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_credentials_table():
    Base.metadata.create_all(bind=engine)


_ephemeral_key_cache = None  # module-level cache, see _get_fernet() below


def _get_fernet() -> Fernet:
    """
    Returns a Fernet instance for encrypting/decrypting credentials.

    If CREDENTIAL_ENCRYPTION_KEY is set, always uses that (consistent
    across restarts). If not set, generates ONE random key and caches
    it at module level for the lifetime of this process - critical,
    because regenerating a new random key on every call would make
    every decryption fail immediately after encryption (each call
    would use a different key). The cache means credentials saved and
    read within the same running session work correctly; only a
    process restart without a real env var set will invalidate them.
    """
    global _ephemeral_key_cache

    key = os.environ.get("CREDENTIAL_ENCRYPTION_KEY")
    if not key:
        if _ephemeral_key_cache is None:
            _ephemeral_key_cache = Fernet.generate_key().decode()
            print(
                "\n⚠️  No CREDENTIAL_ENCRYPTION_KEY set. Generated a temporary "
                "one for this session:\n"
                f"    {_ephemeral_key_cache}\n"
                "Set this as an environment variable (or in run_windows.bat / "
                "run_mac_linux.sh) to keep saved credentials readable across "
                "restarts. Without it, credentials saved now will still work "
                "for the rest of THIS run, but become unreadable the next "
                "time the app starts.\n"
            )
        key = _ephemeral_key_cache
    return Fernet(key.encode() if isinstance(key, str) else key)


def set_credential(key: str, value: str):
    """Encrypts and saves (or updates) a credential."""
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
    """
    Retrieves a credential by key. Checks the encrypted database first;
    falls back to a plain environment variable of the same name if not
    found in the database (useful for local dev / the run scripts).
    Returns None if neither source has it.
    """
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
            print(
                f"⚠️  Could not decrypt stored credential '{key}' - the "
                f"CREDENTIAL_ENCRYPTION_KEY may have changed since it was "
                f"saved. Falling back to environment variable if set."
            )

    return os.environ.get(key)


def list_credential_keys() -> list:
    """Returns which credential keys are stored (never the values) -
    used by the UI to show what's configured without exposing secrets."""
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
