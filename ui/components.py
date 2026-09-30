import streamlit as st

def render_header(title: str, subtitle: str = "", badge: str = ""):
    """Renders a clean, professional section header."""
    badge_html = f'<span style="background-color: #2563EB; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; margin-left: 8px; vertical-align: middle;">{badge}</span>' if badge else ""
    st.markdown(
        f"""
        <div style="margin-bottom: 1.5rem;">
            <h1 style="font-size: 1.8rem; font-weight: 700; color: #1E293B; margin-bottom: 0.2rem; display: flex; align-items: center;">
                {title} {badge_html}
            </h1>
            <p style="font-size: 0.95rem; color: #64748B; margin-top: 0;">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_metric_card(title: str, value: str, subtitle: str = "", border_color: str = "#3B82F6"):
    """Renders a modern metric card."""
    st.markdown(
        f"""
        <div style="
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-left: 4px solid {border_color};
            border-radius: 10px;
            padding: 1rem 1.2rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        ">
            <div style="font-size: 0.82rem; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 0.05em;">{title}</div>
            <div style="font-size: 1.7rem; font-weight: 700; color: #0F172A; margin: 0.3rem 0;">{value}</div>
            <div style="font-size: 0.8rem; color: #94A3B8;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_empty_state(message: str, action_text: str = "", icon: str = "ℹ️"):
    """Renders a clean empty state card."""
    st.markdown(
        f"""
        <div style="
            text-align: center;
            background: #F8FAFC;
            border: 1px dashed #CBD5E1;
            border-radius: 12px;
            padding: 2.5rem 1.5rem;
            margin: 1rem 0;
        ">
            <div style="font-size: 2rem; margin-bottom: 0.5rem;">{icon}</div>
            <div style="font-size: 1rem; font-weight: 600; color: #334155; margin-bottom: 0.3rem;">{message}</div>
            <div style="font-size: 0.85rem; color: #64748B;">{action_text}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
