@echo off
setlocal

set "ROOT=%~dp0"
set "AI_BACKEND=%ROOT%ai_backend"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

echo ============================================
echo  TestForge - Starting AI Backend, Backend and Frontend
echo ============================================

REM --- AI backend setup ---
if not exist "%AI_BACKEND%\venv\Scripts\python.exe" (
    echo [AI Backend] Creating virtual environment...
    python -m venv "%AI_BACKEND%\venv"
    if errorlevel 1 (
        echo [AI Backend] ERROR: Failed to create virtual environment. Is Python 3.11+ installed?
        pause
        exit /b 1
    )
)

echo [AI Backend] Installing/checking dependencies...
"%AI_BACKEND%\venv\Scripts\python.exe" -m pip install --upgrade pip >nul
"%AI_BACKEND%\venv\Scripts\python.exe" -m pip install -r "%AI_BACKEND%\requirements.txt"
if errorlevel 1 (
    echo [AI Backend] ERROR: Failed to install Python dependencies.
    pause
    exit /b 1
)

REM --- Backend setup ---
if not exist "%BACKEND%\venv\Scripts\python.exe" (
    echo [Backend] Creating virtual environment...
    python -m venv "%BACKEND%\venv"
    if errorlevel 1 (
        echo [Backend] ERROR: Failed to create virtual environment. Is Python 3.11+ installed?
        pause
        exit /b 1
    )
)

echo [Backend] Installing/checking dependencies...
"%BACKEND%\venv\Scripts\python.exe" -m pip install --upgrade pip >nul
"%BACKEND%\venv\Scripts\python.exe" -m pip install -r "%BACKEND%\requirements.txt"
if errorlevel 1 (
    echo [Backend] ERROR: Failed to install Python dependencies.
    pause
    exit /b 1
)

REM --- Frontend setup ---
if not exist "%FRONTEND%\node_modules" (
    echo [Frontend] Installing npm dependencies...
    pushd "%FRONTEND%"
    call npm install
    popd
    if errorlevel 1 (
        echo [Frontend] ERROR: npm install failed. Is Node.js installed?
        pause
        exit /b 1
    )
)

REM --- Launch AI backend (Flask, port 5001) ---
echo [AI Backend] Starting Flask server on http://localhost:5001 ...
start "TestForge AI Backend" cmd /k "cd /d "%AI_BACKEND%" && venv\Scripts\python.exe run.py"

REM --- Launch backend (Flask, port 5000) ---
echo [Backend] Starting Flask server on http://localhost:5000 ...
start "TestForge Backend" cmd /k "cd /d "%BACKEND%" && set AI_BACKEND_URL=http://localhost:5001&& venv\Scripts\python.exe run.py"

REM --- Launch frontend (Vite dev server, port 5173) ---
echo [Frontend] Starting Vite dev server on http://localhost:5173 ...
start "TestForge Frontend" cmd /k "cd /d "%FRONTEND%" && npm run dev"

REM --- Open browser ---
timeout /t 5 /nobreak >nul
start "" "http://localhost:5173"

echo.
echo ============================================
echo  TestForge is starting in three new windows.
echo  AI Backend: http://localhost:5001
echo  Backend:    http://localhost:5000
echo  Frontend:   http://localhost:5173
echo  Close those windows to stop the servers.
echo ============================================
endlocal
