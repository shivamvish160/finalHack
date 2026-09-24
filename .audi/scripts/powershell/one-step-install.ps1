#!/usr/bin/env pwsh

[CmdletBinding()]
param(
	[string]$RepoUrl = "https://gitlab.int.bell.ca/DCX/Services/audi-specflow.git",
	[string]$Version,
	[switch]$Latest,
	[string]$ProjectName,
	[switch]$Here,
	[string]$Ai = "copilot",
	[ValidateSet("ps", "sh")]
	[string]$ScriptType = "ps",
	[switch]$IgnoreAgentTools,
	[switch]$SkipTls,
	[switch]$Offline,
	[switch]$NoGit,
	[string]$Proxy,
	[switch]$UseDefaultProxyCredentials,
	[string]$IndexUrl,
	[string]$ExtraIndexUrl
)

$ErrorActionPreference = 'Stop'
if ($PSVersionTable.PSVersion.Major -ge 7) {
	$PSNativeCommandUseErrorActionPreference = $true
}

$recommendedProxy = "http://fastweb.int.bell.ca:8083"

<#
.SYNOPSIS
	One-step installer for AUDI CLI on Windows/PowerShell.

.DESCRIPTION
	Installs/updates AUDI CLI from the configured GitLab repository, runs `audi check`,
	and can optionally initialize a project.

	Prerequisites:
	- Python 3.11+ must be installed and available in PATH.
	- uv is optional; this script installs uv automatically when missing.

	If both Python and uv are missing, install Python first, then rerun this script.

.EXAMPLE
	.\one-step-install.ps1

.EXAMPLE
	.\one-step-install.ps1 -ProjectName my-app -Ai copilot -ScriptType ps

.EXAMPLE
	.\one-step-install.ps1 -Here -IgnoreAgentTools
#>

function Write-Info {
	param([string]$Message)
	Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Ok {
	param([string]$Message)
	Write-Host "[OK]   $Message" -ForegroundColor Green
}

function Write-WarnMsg {
	param([string]$Message)
	Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Show-InstallTroubleshooting {
	param([string]$ErrorText)

	Write-Host ""
	Write-WarnMsg "Install appears to have failed due to network/package index access."
	if (-not [string]::IsNullOrWhiteSpace($ErrorText)) {
		Write-WarnMsg "Error summary: $ErrorText"
	}

	Write-Host "Try one of the following:" -ForegroundColor Yellow

	if ([string]::IsNullOrWhiteSpace($Proxy) -and [string]::IsNullOrWhiteSpace($env:HTTPS_PROXY) -and [string]::IsNullOrWhiteSpace($env:HTTP_PROXY)) {
		Write-Host "  1) Retry with Bell proxy:" -ForegroundColor Yellow
		Write-Host "     .\scripts\powershell\one-step-install.ps1 -Proxy $recommendedProxy -UseDefaultProxyCredentials" -ForegroundColor Gray
	}
	else {
		Write-Host "  1) Confirm proxy credentials/access are valid." -ForegroundColor Yellow
	}

	Write-Host "  2) Retry with your internal Python package mirror:" -ForegroundColor Yellow
	Write-Host "     .\scripts\powershell\one-step-install.ps1 -IndexUrl <YOUR_INTERNAL_SIMPLE_INDEX_URL>" -ForegroundColor Gray

	Write-Host "  3) If internet access is blocked, use enterprise offline install steps:" -ForegroundColor Yellow
	Write-Host "     docs/installation.md#enterprise--air-gapped-installation" -ForegroundColor Gray
	Write-Host ""
}

function Show-VersionTroubleshooting {
	param([string]$ErrorText)

	Write-Host ""
	Write-WarnMsg "Install failed while resolving a Git ref (tag/branch/commit)."
	if (-not [string]::IsNullOrWhiteSpace($ErrorText)) {
		Write-WarnMsg "Error summary: $ErrorText"
	}

	Write-Host "A Git tag (for example, v0.6.1) is just a named pointer to a specific commit." -ForegroundColor Yellow
	Write-Host "If that tag does not exist in the remote/mirror, installation with -Version fails." -ForegroundColor Yellow

	Write-Host "Try one of the following:" -ForegroundColor Yellow
	Write-Host "  1) Install latest from default branch:" -ForegroundColor Yellow
	Write-Host "     .\scripts\powershell\one-step-install.ps1 -Latest" -ForegroundColor Gray
	Write-Host "  2) Install from an existing release tag:" -ForegroundColor Yellow
	Write-Host "     .\scripts\powershell\one-step-install.ps1 -Version v<existing-tag>" -ForegroundColor Gray
	Write-Host ""
}

$script:WebRequestSplat = @{}

function Test-CommandExists {
	param([Parameter(Mandatory = $true)][string]$CommandName)
	return [bool](Get-Command $CommandName -ErrorAction SilentlyContinue)
}

function Install-Uv {
	Write-Info "'uv' was not found. Installing uv..."
	try {
		$installer = Invoke-RestMethod -Uri "https://astral.sh/uv/install.ps1" @script:WebRequestSplat
		Invoke-Expression $installer
	}
	catch {
		throw "Failed to install uv automatically. Install manually: https://docs.astral.sh/uv/getting-started/installation/"
	}

	# Ensure uv install location is available in current session
	$uvBin = Join-Path $HOME ".local\bin"
	if ((Test-Path $uvBin) -and ($env:Path -notlike "*$uvBin*")) {
		$env:Path = "$uvBin;$env:Path"
	}

	if (-not (Test-CommandExists "uv")) {
		throw "uv installation completed, but 'uv' is still not available in PATH for this session. Open a new terminal and rerun."
	}

	Write-Ok "uv installed successfully."
}

Write-Info "Starting one-step AUDI CLI installation..."

if (-not [string]::IsNullOrWhiteSpace($Proxy)) {
	Write-Info "Using explicit proxy: $Proxy"
	$env:HTTPS_PROXY = $Proxy
	$env:HTTP_PROXY = $Proxy
	$env:ALL_PROXY = $Proxy
	$script:WebRequestSplat["Proxy"] = $Proxy

	if ($UseDefaultProxyCredentials) {
		$script:WebRequestSplat["ProxyUseDefaultCredentials"] = $true
		Write-Info "Proxy default credentials are enabled for web requests."
	}
}
elseif (-not [string]::IsNullOrWhiteSpace($env:HTTPS_PROXY) -or -not [string]::IsNullOrWhiteSpace($env:HTTP_PROXY)) {
	Write-Info "Proxy detected from environment variables (HTTPS_PROXY/HTTP_PROXY)."
}

if (-not [string]::IsNullOrWhiteSpace($IndexUrl)) {
	Write-Info "Using custom package index: $IndexUrl"
	$env:UV_INDEX_URL = $IndexUrl
	$env:PIP_INDEX_URL = $IndexUrl
}

if (-not [string]::IsNullOrWhiteSpace($ExtraIndexUrl)) {
	Write-Info "Using extra package index: $ExtraIndexUrl"
	$env:UV_EXTRA_INDEX_URL = $ExtraIndexUrl
	$env:PIP_EXTRA_INDEX_URL = $ExtraIndexUrl
}

if (-not (Test-CommandExists "python")) {
		throw @"
Python 3.11+ is required but 'python' is not available in PATH.

Install Python first, then rerun this script.

Windows quick install options:
	winget install Python.Python.3.11
or
	https://www.python.org/downloads/
"@
}

if (-not (Test-CommandExists "uv")) {
	Install-Uv
}
else {
	Write-Ok "uv is already installed."
}

$sourceSpec = if ($Latest -or [string]::IsNullOrWhiteSpace($Version)) {
	"git+$RepoUrl"
}
else {
	"git+$RepoUrl@$Version"
}

if ($Latest -or [string]::IsNullOrWhiteSpace($Version)) {
	Write-Info "Version pin not provided; installing latest from repository default branch."
}
else {
	Write-Info "Version pin requested: $Version"
}

Write-Info "Installing AUDI CLI from: $sourceSpec"
try {
	uv tool install audi-cli --force --from $sourceSpec
}
catch {
	$installError = $_.Exception.Message
	if ($installError -match "pypi\.org|failed to fetch|proxy|timed out|timeout|name or service not known|could not resolve|connection") {
		Show-InstallTroubleshooting -ErrorText $installError
	}
	if ($installError -match "couldn't find remote ref|did not match any file\(s\) known to git|unknown revision|invalid object name|not a valid object name|reference is not a tree") {
		Show-VersionTroubleshooting -ErrorText $installError
	}
	throw
}
Write-Ok "AUDI CLI installed/updated."

Write-Info "Running 'audi check'..."
audi check
Write-Ok "AUDI CLI is ready."

$shouldInit = $Here -or -not [string]::IsNullOrWhiteSpace($ProjectName)
if ($shouldInit) {
	$initArgs = @("init")

	if ($Here) {
		$initArgs += "--here"
	}
	else {
		$initArgs += $ProjectName
	}

	if (-not [string]::IsNullOrWhiteSpace($Ai)) {
		$initArgs += @("--ai", $Ai)
	}

	if (-not [string]::IsNullOrWhiteSpace($ScriptType)) {
		$initArgs += @("--script", $ScriptType)
	}

	if ($IgnoreAgentTools) { $initArgs += "--ignore-agent-tools" }
	if ($SkipTls) { $initArgs += "--skip-tls" }
	if ($Offline) { $initArgs += "--offline" }
	if ($NoGit) { $initArgs += "--no-git" }

	Write-Info "Initializing project..."
	audi @initArgs
	Write-Ok "Project initialization completed."
}
else {
	Write-WarnMsg "Installation complete. To initialize a project in one step, run this script with -ProjectName <name> or -Here."
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
