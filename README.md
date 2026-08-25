# Low-Code Workflow Automation Engine

A working, multi-layer automation engine in the spirit of Zapier / n8n /
UnifyApps' iPaaS layer: a user (or a plain-English instruction) defines a
**trigger → branching conditions → data enrichment → connector actions**
graph, and the engine executes it - with a full audit trail of exactly
which path was taken and why.

This is v2 of the project. v1 was a single flat rule (one trigger, one
condition, one action). This version replaces that with a real graph
engine, a pluggable connector architecture, nested boolean conditions,
a genuine data-enrichment layer, real outbound HTTP calls, and an
LLM-backed natural-language workflow builder.

**Publishing this repo publicly?** All secrets (API keys, encryption
key) load from a local `.env` file, which is gitignored and never
committed — `.env.example` (with blank placeholders) is the only
version meant to be pushed. Nothing in the committed code contains a
real key, webhook URL, or credential of any kind.

## Architecture

```
┌─────────────────┐        ┌──────────────────────────────┐
│  Streamlit UI    │─HTTP──▶│  FastAPI backend               │
│  - NL builder    │        │  - workflow CRUD (graph-aware) │
│  - JSON builder  │        │  - /webhooks/{trigger} (real   │
│  - audit viewer  │        │    external ingestion)         │
└─────────────────┘        │  - /events (manual simulation) │
                             └──────────┬────────────────────┘
                                        │
                             ┌──────────▼────────────────────┐
                             │  engine.py - graph walker      │
                             │  visits CONDITION / TRANSFORM /│
                             │  ACTION steps, branching on    │
                             │  condition results, retrying   │
                             │  failed actions, logging every │
                             │  step visited                  │
                             └──────────┬────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
            conditions.py         transform.py        connectors/*.py
            nested AND/OR         field derivation +   log, email, slack,
            rule groups           connector-based       sheet, http (REAL),
                                  enrichment lookups     sql_lookup (REAL)
```

## What makes this "layered" rather than a flat rule engine

1. **Branching graphs, not a single if/then.** A workflow is a directed
   graph of steps (`app/models.py: WorkflowStep`). A CONDITION step has
   *two* possible next steps (`on_success_step_id` / `on_failure_step_id`),
   so a workflow can genuinely branch: "if VIP, alert Slack; otherwise,
   just log it" — both branches exist in the same workflow, not two
   separate ones.

2. **Nested boolean conditions.** `app/conditions.py` evaluates
   arbitrarily nested `AND`/`OR` groups recursively — e.g.
   `amount > 1000 AND (region == Delhi OR region == Mumbai)` — not a
   single field/operator/value check.

3. **Pluggable connector architecture.** Every integration (`app/connectors/*.py`)
   implements `BaseConnector` and is registered in one place
   (`app/connectors/__init__.py`). Adding a new integration means
   writing one new file — the engine, models, and API never need to
   change. Six connectors are implemented: `log`, `email`, `slack`,
   `sheet` (all simulated/local-file for demoability), plus `http` and
   `sql_lookup`, which are **genuinely functional** — `http` makes real
   outbound HTTP requests to any URL, and `sql_lookup` queries a real
   reference table in the app's own database.

4. **A real data-enrichment (transform) layer.** `app/transform.py`
   lets a TRANSFORM step call a connector to enrich the event with data
   it didn't originally contain — e.g. an order event carrying only a
   `customer_id` gets enriched with that customer's real `tier` from
   the database before a downstream condition decides whether to alert
   on it. This is the "data transformation" pillar most workflow tools
   have and single-rule engines don't.

5. **Retry logic and a full execution audit trail.** Action steps can
   be configured with `max_attempts`/`backoff_seconds`; every step
   visited during a run is logged with its status and a snapshot of
   the working data at that point (`ExecutionStepLog`), so you can
   reconstruct exactly which path any given event took through the
   graph, not just whether the workflow "worked."

6. **Two real trigger paths.** `/events` is for manually simulating an
   event from the UI; `/webhooks/{trigger_type}` is a genuine HTTP
   endpoint any external system can POST to, which runs the same
   engine — this is how a real production trigger would arrive.

7. **Natural-language workflow creation.** `app/nl_builder.py` turns a
   plain-English instruction into a runnable workflow graph. If
   `GROQ_API_KEY` is set (Groq is the provider this project is
   configured for by default; Anthropic/OpenAI keys also work if set
   instead), it makes a real LLM call; otherwise it falls back to a
   deterministic keyword parser so the feature and its API shape work
   end-to-end without external credentials. The response always tells
   you which mode ran — this is **not** hidden or oversold as more
   capable than it is.

## Seeded example workflows (`seed_data.py`)

1. **VIP order alert with branching** — a nested `AND(amount>1000, OR(region==Delhi, region==Mumbai))`
   condition branches to a Slack alert on success or a quiet log entry
   on failure.
2. **Enriched customer tier alert** — a TRANSFORM step does a real SQL
   lookup to attach `customer_tier` to the event, a CONDITION checks
   that enriched field, and on success a two-step ACTION chain
   (email → sheet) runs.
3. **Webhook relay for new signups** — uses the real (non-simulated)
   `http` connector to relay every signup to an external URL, with
   retry configured.

## How to run it

```bash
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt

# Terminal 1
uvicorn app.main:app --reload

# Terminal 2
python seed_data.py

# Terminal 3
streamlit run streamlit_app.py
```

Windows users: double-click `run_windows.bat` instead, which handles
all three steps automatically. Mac/Linux: `./run_mac_linux.sh`.

### Try the branching logic

In the **Simulate Event** tab, send `trigger_type=new_order` with:
```json
{"name": "Aashir", "region": "Delhi", "amount": 1500, "customer_id": "CUST001"}
```
Then check the **Execution Audit Trail** tab — you'll see the VIP
workflow took the Slack-alert branch, and the enrichment workflow
looked up `CUST001` (seeded as gold-tier), passed the condition, and
ran both the email and sheet actions. Change `amount` to `200` or the
`customer_id` to `CUST002` (silver-tier) and re-run to see the *other*
branch get taken instead — same workflow, different path.

### Try the natural-language builder

In the **Build from English** tab, try:
> "When a new order over 2000 comes in from Bangalore, post it to #alerts and log it"

Without a `GROQ_API_KEY` set, this runs through the deterministic
fallback parser — check the response's `parse_mode` field. Setting a
real key (`export GROQ_API_KEY=...` before starting the backend)
switches this to genuine LLM-based parsing (Groq's `llama-3.3-70b-versatile`),
which handles far more varied phrasing than the fallback's keyword
matching.

### Try the real webhook endpoint

```bash
curl -X POST http://localhost:8000/webhooks/new_order \
  -H "Content-Type: application/json" \
  -d '{"name": "ExternalTest", "region": "Delhi", "amount": 3000, "customer_id": "CUST003"}'
```
This is a genuine HTTP endpoint, not a simulation — any real system
could call this the same way.

## Going live: real Slack, WhatsApp, email, Sheets, Calendar

Every connector runs in simulated mode (clearly labeled `[SIMULATED]`
in logs) until you provide real credentials — no connector silently
pretends to be real. **See `SETUP_CHECKLIST.md`** for exact steps to
get free accounts for Slack, Twilio (WhatsApp), Gmail (email), and
Google Cloud (Sheets/Calendar), then paste the resulting keys into the
**🔐 Credentials tab** in the running app. Credentials are encrypted at
rest (`app/credentials.py`, Fernet symmetric encryption) — set
`CREDENTIAL_ENCRYPTION_KEY` (see the checklist) so saved credentials
survive a restart.

## Cross-event rules: aggregate-state tracking

Beyond judging one event in isolation, a condition can also check
patterns across past events — e.g. "this customer has placed 5+ orders
in the last hour" — via `app/aggregate_state.py`. A condition rule can
include an `"aggregate"` leaf instead of a plain field check:

```json
{"aggregate": {"trigger_type": "new_order", "group_by_field": "customer_id",
                "window_minutes": 60, "operator": ">=", "value": "5"}}
```

This queries the real `event_log` table (every event is already stored
permanently) rather than a separate counter that could drift out of
sync with what actually happened.

## Analytics dashboard

The **📈 Analytics tab** computes real aggregate metrics directly from
the execution logs — total runs, failure rate, most-triggered
workflows, failures broken down by connector, and average steps per
run. Nothing here is a separate/simulated number; it's the same data
visible in the Execution Audit Trail, just aggregated.

## Known limitations (stated honestly, not hidden)

- The visual builder is JSON-based, not drag-and-drop — building a
  true node-graph editor is a significant frontend project on its own
  and out of scope here; the JSON shown is exactly what the engine
  executes, so it's an honest "advanced mode" rather than a simplified
  stand-in.
- The natural-language fallback parser (no LLM key) only recognizes a
  specific, limited set of phrasings — it is explicitly a fallback,
  not a claim of full natural-language understanding.
- The Twilio WhatsApp connector uses Twilio's free sandbox, which only
  sends to numbers that have explicitly joined it (fine for a demo,
  not for arbitrary real customers — that requires a paid WhatsApp
  Business setup with Meta).
- The credential encryption key, if not set as a real environment
  variable, is regenerated randomly each process restart — credentials
  saved in a previous run become unreadable (a clear warning is printed
  when this happens; see `SETUP_CHECKLIST.md` step 0 to avoid it).
- The graph walker has a hard step-count ceiling (`MAX_GRAPH_STEPS`) to
  guard against a misconfigured cyclic graph; there's no cycle
  *detection* beyond that ceiling.
- Aggregate-state queries scan recent `event_log` rows and parse each
  one's JSON payload in Python rather than querying inside SQL — fine
  at small-business scale, but wouldn't scale to high-volume production
  traffic without indexing payload fields properly.
