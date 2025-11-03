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
from utils.gamification import get_xp_for_level, get_level_tier, get_affinity_tier, calculate_xp_progress, add_xp, update_streak, add_affinity
from utils.personas import build_persona_data, get_available_personas, PERSONA_UNLOCK_LEVELS
from utils.snippets import CODE_SNIPPETS

# ==========================
# IMPORT COMPONENTS
# ==========================
from components import (
    render_header,
    render_sidebar,
    render_reward_popup,
    render_persona_selector,
    render_question_mode,
    render_code_review_mode,
    render_snippets_library,
    render_analytics
)

# ==========================
# PAGE CONFIG & CSS
# ==========================
st.set_page_config(page_title="AI Java Tutor Pro", page_icon="🧠", layout="wide")

# --- Load CSS ---
st.markdown("""
<style>
.level-card { background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); padding:20px; border-radius:15px; border:2px solid rgba(255,255,255,0.2); margin-bottom:20px;}
.persona-card { padding:20px; border-radius:10px; color:white; margin:10px 0; transition: transform 0.3s; border:2px solid rgba(255,255,255,0.3); backdrop-filter: blur(10px);}
.persona-card:hover { transform: scale(1.02);}
.locked-persona { opacity:0.5; filter: grayscale(100%);}
.xp-bar { height:30px; background: rgba(0,0,0,0.3); border-radius:15px; overflow:hidden; position:relative;}
.xp-fill { height:100%; background: linear-gradient(90deg,#43e97b 0%,#38f9d7 100%); transition: width 0.5s ease;}
.xp-text { position:absolute; top:50%; left:50%; transform: translate(-50%,-50%); font-weight:bold; color:white; text-shadow:0 0 10px rgba(0,0,0,0.5);}
.streak-badge { display:inline-flex; align-items:center; background: linear-gradient(135deg,#f093fb 0%,#f5576c 100%); padding:10px 20px; border-radius:20px; font-size:24px; font-weight:bold; color:white;}
.affinity-bar { height:8px; background: rgba(255,255,255,0.2); border-radius:4px; overflow:hidden; margin-top:5px;}
.affinity-fill { height:100%; background: linear-gradient(90deg,#ffd93d 0%,#f5576c 100%);}
.explanation-box { background-color: rgba(230,247,255,0.1); backdrop-filter: blur(10px); padding:20px; border-radius:10px; border-left:4px solid #1890ff; margin:15px 0; color:white;}
.code-review-box { background-color: rgba(40,40,60,0.9); backdrop-filter: blur(10px); padding:20px; border-radius:10px; border-left:4px solid #f5576c; margin:15px 0; color:white;}
.snippet-card { background: rgba(255,255,255,0.1); backdrop-filter: blur(10px); padding:15px; border-radius:10px; border:2px solid rgba(255,255,255,0.2); margin:10px 0;}
.snippet-locked { opacity:0.6; filter: grayscale(80%);}
.reward-popup { position: fixed; top:50%; left:50%; transform:translate(-50%,-50%); background:linear-gradient(135deg,#667eea 0%,#764ba2 100%); padding:40px; border-radius:20px; box-shadow:0 10px 50px rgba(0,0,0,0.5); z-index:1000; text-align:center; animation:bounceIn 0.5s;}
@keyframes bounceIn { 0% {transform: translate(-50%,-50%) scale(0.3);} 50% {transform: translate(-50%,-50%) scale(1.05);} 100% {transform: translate(-50%,-50%) scale(1);}}
.stApp { background-attachment: fixed;}
</style>
""", unsafe_allow_html=True)

# ==========================
# AI CREW
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
# CACHED DATA
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
    if 'show_reward' not in st.session_state:
        st.session_state.show_reward = None
    if 'show_snippets' not in st.session_state:
        st.session_state.show_snippets = False
    if 'show_analytics' not in st.session_state:
        st.session_state.show_analytics = False
    if 'explanation' not in st.session_state:
        st.session_state.explanation = None
    if 'code_review' not in st.session_state:
        st.session_state.code_review = None
    if 'show_rating' not in st.session_state:
        st.session_state.show_rating = False
    if 'current_question' not in st.session_state:
        st.session_state.current_question = ""

init_session_state()
update_streak(st.session_state.user_progress, st.session_state)

# ==========================
# LOAD PERSONA DATA
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
# RENDER HEADER & SIDEBAR
# ==========================
render_header(user_level, user_xp, user_streak, next_level_xp, xp_progress, tier)
render_sidebar(user_level, user_xp, user_streak, persona_avatars, historical_df)

# ==========================
# RENDER REWARD POPUP
# ==========================
if st.session_state.show_reward:
    render_reward_popup(st.session_state.show_reward)

# ==========================
# MAIN CONTENT ROUTER
# ==========================
if st.session_state.show_snippets:
    render_snippets_library(user_level, user_affinity)
elif st.session_state.show_analytics:
    render_analytics(historical_df)
else:
    render_persona_selector(user_level, user_affinity, persona_avatars)
    
    if st.session_state.current_persona:
        selected_persona = st.session_state.current_persona
        selected_background = backgrounds.get(selected_persona, "rgba(102, 126, 234, 0.85)")
        
        st.markdown(f"""
            <style>
                .stApp {{
                    background: {selected_background};
                    background-attachment: fixed;
                }}
            </style>
        """, unsafe_allow_html=True)
        
        if st.session_state.active_mode == 'question':
            render_question_mode(selected_persona, persona_avatars, create_crew, user_level)
        else:
            render_code_review_mode(selected_persona, persona_avatars, create_crew)
