"""
FastAPI backend (v2) for the Low-Code Workflow Automation Engine.

Run with:
    uvicorn app.main:app --reload

Docs at http://localhost:8000/docs
"""

from dotenv import load_dotenv
load_dotenv()  # loads GROQ_API_KEY, CREDENTIAL_ENCRYPTION_KEY, etc. from a
                # local .env file (not committed to git - see .env.example)

import json
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models import (
    init_db,
    get_db,
    Workflow,
    WorkflowStep,
    EventLog,
    ExecutionRun,
    ExecutionStepLog,
    CustomerLookup,
)
from app.engine import process_event
from app.connectors import list_connectors_and_actions
from app.nl_builder import parse_instruction, graph_spec_to_workflow_steps
from app.credentials import set_credential, get_credential, list_credential_keys, delete_credential

app = FastAPI(title="Low-Code Workflow Automation Engine v2")


@app.on_event("startup")
def on_startup():
    init_db()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class StepIn(BaseModel):
    step_type: str  # "condition" | "transform" | "action"
    label: Optional[str] = None
    config: dict
    on_success_index: Optional[int] = None  # index into the steps list (condition only)
    on_failure_index: Optional[int] = None
    next_index: Optional[int] = None  # transform/action only


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str
    steps: List[StepIn]  # index 0 is always the start step
    is_active: bool = True


class EventIn(BaseModel):
    trigger_type: str
    data: dict


class NLInstructionIn(BaseModel):
    instruction: str
    workflow_name: Optional[str] = None


class LookupSeedIn(BaseModel):
    customer_id: str
    tier: str
    region: Optional[str] = None


class CredentialIn(BaseModel):
    key: str
    value: str


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

@app.get("/meta/connectors")
def get_connectors():
    """Powers the UI's connector/action dropdowns - adding a connector
    to the registry automatically shows up here, no API change needed."""
    return list_connectors_and_actions()


@app.get("/meta/operators")
def get_operators():
    from app.conditions import OPERATORS

    return {"operators": list(OPERATORS.keys())}


# ---------------------------------------------------------------------------
# Workflow CRUD (graph-aware)
# ---------------------------------------------------------------------------

@app.post("/workflows")
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)):
    """
    Creates a workflow and its full step graph in one call. Steps are
    given by index in the request; branch/next references are resolved
    to real DB ids after insert (since ids don't exist until insert time).
    """
    workflow = Workflow(
        name=payload.name,
        description=payload.description,
        trigger_type=payload.trigger_type,
        is_active=payload.is_active,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    db_steps = []
    for step_in in payload.steps:
        db_step = WorkflowStep(
            workflow_id=workflow.id,
            step_type=step_in.step_type,
            label=step_in.label,
            config=json.dumps(step_in.config),
        )
        db.add(db_step)
        db_steps.append(db_step)
    db.commit()
    for s in db_steps:
        db.refresh(s)

    # Resolve index-based references to real ids
    for step_in, db_step in zip(payload.steps, db_steps):
        if step_in.on_success_index is not None:
            db_step.on_success_step_id = db_steps[step_in.on_success_index].id
        if step_in.on_failure_index is not None:
            db_step.on_failure_step_id = db_steps[step_in.on_failure_index].id
        if step_in.next_index is not None:
            db_step.next_step_id = db_steps[step_in.next_index].id

    workflow.start_step_id = db_steps[0].id if db_steps else None
    db.commit()
    db.refresh(workflow)
    return {"id": workflow.id, "name": workflow.name, "step_count": len(db_steps)}


@app.get("/workflows")
def list_workflows(db: Session = Depends(get_db)):
    workflows = db.query(Workflow).all()
    result = []
    for w in workflows:
        result.append(
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "trigger_type": w.trigger_type,
                "is_active": w.is_active,
                "start_step_id": w.start_step_id,
                "step_count": len(w.steps),
            }
        )
    return result


@app.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "id": workflow.id,
        "name": workflow.name,
        "trigger_type": workflow.trigger_type,
        "start_step_id": workflow.start_step_id,
        "is_active": workflow.is_active,
        "steps": [
            {
                "id": s.id,
                "step_type": s.step_type,
                "label": s.label,
                "config": s.get_config(),
                "on_success_step_id": s.on_success_step_id,
                "on_failure_step_id": s.on_failure_step_id,
                "next_step_id": s.next_step_id,
            }
            for s in workflow.steps
        ],
    }


@app.patch("/workflows/{workflow_id}/toggle")
def toggle_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    workflow.is_active = not workflow.is_active
    db.commit()
    return {"id": workflow_id, "is_active": workflow.is_active}


@app.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(workflow)
    db.commit()
    return {"deleted": workflow_id}


# ---------------------------------------------------------------------------
# Natural-language workflow builder
# ---------------------------------------------------------------------------

@app.post("/workflows/from-instruction")
def create_workflow_from_instruction(payload: NLInstructionIn, db: Session = Depends(get_db)):
    """
    Parses a plain-English instruction into a workflow graph and creates
    it. Uses a real LLM if ANTHROPIC_API_KEY/OPENAI_API_KEY is set in
    the environment, otherwise a deterministic keyword-based fallback -
    the response's "mode" field tells you which one ran.
    """
    parse_result = parse_instruction(payload.instruction)
    spec = parse_result["parsed"]
    step_dicts = graph_spec_to_workflow_steps(spec)

    if not step_dicts:
        raise HTTPException(status_code=400, detail="Could not derive any steps from instruction")

    # Wire up a simple linear chain: condition (if present) -> action -> action -> ...
    steps_in = []
    for i, step_dict in enumerate(step_dicts):
        next_idx = i + 1 if i + 1 < len(step_dicts) else None
        if step_dict["step_type"] == "condition":
            steps_in.append(
                StepIn(
                    step_type="condition",
                    label=step_dict["label"],
                    config=step_dict["config"],
                    on_success_index=next_idx,
                    on_failure_index=None,  # no steps run if filter fails
                )
            )
        else:
            steps_in.append(
                StepIn(
                    step_type="action",
                    label=step_dict["label"],
                    config=step_dict["config"],
                    next_index=next_idx,
                )
            )

    workflow_payload = WorkflowCreate(
        name=payload.workflow_name or f"NL: {payload.instruction[:40]}",
        description=f"Generated from instruction: {payload.instruction}",
        trigger_type=spec["trigger_type"],
        steps=steps_in,
    )
    created = create_workflow(workflow_payload, db)
    created["parse_mode"] = parse_result["mode"]
    created["llm_error"] = parse_result.get("llm_error")
    created["parsed_spec"] = spec
    return created


# ---------------------------------------------------------------------------
# Event ingestion (manual simulation + real webhook endpoint)
# ---------------------------------------------------------------------------

@app.post("/events")
def submit_event(event: EventIn, db: Session = Depends(get_db)):
    """Manually simulate an event (used by the 'Simulate Event' UI tab)."""
    results = process_event(db, event.trigger_type, event.data, source="manual")
    return {"event": event.dict(), "results": results}


@app.post("/webhooks/{trigger_type}")
async def webhook_ingest(trigger_type: str, request: Request, db: Session = Depends(get_db)):
    """
    Real webhook endpoint - any external system can POST JSON here and
    it will run every active workflow listening for this trigger_type,
    exactly like a production iPaaS ingestion endpoint. This is the
    genuine trigger path; /events above is the simulation path used
    for demoing without a real external caller.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request body must be valid JSON")

    results = process_event(db, trigger_type, data, source="webhook")
    return {"received": data, "results": results}


@app.get("/events")
def list_events(db: Session = Depends(get_db)):
    events = db.query(EventLog).order_by(EventLog.id.desc()).limit(50).all()
    return [
        {
            "id": e.id,
            "trigger_type": e.trigger_type,
            "payload": json.loads(e.payload),
            "source": e.source,
            "received_at": e.received_at,
        }
        for e in events
    ]


# ---------------------------------------------------------------------------
# Execution history (full audit trail)
# ---------------------------------------------------------------------------

@app.get("/runs")
def list_runs(db: Session = Depends(get_db)):
    runs = db.query(ExecutionRun).order_by(ExecutionRun.id.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "workflow_id": r.workflow_id,
            "event_id": r.event_id,
            "status": r.status,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
        }
        for r in runs
    ]


@app.get("/runs/{run_id}/steps")
def get_run_steps(run_id: int, db: Session = Depends(get_db)):
    """The real payoff of the audit trail: see the exact path taken
    through the graph for one specific run, including every branch
    decision and the working data at each point."""
    steps = (
        db.query(ExecutionStepLog)
        .filter(ExecutionStepLog.run_id == run_id)
        .order_by(ExecutionStepLog.id)
        .all()
    )
    return [
        {
            "step_id": s.step_id,
            "step_type": s.step_type,
            "status": s.status,
            "detail": s.detail,
            "working_data": json.loads(s.working_data_snapshot) if s.working_data_snapshot else None,
            "executed_at": s.executed_at,
        }
        for s in steps
    ]


# ---------------------------------------------------------------------------
# Reference data (for the sql_lookup connector demo)
# ---------------------------------------------------------------------------

@app.post("/reference/customers")
def seed_customer(payload: LookupSeedIn, db: Session = Depends(get_db)):
    existing = db.query(CustomerLookup).filter(CustomerLookup.customer_id == payload.customer_id).first()
    if existing:
        existing.tier = payload.tier
        existing.region = payload.region
    else:
        db.add(CustomerLookup(customer_id=payload.customer_id, tier=payload.tier, region=payload.region))
    db.commit()
    return {"customer_id": payload.customer_id, "tier": payload.tier}


@app.get("/reference/customers")
def list_customers(db: Session = Depends(get_db)):
    return [
        {"customer_id": c.customer_id, "tier": c.tier, "region": c.region}
        for c in db.query(CustomerLookup).all()
    ]


# ---------------------------------------------------------------------------
# Credential management (encrypted storage - see app/credentials.py)
# ---------------------------------------------------------------------------

@app.post("/credentials")
def save_credential(payload: CredentialIn):
    set_credential(payload.key, payload.value)
    return {"saved": payload.key}


@app.get("/credentials")
def get_configured_credentials():
    """Returns which credential KEYS are set - never the actual values,
    since this endpoint is called by the UI to show configuration status."""
    return {"keys": list_credential_keys()}


@app.delete("/credentials/{key}")
def remove_credential(key: str):
    delete_credential(key)
    return {"deleted": key}


# ---------------------------------------------------------------------------
# Analytics - real aggregate queries over execution logs
# ---------------------------------------------------------------------------

@app.get("/analytics/summary")
def analytics_summary(db: Session = Depends(get_db)):
    """
    Computes reliability metrics directly from ExecutionRun and
    ExecutionStepLog - no separate analytics store, so these numbers
    are always consistent with what /runs and /runs/{id}/steps show.
    """
    all_runs = db.query(ExecutionRun).all()
    total_runs = len(all_runs)
    runs_with_error = sum(1 for r in all_runs if r.status == "error")
    failure_rate_pct = round((runs_with_error / total_runs) * 100, 1) if total_runs else 0.0

    # Most-triggered workflows
    workflow_counts = {}
    for r in all_runs:
        workflow_counts[r.workflow_id] = workflow_counts.get(r.workflow_id, 0) + 1
    most_triggered = []
    for wf_id, count in sorted(workflow_counts.items(), key=lambda x: -x[1]):
        wf = db.query(Workflow).filter(Workflow.id == wf_id).first()
        most_triggered.append({"workflow": wf.name if wf else f"#{wf_id}", "runs": count})

    # Failures by connector (look at action steps that errored)
    all_steps = db.query(ExecutionStepLog).filter(ExecutionStepLog.step_type == "action").all()
    connector_failures = {}
    for step in all_steps:
        if step.status == "error":
            # Look up which connector this step belongs to
            wf_step = db.query(WorkflowStep).filter(WorkflowStep.id == step.step_id).first()
            connector = "unknown"
            if wf_step:
                try:
                    connector = wf_step.get_config().get("connector", "unknown")
                except Exception:
                    pass
            connector_failures[connector] = connector_failures.get(connector, 0) + 1
    failures_by_connector = [
        {"connector": k, "failures": v} for k, v in connector_failures.items()
    ]

    # Average steps per run
    all_run_ids = [r.id for r in all_runs]
    if all_run_ids:
        total_steps = db.query(ExecutionStepLog).filter(ExecutionStepLog.run_id.in_(all_run_ids)).count()
        avg_steps = round(total_steps / len(all_run_ids), 1)
    else:
        avg_steps = 0.0

    return {
        "total_runs": total_runs,
        "runs_with_error": runs_with_error,
        "failure_rate_pct": failure_rate_pct,
        "most_triggered_workflows": most_triggered,
        "failures_by_connector": failures_by_connector,
        "avg_steps_per_run": avg_steps,
    }
