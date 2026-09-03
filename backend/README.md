# 💼 AI Recruitment & Talent Copilot

Autonomous Real-Time Resume Profiling, Candidate Matching & Skill Gap Analytics Engine.

---

## 🚀 Quick Setup & How to Run (For New Users)

### Option 1: One-Click Startup (Windows)
Double-click `run.bat` in the project folder. It will automatically install dependencies from `requirements.txt` and launch the web interface in your browser.

---

### Option 2: Manual Terminal Commands (Windows / Mac / Linux)

#### 1. Prerequisites
Make sure **Python 3.10+** is installed on your system:
```bash
python --version
```

#### 2. Install Dependencies
Open a terminal in the project directory and run:
```bash
pip install -r requirements.txt
```

#### 3. Run the Streamlit Application
Start the app server:
```bash
streamlit run app.py
```
*(Alternatively: `python -m streamlit run app.py`)*

The web application will open automatically in your browser at **http://localhost:8501**.

---

## 🔑 (Optional) LLM AI API Setup
- The application runs in **Offline Mode** by default using fast rule-based section parsing.
- To enable advanced LLM extraction (Google Gemini or OpenAI), open **⚙️ Settings** in the app sidebar and paste your API key.
