# Setup Checklist - Making Every Connector Genuinely Live

Every connector runs in **simulated mode** (clearly labeled `[SIMULATED]`
in logs) until its credentials are configured via the **Credentials** page.

## 0. Encryption key (do this first)

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Paste the output into `.env` as `CREDENTIAL_ENCRYPTION_KEY`.

## 1. Slack (~2 minutes, free)

1. https://api.slack.com/apps → Create New App → From scratch
2. Incoming Webhooks → toggle On → Add New Webhook to Workspace → pick a channel
3. Copy the URL, paste it into the Credentials page as `SLACK_WEBHOOK_URL`

## 2. WhatsApp via Twilio (~5 minutes, free trial)

1. Sign up at https://www.twilio.com/try-twilio
2. Messaging → Try it out → Send a WhatsApp message → follow the "join <word>" instructions from your own WhatsApp
3. Copy Account SID and Auth Token from the console
4. Save `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` (e.g. `whatsapp:+14155238886`)

## 3. Email via Gmail SMTP (~5 minutes, free)

1. Enable 2-Step Verification: https://myaccount.google.com/security
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Save `EMAIL_SMTP_USER` (your Gmail address) and `EMAIL_SMTP_PASSWORD` (the app password)

## 4. Google Sheets + Calendar (~15-20 minutes, free)

1. https://console.cloud.google.com → new project → enable Google Sheets API + Google Calendar API
2. APIs & Services → Credentials → Create Service Account → Keys → Add Key → JSON
3. Paste the entire JSON file contents as `GOOGLE_SERVICE_ACCOUNT_JSON`
4. Share your target Sheet/Calendar with the service account's email (found inside the JSON)

## Verifying it worked

Trigger a workflow using the connector, then check **Execution audit trail**.
A real success has no `[SIMULATED]` tag; a real failure shows a genuine
error from that service — expected and correct, not a bug.
