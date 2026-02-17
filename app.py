#!/usr/bin/env python3
"""
Maui Travel Advisor — Web UI

Ask a travel question, get a personalized recommendation with explanation.
Supports Demo mode (mock data) or Live mode (Anthropic API + real weather).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="Maui Travel Advisor",
    page_icon="🌴",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom styles for a clean, travel-themed look
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    
    .stApp {
        background: linear-gradient(180deg, #f0f9f4 0%, #e8f5e9 30%, #fff 70%);
    }
    
    h1 {
        font-family: 'DM Sans', sans-serif;
        color: #1b5e20;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    
    .subtitle {
        color: #2e7d32;
        font-size: 1.05rem;
        margin-bottom: 2rem;
    }
    
    .input-section {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 12px rgba(27, 94, 32, 0.08);
        margin-bottom: 1.5rem;
        border: 1px solid #c8e6c9;
    }
    
    .result-box {
        background: white;
        padding: 1.5rem 1.75rem;
        border-radius: 12px;
        box-shadow: 0 2px 16px rgba(27, 94, 32, 0.12);
        margin-top: 1rem;
        border-left: 4px solid #2e7d32;
    }
    
    .recommendation-title {
        font-family: 'DM Sans', sans-serif;
        color: #1b5e20;
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
    }
    
    .explanation-block {
        background: #f1f8e9;
        padding: 1rem 1.25rem;
        border-radius: 8px;
        margin: 0.75rem 0;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    
    .score-badge {
        display: inline-block;
        background: #2e7d32;
        color: white;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    .mode-badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 500;
    }
    
    .mode-demo { background: #fff3e0; color: #e65100; }
    .mode-live { background: #e3f2fd; color: #1565c0; }
</style>
""", unsafe_allow_html=True)


def _build_profile_override_from_ui(ui_prefs: dict) -> dict:
    """Build profile dict (same shape as get_user_profile) from UI preference inputs."""
    if not ui_prefs or not ui_prefs.get("use_preferences"):
        return None
    # Defaults matching tools/mcp_server get_user_profile
    raw = {
        "preferred_temp_min": 75,
        "preferred_temp_max": 85,
        "rain_tolerance": "medium",
        "flight_budget_soft": int(ui_prefs.get("flight_budget_soft", 600)),
        "flight_budget_hard": int(ui_prefs.get("flight_budget_hard", 850)),
        "hotel_budget_min": int(ui_prefs.get("hotel_budget_min", 180)),
        "hotel_budget_max": int(ui_prefs.get("hotel_budget_max", 350)),
        "trip_length": ui_prefs.get("trip_length", "6-9 days"),
        "flexibility_days": int(ui_prefs.get("flexibility_days", 4)),
        "hotel_loyalty": "marriott_bonvoy",
        "safety_priority": 4,
        "comfort_priority": 4,
        "can_take_red_eye": False,
        "prefers_weekday_departure": True,
    }
    origin = (ui_prefs.get("origin") or "SFO").strip().upper()[:3]
    return {
        "user_id": "ui",
        "preferences": {},
        "raw_profile": raw,
        "origin": origin or "SFO",
    }


def run_demo_recommendation(query: str, profile_override: dict = None):
    """Run recommendation using mock data (no API key). Uses UI input for query and preferences."""
    from demo import create_mock_data
    from core.synthesis import synthesize_recommendation

    profile, weather, flights, hotels = create_mock_data(profile_override=profile_override)
    recommendation = synthesize_recommendation(weather, flights, hotels, profile)
    return recommendation.format_recommendation(), recommendation


def run_live_recommendation(query: str, profile_override: dict = None):
    """Run recommendation using coordinator (Anthropic API + real weather). Uses UI input."""
    from agent.coordinator import MauiTravelCoordinator

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. Set it in your environment or use Demo mode."
        )
    coordinator = MauiTravelCoordinator(api_key)
    result = coordinator.process_query(query, profile_override=profile_override)
    return result, None


def main():
    st.markdown("# 🌴 Maui Travel Advisor")
    mode = st.radio(
        "Mode",
        options=["Demo (mock data, no API key)", "Live (Anthropic API + real weather)"],
        index=0,
        horizontal=True,
        label_visibility="collapsed",
    )
    use_live = "Live" in mode

    # One box only: type your question here
    query = st.text_area(
        "Your question",
        value="",
        height=120,
        placeholder="e.g. When should I go to Maui this month? Is it a good time? Best time for a week?",
        label_visibility="visible",
    )

    with st.expander("Your preferences (optional)"):
        use_prefs = st.checkbox("Use these preferences for the recommendation", value=False)
        c1, c2 = st.columns(2)
        with c1:
            origin = st.text_input("Origin airport (e.g. SFO, LAX)", value="SFO", max_chars=3)
            trip_length = st.selectbox(
                "Trip length",
                options=["3-5 days", "6-9 days", "10-14 days", "15+ days"],
                index=1,
            )
            flexibility_days = st.slider("Date flexibility (days)", 0, 14, 4)
        with c2:
            flight_budget_soft = st.number_input("Target flight budget ($)", min_value=200, max_value=2000, value=600, step=50)
            flight_budget_hard = st.number_input("Max flight budget ($)", min_value=300, max_value=2500, value=850, step=50)
            hotel_budget_min = st.number_input("Hotel min $/night", min_value=80, max_value=500, value=180, step=20)
            hotel_budget_max = st.number_input("Hotel max $/night", min_value=150, max_value=800, value=350, step=20)
    ui_prefs = {
        "use_preferences": use_prefs,
        "origin": (origin or "SFO").strip().upper()[:3],
        "trip_length": trip_length,
        "flexibility_days": flexibility_days,
        "flight_budget_soft": flight_budget_soft,
        "flight_budget_hard": flight_budget_hard,
        "hotel_budget_min": hotel_budget_min,
        "hotel_budget_max": hotel_budget_max,
    }
    profile_override = _build_profile_override_from_ui(ui_prefs)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        run = st.button("Get recommendation", type="primary", use_container_width=True)

    if run and query.strip():
        with st.spinner("Analyzing weather, flights, and hotels…"):
            try:
                if use_live:
                    text_result, rec_obj = run_live_recommendation(query.strip(), profile_override=profile_override)
                else:
                    text_result, rec_obj = run_demo_recommendation(query.strip(), profile_override=profile_override)
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

        st.success("Recommendation ready.")

        # Summary / scoring if we have the recommendation object (demo mode)
        if rec_obj is not None:
            rec_window = rec_obj.recommended_window
            st.markdown("### 📊 Score summary")
            st.markdown(
                f"""
                <span class="score-badge">Weather {rec_window.weather_score:.1f}/100</span>
                <span class="score-badge">Flight {rec_window.flight_score:.1f}/100</span>
                <span class="score-badge">Hotel {rec_window.hotel_score:.1f}/100</span>
                <span class="score-badge">Overall {rec_window.overall_score:.1f}/100</span>
                """,
                unsafe_allow_html=True,
            )
            st.caption("Weights: Weather 40%, Flight 35%, Hotel 25%")
            st.markdown("---")

        st.markdown("### 🌺 Recommendation & explanation")
        st.markdown('<div class="result-box">', unsafe_allow_html=True)
        # Render as markdown so line breaks and structure show nicely
        st.markdown(text_result)
        st.markdown("</div>", unsafe_allow_html=True)

    elif run and not query.strip():
        st.warning("Please enter a question.")

    # Footer
    st.markdown("---")
    st.caption(
        "Maui Travel Advisor uses a 6-stage process: reflection → profile → weather → flights → hotels → synthesis."
    )


if __name__ == "__main__":
    main()
