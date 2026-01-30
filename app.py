import streamlit as st
import random
import re
from collections import defaultdict

# --- 1. SETTINGS & MOBILE CSS ---
st.set_page_config(page_title="Scrabble Anagram Pro", layout="wide")

st.markdown("""
    <style>
        [data-testid="stSidebar"] { min-width: 180px; max-width: 220px; }
        .st-emotion-cache-16idsys p { font-size: 13px; }
        [data-testid="stMetricValue"] { font-size: 22px; }
        /* Grid styling for the number buttons */
        .stButton > button { width: 100%; border-radius: 5px; height: 3em; }
    </style>
""", unsafe_allow_html=True)

# --- 2. INITIALIZATION ---
state_keys = {
    'streak': 0, 'display_alpha': None, 'answered': False, 
    'current_solutions': [], 'is_phony': False, 'last_guess': None, 
    'last_scored_id': None, 'needs_new_rack': True, 'show_defs': True
}
for key, val in state_keys.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- 3. DATA PARSING ---
@st.cache_data
def load_lexicon(file_content):
    data, alphagram_map = [], defaultdict(list)
    lines = file_content.decode("latin-1").splitlines()
    for line in lines:
        parts = line.split('\t')
        if not parts: continue
        word = re.sub(r'[^A-Z]', '', parts[0].replace('·', '').upper())
        if not word: continue
        
        d = {'word': word, 'def': parts[1].strip() if len(parts) > 1 else "",
             'f': parts[2].strip() if len(parts) > 2 else "",
             'b': parts[3].strip() if len(parts) > 3 else "",
             'prob': int(parts[4]) if len(parts) > 4 and parts[4].strip().isdigit() else 999999,
             'play': int(parts[5]) if len(parts) > 5 and parts[5].strip().isdigit() else 0}
        
        alpha = "".join(sorted(word))
        data.append(d); alphagram_map[alpha].append(d)
    return data, alphagram_map

# --- 4. SIDEBAR (COMPACT) ---
st.sidebar.metric("Streak", st.session_state.streak)
uploaded_file = st.sidebar.file_uploader("Upload Lexicon", type="txt", label_visibility="collapsed")

if uploaded_file:
    if 'master_data' not in st.session_state:
        st.session_state.master_data, st.session_state.alpha_map = load_lexicon(uploaded_file.getvalue())
        st.session_state.valid_alphas = set(st.session_state.alpha_map.keys())

    st.sidebar.header("Quiz Settings")
    w_len = st.sidebar.number_input("Len", 2, 15, 5)
    max_p = st.sidebar.number_input("Max Prob", value=40000)
    min_play = st.sidebar.number_input("Min Play", value=0)
    st.session_state.show_defs = st.sidebar.checkbox("Show Definitions", value=True)

    # Filtering
    filtered = [a for a, words in st.session_state.alpha_map.items() 
                if len(a) == w_len and any(w['prob'] <= max_p and w['play'] >= min_play for w in words)]

    # --- 5. LOGIC ---
    def trigger_new():
        if not filtered: return
        st.session_state.is_phony = random.choice([True, False])
        base = random.choice(filtered)
        if st.session_state.is_phony:
            v, c = 'AEIOU', 'BCDFGHJKLMNPQRSTVWXYZ'
            arr = list(base); idx = random.randint(0, len(arr)-1)
            arr[idx] = random.choice([x for x in v if x != arr[idx]]) if arr[idx] in v else random.choice([x for x in c if x != arr[idx]])
            st.session_state.display_alpha = "".join(sorted(arr))
            if st.session_state.display_alpha in st.session_state.valid_alphas: st.session_state.is_phony = False
            st.session_state.current_solutions = st.session_state.alpha_map.get(st.session_state.display_alpha, [])
        else:
            st.session_state.current_solutions = st.session_state.alpha_map[base]
            if w_len in [7, 8]:
                arr = list(base); arr[random.randint(0, len(arr)-1)] = '?'
                st.session_state.display_alpha = "".join(sorted(arr))
            else: st.session_state.display_alpha = base
        st.session_state.answered = False
        st.session_state.last_guess = None
        st.session_state.needs_new_rack = False

    if st.session_state.needs_new_rack: trigger_new()

    # --- 6. MAIN LAYOUT ---
    col1, col2 = st.columns([1, 1], gap="small")

    with col1:
        st.markdown(f"<h2 style='text-align: center; letter-spacing: 10px; color: #f1c40f;'>{st.session_state.display_alpha}</h2>", unsafe_allow_html=True)
        
        if not st.session_state.answered:
            st.write("### How many valid words?")
            # Button Grid 0-11 (11 represents 10+)
            btn_cols = st.columns(4)
            for i in range(12):
                label = str(i) if i <= 10 else "10+"
                if btn_cols[i % 4].button(label, key=f"btn_{i}", use_container_width=True):
                    st.session_state.last_guess = i
                    st.session_state.answered = True
                    st.rerun()
        else:
            if st.button("Next Rack (Enter)", use_container_width=True, type="primary"):
                st.session_state.needs_new_rack = True
                st.rerun()
        
        if st.button("Skip / Reset Streak", use_container_width=True):
            st.session_state.streak = 0
            st.session_state.needs_new_rack = True
            st.rerun()

    with col2:
        if st.session_state.answered:
            real_count = len(st.session_state.current_solutions)
            # Logic for 10+ button
            is_correct = (st.session_state.last_guess == real_count) or (st.session_state.last_guess == 11 and real_count > 10)
            
            if is_correct:
                st.success(f"CORRECT! Total Solutions: {real_count}")
                if st.session_state.last_scored_id != st.session_state.display_alpha:
                    st.session_state.streak += 1
                    st.session_state.last_scored_id = st.session_state.display_alpha
                    st.rerun()
            else:
                display_guess = str(st.session_state.last_guess) if st.session_state.last_guess <= 10 else "10+"
                st.error(f"WRONG. Actual: {real_count} | Your Guess: {display_guess}")
                if st.session_state.streak > 0:
                    st.session_state.streak = 0
                    st.rerun()

            if st.session_state.current_solutions:
                for sol in st.session_state.current_solutions:
                    with st.expander(f"📖 {sol['word']}", expanded=True):
                        if st.session_state.show_defs:
                            st.write(f"*{sol['def']}*")
                        st.write(f"**Hooks:** `[{sol['f']}]` {sol['word']} `[{sol['b']}]`")
                        st.caption(f"Prob: {sol['prob']} | Play: {sol['play']}")
            else:
                st.info("Rack was a PHONY.")