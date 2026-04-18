# SKILL: Lead Generation Funnel (SunBiz Funding)

> End-to-end lead capture system — from ad click to qualified MCA merchant.

---

## Overview
This skill covers the complete lead generation funnel for SunBiz Funding's MCA consolidation and business funding services. The goal is to capture qualified merchant leads through the JotForm and route them to underwriting as efficiently as possible.

## Lead Funnel Architecture

```
IMPRESSION (see ad)
    ↓
CLICK (interested — goes to JotForm)
    ↓
JOTFORM SUBMISSION (lead captured) ← Primary conversion event
    ↓
QUALIFICATION (underwriting team reviews bank statements)
    ↓
FOLLOW-UP (call/SMS within 5-15 minutes)
    ↓
FUNDED DEAL (revenue)
```

**CRITICAL:** ALL ad CTAs link to the JotForm. This is the single lead capture destination.

## JotForm Integration

### Setup
- **JotForm URL:** https://form.jotform.com/253155026259254
- All ads use this link as CTA destination
- Track with UTM parameters: `?utm_source=meta&utm_medium=paid&utm_campaign=[name]&utm_content=[ad_id]`
- JotForm contains the qualification questions — no separate landing page needed

### Required Lead Data (per SOP)
The JotForm must capture:
1. **Average Monthly Revenue** (CRUCIAL — must be >$15K, ideally >$25K)
2. **Number of Current MCA Positions** (0, 1-2, 3-5, 5+)
3. **Time in Business (TIB)**
4. Full Name
5. Email
6. Phone
7. Business Name

## Two Lead Capture Approaches

### Option A: JotForm Direct (PRIMARY — All Campaigns)
- User clicks ad CTA → lands on JotForm
- JotForm handles all qualification questions
- Simplest flow, single conversion point
- Track via UTM parameters

### Option B: Meta Lead Form (BACKUP — For Testing)
If testing in-platform forms for comparison:

```python
# Meta Lead Form for MCA Consolidation
lead_form = page.create_lead_gen_form(params={
    'name': 'SunBiz Funding - MCA Consolidation',
    'privacy_policy': {'url': 'https://sunbizfunding.com/privacy'},
    'context_card': {
        'title': 'See If You Qualify',
        'content': 'Find out if you can consolidate your MCA positions and reduce your daily payments. Takes 30 seconds.',
    },
    'questions': [
        {'type': 'CUSTOM', 'key': 'monthly_revenue', 'label': 'Average Monthly Revenue',
         'options': [
             {'value': 'Under $15K'},
             {'value': '$15K - $25K'},
             {'value': '$25K - $50K'},
             {'value': '$50K - $100K'},
             {'value': '$100K - $250K'},
             {'value': '$250K - $500K'},
             {'value': '$500K+'},
         ]},
        {'type': 'CUSTOM', 'key': 'mca_positions', 'label': 'Current MCA Positions',
         'options': [
             {'value': '0 - No current positions'},
             {'value': '1-2 positions'},
             {'value': '3-5 positions'},
             {'value': '5+ positions'},
         ]},
        {'type': 'CUSTOM', 'key': 'time_in_business', 'label': 'Time in Business',
         'options': [
             {'value': 'Less than 6 months'},
             {'value': '6-12 months'},
             {'value': '1-2 years'},
             {'value': '2-5 years'},
             {'value': '5+ years'},
         ]},
        {'type': 'BUSINESS_NAME'},
        {'type': 'FULL_NAME'},
        {'type': 'EMAIL'},
        {'type': 'PHONE'},
    ],
    'thank_you_page': {
        'title': 'Thank You!',
        'body': 'A SunBiz Funding capital specialist will contact you within 1 business hour to discuss your options.',
        'button_text': 'Visit Our Website',
        'url': 'https://sunbizfunding.com',
    },
    'form_type': 'HIGHER_INTENT',  # Adds review step — critical for lead quality
})
```

**Use "Higher Intent" form type** — adds a review step where merchants confirm info before submitting. Fewer leads but significantly higher quality.

## Lead Quality Scoring (MCA-Specific)

### Scoring Matrix
| Criteria | Points | Reasoning |
|----------|--------|-----------|
| Revenue $100K+/mo | +30 | Premium merchant, large deal |
| Revenue $50K-$100K/mo | +25 | Strong candidate |
| Revenue $25K-$50K/mo | +15 | Meets minimum ICP |
| Revenue $15K-$25K/mo | +5 | Borderline |
| Revenue <$15K/mo | -10 | Below minimum — likely disqualify |
| 2-5 MCA positions | +25 | Primary ICP — consolidation |
| 0-1 MCA positions | +20 | Secondary ICP — growth capital |
| 5+ MCA positions | +10 | Complex — possible death spiral |
| TIB 2+ years | +15 | Established |
| TIB 1-2 years | +10 | Meets minimum |
| TIB <1 year | 0 | Risky |
| Phone provided | +10 | Reachable |

### Score Tiers
- **70+ = HOT** → Call within 15 minutes (speed-to-lead wins deals)
- **50-69 = WARM** → Call within 1 hour
- **30-49 = COOL** → Call within 4 hours
- **<30 = COLD** → Email/SMS nurture sequence only

### Auto-Disqualify
- Revenue under $15K/month
- Chronic NSFs (>7) if detectable
- Death Spiral indicators (>45% leverage + declining revenue)
- Restricted industries per campaign (Trucking, Staffing, Auto — varies by funder)

## Post-Submission Automation (Speed-to-Lead = #1 Factor)

### Immediate (0-60 seconds)
1. **Instant SMS:** "Hi [Name], thanks for your interest in SunBiz Funding! A capital specialist will call you within the hour. Reply STOP to opt out."
2. **Instant email:** Branded confirmation with what to expect
3. **Notify underwriting team** via Slack/email/CRM
4. **Score the lead** automatically based on form data

### Follow-Up Sequence
| Day | Action | Channel |
|-----|--------|---------|
| Day 0 | Instant confirmation + specialist call within 15 min (HOT) or 1 hour (WARM) | SMS + Phone |
| Day 1 | "Here's what we found" — educational email about consolidation | Email |
| Day 2 | Follow-up call if not connected | Phone |
| Day 3 | Case study email: "How we took a business from 4 positions to 1" | Email |
| Day 5 | "Still interested? Your options are waiting." | SMS |
| Day 7 | Final direct outreach | Phone + SMS |
| Day 14+ | Weekly nurture — educational content, industry insights | Email |

### SMS vs Email (Research Data)
- **SMS-only nurturing delivers 7x more appointments than email-only**
- SMS open rate: 98% vs email 20%
- Use SMS for speed and urgency, email for detailed content
- TCPA compliance required: explicit SMS consent, opt-out in every message

## Tracking & Attribution

### UTM Structure
```
?utm_source=meta
&utm_medium=paid
&utm_campaign=sunbiz_consolidation_q1
&utm_content=before_after_v1
&utm_term=overleveraged
```

### Key Metrics
| Metric | Formula | Target |
|--------|---------|--------|
| CPL (Cost Per Lead) | Ad Spend / Leads | <$50 |
| CPQL (Cost Per Qualified Lead) | Ad Spend / Qualified Leads | <$100 |
| Lead-to-Qualification Rate | Qualified / Total Leads | >30% |
| Lead-to-Fund Rate | Funded / Total Leads | >5% |
| Speed-to-Contact | Time from submission to first call | <15 min (HOT) |

### Conversion Tracking
**Meta Pixel:**
- Track: Lead event on JotForm submission (via JotForm webhook or thank-you page pixel)
- Track: PageView on any SunBiz pages
- Use UTM parameters for campaign attribution

**Offline Conversions:**
- Import funded deal data back to Meta for optimization
- This lets Meta's algorithm find more people like your funded merchants

## Compliance for Lead Gen
1. Privacy policy MUST be linked in all forms
2. Cannot pre-check opt-in boxes
3. Must clearly state how data will be used
4. Cannot sell lead data without explicit consent
5. Follow CAN-SPAM for email follow-ups
6. Follow TCPA for SMS: explicit consent, opt-out in every message
7. MCA products are NOT loans — forms and follow-ups must use correct terminology
