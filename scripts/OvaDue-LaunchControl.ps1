#Requires -Version 5.1
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$ErrorActionPreference = 'Stop'
$script:Root = Split-Path -Parent $PSScriptRoot
$script:Python = Join-Path $script:Root '.venv\Scripts\python.exe'
$script:App = Join-Path $script:Root 'app.py'
$script:DataDir = Join-Path $script:Root 'data'
$script:UploadsDir = Join-Path $script:Root 'uploads'
$script:PidFile = Join-Path $script:DataDir 'streamlit.pid'
$script:LogFile = Join-Path $script:DataDir 'streamlit.log'
$script:ErrorLogFile = Join-Path $script:DataDir 'streamlit-error.log'
$script:StartupLogFile = Join-Path $script:DataDir 'launchcontrol-startup.log'
$script:LastStatus = ''
$script:LogOffset = [int64]0
$script:FollowLogs = $false
$script:ConsoleChars = 0
$script:DashboardPort = 8501
$script:DashboardHealthUrl = 'http://127.0.0.1:8501/_stcore/health'
$script:DashboardUrl = 'http://127.0.0.1:8501'

function Initialize-LaunchControlConfig {
    $configPath = Join-Path $script:Root 'launch control\launch-control.json'
    if (-not (Test-Path -LiteralPath $configPath)) {
        $configPath = Join-Path $PSScriptRoot 'launch-control.json'
    }
    try {
        $config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
        if ($config.processFallback.port) {
            $script:DashboardPort = [int]$config.processFallback.port
        }
        if ($config.healthUrl) {
            $script:DashboardHealthUrl = [string]$config.healthUrl
        }
    } catch { }
    $script:DashboardUrl = "http://127.0.0.1:$($script:DashboardPort)"
}

function Write-StartupLog {
    param([string]$Message)
    try {
        if (-not (Test-Path -LiteralPath $script:DataDir)) {
            New-Item -ItemType Directory -Path $script:DataDir -Force | Out-Null
        }
        Add-Content -LiteralPath $script:StartupLogFile -Value "[$(Get-Date -Format o)] $Message" -Encoding UTF8
    } catch { }
}

function Show-LaunchControlStartupError {
    param([string]$Message)

    Write-StartupLog "FATAL: $Message"
    $logPath = Join-Path $script:DataDir 'launchcontrol-crash.log'
    Add-Content -LiteralPath $logPath -Value "[$(Get-Date -Format o)] [Startup] $Message" -Encoding UTF8
    [System.Windows.Forms.MessageBox]::Show(
        "OvaDue Launch Control failed to start.`r`n`r`n$Message`r`n`r`nSee: $logPath",
        'OvaDue Launch Control',
        'OK',
        'Error'
    ) | Out-Null
}

try {
New-Item -ItemType Directory -Path $script:DataDir, $script:UploadsDir -Force | Out-Null
Initialize-LaunchControlConfig
Write-StartupLog "Launch Control starting (dashboard port $($script:DashboardPort))"

function Get-DashboardPid {
    if (-not (Test-Path -LiteralPath $script:PidFile)) { return 0 }
    try {
        $processId = 0
        $text = (Get-Content -LiteralPath $script:PidFile -TotalCount 1 -ErrorAction Stop).Trim()
        if ([int]::TryParse($text, [ref]$processId)) {
            Get-Process -Id $processId -ErrorAction Stop | Out-Null
            return $processId
        }
    } catch { }
    Remove-Item -LiteralPath $script:PidFile -Force -ErrorAction SilentlyContinue
    return 0
}

function Get-DashboardListeningPort {
    param([int]$ProcessId)
    if ($ProcessId -le 0) { return 0 }
    try {
        $listener = Get-NetTCPConnection -OwningProcess $ProcessId -State Listen -ErrorAction Stop |
            Where-Object { $_.LocalPort -gt 0 } |
            Select-Object -First 1
        if ($listener) { return [int]$listener.LocalPort }
    } catch { }
    return 0
}

function Get-StreamlitListenerPid {
    param([int]$Port = $script:DashboardPort)
    try {
        $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1
        if ($listener -and $listener.OwningProcess -gt 0) {
            return [int]$listener.OwningProcess
        }
    } catch { }
    return 0
}

function Add-EventLine {
    param([string]$Message, [string]$Level = 'INFO')
    if (-not $script:Events) { return }
    $line = "[$(Get-Date -Format 'HH:mm:ss')] [$Level] $Message`r`n"
    $script:Events.AppendText($line)
    $script:ConsoleChars += $line.Length
    if ($script:ConsoleChars -gt 80000 -and $script:Events.TextLength -gt 60000) {
        $script:Events.Text = $script:Events.Text.Substring($script:Events.TextLength - 60000)
        $script:ConsoleChars = $script:Events.TextLength
    }
    $script:Events.SelectionStart = $script:Events.TextLength
    $script:Events.ScrollToCaret()
}

function Test-DashboardHealth {
    param([int]$ProcessId)
    if ($ProcessId -le 0) { return $false }
    $port = Get-DashboardListeningPort -ProcessId $ProcessId
    if ($port -le 0) { $port = $script:DashboardPort }
    $healthUrl = "http://127.0.0.1:$port/_stcore/health"
    try {
        $request = [System.Net.WebRequest]::Create($healthUrl)
        $request.Timeout = 750
        $response = $request.GetResponse()
        $response.Close()
        return $true
    } catch { return $false }
}

function Refresh-Status {
    $processId = Get-DashboardPid
    if ($processId -le 0) {
        $processId = Get-StreamlitListenerPid
        if ($processId -gt 0) {
            Set-Content -LiteralPath $script:PidFile -Value $processId -NoNewline
            Add-EventLine "Adopted existing Streamlit listener PID $processId."
        }
    }
    $healthy = Test-DashboardHealth -ProcessId $processId
    $listeningPort = if ($processId -gt 0) { Get-DashboardListeningPort -ProcessId $processId } else { 0 }
    $displayPort = if ($listeningPort -gt 0) { $listeningPort } else { $script:DashboardPort }
    if ($processId -gt 0) {
        $script:Status.Text = if ($healthy) { "Running on port $displayPort" } else { 'Starting' }
        $script:Status.ForeColor = if ($healthy) { [System.Drawing.Color]::ForestGreen } else { [System.Drawing.Color]::DarkOrange }
        $script:PidLabel.Text = "PID $processId · port $displayPort"
        if ($listeningPort -gt 0) {
            $script:PortLabel.Text = "Port $listeningPort (listening)"
        } else {
            $script:PortLabel.Text = "Port $($script:DashboardPort) (starting)"
        }
        $script:Health.Text = if ($healthy) { 'Health: ok' } else { 'Health: starting or unavailable' }
    } else {
        $script:Status.Text = 'Stopped'; $script:Status.ForeColor = [System.Drawing.Color]::Firebrick
        $script:PidLabel.Text = 'PID -'
        $script:PortLabel.Text = "Port $($script:DashboardPort) (not listening)"
        $script:Health.Text = 'Health: not running'
    }
    $state = "$($script:Status.Text)|$processId|$displayPort|$($script:Health.Text)"
    if ($state -ne $script:LastStatus) {
        Add-EventLine "Status changed: $($script:Status.Text), $($script:PidLabel.Text)"
        $script:LastStatus = $state
    }
}

function Start-Dashboard {
    $existing = Get-DashboardPid
    if ($existing -le 0) { $existing = Get-StreamlitListenerPid }
    if ($existing -gt 0) { Add-EventLine "Dashboard already running as PID $existing."; return }
    if (-not (Test-Path -LiteralPath $script:Python) -or -not (Test-Path -LiteralPath $script:App)) {
        Add-EventLine 'Missing .venv Python or app.py.' 'ERROR'
        [System.Windows.Forms.MessageBox]::Show('Missing .venv Python or app.py.', 'OvaDue Launch Control') | Out-Null
        return
    }
    $streamlitArgs = '-m streamlit run "{0}" --server.headless true --server.address 0.0.0.0 --server.port {1}' -f $script:App, $script:DashboardPort
    $process = Start-Process -FilePath $script:Python -ArgumentList $streamlitArgs -WorkingDirectory $script:Root -WindowStyle Hidden -PassThru -RedirectStandardOutput $script:LogFile -RedirectStandardError $script:ErrorLogFile
    Set-Content -LiteralPath $script:PidFile -Value $process.Id -NoNewline
    Add-EventLine "Started dashboard as PID $($process.Id)."
}

function Stop-Dashboard {
    $processId = Get-DashboardPid
    if ($processId -le 0) { Add-EventLine 'Dashboard is already stopped.'; return }
    & taskkill.exe /PID $processId /T /F | Out-Null
    Remove-Item -LiteralPath $script:PidFile -Force -ErrorAction SilentlyContinue
    Add-EventLine "Stopped dashboard process tree for PID $processId."
}

function Update-LogTail {
    if (-not (Test-Path -LiteralPath $script:LogFile)) { return }
    try {
        $file = Get-Item -LiteralPath $script:LogFile
        if ($file.Length -lt $script:LogOffset) { $script:LogOffset = 0 }
        $stream = [System.IO.File]::Open($script:LogFile, 'Open', 'Read', 'ReadWrite')
        try {
            [void]$stream.Seek($script:LogOffset, [System.IO.SeekOrigin]::Begin)
            $reader = New-Object System.IO.StreamReader($stream)
            $text = $reader.ReadToEnd(); $reader.Dispose(); $script:LogOffset = $stream.Length
        } finally { $stream.Dispose() }
        $lines = @($text -split "`r?`n" | Where-Object { $_ })
        if (-not $script:FollowLogs) { $lines = @($lines | Where-Object { $_ -match '(?i)error|warn|exception|failed' }) }
        foreach ($line in @($lines | Select-Object -Last 40)) { Add-EventLine $line 'LOG' }
    } catch { }
}

$deployScript = Join-Path $PSScriptRoot 'OvaDue-Deploy.ps1'
if (-not (Test-Path -LiteralPath $deployScript)) {
    throw "Missing deploy script: $deployScript"
}
. $deployScript
Initialize-OvaDueDeploy -Root $script:Root -LogAction {
    param([string]$Message, [string]$Level = 'INFO')
    Add-EventLine $Message $Level
}

function Show-OvaDueSetupHelp {
    param([string]$Topic = 'overview')

    $helpText = Get-OvaDueSetupHelp -Root $script:Root -Topic $Topic
    [System.Windows.Forms.MessageBox]::Show($helpText, 'OvaDue Setup Help') | Out-Null
}

function Invoke-DeployAction {
    param(
        [string]$Title,
        [scriptblock]$Action
    )

    try {
        $missing = Test-OvaDueDeployLayout -Root $script:Root
        if ($missing.Count -gt 0) {
            throw ("Missing required files:`r`n- " + ($missing -join "`r`n- "))
        }

        Add-EventLine "$Title started..."
        $result = & $Action
        $summary = ''
        if ($null -ne $result -and $result -is [System.Collections.IDictionary]) {
            $summary = ($result.GetEnumerator() | ForEach-Object { "{0}={1}" -f $_.Key, $_.Value }) -join ', '
        }
        Add-EventLine "$Title completed. $summary"
        [System.Windows.Forms.MessageBox]::Show("$Title completed successfully.`r`n$summary", 'OvaDue Launch Control') | Out-Null
    } catch {
        $message = $_.Exception.Message
        Write-DeployLog "$Title failed: $message" 'ERROR'
        Add-EventLine "$Title failed: $message" 'ERROR'

        $helpTopic = 'overview'
        if ($message -match 'Python was not found|virtual environment|pip|requirements') { $helpTopic = 'installServer' }
        elseif ($message -match 'Git is not installed|git command failed|gitRepositoryUrl') { $helpTopic = 'installFromGit' }
        elseif ($message -match 'Missing required files|Missing deploy script|deploy-config|package-include') { $helpTopic = 'missingFiles' }
        elseif ($message -match 'migration|Migration pack|OvaDue_Migration_') { $helpTopic = 'migration' }

        $helpText = Get-OvaDueSetupHelp -Root $script:Root -Topic $helpTopic
        $dialogText = "$Title failed.`r`n`r`n$message`r`n`r`n$helpText"
        [System.Windows.Forms.MessageBox]::Show($dialogText, 'OvaDue Launch Control', 'OK', 'Error') | Out-Null
    }
}

function Get-MigrationDialogDirectory {
    param([ValidateSet('export','import')]$Mode)

    $dir = if ($Mode -eq 'export') {
        Resolve-OvaDueMigrationExportDirectory
    } else {
        $config = Get-OvaDueDeployConfig
        $configured = [string]$config.migrationImportDirectory
        if ($configured) {
            [System.IO.Path]::GetFullPath($configured)
        } elseif ([string]$config.upgradeSource) {
            [System.IO.Path]::GetFullPath([string]$config.upgradeSource)
        } else {
            'C:\temp'
        }
    }

    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    return $dir
}

function Invoke-BackupMigrationPackUi {
    $dialog = New-Object System.Windows.Forms.SaveFileDialog
    $dialog.Title = 'Save OvaDue migration pack'
    $dialog.Filter = 'OvaDue migration pack (*.zip)|*.zip'
    $dialog.FileName = ("OvaDue_Migration_{0}_{1}.zip" -f $env:COMPUTERNAME, (Get-Date -Format 'yyyyMMdd_HHmmss'))
    $dialog.InitialDirectory = Get-MigrationDialogDirectory -Mode export
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        Add-EventLine 'Backup Migration Pack cancelled.'
        return
    }
    $zipPath = $dialog.FileName
    Invoke-DeployAction 'Backup Migration Pack' {
        Invoke-OvaDueExportMigrationPack -OutputZipPath $zipPath
    }
}

function Invoke-ImportMigrationPackUi {
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Title = 'Select OvaDue migration pack to import'
    $dialog.Filter = 'OvaDue migration pack (*.zip)|*.zip|All files (*.*)|*.*'
    $dialog.InitialDirectory = Get-MigrationDialogDirectory -Mode import
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        Add-EventLine 'Import Migration Pack cancelled.'
        return
    }

    $zipPath = $dialog.FileName
    $confirm = [System.Windows.Forms.MessageBox]::Show(
        ("Import will overwrite matching data/config paths in:`r`n{0}`r`n`r`nPack:`r`n{1}`r`n`r`nApp code is not replaced. Continue?" -f $script:Root, $zipPath),
        'Import Migration Pack',
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Warning
    )
    if ($confirm -ne [System.Windows.Forms.DialogResult]::Yes) {
        Add-EventLine 'Import Migration Pack cancelled.'
        return
    }

    Invoke-DeployAction 'Import Migration Pack' {
        Invoke-OvaDueImportMigrationPack -ZipPath $zipPath -PidFile $script:PidFile
    }
}

function Write-HealthIssuesToEvents {
    param($Result)

    if (-not $Result) { return }
    Add-EventLine ("Health: {0} (OK={1} WARN={2} ERROR={3} AutoFixed={4})" -f `
        $Result.Status, $Result.OkCount, $Result.WarnCount, $Result.ErrorCount, $Result.AutoFixedCount)
    foreach ($issue in @($Result.Issues)) {
        if ($issue.Severity -eq 'OK') { continue }
        $level = if ($issue.Severity -eq 'ERROR') { 'ERROR' } elseif ($issue.Severity -eq 'WARN') { 'WARN' } else { 'INFO' }
        $suffix = if ($issue.AutoFixed) { ' [AUTO-FIXED]' } else { '' }
        Add-EventLine ("{0}: {1}{2}" -f $issue.Id, $issue.Message, $suffix) $level
    }
    if ($Result.ReportPath -and (Test-Path -LiteralPath $Result.ReportPath)) {
        Add-EventLine "Self-heal report: $($Result.ReportPath)"
    }
}

function Invoke-StartupHealthCheck {
    try {
        $result = Invoke-OvaDueHealthCheck -RepairSafe -StartupMode
        Write-HealthIssuesToEvents -Result $result
        if ($result.NeedsInstallServer) {
            Add-EventLine 'Runtime needs Install Server (venv/packages). Click Check & Repair or Install Server.' 'WARN'
        }
        if ($result.Status -eq 'UNHEALTHY') {
            Add-EventLine 'Startup health: issues found. Open Check & Repair for guided steps.' 'WARN'
        }
    } catch {
        Add-EventLine "Startup health check failed: $($_.Exception.Message)" 'WARN'
        Write-StartupLog "Startup health check failed: $($_.Exception.Message)"
    }
}

function Invoke-CheckAndRepairUi {
    Add-EventLine 'Check & Repair started...'
    try {
        $result = Invoke-OvaDueHealthCheck -RepairSafe -WriteReport
        Write-HealthIssuesToEvents -Result $result

        if ($result.NeedsInstallServer) {
            if (-not $result.PythonOk) {
                $help = Get-OvaDueSetupHelp -Root $script:Root -Topic 'installServer'
                $msg = @"
Check & Repair found a broken or missing Python runtime environment, and Python/py is not available on PATH.

Install Python first, then run Check & Repair again.

$help

Full report: $($result.ReportPath)
"@
                [System.Windows.Forms.MessageBox]::Show($msg.Trim(), 'Check & Repair - Python required', 'OK', 'Error') | Out-Null
                return
            }

            $confirm = [System.Windows.Forms.MessageBox]::Show(
                @"
Check & Repair found a missing or broken .venv / packages (common after copying the whole folder to a new PC).

Install Server will recreate .venv and run: pip install -r requirements.txt
This can take several minutes and needs network access for pip.

Root: $($script:Root)

Continue with Install Server?
"@.Trim(),
                'Check & Repair - Install Server',
                [System.Windows.Forms.MessageBoxButtons]::YesNo,
                [System.Windows.Forms.MessageBoxIcon]::Question
            )
            if ($confirm -eq [System.Windows.Forms.DialogResult]::Yes) {
                Invoke-DeployAction 'Install Server (from Check & Repair)' {
                    Invoke-OvaDueInstallServer
                }
                $result = Invoke-OvaDueHealthCheck -RepairSafe -WriteReport
                Write-HealthIssuesToEvents -Result $result
            } else {
                Add-EventLine 'Install Server declined. Click Install Server later after Python is ready.' 'WARN'
            }
        }

        $title = "Check & Repair - $($result.Status)"
        $icon = if ($result.Status -eq 'HEALTHY') {
            [System.Windows.Forms.MessageBoxIcon]::Information
        } elseif ($result.Status -eq 'WARNINGS') {
            [System.Windows.Forms.MessageBoxIcon]::Warning
        } else {
            [System.Windows.Forms.MessageBoxIcon]::Error
        }

        $userSteps = @($result.Issues | Where-Object { $_.Severity -ne 'OK' -and $_.Guidance } | ForEach-Object {
            "- $($_.Id): $($_.Message)`r`n  $($_.Guidance)"
        })
        $stepsBlock = if ($userSteps.Count -gt 0) {
            "`r`n`r`nActions / guidance:`r`n" + ($userSteps -join "`r`n`r`n")
        } else {
            "`r`n`r`nNo further action required. You can click Start Dashboard."
        }

        $body = @"
Status: $($result.Status)
OK=$($result.OkCount)  WARN=$($result.WarnCount)  ERROR=$($result.ErrorCount)  AutoFixed=$($result.AutoFixedCount)

Report written to:
$($result.ReportPath)
$stepsBlock

Next steps if healthy:
1. Click Start Dashboard
2. Click Open Dashboard (http://127.0.0.1:8501)
"@.Trim()

        # MessageBox has practical length limits; truncate but keep report path
        if ($body.Length -gt 3500) {
            $body = $body.Substring(0, 3400) + "`r`n`r`n...(truncated)`r`nSee full report:`r`n$($result.ReportPath)"
        }
        [System.Windows.Forms.MessageBox]::Show($body, $title, 'OK', $icon) | Out-Null
        Add-EventLine "Check & Repair finished: $($result.Status)"
    } catch {
        $message = $_.Exception.Message
        Add-EventLine "Check & Repair failed: $message" 'ERROR'
        $help = Get-OvaDueSetupHelp -Root $script:Root -Topic 'healthCheck'
        [System.Windows.Forms.MessageBox]::Show(
            "Check & Repair failed.`r`n`r`n$message`r`n`r`n$help",
            'OvaDue Launch Control',
            'OK',
            'Error'
        ) | Out-Null
    }
}


$form = New-Object System.Windows.Forms.Form
$form.AutoScaleMode = [System.Windows.Forms.AutoScaleMode]::None
$form.Text = 'OvaDue Launch Control'; $form.Size = New-Object System.Drawing.Size(1040, 720); $form.MinimumSize = New-Object System.Drawing.Size(900, 600)
$form.StartPosition = 'CenterScreen'; $form.Font = New-Object System.Drawing.Font('Segoe UI', 9)

$header = New-Object System.Windows.Forms.Panel
$header.Dock = 'Top'
$header.Height = 76
$header.BackColor = [System.Drawing.Color]::FromArgb(31, 66, 117)
$title = New-Object System.Windows.Forms.Label
$title.Text = 'OvaDue Launch Control'
$title.AutoSize = $true
$title.ForeColor = [System.Drawing.Color]::White
$title.Font = New-Object System.Drawing.Font('Segoe UI Semibold', 16)
$title.Location = New-Object System.Drawing.Point(18, 13)
[void]$header.Controls.Add($title)
$subTitle = New-Object System.Windows.Forms.Label
$subTitle.Text = 'Start, stop, diagnose, Check & Repair, deploy, and migrate the local Streamlit dashboard.'
$subTitle.AutoSize = $true
$subTitle.ForeColor = [System.Drawing.Color]::Gainsboro
$subTitle.Location = New-Object System.Drawing.Point(20, 46)
[void]$header.Controls.Add($subTitle)

# Single Fill container below the header; avoids multiple same-edge Dock siblings directly on the form.
$body = New-Object System.Windows.Forms.Panel
$body.Dock = 'Fill'
[void]$form.Controls.Add($body)
[void]$form.Controls.Add($header)

$split = New-Object System.Windows.Forms.SplitContainer
$split.Dock = 'Fill'
$split.FixedPanel = 'Panel1'
$split.IsSplitterFixed = $true
$split.BackColor = [System.Drawing.Color]::FromArgb(243, 245, 249)
[void]$body.Controls.Add($split)
$form.Add_Load({
    $split.Panel1MinSize = 250
    $split.Panel2MinSize = 320
    $distance = [Math]::Min(286, ($split.Width - $split.Panel2MinSize - 4))
    if ($distance -lt $split.Panel1MinSize) { $distance = $split.Panel1MinSize }
    $split.SplitterDistance = $distance
    $split.PerformLayout()
    $body.PerformLayout()
    $form.PerformLayout()
})

$rail = New-Object System.Windows.Forms.FlowLayoutPanel
$rail.Dock = 'Fill'
$rail.Padding = New-Object System.Windows.Forms.Padding(16, 12, 16, 16)
$rail.FlowDirection = 'TopDown'
$rail.WrapContents = $false
$rail.BackColor = [System.Drawing.Color]::FromArgb(243, 245, 249)
$rail.AutoScroll = $true
[void]$split.Panel1.Controls.Add($rail)
function Add-RailLabel([string]$Text, [System.Drawing.Font]$Font = $null) {
    $label = New-Object System.Windows.Forms.Label
    $label.Text = $Text
    $label.Width = 250
    $label.AutoSize = $false
    $label.TextAlign = [System.Drawing.ContentAlignment]::MiddleLeft
    if ($Font) {
        $label.Font = $Font
        $label.Height = [Math]::Max(28, [int][Math]::Ceiling($Font.GetHeight() + 8))
    } else {
        $label.Height = 24
    }
    [void]$rail.Controls.Add($label)
    return $label
}
function Add-RailButton([string]$Text, [scriptblock]$Action) { $button = New-Object System.Windows.Forms.Button; $button.Text = $Text; $button.Width = 250; $button.Height = 34; $button.Add_Click($Action); [void]$rail.Controls.Add($button); return $button }
Add-RailLabel 'Status' | Out-Null
$script:Status = Add-RailLabel 'Stopped' (New-Object System.Drawing.Font('Segoe UI Semibold', 15))
$script:PidLabel = Add-RailLabel 'PID -'
$script:PortLabel = Add-RailLabel "Port $($script:DashboardPort) (not listening)"
$script:Health = Add-RailLabel 'Health: not checked'
Add-RailLabel 'Mode: supervised Streamlit session process' | Out-Null
Add-RailButton 'Start Dashboard' { Start-Dashboard; Refresh-Status } | Out-Null
Add-RailButton 'Stop Dashboard' { Stop-Dashboard; Refresh-Status } | Out-Null
Add-RailButton 'Restart Dashboard' { Stop-Dashboard; Start-Sleep -Milliseconds 400; Start-Dashboard; Refresh-Status } | Out-Null
Add-RailButton 'Refresh Status' { Refresh-Status } | Out-Null
$follow = Add-RailButton 'Follow Logs: OFF' { $script:FollowLogs = -not $script:FollowLogs; $this.Text = if ($script:FollowLogs) { 'Follow Logs: ON' } else { 'Follow Logs: OFF' }; Add-EventLine "Follow logs: $($script:FollowLogs)" }
Add-RailButton 'Open Dashboard' { Start-Process $script:DashboardUrl } | Out-Null
Add-RailButton 'Open Uploads Folder' { Start-Process explorer.exe -ArgumentList $script:UploadsDir } | Out-Null
Add-RailButton 'Open Logs Folder' { Start-Process explorer.exe -ArgumentList $script:DataDir } | Out-Null
Add-RailButton 'Run Diagnostics' { Set-Content -LiteralPath (Join-Path $script:DataDir 'diagnostics.requested') -Value (Get-Date -Format o); Add-EventLine 'Diagnostics request recorded.' } | Out-Null
Add-RailButton 'Check & Repair' { Invoke-CheckAndRepairUi } | Out-Null
Add-RailLabel 'Deploy' (New-Object System.Drawing.Font('Segoe UI Semibold', 10)) | Out-Null
Add-RailButton 'Setup Help' { Show-OvaDueSetupHelp } | Out-Null
Add-RailButton 'Install from Git' { Invoke-DeployAction 'Install from Git' { Invoke-OvaDueInstallFromGit -LaunchControl } } | Out-Null
Add-RailButton 'Install Server' { Invoke-DeployAction 'Install Server' { Invoke-OvaDueInstallServer } } | Out-Null
Add-RailButton 'Package and Push Update' { Invoke-DeployAction 'Package and Push Update' { Invoke-OvaDuePackageAndPush } } | Out-Null
Add-RailButton 'Upgrade from Push' { Invoke-DeployAction 'Upgrade from Push' { Invoke-OvaDueUpgradeFromPush -PidFile $script:PidFile } } | Out-Null
Add-RailLabel 'Migration' (New-Object System.Drawing.Font('Segoe UI Semibold', 10)) | Out-Null
Add-RailButton 'Backup Migration Pack' { Invoke-BackupMigrationPackUi } | Out-Null
Add-RailButton 'Import Migration Pack' { Invoke-ImportMigrationPackUi } | Out-Null
Add-RailButton 'Migration Help' { Show-OvaDueSetupHelp -Topic 'migration' } | Out-Null
Add-RailButton 'Health Check Help' { Show-OvaDueSetupHelp -Topic 'healthCheck' } | Out-Null

$content = New-Object System.Windows.Forms.Panel
$content.Dock = 'Fill'
[void]$split.Panel2.Controls.Add($content)

$eventsHeader = New-Object System.Windows.Forms.Label
$eventsHeader.Text = 'Events / issues (status changes + WARN/ERROR; use Follow logs for full tail)'
$eventsHeader.Dock = 'Top'
$eventsHeader.Height = 28
$eventsHeader.Padding = New-Object System.Windows.Forms.Padding(10, 6, 0, 0)
$eventsHeader.BackColor = [System.Drawing.Color]::FromArgb(32, 32, 32)
$eventsHeader.ForeColor = [System.Drawing.Color]::White

$script:Events = New-Object System.Windows.Forms.RichTextBox
$script:Events.Dock = 'Fill'
$script:Events.ReadOnly = $true
$script:Events.BorderStyle = 'None'
$script:Events.BackColor = [System.Drawing.Color]::FromArgb(20, 20, 20)
$script:Events.ForeColor = [System.Drawing.Color]::Gainsboro
$script:Events.Font = New-Object System.Drawing.Font('Consolas', 10)
$script:Events.WordWrap = $false
$script:Events.HideSelection = $false
[void]$content.Controls.Add($script:Events)
[void]$content.Controls.Add($eventsHeader)

function Write-CrashLog {
    param([string]$Context, $ErrorRecord)
    $text = "[$(Get-Date -Format o)] [$Context] $($ErrorRecord.Exception.Message)`r`n$($ErrorRecord.InvocationInfo.PositionMessage)`r`n"
    Add-Content -LiteralPath (Join-Path $script:DataDir 'launchcontrol-crash.log') -Value $text
}

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 4000
$timer.Add_Tick({
    try { Refresh-Status; Update-LogTail; $form.Invalidate($true) } catch { Write-CrashLog 'Timer' $_ }
})
$form.Add_Shown({
    try {
        Add-EventLine 'Launch Control ready. Closing this window does not stop the dashboard.'
        Refresh-Status
        Update-LogTail
        Invoke-StartupHealthCheck
        $timer.Start()
        $form.Refresh()
    } catch { Write-CrashLog 'Shown' $_ }
})
$form.Add_FormClosed({ $timer.Stop() })
Write-StartupLog 'Launch Control UI ready, opening window'
[void]$form.ShowDialog()
Write-StartupLog 'Launch Control closed'
} catch {
    Show-LaunchControlStartupError $_.Exception.Message
    exit 1
}