@echo off
REM Meta Ads MCP Wrapper — Reads credentials from .env.agents and launches MCP server
REM Server: pipeboard-co/meta-ads-mcp (installed via uvx)
REM Credentials: sourced from .env.agents at project root

REM Resolve project root (one level up from this script)
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM Parse .env.agents for Meta credentials
for /f "usebackq tokens=1,* delims==" %%A in ("%PROJECT_ROOT%\.env.agents") do (
    if "%%A"=="META_ACCESS_TOKEN"  set META_ACCESS_TOKEN=%%B
    if "%%A"=="META_APP_ID"        set META_APP_ID=%%B
    if "%%A"=="META_APP_SECRET"    set META_APP_SECRET=%%B
    if "%%A"=="META_AD_ACCOUNT_ID" set META_AD_ACCOUNT_ID=%%B
)

REM Launch the Meta Ads MCP server via uvx (pipeboard-co/meta-ads-mcp)
uvx meta-ads-mcp
