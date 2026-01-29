import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Scrabble Study Pro", layout="centered")

@st.cache_data
def load_data(uploaded_file):
    # Parsing based on: Word | Definition | Front Hooks | Back Hooks | Prob | Extra
    cols = ['Word', 'Definition', 'Front_Hooks', 'Back_Hooks', 'Prob', 'Extra']
    df = pd.read_csv(uploaded_file, sep='\t', names=cols, header=None, engine='python')
    
    # Cleaning: strip dots and whitespace to ensure strict length counts
    df['Word'] = df['Word'].astype(str).str.replace('·', '').str.strip().str.upper()
    df['Front_Hooks'] = df['Front_Hooks'].fillna('').astype(str).str.strip()
    df['Back_Hooks'] = df['Back_Hooks'].fillna('').astype(str).str.strip()
    return df

def generate_phony(real_word, valid_set):
    vowels = 'AEIOU'
    arr = list(real_word)
    mode = random.choice(['vowel_swap', 'transpose', 'hook_error'])
    
    if mode == 'vowel_swap':
        v_indices = [i for i, c in enumerate(real_word) if c in vowels]
        if v_indices:
            idx = random.choice(v_indices)
            new_v = random.choice([v for v in vowels if v != real_word[idx]])
            arr[idx] = new_v
    elif mode == 'transpose':
        idx = random.randint(0, len(arr) - 2)
        arr[idx], arr[idx+1] = arr[idx+1], arr[idx]
    else: # Hook error
        return real_word + random.choice(['S', 'E', 'Y'])
    
    phony = "".join(arr)
    # Ensure the phony isn't a valid word by chance
    return phony if phony not in valid_set else generate_phony(real_word, valid_set)

st.title("Scrabble Study Pro")

# Corrected function call: st.file_uploader
uploaded_file = st.file_uploader("Upload your word list (.txt)", type="txt")

if uploaded_file:
    df = load_data(uploaded_file)
    valid_set = set(df['Word'].unique())

    # --- Quiz Settings ---
    st.sidebar.header("Settings")
    w_len = st.sidebar.number_input("Word Length", min_value=2, max_value=15, value=5)
    max_p = st.sidebar.number_input("Max Probability Rank", value=15000)

    if 'display_word' not in st.session_state:
        st.session_state.display_word = None
        st.session_state.is_phony = False
        st.session_state.answered = False
        st.session_state.current_data = None

    def get_new_word():
        # Strict length filtering to prevent 6s in a 5-letter quiz
        pool = df[(df['Word'].str.len() == w_len) & (df['Prob'] <= max_p)]
        
        if pool.empty:
            st.warning("No words found! Try a higher Probability Rank.")
            return

        target = pool.sample(n=1).iloc[0]
        st.session_state.is_phony = random.choice([True, False])
        
        if st.session_state.is_phony:
            st.session_state.display_word = generate_phony(target['Word'], valid_set)
            st.session_state.current_data = None
        else:
            word_str = target['Word']
            # Blanks strictly for 7s and 8s only
            if w_len in [7, 8]:
                char_list = list(word_str)
                char_list[random.randint(0, len(char_list)-1)] = '?'
                st.session_state.display_word = "".join(char_list)
            else:
                st.session_state.display_word = word_str
            st.session_state.current_data = target
            
        st.session_state.answered = False

    if st.button("New Word"):
        get_new_word()

    if st.session_state.display_word:
        st.markdown(f"<h1 style='text-align: center; letter-spacing: 15px;'>{st.session_state.display_word}</h1>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("VALID", use_container_width=True):
                st.session_state.user_choice = True
                st.session_state.answered = True
        with c2:
            if st.button("PHONY", use_container_width=True):
                st.session_state.user_choice = False
                st.session_state.answered = True

        if st.session_state.answered:
            real_valid = not st.session_state.is_phony
            if st.session_state.user_choice == real_valid:
                st.success("Correct!")
            else:
                st.error("Incorrect!")

            if st.session_state.is_phony:
                st.info(f"'{st.session_state.display_word}' is a PHONY.")
            else:
                d = st.session_state.current_data
                st.markdown("---")
                st.write(f"**Definition:** {d['Definition']}")
                # Clean hook display: [Front] ACTUAL_WORD [Back]
                f = f"[{d['Front_Hooks']}]" if d['Front_Hooks'] else "[ ]"
                b = f"[{d['Back_Hooks']}]" if d['Back_Hooks'] else "[ ]"
                st.markdown(f"**Hooks:** `{f}` **{d['Word']}** `{b}`")
                st.write(f"**Prob Rank:** {d['Prob']}")