@echo off
setlocal EnableExtensions
cd /d "%~dp0"
call "%~dp0scripts\OvaDue-LaunchControl.cmd" %*
exit /b %ERRORLEVEL%
