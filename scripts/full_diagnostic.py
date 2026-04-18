"""Full diagnostic — SunBiz Meta Ads health check."""
import sys
import json
import requests
from datetime import datetime

sys.path.insert(0, "scripts")
from meta_ads_engine import MetaAdsEngine

engine = MetaAdsEngine()
token = engine.token

# Fetch campaigns dynamically
_campaigns = engine.get_all_campaigns()
CAMPAIGN_IDS = {c["id"]: c["name"] for c in _campaigns}
if not CAMPAIGN_IDS:
    print("  ERROR: No campaigns found in ad account.")
    sys.exit(1)

print("=" * 60)
print("  FULL DIAGNOSTIC — SUNBIZ META ADS")
print("  " + datetime.now().strftime("%Y-%m-%d %H:%M"))
print("=" * 60)

# 1. TOKEN HEALTH
print("\n--- 1. TOKEN HEALTH ---")
r = requests.get("https://graph.facebook.com/v21.0/me", params={"access_token": token, "fields": "id,name"})
if r.status_code == 200:
    print("  Token: VALID")
    print("  User: " + r.json().get("name", "?"))
else:
    print("  TOKEN EXPIRED: " + str(r.status_code))

r2 = requests.get("https://graph.facebook.com/v21.0/debug_token", params={"input_token": token, "access_token": token})
td = r2.json().get("data", {})
expires = td.get("expires_at", 0)
if expires:
    exp_dt = datetime.fromtimestamp(expires)
    days_left = (exp_dt - datetime.now()).days
    print("  Expires: " + str(exp_dt) + " (" + str(days_left) + " days left)")
    if days_left < 7:
        print("  WARNING: Token expires soon!")

# 2. AD ACCOUNT STATUS
print("\n--- 2. AD ACCOUNT STATUS ---")
r3 = requests.get("https://graph.facebook.com/v21.0/" + engine.ad_account_id, params={
    "access_token": token,
    "fields": "name,account_status,disable_reason,amount_spent,balance,currency,spend_cap,funding_source_details"
})
acct = r3.json()
status_map = {1: "ACTIVE", 2: "DISABLED", 3: "UNSETTLED", 7: "PENDING_RISK_REVIEW", 8: "PENDING_SETTLEMENT", 9: "IN_GRACE_PERIOD", 100: "PENDING_CLOSURE", 101: "CLOSED"}
acct_status = status_map.get(acct.get("account_status", 0), str(acct.get("account_status", "?")))
print("  Account: " + acct.get("name", "?"))
print("  Status: " + acct_status)
disable = acct.get("disable_reason", 0)
if disable and disable != 0:
    print("  DISABLE REASON: " + str(disable))
balance = acct.get("balance", "0")
print("  Balance: $" + str(int(balance) / 100))
amt = acct.get("amount_spent", "0")
print("  Lifetime Spend: $" + str(int(amt) / 100))
spend_cap = acct.get("spend_cap", "0")
if spend_cap and spend_cap != "0":
    print("  Spend Cap: $" + str(int(spend_cap) / 100))
else:
    print("  Spend Cap: None")
funding = acct.get("funding_source_details", {})
if funding:
    print("  Payment: " + str(funding.get("display_string", "?")))

# 3. AD STATUS & POLICY
print("\n--- 3. AD STATUS & POLICY CHECK ---")
r4 = requests.get("https://graph.facebook.com/v21.0/" + engine.ad_account_id + "/ads", params={
    "access_token": token,
    "fields": "id,name,effective_status,ad_review_feedback",
    "limit": 50
})
ads = r4.json().get("data", [])
disapproved = 0
active = 0
paused = 0
for ad in ads:
    status = ad.get("effective_status", "?")
    if status == "DISAPPROVED":
        disapproved += 1
        print("  DISAPPROVED: " + ad.get("name", "?"))
        fb = ad.get("ad_review_feedback", {})
        if fb:
            print("    Reason: " + json.dumps(fb))
    elif status == "ACTIVE":
        active += 1
    elif status == "PAUSED":
        paused += 1
print("  Active: " + str(active) + " | Paused: " + str(paused) + " | Disapproved: " + str(disapproved))
if disapproved == 0:
    print("  All ads passed Meta policy review.")

# 4. DELIVERY CHECK
print("\n--- 4. DELIVERY CHECK (today) ---")
for cid, cname in CAMPAIGN_IDS.items():
    r = requests.get("https://graph.facebook.com/v21.0/" + cid + "/insights", params={
        "access_token": token,
        "fields": "spend,impressions,clicks,actions",
        "date_preset": "today"
    })
    d = r.json().get("data", [])
    if d:
        row = d[0]
        spend = row.get("spend", "0")
        imps = row.get("impressions", "0")
        link_clicks = "0"
        for a in row.get("actions", []):
            if a["action_type"] == "link_click":
                link_clicks = a["value"]
        flag = "DELIVERING" if float(spend) > 0 else "NOT DELIVERING"
        print("  " + cname + ": " + flag + " | $" + spend + " today | " + imps + " imps | " + link_clicks + " link clicks")
    else:
        print("  " + cname + ": NOT DELIVERING (no data today)")

# 5. CLICK QUALITY / FRAUD DETECTION
print("\n--- 5. CLICK QUALITY & FRAUD DETECTION ---")
for cid, cname in CAMPAIGN_IDS.items():
    r = requests.get("https://graph.facebook.com/v21.0/" + cid + "/insights", params={
        "access_token": token,
        "fields": "spend,clicks,unique_clicks,inline_link_clicks,unique_inline_link_clicks,frequency,reach,impressions",
        "date_preset": "maximum"
    })
    d = r.json().get("data", [])
    if d:
        row = d[0]
        total_clicks = int(row.get("clicks", 0))
        unique_clicks = int(row.get("unique_clicks", 0))
        link_clicks = int(row.get("inline_link_clicks", 0))
        unique_link = int(row.get("unique_inline_link_clicks", 0))
        freq = float(row.get("frequency", 0))

        repeat_rate = ((total_clicks - unique_clicks) / total_clicks * 100) if total_clicks > 0 else 0
        link_repeat = ((link_clicks - unique_link) / link_clicks * 100) if link_clicks > 0 else 0

        print("  " + cname + ":")
        print("    Clicks: " + str(total_clicks) + " total / " + str(unique_clicks) + " unique (" + str(round(repeat_rate, 1)) + "% repeat)")
        print("    Link clicks: " + str(link_clicks) + " total / " + str(unique_link) + " unique (" + str(round(link_repeat, 1)) + "% repeat)")
        print("    Frequency: " + str(round(freq, 2)))

        flags = []
        if repeat_rate > 30:
            flags.append("HIGH REPEAT CLICKS")
        if link_repeat > 25:
            flags.append("HIGH REPEAT LINK CLICKS")
        if freq > 3:
            flags.append("AD FATIGUE (freq > 3)")
        if flags:
            print("    FLAGS: " + ", ".join(flags))
        else:
            print("    Status: CLEAN")

# 6. PLACEMENT VERIFICATION
print("\n--- 6. PLACEMENT VERIFICATION ---")
r = requests.get("https://graph.facebook.com/v21.0/" + engine.ad_account_id + "/insights", params={
    "access_token": token,
    "fields": "spend,impressions,clicks",
    "date_preset": "maximum",
    "breakdowns": "publisher_platform,platform_position"
})
for row in r.json().get("data", []):
    plat = row.get("publisher_platform", "?")
    pos = row.get("platform_position", "?")
    spend = row.get("spend", "0")
    imps = row.get("impressions", "0")
    clicks = row.get("clicks", "0")
    print("  " + plat + "/" + pos + ": $" + spend + " | " + imps + " imps | " + clicks + " clicks")

# 7. DEVICE BREAKDOWN
print("\n--- 7. DEVICE BREAKDOWN ---")
r2 = requests.get("https://graph.facebook.com/v21.0/" + engine.ad_account_id + "/insights", params={
    "access_token": token,
    "fields": "spend,impressions,clicks,actions",
    "date_preset": "maximum",
    "breakdowns": "device_platform"
})
for row in r2.json().get("data", []):
    device = row.get("device_platform", "?")
    spend = row.get("spend", "0")
    imps = row.get("impressions", "0")
    link_clicks = "0"
    for a in row.get("actions", []):
        if a["action_type"] == "link_click":
            link_clicks = a["value"]
    print("  " + device + ": $" + spend + " | " + imps + " imps | " + link_clicks + " link clicks")

# 8. COST BENCHMARKING
print("\n--- 8. COST BENCHMARKING vs INDUSTRY ---")
r = requests.get("https://graph.facebook.com/v21.0/" + engine.ad_account_id + "/insights", params={
    "access_token": token,
    "fields": "spend,cpc,cpm,ctr,actions,cost_per_action_type,frequency",
    "date_preset": "maximum"
})
d = r.json().get("data", [{}])[0]
cpc = float(d.get("cpc", 0))
cpm = float(d.get("cpm", 0))
ctr = float(d.get("ctr", 0))
cost_link = 0
for a in d.get("cost_per_action_type", []):
    if a["action_type"] == "link_click":
        cost_link = float(a["value"])

print("  YOUR METRICS         vs  INDUSTRY AVG (Financial Services)")
print("  CPC:       $" + str(round(cpc, 2)).ljust(8) + "       $1.00-3.00")
print("  Cost/Link: $" + str(round(cost_link, 2)).ljust(8) + "       $1.50-4.00")
print("  CPM:       $" + str(round(cpm, 2)).ljust(8) + "       $15.00-25.00")
print("  CTR:       " + str(round(ctr, 2)).ljust(8) + "%      0.50-1.50%")

print()
if cpc < 1.0:
    print("  CPC: A+ (well below industry avg)")
if cpm < 15.0:
    print("  CPM: A+ (well below industry avg)")
if ctr > 2.0:
    print("  CTR: A+ (far above industry avg)")
if cost_link < 1.0:
    print("  Cost/Link: A+ (exceptional)")

# 9. BUDGET PACING
print("\n--- 9. BUDGET PACING ---")
for cid, cname in CAMPAIGN_IDS.items():
    r2 = requests.get("https://graph.facebook.com/v21.0/" + cid + "/adsets", params={
        "access_token": token,
        "fields": "lifetime_budget,budget_remaining,start_time,end_time"
    })
    adsets = r2.json().get("data", [])
    r3 = requests.get("https://graph.facebook.com/v21.0/" + cid + "/insights", params={
        "access_token": token, "fields": "spend", "date_preset": "maximum"
    })
    ci = r3.json().get("data", [{}])
    camp_spend = float(ci[0].get("spend", 0)) if ci else 0

    if adsets:
        a = adsets[0]
        lb = int(a.get("lifetime_budget", 0)) / 100
        br = int(a.get("budget_remaining", 0)) / 100
        start = a.get("start_time", "")[:10]
        end = a.get("end_time", "")[:10]

        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        now = datetime.now()
        total_days = (end_dt - start_dt).days
        elapsed_days = (now - start_dt).days
        remaining_days = max((end_dt - now).days, 0)

        pct_time = (elapsed_days / total_days * 100) if total_days > 0 else 0
        pct_budget = ((lb - br) / lb * 100) if lb > 0 else 0

        if pct_budget > pct_time + 15:
            pace = "OVERSPENDING"
        elif pct_budget < pct_time - 15:
            pace = "UNDERSPENDING"
        else:
            pace = "ON TRACK"

        print("  " + cname + ":")
        print("    $" + str(round(camp_spend, 2)) + " of $" + str(lb) + " spent (" + str(round(pct_budget, 1)) + "%)")
        print("    " + str(elapsed_days) + " of " + str(total_days) + " days elapsed (" + str(round(pct_time, 1)) + "%)")
        print("    " + str(remaining_days) + " days left | Pacing: " + pace)

# 10. DEMOGRAPHIC EFFICIENCY
print("\n--- 10. DEMOGRAPHIC SPEND ---")
r = requests.get("https://graph.facebook.com/v21.0/" + engine.ad_account_id + "/insights", params={
    "access_token": token,
    "fields": "spend,impressions,clicks,actions,cpc,ctr",
    "date_preset": "maximum",
    "breakdowns": "age,gender"
})
demo_data = r.json().get("data", [])
print("  Age/Gender       | Spend     | Clicks | Link Clicks | CPC    | CTR")
print("  " + "-" * 70)
total_65_spend = 0.0
total_all_spend = 0.0
for row in demo_data:
    age = row.get("age", "?")
    gender = row.get("gender", "?")
    spend = row.get("spend", "0")
    clicks = row.get("clicks", "0")
    cpc_val = row.get("cpc", "0")
    ctr_val = row.get("ctr", "0")
    link_clicks = "0"
    for a in row.get("actions", []):
        if a["action_type"] == "link_click":
            link_clicks = a["value"]
    g = gender[0].upper() if gender != "unknown" else "U"
    label = g + " " + age
    print("  " + label.ljust(18) + " | $" + str(spend).ljust(8) + " | " + str(clicks).ljust(6) + " | " + str(link_clicks).ljust(11) + " | $" + str(round(float(cpc_val), 2)).ljust(5) + " | " + str(round(float(ctr_val), 1)) + "%")

    s = float(spend)
    total_all_spend += s
    if age == "65+":
        total_65_spend += s

if total_all_spend > 0:
    pct_65 = round(total_65_spend / total_all_spend * 100, 1)
    print("\n  65+ demographic: $" + str(round(total_65_spend, 2)) + " (" + str(pct_65) + "% of total spend)")
    if pct_65 > 40:
        print("  WARNING: Heavy 65+ skew. Consider narrowing age to 25-54.")

print("\n" + "=" * 60)
print("  DIAGNOSTIC COMPLETE")
print("=" * 60)
