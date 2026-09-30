from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from backend.config import settings, reload_env
from backend.logging_config import logger
from database.database import init_db, get_db
from database.crud import get_student_profile

# Ensure latest environment variables are synced on run
reload_env()

# Initialize database tables on app launch
try:
    init_db()
except Exception as e:
    logger.critical(f"Database initialization failure: {e}", exc_info=True)
    st.error("Failed to initialize database. Please check your configuration.")

# Configure Streamlit page
st.set_page_config(
    page_title=settings.APP_NAME,
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern, professional student UI
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1200px;
    }
    
    /* Global fonts and colors */
    html, body, [class*="css"] {
        color: #1E293B;
    }
    
    /* Sidebar branding */
    .sidebar-brand {
        padding: 0.5rem 0 1rem 0;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 1rem;
    }
    .brand-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1E3A8A;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .brand-subtitle {
        font-size: 0.78rem;
        color: #64748B;
        margin-top: 2px;
    }
    
    /* Student badge */
    .student-badge {
        background-color: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-radius: 8px;
        padding: 0.5rem 0.8rem;
        font-size: 0.82rem;
        color: #334155;
        margin-bottom: 1.2rem;
    }
    
    /* Form buttons */
    .stButton>button[kind="primary"] {
        background-color: #2563EB;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        border: none;
    }
    .stButton>button[kind="primary"]:hover {
        background-color: #1D4ED8;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="brand-title">🎓 AI Student Copilot</div>
        <div class="brand-subtitle">Personalized Academic Assistant</div>
    </div>
    """, unsafe_allow_html=True)

    # Show active student info in sidebar
    profile_info = None
    with get_db() as db:
        profile = get_student_profile(db)
        if profile:
            profile_info = {
                "name": profile.name,
                "course": profile.course,
                "semester": profile.semester
            }

    if profile_info:
        st.markdown(f"""
        <div class="student-badge">
            <strong>👤 {profile_info['name']}</strong><br>
            <span style="font-size: 0.75rem; color: #64748B;">{profile_info['course']} • {profile_info['semester']}</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="student-badge" style="background-color: #FEF3C7; border-color: #FCD34D;">
            <strong>👋 Welcome!</strong><br>
            <span style="font-size: 0.75rem; color: #92400E;">Profile not set yet.</span>
        </div>
        """, unsafe_allow_html=True)

    nav_selection = st.radio(
        "Navigation",
        options=[
            "📊 Dashboard",
            "💬 AI Chat",
            "🎯 My Goals",
            "📅 Study Planner",
            "📄 Uploaded Materials",
            "🧠 Knowledge Base",
            "🤖 Agents & Execution Trace",
            "📝 Quizzes & Mock Exams",
            "📈 Progress & Weaknesses",
            "📑 Reports",
            "👤 Student Profile",
            "📚 Subjects & Syllabus",
            "🧠 Memory & Personalization",
            "⚙️ Settings",
            "🛠️ Developer Diagnostics"
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.caption(f"v{settings.APP_VERSION} • {settings.APP_ENV.title()} Mode")

# ----------------------------------------------------------------------------
# PAGE ROUTING
# ----------------------------------------------------------------------------
try:
    if nav_selection == "📊 Dashboard":
        from ui.dashboard import render_dashboard_page
        render_dashboard_page()

    elif nav_selection == "💬 AI Chat":
        from ui.tutor import render_tutor
        render_tutor()

    elif nav_selection == "🎯 My Goals":
        from ui.goals_view import render_goals_page
        render_goals_page()

    elif nav_selection == "📅 Study Planner":
        from ui.planner_view import render_planner_page
        render_planner_page()

    elif nav_selection == "📄 Uploaded Materials":
        from ui.materials import render_materials_page
        render_materials_page()

    elif nav_selection == "🧠 Knowledge Base":
        from ui.knowledge_view import render_knowledge_base_page
        render_knowledge_base_page()

    elif nav_selection == "🤖 Agents & Execution Trace":
        from ui.agents_view import render_agents_trace_page
        render_agents_trace_page()

    elif nav_selection == "📝 Quizzes & Mock Exams":
        from ui.quizzes_view import render_quizzes_page
        render_quizzes_page()

    elif nav_selection == "📈 Progress & Weaknesses":
        from ui.analytics_view import render_analytics_page
        render_analytics_page()

    elif nav_selection == "📑 Reports":
        from ui.reports_view import render_reports_page
        render_reports_page()

    elif nav_selection == "👤 Student Profile":
        from ui.profile import render_profile_page
        render_profile_page()

    elif nav_selection == "📚 Subjects & Syllabus":
        from ui.subjects import render_subjects_page
        render_subjects_page()

    elif nav_selection == "🧠 Memory & Personalization":
        from ui.memory_view import render_memory_page
        render_memory_page()

    elif nav_selection == "⚙️ Settings":
        from ui.settings_view import render_settings_page
        render_settings_page()

    elif nav_selection == "🛠️ Developer Diagnostics":
        from ui.diagnostics_view import render_diagnostics_page
        render_diagnostics_page()

except Exception as ex:
    logger.error(f"Error rendering page {nav_selection}: {ex}", exc_info=True)
    st.error("An unexpected error occurred while loading this page. Please try refreshing or check the application logs.")
