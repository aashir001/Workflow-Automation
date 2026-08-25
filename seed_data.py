"""
Seeds three example workflows that actually exercise the layered
architecture (branching, nested conditions, multi-connector chains,
and real enrichment) rather than a single flat rule:

  1. "VIP order alert with branching" - nested AND/OR condition,
     branches to a Slack alert on one path and a plain log on the other.
  2. "Enriched customer tier alert" - a TRANSFORM step does a real SQL
     lookup to enrich the event, then a CONDITION checks the enriched
     field, before a multi-step ACTION chain (email -> sheet -> log).
  3. "Webhook relay" - demonstrates the real (non-simulated) HTTP
     connector by relaying every new_signup event to a test endpoint.

Run with:
    python seed_data.py
(after starting the backend at least once, so the DB schema exists)
"""

import json
from app.models import init_db, SessionLocal, Workflow, WorkflowStep, CustomerLookup

init_db()
db = SessionLocal()

# ---------------------------------------------------------------------------
# Reference data for the sql_lookup connector
# ---------------------------------------------------------------------------
db.query(CustomerLookup).delete()
db.add_all(
    [
        CustomerLookup(customer_id="CUST001", tier="gold", region="Delhi"),
        CustomerLookup(customer_id="CUST002", tier="silver", region="Mumbai"),
        CustomerLookup(customer_id="CUST003", tier="gold", region="Bangalore"),
    ]
)
db.commit()

# ---------------------------------------------------------------------------
# Workflow 1: branching on a nested AND/OR condition
#
#   amount > 1000 AND (region == Delhi OR region == Mumbai)
#     -> TRUE  branch: Slack alert
#     -> FALSE branch: quiet log entry
# ---------------------------------------------------------------------------

wf1 = Workflow(name="VIP order alert with branching", trigger_type="new_order")
db.add(wf1)
db.commit()
db.refresh(wf1)

condition_config = {
    "logic": "AND",
    "rules": [
        {"field": "amount", "operator": ">", "value": "1000"},
        {
            "logic": "OR",
            "rules": [
                {"field": "region", "operator": "==", "value": "Delhi"},
                {"field": "region", "operator": "==", "value": "Mumbai"},
            ],
        },
    ],
}

step1_condition = WorkflowStep(
    workflow_id=wf1.id,
    step_type="condition",
    label="High-value metro order?",
    config=json.dumps(condition_config),
)
step2_slack = WorkflowStep(
    workflow_id=wf1.id,
    step_type="action",
    label="Alert #sales-vip on Slack",
    config=json.dumps(
        {
            "connector": "slack",
            "action": "post_message",
            "params": {
                "channel": "#sales-vip",
                "message": "VIP order: {name}, amount {amount}, region {region}",
            },
            "retry": {"max_attempts": 2, "backoff_seconds": 1},
        }
    ),
)
step3_quiet_log = WorkflowStep(
    workflow_id=wf1.id,
    step_type="action",
    label="Quiet log (non-VIP order)",
    config=json.dumps(
        {
            "connector": "log",
            "action": "log_event",
            "params": {"message": "Standard order: {name}, amount {amount}"},
        }
    ),
)
db.add_all([step1_condition, step2_slack, step3_quiet_log])
db.commit()
for s in (step1_condition, step2_slack, step3_quiet_log):
    db.refresh(s)

step1_condition.on_success_step_id = step2_slack.id
step1_condition.on_failure_step_id = step3_quiet_log.id
wf1.start_step_id = step1_condition.id
db.commit()

# ---------------------------------------------------------------------------
# Workflow 2: TRANSFORM (real SQL enrichment) -> CONDITION on enriched
# field -> multi-step ACTION chain
# ---------------------------------------------------------------------------

wf2 = Workflow(name="Enriched customer tier alert", trigger_type="new_order")
db.add(wf2)
db.commit()
db.refresh(wf2)

step1_enrich = WorkflowStep(
    workflow_id=wf2.id,
    step_type="transform",
    label="Look up customer tier",
    config=json.dumps(
        {
            "lookup": {
                "connector": "sql_lookup",
                "action": "get_customer_tier",
                "input_field": "customer_id",
                "param_name": "customer_id",
                "output_field": "customer_tier",
            }
        }
    ),
)
step2_check_gold = WorkflowStep(
    workflow_id=wf2.id,
    step_type="condition",
    label="Is customer tier gold?",
    config=json.dumps({"logic": "AND", "rules": [{"field": "customer_tier", "operator": "==", "value": "gold"}]}),
)
step3_email = WorkflowStep(
    workflow_id=wf2.id,
    step_type="action",
    label="Email account manager",
    config=json.dumps(
        {
            "connector": "email",
            "action": "send_email",
            "params": {
                "to": "accounts@example.com",
                "subject": "Gold customer order: {customer_id}",
                "body": "Order from {customer_id} (tier: {customer_tier}), amount {amount}",
            },
        }
    ),
)
step4_sheet = WorkflowStep(
    workflow_id=wf2.id,
    step_type="action",
    label="Record in gold-tier sheet",
    config=json.dumps(
        {
            "connector": "sheet",
            "action": "append_row",
            "params": {"fields": ["customer_id", "customer_tier", "amount"]},
        }
    ),
)
db.add_all([step1_enrich, step2_check_gold, step3_email, step4_sheet])
db.commit()
for s in (step1_enrich, step2_check_gold, step3_email, step4_sheet):
    db.refresh(s)

step1_enrich.next_step_id = step2_check_gold.id
step2_check_gold.on_success_step_id = step3_email.id
step2_check_gold.on_failure_step_id = None  # non-gold customers: do nothing further
step3_email.next_step_id = step4_sheet.id
wf2.start_step_id = step1_enrich.id
db.commit()

# ---------------------------------------------------------------------------
# Workflow 3: real outbound HTTP call (not simulated) relaying signups
# to a public request-inspection endpoint, so you can literally watch
# the real HTTP request arrive.
# ---------------------------------------------------------------------------

wf3 = Workflow(name="Webhook relay for new signups", trigger_type="new_signup")
db.add(wf3)
db.commit()
db.refresh(wf3)

step1_relay = WorkflowStep(
    workflow_id=wf3.id,
    step_type="action",
    label="Relay to webhook.site test endpoint",
    config=json.dumps(
        {
            "connector": "http",
            "action": "post_json",
            "params": {
                # Replace with your own https://webhook.site/<id> URL to watch
                # real requests arrive - left as a placeholder here so seeding
                # doesn't depend on network access.
                "url": "https://httpbin.org/post",
                "body": {"relayed_signup": "{name}", "region": "{region}"},
            },
            "retry": {"max_attempts": 2, "backoff_seconds": 1},
        }
    ),
)
db.add(step1_relay)
db.commit()
db.refresh(step1_relay)
wf3.start_step_id = step1_relay.id
db.commit()

db.close()
print("Seeded 3 layered workflows (branching, enrichment, real HTTP relay) + 3 reference customers.")
