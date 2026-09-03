import json
from app.models import init_db, SessionLocal, Workflow, WorkflowStep, CustomerLookup

init_db()
db = SessionLocal()

db.query(CustomerLookup).delete()
db.add_all([
    CustomerLookup(customer_id="CUST001", tier="gold", region="Delhi"),
    CustomerLookup(customer_id="CUST002", tier="silver", region="Mumbai"),
    CustomerLookup(customer_id="CUST003", tier="gold", region="Bangalore"),
])
db.commit()

# Workflow 1: branching on nested AND/OR
wf1 = Workflow(name="VIP order alert with branching", trigger_type="new_order")
db.add(wf1); db.commit(); db.refresh(wf1)

condition_config = {
    "logic": "AND",
    "rules": [
        {"field": "amount", "operator": ">", "value": "1000"},
        {"logic": "OR", "rules": [
            {"field": "region", "operator": "==", "value": "Delhi"},
            {"field": "region", "operator": "==", "value": "Mumbai"},
        ]},
    ],
}
s1 = WorkflowStep(workflow_id=wf1.id, step_type="condition", label="High-value metro order?",
                   config=json.dumps(condition_config))
s2 = WorkflowStep(workflow_id=wf1.id, step_type="action", label="Alert Slack",
                   config=json.dumps({"connector": "slack", "action": "post_message",
                                       "params": {"channel": "#sales-vip",
                                                  "message": "VIP order: {name}, amount {amount}"},
                                       "retry": {"max_attempts": 2, "backoff_seconds": 1}}))
s3 = WorkflowStep(workflow_id=wf1.id, step_type="action", label="Quiet log",
                   config=json.dumps({"connector": "log", "action": "log_event",
                                       "params": {"message": "Standard order: {name}"}}))
db.add_all([s1, s2, s3]); db.commit()
for s in (s1, s2, s3): db.refresh(s)
s1.on_success_step_id = s2.id
s1.on_failure_step_id = s3.id
wf1.start_step_id = s1.id
db.commit()

# Workflow 2: transform (enrichment) -> condition -> action chain
wf2 = Workflow(name="Enriched customer tier alert", trigger_type="new_order")
db.add(wf2); db.commit(); db.refresh(wf2)

t1 = WorkflowStep(workflow_id=wf2.id, step_type="transform", label="Look up tier",
                   config=json.dumps({"lookup": {"connector": "sql_lookup", "action": "get_customer_tier",
                                                  "input_field": "customer_id", "param_name": "customer_id",
                                                  "output_field": "customer_tier"}}))
t2 = WorkflowStep(workflow_id=wf2.id, step_type="condition", label="Is gold?",
                   config=json.dumps({"logic": "AND", "rules": [
                       {"field": "customer_tier", "operator": "==", "value": "gold"}]}))
t3 = WorkflowStep(workflow_id=wf2.id, step_type="action", label="Email account manager",
                   config=json.dumps({"connector": "email", "action": "send_email",
                                       "params": {"to": "accounts@example.com",
                                                  "subject": "Gold customer order: {customer_id}",
                                                  "body": "Order from {customer_id}, amount {amount}"}}))
db.add_all([t1, t2, t3]); db.commit()
for s in (t1, t2, t3): db.refresh(s)
t1.next_step_id = t2.id
t2.on_success_step_id = t3.id
wf2.start_step_id = t1.id
db.commit()

db.close()
print("Seeded 2 branching workflows + 3 reference customers.")
