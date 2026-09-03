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
    logic = group.get("logic", "AND").upper()
    rules = group.get("rules", [])
    if not rules:
        return True

    results = []
    for rule in rules:
        if "logic" in rule:
            results.append(evaluate_group(rule, data, db=db))
        elif "aggregate" in rule:
            if db is None:
                results.append(False)
            else:
                from app.aggregate_state import evaluate_aggregate_leaf
                results.append(evaluate_aggregate_leaf(rule, data, db))
        else:
            results.append(evaluate_leaf(rule, data))

    if logic == "AND":
        return all(results)
    elif logic == "OR":
        return any(results)
    else:
        raise ValueError(f"Unknown logic operator '{logic}'")
