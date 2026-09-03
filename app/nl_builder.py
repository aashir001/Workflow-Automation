import os
import re
import json


def _has_llm_key() -> bool:
    return bool(
        os.environ.get("GROQ_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )


PARSE_SYSTEM_PROMPT = """You convert a plain-English automation instruction into JSON
describing a workflow graph. Output ONLY valid JSON, no prose, matching this shape:

{
  "trigger_type": "new_order" | "new_signup" | "row_added" | "status_changed",
  "condition": {"logic": "AND", "rules": [{"field": str, "operator": str, "value": str}]} | null,
  "actions": [{"connector": str, "action": str, "params": {...}}]
}

Valid connectors/actions: log.log_event(message), email.send_email(to,subject,body),
slack.post_message(channel,message), sheet.append_row(fields), http.post_json(url,body).
Valid operators: ==, !=, >, <, >=, <=, contains, in.
If no condition is implied, use null for "condition"."""


def parse_with_llm(instruction: str) -> dict:
    if os.environ.get("GROQ_API_KEY"):
        from groq import Groq
        client = Groq()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": PARSE_SYSTEM_PROMPT},
                {"role": "user", "content": instruction},
            ],
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content
    elif os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-5", max_tokens=1000, system=PARSE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": instruction}],
        )
        text = response.content[0].text
    else:
        import openai
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": PARSE_SYSTEM_PROMPT},
                {"role": "user", "content": instruction},
            ],
        )
        text = response.choices[0].message.content
    return json.loads(text)


def parse_with_fallback(instruction: str) -> dict:
    text = instruction.lower()
    if "signup" in text or "sign up" in text or "sign-up" in text:
        trigger_type = "new_signup"
    elif "order" in text:
        trigger_type = "new_order"
    elif "status" in text:
        trigger_type = "status_changed"
    else:
        trigger_type = "row_added"

    rules = []
    amount_match = re.search(r"(?:over|above|greater than|more than)\s*(?:₹|rs\.?|inr)?\s*([\d,]+)", text)
    if amount_match:
        rules.append({"field": "amount", "operator": ">", "value": amount_match.group(1).replace(",", "")})

    region_match = re.search(r"\bfrom\s+([A-Za-z]+)", instruction)
    if region_match and region_match.group(1).lower() not in ("a", "the", "an"):
        rules.append({"field": "region", "operator": "==", "value": region_match.group(1)})

    condition = {"logic": "AND", "rules": rules} if rules else None

    actions = []
    if "email" in text:
        actions.append({"connector": "email", "action": "send_email",
                         "params": {"to": "manager@example.com", "subject": "Workflow alert",
                                    "body": "Triggered by: " + instruction}})
    if "log" in text:
        actions.append({"connector": "log", "action": "log_event",
                         "params": {"message": "Auto-logged: " + instruction}})
    slack_match = re.search(r"post(?:\s+it)?\s+to\s+(#\w+)", text)
    if slack_match or "slack" in text:
        channel = slack_match.group(1) if slack_match else "#general"
        actions.append({"connector": "slack", "action": "post_message",
                         "params": {"channel": channel, "message": instruction}})
    if not actions:
        actions.append({"connector": "log", "action": "log_event",
                         "params": {"message": "Auto-logged (no action keyword matched): " + instruction}})

    return {"trigger_type": trigger_type, "condition": condition, "actions": actions}


def parse_instruction(instruction: str) -> dict:
    if _has_llm_key():
        try:
            return {"parsed": parse_with_llm(instruction), "mode": "llm"}
        except Exception as e:
            return {"parsed": parse_with_fallback(instruction), "mode": "fallback", "llm_error": str(e)}
    return {"parsed": parse_with_fallback(instruction), "mode": "fallback"}


def graph_spec_to_workflow_steps(spec: dict) -> list:
    steps = []
    if spec.get("condition"):
        steps.append({"step_type": "condition", "config": spec["condition"], "label": "Filter"})
    for action in spec.get("actions", []):
        steps.append({
            "step_type": "action",
            "config": {
                "connector": action["connector"], "action": action["action"],
                "params": action.get("params", {}), "retry": {"max_attempts": 1, "backoff_seconds": 0},
            },
            "label": f"Action: {action['connector']}.{action['action']}",
        })
    return steps
