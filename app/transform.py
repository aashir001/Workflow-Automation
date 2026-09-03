from app.connectors import get_connector


def apply_template(template: str, data: dict) -> str:
    try:
        return template.format(**data)
    except (KeyError, IndexError):
        return template


def apply_transform(config: dict, working_data: dict) -> dict:
    data = dict(working_data)
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
