import streamlit as st
import random
import re
from collections import defaultdict

# 1. INITIALIZATION
for key in ['streak', 'display_alpha', 'answered', 'current_solutions', 'is_phony']:
    if key not in st.session_state:
        st.session_state[key] = 0 if key == 'streak' else (None if key == 'display_alpha' else (False if key in ['answered', 'is_phony'] else []))

st.set_page_config(page_title="Scrabble Anagram Pro", layout="wide")

def parse_scrabble_file(uploaded_file):
    data, alphagram_map = [], defaultdict(list)
    content = uploaded_file.read().decode("latin-1")
    for line in content.splitlines():
        parts = line.split('\t')
        if not parts: continue
        raw_word = parts[0].replace('·', '').upper()
        clean_word = re.sub(r'[^A-Z]', '', raw_word)
        if not clean_word: continue
        
        try:
            prob = int(parts[4].strip()) if len(parts) > 4 and parts[4].strip().isdigit() else 999999
            play = int(parts[5].strip()) if len(parts) > 5 and parts[5].strip().isdigit() else 0
        except: prob, play = 999999, 0
            
        alpha = "".join(sorted(clean_word))
        word_info = {'word': clean_word, 'def': parts[1].strip() if len(parts) > 1 else "", 
                     'f': parts[2].strip() if len(parts) > 2 else "", 
                     'b': parts[3].strip() if len(parts) > 3 else "", 
                     'prob': prob, 'play': play}
        data.append(word_info)
        alphagram_map[alpha].append(word_info)
    return data, alphagram_map

def generate_phony(real_alpha, valid_alphas):
    vowels, cons = 'AEIOU', 'BCDFGHJKLMNPQRSTVWXYZ'
    for _ in range(15):
        arr = list(real_alpha)
        idx = random.randint(0, len(arr) - 1)
        arr[idx] = random.choice([v for v in vowels if v != arr[idx]]) if arr[idx] in vowels else random.choice([c for c in cons if c != arr[idx]])
        new_alpha = "".join(sorted(arr))
        if new_alpha not in valid_alphas: return new_alpha
    return "".join(random.sample(cons, len(real_alpha)))

# --- UI SETUP ---
uploaded_file = st.sidebar.file_uploader("Upload Lexicon (.txt)", type="txt")

if uploaded_file:
    if 'master_data' not in st.session_state:
        st.session_state.master_data, st.session_state.alpha_map = parse_scrabble_file(uploaded_file)
        st.session_state.valid_alphas = set(st.session_state.alpha_map.keys())

    # Sidebar
    st.sidebar.header("Settings")
    w_len = st.sidebar.number_input("Length", 2, 15, 5)
    max_p = st.sidebar.number_input("Max Prob Rank", value=40000)
    min_play = st.sidebar.number_input("Min Playability", value=0)
    st.sidebar.divider()
    st.sidebar.metric("Current Streak", st.session_state.streak)

    # Filtering Pool
    filtered = [a for a, words in st.session_state.alpha_map.items() 
                if len(a) == w_len and any(w['prob'] <= max_p and w['play'] >= min_play for w in words)]

    # Layout: Left for Input, Right for Result/Solutions
    col_main, col_res = st.columns([1, 1], gap="large")

    with col_main:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("New Rack", use_container_width=True):
                st.session_state.is_phony = random.choice([True, False])
                base_alpha = random.choice(filtered)
                if st.session_state.is_phony:
                    st.session_state.display_alpha = generate_phony(base_alpha, st.session_state.valid_alphas)
                    st.session_state.current_solutions = []
                else:
                    st.session_state.current_solutions = st.session_state.alpha_map[base_alpha]
                    if w_len in [7, 8]:
                        arr = list(base_alpha); arr[random.randint(0, len(arr)-1)] = '?'
                        st.session_state.display_alpha = "".join(sorted(arr))
                    else: st.session_state.display_alpha = base_alpha
                st.session_state.answered = False
                st.rerun()
        
        with c2:
            if st.button("Skip Rack", use_container_width=True):
                st.session_state.streak = 0
                st.session_state.display_alpha = None
                st.rerun()

        if st.session_state.display_alpha:
            st.markdown(f"<h1 style='text-align: center; letter-spacing: 15px; color: #f1c40f; font-size: 60px;'>{st.session_state.display_alpha}</h1>", unsafe_allow_html=True)
            
            with st.form("guess_form", clear_on_submit=False):
                user_guess = st.number_input("How many valid words?", min_value=0, step=1)
                submit = st.form_submit_button("Submit (Enter)", use_container_width=True)
                if submit:
                    st.session_state.answered = True
                    st.session_state.last_guess = user_guess

    with col_res:
        if st.session_state.answered:
            real_count = len(st.session_state.current_solutions)
            if st.session_state.last_guess == real_count:
                st.success(f"CORRECT! There are {real_count} word(s).")
                if st.session_state.get('last_scored') != st.session_state.display_alpha:
                    st.session_state.streak += 1
                    st.session_state.last_scored = st.session_state.display_alpha
                    st.rerun()
            else:
                st.error(f"WRONG. The actual count was {real_count}.")
                st.session_state.streak = 0
                st.rerun()

            if not st.session_state.is_phony:
                for sol in st.session_state.current_solutions:
                    with st.expander(f"📖 {sol['word']}", expanded=True):
                        st.caption(f"Prob: {sol['prob']} | Play: {sol['play']}")
                        st.write(f"**Hooks:** `[{sol['f']}]` {sol['word']} `[{sol['b']}]`")
                        st.write(f"*{sol['def']}*")
            else:
                st.info("This rack was a PHONY.")