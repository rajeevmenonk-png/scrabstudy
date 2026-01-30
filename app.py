import streamlit as st
import random
import re
from collections import defaultdict

st.set_page_config(page_title="Scrabble Anagram Pro", layout="centered")

def parse_scrabble_file(uploaded_file):
    """
    Standardizes the Lexicon. 
    Aggressive cleaning ensures word counts are 100% accurate.
    """
    data = []
    alphagram_map = defaultdict(list)
    content = uploaded_file.read().decode("latin-1")
    lines = content.splitlines()
    
    for line in lines:
        parts = line.split('\t')
        if not parts: continue
        
        # COLUMN 0: THE WORD
        # Cleaning dots, trailing spaces, and hidden carriage returns
        raw_word = parts[0].replace('·', '').upper()
        clean_word = re.sub(r'[^A-Z]', '', raw_word)
        if not clean_word: continue
        
        # Standard metadata columns
        definition = parts[1].strip() if len(parts) > 1 else ""
        f_hooks = parts[2].strip() if len(parts) > 2 else ""
        b_hooks = parts[3].strip() if len(parts) > 3 else ""
        
        try:
            # Col 4: Prob | Col 5: Playability
            prob = int(parts[4].strip()) if len(parts) > 4 and parts[4].strip().isdigit() else 999999
            play = int(parts[5].strip()) if len(parts) > 5 and parts[5].strip().isdigit() else 0
        except:
            prob, play = 999999, 0
            
        # The Alphagram (used as the primary key for lookup)
        alpha = "".join(sorted(clean_word))
        
        word_info = {
            'word': clean_word, 
            'def': definition, 
            'f': f_hooks, 
            'b': b_hooks, 
            'prob': prob, 
            'play': play
        }
        
        data.append(word_info)
        alphagram_map[alpha].append(word_info)
        
    return data, alphagram_map

def generate_phony(real_alpha, valid_alphas):
    """Creates a letter set that looks valid but has zero anagrams."""
    vowels, cons = 'AEIOU', 'BCDFGHJKLMNPQRSTVWXYZ'
    arr = list(real_alpha)
    idx = random.randint(0, len(arr) - 1)
    # Swap vowel for vowel or consonant for consonant to keep it 'plausible'
    if arr[idx] in vowels:
        arr[idx] = random.choice([v for v in vowels if v != arr[idx]])
    else:
        arr[idx] = random.choice([c for c in cons if c != arr[idx]])
    
    new_alpha = "".join(sorted(arr))
    return new_alpha if new_alpha not in valid_alphas else generate_phony(real_alpha, valid_alphas)

st.title("Scrabble Anagram Pro")

uploaded_file = st.file_uploader("Upload Lexicon (.txt)", type="txt")

if uploaded_file:
    # Initialize Persistent Data
    if 'master_data' not in st.session_state:
        with st.spinner("Processing Lexicon..."):
            data, alpha_map = parse_scrabble_file(uploaded_file)
            st.session_state.master_data = data
            st.session_state.alpha_map = alpha_map
            st.session_state.valid_alphas = set(alpha_map.keys())
            st.session_state.streak = 0

    # --- Sidebar Configuration ---
    st.sidebar.header("Quiz Settings")
    w_len = st.sidebar.number_input("Word Length", 2, 15, 5)
    max_p = st.sidebar.number_input("Max Prob Rank", value=40000)
    min_play = st.sidebar.number_input("Min Playability", value=0)
    
    st.sidebar.markdown("---")
    st.sidebar.metric("Current Streak", st.session_state.streak)
    
    # Filter the Pool
    filtered_alphas = [
        a for a, words in st.session_state.alpha_map.items() 
        if len(a) == w_len and any(w['prob'] <= max_p and w['play'] >= min_play for w in words)
    ]
    st.sidebar.write(f"Racks matching filters: **{len(filtered_alphas)}**")

    # --- Session State Management ---
    if 'display_alpha' not in st.session_state:
        st.session_state.display_alpha = None
        st.session_state.is_phony = False
        st.session_state.answered = False
        st.session_state.current_solutions = []

    if st.button("New Rack"):
        st.session_state.is_phony = random.choice([True, False])
        base_alpha = random.choice(filtered_alphas)
        
        if st.session_state.is_phony:
            st.session_state.display_alpha = generate_phony(base_alpha, st.session_state.valid_alphas)
            st.session_state.current_solutions = []
        else:
            st.session_state.current_solutions = st.session_state.alpha_map[base_alpha]
            # Blank simulation strictly for 7s and 8s
            if w_len in [7, 8]:
                arr = list(base_alpha)
                arr[random.randint(0, len(arr)-1)] = '?'
                st.session_state.display_alpha = "".join(sorted(arr))
            else:
                st.session_state.display_alpha = base_alpha
        st.session_state.answered = False

    # --- UI Layout ---
    if st.session_state.display_alpha:
        # Reduced font size and tighter spacing for better scannability
        st.markdown(f"<h2 style='text-align: center; letter-spacing: 12px; color: #f1c40f; margin-bottom: 0px;'>{st.session_state.display_alpha}</h2>", unsafe_allow_html=True)
        
        # Guess Input
        user_guess = st.number_input("How many valid words?", min_value=0, step=1, key="user_guess_input")
        
        if st.button("Submit Guess"):
            st.session_state.answered = True

        if st.session_state.answered:
            real_count = len(st.session_state.current_solutions)
            if user_guess == real_count:
                st.success(f"Correct! Total Solutions: {real_count}")
                # Increment streak only if this is a fresh answer
                if 'last_streak_update' not in st.session_state or st.session_state.last_streak_update != st.session_state.display_alpha:
                    st.session_state.streak += 1
                    st.session_state.last_streak_update = st.session_state.display_alpha
                    st.rerun()
            else:
                st.error(f"Incorrect. Total Solutions: {real_count}")
                st.session_state.streak = 0
                st.rerun()

            # Feedback Reveal (Only if valid words exist)
            if not st.session_state.is_phony:
                st.markdown("---")
                for sol in st.session_state.current_solutions:
                    with st.expander(f"{sol['word']}"):
                        st.write(f"**Definition:** {sol['def']}")
                        f_hook = f"[{sol['f']}]" if sol['f'] else "[ ]"
                        b_hook = f"[{sol['b']}]" if sol['b'] else "[ ]"
                        st.markdown(f"**Hooks:** `{f_hook}` **{sol['word']}** `{b_hook}`")
                        st.write(f"**P:** {sol['prob']} | **PL:** {sol['play']}")
            else:
                st.info("This rack was a PHONY (Zero solutions).")