# Maven Install Chain

Maven (the CMO Agent) ships through the **unified OASIS AI Agent Factory installer** hosted in [CC90210/CEO-Agent](https://github.com/CC90210/CEO-Agent). The two scripts in this folder are thin shims that preselect `--profile maven` so users land directly in Maven's wizard.

## One-Line Install

**macOS / Linux / WSL:**
```bash
curl -sSL https://raw.githubusercontent.com/CC90210/CMO-Agent/main/install/quickstart.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/CC90210/CMO-Agent/main/install/quickstart.ps1 | iex
```

## What Happens

1. The shim prints "Maven — fetching unified installer" and forwards to `CEO-Agent/install/quickstart.{sh,ps1}` with `--profile maven` preselected.
2. The unified installer auto-detects + installs missing prereqs (python ≥3.10, git, node, npm) via Homebrew / apt / dnf / pacman / zypper / winget after one consent prompt.
3. It clones `CC90210/CMO-Agent` into `~/maven-repo` (or `$MAVEN_REPO_DIR` if set).
4. It launches the wizard at `bravo_cli/wizard.py`. Because `--profile maven` is preselected, the wizard skips the picker and asks Maven-specific questions: brand voice, primary platform, posting frequency, content types, primary CTA — plus required Anthropic key and optional OpenAI, Google AI, Telegram, Stripe, Meta Ads, Google Ads, Late/Zernio, LinkedIn, X.
5. Final step: `bravo doctor` runs to confirm everything is wired.

## Why a Shim Instead of a Forked Installer

The Bravo wizard is **multi-profile aware** — every C-Suite agent (Bravo, Atlas, Maven, Aura, Hermes) is a first-class profile with its own metadata, env-var prefix (`MAVEN_*`), service prompts, and repo target. Forking the install chain per agent would multiply maintenance burden 5x. The shim approach keeps one installer, one wizard, one set of fixes.

## Manual / Non-Interactive

```bash
# Skip consent prompts (CI / scripted installs):
OASIS_AUTO_INSTALL=1 curl -sSL https://raw.githubusercontent.com/CC90210/CMO-Agent/main/install/quickstart.sh | bash

# Custom clone destination:
MAVEN_REPO_DIR=$HOME/cmo-agent BRAVO_REPO_DIR=$HOME/.bravo-launcher \
  curl -sSL https://raw.githubusercontent.com/CC90210/CMO-Agent/main/install/quickstart.sh | bash
```

## Environment Variables

| Var | Purpose |
|-----|---------|
| `OASIS_PROFILE` | Pre-selected profile (set to `maven` by the shim — override only if you know why) |
| `OASIS_AUTO_INSTALL` | `1` skips consent prompts |
| `OASIS_NO_AUTO_INSTALL` | `1` keeps the old "tell me what's missing" behavior |
| `MAVEN_REPO_DIR` | Where to clone `CMO-Agent` (default: `~/maven-repo`) |
| `BRAVO_REPO_DIR` | Where to drop the launcher copy of `CEO-Agent` (default: `~/bravo-repo`) |

## What Gets Installed Beyond the Common Path

Maven has **heavier deps than Atlas** because it renders video and runs paid ads:

- `npm install` for Remotion 4.x (already in `package.json`)
- `pip install -r requirements.txt` for Meta Ads SDK + Google Ads SDK + ElevenLabs voiceover client
- `ad-engine/` sidecar gets its own `npm install` after the main repo installs
- The wizard offers (but doesn't force) Meta Ads + Google Ads keys; you can connect them later via `bravo config`

## Troubleshooting

- **`npm install` errors on Remotion** → open a new terminal so the new Node LTS is on PATH; if still broken, `cd ad-engine && npm install --legacy-peer-deps`.
- **"python3 not found after install"** → open a new terminal so the freshly-installed binary is on PATH, then re-run.
- **Microsoft Store `python.exe` stub** (Windows) → the installer detects + rejects the stub, then installs `Python.Python.3.12` via winget.
- **Failed clone** → the installer retries via atomic swap; the broken directory is preserved at `<repo-dir>.broken.<timestamp>` for inspection.
