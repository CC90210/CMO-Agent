# Maven — Install Guide

## Quick Start (Recommended)

```bash
python scripts/setup_wizard.py
```

The wizard collects your operator profile interactively and writes `brain/operator.profile.json` (gitignored — local only). It then calls `personalize` and `scaffold` automatically.

## Manual Flow

### 1. Clone

```bash
git clone https://github.com/CC90210/CMO-Agent.git my-maven
cd my-maven
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Node dependencies (for Remotion video pipeline)

```bash
npm install
cd ad-engine && npm install && cd ..
```

### 4. Configure credentials

```bash
cp .env.agents.template .env.agents
# Edit .env.agents — add Anthropic key, Meta/Google Ads keys, ElevenLabs, Zernio, etc.
```

### 5. Personalize

```bash
# Check if already personalized:
python scripts/personalize.py check --json

# Apply operator profile to brain/USER.md and memory files:
python scripts/personalize.py apply
```

### 6. (Fork only) Token-replace CC's identifiers

Only run this if you forked the repo for a new operator. It rewrites CC's name/brand across all tracked files.

```bash
# Preview what would change:
python scripts/scaffold.py --json

# Apply after reviewing:
python scripts/scaffold.py --apply --backup
```

## Verification

```bash
python scripts/personalize.py check --json   # should show "personalized": true
python scripts/scaffold.py --json            # should refuse with safety guard (CC's repo)
```

## Runtimes

Maven supports three AI runtimes — all read the same `brain/` and `skills/`:

| Runtime | Entry point |
|---------|-------------|
| Claude Code | `CLAUDE.md` |
| Gemini CLI | `GEMINI.md` |
| Antigravity IDE | `ANTIGRAVITY.md` |
