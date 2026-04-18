"""
Generate Google Ads OAuth token JSON for the cohnen/mcp-google-ads server.

The cohnen server (vendor/mcp-google-ads/google_ads_server.py) expects a
GOOGLE_ADS_CREDENTIALS_PATH pointing to a JSON file in the
google.oauth2.credentials.Credentials authorized_user format.

This script reads OAuth credentials from .env.agents, writes the token JSON
to vendor/mcp-google-ads/google_ads_token.json, then exits. Run it once
before starting the Google Ads MCP server.

Usage:
    python scripts/generate_google_ads_token.py
"""

import json
import os
import sys
from pathlib import Path

# Resolve project root relative to this file
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env.agents"
TOKEN_OUT = PROJECT_ROOT / "vendor" / "mcp-google-ads" / "google_ads_token.json"


def load_env_agents() -> dict[str, str]:
    """Parse .env.agents into a dict, skipping comments and blanks."""
    env: dict[str, str] = {}
    with open(ENV_FILE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()
    return env


def main() -> None:
    if not ENV_FILE.exists():
        print(f"ERROR: .env.agents not found at {ENV_FILE}", file=sys.stderr)
        sys.exit(1)

    env = load_env_agents()

    required_keys = [
        "GOOGLE_ADS_CLIENT_ID",
        "GOOGLE_ADS_CLIENT_SECRET",
        "GOOGLE_ADS_REFRESH_TOKEN",
    ]
    missing = [k for k in required_keys if not env.get(k) or env[k].startswith("INSERT_")]
    if missing:
        print(
            "Google Ads credentials not yet configured in .env.agents.\n"
            f"Missing or placeholder values: {', '.join(missing)}\n"
            "Add real credentials to .env.agents and re-run this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    # google.oauth2.credentials.Credentials authorized_user JSON format
    token_data = {
        "token": None,
        "refresh_token": env["GOOGLE_ADS_REFRESH_TOKEN"],
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": env["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": env["GOOGLE_ADS_CLIENT_SECRET"],
        "scopes": ["https://www.googleapis.com/auth/adwords"],
    }

    TOKEN_OUT.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_OUT.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    print(f"Token JSON written to {TOKEN_OUT}")


if __name__ == "__main__":
    main()
