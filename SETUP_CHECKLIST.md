# Setup Checklist - Making Every Connector Genuinely Live

Every connector runs in **simulated mode** (clearly labeled `[SIMULATED]`
in logs) until its credentials are configured. Nothing pretends to be
real once you add a credential - if a saved credential is wrong or a
service is unreachable, the connector will report a genuine error
instead of silently faking success.

Set credentials via the **🔐 Credentials tab** in the Streamlit UI
(preferred - encrypted storage, no code editing) or as environment
variables of the same name before starting the backend.

---

## 0. Encryption key (do this first, takes 30 seconds)

Without this, any credentials you save will stop working the next time
you restart the app (a fresh random key gets generated each run).

The first time you run `run_windows.bat` (or `run_mac_linux.sh`), it
automatically creates a `.env` file for you (copied from `.env.example`)
if one doesn't already exist. Open that `.env` file and fill in:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Paste the output as the value for `CREDENTIAL_ENCRYPTION_KEY` in `.env`.

**Important:** `.env` is listed in `.gitignore` and will never be
committed to git — this is where your real secrets belong. Only
`.env.example` (with blank placeholder values) is meant to be shared
or pushed to a public repository.

---

## 1. Slack (~2 minutes, free)

1. Go to https://api.slack.com/apps
2. **Create New App** → **From scratch** → name it anything → pick your workspace
3. Left sidebar → **Incoming Webhooks** → toggle **On**
4. **Add New Webhook to Workspace** → pick a channel → **Allow**
5. Copy the URL (`https://hooks.slack.com/services/...`)
6. Paste it into the Credentials tab as `SLACK_WEBHOOK_URL`

---

## 2. WhatsApp via Twilio (~5 minutes, free trial, no business verification)

1. Sign up free at https://www.twilio.com/try-twilio
2. In the console, go to **Messaging** → **Try it out** → **Send a WhatsApp message**
3. Follow the on-screen instructions to send `join <your-sandbox-word>` from your own WhatsApp to the given number - this links your phone to the sandbox
4. From the main console dashboard, copy your **Account SID** and **Auth Token**
5. In the Credentials tab, set:
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_WHATSAPP_FROM` → the sandbox number shown, formatted as `whatsapp:+14155238886`
6. When sending a WhatsApp action in a workflow, the `to` param must be your own linked number, e.g. `whatsapp:+91XXXXXXXXXX`

Note: Twilio's sandbox only sends to numbers that have joined it (i.e., your own, for testing). Moving beyond sandbox to arbitrary numbers requires a paid Twilio WhatsApp Business setup - out of scope for a demo project.

---

## 3. Email via Gmail SMTP (~5 minutes, free)

1. Enable 2-Step Verification on your Google account (required): https://myaccount.google.com/security
2. Generate an App Password: https://myaccount.google.com/apppasswords
   (choose "Mail" as the app - Google gives you a 16-character password)
3. In the Credentials tab, set:
   - `EMAIL_SMTP_USER` → your full Gmail address
   - `EMAIL_SMTP_PASSWORD` → the 16-character app password (NOT your real Gmail password)
   - `EMAIL_SMTP_HOST` is optional (defaults to `smtp.gmail.com`)

---

## 4. Google Sheets + Calendar (~15-20 minutes, free, the fiddliest one)

1. Go to https://console.cloud.google.com → create a new project (free)
2. In the project, go to **APIs & Services → Library** → enable:
   - **Google Sheets API**
   - **Google Calendar API**
3. Go to **APIs & Services → Credentials** → **Create Credentials** → **Service Account**
4. Give it any name → Create → skip the optional permission steps → Done
5. Click into the new service account → **Keys** tab → **Add Key** → **Create new key** → **JSON** → download it
6. Open the downloaded JSON file in a text editor, copy its **entire contents**
7. In the Credentials tab, paste the whole JSON as the value for `GOOGLE_SERVICE_ACCOUNT_JSON`

**For Sheets:** open your target Google Sheet → **Share** → paste the service account's email (found inside the JSON file, looks like `xxx@xxx.iam.gserviceaccount.com`) → give it **Editor** access. When configuring a Sheets action in a workflow, use the Sheet's ID (the long string in its URL between `/d/` and `/edit`).

**For Calendar:** open Google Calendar → target calendar's **Settings** → **Share with specific people** → paste the same service account email → **Make changes to events**. Use the Calendar ID from **Settings → Integrate calendar**.

---

## What each connector does once configured

| Connector | Simulated behavior (no credential) | Real behavior (credential set) |
|---|---|---|
| Slack | Writes `[SIMULATED]` log line | Posts to your actual Slack channel |
| WhatsApp | Writes `[SIMULATED]` log line | Sends a real WhatsApp message via Twilio |
| Email | Writes `[SIMULATED]` log line | Sends a real email via SMTP |
| Google Sheets | Writes to local `workflow_sheet.csv` | Appends a row to your actual Google Sheet |
| Google Calendar | Writes `[SIMULATED]` log line | Creates a real event on your actual calendar |
| HTTP | N/A - always real | Always makes a genuine outbound request |
| SQL Lookup | N/A - always real | Always queries the real local database |

---

## Verifying it actually worked

After setting a credential and triggering a workflow that uses it, check
the **Execution Audit Trail** tab. A real success looks like a normal
completion message (no `[SIMULATED]` tag). A real failure (e.g., a typo
in a webhook URL) will show a genuine error message from that service -
this is expected and correct behavior, not a bug.
