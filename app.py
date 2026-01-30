import streamlit as st
import random
import re
from collections import defaultdict
import streamlit.components.v1 as components

# --- 1. INITIALIZATION ---
state_keys = {
    'streak': 0, 'display_alpha': None, 'answered': False, 
    'current_solutions': [], 'is_phony': False, 'last_guess': None, 
    'last_scored_id': None, 'needs_new_rack': True, 'show_defs': True
}
for key, val in state_keys.items():
    if key not in st.session_state:
        st.session_state[key] = val

st.set_page_config(page_title="Scrabble Anagram Pro", layout="wide")

# --- 2. KEYBOARD & UI STYLING ---
# Injects JavaScript to map keys 0-8 and 9 (for 8+) to Streamlit buttons
components.html(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.key >= '0' && e.key <= '9') {
            // Find buttons by text content
            const btns = Array.from(doc.querySelectorAll('button'));
            const targetLabel = e.key === '9' ? '8+' : e.key;
            const targetBtn = btns.find(b => b.innerText === targetLabel);
            if (targetBtn) targetBtn.click();
        } else if (e.key === 'Enter') {
            const nextBtn = Array.from(doc.querySelectorAll('button')).find(b => b.innerText.includes('Next Rack'));
            if (nextBtn) nextBtn.click();
        }
    });
    </script>
    """,
    height=0,
)

st.markdown("""
    <style>
        [data-testid="stSidebar"] { min-width: 220px; max-width: 280px; }
        .stMetric { background-color: #1e2130; padding: 10px; border-radius: 10px; }
        /* Professional Scrabble-themed buttons */
        div.stButton > button {
            width: 100%; border-radius: 8px; height: 3.5em; 
            font-weight: bold; font-size: 1.1rem;
            border: 1px solid #4a4a4a; transition: 0.3s;
        }
        div.stButton > button:hover { border-color: #f1c40f; color: #f1c40f; }
        /* Highlight the Next Rack button */
        div[data-testid="stVerticalBlock"] > div:nth-child(2) button {
            background-color: #27ae60 !important; color: white !important; border: none !important;
        }
    </style>
""", unsafe_allow_html=True)

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
st.sidebar.metric("Current Streak", st.session_state.streak)
uploaded_file = st.sidebar.file_uploader("Upload Lexicon", type="txt", label_visibility="collapsed")

if uploaded_file:
    if 'master_data' not in st.session_state:
        st.session_state.master_data, st.session_state.alpha_map = load_lexicon(uploaded_file.getvalue())
        st.session_state.valid_alphas = set(st.session_state.alpha_map.keys())

    st.sidebar.header("Quiz Filters")
    w_len = st.sidebar.number_input("Word Length", 2, 15, 7)
    
    col_p1, col_p2 = st.sidebar.columns(2)
    min_p = col_p1.number_input("Min Prob", value=0)
    max_p = col_p2.number_input("Max Prob", value=40000)
    
    col_pl1, col_pl2 = st.sidebar.columns(2)
    min_play = col_pl1.number_input("Min Play", value=0)
    max_play = col_pl2.number_input("Max Play", value=1000)
    
    st.session_state.show_defs = st.sidebar.checkbox("Show Definitions", value=True)

    filtered = [a for a, words in st.session_state.alpha_map.items() 
                if len(a) == w_len and any(min_p <= w['prob'] <= max_p and min_play <= w['play'] <= max_play for w in words)]

    # --- 5. LOGIC ---
    def find_all_blank_anagrams(rack_with_blank):
        results, seen = [], set()
        base = rack_with_blank.replace('?', '')
        for char_code in range(65, 91):
            sub_alpha = "".join(sorted(base + chr(char_code)))
            for m in st.session_state.alpha_map.get(sub_alpha, []):
                if m['word'] not in seen:
                    results.append(m); seen.add(m['word'])
        return results

    def trigger_new():
        if not filtered: return
        # 20% Phony Chance
        st.session_state.is_phony = random.random() < 0.20
        # 20% Blank Chance (only for lengths that support it, but user requested 20% overall)
        use_blank = random.random() < 0.20
        
        base = random.choice(filtered)
        rack = base
        if use_blank:
            arr = list(base); arr[random.randint(0, len(arr)-1)] = '?'
            rack = "".join(sorted(arr))

        if st.session_state.is_phony:
            while True:
                v, c = 'AEIOU', 'BCDFGHJKLMNPQRSTVWXYZ'
                arr = list(rack); idx = random.randint(0, len(arr)-1)
                if arr[idx] == '?': continue
                arr[idx] = random.choice([x for x in v if x != arr[idx]]) if arr[idx] in v else random.choice([x for x in c if x != arr[idx]])
                test_rack = "".join(sorted(arr))
                sols = find_all_blank_anagrams(test_rack) if '?' in test_rack else st.session_state.alpha_map.get(test_rack, [])
                if not sols:
                    st.session_state.display_alpha = test_rack
                    st.session_state.current_solutions = []
                    break
        else:
            st.session_state.display_alpha = rack
            st.session_state.current_solutions = find_all_blank_anagrams(rack) if '?' in rack else st.session_state.alpha_map.get(rack, [])
        
        st.session_state.answered = False
        st.session_state.needs_new_rack = False

    if st.session_state.needs_new_rack: trigger_new()

    # --- 6. MAIN LAYOUT ---
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown(f"<h1 style='text-align: center; letter-spacing: 12px; color: #f1c40f; font-size: 4rem; margin-bottom: 0;'>{st.session_state.display_alpha}</h1>", unsafe_allow_html=True)
        
        if not st.session_state.answered:
            st.write("### How many valid words?")
            btn_cols = st.columns(3)
            # Buttons 0-8 and 8+
            for i in range(10):
                label = str(i) if i <= 8 else "8+"
                if btn_cols[i % 3].button(label, key=f"btn_{i}"):
                    st.session_state.last_guess = i
                    st.session_state.answered = True
                    st.rerun()
        else:
            st.write("### Review Results")
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
            correct = (st.session_state.last_guess == real_count) or (st.session_state.last_guess == 9 and real_count > 8)
            
            if correct:
                st.success(f"CORRECT! Total: {real_count}")
                if st.session_state.last_scored_id != st.session_state.display_alpha:
                    st.session_state.streak += 1
                    st.session_state.last_scored_id = st.session_state.display_alpha
                    st.rerun()
            else:
                st.error(f"WRONG. Actual: {real_count} | Your Guess: {st.session_state.last_guess if st.session_state.last_guess <= 8 else '8+'}")
                if st.session_state.streak > 0:
                    st.session_state.streak = 0
                    st.rerun()

            for sol in sorted(st.session_state.current_solutions, key=lambda x: x['word']):
                with st.expander(f"📖 {sol['word']}", expanded=True):
                    if st.session_state.show_defs: st.write(f"*{sol['def']}*")
                    st.write(f"**Hooks:** `[{sol['f']}]` {sol['word']} `[{sol['b']}]`")
                    st.caption(f"Prob: {sol['prob']} | Play: {sol['play']}")