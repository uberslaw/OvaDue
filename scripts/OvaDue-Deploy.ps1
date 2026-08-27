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

    throw 'Python was not found. Install Python 3.11+ or ensure the py launcher is available.'
}

function Invoke-OvaDueInstallServer {
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
    if (Test-Path -LiteralPath $venvPath) {
        Write-DeployLog "Existing virtual environment found; reusing $venvPath" 'WARN'
    } else {
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
    $verifyArgs = @('-c', 'import streamlit, pandas, plotly; print(streamlit.__version__)')
    $verify = Start-Process -FilePath $pythonExe -ArgumentList $verifyArgs -WorkingDirectory $script:DeployRoot -Wait -PassThru -NoNewWindow -RedirectStandardOutput (Join-Path $script:DataDir 'install-verify.out.log') -RedirectStandardError (Join-Path $script:DataDir 'install-verify.err.log')
    if ($verify.ExitCode -ne 0) {
        throw 'Server install verification failed. See data\install-verify.err.log'
    }

    Write-DeployLog 'Server install completed successfully.'
    return [ordered]@{
        VirtualEnvironment = $venvPath
        Python = $pythonExe
    }
}
