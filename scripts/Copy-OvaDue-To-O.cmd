@echo off
echo Copying OvaDue to O:\
robocopy "C:\Users\christopher.owen\OneDrive - Arup\Arup\AI\OvaDue" "O:" /E /R:2 /W:3 /XD ".venv" "__pycache__" ".git"
echo Done. Robocopy exit code: %ERRORLEVEL%
pause
