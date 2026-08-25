"""
Transform step: the "T" in ETL. Takes the current working data,
optionally enriches it via a connector lookup, and/or derives new
fields via simple string templates, returning an updated copy.

This is what lets a downstream condition or action see fields that
weren't in the original event at all - e.g. enrich an order event
with the customer's tier before deciding whether to send a VIP alert.
"""

from app.connectors import get_connector


def apply_template(template: str, data: dict) -> str:
    """Fills {field} placeholders in a template string from data.
    Missing fields are left as literal '{field}' rather than raising,
    so a bad template doesn't crash the whole workflow run."""
    try:
        return template.format(**data)
    except (KeyError, IndexError):
        return template


def apply_transform(config: dict, working_data: dict) -> dict:
    """
    config shape:
        {
          "set_fields": [{"target": "priority", "template": "HIGH"}],
          "lookup": {
             "connector": "sql_lookup",
             "action": "get_customer_tier",
             "input_field": "customer_id",   # read this field from working_data
             "param_name": "customer_id",     # pass it to the connector under this name
             "output_field": "customer_tier"  # write the connector's result here
          }
        }
    Both "set_fields" and "lookup" are optional; either or both may be present.
    Returns a NEW dict - the original working_data is never mutated in place,
    so each step's snapshot in the execution log is a true point-in-time record.
    """
    data = dict(working_data)  # shallow copy

    lookup = config.get("lookup")
    if lookup:
        connector = get_connector(lookup["connector"])
        input_value = data.get(lookup["input_field"])
        params = {lookup.get("param_name", lookup["input_field"]): input_value}
        result = connector.execute(lookup["action"], params, data)
        data[lookup["output_field"]] = result

    for field_spec in config.get("set_fields", []):
        data[field_spec["target"]] = apply_template(field_spec["template"], data)

    return data
