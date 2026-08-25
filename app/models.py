"""
Data model for the Workflow Automation Engine (v2).

The key structural change from v1: a "Workflow" is no longer a single
flat rule (trigger -> one condition -> one action). It is a small
directed graph of Steps. Each step is one of:

  - CONDITION : evaluates a (possibly nested AND/OR) rule group against
                the current working data, and branches to a different
                next step depending on whether it passed or failed.
  - TRANSFORM : derives/renames/enriches fields on the working data
                (including optional enrichment lookups against a
                connector, e.g. "look up this customer's tier").
  - ACTION    : calls a named action on a registered connector
                (log, email, Slack, sheet, outbound HTTP webhook, ...).

Steps reference each other by id (on_success_step_id / on_failure_step_id
for conditions, next_step_id for transform/action), so a workflow is
literally a small state machine walked by the engine at runtime -
this is what makes it "branching" rather than a single if/then.
"""

import json
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Boolean,
    ForeignKey,
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


# ---------------------------------------------------------------------------
# Core workflow graph
# ---------------------------------------------------------------------------

class Workflow(Base):
    """
    A named automation. Owns a graph of WorkflowStep rows connected by
    id references. `start_step_id` is where execution begins whenever
    a matching event arrives.
    """
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    trigger_type = Column(String, nullable=False, index=True)
    start_step_id = Column(Integer, nullable=True)  # set after steps are created

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    steps = relationship(
        "WorkflowStep", backref="workflow", cascade="all, delete-orphan"
    )


class WorkflowStep(Base):
    """
    One node in a workflow's graph.

    `config` is a JSON blob whose shape depends on step_type:

      CONDITION:
        {
          "logic": "AND" | "OR",
          "rules": [
             {"field": "amount", "operator": ">", "value": "1000"},
             {"field": "region", "operator": "==", "value": "Delhi"},
             {  # nested group, arbitrary depth
                "logic": "OR",
                "rules": [ ... ]
             }
          ]
        }

      TRANSFORM:
        {
          "set_fields": [
             {"target": "priority", "template": "HIGH" }  # literal / templated string
          ],
          "lookup": {                      # optional enrichment step
             "connector": "sql_lookup",
             "action": "get_customer_tier",
             "input_field": "customer_id",
             "output_field": "customer_tier"
          }
        }

      ACTION:
        {
          "connector": "email",            # which registered connector
          "action": "send_email",          # which action on that connector
          "params": {"to": "{name}@x.com", "subject": "..."},
          "retry": {"max_attempts": 3, "backoff_seconds": 1}
        }
    """
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)

    step_type = Column(String, nullable=False)  # StepType value
    label = Column(String, nullable=True)  # human-readable name for UI/logs
    config = Column(Text, nullable=False)  # JSON string, shape per step_type

    # CONDITION steps use both branches; TRANSFORM/ACTION use next_step_id only.
    on_success_step_id = Column(Integer, nullable=True)
    on_failure_step_id = Column(Integer, nullable=True)
    next_step_id = Column(Integer, nullable=True)

    def get_config(self) -> dict:
        return json.loads(self.config)


# ---------------------------------------------------------------------------
# Event ingestion + full execution audit trail
# ---------------------------------------------------------------------------

class EventLog(Base):
    """Every inbound event, whether simulated or a real webhook call."""
    __tablename__ = "event_log"

    id = Column(Integer, primary_key=True, index=True)
    trigger_type = Column(String, nullable=False, index=True)
    payload = Column(Text, nullable=False)
    source = Column(String, default="manual")  # "manual" | "webhook"
    received_at = Column(DateTime, default=datetime.utcnow)


class ExecutionRun(Base):
    """One full traversal of a workflow's graph for one event."""
    __tablename__ = "execution_runs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, nullable=False)
    event_id = Column(Integer, nullable=False)
    status = Column(String, nullable=False)  # "completed" | "error"
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)


class ExecutionStepLog(Base):
    """
    One node visited during a run. This is the real audit trail: for
    any run you can reconstruct exactly which path through the graph
    was taken and why (which branch a condition took, what a transform
    produced, whether an action succeeded/retried/failed).
    """
    __tablename__ = "execution_step_log"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, nullable=False)
    step_id = Column(Integer, nullable=False)
    step_type = Column(String, nullable=False)
    status = Column(String, nullable=False)  # "passed"/"failed" (condition),
    # "applied" (transform), "success"/"retried"/"error" (action)
    detail = Column(Text, nullable=True)  # human-readable outcome
    working_data_snapshot = Column(Text, nullable=True)  # JSON, for debugging
    executed_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Connector-side persistence (for connectors that need local state,
# e.g. the SQL lookup connector's reference table)
# ---------------------------------------------------------------------------

class CustomerLookup(Base):
    """
    A small reference table the sql_lookup connector queries against,
    to demonstrate real enrichment (not just a mocked return value).
    """
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
