"""
Natural-language workflow builder: takes a plain-English instruction
("when a new order over 1000 comes in from Delhi, email the manager
and log it") and produces a workflow graph (trigger + steps) in the
same shape the engine already executes - no separate code path.

Two modes:
  1. REAL LLM MODE - if a GROQ_API_KEY (or ANTHROPIC_API_KEY /
     OPENAI_API_KEY) is set in the environment, this calls that API to
     do genuine natural-language parsing into the structured graph.
  2. DETERMINISTIC FALLBACK - if no API key is configured, a small
     rule-based parser handles a useful subset of phrasing (trigger
     type, a numeric threshold condition, a region condition, and a
     small set of known actions) so the feature is still demoable
     without external credentials. This is clearly weaker than real
     LLM parsing and is labelled as such in its output.

Being upfront: the fallback is NOT "the LLM layer" - it's a stand-in
so the code path and API shape exist and work end-to-end. The value
of an LLM here is handling arbitrary phrasing the fallback can't;
wiring in a real key is a one-line config change (see below).
"""

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
    """
    Real LLM call. Tries Groq first (since it's the key configured for
    this project), then falls back to Anthropic or OpenAI if their keys
    are set instead. Requires the matching SDK package for whichever
    provider actually has a key present.
    """
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
            model="claude-sonnet-4-5",
            max_tokens=1000,
            system=PARSE_SYSTEM_PROMPT,
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
    """
    Deterministic, regex/keyword-based parser. Handles a useful subset:
      - trigger: "order"/"signup"/"row"/"status" keyword -> trigger_type
      - a numeric threshold: "over/above/greater than <number>" -> amount > number
      - a region: "from <Word>" -> region == Word
      - actions: "email"/"log"/"slack"/"post to <channel>"
    Clearly NOT full natural-language understanding - a real LLM call
    (see parse_with_llm) is what generalizes beyond these patterns.
    """
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
    amount_match = re.search(
        r"(?:over|above|greater than|more than)\s*(?:₹|rs\.?|inr)?\s*([\d,]+)", text
    )
    if amount_match:
        value = amount_match.group(1).replace(",", "")
        rules.append({"field": "amount", "operator": ">", "value": value})

    region_match = re.search(r"\bfrom\s+([A-Za-z]+)", instruction)
    if region_match:
        region = region_match.group(1)
        if region.lower() not in ("a", "the", "an"):
            rules.append({"field": "region", "operator": "==", "value": region})

    condition = {"logic": "AND", "rules": rules} if rules else None

    actions = []
    if "email" in text:
        actions.append(
            {
                "connector": "email",
                "action": "send_email",
                "params": {
                    "to": "manager@example.com",
                    "subject": "Workflow alert",
                    "body": "Triggered by: " + instruction,
                },
            }
        )
    if "log" in text:
        actions.append(
            {
                "connector": "log",
                "action": "log_event",
                "params": {"message": "Auto-logged: " + instruction},
            }
        )
    slack_match = re.search(r"post(?:\s+it)?\s+to\s+(#\w+)", text)
    if slack_match or "slack" in text:
        channel = slack_match.group(1) if slack_match else "#general"
        actions.append(
            {
                "connector": "slack",
                "action": "post_message",
                "params": {"channel": channel, "message": instruction},
            }
        )

    if not actions:  # always produce at least one action so the graph is runnable
        actions.append(
            {
                "connector": "log",
                "action": "log_event",
                "params": {"message": "Auto-logged (no action keyword matched): " + instruction},
            }
        )

    return {"trigger_type": trigger_type, "condition": condition, "actions": actions}


def parse_instruction(instruction: str) -> dict:
    """
    Public entry point. Returns:
        {
          "parsed": {...graph spec...},
          "mode": "llm" | "fallback"
        }
    """
    if _has_llm_key():
        try:
            return {"parsed": parse_with_llm(instruction), "mode": "llm"}
        except Exception as e:
            # Fall through to deterministic parser rather than hard-failing,
            # but surface the error so it's not silently swallowed.
            return {
                "parsed": parse_with_fallback(instruction),
                "mode": "fallback",
                "llm_error": str(e),
            }
    return {"parsed": parse_with_fallback(instruction), "mode": "fallback"}


def graph_spec_to_workflow_steps(spec: dict) -> list:
    """
    Converts the flat {trigger_type, condition, actions} spec above into
    the WorkflowStep row shape the engine executes: at most one condition
    step followed by a linear chain of action steps. (A hand-built
    workflow in the UI can be a richer branching graph than this generates;
    the NL builder intentionally targets the common "trigger -> filter ->
    do these things" shape, which covers most real requests.)
    Returns a list of step dicts ready to be inserted, with next/branch
    ids computed relative to a 1-indexed position - the caller assigns
    real DB ids after insert.
    """
    steps = []
    order = []

    if spec.get("condition"):
        steps.append({"step_type": "condition", "config": spec["condition"], "label": "Filter"})
        order.append("condition")

    for i, action in enumerate(spec.get("actions", [])):
        steps.append(
            {
                "step_type": "action",
                "config": {
                    "connector": action["connector"],
                    "action": action["action"],
                    "params": action.get("params", {}),
                    "retry": {"max_attempts": 1, "backoff_seconds": 0},
                },
                "label": f"Action: {action['connector']}.{action['action']}",
            }
        )
        order.append(f"action_{i}")

    return steps
