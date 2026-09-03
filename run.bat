@echo off
echo =======================================================
echo  Starting AI Recruitment and Talent Copilot
echo =======================================================

:: Determine Python command (try py first, then python)
set PYTHON_CMD=
py --version >nul 2>&1 && set PYTHON_CMD=py
if not defined PYTHON_CMD (
    python --version >nul 2>&1 && set PYTHON_CMD=python
)

if not defined PYTHON_CMD (
    echo [ERROR] Python is not installed or not found.
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

:: If run from parent directory, switch to New folder if app.py is there
if not exist app.py (
    if exist "New folder\app.py" (
        cd "New folder"
    )
)

:: Install dependencies
echo [1/2] Checking required Python packages...
%PYTHON_CMD% -m pip install -r requirements.txt

:: Launch Streamlit app
echo [2/2] Launching Web Application...
%PYTHON_CMD% -m streamlit run app.py

pause
