# SKILL: Email Outbound (Gmail Blast System)

> Send production-grade HTML email campaigns for SunBiz Funding via Gmail SMTP — bulk sending, personalization, tracking, CAN-SPAM compliance.

---

## Overview
Full email blast system using Gmail SMTP with App Passwords. Sends personalized HTML emails to CSV-based prospect lists at scale with rate limiting, unsubscribe management, campaign tracking, and CAN-SPAM compliance. Every email drives to the JotForm: `https://form.jotform.com/253155026259254`

## Setup
```bash
pip install python-dotenv
```
Add to `.env.agents`:
```
GMAIL_ADDRESS=your_gmail@gmail.com
GMAIL_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
```
**Get App Password:** Google Account → Security → 2-Step Verification (must be ON) → App Passwords → Generate for "Mail"

## Architecture

### System Components
```
scripts/email_blast.py          — Core send engine (SMTP, rate limiting, logging)
templates/email/*.html          — HTML email templates (Jinja2-style tokens)
data/email_lists/*.csv          — Recipient lists (CSV format)
data/email_lists/unsubscribes.csv — Global unsubscribe list
data/email_logs/*.csv           — Per-campaign send logs
```

### Send Pipeline
```
1. Load recipient CSV → validate emails → filter unsubscribes
2. Load HTML template → resolve personalization tokens
3. For each recipient:
   a. Personalize HTML ({{first_name}}, {{business_name}}, etc.)
   b. Send via Gmail SMTP (TLS on port 587)
   c. Log result (success/failure + timestamp)
   d. Rate limit delay (configurable)
4. Generate campaign summary stats
5. Save log to data/email_logs/
```

### Rate Limiting Strategy
- **Gmail (personal):** 500 emails/day limit
- **Google Workspace:** 2,000 emails/day limit
- **Default throttle:** 20 emails/second max, 1-second delay between batches
- **Batch size:** 50 emails per batch, 5-second delay between batches
- **Retry:** Exponential backoff (2s, 4s, 8s, 16s) for transient failures
- **Circuit breaker:** Stop campaign if >10% failure rate in last 50 sends

## Email Templates

### Available Templates

| Template | File | Use Case |
|----------|------|----------|
| `sunbiz_funding` | `templates/email/sunbiz_funding.html` | Growth capital outreach — funding grid, weekly payments |
| `consolidation_blast` | `templates/email/consolidation_blast.html` | MCA consolidation — before/after, pain points |

### Personalization Tokens
| Token | Source | Example |
|-------|--------|---------|
| `{{first_name}}` | CSV column | "John" |
| `{{last_name}}` | CSV column | "Smith" |
| `{{business_name}}` | CSV column | "Smith Construction" |
| `{{monthly_revenue}}` | CSV column | "$85,000" |
| `{{funding_amount}}` | CSV column | "$50,000" |
| `{{unsubscribe_url}}` | Auto-generated | Unsubscribe link |
| `{{tracking_pixel}}` | Auto-generated | 1x1 open tracking pixel |
| `{{campaign_id}}` | Auto-generated | Unique campaign identifier |

### CSV Format
```csv
email,first_name,last_name,business_name,monthly_revenue,funding_amount
john@example.com,John,Smith,Smith Construction,85000,50000
jane@example.com,Jane,Doe,Doe Catering,120000,75000
```

## Usage

### Full Campaign
```python
from scripts.email_blast import send_campaign

results = send_campaign(
    template_name="sunbiz_funding",
    recipient_csv="data/email_lists/prospects_march.csv",
    campaign_name="march_growth_blast",
    subject="You Qualify for Business Funding — SunBiz Funding",
    from_name="SunBiz Funding",
    dry_run=False,
)
```

### Dry Run (Test Without Sending)
```python
results = send_campaign(
    template_name="sunbiz_funding",
    recipient_csv="data/email_lists/prospects.csv",
    campaign_name="test_run",
    dry_run=True,  # Logs everything but doesn't send
)
```

### Single Test Email
```python
from scripts.email_blast import send_single_email

send_single_email(
    to_email="your@email.com",
    subject="Test — SunBiz Funding",
    html_body="<h1>Test</h1>",
    from_name="SunBiz Funding",
)
```

### Check Campaign Stats
```python
from scripts.email_blast import get_campaign_stats

stats = get_campaign_stats("march_growth_blast")
print(f"Sent: {stats['sent']}, Failed: {stats['failed']}")
```

### Manage Unsubscribes
```python
from scripts.email_blast import add_unsubscribe, check_unsubscribe

add_unsubscribe("user@example.com")
is_unsub = check_unsubscribe("user@example.com")  # True
```

## CAN-SPAM Compliance (MANDATORY)

Every email MUST include:
1. **Clear sender identification:** "SunBiz Funding" in From name
2. **Accurate subject line:** No deceptive or misleading subjects
3. **Physical address:** Business mailing address in footer
4. **Unsubscribe mechanism:** Working unsubscribe link in every email
5. **Honor unsubscribes:** Process within 10 business days
6. **No purchased lists without consent:** Only email prospects with prior business relationship or opt-in

### MCA Language Rules
- NEVER: "loan", "lender", "interest rate", "guaranteed approval"
- ALWAYS: "advance", "funding", "capital", "factor rate", "see if you qualify"

## Monitoring & Alerts
- Campaign logs saved to `data/email_logs/[campaign_id].csv`
- Each row: timestamp, recipient, status (sent/failed/skipped), error message
- Summary stats: total, sent, failed, skipped (unsubscribed), duration
- If failure rate >10%, campaign auto-pauses with alert

## Security
- Gmail App Password stored in `.env.agents` (NEVER hardcode)
- `.env.agents` is in `.gitignore`
- Recipient CSVs with real data are gitignored
- Only `sample_recipients.csv` committed for testing
- Unsubscribe list persists across campaigns
