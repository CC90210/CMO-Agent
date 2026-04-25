<#
.SYNOPSIS
  Maven (CMO-Agent) quickstart for Windows PowerShell.

.DESCRIPTION
  Usage:
    irm https://raw.githubusercontent.com/CC90210/CMO-Agent/main/install/quickstart.ps1 | iex

  Maven ships through the unified OASIS AI Agent Factory installer hosted
  in CC90210/CEO-Agent. This shim just preselects the `maven` profile so
  the user lands directly in Maven's wizard with no extra clicks.

  When piped through iex, positional flags get lost, so we set
  $env:OASIS_PROFILE before invoking the upstream irm|iex.
#>

param(
    [switch]$AutoInstall,
    [switch]$NoAutoInstall
)

$ErrorActionPreference = 'Stop'

$Remote  = 'https://raw.githubusercontent.com/CC90210/CEO-Agent/main/install/quickstart.ps1'
$Profile = 'maven'

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

Write-Host "Maven (CMO Agent) - fetching unified installer" -ForegroundColor Magenta
Write-Host "  source: $Remote"  -ForegroundColor DarkGray
Write-Host "  profile: maven (Brand - Content - Ads - Funnels - Growth)" -ForegroundColor DarkGray
Write-Host ""

if ($AutoInstall)   { $env:OASIS_AUTO_INSTALL    = '1' }
if ($NoAutoInstall) { $env:OASIS_NO_AUTO_INSTALL = '1' }
$env:OASIS_PROFILE = $Profile

Invoke-RestMethod -Uri $Remote | Invoke-Expression
