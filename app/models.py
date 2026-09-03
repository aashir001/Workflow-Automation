"""
Data model for the Workflow Automation Engine (v2).

A "Workflow" is a small directed graph of Steps. Each step is one of:
  - CONDITION : evaluates a (possibly nested AND/OR) rule group, branches
                to a different next step depending on pass/fail
  - TRANSFORM : derives/enriches fields on the working data
  - ACTION    : calls a named action on a registered connector
"""

import json
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text, Boolean, ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = "sqlite:///./workflow_automation.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class StepType(str, Enum):
    CONDITION = "condition"
    TRANSFORM = "transform"
    ACTION = "action"


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    trigger_type = Column(String, nullable=False, index=True)
    start_step_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    steps = relationship("WorkflowStep", backref="workflow", cascade="all, delete-orphan")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    step_type = Column(String, nullable=False)
    label = Column(String, nullable=True)
    config = Column(Text, nullable=False)

    on_success_step_id = Column(Integer, nullable=True)
    on_failure_step_id = Column(Integer, nullable=True)
    next_step_id = Column(Integer, nullable=True)

    def get_config(self) -> dict:
        return json.loads(self.config)


class EventLog(Base):
    __tablename__ = "event_log"

    id = Column(Integer, primary_key=True, index=True)
    trigger_type = Column(String, nullable=False, index=True)
    payload = Column(Text, nullable=False)
    source = Column(String, default="manual")
    received_at = Column(DateTime, default=datetime.utcnow)


class ExecutionRun(Base):
    __tablename__ = "execution_runs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, nullable=False)
    event_id = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)


class ExecutionStepLog(Base):
    __tablename__ = "execution_step_log"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, nullable=False)
    step_id = Column(Integer, nullable=False)
    step_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    detail = Column(Text, nullable=True)
    working_data_snapshot = Column(Text, nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow)


class CustomerLookup(Base):
    __tablename__ = "customer_lookup"

    customer_id = Column(String, primary_key=True)
    tier = Column(String, nullable=False)
    region = Column(String, nullable=True)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
