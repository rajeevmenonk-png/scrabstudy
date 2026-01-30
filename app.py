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
        .stButton > button { width: 100%; border-radius: 5px; height: 3.5em; font-weight: bold; }
        div[data-testid="stVerticalBlock"] > div:nth-child(2) button { background-color: #27ae60; color: white; }
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

# --- 4. SIDEBAR ---
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

    filtered = [a for a, words in st.session_state.alpha_map.items() 
                if len(a) == w_len and any(w['prob'] <= max_p and w['play'] >= min_play for w in words)]

    # --- 5. BLANK SEARCH LOGIC ---
    def find_all_blank_anagrams(rack_with_blank):
        """Finds all valid words by substituting the '?' with A-Z."""
        results = []
        seen_words = set()
        base_letters = rack_with_blank.replace('?', '')
        
        for char_code in range(65, 91): # A to Z
            substituted_alpha = "".join(sorted(base_letters + chr(char_code)))
            matches = st.session_state.alpha_map.get(substituted_alpha, [])
            for m in matches:
                if m['word'] not in seen_words:
                    results.append(m)
                    seen_words.add(m['word'])
        return results

    def trigger_new():
        if not filtered: return
        st.session_state.is_phony = random.choice([True, False])
        base = random.choice(filtered)
        
        # Determine Display Rack
        if w_len in [7, 8]:
            arr = list(base)
            arr[random.randint(0, len(arr)-1)] = '?'
            st.session_state.display_alpha = "".join(sorted(arr))
        else:
            st.session_state.display_alpha = base

        # Phony Logic: If phony, ensure NO words can be made (even with a blank)
        if st.session_state.is_phony:
            # We modify letters until the blank search returns zero
            while True:
                v, c = 'AEIOU', 'BCDFGHJKLMNPQRSTVWXYZ'
                arr = list(st.session_state.display_alpha); idx = random.randint(0, len(arr)-1)
                if arr[idx] == '?': continue
                arr[idx] = random.choice([x for x in v if x != arr[idx]]) if arr[idx] in v else random.choice([x for x in c if x != arr[idx]])
                test_alpha = "".join(sorted(arr))
                potential_solutions = find_all_blank_anagrams(test_alpha) if '?' in test_alpha else st.session_state.alpha_map.get(test_alpha, [])
                if not potential_solutions:
                    st.session_state.display_alpha = test_alpha
                    st.session_state.current_solutions = []
                    break
        else:
            # Valid Logic: Find EVERY solution possible with this rack
            if '?' in st.session_state.display_alpha:
                st.session_state.current_solutions = find_all_blank_anagrams(st.session_state.display_alpha)
            else:
                st.session_state.current_solutions = st.session_state.alpha_map.get(st.session_state.display_alpha, [])
        
        st.session_state.answered = False
        st.session_state.last_guess = None
        st.session_state.needs_new_rack = False

    if st.session_state.needs_new_rack: trigger_new()

    # --- 6. MAIN LAYOUT ---
    col1, col2 = st.columns([1, 1], gap="small")

    with col1:
        st.markdown(f"<h2 style='text-align: center; letter-spacing: 10px; color: #f1c40f; margin-bottom: 0;'>{st.session_state.display_alpha}</h2>", unsafe_allow_html=True)
        
        if not st.session_state.answered:
            st.write("### How many valid words?")
            btn_cols = st.columns(3) # Grouped for 0-8 range
            for i in range(10): # 0 to 9 (9 represents 8+)
                label = str(i) if i <= 8 else "8+"
                if btn_cols[i % 3].button(label, key=f"btn_{i}"):
                    st.session_state.last_guess = i
                    st.session_state.answered = True
                    st.rerun()
        else:
            if st.button("Next Rack (Enter)", use_container_width=True, type="primary", key="next_btn"):
                st.session_state.needs_new_rack = True
                st.rerun()
        
        if st.button("Skip / Reset Streak", use_container_width=True):
            st.session_state.streak = 0
            st.session_state.needs_new_rack = True
            st.rerun()

    with col2:
        if st.session_state.answered:
            real_count = len(st.session_state.current_solutions)
            is_correct = (st.session_state.last_guess == real_count) or (st.session_state.last_guess == 9 and real_count > 8)
            
            if is_correct:
                st.success(f"CORRECT! Total Solutions: {real_count}")
                if st.session_state.last_scored_id != st.session_state.display_alpha:
                    st.session_state.streak += 1
                    st.session_state.last_scored_id = st.session_state.display_alpha
                    st.rerun()
            else:
                display_guess = str(st.session_state.last_guess) if st.session_state.last_guess <= 8 else "8+"
                st.error(f"WRONG. Actual: {real_count} | You: {display_guess}")
                if st.session_state.streak > 0:
                    st.session_state.streak = 0
                    st.rerun()

            if st.session_state.current_solutions:
                # Sort alphabetically for better study review
                sorted_solutions = sorted(st.session_state.current_solutions, key=lambda x: x['word'])
                for sol in sorted_solutions:
                    with st.expander(f"📖 {sol['word']}", expanded=True):
                        if st.session_state.show_defs:
                            st.write(f"*{sol['def']}*")
                        st.write(f"**Hooks:** `[{sol['f']}]` {sol['word']} `[{sol['b']}]`")
                        st.caption(f"Prob: {sol['prob']} | Play: {sol['play']}")
            else:
                st.info("Rack was a PHONY.")