"""
Aggregate-state tracking.

Every normal condition only looks at the ONE event currently being
processed. This module adds the ability to check patterns ACROSS past
events - e.g. "has this customer placed more than 5 orders in the last
hour" - by querying the EventLog table (which already stores every
event permanently) rather than adding a separate counter table that
could drift out of sync.

A condition rule can now include an "aggregate" leaf instead of a
plain field/operator/value leaf:

    {
      "aggregate": {
        "trigger_type": "new_order",
        "group_by_field": "customer_id",
        "window_minutes": 60,
        "operator": ">",
        "value": "5"
      }
    }

This counts how many past events of `trigger_type` had the same value
for `group_by_field` as the CURRENT event, within the last
`window_minutes`, and compares that count against `value` using
`operator`. The current event itself is included in the count (so
"more than 5" means "this is at least the 6th").
"""

import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import EventLog


def get_event_count(
    db: Session,
    trigger_type: str,
    group_by_field: str,
    group_by_value: str,
    window_minutes: int,
) -> int:
    """
    Counts events of `trigger_type` in the last `window_minutes` whose
    payload's `group_by_field` matches `group_by_value`.

    Done by querying EventLog directly rather than maintaining a
    separate running counter, so the count is always exactly correct
    (a running counter can drift if a workflow errors mid-update) at
    the cost of scanning recent rows - acceptable at the scale this
    project targets small businesses.
    """
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
    """
    Evaluates one aggregate rule against the live database, using the
    current event's own field value as the group-by target (e.g. "this
    order's customer_id") unless a fixed group_by_value is given.
    """
    from app.conditions import OPERATORS  # local import avoids a cycle

    spec = rule["aggregate"]
    group_by_field = spec["group_by_field"]
    group_by_value = spec.get(
        "group_by_value", current_event_data.get(group_by_field)
    )
    if group_by_value is None:
        return False

    count = get_event_count(
        db=db,
        trigger_type=spec["trigger_type"],
        group_by_field=group_by_field,
        group_by_value=group_by_value,
        window_minutes=spec["window_minutes"],
    )

    op_fn = OPERATORS.get(spec["operator"])
    if op_fn is None:
        raise ValueError(f"Unknown operator '{spec['operator']}'")
    return op_fn(count, spec["value"])
