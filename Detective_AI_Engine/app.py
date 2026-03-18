import streamlit as st
import time
import random
from agents import DetectiveEngine, Background, MysteryLogic, Character
from typing import List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

# --- Page Config & Styling ---
st.set_page_config(page_title="琉璃案件夾 | AI 偵探引擎", page_icon="🕵️‍♂️", layout="wide")

def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()

# --- Session State Initialization ---
if "background" not in st.session_state:
    st.session_state.background = None
if "mystery" not in st.session_state:
    st.session_state.mystery = None
if "characters" not in st.session_state:
    st.session_state.characters = []
if "generating" not in st.session_state:
    st.session_state.generating = False
if "game_state" not in st.session_state:
    st.session_state.game_state = "START" 
if "dialogue_history" not in st.session_state:
    st.session_state.dialogue_history = {} 
if "current_options" not in st.session_state:
    st.session_state.current_options = {} # {char_name: [questions]}
if "interactions_left" not in st.session_state:
    st.session_state.interactions_left = 10
if "interacted_suspects" not in st.session_state:
    st.session_state.interacted_suspects = set()
if "chosen_killer" not in st.session_state:
    st.session_state.chosen_killer = None

# --- Game Logic Functions ---
def generate_new_game():
    st.session_state.generating = True
    engine = DetectiveEngine(model_name=selected_model)
    
    with st.status("🔍 正在招募偵探代理人...", expanded=True) as status:
        st.write("🌍 世界觀代理人正在構思場景...")
        theme_input = None if selected_theme == "隨機生成 ✨" else selected_theme
        bg = engine.generate_background(theme=theme_input)
        st.session_state.background = bg
        
        st.write("💀 邏輯代理人正在策劃罪案與編寫結局...")
        myst = engine.generate_mystery(bg, count=num_suspects)
        st.session_state.mystery = myst
        
        st.write("👥 角色代理人正在面試嫌疑人...")
        chars = engine.generate_characters(bg, myst, count=num_suspects)
        st.session_state.characters = chars
        
        # Reset Game State
        st.session_state.game_state = "INVESTIGATION"
        st.session_state.dialogue_history = {c.name: [] for c in chars}
        st.session_state.current_options = {c.name: c.initial_questions for c in chars}
        st.session_state.interactions_left = num_suspects + 5
        st.session_state.interacted_suspects = set()
        st.session_state.chosen_killer = None
        
        status.update(label="✅ 案卷已備妥！偵查開始。", state="complete", expanded=False)
    
    st.session_state.generating = False
    st.rerun()

def handle_dynamic_dialogue(char_name, question):
    if st.session_state.interactions_left > 0:
        engine = DetectiveEngine(model_name=selected_model)
        char = next(c for c in st.session_state.characters if c.name == char_name)
        
        with st.spinner(f"正在詢問 {char_name}..."):
            interaction = engine.get_dynamic_response(char, question, st.session_state.mystery)
            
            st.session_state.dialogue_history[char_name].append({
                "question": question,
                "answer": interaction['response']
            })
            # Update options to next questions based on AI response
            st.session_state.current_options[char_name] = interaction['next_questions']
            
            st.session_state.interactions_left -= 1
            st.session_state.interacted_suspects.add(char_name)
            
            if st.session_state.interactions_left <= 0:
                 st.session_state.game_state = "JUDGMENT"
            st.rerun()

# --- UI Components ---
st.markdown('<h1 class="main-title">THE GLASS CASE 琉璃案件夾</h1>', unsafe_allow_html=True)

with st.sidebar:
    st.title("⚙️ 引擎設定")
    api_key = st.text_input("Groq API 金鑰", value=os.getenv("GROQ_API_KEY", ""), type="password")
    if api_key:
        os.environ["GROQ_API_KEY"] = api_key
    selected_model = st.selectbox("LLM 模型", [
        "llama-3.3-70b-versatile"
    ])
    selected_theme = st.selectbox("謎題主題", ["隨機生成 ✨", "經典黑色電影", "科幻賽博龐克", "維多利亞時代倫敦", "現代懸疑"])
    num_suspects = st.slider("嫌疑人數", 3, 6, 4)
    if st.session_state.game_state == "INVESTIGATION":
        st.metric("🕵️剩餘訊問次數", st.session_state.interactions_left)

# 1. Start Screen
if st.session_state.game_state == "START":
    st.markdown("""<div style="text-align: center; margin: 4rem 0;"><h2>準備好解開謎題了嗎？</h2></div>""", unsafe_allow_html=True)
    if st.button("🧧 開始新案件", use_container_width=True):
        if not os.getenv("GROQ_API_KEY"): st.error("請輸入金鑰")
        else: generate_new_game()

# 2. Investigation Phase
elif st.session_state.game_state in ["INVESTIGATION", "JUDGMENT"]:
    bg, myst, chars = st.session_state.background, st.session_state.mystery, st.session_state.characters
    
    st.markdown(f"### 📍 案發現場：{bg.location_name}")
    with st.expander("📖 查閱案件完整卷宗", expanded=True):
        st.markdown(f"""<div class="case-card" style="border-left: 6px solid #c92a2a;"><div class="typewriter-text" style="white-space: pre-wrap;">{myst.full_story}</div></div>""", unsafe_allow_html=True)

    # Suspect Dialogue Section
    st.markdown("### 🗣️ 訊問室")
    tabs = st.tabs([c.name for c in chars])
    for i, char in enumerate(chars):
        with tabs[i]:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"""<div class="suspect-card"><h4>{char.name}</h4><p>{char.role}</p><hr style='margin:5px 0;'><p style='font-size:0.85rem; color:#c92a2a;'><b>疑點：</b>{char.suspicion_reason}</p></div>""", unsafe_allow_html=True)
                if st.session_state.game_state == "INVESTIGATION":
                    st.write("**請選擇訊問方向：**")
                    for q in st.session_state.current_options.get(char.name, []):
                        if st.button(f"🔍 {q}", key=f"q_{char.name}_{q}"):
                            handle_dynamic_dialogue(char.name, q)
                    
                    if len(st.session_state.interacted_suspects) >= len(chars):
                        if st.button("🏁 結束調查進行指控", key=f"end_{char.name}", type="primary"):
                            st.session_state.game_state = "JUDGMENT"
                            st.rerun()
            with col2:
                for entry in st.session_state.dialogue_history[char.name]:
                    st.chat_message("user").write(entry['question'])
                    st.chat_message("assistant").write(entry['answer'])

    if st.session_state.game_state == "JUDGMENT":
        st.divider()
        st.markdown("<h3 style='text-align: center; color: #ff4b4b;'>⚖️ 最終指控</h3>", unsafe_allow_html=True)
        choice = st.radio("誰才是真兇？", [c.name for c in chars], horizontal=True)
        if st.button("🔥 送交法官"):
            st.session_state.chosen_killer = choice
            st.session_state.game_state = "END"
            st.rerun()

# 3. End Screen
elif st.session_state.game_state == "END":
    myst, chars = st.session_state.mystery, st.session_state.characters
    truth = chars[myst.killer_index]
    
    if st.session_state.chosen_killer == truth.name:
        st.balloons()
        st.success(f"🏆 正義伸張！兇手正是 {truth.name}")
    else:
        st.error(f"❌ 冤獄！真正的兇手是 {truth.name}")
    
    st.markdown(f"""
    <div class="case-card" style="border-left: 10px solid #ff4b4b;">
        <h2>🔍 案件真相大解密</h2>
        <div style="white-space: pre-wrap; line-height: 1.8; font-size: 1.1rem;">
{myst.truth_reveal_story}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 挑戰下一案"):
        st.session_state.game_state = "START"
        st.rerun()
