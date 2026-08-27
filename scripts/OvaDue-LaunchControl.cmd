@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PS1=%~dp0OvaDue-LaunchControl.ps1"
if not exist "%PS1%" (
  echo Missing "%PS1%"
  pause
  exit /b 1
)

set "PWSH=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%PWSH%" set "PWSH=powershell.exe"

"%PWSH%" -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File "%PS1%" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" pause
exit /b %RC%