@echo off
REM Launches the built app/exe and creates a Desktop shortcut (if missing).
REM Uses the same script for all behavior.

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%~dp0run_packaged_and_install.py"
    goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
    python "%~dp0run_packaged_and_install.py"
    goto :eof
)

echo Python is not installed or not available in PATH.
echo Install Python and enable:
echo - Add python.exe to PATH
echo - Install launcher for all users (recommended)
echo Then run this script again.
exit /b 1

