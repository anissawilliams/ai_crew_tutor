"""
AI Java Tutor Pro - Main Application
Gamified learning experience with persona-based tutoring
"""
import streamlit as st
import sys
import os
import yaml
import traceback
from datetime import datetime

# Setup paths
base_dir = os.path.dirname(__file__)
sys.path.insert(0, base_dir)

# ==========================
# IMPORT UTILITIES
# ==========================
from utils.storage import load_user_progress, save_user_progress, load_ratings, save_rating
from utils.gamification import (
    get_xp_for_level, get_level_tier, get_affinity_tier,
    calculate_xp_progress, add_xp, update_streak, add_affinity
)
from utils.personas import build_persona_data, get_available_personas, PERSONA_UNLOCK_LEVELS
from utils.snippets import CODE_SNIPPETS, get_persona_snippets

# ==========================
# IMPORT COMPONENTS
# ==========================
from components.header import render_header
from components.sidebar import render_sidebar
from components.rewards import render_reward_popup
from components.persona_selector import render_persona_selector
from components.question_mode import render_question_mode
from components.code_review_mode import render_code_review_mode
from components.snippets_library import render_snippets_library
from components.analytics import render_analytics

# ==========================
# PAGE CONFIG
# ==========================
st.set_page_config(page_title="AI Java Tutor Pro", page_icon="🧠", layout="wide")

# ==========================
# LOAD CSS
# ==========================
def load_css():
    """Load custom CSS styling"""
    st.markdown("""
        <style>
        /* Keep all your CSS from app.py here */
        .level-card { ... }
        .persona-card { ... }
        .locked-persona { ... }
        .xp-bar { ... }
        .xp-fill { ... }
        .xp-text { ... }
        .streak-badge { ... }
        .affinity-bar { ... }
        .affinity-fill { ... }
        .explanation-box { ... }
        .code-review-box { ... }
        .snippet-card { ... }
        .snippet-locked { ... }
        .reward-popup { ... }
        @keyframes bounceIn { ... }
        .stApp { background-attachment: fixed; }
        </style>
    """, unsafe_allow_html=True)

load_css()

# ==========================
# LOAD AI CREW
# ==========================
try:
    from ai_hint_project.crew import create_crew
    AI_AVAILABLE = True
except ImportError:
    st.warning("⚠️ AI crew module not found. Running in demo mode.")
    AI_AVAILABLE = False
    def create_crew(persona, question):
        return f"[Demo Mode] {persona} would explain: {question[:50]}..."

# ==========================
# CACHE DATA
# ==========================
@st.cache_data(show_spinner=False)
def get_cached_persona_data():
    yaml_path = os.path.join(base_dir, 'ai_hint_project/config/agents.yaml')
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)

@st.cache_data(ttl=60)
def load_historical_ratings():
    return load_ratings()

# ==========================
# SESSION STATE INIT
# ==========================
def init_session_state():
    if 'user_progress' not in st.session_state:
        st.session_state.user_progress = load_user_progress()
    if 'current_persona' not in st.session_state:
        st.session_state.current_persona = None
    if 'active_mode' not in st.session_state:
        st.session_state.active_mode = 'question'
    if 'active_page' not in st.session_state:
        st.session_state.active_page = 'home'
    if 'explanation' not in st.session_state:
        st.session_state.explanation = None
    if 'code_review' not in st.session_state:
        st.session_state.code_review = None
    if 'show_reward' not in st.session_state:
        st.session_state.show_reward = None
    if 'show_rating' not in st.session_state:
        st.session_state.show_rating = False

init_session_state()
update_streak(st.session_state.user_progress, st.session_state)

# ==========================
# LOAD DATA
# ==========================
try:
    agents_config = get_cached_persona_data()
    persona_by_level, backgrounds, persona_options, persona_avatars = build_persona_data(agents_config)
except Exception as e:
    st.error(f"⚠️ Failed to load agents: {e}")
    st.stop()

historical_df = load_historical_ratings()
progress = st.session_state.user_progress
user_level = progress['level']
user_xp = progress['xp']
user_streak = progress['streak']
user_affinity = progress.get('affinity', {})
next_level_xp = get_xp_for_level(user_level)
xp_progress = calculate_xp_progress(user_xp, user_level)
tier = get_level_tier(user_level)

# ==========================
# RENDER REWARD POPUP
# ==========================
if st.session_state.show_reward:
    render_reward_popup(st.session_state.show_reward)
    if st.session_state.show_reward:
        st.balloons()

# ==========================
# RENDER HEADER
# ==========================
render_header(user_level, user_xp, user_streak, next_level_xp, xp_progress, tier)

# ==========================
# SIDEBAR
# ==========================
render_sidebar(user_level, user_xp, user_streak, persona_avatars, historical_df)

# ==========================
# MAIN CONTENT
# ==========================
if st.session_state.active_page == 'home':
    render_persona_selector(user_level, user_affinity, persona_avatars)
    if st.session_state.current_persona:
        selected_persona = st.session_state.current_persona
        if st.session_state.active_mode == 'question':
            render_question_mode(selected_persona, persona_avatars, create_crew, user_level)
        else:
            render_code_review_mode(selected_persona, persona_avatars, create_crew)

elif st.session_state.active_page == 'analytics':
    render_analytics(historical_df)

elif st.session_state.active_page == 'snippets':
    render_snippets_library(user_level, user_affinity, persona_avatars, get_available_personas, get_affinity_tier)

# ==========================
# FOOTER
# ==========================
st.divider()
st.caption(f"🧠 AI Java Tutor Pro | Level {user_level} • {user_streak} day streak 🔥")
