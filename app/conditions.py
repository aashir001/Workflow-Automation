"""
Condition evaluation: supports arbitrarily nested AND/OR groups, not
just a single field/operator/value check. A condition config looks
like:

    {
      "logic": "AND",
      "rules": [
        {"field": "amount", "operator": ">", "value": "1000"},
        {
          "logic": "OR",
          "rules": [
            {"field": "region", "operator": "==", "value": "Delhi"},
            {"field": "region", "operator": "==", "value": "Mumbai"}
          ]
        }
      ]
    }

This reads as: amount > 1000 AND (region == Delhi OR region == Mumbai).
Each "rule" is either a leaf (has "field") or another nested group
(has "logic") - `evaluate_group` recurses on whichever it finds.
"""

OPERATORS = {
    "==": lambda a, b: str(a) == str(b),
    "!=": lambda a, b: str(a) != str(b),
    ">": lambda a, b: _num(a) > _num(b),
    "<": lambda a, b: _num(a) < _num(b),
    ">=": lambda a, b: _num(a) >= _num(b),
    "<=": lambda a, b: _num(a) <= _num(b),
    "contains": lambda a, b: str(b).lower() in str(a).lower(),
    "not_contains": lambda a, b: str(b).lower() not in str(a).lower(),
    "in": lambda a, b: str(a) in [x.strip() for x in str(b).split(",")],
}


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("-inf")


def evaluate_leaf(rule: dict, data: dict) -> bool:
    field_value = data.get(rule["field"])
    if field_value is None:
        return False
    op_fn = OPERATORS.get(rule["operator"])
    if op_fn is None:
        raise ValueError(f"Unknown operator '{rule['operator']}'")
    return op_fn(field_value, rule["value"])


def evaluate_group(group: dict, data: dict, db=None) -> bool:
    """
    Recursively evaluates a (possibly nested) condition group.
    An empty rules list is treated as vacuously true (no filter).

    `db` is an optional SQLAlchemy session, required only if any rule
    in this group (or a nested group) is an "aggregate" rule (see
    app/aggregate_state.py) - a cross-event check like "5+ orders in
    the last hour" rather than a check on the current event alone. If
    an aggregate rule is encountered with no db session provided, it
    evaluates to False rather than raising, so plain event-only
    workflows are unaffected.
    """
    logic = group.get("logic", "AND").upper()
    rules = group.get("rules", [])

    if not rules:
        return True

    results = []
    for rule in rules:
        if "logic" in rule:  # nested group
            results.append(evaluate_group(rule, data, db=db))
        elif "aggregate" in rule:  # cross-event rule
            if db is None:
                results.append(False)
            else:
                from app.aggregate_state import evaluate_aggregate_leaf

                results.append(evaluate_aggregate_leaf(rule, data, db))
        else:  # plain leaf condition on the current event
            results.append(evaluate_leaf(rule, data))

    if logic == "AND":
        return all(results)
    elif logic == "OR":
        return any(results)
    else:
        raise ValueError(f"Unknown logic operator '{logic}' (expected AND/OR)")
