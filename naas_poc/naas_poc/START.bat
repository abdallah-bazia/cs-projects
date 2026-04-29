 @echo off
title NaaS Proof of Concept - University of Jijel
color 0A

echo ============================================================
echo   NaaS: NETWORK AS A SERVICE - Proof of Concept
echo   University of Jijel - Computer Science Department
echo ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

:: Install dependencies silently
echo [1/4] Installing dependencies...
pip install flask requests -q
echo       Done.
echo.

:: Start SDN Controller in background
echo [2/4] Starting SDN Controller (port 6633)...
start "SDN Controller" cmd /k "python controller\sdn_controller.py"
timeout /t 2 /nobreak >nul
echo       Controller running.
echo.

:: Start NaaS Portal in background
echo [3/4] Starting NaaS Portal API (port 5000)...
start "NaaS Portal" cmd /k "python portal\naas_portal.py"
timeout /t 2 /nobreak >nul
echo       Portal running.
echo.

:: Run demo
echo [4/4] Running full NaaS demo...
echo.
timeout /t 1 /nobreak >nul
python demo.py

echo.
echo ============================================================
echo   Demo finished. Services still running:
echo     - SDN Controller : http://localhost:6633
echo     - NaaS Portal    : http://localhost:5000/api
echo.
echo   You can test the API manually with curl or Postman.
echo   Close the SDN Controller and NaaS Portal windows to stop.
echo ============================================================
echo.
pause
