import os
import time
from datetime import datetime
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import plotly.graph_objects as go

# Custom Page Configuration
st.set_page_config(
    page_title="AI Recruitment & Talent Management Platform",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Imports from backend modules
from database import (
    init_db,
    get_db,
    User,
    Job,
    Candidate,
    Evaluation,
    Application,
    InterviewSession,
    InterviewQuestion,
    get_all_jobs,
    get_job_by_id,
    save_job,
    delete_job,
    get_all_candidates,
    get_candidate_by_id,
    save_candidate,
    update_candidate,
    delete_candidate,
    get_evaluations_for_job,
    get_evaluations_for_candidate,
    reset_database,
    clear_candidate_data,
    get_or_create_application,
    get_all_applications,
    get_applications_for_candidate,
    get_application_by_id,
    update_application_stage,
    update_application_details,
    get_ats_pipeline_counts,
    save_interview_session,
    get_interview_sessions_for_candidate,
    get_all_interview_sessions,
    get_interview_session_by_id,
    save_interview_question,
    get_questions_for_job_candidate,
    save_user,
    get_all_users,
    delete_user,
    authenticate_user,
    get_admin_system_metrics,
)
from parser import parse_document
from extractor import extract_candidate_with_llm, extract_job_with_llm
from matcher import rank_and_save_evaluations_for_job, evaluate_candidate_for_job
from analytics import (
    calculate_skill_gap_pct,
    generate_training_recommendations,
    plot_candidate_radar,
    plot_skills_gauge,
    plot_skills_donut,
    plot_skill_coverage_matrix,
    plot_top_candidates_bar,
    export_evaluation_pdf,
    export_evaluations_csv,
)
from question_generator import generate_interview_questions, InterviewQuestionSet
from ats import (
    STAGES,
    STAGE_COLORS,
    STAGE_ICONS,
    sync_shortlisted_candidates_to_ats,
    get_kanban_pipeline_data,
    advance_candidate_stage,
    schedule_interview,
    record_recruiter_feedback,
    get_ats_funnel_metrics,
)
from interview_simulator import (
    evaluate_single_answer,
    generate_overall_interview_report,
    export_interview_report_pdf,
    AnswerEvaluation,
    SessionReport,
)
from sample_data import seed_database_if_empty, seed_demo_data

# Initialize database tables on startup
seed_database_if_empty()

# Initialize Session State Variables
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None
if "selected_portal_login" not in st.session_state:
    st.session_state.selected_portal_login = "🏢 Recruiter Portal"
if "current_portal" not in st.session_state:
    st.session_state.current_portal = "🏢 Recruiter Portal"
if "logged_candidate_id" not in st.session_state:
    st.session_state.logged_candidate_id = 1
if "llm_provider" not in st.session_state:
    st.session_state.llm_provider = "google"
if "api_key" not in st.session_state:
    st.session_state.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
if "weights" not in st.session_state:
    st.session_state.weights = (0.50, 0.35, 0.15)

# Interview simulation session state
if "sim_job_id" not in st.session_state:
    st.session_state.sim_job_id = None
if "sim_candidate_id" not in st.session_state:
    st.session_state.sim_candidate_id = None
if "sim_questions" not in st.session_state:
    st.session_state.sim_questions = []
if "sim_current_idx" not in st.session_state:
    st.session_state.sim_current_idx = 0
if "sim_evaluations" not in st.session_state:
    st.session_state.sim_evaluations = []
if "sim_answers" not in st.session_state:
    st.session_state.sim_answers = []
if "sim_completed" not in st.session_state:
    st.session_state.sim_completed = False
if "sim_report" not in st.session_state:
    st.session_state.sim_report = None

# Custom CSS for Executive Light Theme & Portal UI
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .stApp {
        background: #f8fafc !important;
        color: #0f172a !important;
    }
    
    /* =========================================================================
       SIDEBAR NAVIGATION STYLING - HIGH CONTRAST & VISIBILITY
       ========================================================================= */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0 !important;
    }

    section[data-testid="stSidebar"] * {
        color: #0f172a !important;
    }

    /* Sidebar Radio Navigation Header */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] > label {
        color: #0f172a !important;
        font-weight: 800 !important;
        font-size: 0.95rem !important;
        letter-spacing: 0.025em !important;
        text-transform: uppercase !important;
        margin-bottom: 8px !important;
        display: block !important;
    }

    /* Sidebar Radio Item Labels */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label p,
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label span,
    section[data-testid="stSidebar"] div[data-testid="stRadio"] label div {
        color: #1e293b !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        line-height: 1.4 !important;
    }

    /* Sidebar Radio Container Items */
    section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label {
        background: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 10px !important;
        padding: 8px 14px !important;
        margin-bottom: 6px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label:hover {
        background: #eff6ff !important;
        border-color: #93c5fd !important;
        transform: translateX(2px) !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label[data-checked="true"] {
        background: #eff6ff !important;
        border-color: #2563eb !important;
        border-left: 4px solid #2563eb !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] div[role="radiogroup"] > label[data-checked="true"] p {
        color: #1d4ed8 !important;
        font-weight: 700 !important;
    }

    /* =========================================================================
       UNIVERSAL INPUT FIELDS - REMOVE ALL BLACK/DARK BACKGROUNDS
       ========================================================================= */
    input, textarea, select {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }

    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    div[data-baseweb="textarea"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }

    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea {
        background-color: #ffffff !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
    }

    div[data-baseweb="input"] input::placeholder,
    div[data-baseweb="textarea"] textarea::placeholder {
        color: #94a3b8 !important;
        -webkit-text-fill-color: #94a3b8 !important;
    }

    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #0f172a !important;
    }

    div[data-baseweb="select"] * {
        color: #0f172a !important;
    }

    div[data-baseweb="popover"],
    div[data-baseweb="menu"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
    }

    div[data-baseweb="menu"] li {
        color: #0f172a !important;
        background-color: #ffffff !important;
    }

    div[data-baseweb="menu"] li:hover {
        background-color: #eff6ff !important;
        color: #2563eb !important;
    }

    /* Form Field Labels */
    label[data-testid="stWidgetLabel"] p,
    label[data-testid="stWidgetLabel"] span {
        color: #1e293b !important;
        font-weight: 700 !important;
        font-size: 0.88rem !important;
    }

    /* Field Focus Highlight */
    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="textarea"]:focus-within,
    div[data-baseweb="select"]:focus-within {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15) !important;
    }

    /* =========================================================================
       METRIC CARDS, PANELS, AND CONTAINERS
       ========================================================================= */
    div[data-testid="stMetric"] {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05) !important;
        transition: all 0.25s ease !important;
    }
    
    div[data-testid="stMetric"]:hover {
        border-color: #3b82f6 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.12) !important;
    }

    div[data-testid="stMetricLabel"] {
        color: #64748b !important;
        font-size: 0.82rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.03em !important;
        text-transform: uppercase !important;
    }

    div[data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-weight: 800 !important;
        font-size: 2rem !important;
    }

    .glass-panel {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 18px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }

    .glass-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.04);
        transition: all 0.2s ease;
    }

    .glass-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.08);
    }

    .portal-banner {
        background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%);
        border: 1px solid #dbeafe;
        border-radius: 14px;
        padding: 16px 22px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .portal-select-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 22px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        transition: all 0.25s ease;
        cursor: pointer;
    }

    .portal-select-card:hover {
        border-color: #2563eb;
        transform: translateY(-3px);
        box-shadow: 0 12px 24px -6px rgba(37, 99, 235, 0.12);
    }

    /* Badges */
    .skill-badge {
        display: inline-flex;
        align-items: center;
        background: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
        border-radius: 9999px;
        padding: 3px 12px;
        margin: 2px;
        font-size: 0.78rem;
        font-weight: 600;
    }

    .matched-badge {
        display: inline-flex;
        align-items: center;
        background: #ecfdf5;
        color: #047857;
        border: 1px solid #a7f3d0;
        border-radius: 9999px;
        padding: 3px 12px;
        margin: 2px;
        font-size: 0.78rem;
        font-weight: 600;
    }

    .missing-badge {
        display: inline-flex;
        align-items: center;
        background: #fef2f2;
        color: #b91c1c;
        border: 1px solid #fecaca;
        border-radius: 9999px;
        padding: 3px 12px;
        margin: 2px;
        font-size: 0.78rem;
        font-weight: 600;
    }

    .stage-badge {
        display: inline-flex;
        align-items: center;
        border-radius: 8px;
        padding: 3px 10px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .difficulty-beginner {
        background: #ecfdf5;
        color: #059669;
        border: 1px solid #a7f3d0;
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    .difficulty-intermediate {
        background: #fffbeb;
        color: #d97706;
        border: 1px solid #fde68a;
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    .difficulty-advanced {
        background: #fef2f2;
        color: #dc2626;
        border: 1px solid #fecaca;
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    
    .section-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0.35rem;
    }

    .sub-title {
        color: #64748b;
        font-size: 0.95rem;
        margin-bottom: 1rem;
    }

    /* Question & Simulator Card Styles */
    .question-card {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #2563eb !important;
        border-radius: 14px !important;
        padding: 20px 24px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
    }

    .question-title {
        font-size: 1.2rem !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        margin-top: 8px !important;
        line-height: 1.45 !important;
    }

    .benchmark-box {
        background: #f0fdf4 !important;
        border: 1px solid #bbf7d0 !important;
        border-left: 4px solid #10b981 !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
        margin-top: 10px !important;
        color: #14532d !important;
        font-size: 0.9rem !important;
        line-height: 1.5 !important;
    }

    .probe-box {
        background: #eff6ff !important;
        border: 1px solid #bfdbfe !important;
        border-left: 4px solid #3b82f6 !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
        margin-top: 8px !important;
        color: #1e3a8a !important;
        font-size: 0.9rem !important;
        line-height: 1.5 !important;
    }

    .scenario-box {
        background: #fffbeb !important;
        border: 1px solid #fde68a !important;
        border-left: 4px solid #f59e0b !important;
        border-radius: 10px !important;
        padding: 12px 16px !important;
        margin-top: 10px !important;
        color: #78350f !important;
        font-size: 0.9rem !important;
        line-height: 1.5 !important;
    }

    /* Expanders & Tabs */
    div[data-testid="stExpander"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
    }

    button[data-baseweb="tab"] {
        color: #64748b !important;
        font-weight: 600 !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #2563eb !important;
        font-weight: 700 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

db = next(get_db())
candidates_list = get_all_candidates(db)
jobs_list = get_all_jobs(db)


# ==============================================================================
# ==============================================================================
# MAIN SCREEN: PORTAL SELECTION & CREDENTIAL AUTHENTICATION GATEWAY
# ==============================================================================
# ==============================================================================

if st.session_state.authenticated_user is None:

    # Hero Branding Header
    st.markdown(
        """
        <div style='text-align: center; padding: 25px 0 15px 0;'>
            <div style='display: inline-flex; align-items: center; gap: 10px; background: #eff6ff; border: 1px solid #bfdbfe; padding: 6px 18px; border-radius: 9999px; margin-bottom: 12px;'>
                <span style='color: #1d4ed8; font-weight: 700; font-size: 0.82rem;'>💼 ENTERPRISE RECRUITMENT & TALENT MANAGEMENT PLATFORM</span>
            </div>
            <h1 style='font-size: 2.5rem; font-weight: 800; color: #0f172a; margin: 0;'>
                Select Portal to Access Login
            </h1>
            <p style='color: #64748b; font-size: 1rem; max-width: 600px; margin: 8px auto 0 auto;'>
                Select your role portal below. The login screen with <b>pre-generated default demo credentials</b> will load instantly.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3 Portal Interactive Selector Cards
    col_p1, col_p2, col_p3 = st.columns(3)
    
    is_rec = st.session_state.selected_portal_login == "🏢 Recruiter Portal"
    is_cand = st.session_state.selected_portal_login == "👤 Candidate Portal"
    is_adm = st.session_state.selected_portal_login == "🛡️ Admin Portal"

    with col_p1:
        border_style = "border: 2px solid #2563eb; background: #f0f9ff;" if is_rec else "border: 1px solid #e2e8f0; background: #ffffff;"
        st.markdown(
            f"""
            <div class='portal-select-card' style='{border_style} border-top: 4px solid #2563eb;'>
                <div style='font-size: 2.2rem; margin-bottom: 6px;'>🏢</div>
                <div style='font-size: 1.2rem; font-weight: 800; color: #0f172a;'>Recruiter Portal</div>
                <div style='color: #64748b; font-size: 0.82rem; margin-top: 4px; min-height: 38px;'>
                    Job postings, candidate match rankings, ATS Kanban pipeline, and question generation.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🏢 Select Recruiter Portal", key="btn_sel_rec", type="primary" if is_rec else "secondary", width="stretch"):
            st.session_state.selected_portal_login = "🏢 Recruiter Portal"
            st.rerun()

    with col_p2:
        border_style = "border: 2px solid #059669; background: #f0fdf4;" if is_cand else "border: 1px solid #e2e8f0; background: #ffffff;"
        st.markdown(
            f"""
            <div class='portal-select-card' style='{border_style} border-top: 4px solid #059669;'>
                <div style='font-size: 2.2rem; margin-bottom: 6px;'>👤</div>
                <div style='font-size: 1.2rem; font-weight: 800; color: #0f172a;'>Candidate Portal</div>
                <div style='color: #64748b; font-size: 0.82rem; margin-top: 4px; min-height: 38px;'>
                    Candidate self-service, resume parser, application status tracking, and AI mock interview simulator.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("👤 Select Candidate Portal", key="btn_sel_cand", type="primary" if is_cand else "secondary", width="stretch"):
            st.session_state.selected_portal_login = "👤 Candidate Portal"
            st.rerun()

    with col_p3:
        border_style = "border: 2px solid #dc2626; background: #fef2f2;" if is_adm else "border: 1px solid #e2e8f0; background: #ffffff;"
        st.markdown(
            f"""
            <div class='portal-select-card' style='{border_style} border-top: 4px solid #dc2626;'>
                <div style='font-size: 2.2rem; margin-bottom: 6px;'>🛡️</div>
                <div style='font-size: 1.2rem; font-weight: 800; color: #0f172a;'>Admin Portal</div>
                <div style='color: #64748b; font-size: 0.82rem; margin-top: 4px; min-height: 38px;'>
                    System health monitoring, user role permissions, application audit logs, and global reports.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🛡️ Select Admin Portal", key="btn_sel_adm", type="primary" if is_adm else "secondary", width="stretch"):
            st.session_state.selected_portal_login = "🛡️ Admin Portal"
            st.rerun()

    st.write("")
    st.divider()

    # ==========================================================================
    # DEDICATED LOGIN VIEW 1: RECRUITER PORTAL LOGIN
    # ==========================================================================
    if st.session_state.selected_portal_login == "🏢 Recruiter Portal":
        st.markdown("<div class='section-title'>🏢 Recruiter Portal Sign In</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Sign in with verified Recruiter credentials to manage talent pipelines and AI interview generation.</div>", unsafe_allow_html=True)

        col_form, col_cred = st.columns([3, 2])
        with col_cred:
            st.markdown(
                """
                <div class='glass-panel' style='border-top: 3px solid #2563eb;'>
                    <div style='font-size: 0.95rem; font-weight: 700; color: #1d4ed8; margin-bottom: 6px;'>⚡ Generated Default Demo Credentials</div>
                    <div style='font-size: 0.85rem; color: #334155; line-height: 1.6;'>
                        <b>Primary Recruiter:</b><br>
                        • Username: <code>recruiter_sarah</code><br>
                        • Password: <code>recruiter123</code><br><br>
                        <b>Secondary Sourcer:</b><br>
                        • Username: <code>recruiter_david</code><br>
                        • Password: <code>recruiter123</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_form:
            rec_account_choice = st.selectbox(
                "Select Recruiter Demo Profile:",
                ["Sarah Jenkins (Lead Recruiter) — recruiter_sarah", "David Sterling (Sourcer) — recruiter_david", "Custom Login Credentials"],
                key="rec_demo_choice",
            )

            default_u = "recruiter_sarah" if "Sarah" in rec_account_choice else ("recruiter_david" if "David" in rec_account_choice else "")
            default_p = "recruiter123" if default_u else ""

            with st.form("recruiter_login_form"):
                u_in = st.text_input("Recruiter Username *", value=default_u)
                p_in = st.text_input("Password *", value=default_p, type="password")

                if st.form_submit_button("🚀 Sign In to Recruiter Portal", type="primary", width="stretch"):
                    user = authenticate_user(db, u_in, p_in, expected_role="Recruiter")
                    if user:
                        st.session_state.authenticated_user = user.to_dict()
                        st.session_state.current_portal = "🏢 Recruiter Portal"
                        st.success(f"Welcome back, {user.full_name}! Redirecting...")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please verify your recruiter username and password.")

    # ==========================================================================
    # DEDICATED LOGIN VIEW 2: CANDIDATE PORTAL LOGIN
    # ==========================================================================
    elif st.session_state.selected_portal_login == "👤 Candidate Portal":
        st.markdown("<div class='section-title'>👤 Candidate Portal Sign In & Registration</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Sign in to track application status, take role-specific AI Mock Interviews, and update your resume skills.</div>", unsafe_allow_html=True)

        cand_tab_login, cand_tab_signup = st.tabs(["🔑 Candidate Sign In", "📝 Register New Candidate Profile"])

        with cand_tab_login:
            col_form, col_info = st.columns([3, 2])
            with col_info:
                st.markdown(
                    """
                    <div class='glass-panel' style='border-top: 3px solid #059669;'>
                        <div style='font-size: 0.95rem; font-weight: 700; color: #047857; margin-bottom: 6px;'>👤 Candidate Portal Access</div>
                        <div style='font-size: 0.85rem; color: #334155; line-height: 1.6;'>
                            Sign in with your candidate account to access your personal dashboard, track recruitment rounds, and practice AI mock interviews.<br><br>
                            <b>New candidate?</b> Switch to the <b>📝 Register New Candidate Profile</b> tab to create your profile or parse your resume.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_form:
                with st.form("candidate_login_form"):
                    cu_in = st.text_input("Candidate Username *", placeholder="Enter your username")
                    cp_in = st.text_input("Password *", type="password", placeholder="Enter your password")

                    if st.form_submit_button("🚀 Sign In to Candidate Portal", type="primary", width="stretch"):
                        user = authenticate_user(db, cu_in, cp_in, expected_role="Candidate")
                        if user:
                            st.session_state.authenticated_user = user.to_dict()
                            st.session_state.current_portal = "👤 Candidate Portal"
                            st.session_state.logged_candidate_id = user.candidate_id
                            st.success(f"Welcome back, {user.full_name}! Redirecting...")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Invalid credentials. Please verify your candidate username and password, or register a new profile.")

        with cand_tab_signup:
            st.markdown("### 📝 Register Candidate Profile & Account")
            st.markdown("Register your candidate profile. All details are saved permanently in the database so recruiters can match you against open roles.")

            reg_method = st.radio("Registration Method:", ["📤 Upload Resume (Auto-Extract with AI & Create Account)", "✍️ Manual Form Entry"], horizontal=True, key="cand_reg_method_sel")

            if "📤 Upload Resume" in reg_method:
                st.markdown("Upload your resume (**PDF**, **DOCX**, **TXT**). Our AI parser will automatically extract your contact details, experience, education, skills, and projects.")
                c_res_file = st.file_uploader("Choose Resume File:", type=["pdf", "docx", "txt"], key="cand_reg_res_up")
                
                col_ru1, col_ru2 = st.columns(2)
                with col_ru1:
                    rg_res_uname = st.text_input("Choose Username *", placeholder="e.g. alex_mercer", key="rg_res_un")
                with col_ru2:
                    rg_res_pwd = st.text_input("Choose Password *", type="password", value="candidate123", key="rg_res_pw")

                if st.button("⚡ Parse Resume & Register Account", type="primary", width="stretch", key="btn_parse_reg_cand"):
                    if not c_res_file:
                        st.error("Please upload your resume file first.")
                    elif not rg_res_uname or not rg_res_pwd:
                        st.error("Please enter a username and password for your candidate account.")
                    else:
                        with st.spinner("Parsing resume and registering profile in database..."):
                            raw_text = parse_document(c_res_file.name, c_res_file.read())
                            prof = extract_candidate_with_llm(raw_text, provider=st.session_state.llm_provider, api_key=st.session_state.api_key)
                            
                            c_name = prof.full_name or c_res_file.name.rsplit(".", 1)[0].replace("_", " ").title()
                            c_mail = prof.email or f"{rg_res_uname}@candidate.org"

                            cand = save_candidate(db, {
                                "full_name": c_name,
                                "email": c_mail,
                                "phone": prof.phone,
                                "parsed_experience": prof.total_experience_years,
                                "parsed_education": prof.parsed_education,
                                "skills": prof.skills,
                                "projects": prof.projects,
                                "certifications": prof.certifications,
                                "raw_text": raw_text,
                            })

                            new_u = save_user(db, {
                                "username": rg_res_uname,
                                "password": rg_res_pwd,
                                "full_name": c_name,
                                "email": c_mail,
                                "role": "Candidate",
                                "candidate_id": cand.id,
                            })

                            # Auto-evaluate against all active jobs in database
                            for j in jobs_list:
                                rank_and_save_evaluations_for_job(db, j.id, [cand], j, weights=st.session_state.weights)

                            st.session_state.authenticated_user = new_u.to_dict()
                            st.session_state.current_portal = "👤 Candidate Portal"
                            st.session_state.logged_candidate_id = cand.id
                            st.success("🎉 Account created and resume saved in database! Logging you in...")
                            time.sleep(0.5)
                            st.rerun()

            else:
                with st.form("cand_reg_form_manual"):
                    rg_name = st.text_input("Full Name *", placeholder="e.g. Alex Mercer")
                    rg_email = st.text_input("Email Address *", placeholder="alex.mercer@example.com")
                    rg_phone = st.text_input("Phone Number", placeholder="+1 (555) 123-9876")
                    col_u1, col_u2 = st.columns(2)
                    with col_u1:
                        rg_uname = st.text_input("Create Username *", placeholder="alex_mercer")
                    with col_u2:
                        rg_pwd = st.text_input("Create Password *", type="password", value="candidate123")
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        rg_exp = st.number_input("Years of Experience", 0.0, 30.0, 3.0, 0.5)
                    with col_e2:
                        rg_edu = st.selectbox("Education Level", ["Bachelor's", "Master's", "Ph.D.", "Associate", "Other"])
                    rg_skills = st.text_input("Skills (comma-separated)", placeholder="python, aws, docker, react, machine learning")

                    if st.form_submit_button("🎉 Register & Sign In", type="primary", width="stretch"):
                        if rg_name and rg_email and rg_uname and rg_pwd:
                            sk_list = [s.strip().lower() for s in rg_skills.split(",") if s.strip()]
                            cand = save_candidate(db, {
                                "full_name": rg_name,
                                "email": rg_email,
                                "phone": rg_phone,
                                "parsed_experience": rg_exp,
                                "parsed_education": [rg_edu],
                                "skills": sk_list,
                            })
                            new_u = save_user(db, {
                                "username": rg_uname,
                                "password": rg_pwd,
                                "full_name": rg_name,
                                "email": rg_email,
                                "role": "Candidate",
                                "candidate_id": cand.id,
                            })

                            # Auto-evaluate against all active jobs in database
                            for j in jobs_list:
                                rank_and_save_evaluations_for_job(db, j.id, [cand], j, weights=st.session_state.weights)

                            st.session_state.authenticated_user = new_u.to_dict()
                            st.session_state.current_portal = "👤 Candidate Portal"
                            st.session_state.logged_candidate_id = cand.id
                            st.success("Account created and profile saved in database! Logging you in...")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Please fill in all required fields marked with *.")

    # ==========================================================================
    # DEDICATED LOGIN VIEW 3: ADMIN PORTAL LOGIN
    # ==========================================================================
    elif st.session_state.selected_portal_login == "🛡️ Admin Portal":
        st.markdown("<div class='section-title'>🛡️ Admin & Governance Portal Sign In</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Sign in with Superadmin credentials for platform monitoring, role permissions, and database governance.</div>", unsafe_allow_html=True)

        col_form, col_cred = st.columns([3, 2])
        with col_cred:
            st.markdown(
                """
                <div class='glass-panel' style='border-top: 3px solid #dc2626;'>
                    <div style='font-size: 0.95rem; font-weight: 700; color: #dc2626; margin-bottom: 6px;'>⚡ Generated Admin Demo Credentials</div>
                    <div style='font-size: 0.85rem; color: #334155; line-height: 1.6;'>
                        <b>Superadmin Account:</b><br>
                        • Username: <code>admin</code><br>
                        • Password: <code>admin123</code><br><br>
                        <span style='color: #64748b; font-size: 0.75rem;'>Full privileges: User role management, database resets, and LLM configuration.</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_form:
            with st.form("admin_login_form"):
                au_in = st.text_input("Administrator Username *", value="admin")
                ap_in = st.text_input("Password *", value="admin123", type="password")

                if st.form_submit_button("🚀 Sign In to Admin Portal", type="primary", width="stretch"):
                    user = authenticate_user(db, au_in, ap_in, expected_role="Admin")
                    if user:
                        st.session_state.authenticated_user = user.to_dict()
                        st.session_state.current_portal = "🛡️ Admin Portal"
                        st.success("Superadmin authentication successful! Redirecting...")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Administrator role access required.")

    st.stop()



# ==============================================================================
# ==============================================================================
# AUTHENTICATED APPLICATION SHELL
# ==============================================================================
# ==============================================================================

selected_portal = st.session_state.current_portal
current_user = st.session_state.authenticated_user

if not current_user:
    st.stop()
else:
    # Sidebar User Identity Card
    st.sidebar.image("https://img.icons8.com/isometric/96/briefcase.png", width=54)
    st.sidebar.markdown(
        f"""
        <div style='background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; margin-bottom: 12px;'>
            <div style='font-size: 0.75rem; color: #2563eb; font-weight: 700; text-transform: uppercase;'>{selected_portal}</div>
            <div style='font-size: 1rem; font-weight: 800; color: #0f172a;'>👤 {current_user.get('full_name', 'User')}</div>
            <div style='font-size: 0.75rem; color: #64748b;'>@{current_user.get('username', 'user')} • {current_user.get('role', 'Member')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.sidebar.button("🚪 Sign Out / Switch Portal", width="stretch"):
        st.session_state.authenticated_user = None
        st.session_state.sim_questions = []
        st.session_state.sim_evaluations = []
        st.session_state.sim_answers = []
        st.session_state.sim_completed = False
        st.session_state.sim_report = None
        st.rerun()

    st.sidebar.divider()

# Candidate identity selector when in Candidate Portal (Strictly scoped to logged in candidate)
active_candidate = None
if current_user and selected_portal == "👤 Candidate Portal":
    cand_id = st.session_state.get("logged_candidate_id") or current_user.get("candidate_id")
    if cand_id:
        active_candidate = get_candidate_by_id(db, cand_id)
    if not active_candidate and current_user.get("email"):
        cands = get_all_candidates(db)
        active_candidate = next((c for c in cands if c.email and c.email.lower() == current_user["email"].lower()), None)
    if not active_candidate and current_user.get("full_name"):
        cands = get_all_candidates(db)
        active_candidate = next((c for c in cands if c.full_name.lower() == current_user["full_name"].lower()), None)

# Role-specific Navigation Menu Options
if selected_portal == "🏢 Recruiter Portal":
    nav_option = st.sidebar.radio(
        "Recruiter Navigation",
        [
            "📊 Dashboard & Pipeline",
            "👥 Jobs & Talent Pool",
            "🗓️ Interview Hub & Schedules",
            "📈 Recruitment Analytics",
        ],
    )

elif selected_portal == "👤 Candidate Portal":
    nav_option = st.sidebar.radio(
        "Candidate Navigation",
        [
            "📊 Application Status & Dashboard",
            "💼 Browse Openings & Apply",
            "🎙️ AI Interview Center",
            "👤 My Profile & Resume",
        ],
    )

elif selected_portal == "🛡️ Admin Portal":
    nav_option = st.sidebar.radio(
        "Admin Navigation",
        [
            "📊 Admin Dashboard",
            "👥 User Management",
            "🏢 Recruiter Management",
            "👤 Candidate Management",
            "💼 Job & Role Management",
            "📑 Application Management",
            "🖥️ System Monitoring & API Settings",
            "📈 Global Reports & Analytics",
        ],
    )

st.sidebar.divider()
st.sidebar.info(
    f"**AI Engine:** `{st.session_state.llm_provider.title()}` ({'🟢 API Connected' if st.session_state.api_key else '🟡 Offline Intelligent Engine'})"
)


# ==============================================================================
# ==============================================================================
# PORTAL 1: 🏢 RECRUITER PORTAL
# ==============================================================================
# ==============================================================================

if selected_portal == "🏢 Recruiter Portal":

    # --- 1. RECRUITER DASHBOARD & PIPELINE ---
    if nav_option == "📊 Dashboard & Pipeline":
        st.markdown("<div class='section-title'>📊 Executive Dashboard & Candidate Pipeline</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>High-level hiring KPIs, live ATS pipeline Kanban board, and recent candidate matching evaluations.</div>", unsafe_allow_html=True)
        
        funnel = get_ats_funnel_metrics(db)
        evals_all = [ev for j in jobs_list for ev in get_evaluations_for_job(db, j.id)]
        avg_score = sum(ev.overall_hiring_score for ev in evals_all) / len(evals_all) if evals_all else 0.0
        interview_sessions = get_all_interview_sessions(db, limit=5)
        shortlisted_count = sum(1 for ev in evals_all if ev.overall_hiring_score >= 70.0)

        # Top KPI Metrics Row
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Total Candidates", f"{len(candidates_list)}", delta="Talent Pool")
        with c2:
            st.metric("Active Openings", f"{len(jobs_list)}", delta="Target Roles")
        with c3:
            st.metric("Shortlisted (≥70%)", f"{shortlisted_count}", delta="High Fit")
        with c4:
            st.metric("Interviews Scheduled", f"{funnel['counts'].get('Interview', 0)}", delta="Active Pipeline")
        with c5:
            st.metric("Avg Hiring Fit", f"{avg_score:.1f}%", delta="Quality Score")

        st.divider()

        # ATS Funnel Cards
        st.subheader("🏢 Candidate Pipeline Overview")
        f1, f2, f3, f4, f5 = st.columns(5)
        stages_data = [
            ("Applied", "#64748b", "📥", "Initial Ingest"),
            ("Screening", "#0284c7", "🔍", "Skill Review"),
            ("Interview", "#8b5cf6", "🎙️", "AI / Video"),
            ("Selected", "#10b981", "🎉", "Hired"),
            ("Rejected", "#ef4444", "🚫", "Archived"),
        ]
        for idx, (s_name, color, icon, sub) in enumerate(stages_data):
            col = [f1, f2, f3, f4, f5][idx]
            with col:
                cnt = funnel["counts"].get(s_name, 0)
                st.markdown(
                    f"""
                    <div class='glass-card' style='border-left: 4px solid {color};'>
                        <div style='color: {color}; font-size: 0.8rem; font-weight: 700;'>{icon} {s_name.upper()}</div>
                        <div style='font-size: 1.8rem; font-weight: 800; color: #0f172a;'>{cnt}</div>
                        <div style='color: #64748b; font-size: 0.75rem;'>{sub}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.divider()

        # Kanban Interactive Pipeline
        st.subheader("📋 Interactive 5-Stage ATS Pipeline")
        col_j, col_sync = st.columns([3, 2])
        with col_j:
            filter_j = st.selectbox("Filter Pipeline by Position", [None] + jobs_list, format_func=lambda j: j.title if j else "All Job Positions", key="kanban_j_sel")
        with col_sync:
            st.write("")
            if st.button("⚡ Bulk Sync Shortlisted to ATS", type="primary", width="stretch"):
                total_s = sum(sync_shortlisted_candidates_to_ats(db, j.id) for j in jobs_list)
                st.success(f"Synchronized {total_s} candidates into pipeline!")
                st.rerun()

        job_id_filter = filter_j.id if filter_j else None
        kanban = get_kanban_pipeline_data(db, job_id=job_id_filter)

        k1, k2, k3, k4, k5 = st.columns(5)
        col_map = {"Applied": k1, "Screening": k2, "Interview": k3, "Selected": k4, "Rejected": k5}

        for stg in STAGES:
            c = col_map[stg]
            cards = kanban.get(stg, [])
            with c:
                color = STAGE_COLORS[stg]
                icon = STAGE_ICONS[stg]
                st.markdown(
                    f"""
                    <div style='background: #ffffff; border: 1px solid #e2e8f0; border-top: 4px solid {color}; border-radius: 8px 8px 0 0; padding: 10px; margin-bottom: 12px; text-align: center;'>
                        <span style='font-size: 0.85rem; font-weight: 800; color: #0f172a;'>{icon} {stg.upper()}</span>
                        <span style='background: #eff6ff; color: #1d4ed8; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; margin-left: 6px; font-weight: 700;'>{len(cards)}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if not cards:
                    st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.8rem; padding: 20px 0;'>No candidates</div>", unsafe_allow_html=True)

                for card in cards:
                    st.markdown(
                        f"""
                        <div class='glass-card' style='padding: 12px; margin-bottom: 10px;'>
                            <div style='font-weight: 700; color: #0f172a; font-size: 0.95rem;'>{card['candidate_name']}</div>
                            <div style='color: #64748b; font-size: 0.75rem;'>💼 {card['job_title']}</div>
                            <div style='display: flex; justify-content: space-between; margin-top: 6px; font-size: 0.8rem;'>
                                <span style='color: #2563eb; font-weight: 700;'>{card['hiring_score']:.1f}% Fit</span>
                                <span style='color: #64748b;'>{card['experience']} yrs</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    with st.popover(f"⚙️ Manage: {card['candidate_name']}", width="stretch"):
                        st.markdown(f"**Current Stage:** `{card['stage']}`")
                        new_stg = st.selectbox("Move Stage", STAGES, index=STAGES.index(card['stage']) if card['stage'] in STAGES else 0, key=f"ats_mv_{card['app_id']}")
                        if st.button("Update Stage", key=f"btn_mv_{card['app_id']}", type="primary"):
                            advance_candidate_stage(db, card['app_id'], new_stg)
                            st.rerun()

                        st.divider()
                        st.markdown("**🗓️ Schedule Interview**")
                        s_dt = st.text_input("Date/Time", value=card['interview_scheduled_at'] if card['interview_scheduled_at'] != "Not Scheduled" else "Tomorrow 10:00 AM", key=f"sdt_{card['app_id']}")
                        s_mode = st.selectbox("Mode", ["AI Mock Simulation", "Live Technical Video", "In-Person Executive"], key=f"smod_{card['app_id']}")
                        if st.button("Confirm Schedule", key=f"btn_cf_{card['app_id']}"):
                            schedule_interview(db, card['app_id'], s_dt, s_mode)
                            st.success("Interview scheduled!")
                            st.rerun()

                        st.divider()
                        st.markdown("**📝 Recruiter Feedback**")
                        r_score = st.slider("Rating (1-5)", 1.0, 5.0, float(card['recruiter_rating'] or 4.0), 0.5, key=f"rscr_{card['app_id']}")
                        r_fb = st.text_area("Feedback Notes", value=card['recruiter_feedback'], key=f"rfb_{card['app_id']}")
                        if st.button("Save Feedback", key=f"btn_rfb_{card['app_id']}"):
                            record_recruiter_feedback(db, card['app_id'], r_fb, r_score)
                            st.success("Feedback recorded!")
                            st.rerun()

    # --- 2. JOBS & TALENT POOL ---
    elif nav_option == "👥 Jobs & Talent Pool":
        st.markdown("<div class='section-title'>👥 Talent Pool & Job Descriptions</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Manage candidate directory, upload resumes in batch, post jobs with AI extraction, and review shortlisted candidates.</div>", unsafe_allow_html=True)

        tab_dir, tab_up, tab_jd, tab_short = st.tabs(["👥 Candidate Directory", "📤 Batch Resume Upload", "🎯 Job Descriptions", "⭐ Shortlisted Candidates"])

        # Tab 1: Candidate Directory
        with tab_dir:
            col_d_hdr1, col_d_hdr2 = st.columns([4, 2])
            with col_d_hdr1:
                st.markdown(f"#### 👥 Candidate Talent Pool (`{len(candidates_list)}` stored in persistent database)")
            with col_d_hdr2:
                with st.popover("🗑️ Clear Candidate Database", width="stretch"):
                    st.warning("⚠️ **Warning**: This will permanently delete all candidate profiles, parsed resumes, ATS applications, and mock interview reports.")
                    confirm_clear = st.checkbox("I confirm I want to clear candidate data", key="chk_clear_cand_db_rec")
                    if st.button("🔥 Yes, Clear Candidate Database", type="primary", disabled=not confirm_clear, key="btn_exec_clear_cand_db"):
                        res = clear_candidate_data(db)
                        st.success(f"Cleared {res['candidates']} candidates and {res['applications']} applications from database!")
                        time.sleep(0.5)
                        st.rerun()

            if not candidates_list:
                st.info("No candidates in the talent pool yet. Use the '📤 Batch Resume Upload' tab to add candidates or let candidates register.")
            else:
                search_query = st.text_input("🔍 Search Candidates by Name or Skill", "", key="dir_search_q")
                filtered_c = candidates_list
                if search_query:
                    q = search_query.lower()
                    filtered_c = [c for c in candidates_list if q in c.full_name.lower() or (c.email and q in c.email.lower()) or any(q in s for s in (c.skills or []))]

                st.write(f"Showing **{len(filtered_c)}** candidate(s):")
                for c in filtered_c:
                    col1, col2 = st.columns([5, 2])
                    with col1:
                        st.markdown(f"### 👤 {c.full_name} <span style='font-size:0.9rem; color:#64748b;'>({c.email or 'No Email'})</span>", unsafe_allow_html=True)
                        st.markdown(f"**Experience:** {c.parsed_experience} years | **Education:** {', '.join(c.parsed_education or ['N/A'])}")
                        badges = " ".join([f'<span class="skill-badge">{s}</span>' for s in (c.skills or [])])
                        st.markdown(badges or "No skills recorded", unsafe_allow_html=True)
                        if c.projects:
                            st.caption(f"**Key Projects:** {', '.join(c.projects)}")
                    with col2:
                        with st.popover("📄 Raw Resume"):
                            st.code(c.raw_text or "No raw text available.", language="text")
                        if st.button("🗑️ Delete Candidate", key=f"del_cand_dir_{c.id}"):
                            delete_candidate(db, c.id)
                            st.rerun()
                    st.divider()

        # Tab 2: Batch Resume Uploader
        with tab_up:
            st.markdown("### 📤 Upload Candidate Resumes")
            st.markdown("Upload candidate resume files (**PDF**, **DOCX**, **TXT**). Extracted candidate profiles are **permanently saved in the database** and automatically evaluated against all active job requirements.")
            
            up_resumes = st.file_uploader(
                "Choose resume files to parse & add to candidate talent pool:",
                type=["pdf", "docx", "txt"],
                accept_multiple_files=True,
                key="rec_batch_res_uploader_tab",
            )
            if up_resumes and st.button("⚡ Parse & Ingest Resumes to Database", type="primary"):
                with st.spinner("Parsing resumes, saving to database, and computing match evaluations..."):
                    new_cands = []
                    for uf in up_resumes:
                        raw_text = parse_document(uf.name, uf.read())
                        profile = extract_candidate_with_llm(raw_text, provider=st.session_state.llm_provider, api_key=st.session_state.api_key)
                        saved_c = save_candidate(db, {
                            "full_name": profile.full_name or uf.name.rsplit(".", 1)[0].replace("_", " ").title(),
                            "email": profile.email or f"{uf.name.rsplit('.', 1)[0].lower()}@candidate.org",
                            "phone": profile.phone,
                            "parsed_experience": profile.total_experience_years,
                            "parsed_education": profile.parsed_education,
                            "skills": profile.skills,
                            "projects": profile.projects,
                            "certifications": profile.certifications,
                            "raw_text": raw_text,
                        })
                        new_cands.append(saved_c)

                        # Auto-evaluate against all active jobs in database
                        for j in jobs_list:
                            rank_and_save_evaluations_for_job(db, j.id, [saved_c], j, weights=st.session_state.weights)
                            sync_shortlisted_candidates_to_ats(db, j.id)

                st.success(f"🎉 Successfully parsed and saved {len(new_cands)} candidate(s) into persistent database! All candidate records remain available until you select to clear the database.")
                st.rerun()

            st.divider()
            st.markdown("##### 🌱 Optional Sample Demo Data")
            st.caption("Load sample candidate records for quick testing and demonstration:")
            if st.button("🌱 Load 4 Sample Candidates (Demo)", type="secondary"):
                from sample_data import seed_demo_data
                seed_demo_data()
                st.success("Sample candidates loaded!")
                st.rerun()

        # Tab 3: Job Descriptions
        with tab_jd:
            with st.expander("➕ Create / Post New Job Opening", expanded=False):
                post_mode = st.radio("Posting Method:", ["📋 Paste Raw Job Description (Auto-Extract with AI)", "✍️ Manual Field Entry"], horizontal=True, key="jd_post_mode_r")

                if "📋 Paste" in post_mode:
                    st.markdown("Paste the entire job posting copied from any tool (**LinkedIn**, **Indeed**, **Workday**, **Greenhouse**, **PDF**, **Google Docs**, etc.).")
                    raw_jd = st.text_area("Paste Full Job Description:", height=150, placeholder="Job Title: Full-Stack Engineer\nResponsibilities: Build React and FastAPI web apps with 3+ years experience...")
                    
                    if st.button("⚡ Auto-Extract Job Requirements", type="primary", key="btn_ext_jd_r"):
                        if raw_jd.strip():
                            extracted = extract_job_with_llm(raw_jd, provider=st.session_state.llm_provider, api_key=st.session_state.api_key)
                            st.session_state.recruiter_job_draft = extracted.model_dump()
                            st.success("Extracted job details! Review and activate below.")

                    if "recruiter_job_draft" in st.session_state and st.session_state.recruiter_job_draft:
                        d = st.session_state.recruiter_job_draft
                        st.divider()
                        with st.form("save_extracted_job_form_tab"):
                            jt = st.text_input("Job Title *", value=d.get("title", ""))
                            jr = st.text_input("Role / Designation", value=d.get("role", ""))
                            jd_summary = st.text_area("Description Summary", value=d.get("description", ""))
                            col_a, col_b = st.columns(2)
                            with col_a:
                                sk_str = st.text_input("Required Skills *", value=", ".join(d.get("required_skills", [])))
                                exp_val = st.number_input("Min Experience (Years)", 0.0, 25.0, float(d.get("min_experience", 2.0)), 0.5)
                            with col_b:
                                edu_val = st.selectbox("Required Education", ["Bachelor's", "Master's", "Ph.D.", "Associate", "Any Degree"])
                                cert_str = st.text_input("Certifications", value=", ".join(d.get("certifications", [])))
                            
                            if st.form_submit_button("🚀 Save & Activate Job Posting", type="primary"):
                                if jt and sk_str:
                                    skills_l = [s.strip().lower() for s in sk_str.split(",") if s.strip()]
                                    certs_l = [c.strip() for c in cert_str.split(",") if c.strip()]
                                    new_j = save_job(db, {"title": jt, "role": jr or jt, "description": jd_summary, "required_skills": skills_l, "min_experience": exp_val, "required_education": edu_val, "certifications": certs_l})
                                    rank_and_save_evaluations_for_job(db, new_j.id, candidates_list, new_j, weights=st.session_state.weights)
                                    sync_shortlisted_candidates_to_ats(db, new_j.id)
                                    st.session_state.recruiter_job_draft = None
                                    st.success("Job posting activated!")
                                    st.rerun()

                else:
                    with st.form("manual_job_form_tab"):
                        jt = st.text_input("Job Title *", placeholder="e.g. Senior Cloud Architect")
                        jr = st.text_input("Role", placeholder="e.g. Cloud Lead")
                        jd_summary = st.text_area("Description", placeholder="Responsibilities and role summary...")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            sk_str = st.text_input("Required Skills (comma-separated) *", placeholder="python, aws, docker, kubernetes")
                            exp_val = st.number_input("Min Experience (Years)", 0.0, 25.0, 3.0, 0.5)
                        with col_b:
                            edu_val = st.selectbox("Required Education", ["Bachelor's", "Master's", "Ph.D.", "Associate", "Any Degree"])
                            cert_str = st.text_input("Certifications", placeholder="AWS Certified Solutions Architect")

                        if st.form_submit_button("🚀 Save Job Description", type="primary"):
                            if jt and sk_str:
                                skills_l = [s.strip().lower() for s in sk_str.split(",") if s.strip()]
                                certs_l = [c.strip() for c in cert_str.split(",") if c.strip()]
                                new_j = save_job(db, {"title": jt, "role": jr or jt, "description": jd_summary, "required_skills": skills_l, "min_experience": exp_val, "required_education": edu_val, "certifications": certs_l})
                                rank_and_save_evaluations_for_job(db, new_j.id, candidates_list, new_j, weights=st.session_state.weights)
                                sync_shortlisted_candidates_to_ats(db, new_j.id)
                                st.success("Job posting created!")
                                st.rerun()

            st.divider()
            st.subheader("💼 Active Job Listings")
            if jobs_list:
                for j in jobs_list:
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.markdown(f"### 💼 {j.title} <span style='font-size:0.9rem; color:#64748b;'>({j.role})</span>", unsafe_allow_html=True)
                        st.markdown(f"**Experience Requirement:** {j.min_experience} yrs | **Education:** {j.required_education}")
                        if j.description:
                            st.caption(f"{j.description[:220]}...")
                        badges = " ".join([f'<span class="skill-badge">{s}</span>' for s in j.required_skills])
                        st.markdown(badges, unsafe_allow_html=True)
                    with col2:
                        if st.button("🗑️ Delete", key=f"del_j_tab_{j.id}"):
                            delete_job(db, j.id)
                            st.rerun()
                    st.divider()
            else:
                st.info("No active job postings.")

        # Tab 4: Shortlisted Candidates & Search
        with tab_short:
            if not jobs_list:
                st.warning("Please create at least one Job Description.")
            else:
                col_sj, col_th = st.columns([3, 2])
                with col_sj:
                    sel_job = st.selectbox("Select Target Job Opening", jobs_list, format_func=lambda j: j.title, key="short_j_sel")
                with col_th:
                    min_score_thresh = st.slider("Shortlist Threshold (%)", 50.0, 95.0, 70.0, 5.0, key="thresh_slider")

                evals = get_evaluations_for_job(db, sel_job.id)
                shortlisted_evals = [ev for ev in evals if ev.overall_hiring_score >= min_score_thresh]

                if shortlisted_evals:
                    st.write(f"Displaying **{len(shortlisted_evals)}** candidate(s) meeting {min_score_thresh:.0f}%+ match threshold:")
                    for ev in shortlisted_evals:
                        cand = ev.candidate
                        col1, col2 = st.columns([5, 2])
                        with col1:
                            st.markdown(f"### 👤 #{ev.rank} - {cand.full_name} <span style='color:#059669; font-weight:700;'>({ev.overall_hiring_score:.1f}% Fit)</span>", unsafe_allow_html=True)
                            st.markdown(f"**Skill Match:** {ev.skill_match_pct:.1f}% | **Experience:** {cand.parsed_experience} yrs (Required: {sel_job.min_experience} yrs)")
                            badges = " ".join([f'<span class="matched-badge">✓ {s}</span>' for s in (ev.matched_skills or [])])
                            st.markdown(badges, unsafe_allow_html=True)
                        with col2:
                            st.write("")
                            if st.button("🗓️ Schedule Interview", key=f"short_sched_tab_{cand.id}_{sel_job.id}", width="stretch", type="primary"):
                                app = get_or_create_application(db, cand.id, sel_job.id, stage="Interview")
                                schedule_interview(db, app.id, "Tomorrow 10:00 AM", "AI Mock Simulation")
                                st.success(f"Interview scheduled for {cand.full_name}!")
                                st.rerun()
                        st.divider()
                else:
                    st.info(f"No candidates meet the {min_score_thresh:.0f}%+ score threshold for this position yet.")

    # --- 3. INTERVIEW HUB & SCHEDULES (CONSOLIDATED UNIFIED INTERVIEW CENTER) ---
    elif nav_option == "🗓️ Interview Hub & Schedules":
        st.markdown("<div class='section-title'>🗓️ AI Interview Management & Scheduling Hub</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Centralized command center to schedule interviews, track active interview sessions, generate question suites, and review performance reports.</div>", unsafe_allow_html=True)

        int_tab_sched, int_tab_list, int_tab_qgen, int_tab_rep = st.tabs([
            "⚡ Schedule New Interview",
            "📋 Scheduled & Active Interviews",
            "❓ AI Question Suite Generator",
            "📑 AI Performance Reports & Feedback",
        ])

        # TAB 1: 1-CLICK QUICK INTERVIEW SCHEDULER
        with int_tab_sched:
            st.markdown("### ⚡ Quick Interview Scheduler")
            st.markdown("Select a target job and candidate to immediately schedule an interview round and initialize questions.")

            if not jobs_list or not candidates_list:
                st.warning("You need at least 1 Job Description and 1 Candidate in the talent pool to schedule interviews.")
            else:
                with st.form("quick_schedule_form"):
                    col_sj, col_sc = st.columns(2)
                    with col_sj:
                        target_j = st.selectbox("1. Target Job Opening *", jobs_list, format_func=lambda j: f"💼 {j.title} ({j.role})")
                    with col_sc:
                        target_c = st.selectbox("2. Candidate to Interview *", candidates_list, format_func=lambda c: f"👤 {c.full_name} ({c.parsed_experience} yrs exp)")

                    col_sdt, col_smod = st.columns(2)
                    with col_sdt:
                        int_time_input = st.text_input("3. Scheduled Date & Time *", value="Tomorrow at 10:00 AM")
                    with col_smod:
                        int_mode_input = st.selectbox("4. Interview Mode", ["AI Mock Simulation", "Live Technical Video", "In-Person Executive"])

                    int_notes_input = st.text_area("5. Recruiter Focus Areas / Instructions (Optional)", placeholder="Focus on LLM architecture, vector databases, and system design trade-offs...")

                    if st.form_submit_button("🚀 Confirm & Schedule Interview", type="primary", width="stretch"):
                        app = get_or_create_application(db, target_c.id, target_j.id, stage="Interview")
                        schedule_interview(db, app.id, int_time_input, int_mode_input, int_notes_input)
                        
                        # Generate and cache question set
                        q_set = generate_interview_questions(job=target_j, candidate=target_c, provider=st.session_state.llm_provider, api_key=st.session_state.api_key)
                        st.session_state.sim_questions = q_set.technical_questions[:3] + q_set.behavioural_questions[:1] + q_set.situational_questions[:1]
                        st.session_state.sim_job_id = target_j.id
                        st.session_state.sim_candidate_id = target_c.id
                        st.session_state.sim_app_id = app.id

                        st.success(f"🎉 Interview successfully scheduled for {target_c.full_name} on {target_j.title}!")
                        st.rerun()

        # TAB 2: SCHEDULED & ACTIVE INTERVIEWS LIST
        with int_tab_list:
            st.markdown("### 📋 Active Scheduled Interviews")
            all_apps = get_all_applications(db)
            scheduled_apps = [a for a in all_apps if a.stage == "Interview" or (a.interview_scheduled_at and a.interview_scheduled_at != "Not Scheduled")]

            if not scheduled_apps:
                st.info("No active interviews currently scheduled. Use the '⚡ Schedule New Interview' tab to schedule one.")
            else:
                st.write(f"Found **{len(scheduled_apps)}** scheduled interview round(s):")
                for app in scheduled_apps:
                    cand = app.candidate
                    job = app.job
                    if not cand or not job:
                        continue

                    col1, col2 = st.columns([5, 2])
                    with col1:
                        st.markdown(
                            f"""
                            <div class='glass-card' style='border-left: 4px solid #7c3aed;'>
                                <div style='display:flex; justify-content:space-between; align-items:center;'>
                                    <span style='font-size:1.15rem; font-weight:800; color:#0f172a;'>👤 {cand.full_name} — 💼 {job.title}</span>
                                    <span class='stage-badge' style='background:#f5f3ff; color:#7c3aed; border:1px solid #ddd6fe;'>{app.stage.upper()}</span>
                                </div>
                                <div style='margin-top:6px; color:#334155; font-size:0.9rem;'>
                                    🗓️ <b>Scheduled Time:</b> {app.interview_scheduled_at or 'Ready'} | 🎙️ <b>Mode:</b> {app.interview_mode}
                                </div>
                                <div style='margin-top:4px; color:#64748b; font-size:0.85rem;'>
                                    📝 <b>Notes:</b> {app.recruiter_notes or 'Standard technical simulation'}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with col2:
                        st.write("")
                        with st.popover("⚙️ Manage & Move Stage", width="stretch"):
                            st.markdown(f"**Candidate:** {cand.full_name}")
                            up_stg = st.selectbox("Stage", STAGES, index=STAGES.index(app.stage) if app.stage in STAGES else 2, key=f"hub_stg_{app.id}")
                            up_time = st.text_input("Time", value=app.interview_scheduled_at or "Tomorrow 10:00 AM", key=f"hub_time_{app.id}")
                            if st.button("Update Interview Record", key=f"btn_hub_up_{app.id}", type="primary"):
                                schedule_interview(db, app.id, up_time, app.interview_mode)
                                advance_candidate_stage(db, app.id, up_stg)
                                st.success("Updated!")
                                st.rerun()

                        if st.button(f"🎉 Select Candidate", key=f"hub_sel_{app.id}", type="secondary", width="stretch"):
                            advance_candidate_stage(db, app.id, "Selected")
                            st.success(f"{cand.full_name} marked as Selected!")
                            st.rerun()
                    st.divider()

        # TAB 3: AI QUESTION SUITE GENERATOR
        with int_tab_qgen:
            st.markdown("### ❓ AI Interview Question Generator")
            st.markdown("Synthesize role-specific technical questions (Beginner, Intermediate, Advanced), STAR behavioural prompts, and situational scenario questions.")

            if not jobs_list:
                st.warning("Please create at least one Job Description first.")
            else:
                col1, col2 = st.columns(2)
                with col1:
                    q_job = st.selectbox("Select Target Job Opening", jobs_list, format_func=lambda j: f"{j.title} ({j.role})", key="qgen_hub_j")
                with col2:
                    q_cand = st.selectbox("Target Candidate (Optional for personalization)", [None] + candidates_list, format_func=lambda c: f"{c.full_name} ({c.parsed_experience} yrs)" if c else "General Role Benchmark", key="qgen_hub_c")

                if st.button("✨ Generate AI Interview Question Suite", type="primary", width="stretch", key="btn_gen_q_hub"):
                    with st.spinner("Analyzing job competencies and synthesizing role questions..."):
                        q_set = generate_interview_questions(job=q_job, candidate=q_cand, provider=st.session_state.llm_provider, api_key=st.session_state.api_key)
                        st.session_state.recruiter_generated_q_set = q_set
                        st.session_state.sim_questions = q_set.technical_questions + q_set.behavioural_questions + q_set.situational_questions
                        st.session_state.sim_job_id = q_job.id
                        st.session_state.sim_candidate_id = q_cand.id if q_cand else (candidates_list[0].id if candidates_list else None)

                if "recruiter_generated_q_set" in st.session_state and st.session_state.recruiter_generated_q_set:
                    q_set: InterviewQuestionSet = st.session_state.recruiter_generated_q_set
                    st.divider()
                    st.markdown(f"### 📋 Question Suite for **{q_set.job_title}** ({q_set.candidate_name})")

                    tab_t, tab_b, tab_s = st.tabs(["💻 Technical Questions", "🤝 Behavioural (STAR)", "🏢 Situational Scenarios"])
                    with tab_t:
                        for idx, q in enumerate(q_set.technical_questions, 1):
                            diff_class = f"difficulty-{q.difficulty.lower()}"
                            st.markdown(
                                f"""
                                <div class='question-card'>
                                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                                        <span style='font-size:0.85rem; font-weight:700; color:#2563eb;'>QUESTION {idx}</span>
                                        <span class='{diff_class}'>{q.difficulty.upper()}</span>
                                    </div>
                                    <div class='question-title'>{q.question_text}</div>
                                    <div style='margin-top:6px;'><span class='skill-badge'>Target: {q.target_skill.title()}</span></div>
                                    <div class='benchmark-box'>
                                        <b>🎯 Ideal Benchmark:</b> {q.sample_ideal_answer}
                                    </div>
                                    <div class='probe-box'>
                                        <b>🔍 Follow-up Probe:</b> {q.follow_up_question}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                    with tab_b:
                        for idx, q in enumerate(q_set.behavioural_questions, 1):
                            st.markdown(
                                f"""
                                <div class='question-card' style='border-left-color: #059669;'>
                                    <div style='font-size:0.85rem; font-weight:700; color:#059669;'>BEHAVIOURAL PROMPT {idx}</div>
                                    <div class='question-title'>{q.question_text}</div>
                                    <div style='margin-top:6px;'><span class='skill-badge' style='background:#ecfdf5; color:#047857; border-color:#a7f3d0;'>Competency: {q.target_skill}</span></div>
                                    <div class='benchmark-box'>
                                        <b>🎯 STAR Assessment Benchmark:</b> {q.sample_ideal_answer}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                    with tab_s:
                        for idx, q in enumerate(q_set.situational_questions, 1):
                            st.markdown(
                                f"""
                                <div class='question-card' style='border-left-color: #d97706;'>
                                    <div style='font-size:0.85rem; font-weight:700; color:#d97706;'>SCENARIO CASE {idx}</div>
                                    <div class='question-title'>{q.question_text}</div>
                                    <div style='margin-top:6px;'><span class='skill-badge' style='background:#fffbeb; color:#b45309; border-color:#fde68a;'>Domain: {q.target_skill}</span></div>
                                    <div class='scenario-box'>
                                        <b>🎯 Architectural & Decision Criteria:</b> {q.sample_ideal_answer}
                                    </div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

        # TAB 4: PERFORMANCE REPORTS & RECRUITER FEEDBACK
        with int_tab_rep:
            st.markdown("### 📑 AI Interview Performance Reports & Feedback Logs")
            all_sessions = get_all_interview_sessions(db, limit=20)
            if all_sessions:
                for s in all_sessions:
                    cand = s.candidate
                    job = s.job
                    cname = cand.full_name if cand else f"Candidate #{s.candidate_id}"
                    jtitle = job.title if job else "Role"

                    with st.expander(f"👤 **{cname}** — {jtitle} | Score: **{s.total_score}%** ({s.hiring_recommendation})"):
                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            st.metric("Composite Score", f"{s.total_score:.1f}%")
                        with c2:
                            st.metric("Technical Accuracy", f"{s.technical_score:.1f}%")
                        with c3:
                            st.metric("Communication Clarity", f"{s.communication_score:.1f}%")
                        with c4:
                            st.metric("Confidence Rating", f"{s.confidence_level} ({s.confidence_score:.0f}%)")

                        st.markdown(f"**AI Executive Summary:** {s.summary_report}")

                        col_str, col_imp = st.columns(2)
                        with col_str:
                            st.markdown("**✅ Identified Strengths:**")
                            for str_item in (s.strengths or []):
                                st.markdown(f"- {str_item}")
                        with col_imp:
                            st.markdown("**🎯 Areas for Improvement:**")
                            for imp_item in (s.improvements or []):
                                st.markdown(f"- {imp_item}")

                        if cand and job:
                            pdf_data = export_interview_report_pdf(s, cand, job, s.questions)
                            st.download_button(
                                f"📥 Download Performance Report for {cname} (PDF)",
                                data=pdf_data,
                                file_name=f"Interview_Report_{cname.replace(' ', '_')}.pdf",
                                mime="application/pdf",
                                key=f"rec_hub_pdf_{s.id}",
                                width="stretch",
                            )
            else:
                st.info("No AI interview sessions completed yet.")

    # --- 4. RECRUITMENT ANALYTICS ---
    elif nav_option == "📈 Recruitment Analytics":
        st.markdown("<div class='section-title'>📈 Recruitment Analytics & Skill Gap Intelligence</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Explore candidate competency comparisons, skill coverage heatmaps, and learning roadmaps.</div>", unsafe_allow_html=True)

        if not jobs_list:
            st.warning("Please create at least one Job Description.")
        else:
            selected_job = st.selectbox("Select Target Job Opening", jobs_list, format_func=lambda j: f"{j.title} ({j.role})", key="analytics_j_sel")
            evaluations = get_evaluations_for_job(db, selected_job.id)

            if not evaluations:
                st.info("No candidate evaluations computed for this job.")
            else:
                tab_ov, tab_dd = st.tabs(["📊 Leaderboard & Skill Matrix", "🔍 Candidate Deep-Dive & Roadmap"])
                
                with tab_ov:
                    c_bar, c_mat = st.columns([1, 1])
                    with c_bar:
                        fig_b = plot_top_candidates_bar(evaluations)
                        st.plotly_chart(fig_b, width="stretch")
                    with c_mat:
                        fig_m = plot_skill_coverage_matrix(evaluations, selected_job.required_skills or [])
                        st.plotly_chart(fig_m, width="stretch")

                    # CSV Export
                    csv_data = export_evaluations_csv(evaluations, selected_job.title)
                    st.download_button("📥 Export Matrix (CSV)", data=csv_data, file_name=f"Match_Matrix_{selected_job.title}.csv", mime="text/csv", width="stretch")

                with tab_dd:
                    sel_idx = st.selectbox("Select Candidate", range(len(evaluations)), format_func=lambda i: f"#{evaluations[i].rank} - {evaluations[i].candidate.full_name} ({evaluations[i].overall_hiring_score:.1f}%)")
                    sev = evaluations[sel_idx]
                    scand = sev.candidate

                    fig_g = plot_skills_gauge(sev.skill_match_pct, sev.overall_hiring_score)
                    st.plotly_chart(fig_g, width="stretch")

                    c_rad, c_don = st.columns([1, 1])
                    with c_rad:
                        cand_exp_score = min(100.0, (scand.parsed_experience / max(1.0, selected_job.min_experience)) * 100.0)
                        fig_r = plot_candidate_radar(scand.full_name, sev.skill_match_pct, cand_exp_score, 100.0, sev.overall_hiring_score)
                        st.plotly_chart(fig_r, width="stretch")
                    with c_don:
                        fig_d = plot_skills_donut(len(sev.matched_skills or []), len(sev.missing_skills or []), len(sev.additional_skills or []))
                        st.plotly_chart(fig_d, width="stretch")

                    st.divider()
                    st.subheader("💡 Automated Upskilling Recommendations")
                    recs = generate_training_recommendations(sev.missing_skills, provider=st.session_state.llm_provider, api_key=st.session_state.api_key)
                    for sk, crs in recs.items():
                        st.markdown(f"- **{sk.title()}:** {crs}")


# ==============================================================================
# ==============================================================================
# PORTAL 2: 👤 CANDIDATE PORTAL (Strictly Scoped to Active Candidate)
# ==============================================================================
# ==============================================================================

elif selected_portal == "👤 Candidate Portal":

    if not active_candidate:
        st.markdown(
            """
            <div class='glass-panel' style='text-align: center; padding: 40px 20px;'>
                <div style='font-size: 3rem; margin-bottom: 8px;'>👤</div>
                <div style='font-size: 1.4rem; font-weight: 800; color: #0f172a;'>No Candidate Resume Profile Linked Yet</div>
                <p style='color: #64748b; max-width: 520px; margin: 10px auto 20px auto; font-size: 0.95rem;'>
                    Upload your resume below to automatically parse your technical skills, experience, and projects to start applying for jobs and taking AI mock interviews.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📤 Upload Your Resume")
            c_file = st.file_uploader("Upload Resume File (PDF, DOCX, TXT):", type=["pdf", "docx", "txt"], key="cand_onboard_res")
            if c_file and st.button("⚡ Parse Resume & Activate Profile", type="primary"):
                raw_text = parse_document(c_file.name, c_file.read())
                prof = extract_candidate_with_llm(raw_text, provider=st.session_state.llm_provider, api_key=st.session_state.api_key)
                new_cand = save_candidate(db, {
                    "full_name": prof.full_name or current_user.get("full_name", "Candidate"),
                    "email": prof.email or current_user.get("email", ""),
                    "phone": prof.phone,
                    "parsed_experience": prof.total_experience_years,
                    "parsed_education": prof.parsed_education,
                    "skills": prof.skills,
                    "projects": prof.projects,
                    "certifications": prof.certifications,
                    "raw_text": raw_text,
                })
                save_user(db, {
                    "username": current_user["username"],
                    "candidate_id": new_cand.id,
                })
                # Auto-evaluate against all active jobs in database
                for j in jobs_list:
                    rank_and_save_evaluations_for_job(db, j.id, [new_cand], j, weights=st.session_state.weights)

                st.session_state.logged_candidate_id = new_cand.id
                st.session_state.authenticated_user["candidate_id"] = new_cand.id
                st.success("Resume parsed and profile activated! Loading portal...")
                time.sleep(0.5)
                st.rerun()

        with col2:
            st.markdown("### ✍️ Manual Profile Entry")
            with st.form("manual_cand_profile_form"):
                m_name = st.text_input("Full Name *", value=current_user.get("full_name", ""))
                m_email = st.text_input("Email *", value=current_user.get("email", ""))
                m_phone = st.text_input("Phone Number", placeholder="+1 (555) 123-4567")
                m_exp = st.number_input("Years of Experience", 0.0, 30.0, 2.0, 0.5)
                m_skills = st.text_input("Skills (comma-separated)", placeholder="python, react, fastapi, sql")

                if st.form_submit_button("🚀 Create Profile", type="primary", width="stretch"):
                    if m_name and m_email:
                        sk_l = [s.strip().lower() for s in m_skills.split(",") if s.strip()]
                        new_cand = save_candidate(db, {
                            "full_name": m_name,
                            "email": m_email,
                            "phone": m_phone,
                            "parsed_experience": m_exp,
                            "skills": sk_l,
                        })
                        save_user(db, {
                            "username": current_user["username"],
                            "candidate_id": new_cand.id,
                        })
                        # Auto-evaluate against all active jobs in database
                        for j in jobs_list:
                            rank_and_save_evaluations_for_job(db, j.id, [new_cand], j, weights=st.session_state.weights)

                        st.session_state.logged_candidate_id = new_cand.id
                        st.session_state.authenticated_user["candidate_id"] = new_cand.id
                        st.success("Profile created! Loading portal...")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Please provide your full name and email.")

    else:
        # Candidate Portal Banner
        st.markdown(
            f"""
            <div class='portal-banner'>
                <div>
                    <span style='font-size: 1.25rem; font-weight: 800; color: #0f172a;'>👋 Welcome back, {active_candidate.full_name}</span>
                    <div style='font-size: 0.85rem; color: #2563eb; margin-top: 2px;'>Candidate Self-Service, Application Tracker & AI Interview Hub</div>
                </div>
                <div style='text-align: right;'>
                    <span class='stage-badge' style='background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0;'>Verified Profile</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        cand_apps = get_applications_for_candidate(db, active_candidate.id)
        cand_sessions = get_interview_sessions_for_candidate(db, active_candidate.id)

        # --- 1. APPLICATION STATUS & DASHBOARD ---
        if nav_option == "📊 Application Status & Dashboard":
            st.markdown("<div class='section-title'>📊 Candidate Application Status & Dashboard</div>", unsafe_allow_html=True)
            st.markdown("<div class='sub-title'>Live tracking of your active recruitment stages, upcoming interview rounds, and application progress.</div>", unsafe_allow_html=True)

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Applications Submitted", f"{len(cand_apps)}")
            with c2:
                interviews_ready = sum(1 for a in cand_apps if a.stage in ["Interview", "Screening"] or (a.interview_scheduled_at and a.interview_scheduled_at != "Not Scheduled"))
                st.metric("Interviews Available", f"{interviews_ready}", delta="Active")
            with c3:
                last_score = cand_sessions[0].total_score if cand_sessions else 0.0
                st.metric("Latest Interview Score", f"{last_score:.1f}%" if cand_sessions else "N/A")
            with c4:
                selected_status = any(a.stage == "Selected" for a in cand_apps)
                st.metric("Hiring Decision", "🎉 Selected" if selected_status else ("In Review" if cand_apps else "No Apps"))

            st.divider()

            if not cand_apps:
                st.markdown(
                    """
                    <div class='glass-panel' style='text-align: center; padding: 35px 20px;'>
                        <div style='font-size: 2.5rem; margin-bottom: 8px;'>📬</div>
                        <div style='font-size: 1.2rem; font-weight: 800; color: #0f172a;'>No Active Applications Found</div>
                        <p style='color: #64748b; font-size: 0.9rem; max-width: 450px; margin: 6px auto 14px auto;'>
                            You have not submitted an application yet. Explore open roles and submit your application with one click!
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                for app in cand_apps:
                    job = app.job
                    if not job:
                        continue

                    badge_color = STAGE_COLORS.get(app.stage, "#64748b")
                    stage_order = ["Applied", "Screening", "Interview", "Selected"]
                    curr_stage_idx = stage_order.index(app.stage) if app.stage in stage_order else 0

                    st.markdown(
                        f"""
                        <div class='glass-panel' style='border-left: 5px solid {badge_color}; margin-bottom: 16px;'>
                            <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
                                <div>
                                    <div style='font-size: 1.3rem; font-weight: 800; color: #0f172a;'>💼 {job.title}</div>
                                    <div style='color: #64748b; font-size: 0.85rem; margin-top: 2px;'>
                                        🏢 <b>Department:</b> {job.department or 'Engineering'} | 🏷️ <b>Role:</b> {job.role} | 📅 <b>Applied:</b> {app.created_at.strftime('%b %d, %Y') if app.created_at else 'Recent'}
                                    </div>
                                </div>
                                <div>
                                    <span class='stage-badge' style='background: #f1f5f9; color: {badge_color}; border: 1px solid {badge_color}40; font-size: 0.82rem;'>
                                        STATUS: {app.stage.upper()}
                                    </span>
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Visual 4-Step Stepper Progress Bar
                    st.markdown("##### 🧭 Recruitment Stage Progression")
                    st1, st2, st3, st4 = st.columns(4)

                    # Step 1: Applied
                    with st1:
                        s1_active = curr_stage_idx == 0
                        s1_bg = "#ecfdf5" if curr_stage_idx > 0 else ("#eff6ff" if s1_active else "#f8fafc")
                        s1_border = "#10b981" if curr_stage_idx > 0 else ("#3b82f6" if s1_active else "#e2e8f0")
                        s1_icon = "✅" if curr_stage_idx > 0 else ("🔵" if s1_active else "⚪")
                        st.markdown(
                            f"""
                            <div style='background: {s1_bg}; border: 2px solid {s1_border}; border-radius: 12px; padding: 12px; text-align: center;'>
                                <div style='font-size: 1.05rem; font-weight: 700; color: #0f172a;'>{s1_icon} 1. Applied</div>
                                <div style='font-size: 0.75rem; color: #64748b; margin-top: 3px;'>Submitted</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    # Step 2: Screening
                    with st2:
                        s2_active = curr_stage_idx == 1
                        s2_bg = "#ecfdf5" if curr_stage_idx > 1 else ("#eff6ff" if s2_active else "#f8fafc")
                        s2_border = "#10b981" if curr_stage_idx > 1 else ("#3b82f6" if s2_active else "#e2e8f0")
                        s2_icon = "✅" if curr_stage_idx > 1 else ("🔵" if s2_active else "⚪")
                        st.markdown(
                            f"""
                            <div style='background: {s2_bg}; border: 2px solid {s2_border}; border-radius: 12px; padding: 12px; text-align: center;'>
                                <div style='font-size: 1.05rem; font-weight: 700; color: #0f172a;'>{s2_icon} 2. Screening</div>
                                <div style='font-size: 0.75rem; color: #64748b; margin-top: 3px;'>Skill Review</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    # Step 3: Interview
                    with st3:
                        s3_active = curr_stage_idx == 2
                        s3_bg = "#ecfdf5" if curr_stage_idx > 2 else ("#eff6ff" if s3_active else "#f8fafc")
                        s3_border = "#10b981" if curr_stage_idx > 2 else ("#3b82f6" if s3_active else "#e2e8f0")
                        s3_icon = "✅" if curr_stage_idx > 2 else ("🔵" if s3_active else "⚪")
                        st.markdown(
                            f"""
                            <div style='background: {s3_bg}; border: 2px solid {s3_border}; border-radius: 12px; padding: 12px; text-align: center;'>
                                <div style='font-size: 1.05rem; font-weight: 700; color: #0f172a;'>{s3_icon} 3. Interview</div>
                                <div style='font-size: 0.75rem; color: #64748b; margin-top: 3px;'>AI Mock / Technical</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    # Step 4: Decision
                    with st4:
                        s4_done = app.stage == "Selected"
                        s4_rej = app.stage == "Rejected"
                        s4_bg = "#ecfdf5" if s4_done else ("#fef2f2" if s4_rej else "#f8fafc")
                        s4_border = "#10b981" if s4_done else ("#ef4444" if s4_rej else "#e2e8f0")
                        s4_icon = "🎉" if s4_done else ("🚫" if s4_rej else "⚪")
                        s4_label = "Selected" if s4_done else ("Rejected" if s4_rej else "4. Decision")
                        st.markdown(
                            f"""
                            <div style='background: {s4_bg}; border: 2px solid {s4_border}; border-radius: 12px; padding: 12px; text-align: center;'>
                                <div style='font-size: 1.05rem; font-weight: 700; color: #0f172a;'>{s4_icon} {s4_label}</div>
                                <div style='font-size: 0.75rem; color: #64748b; margin-top: 3px;'>Final Decision</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    st.write("")
                    col_info, col_cta = st.columns([3, 2])
                    with col_info:
                        if app.stage == "Interview" or (app.interview_scheduled_at and app.interview_scheduled_at != "Not Scheduled"):
                            st.info(f"🎙️ **Interview Round Active!**\n\n• **Schedule:** {app.interview_scheduled_at or 'Ready for Simulation'}\n• **Interview Mode:** `{app.interview_mode}`\n\nLaunch the AI interview simulation to answer questions and record responses.")
                        elif app.stage == "Screening":
                            st.warning(f"🔍 **Under Recruiter Screening**\n\nYour skills profile is being matched against the role requirements.")
                        elif app.stage == "Selected":
                            st.success(f"🎉 **Congratulations! You are Selected for {job.title}!**\n\nThe recruitment team has approved your hiring recommendation.")
                        elif app.stage == "Rejected":
                            st.error(f"⚠️ **Application Status: Not Selected**\n\nReview the feedback and personalized upskilling roadmap in the portal.")
                        else:
                            st.info("📥 **Application Received**\n\nYour application has been received and is in the recruiter review queue.")

                    with col_cta:
                        if app.stage in ["Interview", "Screening"] or (app.interview_scheduled_at and app.interview_scheduled_at != "Not Scheduled"):
                            if st.button(f"🎙️ Launch AI Interview for {job.title}", key=f"btn_trk_int_{app.id}", type="primary", width="stretch"):
                                q_set = generate_interview_questions(job=job, candidate=active_candidate, provider=st.session_state.llm_provider, api_key=st.session_state.api_key)
                                st.session_state.sim_questions = q_set.technical_questions[:3] + q_set.behavioural_questions[:1] + q_set.situational_questions[:1]
                                st.session_state.sim_current_idx = 0
                                st.session_state.sim_evaluations = []
                                st.session_state.sim_answers = []
                                st.session_state.sim_completed = False
                                st.session_state.sim_report = None
                                st.session_state.sim_job_id = job.id
                                st.session_state.sim_candidate_id = active_candidate.id
                                st.session_state.sim_app_id = app.id
                                st.success("Interview session initialized! Navigate to '🎙️ AI Interview Center' in the sidebar.")
                        elif app.stage == "Selected":
                            st.balloons()

                    st.divider()

        # --- 2. BROWSE OPENINGS & APPLY ---
        elif nav_option == "💼 Browse Openings & Apply":
            st.markdown("<div class='section-title'>💼 Browse Job Openings & Quick Apply</div>", unsafe_allow_html=True)
            st.markdown("<div class='sub-title'>Explore open positions, review required skill profiles, and submit your application with one click.</div>", unsafe_allow_html=True)

            if not jobs_list:
                st.info("No active job postings found at this time.")
            else:
                applied_job_ids = {a.job_id for a in cand_apps}
                for job in jobs_list:
                    has_applied = job.id in applied_job_ids
                    col1, col2 = st.columns([4, 2])
                    with col1:
                        st.markdown(
                            f"""
                            <div class='glass-card' style='border-left: 4px solid #2563eb;'>
                                <div style='display: flex; justify-content: space-between; align-items: center;'>
                                    <span style='font-size: 1.15rem; font-weight: 800; color: #0f172a;'>💼 {job.title}</span>
                                    <span class='stage-badge' style='background: #eff6ff; color: #1d4ed8;'>{job.role}</span>
                                </div>
                                <div style='color: #64748b; font-size: 0.85rem; margin-top: 4px;'>
                                    🏢 <b>Dept:</b> {job.department or 'Engineering'} | ⏳ <b>Min Experience:</b> {job.min_experience} yrs | 🎓 <b>Education:</b> {job.required_education}
                                </div>
                                <div style='margin-top: 8px;'>
                                    {' '.join([f'<span class=\"skill-badge\">{s}</span>' for s in job.required_skills])}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    with col2:
                        if has_applied:
                            st.success("✅ Already Applied")
                            st.caption("Track live status in '📊 Application Status & Dashboard'.")
                        else:
                            if st.button(f"⚡ Quick Apply", key=f"quick_apply_{job.id}", type="primary", width="stretch"):
                                new_app = get_or_create_application(db, active_candidate.id, job.id, stage="Applied")
                                rank_and_save_evaluations_for_job(db, job.id, [active_candidate], job, weights=st.session_state.weights)
                                st.success(f"Application for {job.title} submitted successfully!")
                                time.sleep(0.5)
                                st.rerun()
                    st.write("")

        # --- 3. AI INTERVIEW CENTER (CONSOLIDATED UNIFIED INTERVIEW HUB) ---
        elif nav_option == "🎙️ AI Interview Center":
            st.markdown("<div class='section-title'>🎙️ AI Interview Hub & Simulation Center</div>", unsafe_allow_html=True)
            st.markdown("<div class='sub-title'>Take AI mock interviews with voice and text, practice question banks, and review performance reports.</div>", unsafe_allow_html=True)

            cand_tab_sim, cand_tab_bank, cand_tab_hist = st.tabs([
                "🎙️ Take AI Interview (Simulator)",
                "❓ Assigned Practice Questions",
                "📜 Past Performance & Upskilling",
            ])

            # TAB 1: AI MOCK INTERVIEW SIMULATOR
            with cand_tab_sim:
                if not st.session_state.sim_questions:
                    st.info("No active interview loaded yet. Select a job below to start your AI interview:")
                    if jobs_list:
                        for j in jobs_list:
                            col_j1, col_j2 = st.columns([4, 2])
                            with col_j1:
                                st.markdown(f"**💼 {j.title}** ({j.role}) — *Min Exp: {j.min_experience} yrs*")
                            with col_j2:
                                if st.button(f"🚀 Start AI Interview", key=f"start_sim_hub_{j.id}", type="primary", width="stretch"):
                                    q_set = generate_interview_questions(job=j, candidate=active_candidate, provider=st.session_state.llm_provider, api_key=st.session_state.api_key)
                                    st.session_state.sim_questions = q_set.technical_questions[:3] + q_set.behavioural_questions[:1] + q_set.situational_questions[:1]
                                    st.session_state.sim_current_idx = 0
                                    st.session_state.sim_evaluations = []
                                    st.session_state.sim_answers = []
                                    st.session_state.sim_completed = False
                                    st.session_state.sim_report = None
                                    st.session_state.sim_job_id = j.id
                                    st.session_state.sim_candidate_id = active_candidate.id
                                    st.rerun()
                    else:
                        st.warning("No active job postings available.")

                elif not st.session_state.sim_completed:
                    questions = st.session_state.sim_questions
                    cur_idx = st.session_state.sim_current_idx
                    total_q = len(questions)

                    if cur_idx < total_q:
                        curr_q = questions[cur_idx]
                        st.progress((cur_idx) / total_q)
                        st.caption(f"Question **{cur_idx + 1}** of **{total_q}** ({curr_q.category.title()} — {curr_q.difficulty})")

                        diff_class = f"difficulty-{curr_q.difficulty.lower()}"
                        st.markdown(
                            f"""
                            <div class='question-card' style='background: #ffffff; border: 1px solid #e2e8f0; border-left: 5px solid #2563eb; padding: 24px; box-shadow: 0 4px 16px rgba(37,99,235,0.06);'>
                                <div style='display: flex; justify-content: space-between; align-items: center;'>
                                    <span style='font-size: 0.85rem; font-weight: 800; color: #2563eb; letter-spacing: 0.04em;'>QUESTION {cur_idx + 1} OF {total_q} • {curr_q.category.upper()}</span>
                                    <span class='{diff_class}'>{curr_q.difficulty.upper()}</span>
                                </div>
                                <div style='font-size: 1.3rem; font-weight: 800; color: #0f172a; margin-top: 12px; line-height: 1.45;'>
                                    {curr_q.question_text}
                                </div>
                                <div style='margin-top: 10px;'>
                                    <span class='skill-badge'>🎯 Target Competency: {curr_q.target_skill.title()}</span>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        # TTS Audio Prompt & STT Component
                        tts_js = f"""
                        <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; margin-bottom: 10px; font-family: 'Plus Jakarta Sans', sans-serif;">
                            <div style="display: flex; align-items: center; justify-content: space-between;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <button id="spkBtn" style="background: #2563eb; color: white; border: none; border-radius: 8px; padding: 7px 14px; font-weight: 600; cursor: pointer;">🔊 Listen</button>
                                    <button id="recBtn" style="background: #dc2626; color: white; border: none; border-radius: 8px; padding: 7px 14px; font-weight: 600; cursor: pointer;">🎙️ Speak Answer</button>
                                </div>
                                <span id="sttStatus" style="color: #64748b; font-size: 0.85rem;">Mic ready</span>
                            </div>
                            <div id="transcriptBox" style="margin-top: 8px; font-size: 0.85rem; color: #334155; min-height: 20px; font-style: italic;">
                                (Click 'Speak Answer' to talk, or type below)
                            </div>
                        </div>
                        <script>
                        const spkBtn = document.getElementById('spkBtn');
                        const recBtn = document.getElementById('recBtn');
                        const sttStatus = document.getElementById('sttStatus');
                        const transcriptBox = document.getElementById('transcriptBox');

                        spkBtn.addEventListener('click', () => {{
                            if ('speechSynthesis' in window) {{
                                const u = new SpeechSynthesisUtterance("{curr_q.question_text.replace('\"', '')}");
                                window.speechSynthesis.speak(u);
                            }}
                        }});

                        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
                        if (SR) {{
                            const recognition = new SR();
                            recognition.continuous = true;
                            recognition.interimResults = true;
                            let isRec = false;

                            recBtn.addEventListener('click', () => {{
                                if (!isRec) {{
                                    recognition.start();
                                    isRec = true;
                                    recBtn.innerText = '⏹️ Stop Recording';
                                    recBtn.style.background = '#eab308';
                                    sttStatus.innerText = '🔴 Listening...';
                                }} else {{
                                    recognition.stop();
                                    isRec = false;
                                    recBtn.innerText = '🎙️ Speak Answer';
                                    recBtn.style.background = '#dc2626';
                                    sttStatus.innerText = 'Voice captured!';
                                }}
                            }});

                            recognition.onresult = (e) => {{
                                let text = '';
                                for (let i = e.resultIndex; i < e.results.length; ++i) {{
                                    text += e.results[i][0].transcript;
                                }}
                                transcriptBox.innerText = text;
                                navigator.clipboard.writeText(text);
                            }};
                        }}
                        </script>
                        """
                        components.html(tts_js, height=105)

                        ans_mode = st.radio("Response Format:", ["⌨️ Typed Text", "🎙️ Voice Transcribed"], horizontal=True, key=f"cand_hub_mod_{cur_idx}")
                        ans_text = st.text_area("Your Response:", placeholder="Explain core concepts, trade-offs, and practical project examples...", height=140, key=f"cand_ans_hub_{cur_idx}")

                        if st.button("⚡ Submit Response for AI Evaluation", type="primary", width="stretch", key=f"btn_sub_ans_{cur_idx}"):
                            if not ans_text.strip():
                                st.warning("Please type or speak your answer before submitting.")
                            else:
                                with st.spinner("AI evaluating technical accuracy & communication..."):
                                    ev_res = evaluate_single_answer(
                                        question_text=curr_q.question_text,
                                        target_skill=curr_q.target_skill,
                                        ideal_answer=curr_q.sample_ideal_answer,
                                        candidate_response=ans_text,
                                        provider=st.session_state.llm_provider,
                                        api_key=st.session_state.api_key,
                                    )
                                    st.session_state.sim_evaluations.append(ev_res)
                                    st.session_state.sim_answers.append({"question": curr_q, "answer": ans_text, "evaluation": ev_res, "mode": "voice" if "Voice" in ans_mode else "text"})

                                    if cur_idx + 1 < total_q:
                                        st.session_state.sim_current_idx += 1
                                        st.rerun()
                                    else:
                                        st.session_state.sim_completed = True
                                        st.rerun()

                elif st.session_state.sim_completed:
                    target_j = get_job_by_id(db, st.session_state.sim_job_id)
                    job_name = target_j.title if target_j else "Position"

                    if not st.session_state.sim_report:
                        with st.spinner("Compiling performance report..."):
                            rep: SessionReport = generate_overall_interview_report(
                                evaluations=st.session_state.sim_evaluations,
                                candidate_name=active_candidate.full_name,
                                job_title=job_name,
                                provider=st.session_state.llm_provider,
                                api_key=st.session_state.api_key,
                            )
                            st.session_state.sim_report = rep

                            sess = save_interview_session(db, {
                                "candidate_id": active_candidate.id,
                                "job_id": target_j.id if target_j else 1,
                                "total_score": rep.total_score,
                                "technical_score": rep.technical_score,
                                "communication_score": rep.communication_score,
                                "confidence_score": rep.confidence_score,
                                "confidence_level": rep.confidence_level,
                                "strengths": rep.strengths,
                                "improvements": rep.improvements,
                                "summary_report": rep.summary_report,
                                "hiring_recommendation": rep.hiring_recommendation,
                            })

                            for it in st.session_state.sim_answers:
                                save_interview_question(db, {
                                    "session_id": sess.id,
                                    "job_id": target_j.id if target_j else 1,
                                    "candidate_id": active_candidate.id,
                                    "category": it["question"].category,
                                    "difficulty": it["question"].difficulty,
                                    "question_text": it["question"].question_text,
                                    "target_skill": it["question"].target_skill,
                                    "candidate_response": it["answer"],
                                    "input_mode": it["mode"],
                                    "relevance_score": it["evaluation"].relevance_score,
                                    "clarity_score": it["evaluation"].clarity_score,
                                    "ai_feedback": it["evaluation"].technical_feedback,
                                })

                    rep = st.session_state.sim_report
                    st.success("🎉 AI Mock Interview Completed Successfully!")
                    st.markdown(f"## 🏆 Performance Report: **{active_candidate.full_name}**")
                    st.markdown(f"**Target Role:** `{job_name}` | **Outcome:** `<span style='color:#059669; font-weight:800;'>{rep.hiring_recommendation.upper()}</span>`", unsafe_allow_html=True)

                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("Total Score", f"{rep.total_score:.1f}%")
                    with c2:
                        st.metric("Technical Depth", f"{rep.technical_score:.1f}%")
                    with c3:
                        st.metric("Communication", f"{rep.communication_score:.1f}%")
                    with c4:
                        st.metric("Confidence", f"{rep.confidence_level}")

                    st.divider()

                    col_rad, col_fb = st.columns(2)
                    with col_rad:
                        fig_r = plot_candidate_radar(active_candidate.full_name, rep.technical_score, rep.communication_score, rep.confidence_score, rep.total_score)
                        st.plotly_chart(fig_r, width="stretch")
                    with col_fb:
                        st.markdown("**✅ Your Key Strengths:**")
                        for s in rep.strengths:
                            st.markdown(f"- **{s}**")
                        st.markdown("**🎯 Improvement Suggestions:**")
                        for i in rep.improvements:
                            st.markdown(f"- {i}")

                    if target_j:
                        dummy_s = InterviewSession(candidate_id=active_candidate.id, job_id=target_j.id, total_score=rep.total_score, technical_score=rep.technical_score, communication_score=rep.communication_score, confidence_score=rep.confidence_score, confidence_level=rep.confidence_level, strengths=rep.strengths, improvements=rep.improvements, summary_report=rep.summary_report, hiring_recommendation=rep.hiring_recommendation, created_at=datetime.now())
                        pdf_bytes = export_interview_report_pdf(dummy_s, active_candidate, target_j, [])
                        st.download_button("📥 Download Interview PDF Report", data=pdf_bytes, file_name=f"My_Interview_Report.pdf", mime="application/pdf", type="primary", width="stretch")

            # TAB 2: ASSIGNED PRACTICE QUESTIONS
            with cand_tab_bank:
                st.markdown("### ❓ Practice Question Pool")
                st.markdown("Review questions commonly evaluated for active positions:")
                if jobs_list:
                    for j in jobs_list:
                        with st.expander(f"💼 Role: **{j.title}**"):
                            q_set = generate_interview_questions(job=j, candidate=active_candidate)
                            for q in q_set.technical_questions + q_set.behavioural_questions:
                                st.markdown(f"- **[{q.difficulty}]** {q.question_text} *(Skill: {q.target_skill.title()})*")
                else:
                    st.info("No active job postings.")

            # TAB 3: PAST PERFORMANCE & UPSKILLING
            with cand_tab_hist:
                st.markdown("### 📜 Past Interview Sessions & Upskilling Roadmaps")
                if cand_sessions:
                    for s in cand_sessions:
                        job = s.job
                        with st.expander(f"🗓️ Session on {s.created_at.strftime('%Y-%m-%d %H:%M')} | {job.title if job else 'Role'} | Score: **{s.total_score}%**"):
                            c1, c2, c3 = st.columns(3)
                            with c1:
                                st.metric("Technical Score", f"{s.technical_score}%")
                            with c2:
                                st.metric("Communication", f"{s.communication_score}%")
                            with c3:
                                st.metric("Confidence", f"{s.confidence_level}")
                            st.caption(f"Summary: {s.summary_report}")
                else:
                    st.info("No past interview sessions recorded yet.")

                st.divider()
                st.subheader("💡 Recommended Upskilling Courses")
                all_missing = []
                for j in jobs_list:
                    ev = next((e for e in active_candidate.evaluations if e.job_id == j.id), None)
                    if ev:
                        all_missing.extend(ev.missing_skills)

                uniq_missing = list(dict.fromkeys(all_missing))
                if uniq_missing:
                    recs = generate_training_recommendations(uniq_missing, provider=st.session_state.llm_provider, api_key=st.session_state.api_key)
                    for sk, crs in recs.items():
                        st.markdown(
                            f"""
                            <div class='glass-card' style='border-left: 4px solid #2563eb;'>
                                <div style='font-size: 1rem; font-weight: 700; color: #0f172a;'>🎯 Skill: {sk.title()}</div>
                                <div style='font-size: 0.85rem; color: #64748b; margin-top: 2px;'>📚 <b>Recommended Course:</b> {crs}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                else:
                    st.success("🌟 Outstanding profile! You meet all technical skill requirements across active jobs.")

        # --- 4. MY PROFILE & RESUME ---
        elif nav_option == "👤 My Profile & Resume":
            st.markdown("<div class='section-title'>👤 My Profile & Resume Details</div>", unsafe_allow_html=True)
            st.markdown("<div class='sub-title'>Keep your profile information, contact details, and resume skills updated.</div>", unsafe_allow_html=True)

            prof_tab_info, prof_tab_res = st.tabs(["👤 Profile Information", "📄 Resume & Extracted Skills"])

            with prof_tab_info:
                with st.form("candidate_profile_edit_form_hub"):
                    p_name = st.text_input("Full Name", value=active_candidate.full_name)
                    p_email = st.text_input("Email Address", value=active_candidate.email or "")
                    p_phone = st.text_input("Phone Number", value=active_candidate.phone or "")
                    p_exp = st.number_input("Years of Experience", 0.0, 30.0, float(active_candidate.parsed_experience or 0.0), 0.5)
                    p_edu = st.text_input("Education (comma-separated)", value=", ".join(active_candidate.parsed_education or []))
                    
                    if st.form_submit_button("💾 Save Profile Changes", type="primary"):
                        edu_list = [e.strip() for e in p_edu.split(",") if e.strip()]
                        update_candidate(db, active_candidate.id, {
                            "full_name": p_name,
                            "email": p_email,
                            "phone": p_phone,
                            "parsed_experience": p_exp,
                            "parsed_education": edu_list,
                        })
                        st.success("Profile updated successfully!")
                        st.rerun()

            with prof_tab_res:
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🎯 Extracted Skills Profile")
                    badges = " ".join([f'<span class="skill-badge">{s}</span>' for s in (active_candidate.skills or [])])
                    st.markdown(badges or "No skills recorded.", unsafe_allow_html=True)

                    st.subheader("🏆 Key Projects & Certifications")
                    st.markdown(f"**Projects:** {', '.join(active_candidate.projects or ['None listed'])}")
                    st.markdown(f"**Certifications:** {', '.join(active_candidate.certifications or ['None listed'])}")

                with col2:
                    st.subheader("📤 Re-Upload / Update Resume")
                    up_file = st.file_uploader("Upload new resume (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"], key="cand_up_res_hub")
                    if up_file and st.button("⚡ Parse & Update Skills", type="primary", key="btn_reparse_res_hub"):
                        raw = parse_document(up_file.name, up_file.read())
                        prof = extract_candidate_with_llm(raw, provider=st.session_state.llm_provider, api_key=st.session_state.api_key)
                        update_candidate(db, active_candidate.id, {
                            "full_name": prof.full_name or active_candidate.full_name,
                            "parsed_experience": prof.total_experience_years,
                            "parsed_education": prof.parsed_education,
                            "skills": prof.skills,
                            "projects": prof.projects,
                            "certifications": prof.certifications,
                            "raw_text": raw,
                        })
                        st.success("Resume updated and re-parsed!")
                        st.rerun()


# ==============================================================================
# ==============================================================================
# PORTAL 3: 🛡️ ADMIN PORTAL
# ==============================================================================
# ==============================================================================

elif selected_portal == "🛡️ Admin Portal":

    # Admin Portal Banner
    st.markdown(
        """
        <div class='portal-banner' style='background: #fef2f2; border: 1px solid #fecaca;'>
            <div>
                <span style='font-size: 1.25rem; font-weight: 800; color: #0f172a;'>🛡️ Platform Administration & Governance Hub</span>
                <div style='font-size: 0.85rem; color: #dc2626; margin-top: 2px;'>System Monitoring, User Role Permissions, and Database Management</div>
            </div>
            <div>
                <span class='stage-badge' style='background: #fee2e2; color: #dc2626; border: 1px solid #fca5a5;'>Superadmin Active</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    admin_metrics = get_admin_system_metrics(db)

    # --- 1. ADMIN DASHBOARD ---
    if nav_option == "📊 Admin Dashboard":
        st.markdown("<div class='section-title'>📊 System Health & Governance Overview</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Platform-wide system metrics, user roles, active recruiters, and application audit counts.</div>", unsafe_allow_html=True)

        a1, a2, a3, a4, a5 = st.columns(5)
        with a1:
            st.metric("Total Users", f"{admin_metrics['total_users']}")
        with a2:
            st.metric("Candidates", f"{admin_metrics['total_candidates']}")
        with a3:
            st.metric("Active Jobs", f"{admin_metrics['total_jobs']}")
        with a4:
            st.metric("Applications", f"{admin_metrics['total_applications']}")
        with a5:
            st.metric("Interviews Taken", f"{admin_metrics['total_interviews']}")

        st.divider()

        col_l, col_r = st.columns([1, 1])
        with col_l:
            st.subheader("🖥️ API & LLM Infrastructure Status")
            st.markdown(
                f"""
                <div class='glass-card'>
                    <div><b>LLM Provider:</b> {st.session_state.llm_provider.title()}</div>
                    <div style='margin-top: 6px;'><b>Connection Mode:</b> {'🟢 Active API Key' if st.session_state.api_key else '🟡 Offline Heuristic Knowledge Engine'}</div>
                    <div style='margin-top: 6px;'><b>Database Status:</b> 🟢 Connected (SQLite / SQLAlchemy)</div>
                    <div style='margin-top: 6px;'><b>Web Speech STT:</b> 🟢 HTML5 Web Speech API Enabled</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_r:
            st.subheader("📈 Quick Platform Actions")
            if st.button("🌱 Re-Seed Full Demo Talent & User Pool", width="stretch"):
                seed_demo_data()
                st.success("Re-seeded all platform data!")
                st.rerun()
            if st.button("🗑️ Reset All Platform Tables", width="stretch"):
                reset_database()
                st.success("Database wiped cleanly.")
                st.rerun()

    # --- 2. USER MANAGEMENT ---
    elif nav_option == "👥 User Management":
        st.markdown("<div class='section-title'>👥 User Account & Role Management</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Create, inspect, and manage role-based user permissions (Recruiter, Candidate, Admin).</div>", unsafe_allow_html=True)

        users = get_all_users(db)
        with st.expander("➕ Create New User Account"):
            with st.form("admin_create_user_form"):
                u_uname = st.text_input("Username *", placeholder="e.g. recruiter_john")
                u_pwd = st.text_input("Password *", type="password", value="password123")
                u_name = st.text_input("Full Name *", placeholder="e.g. John Doe")
                u_email = st.text_input("Email Address *", placeholder="e.g. john@company.com")
                u_role = st.selectbox("Assign Role", ["Recruiter", "Candidate", "Admin"])
                if st.form_submit_button("Create User", type="primary"):
                    if u_uname and u_name and u_email:
                        save_user(db, {"username": u_uname, "password": u_pwd, "full_name": u_name, "email": u_email, "role": u_role})
                        st.success(f"User '{u_uname}' created with role '{u_role}'!")
                        st.rerun()

        st.divider()
        if users:
            u_data = [{"ID": u.id, "Username": u.username, "Full Name": u.full_name, "Email": u.email, "Role": u.role, "Status": "Active" if u.is_active else "Inactive", "Created": u.created_at.strftime("%Y-%m-%d %H:%M")} for u in users]
            st.dataframe(pd.DataFrame(u_data), width="stretch", hide_index=True)
        else:
            st.info("No users registered. Click 'Load Demo Talent Pool' in sidebar.")

    # --- 3. RECRUITER MANAGEMENT ---
    elif nav_option == "🏢 Recruiter Management":
        st.markdown("<div class='section-title'>🏢 Recruiter Directory & Governance</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Manage recruiter accounts, departmental assignments, and hiring authority.</div>", unsafe_allow_html=True)

        recruiters = get_all_users(db, role="Recruiter")
        if recruiters:
            for r in recruiters:
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"### 🏢 {r.full_name} <span style='font-size:0.85rem; color:#2563eb;'>@{r.username}</span>", unsafe_allow_html=True)
                    st.markdown(f"**Email:** {r.email} | **Status:** {'🟢 Active' if r.is_active else '🔴 Inactive'} | **Joined:** {r.created_at.strftime('%Y-%m-%d')}")
                with col2:
                    if st.button("Delete", key=f"del_rec_{r.id}"):
                        delete_user(db, r.id)
                        st.rerun()
                st.divider()
        else:
            st.info("No recruiter accounts found.")

    # --- 4. CANDIDATE MANAGEMENT ---
    elif nav_option == "👤 Candidate Management":
        st.markdown("<div class='section-title'>👤 Candidate Directory & Resume Records</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Central administrative oversight of all candidate profiles, parsed resumes, and evaluations.</div>", unsafe_allow_html=True)

        if candidates_list:
            for c in candidates_list:
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"### 👤 {c.full_name} <span style='font-size:0.85rem; color:#64748b;'>({c.email or 'No email'})</span>", unsafe_allow_html=True)
                    st.markdown(f"**Experience:** {c.parsed_experience} yrs | **Education:** {', '.join(c.parsed_education or ['N/A'])}")
                    st.markdown(" ".join([f'<span class="skill-badge">{s}</span>' for s in c.skills[:6]]), unsafe_allow_html=True)
                with col2:
                    if st.button("Delete", key=f"adm_del_c_{c.id}"):
                        delete_candidate(db, c.id)
                        st.rerun()
                st.divider()
        else:
            st.info("No candidate records found.")

    # --- 5. JOB & ROLE MANAGEMENT ---
    elif nav_option == "💼 Job & Role Management":
        st.markdown("<div class='section-title'>💼 Organization Job & Role Management</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Audit and manage organizational job requisitions across all departments.</div>", unsafe_allow_html=True)

        if jobs_list:
            for j in jobs_list:
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.markdown(f"### 💼 {j.title} <span style='font-size:0.85rem; color:#64748b;'>({j.role})</span>", unsafe_allow_html=True)
                    st.markdown(f"**Department:** {j.department} | **Min Exp:** {j.min_experience} yrs | **Required Skills:** {len(j.required_skills)} skills")
                with col2:
                    if st.button("Delete", key=f"adm_del_j_{j.id}"):
                        delete_job(db, j.id)
                        st.rerun()
                st.divider()
        else:
            st.info("No active jobs.")

    # --- 6. APPLICATION MANAGEMENT ---
    elif nav_option == "📑 Application Management":
        st.markdown("<div class='section-title'>📑 Centralized Application Audit Log</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Platform-wide record of all candidate applications and recruitment stage progression.</div>", unsafe_allow_html=True)

        all_apps = get_all_applications(db)
        if all_apps:
            app_records = []
            for a in all_apps:
                cname = a.candidate.full_name if a.candidate else "N/A"
                jtitle = a.job.title if a.job else "N/A"
                app_records.append({
                    "App ID": a.id,
                    "Candidate": cname,
                    "Job Position": jtitle,
                    "Stage": a.stage,
                    "Interview Scheduled": a.interview_scheduled_at or "Not Scheduled",
                    "Rating": f"{a.recruiter_rating or 0}/5",
                    "Last Updated": a.updated_at.strftime("%Y-%m-%d %H:%M") if a.updated_at else "",
                })
            st.dataframe(pd.DataFrame(app_records), width="stretch", hide_index=True)
        else:
            st.info("No applications recorded.")

    # --- 7. SYSTEM MONITORING & API SETTINGS ---
    elif nav_option == "🖥️ System Monitoring & API Settings":
        st.markdown("<div class='section-title'>🖥️ System Monitoring & API Configuration</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Configure AI model provider API keys, weights, and inspect infrastructure health.</div>", unsafe_allow_html=True)

        with st.form("admin_settings_form"):
            st.subheader("🔑 AI Model API Settings")
            prov = st.selectbox("LLM Provider", ["Google Gemini (Recommended)", "OpenAI GPT-4o"], index=0 if st.session_state.llm_provider == "google" else 1)
            k = st.text_input("API Key (Leave blank for 100% Offline Intelligent Engine)", value=st.session_state.api_key, type="password")

            st.subheader("⚖️ Algorithmic Matching Weights")
            w1 = st.slider("Skill Match Weight", 0.0, 1.0, float(st.session_state.weights[0]), 0.05)
            w2 = st.slider("Experience Match Weight", 0.0, 1.0, float(st.session_state.weights[1]), 0.05)
            w3 = st.slider("Education Fit Weight", 0.0, 1.0, float(st.session_state.weights[2]), 0.05)

            if st.form_submit_button("💾 Save System Configuration", type="primary"):
                st.session_state.llm_provider = "google" if "Gemini" in prov else "openai"
                st.session_state.api_key = k
                st.session_state.weights = (w1, w2, w3)
                st.success("Configuration updated successfully!")
                time.sleep(0.5)
                st.rerun()

        st.divider()
        st.subheader("🗄️ Database Management & Governance")
        st.caption("All candidate profiles and parsed resumes are stored permanently in the database. Use these controls only if you explicitly choose to clear the database.")

        col_adm_db1, col_adm_db2 = st.columns(2)
        with col_adm_db1:
            with st.popover("🗑️ Clear Candidate Database", width="stretch"):
                st.warning("⚠️ **Clear Candidates Only**: This will wipe candidate profiles, parsed resumes, ATS applications, and mock interview reports, while preserving recruiter accounts and job postings.")
                confirm_adm_cand = st.checkbox("Confirm wipe of all candidate records", key="chk_adm_clear_cand")
                if st.button("🔥 Yes, Clear Candidate Database", type="primary", disabled=not confirm_adm_cand, key="btn_adm_clear_cand"):
                    res = clear_candidate_data(db)
                    st.success(f"Cleared {res['candidates']} candidate records!")
                    time.sleep(0.5)
                    st.rerun()

        with col_adm_db2:
            with st.popover("⚠️ Full Platform Database Reset", width="stretch"):
                st.error("🚨 **Full Reset**: Drops and recreates all database tables (Users, Jobs, Candidates, Applications).")
                confirm_adm_full = st.checkbox("Confirm FULL platform database reset", key="chk_adm_clear_full")
                if st.button("💣 Execute Full Database Reset", type="primary", disabled=not confirm_adm_full, key="btn_adm_clear_full"):
                    reset_database()
                    st.session_state.authenticated_user = None
                    st.success("Database fully reset!")
                    time.sleep(0.5)
                    st.rerun()

    # --- 8. GLOBAL REPORTS & ANALYTICS ---
    elif nav_option == "📈 Global Reports & Analytics":
        st.markdown("<div class='section-title'>📈 Global Platform Reports & Analytics</div>", unsafe_allow_html=True)
        st.markdown("<div class='sub-title'>Platform-wide hiring velocity, application conversion rates, and global statistics.</div>", unsafe_allow_html=True)

        funnel = get_ats_funnel_metrics(db)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Total Candidates in Pipeline", f"{funnel['total_active']}")
        with c2:
            st.metric("Selection Conversion Rate", f"{funnel['conversion_rate']}%")
        with c3:
            st.metric("Interview Rate", f"{funnel['interview_rate']}%")

        st.divider()
        st.subheader("🏢 Candidate Distribution across Stages")
        st_df = pd.DataFrame({"Stage": list(funnel["counts"].keys()), "Candidates": list(funnel["counts"].values())})
        fig_funnel = px.bar(st_df, x="Stage", y="Candidates", color="Stage", color_discrete_sequence=["#64748b", "#2563eb", "#7c3aed", "#059669", "#dc2626"])
        fig_funnel.update_layout(paper_bgcolor="rgba(255,255,255,0)", plot_bgcolor="rgba(255,255,255,0)", font=dict(color="#0f172a"))
        st.plotly_chart(fig_funnel, width="stretch")
