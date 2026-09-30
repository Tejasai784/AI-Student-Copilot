"""Settings & Environment Configuration View."""
import streamlit as st
from backend.config import settings
from services.llm_client import get_gemini_diagnostics
from ui.components import render_header, render_metric_card


def render_settings_page():
    render_header(
        title="⚙️ System & AI Settings",
        subtitle="Manage AI model provider preferences, environment credentials, and system configurations securely.",
        badge="Configuration & Security"
    )

    settings.reload()
    diag = get_gemini_diagnostics()

    st.markdown("### 🔑 Gemini AI Status")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        color = "#10B981" if diag["gemini_configured"] == "YES" else "#EF4444"
        render_metric_card("Gemini configured", diag["gemini_configured"], "API key presence check", border_color=color)
    with c2:
        conn_color = "#10B981" if "SUCCESS" in diag["gemini_connection"] else "#EF4444"
        render_metric_card("Gemini connection", diag["gemini_connection"], "Live verification test", border_color=conn_color)
    with c3:
        prov_color = "#10B981" if diag["active_provider"] == "Gemini" else "#3B82F6"
        render_metric_card("Active provider", diag["active_provider"], "Current operational engine", border_color=prov_color)
    with c4:
        render_metric_card("Active model", diag["active_model"], "Configured LLM", border_color="#6366F1")

    # Detailed status summary
    st.markdown("#### Status Overview")
    st.markdown(f"""
- **Gemini configured:** `{diag['gemini_configured']}`
- **Gemini connection:** `{diag['gemini_connection']}`
- **Active provider:** `{diag['active_provider']}`
- **Active model:** `{diag['active_model']}`
""")

    if diag["gemini_configured"] == "NO":
        st.warning("⚠️ **Gemini is not configured.** Enter your `GEMINI_API_KEY` below or add it to your `.env` file to activate Gemini AI capabilities.")
    elif "FAILED" in diag["gemini_connection"]:
        st.error(f"⚠️ **Gemini connection failed:** {diag.get('detail', 'Verification error')}. Please verify that your API key is valid and has Gemini API permissions enabled.")
    else:
        st.success("✅ **Gemini AI is connected and ready.**")

    st.divider()

    st.markdown("### 🔐 Configure Gemini Credentials")
    st.caption("You can securely configure or update your Gemini API credentials here. The key is masked (`••••••••`), written directly to `.env`, and never exposed.")

    from backend.config import update_env_file
    from models.ai_provider import GeminiProvider

    with st.form("gemini_credentials_form"):
        col_k, col_m = st.columns([3, 1])
        with col_k:
            key_input = st.text_input(
                "Gemini API Key (or Google API Key)",
                type="password",
                placeholder="Paste key (starts with AIza...)" if diag["gemini_configured"] == "NO" else "•••••••••••••••••••••••••••••••••••••• (Configured)",
                help="Key is stored locally in .env and masked from view."
            )
        with col_m:
            model_options = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
            current_model = settings.GEMINI_MODEL
            idx = model_options.index(current_model) if current_model in model_options else 0
            model_input = st.selectbox("Model", model_options, index=idx)

        submitted = st.form_submit_button("💾 Save Credentials & Connect", type="primary")
        if submitted:
            cleaned_key = key_input.strip()
            if not cleaned_key:
                if diag["gemini_configured"] == "YES":
                    # Just update model if key not re-entered
                    update_env_file({"GEMINI_MODEL": model_input})
                    st.success(f"Updated model to `{model_input}`.")
                    st.rerun()
                else:
                    st.error("Please enter a valid API key.")
            else:
                update_env_file({
                    "GEMINI_API_KEY": cleaned_key,
                    "GOOGLE_API_KEY": cleaned_key,
                    "GEMINI_MODEL": model_input,
                })
                # Test connection immediately
                test_prov = GeminiProvider(api_key=cleaned_key, model=model_input)
                success, msg = test_prov.test_connection()
                if success:
                    st.success(f"✅ Credentials successfully validated! Connected to `{model_input}`.")
                else:
                    st.error(f"❌ Connection test failed: {msg}")
                st.rerun()

    st.markdown("""
---
#### Manual `.env` Configuration
Alternatively, edit your `.env` file in the project root:
```bash
GEMINI_API_KEY=your_actual_key_here
GEMINI_MODEL=gemini-2.0-flash
```
*Note: API keys are loaded securely into the runtime environment and are never displayed in logs, UI, or diagnostics.*
""")
