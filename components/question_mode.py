"""
Question asking mode component
"""
import streamlit as st
import traceback
from datetime import datetime
from utils.gamification import add_xp, add_affinity
from utils.storage import save_rating, save_user_progress

def render_question_mode(selected_persona, persona_avatars, create_crew, user_level):
    """Render question asking interface"""
    st.subheader("💬 Ask Your Java Question")
    user_question = st.text_area(
        "Enter your programming question:",
        height=150,
        placeholder="e.g., How do I implement a LinkedList in Java?",
        key="question_input"
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        ask_button = st.button("🚀 Get Explanation (+10 XP)", type="primary", use_container_width=True)
    
    with col2:
        if st.session_state.explanation:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.explanation = None
                st.session_state.show_rating = False
                st.rerun()
    
    # Process question
    if ask_button:
        if not user_question.strip():
            st.warning("⚠️ Please enter a question first!")
        else:
            try:
                with st.spinner(f"{persona_avatars[selected_persona]} Thinking..."):
                    result = create_crew(selected_persona, user_question)
                
                st.session_state.explanation = result
                st.session_state.current_question = user_question
                st.session_state.show_rating = True
                
                # Award XP and affinity
                leveled_up = add_xp(st.session_state.user_progress, 10, st.session_state)
                add_affinity(st.session_state.user_progress, selected_persona, 10, st.session_state)
                
                if leveled_up:
                    save_user_progress(st.session_state.user_progress)
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                with st.expander("Show detailed error"):
                    st.code(traceback.format_exc())
    
    # Display explanation
    if st.session_state.explanation:
        st.divider()
        st.markdown("### 🗣️ Explanation")
        st.markdown(f"""
        <div class='explanation-box'>
            {st.session_state.explanation}
        </div>
        """, unsafe_allow_html=True)
        
        # Rating section
        if st.session_state.show_rating:
            render_rating_form(selected_persona, user_level)


def render_rating_form(selected_persona, user_level):
    """Render rating form for explanations"""
    st.divider()
    st.subheader("⭐ Rate This Explanation (+5 XP)")
    
    with st.form("rating_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            clarity = st.slider("🔍 Clarity", 1, 5, 3)
        with col2:
            accuracy = st.slider("✅ Accuracy", 1, 5, 3)
        with col3:
            helpfulness = st.slider("💡 Helpfulness", 1, 5, 3)
        
        feedback = st.text_area("Additional comments (optional):", height=80)
        
        submit_rating = st.form_submit_button("📊 Submit Rating", type="primary", use_container_width=True)
        
        if submit_rating:
            rating_data = {
                'timestamp': datetime.now().isoformat(),
                'persona': selected_persona,
                'question': st.session_state.current_question[:200],
                'user_level': user_level,
                'clarity': clarity,
                'accuracy': accuracy,
                'helpfulness': helpfulness,
                'feedback': feedback
            }
            
            if save_rating(rating_data):
                st.success("✅ Rating submitted! +5 XP!")
                
                # Award XP
                add_xp(st.session_state.user_progress, 5, st.session_state)
                
                # Bonus affinity for high ratings
                avg_rating = (clarity + accuracy + helpfulness) / 3
                if avg_rating >= 4:
                    add_affinity(st.session_state.user_progress, selected_persona, 5, st.session_state)
                    st.success(f"🌟 High rating! +5 affinity with {selected_persona}")
                
                st.session_state.show_rating = False
                st.rerun()
            else:
                st.error("❌ Failed to save rating.")