import streamlit as st
import random
import re

st.set_page_config(page_title="Scrabble Study Pro", layout="centered")

def parse_scrabble_file(uploaded_file):
    """Manually parses the file to ensure 100% accuracy regardless of tab messiness."""
    data = []
    # Read as Latin-1 to handle special dots/characters
    content = uploaded_file.getvalue().decode("latin-1")
    lines = content.splitlines()
    
    for line in lines:
        parts = line.split('\t')
        if len(parts) < 2: continue
        
        # 1. Clean the Word (Column 0)
        # Remove dots and anything not a letter
        raw_word = parts[0].replace('·', '').upper()
        clean_word = re.sub(r'[^A-Z]', '', raw_word)
        
        if not clean_word: continue
        
        # 2. Extract other columns if they exist
        definition = parts[1].strip() if len(parts) > 1 else ""
        f_hooks = parts[2].strip() if len(parts) > 2 else ""
        b_hooks = parts[3].strip() if len(parts) > 3 else ""
        
        # 3. Handle Probability (usually column 4 or 5)
        try:
            # Look for the first part that looks like a number in the later columns
            prob = 999999
            for p in parts[4:]:
                p_clean = p.strip()
                if p_clean.isdigit():
                    prob = int(p_clean)
                    break
        except:
            prob = 999999
            
        data.append({
            'word': clean_word,
            'def': definition,
            'f': f_hooks,
            'b': b_hooks,
            'prob': prob
        })
    return data

def generate_phony(real_word, valid_set):
    vowels = 'AEIOU'
    arr = list(real_word)
    mode = random.choice(['vowel_swap', 'transpose', 'hook_error'])
    if mode == 'vowel_swap':
        v_idx = [i for i, c in enumerate(real_word) if c in vowels]
        if v_idx:
            idx = random.choice(v_idx)
            arr[idx] = random.choice([v for v in vowels if v != real_word[idx]])
    elif mode == 'transpose':
        idx = random.randint(0, len(arr) - 2)
        arr[idx], arr[idx+1] = arr[idx+1], arr[idx]
    else:
        return real_word + random.choice(['S', 'E', 'Y'])
    
    phony = "".join(arr)
    return phony if phony not in valid_set else generate_phony(real_word, valid_set)

st.title("Scrabble Study Pro")

uploaded_file = st.file_uploader("Upload your CSW24 2-15.txt file", type="txt")

if uploaded_file:
    if 'master_data' not in st.session_state:
        st.session_state.master_data = parse_scrabble_file(uploaded_file)
        st.session_state.valid_set = {d['word'] for d in st.session_state.master_data}

    # --- Sidebar ---
    st.sidebar.header("Settings")
    w_len = st.sidebar.number_input("Word Length", min_value=2, max_value=15, value=5)
    max_p = st.sidebar.number_input("Max Probability Rank", value=50000)
    
    # Counter for verification
    current_pool_all = [d for d in st.session_state.master_data if len(d['word']) == w_len]
    st.sidebar.write(f"Words found for length {w_len}: {len(current_pool_all)}")

    if 'display_word' not in st.session_state:
        st.session_state.display_word = None
        st.session_state.is_phony = False
        st.session_state.answered = False

    if st.button("New Word"):
        pool = [d for d in current_pool_all if d['prob'] <= max_p]
        if not pool:
            st.warning("No words found. Try a higher Probability Rank.")
        else:
            target = random.choice(pool)
            st.session_state.is_phony = random.choice([True, False])
            
            if st.session_state.is_phony:
                st.session_state.display_word = generate_phony(target['word'], st.session_state.valid_set)
                st.session_state.current_data = None
            else:
                word_str = target['word']
                # Blanks strictly for 7s and 8s
                if w_len in [7, 8]:
                    arr = list(word_str)
                    arr[random.randint(0, len(arr)-1)] = '?'
                    st.session_state.display_word = "".join(arr)
                else:
                    st.session_state.display_word = word_str
                st.session_state.current_data = target
            st.session_state.answered = False

    if st.session_state.display_word:
        st.markdown(f"<h1 style='text-align: center; letter-spacing: 15px; font-size: 60px;'>{st.session_state.display_word}</h1>", unsafe_allow_html=True)
        
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
                st.info(f"'{st.session_state.display_word}' is a PHONY.")
            else:
                d = st.session_state.current_data
                st.markdown("---")
                st.write(f"**Definition:** {d['def']}")
                f = f"[{d['f']}]" if d['f'] else "[ ]"
                b = f"[{d['b']}]" if d['b'] else "[ ]"
                st.markdown(f"**Hooks:** `{f}` **{d['word']}** `{b}`")
                st.write(f"**Probability Rank:** {d['prob']}")