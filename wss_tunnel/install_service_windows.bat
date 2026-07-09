@echo off
setlocal

:: This script creates a scheduled task to run the WSS client.py silently on startup.

set "TASK_NAME=WSS_Tunnel_Client"
set "PYTHON_EXEC=pythonw.exe"
set "SCRIPT_PATH=%~dp0client.py"

:: Check if pythonw is in PATH
where %PYTHON_EXEC% >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] 'pythonw.exe' not found in PATH. Make sure Python is installed and added to PATH.
    pause
    exit /b 1
)

:: Ensure the client script exists
if not exist "%SCRIPT_PATH%" (
    echo [!] Could not find %SCRIPT_PATH%
    pause
    exit /b 1
)

echo [*] Creating Scheduled Task '%TASK_NAME%'...
:: Delete existing task if it exists to avoid conflicts
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>nul

:: Create the task to run on system startup with highest privileges
schtasks /create /tn "%TASK_NAME%" /tr "\"%PYTHON_EXEC%\" \"%SCRIPT_PATH%\"" /sc onstart /ru SYSTEM /rl HIGHEST /f

if %errorlevel% equ 0 (
    echo [+] Successfully installed WSS Client as a startup service.
    echo [*] Starting the service now...
    schtasks /run /tn "%TASK_NAME%"
    echo [+] Service started.
) else (
    echo [!] Failed to create scheduled task. Please run this script as Administrator.
)

pause
