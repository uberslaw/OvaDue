#Requires -Version 5.1
# Nightly / unattended local backup. Used by Launch Control "Register daily backup"
# and by Windows Task Scheduler (OvaDue-DailyBackup).
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'OvaDue-Deploy.ps1')
Initialize-OvaDueDeploy -Root $Root
$result = Invoke-OvaDueLocalBackup
Write-Output $result.ZipPath
