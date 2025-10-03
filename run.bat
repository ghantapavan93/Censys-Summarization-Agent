@echo off
REM run.bat - Windows batch file for Censys Summarization Agent

echo 🚀 Starting Censys Summarization Agent...

REM Check if virtual environment exists, create if not
IF NOT EXIST .venv (
    echo 📦 Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
CALL .venv\Scripts\activate

REM Install dependencies
echo 📋 Installing dependencies...
pip install -r backend\requirements.txt >nul

REM Change to backend directory and start server
echo 🌐 Starting FastAPI server...
echo Server will be available at: http://localhost:8000
echo Swagger UI available at: http://localhost:8000/docs
echo Press Ctrl+C to stop the server

cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000