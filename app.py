import streamlit as st
import random
import re
from collections import defaultdict

st.set_page_config(page_title="Scrabble Alphagram Pro", layout="centered")

def parse_scrabble_file(uploaded_file):
    """
    Parses the file line-by-line. 
    Format: Word | Definition | Front | Back | Prob | Playability | Alphagram
    """
    data = []
    alphagram_map = defaultdict(list)
    
    # Read as Latin-1 to handle the middle dot '·' and other special characters
    content = uploaded_file.read().decode("latin-1")
    lines = content.splitlines()
    
    for line in lines:
        parts = line.split('\t')
        if not parts:
            continue
        
        # Column 0: The Word (Clean dots and hidden whitespace)
        raw_word = parts[0].replace('·', '').upper()
        clean_word = re.sub(r'[^A-Z]', '', raw_word)
        if not clean_word:
            continue
        
        # Core word data
        definition = parts[1].strip() if len(parts) > 1 else ""
        f_hooks = parts[2].strip() if len(parts) > 2 else ""
        b_hooks = parts[3].strip() if len(parts) > 3 else ""
        
        # Robust parsing for Prob (Col 4) and Playability (Col 5)
        try:
            prob = int(parts[4].strip()) if len(parts) > 4 and parts[4].strip().isdigit() else 999999
            playability = int(parts[5].strip()) if len(parts) > 5 and parts[5].strip().isdigit() else 0
        except:
            prob, playability = 999999, 0
            
        # Alphagram (Col 6) or fallback to auto-generating if missing
        alpha = parts[6].strip().upper() if len(parts) > 6 else "".join(sorted(clean_word))
        
        word_info = {
            'word': clean_word,
            'def': definition,
            'f': f_hooks,
            'b': b_hooks,
            'prob': prob,
            'play': playability,
            'alpha': alpha
        }
        
        data.append(word_info)
        alphagram_map[alpha].append(word_info)
        
    return data, alphagram_map

def generate_phony_alphagram(real_alpha, valid_alphas):
    """Generates a letter set with NO anagrams in the master list."""
    vowels = 'AEIOU'
    consonants = 'BCDFGHJKLMNPQRSTVWXYZ'
    arr = list(real_alpha)
    
    # Swap a random letter to create a non-word rack
    idx = random.randint(0, len(arr) - 1)
    if arr[idx] in vowels:
        arr[idx] = random.choice([v for v in vowels if v != arr[idx]])
    else:
        arr[idx] = random.choice([c for c in consonants if c != arr[idx]])
    
    new_alpha = "".join(sorted(arr))
    if new_alpha not in valid_alphas:
        return new_alpha
    return generate_phony_alphagram(real_alpha, valid_alphas)

st.title("Scrabble Alphagram Pro")

uploaded_file = st.file_uploader("Upload your CSW24 file", type="txt")

if uploaded_file:
    if 'master_data' not in st.session_state:
        with st.spinner("Processing Lexicon..."):
            data, alpha_map = parse_scrabble_file(uploaded_file)
            st.session_state.master_data = data
            st.session_state.alpha_map = alpha_map
            st.session_state.valid_alphas = set(alpha_map.keys())

    # --- Sidebar Filters ---
    st.sidebar.header("Quiz Settings")
    w_len = st.sidebar.number_input("Word Length", min_value=2, max_value=15, value=5)
    max_p = st.sidebar.number_input("Max Probability Rank", value=30000)
    
    # NEW: Playability Filter
    # Playability scores usually range from 0-1000 or similar depending on your list
    min_play = st.sidebar.number_input("Min Playability", value=0)
    
    # Filtering the pool based on ALL criteria
    filtered_alphas = [
        a for a, words in st.session_state.alpha_map.items() 
        if len(a) == w_len 
        and any(w['prob'] <= max_p and w['play'] >= min_play for w in words)
    ]
    
    st.sidebar.markdown("---")
    st.sidebar.write(f"Total words found for length {w_len}: **{len([d for d in st.session_state.master_data if len(d['word']) == w_len])}**")
    st.sidebar.write(f"Racks matching filters: **{len(filtered_alphas)}**")

    # --- Session State ---
    if 'display_alpha' not in st.session_state:
        st.session_state.display_alpha = None
        st.session_state.is_phony = False
        st.session_state.answered = False
        st.session_state.current_solutions = []

    if st.button("New Rack"):
        if not filtered_alphas:
            st.warning("No racks found matching those criteria.")
        else:
            st.session_state.is_phony = random.choice([True, False])
            base_alpha = random.choice(filtered_alphas)
            
            if st.session_state.is_phony:
                st.session_state.display_alpha = generate_phony_alphagram(base_alpha, st.session_state.valid_alphas)
                st.session_state.current_solutions = []
            else:
                # Store solutions for the reveal later
                st.session_state.current_solutions = st.session_state.alpha_map[base_alpha]
                
                # Apply blanks strictly for 7s and 8s
                if w_len in [7, 8]:
                    arr = list(base_alpha)
                    arr[random.randint(0, len(arr)-1)] = '?'
                    st.session_state.display_alpha = "".join(sorted(arr))
                else:
                    st.session_state.display_alpha = base_alpha
                    
            st.session_state.answered = False

    # --- Display Area ---
    if st.session_state.display_alpha:
        st.markdown(f"<h1 style='text-align: center; letter-spacing: 20px; font-size: 75px; color: #f1c40f;'>{st.session_state.display_alpha}</h1>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ VALID", use_container_width=True):
                st.session_state.user_choice, st.session_state.answered = True, True
        with c2:
            if st.button("❌ PHONY", use_container_width=True):
                st.session_state.user_choice, st.session_state.answered = False, True

        if st.session_state.answered:
            correct = st.session_state.user_choice == (not st.session_state.is_phony)
            if correct: st.success("Correct!")
            else: st.error("Incorrect!")

            if st.session_state.is_phony:
                st.info(f"'{st.session_state.display_alpha}' is a PHONY. No valid words can be formed.")
            else:
                st.markdown("---")
                st.subheader("Valid Word(s):")
                # Revealing all valid anagrams for that alphagram
                for sol in st.session_state.current_solutions:
                    with st.expander(f"📖 {sol['word']}"):
                        st.write(f"**Definition:** {sol['def']}")
                        f = f"[{sol['f']}]" if sol['f'] else "[ ]"
                        b = f"[{sol['b']}]" if sol['b'] else "[ ]"
                        st.markdown(f"**Hooks:** `{f}` **{sol['word']}** `{b}`")
                        st.write(f"**Prob Rank:** {sol['prob']} | **Playability:** {sol['play']}")