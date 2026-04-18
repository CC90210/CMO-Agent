# SKILL: Browser Automation

> Playwright-based fallback for operations not supported by APIs.

---

## When to Use Browser Automation
1. API operation not available (rare edge cases)
2. Visual verification of live ads
3. Competitor ad research
4. Landing page testing/screenshots
5. Platform UI-only features (some Google Ads settings)

## Tools (via Playwright MCP)
- `browser_navigate` — Go to URL
- `browser_snapshot` — Get page accessibility tree
- `browser_click` — Click element
- `browser_fill_form` — Fill form fields
- `browser_type` — Type text
- `browser_take_screenshot` — Capture screenshot
- `browser_evaluate` — Run JavaScript
- `browser_wait_for` — Wait for element/condition

## Common Automation Tasks

### Check Live Ad Appearance
1. Navigate to Google search with target keyword
2. Take screenshot of SERP
3. Verify ad appears and looks correct

### Competitor Research
1. Navigate to Facebook Ad Library
2. Search for competitor by name
3. Snapshot their active ads
4. Note copy, creative, and targeting approach

### Landing Page Verification
1. Navigate to landing page URL
2. Verify page loads correctly
3. Check for MCA disclosures and compliance
4. Test form submission (staging only)
5. Take screenshot for documentation

## Rules
1. Browser automation is a FALLBACK — prefer API calls
2. Never use browser automation for operations available via API
3. Always handle login/auth carefully (don't store passwords in scripts)
4. Rate limit browser actions (don't overload platforms)
5. Use for read operations primarily (research, verification)
