@echo off
echo ============================================================
echo  Starting Backend (FastAPI on port 8000)
echo ============================================================
cd backend
call .venv\Scripts\activate.bat
uvicorn app.main:app --reload --port 8000
