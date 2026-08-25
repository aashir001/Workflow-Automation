"""
Streamlit front-end (v2) for the Low-Code Workflow Automation Engine.

New in this version:
  - Natural-language workflow creation (talks to /workflows/from-instruction)
  - Full workflow graph inspector (shows every step and how they connect)
  - Execution audit trail viewer (pick a run, see every step it visited
    and the working data at each point - this is where branching becomes
    visible: you can see exactly which path a given event took)
  - Reference data management for the sql_lookup connector demo
  - Raw-JSON advanced workflow builder for constructing genuinely
    branching, multi-connector graphs (a full drag-and-drop visual
    builder is out of scope for a Streamlit prototype, but the JSON
    shape shown here IS exactly what the engine executes - it's
    honest advanced-mode, not a stand-in)

Run with:
    streamlit run streamlit_app.py
(after starting the backend: uvicorn app.main:app --reload)
"""

import streamlit as st
import requests
import json
import pandas as pd

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Workflow Automation Engine", layout="wide")
st.title("🔧 Low-Code Workflow Automation Engine")
st.caption(
    "Branching conditions · pluggable connectors · real enrichment lookups · "
    "natural-language workflow creation"
)

tab_nl, tab_advanced, tab_workflows, tab_simulate, tab_audit, tab_reference, tab_credentials, tab_analytics = st.tabs(
    [
        "✨ Build from English",
        "🧩 Advanced Builder (JSON)",
        "📋 Workflows",
        "▶️ Simulate Event",
        "🔍 Execution Audit Trail",
        "🗄️ Reference Data",
        "🔐 Credentials",
        "📈 Analytics",
    ]
)

# ---------------------------------------------------------------------------
# TAB: Natural-language builder
# ---------------------------------------------------------------------------
with tab_nl:
    st.subheader("Describe a workflow in plain English")
    st.caption(
        "Uses a real LLM if ANTHROPIC_API_KEY is set in your environment; "
        "otherwise falls back to a keyword-based parser that handles a "
        "useful subset of phrasing (trigger type, one numeric threshold, "
        "one region, and email/log/slack actions). The response tells you "
        "which mode ran."
    )

    instruction = st.text_area(
        "Instruction",
        placeholder="When a new order over 1500 comes in from Mumbai, email the manager and log it",
        height=80,
    )
    wf_name = st.text_input("Workflow name (optional)")

    if st.button("Generate Workflow"):
        if not instruction.strip():
            st.warning("Enter an instruction first.")
        else:
            resp = requests.post(
                f"{API_URL}/workflows/from-instruction",
                json={"instruction": instruction, "workflow_name": wf_name or None},
            )
            if resp.status_code == 200:
                result = resp.json()
                mode = result["parse_mode"]
                if mode == "llm":
                    st.success(f"Created workflow #{result['id']} using a real LLM call.")
                else:
                    st.info(
                        f"Created workflow #{result['id']} using the deterministic "
                        f"fallback parser (no ANTHROPIC_API_KEY set)."
                    )
                    if result.get("llm_error"):
                        st.caption(f"LLM call was attempted but failed: {result['llm_error']}")
                st.json(result["parsed_spec"])
            else:
                st.error(f"Failed: {resp.text}")

# ---------------------------------------------------------------------------
# TAB: Advanced JSON builder - the real graph shape, exposed honestly
# ---------------------------------------------------------------------------
with tab_advanced:
    st.subheader("Build a workflow graph directly")
    st.caption(
        "This is exactly the JSON shape the engine executes - condition "
        "steps branch on success/failure, transform/action steps chain "
        "via next_index. Index 0 in the steps list is always the start step."
    )

    try:
        connectors = requests.get(f"{API_URL}/meta/connectors").json()
        st.markdown("**Available connectors and actions:**")
        st.json(connectors)
    except Exception:
        st.warning("Backend not reachable.")

    example = {
        "name": "Example: branching high-value order alert",
        "trigger_type": "new_order",
        "steps": [
            {
                "step_type": "condition",
                "label": "amount > 1000?",
                "config": {
                    "logic": "AND",
                    "rules": [{"field": "amount", "operator": ">", "value": "1000"}],
                },
                "on_success_index": 1,
                "on_failure_index": 2,
            },
            {
                "step_type": "action",
                "label": "Slack alert",
                "config": {
                    "connector": "slack",
                    "action": "post_message",
                    "params": {"channel": "#alerts", "message": "High value order: {name}"},
                },
            },
            {
                "step_type": "action",
                "label": "Quiet log",
                "config": {
                    "connector": "log",
                    "action": "log_event",
                    "params": {"message": "Normal order: {name}"},
                },
            },
        ],
    }

    workflow_json = st.text_area(
        "Workflow definition (JSON)", value=json.dumps(example, indent=2), height=400
    )

    if st.button("Create Workflow from JSON"):
        try:
            payload = json.loads(workflow_json)
            resp = requests.post(f"{API_URL}/workflows", json=payload)
            if resp.status_code == 200:
                st.success(f"Created: {resp.json()}")
            else:
                st.error(f"Failed: {resp.text}")
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")

# ---------------------------------------------------------------------------
# TAB: Workflow list + graph inspector
# ---------------------------------------------------------------------------
with tab_workflows:
    st.subheader("All workflows")
    try:
        workflows = requests.get(f"{API_URL}/workflows").json()
    except Exception:
        workflows = []
        st.warning("Backend not reachable - is `uvicorn app.main:app --reload` running?")

    if workflows:
        st.dataframe(pd.DataFrame(workflows), use_container_width=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            inspect_id = st.number_input("Workflow ID to inspect", min_value=1, step=1)
            if st.button("Show graph"):
                detail = requests.get(f"{API_URL}/workflows/{int(inspect_id)}").json()
                st.json(detail)
        with col2:
            toggle_id = st.number_input("Workflow ID to toggle", min_value=1, step=1, key="tog")
            if st.button("Toggle active/inactive"):
                r = requests.patch(f"{API_URL}/workflows/{int(toggle_id)}/toggle")
                st.write(r.json())
        with col3:
            delete_id = st.number_input("Workflow ID to delete", min_value=1, step=1, key="del")
            if st.button("Delete"):
                r = requests.delete(f"{API_URL}/workflows/{int(delete_id)}")
                st.write(r.json())
    else:
        st.info("No workflows yet - create one in another tab, or run `python seed_data.py`.")

# ---------------------------------------------------------------------------
# TAB: Simulate an event
# ---------------------------------------------------------------------------
with tab_simulate:
    st.subheader("Simulate an incoming event")
    st.caption(
        "This is the manual simulation path. Real external systems should "
        "instead POST to /webhooks/{trigger_type} - see the README."
    )

    sim_trigger = st.selectbox(
        "Trigger type", ["new_order", "new_signup", "row_added", "status_changed"]
    )
    sim_data_raw = st.text_area(
        "Event data (JSON)",
        value='{"name": "Aashir", "region": "Delhi", "amount": 1500, "customer_id": "CUST001"}',
    )

    if st.button("Send Event"):
        try:
            data = json.loads(sim_data_raw)
            resp = requests.post(
                f"{API_URL}/events", json={"trigger_type": sim_trigger, "data": data}
            )
            st.json(resp.json())
        except json.JSONDecodeError:
            st.error("Event data must be valid JSON.")

# ---------------------------------------------------------------------------
# TAB: Execution audit trail
# ---------------------------------------------------------------------------
with tab_audit:
    st.subheader("Execution runs")
    st.caption(
        "Every run of every workflow's graph, for every event. Pick a run "
        "to see exactly which steps it visited and what the working data "
        "looked like at each point - this is how you verify branching "
        "actually took the path you expect."
    )
    try:
        runs = requests.get(f"{API_URL}/runs").json()
        if runs:
            st.dataframe(pd.DataFrame(runs), use_container_width=True)
            run_id = st.number_input("Run ID to inspect", min_value=1, step=1)
            if st.button("Show step-by-step trace"):
                steps = requests.get(f"{API_URL}/runs/{int(run_id)}/steps").json()
                for s in steps:
                    icon = {"passed": "✅", "failed": "❌", "success": "✅", "error": "🔴", "applied": "🔄"}.get(
                        s["status"], "•"
                    )
                    st.markdown(f"{icon} **Step {s['step_id']}** ({s['step_type']}, {s['status']}): {s['detail']}")
                    with st.expander("Working data at this point"):
                        st.json(s["working_data"])
        else:
            st.info("No runs yet - simulate an event first.")
    except Exception:
        st.warning("Backend not reachable.")

# ---------------------------------------------------------------------------
# TAB: Reference data for the sql_lookup connector
# ---------------------------------------------------------------------------
with tab_reference:
    st.subheader("Customer reference table")
    st.caption(
        "Backs the sql_lookup connector's get_customer_tier action - "
        "used by transform steps to enrich events with real data, "
        "demonstrated in the seeded 'Enriched customer tier alert' workflow."
    )
    try:
        customers = requests.get(f"{API_URL}/reference/customers").json()
        if customers:
            st.dataframe(pd.DataFrame(customers), use_container_width=True)
    except Exception:
        st.warning("Backend not reachable.")

    with st.form("add_customer"):
        st.markdown("**Add / update a customer**")
        cid = st.text_input("Customer ID", placeholder="CUST004")
        tier = st.selectbox("Tier", ["gold", "silver", "bronze"])
        region = st.text_input("Region", placeholder="Hyderabad")
        if st.form_submit_button("Save"):
            r = requests.post(
                f"{API_URL}/reference/customers",
                json={"customer_id": cid, "tier": tier, "region": region},
            )
            st.success(r.json())

# ---------------------------------------------------------------------------
# TAB: Credential management - real keys, encrypted, no code editing needed
# ---------------------------------------------------------------------------
with tab_credentials:
    st.subheader("Connector credentials")
    st.caption(
        "Paste real API keys/webhook URLs here instead of editing connector "
        "source files. Values are encrypted at rest (see app/credentials.py) "
        "and only ever decrypted in-memory when a connector needs them."
    )

    try:
        configured = requests.get(f"{API_URL}/credentials").json()
        configured_keys = configured.get("keys", [])
    except Exception:
        configured_keys = []
        st.warning("Backend not reachable.")

    if configured_keys:
        st.success(f"Currently configured: {', '.join(configured_keys)}")
    else:
        st.info("No credentials configured yet - every connector will run in simulated mode.")

    CREDENTIAL_FIELDS = [
        ("SLACK_WEBHOOK_URL", "Slack incoming webhook URL", "https://hooks.slack.com/services/..."),
        ("TWILIO_ACCOUNT_SID", "Twilio Account SID (WhatsApp)", "ACxxxxxxxxxxxxxxxx"),
        ("TWILIO_AUTH_TOKEN", "Twilio Auth Token (WhatsApp)", ""),
        ("TWILIO_WHATSAPP_FROM", "Twilio WhatsApp sandbox 'from' number", "whatsapp:+14155238886"),
        ("EMAIL_SMTP_USER", "Email address (SMTP)", "you@gmail.com"),
        ("EMAIL_SMTP_PASSWORD", "SMTP app password", ""),
        ("EMAIL_SMTP_HOST", "SMTP host (optional, default smtp.gmail.com)", "smtp.gmail.com"),
        ("GOOGLE_SERVICE_ACCOUNT_JSON", "Google service account JSON (paste full file contents)", "{...}"),
    ]

    with st.form("save_credential"):
        st.markdown("**Add / update a credential**")
        key = st.selectbox("Credential", [f[0] for f in CREDENTIAL_FIELDS],
                            format_func=lambda k: next(f[1] for f in CREDENTIAL_FIELDS if f[0] == k))
        placeholder = next(f[2] for f in CREDENTIAL_FIELDS if f[0] == key)
        value = st.text_area("Value", placeholder=placeholder, height=100 if key == "GOOGLE_SERVICE_ACCOUNT_JSON" else None)
        if st.form_submit_button("Save credential"):
            r = requests.post(f"{API_URL}/credentials", json={"key": key, "value": value})
            if r.status_code == 200:
                st.success(f"Saved {key}.")
            else:
                st.error(f"Failed: {r.text}")

    delete_key = st.selectbox("Delete a credential", ["(none)"] + configured_keys, key="del_cred")
    if delete_key != "(none)" and st.button("Delete selected credential"):
        r = requests.delete(f"{API_URL}/credentials/{delete_key}")
        st.success(r.json())

# ---------------------------------------------------------------------------
# TAB: Analytics - real aggregate queries over the execution logs
# ---------------------------------------------------------------------------
with tab_analytics:
    st.subheader("Reliability analytics")
    st.caption(
        "Aggregate views computed from the real execution_step_log and "
        "execution_runs tables - not simulated numbers."
    )

    try:
        stats = requests.get(f"{API_URL}/analytics/summary").json()
    except Exception:
        stats = None
        st.warning("Backend not reachable.")

    if stats:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total runs", stats["total_runs"])
        with col2:
            st.metric("Runs with an error", stats["runs_with_error"])
        with col3:
            st.metric("Failure rate", f"{stats['failure_rate_pct']}%")

        st.divider()
        st.markdown("**Most-triggered workflows**")
        if stats["most_triggered_workflows"]:
            st.dataframe(pd.DataFrame(stats["most_triggered_workflows"]), use_container_width=True)
        else:
            st.info("No runs yet.")

        st.markdown("**Failure count by connector**")
        if stats["failures_by_connector"]:
            df = pd.DataFrame(stats["failures_by_connector"])
            st.bar_chart(df.set_index("connector"))
        else:
            st.info("No connector failures recorded yet.")

        st.markdown("**Average steps per run**")
        st.metric("Avg steps/run", stats["avg_steps_per_run"])
