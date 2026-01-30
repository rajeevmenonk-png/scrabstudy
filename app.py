import streamlit as st
import random
import re
from collections import defaultdict

# 1. INITIALIZATION - Always at the very top
state_defaults = {
    'streak': 0,
    'display_alpha': None,
    'answered': False,
    'current_solutions': [],
    'is_phony': False,
    'last_guess': 0,
    'last_scored_id': None,
    'needs_new_rack': True
}

for key, value in state_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

st.set_page_config(page_title="Scrabble Anagram Pro", layout="wide")

# --- DATA PARSING ---
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

# --- SIDEBAR (Streak at Top) ---
st.sidebar.metric("Current Streak", st.session_state.streak)
st.sidebar.divider()
uploaded_file = st.sidebar.file_uploader("Upload Lexicon (.txt)", type="txt")

if uploaded_file:
    if 'master_data' not in st.session_state:
        st.session_state.master_data, st.session_state.alpha_map = parse_scrabble_file(uploaded_file)
        st.session_state.valid_alphas = set(st.session_state.alpha_map.keys())

    # Settings
    st.sidebar.header("Quiz Settings")
    w_len = st.sidebar.number_input("Length", 2, 15, 5)
    max_p = st.sidebar.number_input("Max Prob Rank", value=40000)
    min_play = st.sidebar.number_input("Min Playability", value=0)

    filtered = [a for a, words in st.session_state.alpha_map.items() 
                if len(a) == w_len and any(w['prob'] <= max_p and w['play'] >= min_play for w in words)]

    col_main, col_res = st.columns([1, 1], gap="large")

    with col_main:
        def trigger_new_rack():
            if not filtered: return
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
            st.session_state.needs_new_rack = False

        if st.session_state.needs_new_rack:
            trigger_new_rack()
            st.rerun()

        # Rack Display
        if st.session_state.display_alpha:
            st.markdown(f"<h2 style='text-align: center; letter-spacing: 12px; color: #f1c40f; margin-top: 0px;'>{st.session_state.display_alpha}</h2>", unsafe_allow_html=True)
            
            # THE SINGLE FORM FOR DOUBLE ENTER
            with st.form("quiz_form", clear_on_submit=False):
                if not st.session_state.answered:
                    st.write("### How many valid words?")
                    # label is used but visually hidden to ensure state sync
                    guess = st.number_input("Count", min_value=0, step=1, label_visibility="collapsed")
                    submit_label = "Check Answer (Enter)"
                else:
                    st.write("### Reviewing Results...")
                    st.info("Press Enter again for the next rack")
                    submit_label = "Next Rack (Enter)"

                submit = st.form_submit_button(submit_label, use_container_width=True)
                
                if submit:
                    if not st.session_state.answered:
                        st.session_state.last_guess = guess
                        st.session_state.answered = True
                        st.rerun()
                    else:
                        st.session_state.needs_new_rack = True
                        st.rerun()

        if st.button("Skip / Reset Streak", use_container_width=True):
            st.session_state.streak = 0
            st.session_state.needs_new_rack = True
            st.rerun()

    with col_res:
        if st.session_state.answered:
            real_count = len(st.session_state.current_solutions)
            
            if st.session_state.last_guess == real_count:
                st.success(f"CORRECT! Total Solutions: {real_count}")
                if st.session_state.last_scored_id != st.session_state.display_alpha:
                    st.session_state.streak += 1
                    st.session_state.last_scored_id = st.session_state.display_alpha
                    st.rerun()
            else:
                st.error(f"WRONG. Actual: {real_count} | Your Guess: {st.session_state.last_guess}")
                if st.session_state.streak > 0:
                    st.session_state.streak = 0
                    st.rerun()

            if st.session_state.current_solutions:
                for sol in st.session_state.current_solutions:
                    with st.expander(f"📖 {sol['word']}", expanded=True):
                        st.caption(f"Prob: {sol['prob']} | Playability: {sol['play']}")
                        st.write(f"**Hooks:** `[{sol['f']}]` {sol['word']} `[{sol['b']}]` ")
            else:
                st.info("This rack was a PHONY.")