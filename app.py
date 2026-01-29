import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Scrabble Pro Trainer", layout="centered")

# --- DATA LOADING ---
@st.cache_data
def load_data(uploaded_file):
    cols = ['Word', 'Definition', 'Front_Hooks', 'Back_Hooks', 'Prob', 'Inner_Hooks']
    df = pd.read_csv(uploaded_file, sep='\t', names=cols, header=None, engine='python')
    # Clean the word column
    df['Word'] = df['Word'].str.replace('·', '').str.strip()
    return df

# --- PHONY GENERATION ---
def generate_phony(real_word, valid_set):
    vowels = 'AEIOU'
    arr = list(real_word)
    mode = random.choice(['vowel_swap', 'transpose', 'illegal_hook'])
    
    if mode == 'vowel_swap':
        indices = [i for i, c in enumerate(real_word) if c in vowels]
        if indices:
            idx = random.choice(indices)
            new_v = random.choice([v for v in vowels if v != real_word[idx]])
            arr[idx] = new_v
    elif mode == 'transpose':
        idx = random.randint(0, len(arr) - 2)
        arr[idx], arr[idx+1] = arr[idx+1], arr[idx]
    else:
        return real_word + random.choice(['S', 'E', 'Y'])
    
    phony = "".join(arr)
    return phony if phony not in valid_set else generate_phony(real_word, valid_set)

# --- APP UI ---
st.title("Scrabble Word Study Tool")

uploaded_file = st.file_file("Upload your CSW24 2-15.txt file", type="txt")

if uploaded_file:
    df = load_data(uploaded_file)
    valid_set = set(df['Word'].unique())

    # --- SIDEBAR SETTINGS ---
    st.sidebar.header("Quiz Settings")
    w_len = st.sidebar.number_input("Word Length", min_value=2, max_value=15, value=5)
    max_p = st.sidebar.number_input("Max Probability Rank", value=10000)
    contain_let = st.sidebar.text_input("Must Contain Letter").upper()
    min_v = st.sidebar.number_input("Min Vowels", value=0)

    # --- INITIALIZE SESSION STATE ---
    if 'current_word' not in st.session_state:
        st.session_state.current_word = None
        st.session_state.is_phony = False
        st.session_state.answered = False
        st.session_state.user_correct = None

    def get_new_word():
        pool = df[df['Word'].str.len() == w_len]
        pool = pool[pool['Prob'] <= max_p]
        if contain_let:
            pool = pool[pool['Word'].str.contains(contain_let)]
        if min_v > 0:
            pool = pool[pool['Word'].apply(lambda x: sum(1 for c in x if c in 'AEIOU') >= min_v)]
        
        if pool.empty:
            st.error("No words found matching these criteria.")
            return

        target = pool.sample(n=1).iloc[0]
        st.session_state.is_phony = random.choice([True, False])
        
        if st.session_state.is_phony:
            st.session_state.display_word = generate_phony(target['Word'], valid_set)
            st.session_state.current_data = None # No definition for phonies
        else:
            final_word = target['Word']
            # Only apply blanks for 7 and 8 letter words
            if w_len in [7, 8]:
                char_list = list(final_word)
                char_list[random.randint(0, len(char_list)-1)] = '?'
                st.session_state.display_word = "".join(char_list)
            else:
                st.session_state.display_word = final_word
            
            st.session_state.current_data = target

        st.session_state.answered = False
        st.session_state.user_correct = None

    if st.button("Generate Word"):
        get_new_word()

    # --- DISPLAY AREA ---
    if st.session_state.display_word:
        st.markdown(f"<h1 style='text-align: center; letter-spacing: 10px;'>{st.session_state.display_word}</h1>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        if not st.session_state.answered:
            with col1:
                if st.button("VALID", use_container_width=True):
                    st.session_state.user_correct = not st.session_state.is_phony
                    st.session_state.answered = True
                    st.rerun()
            with col2:
                if st.button("PHONY", use_container_width=True):
                    st.session_state.user_correct = st.session_state.is_phony
                    st.session_state.answered = True
                    st.rerun()

        # --- FEEDBACK AREA ---
        if st.session_state.answered:
            if st.session_state.user_correct:
                st.success("Correct!")
            else:
                st.error("Incorrect!")

            if st.session_state.is_phony:
                st.info(f"{st.session_state.display_word} is a PHONY.")
            else:
                data = st.session_state.current_data
                st.markdown(f"**Definition:** {data['Definition']}")
                # Updated hook display: [F]WORD[B]
                st.markdown(f"**Hooks:** `{data['Front_Hooks']}` **{data['Word']}** `{data['Back_Hooks']}`")
                st.markdown(f"**Prob Rank:** {data['Prob']}")