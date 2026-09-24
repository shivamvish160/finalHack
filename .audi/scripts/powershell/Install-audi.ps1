param(
    [string]$TargetFolder,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path

$localVenvDir = Join-Path $scriptDir '.venv'
$localPython = Join-Path $localVenvDir 'Scripts\python.exe'
$localAudi = Join-Path $localVenvDir 'Scripts\audi.exe'
$packageDir = Join-Path $scriptDir 'Package'

$installedAudiCmd = Get-Command audi -ErrorAction SilentlyContinue
$venvAudi = $null

# Use the OS certificate store for uv network calls (common on managed
# Windows machines with enterprise CAs).
if (-not $env:UV_SYSTEM_CERTS) {
    $env:UV_SYSTEM_CERTS = '1'
}

# Load connection settings from the user's persisted environment variables so
# the orchestrator's integrations can reach the configured instances. The
# User-scoped (persisted) value takes precedence; if it is not set, any
# process-scoped value already present in this session is kept as a fallback.
$jiraUrlUser = [Environment]::GetEnvironmentVariable('SPECKIT_JIRA_CONNECTION_URL','User')
if (-not [string]::IsNullOrWhiteSpace($jiraUrlUser)) {
    $env:SPECKIT_JIRA_CONNECTION_URL = $jiraUrlUser
}
$jiraPatUser = [Environment]::GetEnvironmentVariable('SPECKIT_JIRA_PAT','User')
if (-not [string]::IsNullOrWhiteSpace($jiraPatUser)) {
    $env:SPECKIT_JIRA_PAT = $jiraPatUser
}
$gitlabTokenUser = [Environment]::GetEnvironmentVariable('GITLAB_TOKEN','User')
if (-not [string]::IsNullOrWhiteSpace($gitlabTokenUser)) {
    $env:GITLAB_TOKEN = $gitlabTokenUser
}

function Update-OrchestratorStateMetadata {
    param(
        [string]$SpecsOwnerDir,
        [string]$ProjectName
    )

    if ([string]::IsNullOrWhiteSpace($SpecsOwnerDir) -or [string]::IsNullOrWhiteSpace($ProjectName)) {
        return
    }

    $specsDir = Join-Path $SpecsOwnerDir '.audi\specs'
    if (-not (Test-Path $specsDir -PathType Container)) {
        New-Item -ItemType Directory -Path $specsDir -Force | Out-Null
    }

    $featureSpecDir = Join-Path $specsDir $ProjectName
    if (-not (Test-Path $featureSpecDir -PathType Container)) {
        New-Item -ItemType Directory -Path $featureSpecDir -Force | Out-Null
    }

    $statePath = Join-Path $featureSpecDir 'orchestrator-state.json'
    $templatePath = Join-Path $specsDir 'orchestrator-state.json'
    $state = $null

    if (Test-Path $statePath -PathType Leaf) {
        try {
            $state = Get-Content -Path $statePath -Raw | ConvertFrom-Json
        }
        catch {
            $state = [pscustomobject]@{}
        }
    }
    elseif (Test-Path $templatePath -PathType Leaf) {
        try {
            $state = Get-Content -Path $templatePath -Raw | ConvertFrom-Json
        }
        catch {
            $state = [pscustomobject]@{}
        }
    }
    else {
        $state = [pscustomobject]@{}
    }

    $state | Add-Member -NotePropertyName 'feature_name' -NotePropertyValue $ProjectName -Force
    $state | Add-Member -NotePropertyName 'feature_dir' -NotePropertyValue $featureSpecDir -Force
    $state | Add-Member -NotePropertyName 'branch_name' -NotePropertyValue $ProjectName -Force

    $json = $state | ConvertTo-Json -Depth 30
    $utf8 = [System.Text.Encoding]::UTF8
    $bytes = $utf8.GetBytes($json)
    [System.IO.File]::WriteAllBytes($statePath, $bytes)
}

function Initialize-ProjectSecrets {
    param(
        [string]$SourceEnvPath,
        [string]$ProjectDir
    )

    if ([string]::IsNullOrWhiteSpace($ProjectDir) -or -not (Test-Path $ProjectDir -PathType Container)) {
        return
    }

    # Ensure .gitignore exists and ignores secrets + local skill cache so the
    # copied .env token file can never be committed.
    $gitignorePath = Join-Path $ProjectDir '.gitignore'
    $requiredIgnores = @(
        '# Secrets - never commit',
        '.env',
        '.env.local',
        '.secrets/',
        '',
        '# AUDI local skill cache/state',
        '.audi/skills/skills-config.json',
        '.audi/skills/selected-team.json'
    )

    if (Test-Path $gitignorePath -PathType Leaf) {
        $existing = @(Get-Content -Path $gitignorePath -ErrorAction SilentlyContinue)
        $existingSet = @{}
        foreach ($line in $existing) { $existingSet[$line.Trim()] = $true }
        $toAppend = @()
        foreach ($entry in $requiredIgnores) {
            if ($entry -eq '') { continue }
            if (-not $existingSet.ContainsKey($entry.Trim())) { $toAppend += $entry }
        }
        if ($toAppend.Count -gt 0) {
            Add-Content -Path $gitignorePath -Value ('' + [Environment]::NewLine + ($toAppend -join [Environment]::NewLine))
            Write-Host "Updated .gitignore with secret/skill-cache entries." -ForegroundColor Green
        }
    }
    else {
        Set-Content -Path $gitignorePath -Value ($requiredIgnores -join [Environment]::NewLine) -Encoding UTF8
        $audiVersion = $null
        $pyprojectPath = Join-Path $repoRoot 'pyproject.toml'
        if (Test-Path $pyprojectPath -PathType Leaf) {
            $versionLine = Select-String -Path $pyprojectPath -Pattern '^\s*version\s*=\s*"([^"]+)"' -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($versionLine) { $audiVersion = $versionLine.Matches[0].Groups[1].Value }
        }
        if ($audiVersion) {
            Write-Host "AUDI version: $audiVersion" -ForegroundColor Cyan
        }
        Write-Host "Created .gitignore in project." -ForegroundColor Green
    }

    # Write connection settings (GitLab token + Jira) directly from the user's
    # system environment into the project .env, so no source .env file needs to
    # be present. Existing keys are preserved (never overwritten/duplicated).
    $projectEnv = Join-Path $ProjectDir '.env'
    $existingEnv = @()
    if (Test-Path $projectEnv -PathType Leaf) {
        $existingEnv = @(Get-Content -Path $projectEnv -ErrorAction SilentlyContinue)
    }
    $envSettings = @(
        @{ Key = 'GITLAB_TOKEN';                Value = $env:GITLAB_TOKEN },
        @{ Key = 'SPECKIT_JIRA_CONNECTION_URL'; Value = $env:SPECKIT_JIRA_CONNECTION_URL },
        @{ Key = 'SPECKIT_JIRA_PAT';            Value = $env:SPECKIT_JIRA_PAT }
    )
    foreach ($setting in $envSettings) {
        if ([string]::IsNullOrWhiteSpace($setting.Value)) { continue }
        if ($existingEnv -match ("^{0}=" -f [regex]::Escape($setting.Key))) { continue }
        Add-Content -Path $projectEnv -Value ("{0}={1}" -f $setting.Key, $setting.Value)
        Write-Host ("Added {0} to project .env (from system environment)." -f $setting.Key) -ForegroundColor Green
    }
}

function Ensure-GitSafeDirectory {
    param(
        [string]$ProjectDir
    )

    if ([string]::IsNullOrWhiteSpace($ProjectDir) -or -not (Test-Path $ProjectDir -PathType Container)) {
        return
    }

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        return
    }

    $normalizedDir = [System.IO.Path]::GetFullPath($ProjectDir)
    $alreadySafe = $false

    try {
        $safeDirs = git config --global --get-all safe.directory 2>$null
        if ($LASTEXITCODE -eq 0 -and $safeDirs) {
            foreach ($entry in @($safeDirs)) {
                if ([string]::IsNullOrWhiteSpace($entry)) { continue }
                $entryPath = $entry.Trim()
                if ([System.IO.Path]::IsPathRooted($entryPath)) {
                    $entryPath = [System.IO.Path]::GetFullPath($entryPath)
                }
                if ($entryPath -ieq $normalizedDir) {
                    $alreadySafe = $true
                    break
                }
            }
        }
    }
    catch {
        # If reading safe.directory fails, attempt to add below.
    }

    if (-not $alreadySafe) {
        git config --global --add safe.directory "$normalizedDir" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Added git safe.directory for: $normalizedDir" -ForegroundColor Green
        }
    }
}

if ($installedAudiCmd) {
    Write-Host "Detected existing audi installation." -ForegroundColor Cyan

    # The editable install (`pip install -e .`) is a developer convenience so that
    # local template/source changes are picked up. It needs pip (or python -m pip /
    # uv). On a machine without Python/pip on PATH (e.g. an end user), skip it and
    # just use the existing `audi` as-is instead of failing.
    $pyproject = Join-Path $repoRoot 'pyproject.toml'
    $pipCmd = $null
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $pipCmd = 'uv pip'
    }
    elseif (Get-Command pip -ErrorAction SilentlyContinue) {
        $pipCmd = 'pip'
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $pipCmd = 'python -m pip'
    }
    elseif (Get-Command py -ErrorAction SilentlyContinue) {
        $pipCmd = 'py -m pip'
    }
    elseif (Get-Command uv -ErrorAction SilentlyContinue) {
        $pipCmd = 'uv pip'
    }

    # Detect whether the existing 'audi' came from a `uv tool` install. Those
    # live under a uv tools dir with the launcher shimmed into ~\.local\bin, and
    # have no python.exe beside the executable — so an editable `pip install -e .`
    # can't reach that environment. Upgrade it via `uv tool install` instead.
    $installedAudiPath = if ($installedAudiCmd.Path) { $installedAudiCmd.Path } else { $installedAudiCmd.Definition }
    $isUvTool = (-not [string]::IsNullOrWhiteSpace($installedAudiPath)) -and `
        (($installedAudiPath -like '*\uv\tools\*') -or `
         ($installedAudiPath -like '*\.local\bin\*') -or `
         ($installedAudiPath -like '*/uv/tools/*') -or `
         ($installedAudiPath -like '*/.local/bin/*'))

    if ($isUvTool -and (Get-Command uv -ErrorAction SilentlyContinue)) {
        # Force a fresh build/reinstall of the local audi-cli package (busting
        # only its cache entry) so local source edits are always picked up.
        # Scoped to audi-cli — dependencies stay cached, which matters on
        # offline / TLS-intercepted networks where re-downloading would fail.
        Write-Host "Existing 'audi' is a uv tool install; upgrading via 'uv tool install --force' (fresh audi-cli build)..." -ForegroundColor Cyan
        uv --system-certs tool install $repoRoot --force --reinstall-package audi-cli --refresh-package audi-cli
        if ($LASTEXITCODE -ne 0) {
            Write-Host "uv tool install failed with exit code: $LASTEXITCODE; continuing with existing 'audi' installation." -ForegroundColor Yellow
        }
    }
    elseif ((Test-Path $pyproject) -and $pipCmd) {
        Write-Host "Running editable install from repository root ($pipCmd)..." -ForegroundColor Cyan
        Push-Location $repoRoot
        try {
            if ($pipCmd -eq 'uv pip') {
                $uvPython = $null
                if (Test-Path $localPython) {
                    $uvPython = $localPython
                }
                else {
                    if (-not [string]::IsNullOrWhiteSpace($installedAudiPath)) {
                        $candidatePython = Join-Path (Split-Path -Parent $installedAudiPath) 'python.exe'
                        if (Test-Path $candidatePython -PathType Leaf) {
                            $uvPython = $candidatePython
                        }
                    }
                }

                if ($uvPython) {
                    uv --system-certs pip install --python "$uvPython" -e .
                }
                else {
                    uv --system-certs pip install -e .
                }
            }
            else {
                Invoke-Expression "$pipCmd install -e ."
            }
        }
        finally {
            Pop-Location
        }

        if ($LASTEXITCODE -ne 0) {
            Write-Host "Editable install failed with exit code: $LASTEXITCODE; continuing with existing 'audi' installation." -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "Python/pip not found (or no pyproject.toml at repo root); skipping editable reinstall and using the existing 'audi' on PATH." -ForegroundColor Yellow
    }

    $venvAudi = if ($installedAudiCmd.Path) { $installedAudiCmd.Path } else { $installedAudiCmd.Definition }
}
else {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "'uv' was not found on PATH. Attempting to install it..." -ForegroundColor Cyan
        try {
            Invoke-RestMethod -Uri 'https://astral.sh/uv/install.ps1' | Invoke-Expression
        }
        catch {
            Write-Error "Failed to download/run the uv installer: $($_.Exception.Message)"
            Write-Host "Install uv manually from https://docs.astral.sh/uv/ and retry." -ForegroundColor Yellow
            exit 1
        }

        # The installer adds uv to a user bin dir; make it available in this session.
        $uvBin = Join-Path $env:USERPROFILE '.local\bin'
        if ((Test-Path (Join-Path $uvBin 'uv.exe')) -and ($env:Path -notlike "*$uvBin*")) {
            $env:Path = "$uvBin;$env:Path"
        }

        if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
            Write-Error "'uv' installation completed but 'uv' is still not on PATH. Open a new terminal and retry."
            exit 1
        }
        Write-Host "'uv' installed successfully." -ForegroundColor Green
    }
    else {
        # 'uv' is already present; try to update it to the latest version. This
        # is best-effort: managed/offline environments (or package-manager
        # installs) may block or not support self-update, so failures are
        # non-fatal and the existing 'uv' is used as-is.
        Write-Host "'uv' is already installed; checking for updates..." -ForegroundColor Cyan
        try {
            uv self update
            if ($LASTEXITCODE -eq 0) {
                Write-Host "'uv' is up to date." -ForegroundColor Green
            }
            else {
                Write-Host "Could not update 'uv' (exit code $LASTEXITCODE); continuing with the existing version." -ForegroundColor Yellow
            }
        }
        catch {
            Write-Host "Could not update 'uv' ($($_.Exception.Message)); continuing with the existing version." -ForegroundColor Yellow
        }
    }

    # The bundled offline wheels (pyyaml, rpds_py) are CPython 3.14 (cp314)
    # native builds, so the venv must use Python 3.14 to match them.
    $requiredPython = '3.14'

    # If a venv already exists but isn't Python 3.14 (e.g. a stale 3.12 venv from
    # an earlier failed run), remove it so it gets recreated with the right
    # interpreter. Otherwise the install would target the wrong Python and fail.
    if (Test-Path $localPython) {
        $venvVersion = & $localPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -ne 0 -or ($venvVersion -notmatch '^3\.14')) {
            Write-Host "Existing venv is Python '$venvVersion' (need $requiredPython); recreating..." -ForegroundColor Yellow
            Remove-Item -Recurse -Force $localVenvDir -ErrorAction SilentlyContinue
        }
    }

    if (-not (Test-Path $localPython)) {
        # Check whether a matching Python 3.14 interpreter is already available
        # to uv. If not, install a uv-managed build (no system Python required).
        $havePython314 = $false
        $installedPythons = uv --system-certs python list --only-installed 2>$null
        if ($LASTEXITCODE -eq 0 -and $installedPythons -match 'cpython-3\.14') {
            $havePython314 = $true
        }

        if (-not $havePython314) {
            Write-Host "Python $requiredPython not found; installing a uv-managed build..." -ForegroundColor Cyan
            uv --system-certs python install $requiredPython
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Failed to install Python $requiredPython (uv python install exit code: $LASTEXITCODE)."
                Write-Host "If your network blocks downloads, install CPython $requiredPython manually and retry." -ForegroundColor Yellow
                exit $LASTEXITCODE
            }
        }

        Write-Host "Creating local virtual environment at: $localVenvDir" -ForegroundColor Cyan
        uv --system-certs venv $localVenvDir --python $requiredPython
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to create virtual environment (uv venv exit code: $LASTEXITCODE)."
            exit $LASTEXITCODE
        }
    }

    if (-not (Test-Path $localAudi)) {
        if (-not (Test-Path $packageDir -PathType Container)) {
            Write-Error "Package folder not found: $packageDir"
            exit 1
        }

        $audiWheel = Get-ChildItem -Path $packageDir -Filter 'audi_cli-*-py3-none-any.whl' | Select-Object -First 1
        if (-not $audiWheel) {
            Write-Error "AUDI wheel not found in: $packageDir"
            exit 1
        }

        Write-Host "Installing AUDI CLI into local .venv..." -ForegroundColor Cyan
        uv --system-certs pip install --python $localPython --no-index --find-links $packageDir $audiWheel.FullName
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to install AUDI CLI wheel (uv pip install exit code: $LASTEXITCODE)."
            exit $LASTEXITCODE
        }
    }

    $venvAudi = $localAudi
}

if (-not (Test-Path $venvAudi)) {
    Write-Error "audi executable not found at: $venvAudi"
    Write-Host "Create/install it first:" -ForegroundColor Yellow
    Write-Host "  uv venv .venv"
    Write-Host "  uv pip install --python .venv\Scripts\python.exe --no-index --find-links C:\DCX\audi-specflow\scripts\powershell\Package C:\DCX\audi-specflow\scripts\powershell\Package\audi_cli-1.0.0-py3-none-any.whl"
    exit 1
}

if ([string]::IsNullOrWhiteSpace($TargetFolder)) {
    $runFolder = (Get-Location).Path
} else {
    if (-not (Test-Path $TargetFolder -PathType Container)) {
        New-Item -ItemType Directory -Path $TargetFolder -Force | Out-Null
    }
    $runFolder = (Resolve-Path -Path $TargetFolder).Path
}

Push-Location $runFolder
try {
    # Prevent git ownership safety checks from breaking init on Windows folders
    # created or owned by Administrators in enterprise environments.
    Ensure-GitSafeDirectory -ProjectDir $runFolder

    $effectiveArgs = @($ArgsList)
    $resolvedProjectDir = $runFolder
    $resolvedProjectName = Split-Path -Leaf $runFolder

    if ($effectiveArgs -and $effectiveArgs.Count -gt 0 -and $effectiveArgs[0] -eq 'init') {
        $hasHereFlag = $effectiveArgs -contains '--here'
        $hasDotTarget = $effectiveArgs -contains '.'
        $restArgs = @($effectiveArgs | Select-Object -Skip 1)
        $positionalArgs = @($restArgs | Where-Object { $_ -and -not $_.StartsWith('-') })
        $firstProjectArg = if ($positionalArgs.Count -gt 0) { $positionalArgs[0] } else { $null }
        $targetLeafName = Split-Path -Leaf $runFolder
        $projectMatchesTarget = $false
        if ($firstProjectArg) {
            $projectMatchesTarget = ($firstProjectArg -eq $targetLeafName) -or ($firstProjectArg -eq $runFolder)
        }

        # When running init for a target folder, default to in-place initialization.
        if (-not $hasHereFlag -and -not $hasDotTarget -and (($null -eq $firstProjectArg) -or $projectMatchesTarget)) {
            if ($projectMatchesTarget) {
                $restArgs = @($restArgs | Where-Object { $_ -ne $firstProjectArg })
            }
            $effectiveArgs = @('init', '--here') + $restArgs
        }

        $finalHasHereFlag = $effectiveArgs -contains '--here'
        $finalHasDotTarget = $effectiveArgs -contains '.'
        $finalRestArgs = @($effectiveArgs | Select-Object -Skip 1)
        $finalPositionalArgs = @($finalRestArgs | Where-Object { $_ -and -not $_.StartsWith('-') })
        $finalProjectArg = if ($finalPositionalArgs.Count -gt 0) { $finalPositionalArgs[0] } else { $null }

        if ($finalHasHereFlag -or $finalHasDotTarget -or [string]::IsNullOrWhiteSpace($finalProjectArg)) {
            $resolvedProjectDir = $runFolder
        }
        else {
            if ([System.IO.Path]::IsPathRooted($finalProjectArg)) {
                $resolvedProjectDir = $finalProjectArg
            }
            else {
                $resolvedProjectDir = Join-Path $runFolder $finalProjectArg
            }
        }

        try {
            $resolvedProjectDir = (Resolve-Path -Path $resolvedProjectDir -ErrorAction Stop).Path
        }
        catch {
            # If init creates it as a new directory, use the computed path directly.
        }

        $resolvedProjectName = Split-Path -Leaf $resolvedProjectDir
    }

    if ($ArgsList -and $ArgsList.Count -gt 0) {
        & $venvAudi @effectiveArgs
    } else {
        & $venvAudi --help
    }

    if ($LASTEXITCODE -eq 0 -and $effectiveArgs -and $effectiveArgs.Count -gt 0 -and $effectiveArgs[0] -eq 'init') {
        Update-OrchestratorStateMetadata -SpecsOwnerDir $repoRoot -ProjectName $resolvedProjectName
        Initialize-ProjectSecrets -SourceEnvPath (Join-Path $repoRoot '.env') -ProjectDir $resolvedProjectDir
    }
}
finally {
    Pop-Location
}

# Copy the freshly built/installed audi.exe into the user's local bin folder.
$localBinDir = Join-Path $env:USERPROFILE '.local\bin'

# Prefer the freshly-built local .venv executable as the copy source so the
# copy always reflects the latest build. Fall back to whichever audi.exe the
# script resolved earlier.
$copySource = if (Test-Path $localAudi) { $localAudi } else { $venvAudi }

if (Test-Path $copySource) {
    if (-not (Test-Path $localBinDir -PathType Container)) {
        New-Item -ItemType Directory -Path $localBinDir -Force | Out-Null
    }
    $localBinAudi = Join-Path $localBinDir 'audi.exe'
    $sourceFull = (Resolve-Path -Path $venvAudi).Path

    Write-Host "Copying audi.exe to $localBinDir..." -ForegroundColor Cyan
    try {
        Copy-Item -Path $sourceFull -Destination $localBinAudi -Force -ErrorAction Stop
        Write-Host "Copied audi.exe to $localBinAudi." -ForegroundColor Green
    }
    catch {
        # Copy-Item throws when the source and destination are the same file.
        if ($sourceFull -ieq $localBinAudi) {
            Write-Host "audi.exe source is already $localBinAudi; it is up to date." -ForegroundColor Yellow
        }
        else {
            throw
        }
    }
}

exit $LASTEXITCODE
