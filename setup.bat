@echo off
echo ============================================================
echo  ETHARA Project Manager - Full Setup Script
echo ============================================================
echo.

:: ---- Step 1: Start PostgreSQL via Docker ----
echo [1/4] Starting PostgreSQL via Docker...
docker compose up -d
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker failed to start. Make sure Docker Desktop is running!
    pause
    exit /b 1
)
echo.
echo Waiting 5 seconds for PostgreSQL to be ready...
timeout /t 5 /nobreak >nul

:: ---- Step 2: Verify PostgreSQL is running ----
echo [2/4] Verifying PostgreSQL container...
docker ps --filter "name=postgres" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.

:: ---- Step 3: Backend setup ----
echo [3/4] Setting up Backend (FastAPI)...
cd backend

IF NOT EXIST ".venv" (
    echo Creating Python virtual environment...
    python -m venv .venv
    IF %ERRORLEVEL% NEQ 0 (
        echo ERROR: Python not found! Install Python 3.11+ from https://www.python.org
        pause
        exit /b 1
    )
)

echo Activating virtual environment and installing dependencies...
call .venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: pip install failed!
    pause
    exit /b 1
)

echo Running database migrations...
alembic upgrade head
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Alembic migration failed! Check DB connection.
    pause
    exit /b 1
)

echo.
echo [4/4] Backend setup complete!
echo.
cd ..

:: ---- Step 4: Frontend setup ----
echo Setting up Frontend (React + Vite)...
cd frontend

IF NOT EXIST "node_modules" (
    echo Installing npm packages...
    npm install
    IF %ERRORLEVEL% NEQ 0 (
        echo ERROR: npm install failed! Install Node.js from https://nodejs.org
        pause
        exit /b 1
    )
)

cd ..

echo.
echo ============================================================
echo  SETUP COMPLETE!
echo ============================================================
echo.
echo Now open TWO terminal windows and run:
echo.
echo  TERMINAL 1 (Backend):
echo    cd backend
echo    .venv\Scripts\activate.bat
echo    uvicorn app.main:app --reload --port 8000
echo.
echo  TERMINAL 2 (Frontend):
echo    cd frontend
echo    npm run dev
echo.
echo  Then open: http://localhost:5173
echo  API Docs:  http://localhost:8000/docs
echo ============================================================
pause
