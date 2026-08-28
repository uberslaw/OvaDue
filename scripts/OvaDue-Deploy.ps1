#Requires -Version 5.1

function Initialize-OvaDueDeploy {
    param(
        [string]$Root,
        [scriptblock]$LogAction
    )

    $script:DeployRoot = $Root
    $script:DeployLogAction = $LogAction
    $script:DeployConfigPath = Join-Path $Root 'deploy\deploy-config.json'
    $script:IncludeRulesPath = Join-Path $Root 'deploy\package-include.json'
    $script:VersionPath = Join-Path $Root 'deploy\version.json'
    $script:DeployLogPath = Join-Path $Root 'data\deploy.log'
    $script:DeployedVersionPath = Join-Path $Root 'data\deployed-version.json'
    $script:DataDir = Join-Path $Root 'data'
}

function Test-OvaDueDeployLayout {
    param([string]$Root)

    $required = @(
        'app.py',
        'requirements.txt',
        'launch control.cmd',
        'scripts\OvaDue-LaunchControl.ps1',
        'scripts\OvaDue-LaunchControl.cmd',
        'scripts\OvaDue-Deploy.ps1',
        'deploy\deploy-config.json',
        'deploy\package-include.json',
        'deploy\version.json'
    )

    $missing = New-Object System.Collections.Generic.List[string]
    foreach ($relative in $required) {
        $fullPath = Join-Path $Root ($relative -replace '/', '\')
        if (-not (Test-Path -LiteralPath $fullPath)) {
            [void]$missing.Add($relative)
        }
    }
    return @($missing)
}

function Get-OvaDueSetupHelp {
    param(
        [string]$Root,
        [string]$Topic = 'overview'
    )

    $config = $null
    try {
        if (Test-Path -LiteralPath (Join-Path $Root 'deploy\deploy-config.json')) {
            $config = Get-Content -LiteralPath (Join-Path $Root 'deploy\deploy-config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        }
    } catch { }

    $repoUrl = if ($config -and $config.gitRepositoryUrl) { [string]$config.gitRepositoryUrl } else { 'https://github.com/uberslaw/OvaDue.git' }
    $gitPath = if ($config -and $config.gitInstallPath) { [string]$config.gitInstallPath } else { 'C:\OvaDue' }
    $branch = if ($config -and $config.gitBranch) { [string]$config.gitBranch } else { 'main' }

    $manualInstall = @(
        'Manual server setup (if buttons fail):'
        "1. Install Python 3.11+ (python.org) and tick Add to PATH."
        '2. Install Git for Windows (git-scm.com) if using git install.'
        "3. Clone or copy the full app folder (must include scripts\ and deploy\)."
        "   git clone --branch $branch $repoUrl `"$gitPath`""
        "4. cd `"$gitPath`""
        '5. py -3 -m venv .venv'
        '6. .venv\Scripts\pip install -r requirements.txt'
        '7. Double-click "launch control.cmd", then click Install Server or Start Dashboard.'
    ) -join "`r`n"

    $topics = @{
        overview = @(
            'OvaDue setup (pick one path):'
            ''
            'A) Install from Git (recommended on a new server)'
            '   Needs: Git + Python on PATH.'
            "   Clones/updates $repoUrl to $gitPath, installs .venv, opens Launch Control."
            ''
            'B) Install Server (this folder)'
            '   Needs: Python on PATH.'
            '   Creates .venv here and installs requirements.txt.'
            ''
            'Check & Repair (left rail)'
            '   Detects missing/broken pieces after folder copy; auto-fixes safe dirs;'
            '   offers Install Server when .venv/packages are broken.'
            ''
            'C) Upgrade from Push'
            '   Needs: an OvaDue_*.zip already copied to C:\temp.'
            ''
            'D) Migration (new machine with existing data)'
            '   Source: Backup Migration Pack. Target: Install Server/Git, then Import Migration Pack.'
            ''
            'Required files in every copy/git clone:'
            'app.py, requirements.txt, launch control.cmd, scripts\, deploy\'
            ''
            $manualInstall
        ) -join "`r`n"
        installServer = @(
            'Install Server needs Python 3.11+ on PATH.'
            ''
            'Quick fix:'
            '1. Install Python from python.org (tick Add to PATH).'
            "2. Open PowerShell in: $Root"
            '3. py -3 -m venv .venv'
            '4. .venv\Scripts\pip install -r requirements.txt'
            '5. Re-open Launch Control and click Start Dashboard.'
            ''
            'Or run Install Server again after Python is installed.'
        ) -join "`r`n"
        installFromGit = @(
            'Install from Git needs Git for Windows and Python on PATH.'
            ''
            'Quick fix:'
            '1. Install Git: https://git-scm.com/download/win'
            '2. Install Python 3.11+ and tick Add to PATH.'
            '3. Open PowerShell and run:'
            "   git clone --branch $branch $repoUrl `"$gitPath`""
            "   cd `"$gitPath`""
            '   py -3 -m venv .venv'
            '   .venv\Scripts\pip install -r requirements.txt'
            '4. Run "launch control.cmd" from that folder.'
            ''
            "Edit deploy\deploy-config.json to change gitInstallPath (currently $gitPath)."
        ) -join "`r`n"
        missingFiles = @(
            'This folder is missing files needed for deploy actions.'
            ''
            'You need the full OvaDue app, not just app.py.'
            'Required: scripts\OvaDue-Deploy.ps1, scripts\OvaDue-LaunchControl.ps1, deploy\*.json'
            ''
            'Fix:'
            "1. git clone --branch $branch $repoUrl `"$gitPath`""
            '   OR copy the complete project folder from the dev machine.'
            '2. Open Launch Control from that folder (launch control.cmd).'
            ''
            $manualInstall
        ) -join "`r`n"
        migration = @(
            'Machine migration (data + config only):'
            ''
            '1. SOURCE machine - Backup Migration Pack'
            '   Creates OvaDue_Migration_*.zip with uploads, delivered orders,'
            '   deploy-config, Streamlit config, and launch control\launch-control.json.'
            '   Copy the zip to the new machine (USB, share, or C:\temp).'
            ''
            '2. TARGET machine - install app code first'
            '   Install from Git, OR copy the full app folder then Install Server.'
            '   Confirm Python 3.11+ is on PATH before Install Server.'
            ''
            '3. TARGET machine - Import Migration Pack'
            '   Pick the zip from step 1. Restores data/config only; does not replace app code.'
            '   Existing files at the same paths are overwritten by the pack.'
            ''
            'Logs and .venv are never migrated. Re-run Install Server if the venv is missing.'
            "Deploy log: $Root\data\deploy.log"
        ) -join "`r`n"
        healthCheck = @(
            'Check & Repair (Launch Control):'
            ''
            '1. Open Launch Control (launch control.cmd).'
            '2. Click Check & Repair in the left rail.'
            '3. Read the MessageBox and data\self-heal-report.txt.'
            '4. If prompted, confirm Install Server to recreate .venv / packages.'
            '5. Click Start Dashboard, then Open Dashboard.'
            ''
            'After copying the whole folder to a new PC:'
            '- Install Python 3.11+ (tick Add to PATH), then Check & Repair.'
            '- A copied .venv is often broken; Install Server recreates it.'
            '- Import Migration Pack only if uploads/data were NOT copied.'
            ''
            "Report: $Root\data\self-heal-report.txt"
            "Deploy log: $Root\data\deploy.log"
        ) -join "`r`n"
    }

    if ($topics.ContainsKey($Topic)) {
        return $topics[$Topic]
    }
    return $topics['overview']
}

function Write-DeployLog {
    param(
        [string]$Message,
        [string]$Level = 'INFO'
    )

    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [$Level] $Message"
    if (-not (Test-Path -LiteralPath $script:DataDir)) {
        New-Item -ItemType Directory -Path $script:DataDir -Force | Out-Null
    }
    Add-Content -LiteralPath $script:DeployLogPath -Value $line -Encoding UTF8
    if ($script:DeployLogAction) {
        & $script:DeployLogAction $Message $Level
    }
}

function Get-OvaDueDeployConfig {
    if (-not (Test-Path -LiteralPath $script:DeployConfigPath)) {
        throw "Missing deploy config: $($script:DeployConfigPath)"
    }
    return Get-Content -LiteralPath $script:DeployConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Get-OvaDueIncludeRules {
    if (-not (Test-Path -LiteralPath $script:IncludeRulesPath)) {
        throw "Missing package include rules: $($script:IncludeRulesPath)"
    }
    return Get-Content -LiteralPath $script:IncludeRulesPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Get-OvaDueVersionInfo {
    if (-not (Test-Path -LiteralPath $script:VersionPath)) {
        throw "Missing version file: $($script:VersionPath)"
    }
    return Get-Content -LiteralPath $script:VersionPath -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Save-OvaDueVersionInfo {
    param($VersionInfo)

    $VersionInfo | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $script:VersionPath -Encoding UTF8
}

function ConvertTo-RelativePath {
    param(
        [string]$FullPath,
        [string]$Root
    )

    $relative = $FullPath.Substring($Root.Length).TrimStart('\', '/')
    return ($relative -replace '\\', '/')
}

function Test-PathExcludedByRules {
    param(
        [string]$RelativePath,
        [string[]]$Rules
    )

    $normalized = ($RelativePath -replace '\\', '/').TrimStart('/')
    foreach ($rule in @($Rules)) {
        $pattern = ($rule -replace '\\', '/').TrimStart('/')
        if ($pattern.EndsWith('/**')) {
            $prefix = $pattern.Substring(0, $pattern.Length - 3)
            if ($normalized -eq $prefix -or $normalized.StartsWith("$prefix/")) {
                return $true
            }
            continue
        }
        if ($pattern.Contains('*')) {
            $likePattern = ($pattern -replace '/', '\')
            if ($normalized -like $likePattern) {
                return $true
            }
            continue
        }
        if ($normalized -eq $pattern -or $normalized.StartsWith("$pattern/")) {
            return $true
        }
    }
    return $false
}

function Get-OvaDuePackageFiles {
    $rules = Get-OvaDueIncludeRules
    $files = New-Object System.Collections.Generic.List[string]
    $root = $script:DeployRoot

    foreach ($includePath in @($rules.includePaths)) {
        $source = Join-Path $root $includePath
        if (-not (Test-Path -LiteralPath $source)) {
            Write-DeployLog "Include path not found, skipping: $includePath" 'WARN'
            continue
        }

        if ((Get-Item -LiteralPath $source).PSIsContainer) {
            Get-ChildItem -LiteralPath $source -Recurse -File -Force | ForEach-Object {
                $relative = ConvertTo-RelativePath -FullPath $_.FullName -Root $root
                if (Test-PathExcludedByRules -RelativePath $relative -Rules @($rules.neverPackage)) { return }
                if (Test-PathExcludedByRules -RelativePath $relative -Rules @($rules.excludePatterns)) { return }
                [void]$files.Add($relative)
            }
        } else {
            $relative = ConvertTo-RelativePath -FullPath $source -Root $root
            if (-not (Test-PathExcludedByRules -RelativePath $relative -Rules @($rules.neverPackage))) {
                [void]$files.Add($relative)
            }
        }
    }

    return @($files | Sort-Object -Unique)
}

function Get-FileSha256Hex {
    param([string]$Path)
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function New-OvaDuePackageManifest {
    param(
        [string[]]$RelativeFiles,
        [string]$PackageId,
        [int]$ApiVersion
    )

    $entries = @()
    foreach ($relative in $RelativeFiles) {
        $fullPath = Join-Path $script:DeployRoot ($relative -replace '/', '\')
        if (-not (Test-Path -LiteralPath $fullPath)) {
            throw "Package file missing during manifest build: $relative"
        }
        $item = Get-Item -LiteralPath $fullPath
        $entries += [ordered]@{
            path = ($relative -replace '\\', '/')
            sha256 = (Get-FileSha256Hex -Path $fullPath)
            size = [int64]$item.Length
        }
    }

    $entries = @($entries | Sort-Object { $_.path })
    $rootHashInput = ($entries | ForEach-Object { "{0}:{1}" -f $_.path, $_.sha256 }) -join "`n"
    $rootHashBytes = [System.Text.Encoding]::UTF8.GetBytes($rootHashInput)
    $rootHash = [System.BitConverter]::ToString(
        ([System.Security.Cryptography.SHA256]::Create().ComputeHash($rootHashBytes))
    ).Replace('-', '').ToLowerInvariant()

    return [ordered]@{
        appName = 'OvaDue'
        apiVersion = $ApiVersion
        packageId = $PackageId
        createdUtc = (Get-Date).ToUniversalTime().ToString('o')
        createdLocal = (Get-Date).ToString('o')
        rootHash = $rootHash
        files = $entries
    }
}

function Test-OvaDueManifestIntegrity {
    param(
        [string]$ExtractRoot,
        [object]$Manifest
    )

    Write-DeployLog "Verifying package manifest and file hashes..."
    if (-not $Manifest.rootHash) {
        throw 'Manifest is missing rootHash.'
    }
    if (-not $Manifest.files) {
        throw 'Manifest contains no files.'
    }

    $entries = @($Manifest.files | Sort-Object { $_.path })
    foreach ($entry in $entries) {
        $relative = [string]$entry.path
        $expectedHash = [string]$entry.sha256
        $targetPath = Join-Path $ExtractRoot ($relative -replace '/', '\')
        if (-not (Test-Path -LiteralPath $targetPath)) {
            throw "Manifest file missing in package: $relative"
        }
        $actualHash = Get-FileSha256Hex -Path $targetPath
        if ($actualHash -ne $expectedHash) {
            throw "Hash mismatch for $relative. Expected $expectedHash but found $actualHash."
        }
    }

    $rootHashInput = ($entries | ForEach-Object { "{0}:{1}" -f $_.path, $_.sha256 }) -join "`n"
    $rootHashBytes = [System.Text.Encoding]::UTF8.GetBytes($rootHashInput)
    $actualRootHash = [System.BitConverter]::ToString(
        ([System.Security.Cryptography.SHA256]::Create().ComputeHash($rootHashBytes))
    ).Replace('-', '').ToLowerInvariant()

    if ($actualRootHash -ne [string]$Manifest.rootHash) {
        throw "Package rootHash mismatch. Manifest may be corrupt or tampered with."
    }

    Write-DeployLog "Manifest verification passed for API version $($Manifest.apiVersion)."
    return $true
}

function Stop-OvaDueDashboardForDeploy {
    param([string]$PidFile)

    if (-not (Test-Path -LiteralPath $PidFile)) {
        return
    }

    try {
        $processId = 0
        $text = (Get-Content -LiteralPath $PidFile -TotalCount 1 -ErrorAction Stop).Trim()
        if ([int]::TryParse($text, [ref]$processId) -and $processId -gt 0) {
            Write-DeployLog "Stopping dashboard PID $processId before deploy action..."
            & taskkill.exe /PID $processId /T /F | Out-Null
        }
    } catch {
        Write-DeployLog "Dashboard stop skipped: $($_.Exception.Message)" 'WARN'
    } finally {
        Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-OvaDuePackageAndPush {
    $config = Get-OvaDueDeployConfig
    $rules = Get-OvaDueIncludeRules
    $version = Get-OvaDueVersionInfo
    $version.apiVersion = [int]$version.apiVersion + 1
    $version.lastPackagedUtc = (Get-Date).ToUniversalTime().ToString('o')
    $version.lastPackagedBy = $env:COMPUTERNAME
    Save-OvaDueVersionInfo -VersionInfo $version

    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $packageId = "{0}_{1}" -f $config.packageNamePrefix, $timestamp
    $zipName = "$packageId.zip"
    $stageRoot = Join-Path $env:TEMP ("ovadue-package-$timestamp")
    $zipPath = Join-Path $env:TEMP $zipName

    if (Test-Path -LiteralPath $stageRoot) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }

    $relativeFiles = Get-OvaDuePackageFiles
    if (-not $relativeFiles -or $relativeFiles.Count -eq 0) {
        throw 'No files matched the package include rules.'
    }

    Write-DeployLog "Building package $packageId with $($relativeFiles.Count) file(s), API version $($version.apiVersion)..."

    foreach ($relative in $relativeFiles) {
        $source = Join-Path $script:DeployRoot ($relative -replace '/', '\')
        $destination = Join-Path $stageRoot ($relative -replace '/', '\')
        $destinationDir = Split-Path -Parent $destination
        if (-not (Test-Path -LiteralPath $destinationDir)) {
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }

    $manifest = New-OvaDuePackageManifest -RelativeFiles $relativeFiles -PackageId $packageId -ApiVersion ([int]$version.apiVersion)
    $manifestPath = Join-Path $stageRoot 'manifest.json'
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    Test-OvaDueManifestIntegrity -ExtractRoot $stageRoot -Manifest ($manifest | ConvertTo-Json -Depth 8 | ConvertFrom-Json) | Out-Null

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($stageRoot, $zipPath)

    $pushTarget = [string]$config.pushTarget
    if (-not $pushTarget) {
        throw 'pushTarget is not configured in deploy\deploy-config.json'
    }
    if (-not (Test-Path -LiteralPath $pushTarget)) {
        throw "Push target is not reachable: $pushTarget"
    }

    $remoteZip = Join-Path $pushTarget $zipName
    Copy-Item -LiteralPath $zipPath -Destination $remoteZip -Force
    Write-DeployLog "Package pushed to $remoteZip"

    Remove-Item -LiteralPath $stageRoot -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue

    return [ordered]@{
        PackageId = $packageId
        ApiVersion = [int]$version.apiVersion
        RemotePath = $remoteZip
        FileCount = $relativeFiles.Count
    }
}

function Get-NewestOvaDuePackage {
    param([string]$SourceDirectory)

    if (-not (Test-Path -LiteralPath $SourceDirectory)) {
        throw "Upgrade source folder not found: $SourceDirectory"
    }

    $packages = Get-ChildItem -LiteralPath $SourceDirectory -Filter 'OvaDue_*.zip' -File |
        Sort-Object { $_.LastWriteTimeUtc } -Descending

    if (-not $packages -or $packages.Count -eq 0) {
        throw "No OvaDue_*.zip packages found in $SourceDirectory"
    }

    return $packages[0]
}

function Invoke-OvaDueUpgradeFromPush {
    param([string]$PidFile)

    $config = Get-OvaDueDeployConfig
    $rules = Get-OvaDueIncludeRules
    $sourceDirectory = [string]$config.upgradeSource
    if (-not $sourceDirectory) {
        $sourceDirectory = 'C:\temp'
    }

    $packageFile = Get-NewestOvaDuePackage -SourceDirectory $sourceDirectory
    Write-DeployLog "Selected upgrade package: $($packageFile.FullName)"

    $extractRoot = Join-Path $env:TEMP ("ovadue-upgrade-{0}" -f (Get-Date -Format 'yyyyMMddHHmmss'))
    if (Test-Path -LiteralPath $extractRoot) {
        Remove-Item -LiteralPath $extractRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Path $extractRoot -Force | Out-Null

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($packageFile.FullName, $extractRoot)

    $manifestPath = Join-Path $extractRoot 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        throw 'Package is missing manifest.json'
    }

    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Test-OvaDueManifestIntegrity -ExtractRoot $extractRoot -Manifest $manifest | Out-Null

    Stop-OvaDueDashboardForDeploy -PidFile $PidFile

    foreach ($dir in @($rules.ensureDirectories)) {
        $targetDir = Join-Path $script:DeployRoot ($dir -replace '/', '\')
        if (-not (Test-Path -LiteralPath $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
    }

    $updatedCount = 0
    $skippedCount = 0
    foreach ($entry in @($manifest.files)) {
        $relative = [string]$entry.path
        if ($relative -eq 'manifest.json') { continue }
        if (Test-PathExcludedByRules -RelativePath $relative -Rules @($rules.preserveOnUpgrade)) {
            $skippedCount++
            continue
        }

        $source = Join-Path $extractRoot ($relative -replace '/', '\')
        $destination = Join-Path $script:DeployRoot ($relative -replace '/', '\')
        $destinationDir = Split-Path -Parent $destination
        if (-not (Test-Path -LiteralPath $destinationDir)) {
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }
        Copy-Item -LiteralPath $source -Destination $destination -Force
        $updatedCount++
    }

    $deployedInfo = [ordered]@{
        appName = [string]$manifest.appName
        apiVersion = [int]$manifest.apiVersion
        packageId = [string]$manifest.packageId
        deployedUtc = (Get-Date).ToUniversalTime().ToString('o')
        deployedLocal = (Get-Date).ToString('o')
        sourcePackage = $packageFile.FullName
        rootHash = [string]$manifest.rootHash
    }
    $deployedInfo | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $script:DeployedVersionPath -Encoding UTF8

    Remove-Item -LiteralPath $extractRoot -Recurse -Force -ErrorAction SilentlyContinue
    Write-DeployLog "Upgrade complete. Updated $updatedCount file(s), preserved $skippedCount path(s)."

    return [ordered]@{
        PackageId = [string]$manifest.packageId
        ApiVersion = [int]$manifest.apiVersion
        UpdatedFiles = $updatedCount
        PreservedPaths = $skippedCount
        SourcePackage = $packageFile.FullName
    }
}

function Resolve-OvaDuePythonCommand {
    $config = Get-OvaDueDeployConfig
    $launcher = [string]$config.pythonLauncher
    if (-not $launcher) { $launcher = 'py' }

    if (Get-Command $launcher -ErrorAction SilentlyContinue) {
        $args = @()
        if ($config.pythonLauncherArgs) {
            $args = @($config.pythonLauncherArgs)
        }
        return @{ FileName = $launcher; Arguments = $args }
    }

    foreach ($candidate in @('python', 'python3')) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) {
            return @{ FileName = $candidate; Arguments = @() }
        }
    }

    throw 'Python was not found. Install Python 3.11+ from python.org (tick Add to PATH) or ensure the py launcher is available.'
}

function Invoke-OvaDueInstallServer {
    param([string]$InstallRoot)

    $restoreRoot = $null
    if ($InstallRoot) {
        $restoreRoot = $script:DeployRoot
        Initialize-OvaDueDeploy -Root $InstallRoot -LogAction $script:DeployLogAction
    }

    try {
        return Invoke-OvaDueInstallServerCore
    } finally {
        if ($restoreRoot) {
            Initialize-OvaDueDeploy -Root $restoreRoot -LogAction $script:DeployLogAction
        }
    }
}

function Test-OvaDueVenvUsable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$VenvPath
    )

    $pythonExe = Join-Path $VenvPath 'Scripts\python.exe'
    $pipExe = Join-Path $VenvPath 'Scripts\pip.exe'
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        return @{ Usable = $false; Reason = "Missing $pythonExe" }
    }
    if (-not (Test-Path -LiteralPath $pipExe)) {
        return @{ Usable = $false; Reason = "Missing $pipExe" }
    }

    $pyvenvCfg = Join-Path $VenvPath 'pyvenv.cfg'
    if (Test-Path -LiteralPath $pyvenvCfg) {
        try {
            $homeLine = Get-Content -LiteralPath $pyvenvCfg -ErrorAction Stop |
                Where-Object { $_ -match '^\s*home\s*=' } |
                Select-Object -First 1
            if ($homeLine) {
                $homePath = ($homeLine -replace '^\s*home\s*=\s*', '').Trim()
                if ($homePath -and -not (Test-Path -LiteralPath $homePath)) {
                    return @{
                        Usable = $false
                        Reason = "pyvenv.cfg home path missing on this machine: $homePath (typical after whole-folder copy)"
                    }
                }
            }
        } catch { }
    }

    # Use call operator (&) - Start-Process ArgumentList breaks on paths with spaces (OneDrive - Arup).
    $probePy = Join-Path $script:DataDir 'venv-probe.py'
    $outLog = Join-Path $script:DataDir 'venv-probe.out.log'
    $errLog = Join-Path $script:DataDir 'venv-probe.err.log'
    try {
        if (-not (Test-Path -LiteralPath $script:DataDir)) {
            New-Item -ItemType Directory -Path $script:DataDir -Force | Out-Null
        }
        Set-Content -LiteralPath $probePy -Value 'import sys; print(sys.version)' -Encoding ASCII
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $out = & $pythonExe $probePy 2> $errLog
            $exitCode = $LASTEXITCODE
            if ($null -ne $out) {
                Set-Content -LiteralPath $outLog -Value ($out | Out-String) -Encoding UTF8
            }
        } finally {
            $ErrorActionPreference = $prevEap
        }
        if ($exitCode -ne 0) {
            $err = ''
            if (Test-Path -LiteralPath $errLog) {
                $err = ((Get-Content -LiteralPath $errLog -Raw -ErrorAction SilentlyContinue) -replace '\s+', ' ').Trim()
            }
            if (-not $err) { $err = "exit code $exitCode" }
            return @{ Usable = $false; Reason = "venv python failed to run: $err" }
        }
    } catch {
        return @{ Usable = $false; Reason = "venv python probe exception: $($_.Exception.Message)" }
    }

    return @{ Usable = $true; Reason = 'ok'; Python = $pythonExe; Pip = $pipExe }
}

function Invoke-OvaDueInstallServerCore {
    $config = Get-OvaDueDeployConfig
    $rules = Get-OvaDueIncludeRules
    $python = Resolve-OvaDuePythonCommand
    $venvPath = Join-Path $script:DeployRoot ([string]$config.venvRelativePath)
    $requirements = Join-Path $script:DeployRoot ([string]$config.requirementsFile)

    foreach ($dir in @($rules.ensureDirectories)) {
        $targetDir = Join-Path $script:DeployRoot ($dir -replace '/', '\')
        if (-not (Test-Path -LiteralPath $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
    }

    if (-not (Test-Path -LiteralPath $requirements)) {
        throw "Missing requirements file: $requirements"
    }

    Write-DeployLog "Installing server-side runtime into $venvPath ..."
    $reuseVenv = $false
    if (Test-Path -LiteralPath $venvPath) {
        $venvProbe = Test-OvaDueVenvUsable -VenvPath $venvPath
        if ($venvProbe.Usable) {
            Write-DeployLog "Existing virtual environment found; reusing $venvPath" 'WARN'
            $reuseVenv = $true
        } else {
            Write-DeployLog "Removing broken/unusable virtual environment ($($venvProbe.Reason))" 'WARN'
            Remove-Item -LiteralPath $venvPath -Recurse -Force -ErrorAction Stop
        }
    }

    if (-not $reuseVenv) {
        $venvArgs = @($python.Arguments + @('-m', 'venv', $venvPath))
        $process = Start-Process -FilePath $python.FileName -ArgumentList $venvArgs -WorkingDirectory $script:DeployRoot -Wait -PassThru -NoNewWindow
        if ($process.ExitCode -ne 0) {
            throw "Failed to create virtual environment (exit code $($process.ExitCode))."
        }
    }

    $pipPath = Join-Path $venvPath 'Scripts\pip.exe'
    if (-not (Test-Path -LiteralPath $pipPath)) {
        throw "Missing pip executable: $pipPath"
    }

    $pipArgs = @('install', '--upgrade', 'pip')
    $pipUpgrade = Start-Process -FilePath $pipPath -ArgumentList $pipArgs -WorkingDirectory $script:DeployRoot -Wait -PassThru -NoNewWindow
    if ($pipUpgrade.ExitCode -ne 0) {
        throw "Failed to upgrade pip (exit code $($pipUpgrade.ExitCode))."
    }

    $installArgs = @('install', '-r', $requirements)
    $pipInstall = Start-Process -FilePath $pipPath -ArgumentList $installArgs -WorkingDirectory $script:DeployRoot -Wait -PassThru -NoNewWindow
    if ($pipInstall.ExitCode -ne 0) {
        throw "Failed to install Python requirements (exit code $($pipInstall.ExitCode))."
    }

    $pythonExe = Join-Path $venvPath 'Scripts\python.exe'
    $verifyPy = Join-Path $script:DataDir 'install-verify.py'
    Set-Content -LiteralPath $verifyPy -Value 'import streamlit, pandas, plotly; print(streamlit.__version__)' -Encoding ASCII
    $verifyOut = Join-Path $script:DataDir 'install-verify.out.log'
    $verifyErr = Join-Path $script:DataDir 'install-verify.err.log'
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $verifyOutput = & $pythonExe $verifyPy 2> $verifyErr
        $verifyExit = $LASTEXITCODE
        if ($null -ne $verifyOutput) {
            Set-Content -LiteralPath $verifyOut -Value ($verifyOutput | Out-String) -Encoding UTF8
        } else {
            Set-Content -LiteralPath $verifyOut -Value '' -Encoding UTF8
        }
    } finally {
        $ErrorActionPreference = $prevEap
    }
    if ($verifyExit -ne 0) {
        throw 'Server install verification failed. See data\install-verify.err.log'
    }

    Write-DeployLog 'Server install completed successfully.'
    return [ordered]@{
        VirtualEnvironment = $venvPath
        Python = $pythonExe
    }
}

function Resolve-GitCommand {
    if (Get-Command git -ErrorAction SilentlyContinue) {
        return (Get-Command git -ErrorAction SilentlyContinue).Source
    }
    throw 'Git is not installed or not on PATH. Install Git for Windows from https://git-scm.com/download/win'
}

function Invoke-GitCommand {
    param(
        [string]$WorkingDirectory,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $git = Resolve-GitCommand
    $displayArgs = ($Arguments | ForEach-Object {
        if ($_ -match '\s') { '"{0}"' -f $_ } else { $_ }
    }) -join ' '
    Write-DeployLog "Running: git $displayArgs"

    $process = Start-Process `
        -FilePath $git `
        -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory `
        -Wait `
        -PassThru `
        -NoNewWindow `
        -RedirectStandardOutput (Join-Path $script:DataDir 'git-last.out.log') `
        -RedirectStandardError (Join-Path $script:DataDir 'git-last.err.log')

    if ($process.ExitCode -ne 0) {
        $stderr = ''
        $errPath = Join-Path $script:DataDir 'git-last.err.log'
        if (Test-Path -LiteralPath $errPath) {
            $stderr = (Get-Content -LiteralPath $errPath -Raw -ErrorAction SilentlyContinue).Trim()
        }
        throw "Git command failed (exit code $($process.ExitCode)): git $displayArgs${stderr}"
    }
}

function Start-OvaDueLaunchControl {
    param([string]$InstallRoot)

    $config = Get-OvaDueDeployConfig
    $launchControlPath = Join-Path $InstallRoot ([string]$config.launchControlRelativePath)
    if (-not (Test-Path -LiteralPath $launchControlPath)) {
        throw "Launch Control script not found: $launchControlPath"
    }

    $powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    if (-not (Test-Path -LiteralPath $powershell)) {
        $powershell = 'powershell.exe'
    }

    Start-Process `
        -FilePath $powershell `
        -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-STA', '-WindowStyle', 'Hidden', '-File', $launchControlPath) `
        -WorkingDirectory (Split-Path -Parent $launchControlPath)

    Write-DeployLog "Started Launch Control from $launchControlPath"
    return $launchControlPath
}

function Invoke-OvaDueInstallFromGit {
    param(
        [switch]$LaunchControl
    )

    $config = Get-OvaDueDeployConfig
    $rules = Get-OvaDueIncludeRules
    $repoUrl = [string]$config.gitRepositoryUrl
    $branch = [string]$config.gitBranch
    if (-not $branch) { $branch = 'main' }
    $installPath = [string]$config.gitInstallPath
    if (-not $installPath) { $installPath = 'C:\OvaDue' }

    if (-not $repoUrl) {
        throw 'gitRepositoryUrl is not configured in deploy\deploy-config.json'
    }

    Resolve-GitCommand | Out-Null
    $installPath = [System.IO.Path]::GetFullPath($installPath)
    $parentPath = Split-Path -Parent $installPath
    if ($parentPath -and -not (Test-Path -LiteralPath $parentPath)) {
        New-Item -ItemType Directory -Path $parentPath -Force | Out-Null
    }

    $gitDir = Join-Path $installPath '.git'
    if (Test-Path -LiteralPath $gitDir) {
        Write-DeployLog "Updating existing git install at $installPath"
        Invoke-GitCommand -WorkingDirectory $installPath -Arguments @('fetch', 'origin')
        Invoke-GitCommand -WorkingDirectory $installPath -Arguments @('checkout', $branch)
        Invoke-GitCommand -WorkingDirectory $installPath -Arguments @('pull', '--ff-only', 'origin', $branch)
    } elseif (Test-Path -LiteralPath $installPath) {
        $existingItems = @(Get-ChildItem -LiteralPath $installPath -Force -ErrorAction SilentlyContinue)
        if ($existingItems.Count -gt 0) {
            throw "Install path exists but is not a git repo: $installPath"
        }
        Write-DeployLog "Cloning $repoUrl into $installPath"
        Invoke-GitCommand -WorkingDirectory $parentPath -Arguments @('clone', '--branch', $branch, '--single-branch', $repoUrl, (Split-Path -Leaf $installPath))
    } else {
        Write-DeployLog "Cloning $repoUrl into $installPath"
        Invoke-GitCommand -WorkingDirectory $parentPath -Arguments @('clone', '--branch', $branch, '--single-branch', $repoUrl, (Split-Path -Leaf $installPath))
    }

    foreach ($dir in @($rules.ensureDirectories)) {
        $targetDir = Join-Path $installPath ($dir -replace '/', '\')
        if (-not (Test-Path -LiteralPath $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
    }

    $remoteHead = ''
    try {
        $remoteHead = (& git -C $installPath rev-parse --short HEAD 2>$null | Select-Object -First 1)
    } catch { }

    Stop-OvaDueDashboardForDeploy -PidFile (Join-Path $installPath 'data\streamlit.pid')
    $serverInfo = Invoke-OvaDueInstallServer -InstallRoot $installPath

    $versionPath = Join-Path $installPath 'deploy\version.json'
    if (Test-Path -LiteralPath $versionPath) {
        $versionInfo = Get-Content -LiteralPath $versionPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $deployedInfo = [ordered]@{
            appName = [string]$versionInfo.appName
            apiVersion = [int]$versionInfo.apiVersion
            packageId = 'git-install'
            deployedUtc = (Get-Date).ToUniversalTime().ToString('o')
            deployedLocal = (Get-Date).ToString('o')
            sourcePackage = $repoUrl
            gitBranch = $branch
            gitCommit = [string]$remoteHead
            installPath = $installPath
        }
        $deployedPath = Join-Path $installPath 'data\deployed-version.json'
        $deployedInfo | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $deployedPath -Encoding UTF8
    }

    $launchControlPath = $null
    if ($LaunchControl) {
        $launchControlPath = Start-OvaDueLaunchControl -InstallRoot $installPath
    }

    Write-DeployLog "Git install completed at $installPath"
    return [ordered]@{
        InstallPath = $installPath
        Repository = $repoUrl
        Branch = $branch
        Commit = [string]$remoteHead
        VirtualEnvironment = $serverInfo.VirtualEnvironment
        LaunchControl = $launchControlPath
    }
}

function Get-OvaDueMigrationFiles {
    $rules = Get-OvaDueIncludeRules
    $files = New-Object System.Collections.Generic.List[string]
    $root = $script:DeployRoot
    $paths = @($rules.migrationPaths)
    if (-not $paths -or $paths.Count -eq 0) {
        throw 'migrationPaths is not configured in deploy\package-include.json'
    }

    $exclude = @($rules.migrationExcludePatterns)
    if (-not $exclude) { $exclude = @($rules.excludePatterns) }
    $never = @($rules.migrationNeverPackage)
    if (-not $never) { $never = @($rules.neverPackage) }

    foreach ($includePath in $paths) {
        $source = Join-Path $root $includePath
        if (-not (Test-Path -LiteralPath $source)) {
            Write-DeployLog "Migration path not found, skipping: $includePath" 'WARN'
            continue
        }

        if ((Get-Item -LiteralPath $source).PSIsContainer) {
            Get-ChildItem -LiteralPath $source -Recurse -File -Force | ForEach-Object {
                $relative = ConvertTo-RelativePath -FullPath $_.FullName -Root $root
                if (Test-PathExcludedByRules -RelativePath $relative -Rules $never) { return }
                if (Test-PathExcludedByRules -RelativePath $relative -Rules $exclude) { return }
                [void]$files.Add($relative)
            }
        } else {
            $relative = ConvertTo-RelativePath -FullPath $source -Root $root
            if (-not (Test-PathExcludedByRules -RelativePath $relative -Rules $never)) {
                [void]$files.Add($relative)
            }
        }
    }

    return @($files | Sort-Object -Unique)
}

function Resolve-OvaDueMigrationExportDirectory {
    param([string]$OutputDirectory)

    if ($OutputDirectory) {
        return [System.IO.Path]::GetFullPath($OutputDirectory)
    }

    $config = Get-OvaDueDeployConfig
    $configured = [string]$config.migrationExportDirectory
    if ($configured) {
        return [System.IO.Path]::GetFullPath($configured)
    }

    $upgradeSource = [string]$config.upgradeSource
    if ($upgradeSource) {
        return [System.IO.Path]::GetFullPath($upgradeSource)
    }

    return 'C:\temp'
}

function Invoke-OvaDueExportMigrationPack {
    param(
        [string]$OutputDirectory,
        [string]$OutputZipPath
    )

    $config = Get-OvaDueDeployConfig
    $version = Get-OvaDueVersionInfo
    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $packageId = "OvaDue_Migration_{0}_{1}" -f $env:COMPUTERNAME, $timestamp

    if ($OutputZipPath) {
        $zipPath = [System.IO.Path]::GetFullPath($OutputZipPath)
        $exportDir = Split-Path -Parent $zipPath
    } else {
        $exportDir = Resolve-OvaDueMigrationExportDirectory -OutputDirectory $OutputDirectory
        $zipPath = Join-Path $exportDir "$packageId.zip"
    }

    if (-not (Test-Path -LiteralPath $exportDir)) {
        New-Item -ItemType Directory -Path $exportDir -Force | Out-Null
    }

    $stageRoot = Join-Path $env:TEMP ("ovadue-migration-export-$timestamp")
    if (Test-Path -LiteralPath $stageRoot) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }

    $relativeFiles = Get-OvaDueMigrationFiles
    if (-not $relativeFiles -or $relativeFiles.Count -eq 0) {
        throw 'No migration files found. Ensure uploads\ or configured migrationPaths exist on this machine.'
    }

    Write-DeployLog "Building migration pack $packageId with $($relativeFiles.Count) file(s)..."

    foreach ($relative in $relativeFiles) {
        $source = Join-Path $script:DeployRoot ($relative -replace '/', '\')
        $destination = Join-Path $stageRoot ($relative -replace '/', '\')
        $destinationDir = Split-Path -Parent $destination
        if (-not (Test-Path -LiteralPath $destinationDir)) {
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }

    $manifest = New-OvaDuePackageManifest -RelativeFiles $relativeFiles -PackageId $packageId -ApiVersion ([int]$version.apiVersion)
    $manifest['packType'] = 'migration'
    $manifest['sourceComputer'] = $env:COMPUTERNAME
    $manifest['sourceRoot'] = $script:DeployRoot
    $manifestPath = Join-Path $stageRoot 'manifest.json'
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

    $manifestObject = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]$manifestObject.packType -ne 'migration') {
        throw 'Migration manifest packType write/read-back failed.'
    }
    Test-OvaDueManifestIntegrity -ExtractRoot $stageRoot -Manifest $manifestObject | Out-Null

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($stageRoot, $zipPath)

    if (-not (Test-Path -LiteralPath $zipPath)) {
        throw "Migration zip was not written: $zipPath"
    }
    $zipInfo = Get-Item -LiteralPath $zipPath
    if ($zipInfo.Length -le 0) {
        throw "Migration zip is empty: $zipPath"
    }

    Remove-Item -LiteralPath $stageRoot -Recurse -Force -ErrorAction SilentlyContinue
    Write-DeployLog "Migration pack written to $zipPath ($($zipInfo.Length) bytes, $($relativeFiles.Count) file(s))."

    return [ordered]@{
        PackageId = $packageId
        ZipPath = $zipPath
        FileCount = $relativeFiles.Count
        Bytes = [int64]$zipInfo.Length
        PackType = 'migration'
    }
}

function Resolve-OvaDueMigrationImportZip {
    param([string]$ZipPath)

    if ($ZipPath) {
        $resolved = [System.IO.Path]::GetFullPath($ZipPath)
        if (-not (Test-Path -LiteralPath $resolved)) {
            throw "Migration pack not found: $resolved"
        }
        return $resolved
    }

    $config = Get-OvaDueDeployConfig
    $searchRoots = New-Object System.Collections.Generic.List[string]
    $configured = [string]$config.migrationImportDirectory
    if ($configured) { [void]$searchRoots.Add([System.IO.Path]::GetFullPath($configured)) }
    $upgradeSource = [string]$config.upgradeSource
    if ($upgradeSource) { [void]$searchRoots.Add([System.IO.Path]::GetFullPath($upgradeSource)) }
    [void]$searchRoots.Add('C:\temp')

    $candidates = New-Object System.Collections.Generic.List[System.IO.FileInfo]
    foreach ($root in @($searchRoots | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        Get-ChildItem -LiteralPath $root -Filter 'OvaDue_Migration_*.zip' -File -ErrorAction SilentlyContinue |
            ForEach-Object { [void]$candidates.Add($_) }
    }

    if ($candidates.Count -eq 0) {
        throw 'No OvaDue_Migration_*.zip found. Pass -ZipPath or place the pack in C:\temp (or migrationImportDirectory).'
    }

    $newest = $candidates | Sort-Object { $_.LastWriteTimeUtc } -Descending | Select-Object -First 1
    return $newest.FullName
}

function Invoke-OvaDueImportMigrationPack {
    param(
        [string]$ZipPath,
        [string]$PidFile,
        [string]$TargetRoot
    )

    $restoreRoot = $null
    if ($TargetRoot) {
        $restoreRoot = $script:DeployRoot
        Initialize-OvaDueDeploy -Root $TargetRoot -LogAction $script:DeployLogAction
    }

    try {
        return Invoke-OvaDueImportMigrationPackCore -ZipPath $ZipPath -PidFile $PidFile
    } finally {
        if ($restoreRoot) {
            Initialize-OvaDueDeploy -Root $restoreRoot -LogAction $script:DeployLogAction
        }
    }
}

function Invoke-OvaDueImportMigrationPackCore {
    param(
        [string]$ZipPath,
        [string]$PidFile
    )

    $rules = Get-OvaDueIncludeRules
    $resolvedZip = Resolve-OvaDueMigrationImportZip -ZipPath $ZipPath
    Write-DeployLog "Importing migration pack: $resolvedZip"

    $missingLayout = Test-OvaDueDeployLayout -Root $script:DeployRoot
    if ($missingLayout.Count -gt 0) {
        throw ("Target is missing app files (run Install from Git or copy the full folder first):`r`n- " + ($missingLayout -join "`r`n- "))
    }

    $timestamp = Get-Date -Format 'yyyyMMddHHmmss'
    $extractRoot = Join-Path $env:TEMP ("ovadue-migration-import-$timestamp")
    if (Test-Path -LiteralPath $extractRoot) {
        Remove-Item -LiteralPath $extractRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Path $extractRoot -Force | Out-Null

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($resolvedZip, $extractRoot)

    $manifestPath = Join-Path $extractRoot 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        throw 'Migration pack is missing manifest.json'
    }

    $manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($manifest.packType -and [string]$manifest.packType -ne 'migration') {
        throw "Refusing to import packType='$($manifest.packType)'. Expected 'migration' (use Upgrade from Push for app packages)."
    }
    if (-not $manifest.packType) {
        Write-DeployLog 'Migration pack has no packType field; proceeding after integrity check.' 'WARN'
    }

    Test-OvaDueManifestIntegrity -ExtractRoot $extractRoot -Manifest $manifest | Out-Null

    $allowed = @($rules.migrationPaths)
    if (-not $allowed -or $allowed.Count -eq 0) {
        throw 'migrationPaths is not configured; refusing import to avoid overwriting app code.'
    }

    if ($PidFile) {
        Stop-OvaDueDashboardForDeploy -PidFile $PidFile
    }

    foreach ($dir in @($rules.ensureDirectories)) {
        $targetDir = Join-Path $script:DeployRoot ($dir -replace '/', '\')
        if (-not (Test-Path -LiteralPath $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
    }

    $restoredCount = 0
    $skippedCount = 0
    foreach ($entry in @($manifest.files)) {
        $relative = [string]$entry.path
        if ($relative -eq 'manifest.json') { continue }

        $allowedHit = $false
        foreach ($allow in $allowed) {
            $normalizedAllow = ($allow -replace '\\', '/').TrimStart('/')
            $normalizedRel = ($relative -replace '\\', '/').TrimStart('/')
            if ($normalizedRel -eq $normalizedAllow -or $normalizedRel.StartsWith("$normalizedAllow/")) {
                $allowedHit = $true
                break
            }
            # File path allow-list entries (e.g. data/delivered_orders.json)
            if ($normalizedAllow -notmatch '/\*\*$' -and $normalizedRel -eq $normalizedAllow) {
                $allowedHit = $true
                break
            }
        }
        if (-not $allowedHit) {
            Write-DeployLog "Skipping non-migration path in pack: $relative" 'WARN'
            $skippedCount++
            continue
        }

        $source = Join-Path $extractRoot ($relative -replace '/', '\')
        if (-not (Test-Path -LiteralPath $source)) {
            throw "Manifest file missing after extract: $relative"
        }

        $destination = Join-Path $script:DeployRoot ($relative -replace '/', '\')
        $destinationDir = Split-Path -Parent $destination
        if (-not (Test-Path -LiteralPath $destinationDir)) {
            New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
        }
        Copy-Item -LiteralPath $source -Destination $destination -Force

        $actualHash = Get-FileSha256Hex -Path $destination
        if ($actualHash -ne [string]$entry.sha256) {
            throw "Post-import hash mismatch for $relative. Expected $($entry.sha256) but found $actualHash."
        }
        $restoredCount++
    }

    if ($restoredCount -le 0) {
        Remove-Item -LiteralPath $extractRoot -Recurse -Force -ErrorAction SilentlyContinue
        throw ("Migration import restored 0 files from {0}. Pack may be empty or paths are not under migrationPaths." -f $resolvedZip)
    }

    $importRecord = [ordered]@{
        packType = 'migration'
        packageId = [string]$manifest.packageId
        importedUtc = (Get-Date).ToUniversalTime().ToString('o')
        importedLocal = (Get-Date).ToString('o')
        sourcePackage = $resolvedZip
        sourceComputer = [string]$manifest.sourceComputer
        rootHash = [string]$manifest.rootHash
        restoredFiles = $restoredCount
        skippedFiles = $skippedCount
    }
    $recordPath = Join-Path $script:DataDir 'last-migration-import.json'
    $importRecord | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $recordPath -Encoding UTF8
    if (-not (Test-Path -LiteralPath $recordPath)) {
        throw "Failed to write import record: $recordPath"
    }

    Remove-Item -LiteralPath $extractRoot -Recurse -Force -ErrorAction SilentlyContinue
    Write-DeployLog "Migration import complete. Restored $restoredCount file(s), skipped $skippedCount path(s)."

    return [ordered]@{
        PackageId = [string]$manifest.packageId
        ZipPath = $resolvedZip
        RestoredFiles = $restoredCount
        SkippedFiles = $skippedCount
        ImportRecord = $recordPath
        TargetRoot = $script:DeployRoot
    }
}

function New-OvaDueHealthIssue {
    param(
        [string]$Id,
        [ValidateSet('OK', 'INFO', 'WARN', 'ERROR')]
        [string]$Severity,
        [string]$Message,
        [string]$Guidance = '',
        [ValidateSet('None', 'AutoFixed', 'InstallServer', 'UserAction')]
        [string]$Action = 'None',
        [switch]$AutoFixed
    )

    return [ordered]@{
        Id = $Id
        Severity = $Severity
        Message = $Message
        Guidance = $Guidance
        Action = $Action
        AutoFixed = [bool]$AutoFixed
    }
}

function Get-OvaDueRequiredPackages {
    $requirements = Join-Path $script:DeployRoot 'requirements.txt'
    $packages = New-Object System.Collections.Generic.List[string]
    if (Test-Path -LiteralPath $requirements) {
        Get-Content -LiteralPath $requirements -ErrorAction SilentlyContinue | ForEach-Object {
            $line = $_.Trim()
            if (-not $line -or $line.StartsWith('#')) { return }
            $name = ($line -split '[<>=!~\s]')[0].Trim()
            if ($name) {
                # pip name -> import name for known extras
                $importName = $name -replace '-', '_'
                if ($name -eq 'streamlit-js-eval') { $importName = 'streamlit_js_eval' }
                elseif ($name -eq 'streamlit-autorefresh') { $importName = 'streamlit_autorefresh' }
                [void]$packages.Add($importName)
            }
        }
    }
    if ($packages.Count -eq 0) {
        @('streamlit', 'pandas', 'plotly', 'xlrd', 'openpyxl', 'streamlit_js_eval', 'streamlit_autorefresh') | ForEach-Object {
            [void]$packages.Add($_)
        }
    }
    return @($packages)
}

function Invoke-OvaDueHealthCheck {
    <#
    .SYNOPSIS
      Detect missing/broken OvaDue components; optionally auto-correct safe issues.
    .PARAMETER RepairSafe
      Create missing ensureDirectories, clear stale streamlit.pid when process is dead.
    .PARAMETER WriteReport
      Write data\self-heal-report.txt
    .PARAMETER StartupMode
      Lightweight mode for Launch Control open (same checks; quieter logging intent).
    #>
    param(
        [switch]$RepairSafe,
        [switch]$WriteReport,
        [switch]$StartupMode
    )

    if (-not $script:DeployRoot) {
        throw 'Initialize-OvaDueDeploy must be called before Invoke-OvaDueHealthCheck.'
    }

    $root = $script:DeployRoot
    $issues = New-Object System.Collections.Generic.List[object]
    $needsInstallServer = $false
    $needsUserAction = $false
    $autoFixedCount = 0

    function Add-Issue {
        param($Issue)
        [void]$issues.Add($Issue)
        if ($Issue.Action -eq 'InstallServer') { $script:needsInstallServerFlag = $true }
        if ($Issue.Action -eq 'UserAction') { $script:needsUserActionFlag = $true }
        if ($Issue.AutoFixed) { $script:autoFixedCountFlag++ }
    }
    $script:needsInstallServerFlag = $false
    $script:needsUserActionFlag = $false
    $script:autoFixedCountFlag = 0

    # --- ensureDirectories (safe auto-correct) ---
    $rules = $null
    try { $rules = Get-OvaDueIncludeRules } catch {
        Add-Issue (New-OvaDueHealthIssue -Id 'package-include' -Severity 'ERROR' `
            -Message "Cannot read deploy\package-include.json: $($_.Exception.Message)" `
            -Guidance "Copy a complete OvaDue folder (must include deploy\package-include.json), or run Install from Git." `
            -Action UserAction)
    }

    $ensureDirs = @('data', 'uploads')
    if ($rules -and $rules.ensureDirectories) { $ensureDirs = @($rules.ensureDirectories) }
    foreach ($dir in $ensureDirs) {
        $targetDir = Join-Path $root ($dir -replace '/', '\')
        if (Test-Path -LiteralPath $targetDir) {
            Add-Issue (New-OvaDueHealthIssue -Id "dir:$dir" -Severity 'OK' -Message "Directory present: $dir")
        } elseif ($RepairSafe) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
            Add-Issue (New-OvaDueHealthIssue -Id "dir:$dir" -Severity 'WARN' `
                -Message "Created missing directory: $dir" -Action AutoFixed -AutoFixed)
        } else {
            Add-Issue (New-OvaDueHealthIssue -Id "dir:$dir" -Severity 'WARN' `
                -Message "Missing directory: $dir" `
                -Guidance "Click Check & Repair, or run: New-Item -ItemType Directory -Force -Path `"$targetDir`"" `
                -Action UserAction)
        }
    }

    # --- Python launcher ---
    $pythonOk = $false
    $pythonDetail = ''
    try {
        $pythonCmd = Resolve-OvaDuePythonCommand
        $argDisplay = if ($pythonCmd.Arguments -and $pythonCmd.Arguments.Count -gt 0) {
            ' ' + (($pythonCmd.Arguments) -join ' ')
        } else { '' }
        $outLog = Join-Path $script:DataDir 'python-probe.out.log'
        $errLog = Join-Path $script:DataDir 'python-probe.err.log'
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $verArgs = @($pythonCmd.Arguments + @('--version'))
            $verText = & $pythonCmd.FileName @verArgs 2> $errLog
            $verExit = $LASTEXITCODE
            if ($null -ne $verText) {
                Set-Content -LiteralPath $outLog -Value ($verText | Out-String) -Encoding UTF8
            }
            $verText = if ($verText) { ($verText | Out-String).Trim() } else { '' }
            if (-not $verText -and (Test-Path -LiteralPath $errLog)) {
                $verText = (Get-Content -LiteralPath $errLog -Raw -ErrorAction SilentlyContinue).Trim()
            }
        } finally {
            $ErrorActionPreference = $prevEap
        }
        if ($verExit -eq 0) {
            $pythonOk = $true
            $pythonDetail = "$($pythonCmd.FileName)$argDisplay ($verText)"
            Add-Issue (New-OvaDueHealthIssue -Id 'python' -Severity 'OK' -Message "Python available: $pythonDetail")
        } else {
            throw ("Launcher exited {0}: {1}" -f $verExit, $verText)
        }
    } catch {
        Add-Issue (New-OvaDueHealthIssue -Id 'python' -Severity 'ERROR' `
            -Message "Python / py launcher not available: $($_.Exception.Message)" `
            -Guidance @(
                '1. Install Python 3.11+ from https://www.python.org/downloads/windows/'
                '2. During setup, tick "Add python.exe to PATH".'
                '3. Close and re-open Launch Control.'
                '4. Click Check & Repair, then confirm Install Server when prompted.'
                "5. Or from PowerShell in $root : py -3 --version"
            ) -join "`r`n" `
            -Action UserAction)
    }

    # --- App layout ---
    foreach ($rel in @('app.py', 'ovadue', 'pages', 'requirements.txt')) {
        $full = Join-Path $root $rel
        if (Test-Path -LiteralPath $full) {
            Add-Issue (New-OvaDueHealthIssue -Id "layout:$rel" -Severity 'OK' -Message "Present: $rel")
        } else {
            Add-Issue (New-OvaDueHealthIssue -Id "layout:$rel" -Severity 'ERROR' `
                -Message "Missing required path: $rel" `
                -Guidance "This is not a complete OvaDue copy. Re-copy the full folder, or use Install from Git / extract an OvaDue_*.zip that includes app code." `
                -Action UserAction)
        }
    }

    $missingLayout = Test-OvaDueDeployLayout -Root $root
    if ($missingLayout.Count -gt 0) {
        Add-Issue (New-OvaDueHealthIssue -Id 'deploy-layout' -Severity 'ERROR' `
            -Message ("Missing deploy layout files: " + ($missingLayout -join ', ')) `
            -Guidance "Required: app.py, requirements.txt, launch control.cmd, scripts\OvaDue-*.ps1/.cmd, deploy\*.json. Copy the full project or Install from Git." `
            -Action UserAction)
    } else {
        Add-Issue (New-OvaDueHealthIssue -Id 'deploy-layout' -Severity 'OK' -Message 'Deploy layout files present.')
    }

    # --- Streamlit config ---
    $streamlitConfig = Join-Path $root '.streamlit\config.toml'
    if (Test-Path -LiteralPath $streamlitConfig) {
        Add-Issue (New-OvaDueHealthIssue -Id 'streamlit-config' -Severity 'OK' -Message 'Present: .streamlit\config.toml')
    } else {
        Add-Issue (New-OvaDueHealthIssue -Id 'streamlit-config' -Severity 'WARN' `
            -Message 'Missing .streamlit\config.toml (defaults may still work; port/address may differ).' `
            -Guidance "Copy .streamlit\config.toml from a working install, or re-extract an OvaDue_*.zip / Import Migration Pack (includes .streamlit)." `
            -Action UserAction)
    }

    # --- venv + packages ---
    $config = $null
    try { $config = Get-OvaDueDeployConfig } catch {
        Add-Issue (New-OvaDueHealthIssue -Id 'deploy-config' -Severity 'ERROR' `
            -Message "Cannot read deploy\deploy-config.json: $($_.Exception.Message)" `
            -Guidance 'Restore deploy\deploy-config.json from a working machine or migration pack.' `
            -Action UserAction)
    }

    $venvRel = '.venv'
    if ($config -and $config.venvRelativePath) { $venvRel = [string]$config.venvRelativePath }
    $venvPath = Join-Path $root $venvRel
    $venvUsable = $false
    if (-not (Test-Path -LiteralPath $venvPath)) {
        Add-Issue (New-OvaDueHealthIssue -Id 'venv' -Severity 'ERROR' `
            -Message "Virtual environment missing: $venvRel" `
            -Guidance "In Launch Control click Check & Repair and confirm Install Server, or click Install Server. Needs Python on PATH first." `
            -Action InstallServer)
        $script:needsInstallServerFlag = $true
    } else {
        $probe = Test-OvaDueVenvUsable -VenvPath $venvPath
        if ($probe.Usable) {
            $venvUsable = $true
            Add-Issue (New-OvaDueHealthIssue -Id 'venv' -Severity 'OK' -Message "Virtual environment usable: $venvRel")
        } else {
            Add-Issue (New-OvaDueHealthIssue -Id 'venv' -Severity 'ERROR' `
                -Message "Virtual environment broken: $($probe.Reason)" `
                -Guidance @(
                    'Common after whole-folder copy to a new machine.'
                    '1. Ensure Python 3.11+ is installed (py -3 --version).'
                    '2. In Launch Control: Check & Repair -> confirm Install Server when prompted.'
                    '   Install Server removes the broken .venv and recreates it.'
                    "3. Or manually: Remove-Item -Recurse -Force `"$venvPath`" then click Install Server."
                ) -join "`r`n" `
                -Action InstallServer)
            $script:needsInstallServerFlag = $true
        }
    }

    if ($venvUsable) {
        $pythonExe = Join-Path $venvPath 'Scripts\python.exe'
        $pkgs = Get-OvaDueRequiredPackages
        $importList = ($pkgs | ForEach-Object { $_ }) -join ', '
        $code = "import importlib`nmods = [$([string]::Join(', ', ($pkgs | ForEach-Object { "'$_'" })))]`nfailed = []`nfor m in mods:`n    try: importlib.import_module(m)`n    except Exception as e: failed.append('%s: %s' % (m, e))`nif failed:`n    raise SystemExit('; '.join(failed))`nprint('ok')"
        $pkgOut = Join-Path $script:DataDir 'package-probe.out.log'
        $pkgErr = Join-Path $script:DataDir 'package-probe.err.log'
        # Use a temp .py file to avoid quoting hell
        $probePy = Join-Path $script:DataDir 'package-probe.py'
        Set-Content -LiteralPath $probePy -Value $code -Encoding ASCII
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $pkgOutText = & $pythonExe $probePy 2> $pkgErr
            $pkgExit = $LASTEXITCODE
            if ($null -ne $pkgOutText) {
                Set-Content -LiteralPath $pkgOut -Value ($pkgOutText | Out-String) -Encoding UTF8
            } else {
                Set-Content -LiteralPath $pkgOut -Value '' -Encoding UTF8
            }
        } finally {
            $ErrorActionPreference = $prevEap
        }
        if ($pkgExit -eq 0) {
            Add-Issue (New-OvaDueHealthIssue -Id 'packages' -Severity 'OK' -Message "Key packages importable ($($pkgs.Count) from requirements.txt).")
        } else {
            $err = ''
            if (Test-Path -LiteralPath $pkgErr) { $err = (Get-Content -LiteralPath $pkgErr -Raw -ErrorAction SilentlyContinue).Trim() }
            if (-not $err -and (Test-Path -LiteralPath $pkgOut)) { $err = (Get-Content -LiteralPath $pkgOut -Raw -ErrorAction SilentlyContinue).Trim() }
            Add-Issue (New-OvaDueHealthIssue -Id 'packages' -Severity 'ERROR' `
                -Message "Package import failed: $err" `
                -Guidance "Click Check & Repair and confirm Install Server (runs pip install -r requirements.txt), or click Install Server." `
                -Action InstallServer)
            $script:needsInstallServerFlag = $true
        }
    }

    # --- Config paths that should exist (or be reachable) ---
    if ($config) {
        $pathKeys = @(
            @{ Key = 'upgradeSource'; Required = $false; Hint = 'Used by Upgrade from Push. Create the folder or edit deploy\deploy-config.json.' }
            @{ Key = 'migrationExportDirectory'; Required = $false; Hint = 'Used by Backup Migration Pack. Create C:\temp or set migrationExportDirectory.' }
            @{ Key = 'migrationImportDirectory'; Required = $false; Hint = 'Used by Import Migration Pack. Create the folder or edit deploy-config.json.' }
            @{ Key = 'pushTarget'; Required = $false; Hint = 'Network share for Package and Push. Map/create the share, run as admin if needed for admin shares (\\server\c$), or change pushTarget.' }
            @{ Key = 'gitInstallPath'; Required = $false; Hint = 'Only needed for Install from Git. Create parent folder or change gitInstallPath in deploy-config.json.' }
        )
        foreach ($item in $pathKeys) {
            $val = [string]$config.($item.Key)
            if (-not $val) {
                Add-Issue (New-OvaDueHealthIssue -Id "config:$($item.Key)" -Severity 'INFO' -Message "Config $($item.Key) is empty (optional).")
                continue
            }
            # Relative paths are relative to root
            $resolved = $val
            if (-not [System.IO.Path]::IsPathRooted($val)) {
                $resolved = Join-Path $root $val
            }
            try { $resolved = [System.IO.Path]::GetFullPath($resolved) } catch { }
            $exists = $false
            $accessError = $null
            try {
                $exists = Test-Path -LiteralPath $resolved -ErrorAction Stop
            } catch {
                $accessError = $_.Exception.Message
            }
            if ($exists) {
                Add-Issue (New-OvaDueHealthIssue -Id "config:$($item.Key)" -Severity 'OK' -Message "$($item.Key) exists: $resolved")
            } elseif ($accessError) {
                Add-Issue (New-OvaDueHealthIssue -Id "config:$($item.Key)" -Severity 'WARN' `
                    -Message "$($item.Key) not reachable: $resolved ($accessError)" `
                    -Guidance "$($item.Hint) If this is an admin share, run Launch Control elevated or use a non-admin share path." `
                    -Action UserAction)
            } else {
                Add-Issue (New-OvaDueHealthIssue -Id "config:$($item.Key)" -Severity 'WARN' `
                    -Message "$($item.Key) path does not exist: $resolved" `
                    -Guidance $item.Hint `
                    -Action UserAction)
            }
        }
    }

    # --- Port 8501 ---
    $listenerPid = 0
    try {
        $listener = Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($listener -and $listener.OwningProcess -gt 0) {
            $listenerPid = [int]$listener.OwningProcess
        }
    } catch { }
    if ($listenerPid -gt 0) {
        $procName = ''
        try { $procName = (Get-Process -Id $listenerPid -ErrorAction SilentlyContinue).ProcessName } catch { }
        Add-Issue (New-OvaDueHealthIssue -Id 'port-8501' -Severity 'INFO' `
            -Message "Port 8501 is in use by PID $listenerPid ($procName). Not killed." `
            -Guidance "If this is OvaDue, use Start Dashboard / Refresh Status. To stop: click Stop Dashboard in Launch Control (or taskkill /PID $listenerPid /T /F only if you intend to stop it)." `
            -Action None)
    } else {
        Add-Issue (New-OvaDueHealthIssue -Id 'port-8501' -Severity 'OK' -Message 'Port 8501 is free (no listener).')
    }

    # --- Stale streamlit.pid ---
    $pidFile = Join-Path $root 'data\streamlit.pid'
    if (Test-Path -LiteralPath $pidFile) {
        $pidText = ''
        try { $pidText = (Get-Content -LiteralPath $pidFile -TotalCount 1 -ErrorAction Stop).Trim() } catch { }
        $parsedPid = 0
        $alive = $false
        if ([int]::TryParse($pidText, [ref]$parsedPid) -and $parsedPid -gt 0) {
            try {
                Get-Process -Id $parsedPid -ErrorAction Stop | Out-Null
                $alive = $true
            } catch { $alive = $false }
        }
        if ($alive) {
            Add-Issue (New-OvaDueHealthIssue -Id 'streamlit-pid' -Severity 'OK' -Message "data\streamlit.pid points to live PID $parsedPid.")
        } elseif ($RepairSafe) {
            Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
            Add-Issue (New-OvaDueHealthIssue -Id 'streamlit-pid' -Severity 'WARN' `
                -Message "Cleared stale data\streamlit.pid (was '$pidText'; process not running)." `
                -Action AutoFixed -AutoFixed)
        } else {
            Add-Issue (New-OvaDueHealthIssue -Id 'streamlit-pid' -Severity 'WARN' `
                -Message "Stale data\streamlit.pid (was '$pidText'; process not running)." `
                -Guidance 'Click Check & Repair to clear it, or delete data\streamlit.pid.' `
                -Action UserAction)
        }
    } else {
        Add-Issue (New-OvaDueHealthIssue -Id 'streamlit-pid' -Severity 'OK' -Message 'No data\streamlit.pid (dashboard not supervised).')
    }

    $needsInstallServer = [bool]$script:needsInstallServerFlag
    $needsUserAction = [bool]$script:needsUserActionFlag
    $autoFixedCount = [int]$script:autoFixedCountFlag

    $errorCount = @($issues | Where-Object { $_.Severity -eq 'ERROR' }).Count
    $warnCount = @($issues | Where-Object { $_.Severity -eq 'WARN' }).Count
    $okCount = @($issues | Where-Object { $_.Severity -eq 'OK' }).Count

    $status = if ($errorCount -gt 0) { 'UNHEALTHY' } elseif ($warnCount -gt 0) { 'WARNINGS' } else { 'HEALTHY' }

    $summaryLines = New-Object System.Collections.Generic.List[string]
    [void]$summaryLines.Add("OvaDue health check - $status")
    [void]$summaryLines.Add("Root: $root")
    [void]$summaryLines.Add("Mode: $(if ($StartupMode) { 'startup' } else { 'interactive' }); RepairSafe=$RepairSafe")
    [void]$summaryLines.Add("OK=$okCount WARN=$warnCount ERROR=$errorCount AutoFixed=$autoFixedCount NeedsInstallServer=$needsInstallServer")
    [void]$summaryLines.Add('')
    foreach ($issue in $issues) {
        $fixed = if ($issue.AutoFixed) { ' [AUTO-FIXED]' } else { '' }
        [void]$summaryLines.Add("[$($issue.Severity)] $($issue.Id): $($issue.Message)$fixed")
        if ($issue.Guidance -and $issue.Severity -ne 'OK') {
            foreach ($gLine in ($issue.Guidance -split "`r?`n")) {
                [void]$summaryLines.Add("    $gLine")
            }
        }
    }
    if ($needsInstallServer) {
        [void]$summaryLines.Add('')
        [void]$summaryLines.Add('NEXT: In Launch Control confirm Install Server when prompted, or click Install Server.')
    }
    if ($needsUserAction -and -not $needsInstallServer) {
        [void]$summaryLines.Add('')
        [void]$summaryLines.Add('NEXT: Follow UserAction guidance above (Python install, missing files, config paths).')
    }

    $reportText = ($summaryLines -join "`r`n") + "`r`n"
    $reportPath = Join-Path $script:DataDir 'self-heal-report.txt'
    if ($WriteReport) {
        if (-not (Test-Path -LiteralPath $script:DataDir)) {
            New-Item -ItemType Directory -Path $script:DataDir -Force | Out-Null
        }
        $header = "Generated: $(Get-Date -Format o)`r`n"
        Set-Content -LiteralPath $reportPath -Value ($header + $reportText) -Encoding UTF8
    }

    if (-not $StartupMode) {
        Write-DeployLog "Health check finished: $status (errors=$errorCount warns=$warnCount autoFixed=$autoFixedCount)" $(if ($errorCount -gt 0) { 'WARN' } else { 'INFO' })
    }

    # PS 5.1: prefer PSCustomObject over [ordered] return (avoids "Argument types do not match")
    $issueArray = @($issues.ToArray())
    return [pscustomobject]@{
        Status = [string]$status
        Root = [string]$root
        Issues = $issueArray
        ErrorCount = [int]$errorCount
        WarnCount = [int]$warnCount
        OkCount = [int]$okCount
        AutoFixedCount = [int]$autoFixedCount
        NeedsInstallServer = [bool]$needsInstallServer
        NeedsUserAction = [bool]$needsUserAction
        ReportPath = [string]$reportPath
        ReportText = [string]$reportText
        PythonOk = [bool]$pythonOk
        VenvUsable = [bool]$venvUsable
        Port8501Pid = [int]$listenerPid
    }
}


