# Low-Code Workflow Automation Engine (React frontend)

A working, multi-layer automation engine in the spirit of Zapier / n8n /
UnifyApps' iPaaS layer: a user (or a plain-English instruction) defines a
**trigger → branching conditions → data enrichment → connector actions**
graph, and the engine executes it — with a full audit trail of exactly
which path was taken and why.

This version replaces the project's original Streamlit frontend with a
**real React application** (Vite + plain React, no UI framework), calling
the same FastAPI backend over a REST API with CORS enabled. The backend
architecture (branching graph engine, connectors, credentials, analytics)
is unchanged from the project's v2 design — only the frontend changed.

**Publishing this repo publicly?** All secrets load from a local `.env`
file, gitignored and never committed — `.env.example` is the only version
meant to be pushed.

## Architecture

```
┌─────────────────────┐        ┌──────────────────────────────┐
│  React (Vite) SPA    │─HTTP──▶│  FastAPI backend               │
│  8 pages: NL builder,│  CORS  │  - workflow CRUD (graph-aware) │
│  JSON builder,       │        │  - /webhooks/{trigger} (real   │
│  workflows, simulate,│        │    external ingestion)         │
│  audit trail,        │        │  - /events (manual simulation) │
│  reference data,     │        └──────────┬────────────────────┘
│  credentials,        │                   │
│  analytics           │        ┌──────────▼────────────────────┐
└─────────────────────┘        │  engine.py - graph walker      │
                                 │  branching, retries, full      │
                                 │  execution audit logging       │
                                 └──────────┬────────────────────┘
                                            │
                        ┌───────────────────┼───────────────────┐
                        ▼                   ▼                   ▼
                conditions.py         transform.py        connectors/*.py
                nested AND/OR         field derivation +   log, email, slack,
                rule groups           connector-based       whatsapp, sheet,
                                      enrichment lookups     http, sql_lookup,
                                                              google_sheets/cal
```

## What's in the backend (unchanged from the project's v2 design)

- Branching workflow graphs (condition steps have separate success/failure paths)
- Nested AND/OR conditions, evaluated recursively
- 9 pluggable connectors — `log`, `sheet` (local-file), `slack`, `email`,
  `whatsapp`, `google_sheets`, `google_calendar`, `http`, `sql_lookup` — all
  attempt real API calls once credentials are configured, falling back to a
  clearly labeled `[SIMULATED]` log entry otherwise
- Real data enrichment via TRANSFORM steps (e.g. looking up a customer's
  tier from a database mid-workflow)
- Retry logic and a full execution audit trail (every step, every branch
  decision, logged)
- Two trigger paths: `/events` (manual simulation) and
  `/webhooks/{trigger_type}` (a real HTTP endpoint any external system can call)
- Natural-language workflow creation via Groq's LLM API, with a
  deterministic keyword-based fallback when no key is configured
- Cross-event rules (aggregate-state tracking) — e.g. "5+ orders in an hour"
- Encrypted credential storage (Fernet symmetric encryption)

See `SETUP_CHECKLIST.md` for exact steps to get free accounts for Slack,
Twilio (WhatsApp), Gmail (email), and Google Cloud (Sheets/Calendar).

## What's in the frontend

Eight pages, each calling the backend directly via `fetch` (see `frontend/src/api.js`):

1. **Build from English** — type a plain-English instruction, get a working workflow
2. **Advanced builder** — the raw JSON graph shape, for full control
3. **Workflows** — list, inspect, toggle, delete
4. **Simulate event** — manually fire a test event
5. **Execution audit trail** — pick a run, see the exact step-by-step trace
6. **Reference data** — manage the customer lookup table used by enrichment
7. **Credentials** — paste real API keys, encrypted at rest
8. **Analytics** — real aggregate metrics computed from execution logs

No UI framework (Tailwind/MUI/etc.) — plain CSS with a small set of design
tokens (`frontend/src/styles.css`), a dark technical theme suited to the
tool's actual purpose rather than a generic dashboard template.

## How to run it

**Two services need to run at once: the FastAPI backend and the React dev server.**

```bash
# Terminal 1 — backend
python -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload

# Terminal 2 — seed example workflows (one-time)
source venv/bin/activate
python seed_data.py

# Terminal 3 — frontend
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173`. The React dev server proxies API calls
to `http://localhost:8000` (see `frontend/src/api.js` — `API_URL` constant).

Windows users: double-click `run_windows.bat`, which handles all of the
above automatically (and creates `.env` for you on first run).
Mac/Linux: `./run_mac_linux.sh`.

### Building the frontend for production

```bash
cd frontend
npm run build
```
Outputs a static build to `frontend/dist/` — deployable to any static host
(Vercel, Netlify, S3, etc.), as long as it can reach your backend's URL
(update `API_URL` in `frontend/src/api.js` accordingly before building).

### Try the branching logic

In **Simulate event**, send `trigger_type=new_order` with:
```json
{"name": "Aashir", "region": "Delhi", "amount": 1500, "customer_id": "CUST001"}
```
Then check **Execution audit trail** — you'll see the VIP workflow took the
Slack-alert branch, and the enrichment workflow looked up `CUST001`
(seeded as gold-tier), passed its condition, and ran the email action.
Change `amount` to `200` or `customer_id` to `CUST002` (silver-tier) to see
the *other* branch get taken — same workflow, different path.

### Try the natural-language builder

In **Build from English**, try:
> "When a new order over 2000 comes in from Bangalore, post it to #alerts and log it"

Without `GROQ_API_KEY` set, this runs through the deterministic fallback
parser — the response shows a `fallback parser` badge rather than `real LLM`.

## Known limitations (stated honestly)

- The frontend has no build-time environment config for the backend URL —
  `API_URL` in `frontend/src/api.js` is a hardcoded constant. Fine for local
  development; a real deployment would use an environment variable instead.
- No client-side routing library — page switching is done with local React
  state in `App.jsx`, not React Router. Fine for a single-page tool with 8
  flat sections; would need revisiting for deep-linkable URLs.
- No authentication on either the API or the frontend — anyone who can
  reach the backend's URL can read/write everything. Fine for local use or
  a demo; not production-ready as-is.
- The Twilio WhatsApp connector uses Twilio's free sandbox, which only
  sends to numbers that have explicitly joined it.
- The credential encryption key, if not set in `.env`, is regenerated
  randomly each backend restart — credentials saved in a previous run
  become unreadable (a warning is printed when this happens).
