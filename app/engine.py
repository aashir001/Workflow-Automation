import json
import time
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Workflow, WorkflowStep, EventLog, ExecutionRun, ExecutionStepLog
from app.conditions import evaluate_group
from app.transform import apply_transform, apply_template
from app.connectors import get_connector
from app.connectors.base import ConnectorError

MAX_GRAPH_STEPS = 50


def _fill_params(params: dict, data: dict) -> dict:
    filled = {}
    for k, v in params.items():
        filled[k] = apply_template(v, data) if isinstance(v, str) else v
    return filled


def run_action_step(step: WorkflowStep, working_data: dict):
    config = step.get_config()
    connector = get_connector(config["connector"])
    params = _fill_params(config.get("params", {}), working_data)
    retry_cfg = config.get("retry", {"max_attempts": 1, "backoff_seconds": 0})
    max_attempts = retry_cfg.get("max_attempts", 1)
    backoff = retry_cfg.get("backoff_seconds", 0)

    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = connector.execute(config["action"], params, working_data)
            status = "success" if attempt == 1 else f"success_after_retry_{attempt}"
            return status, result
        except ConnectorError as e:
            last_error = str(e)
            if attempt < max_attempts:
                time.sleep(backoff)
        except Exception as e:
            return "error", f"Unexpected error: {e}"
    return "error", f"Failed after {max_attempts} attempts: {last_error}"


def run_workflow_graph(db: Session, workflow: Workflow, event_id: int, event_data: dict) -> ExecutionRun:
    run = ExecutionRun(workflow_id=workflow.id, event_id=event_id, status="completed")
    db.add(run)
    db.commit()
    db.refresh(run)

    steps_by_id = {s.id: s for s in workflow.steps}
    working_data = dict(event_data)
    current_step_id = workflow.start_step_id
    visited_count = 0

    while current_step_id is not None:
        visited_count += 1
        if visited_count > MAX_GRAPH_STEPS:
            _log_step(db, run.id, -1, "error", "error", "Aborted: exceeded max step count", working_data)
            run.status = "error"
            break

        step = steps_by_id.get(current_step_id)
        if step is None:
            break

        if step.step_type == "condition":
            config = step.get_config()
            passed = evaluate_group(config, working_data, db=db)
            status = "passed" if passed else "failed"
            _log_step(db, run.id, step.id, step.step_type, status,
                       f"Condition {'passed' if passed else 'did not pass'}: {config}", working_data)
            current_step_id = step.on_success_step_id if passed else step.on_failure_step_id

        elif step.step_type == "transform":
            config = step.get_config()
            try:
                working_data = apply_transform(config, working_data)
                _log_step(db, run.id, step.id, step.step_type, "applied", f"Transform applied: {config}", working_data)
            except Exception as e:
                _log_step(db, run.id, step.id, step.step_type, "error", f"Transform failed: {e}", working_data)
                run.status = "error"
            current_step_id = step.next_step_id

        elif step.step_type == "action":
            status, detail = run_action_step(step, working_data)
            _log_step(db, run.id, step.id, step.step_type, status, detail, working_data)
            if status == "error":
                run.status = "error"
            current_step_id = step.next_step_id
        else:
            raise ValueError(f"Unknown step_type '{step.step_type}'")

    run.finished_at = datetime.utcnow()
    db.commit()
    return run


def _log_step(db, run_id, step_id, step_type, status, detail, working_data):
    log = ExecutionStepLog(run_id=run_id, step_id=step_id, step_type=step_type,
                            status=status, detail=detail, working_data_snapshot=json.dumps(working_data))
    db.add(log)
    db.commit()


def process_event(db: Session, trigger_type: str, event_data: dict, source: str = "manual") -> list:
    event = EventLog(trigger_type=trigger_type, payload=json.dumps(event_data), source=source)
    db.add(event)
    db.commit()
    db.refresh(event)

    matching_workflows = (
        db.query(Workflow)
        .filter(Workflow.trigger_type == trigger_type, Workflow.is_active == True)
        .all()
    )

    results = []
    for workflow in matching_workflows:
        run = run_workflow_graph(db, workflow, event.id, event_data)
        step_logs = (
            db.query(ExecutionStepLog)
            .filter(ExecutionStepLog.run_id == run.id)
            .order_by(ExecutionStepLog.id)
            .all()
        )
        results.append({
            "workflow_id": workflow.id,
            "workflow_name": workflow.name,
            "run_id": run.id,
            "status": run.status,
            "steps_executed": [
                {"step_id": s.step_id, "type": s.step_type, "status": s.status, "detail": s.detail}
                for s in step_logs
            ],
        })
    return results
