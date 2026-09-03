import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import EventLog


def get_event_count(db: Session, trigger_type: str, group_by_field: str, group_by_value: str, window_minutes: int) -> int:
    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
    candidates = (
        db.query(EventLog)
        .filter(EventLog.trigger_type == trigger_type)
        .filter(EventLog.received_at >= cutoff)
        .all()
    )
    count = 0
    for event in candidates:
        try:
            payload = json.loads(event.payload)
        except json.JSONDecodeError:
            continue
        if str(payload.get(group_by_field)) == str(group_by_value):
            count += 1
    return count


def evaluate_aggregate_leaf(rule: dict, current_event_data: dict, db: Session) -> bool:
    from app.conditions import OPERATORS

    spec = rule["aggregate"]
    group_by_field = spec["group_by_field"]
    group_by_value = spec.get("group_by_value", current_event_data.get(group_by_field))
    if group_by_value is None:
        return False

    count = get_event_count(
        db=db, trigger_type=spec["trigger_type"], group_by_field=group_by_field,
        group_by_value=group_by_value, window_minutes=spec["window_minutes"],
    )
    op_fn = OPERATORS.get(spec["operator"])
    if op_fn is None:
        raise ValueError(f"Unknown operator '{spec['operator']}'")
    return op_fn(count, spec["value"])
