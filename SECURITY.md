# Security Policy — Maven (CMO Agent)

Maven is the CMO of the OASIS AI C-Suite — it drafts content, manages
advertising budgets, publishes to social platforms, and runs the content
pipeline. Maven holds keys to ad accounts (Meta Ads, Google Ads), social
publishers (LinkedIn, Instagram, TikTok, X), and scheduling platforms
(Late / Zernio). Misuse of any of these can burn ad spend, damage brand
reputation, or publish content the customer never approved.

## Reporting a Vulnerability

**Do not open a public GitHub issue for a security vulnerability.**

Please email **security@oasisai.work** (preferred) or
**conaugh@oasisai.work** (fallback) with:

- A description of the issue
- Steps to reproduce (or a proof-of-concept)
- The affected version or commit SHA
- Your assessment of impact

**Response SLA**

| Stage | Target |
|-------|--------|
| Initial acknowledgement | within 48 hours |
| Severity triage | within 5 business days |
| Fix in `main` for critical/high | within 14 days |
| Coordinated public disclosure | 90 days from report, or sooner if a fix ships |

We will credit you in the fix commit and changelog unless you ask to stay
anonymous.

## Supported Versions

Only the latest commit on `main` is actively maintained. Forks and older
tags are not patched. If you are running a pinned commit older than 30
days, pull `main` before reporting — the issue may already be fixed.

## Security Posture

Maven is installed through the OASIS AI setup wizard
(`github.com/CC90210/CEO-Agent`). The wizard enforces the shared
credential posture:

### Credential handling

- All secrets live in a single `.env.agents` file per install — never
  in source, never in git history, never in CI logs.
- `.env.agents` is in `.gitignore` and `.git/info/exclude`; the setup
  wizard refuses to write to any `.env*` path that is tracked by git.
- On POSIX the file is `chmod 0600` (owner read/write only). On Windows,
  NTFS ACLs inherit from the user home directory.
- Ad-platform tokens (Meta long-lived tokens, Google Ads OAuth refresh
  tokens) are validated live at wizard time and stored only in the
  `.env.agents` file.

### Secret scanning

- The OASIS AI wizard ships `scripts/scan_secrets.py`, which runs over
  the working tree + git history. It specifically detects Facebook
  long-lived tokens (`EAA…`) after a 2026-04 incident where a Meta
  token briefly leaked to a public repo — Maven's credential surface
  is now the most hardened part of the scanner.
- A hardened `.gitignore` blocks `*.env*`, `*_token.txt`,
  `credentials.json`, `service_account.json`, `*.pem`, `*.key`, SSH
  keys, and MCP config files that might contain API keys.
- If a secret is ever committed by accident, rotate the credential
  first and rewrite history second (`git filter-repo`) — never in the
  other order.

### Outbound content controls

- All content publishing goes through an adversarial draft critic
  (`draft_critic`) before it touches a real platform. The critic can
  hard-block a post it judges off-brand, ungrounded, or risky.
- Daily and hourly publishing caps are enforced per platform. These are
  not suggestions; the scheduler refuses to exceed them.
- Ad-budget changes require an explicit daily ceiling env variable per
  account. Maven will not raise a daily cap beyond what the user
  configured at wizard time without a new interactive approval.

### Safety hooks

- `.claude/settings.local.json` registers hooks that block destructive
  shell commands and block any edit that would touch a `.env*` file.
- Every ad-spend change is logged to an append-only audit log.

## Scope for this Agent (Maven / CMO)

Maven is the **content, ads, and brand** agent of the C-Suite. By design
it can:

- Draft and schedule content across connected platforms (LinkedIn,
  Instagram, TikTok, X, YouTube, Skool)
- Read and propose changes to ad campaigns on Meta Ads and Google Ads
  up to the per-account daily ceiling set at install time
- Generate video and image assets via the content pipeline (Remotion,
  FFmpeg, ElevenLabs, Whisper) stored in `data/content/`
- Maintain a brand-voice and content-strategy knowledge base for its
  clients
- Publish aggregate pulse metrics to `data/pulse/cmo_pulse.json` for
  cross-agent awareness

Maven **cannot**, by policy:

- Raise a per-account ad-spend ceiling without a fresh interactive
  approval — the wizard-time ceiling is a hard cap
- Send outbound emails or direct messages — Bravo owns outbound via
  `send_gateway.py` with CASL compliance
- Access banking or tax records — those belong to Atlas
- Trigger physical devices — Aura's domain, with its own approval flow
- Publish on behalf of a brand it has not been explicitly configured
  for via the wizard's per-client routing

## Out of Scope

This policy covers Maven's own code and the install path. It does **not**
cover:

- Platform-policy violations caused by the content the customer wrote
  (FTC disclosure rules, platform community guidelines, etc.)
- Ad-account access a customer has granted to a third party outside of
  the wizard install
- The user's own machine hygiene (disk encryption, OS patches, password
  managers)
- Vulnerabilities in upstream dependencies — tracked via GitHub
  Dependabot and patched in regular releases

## Coordinated Disclosure

Please give us a reasonable window to fix before public disclosure.
90 days is the default; we will ship a fix faster if we can and will
request an extension only for genuinely complex issues with clear
communication.

Thank you for helping keep our agents safe for the businesses that
depend on them.
