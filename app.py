import streamlit as st
import random
import re
import os
from collections import defaultdict
import streamlit.components.v1 as components

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Scrabble Anagram Pro", layout="wide")

# --- 2. SESSION STATE SETUP ---
default_values = {
    'streak': 0, 
    'display_alpha': None, 
    'answered': False, 
    'current_solutions': [], 
    'is_phony': False, 
    'last_guess': None, 
    'last_scored_id': None, 
    'needs_new_rack': True,
    'filtered_alphas': [],
    'current_rack_id': 0
}

for key, val in default_values.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- 3. CSS STYLING (The Mobile Fix) ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
        
        /* ALPHAGRAM TEXT */
        .rack-text {
            text-align: center; 
            letter-spacing: 5px; 
            color: #f1c40f; 
            font-size: clamp(2.5rem, 6vw, 4.5rem); 
            font-weight: 900;
            white-space: nowrap; 
            margin-bottom: 20px;
        }

        /* --- MOBILE GRID MAGIC --- */
        /* This targets columns that are nested INSIDE another column. */
        /* It forces them to be 33% wide, creating a 3x3 grid on phones. */
        [data-testid="column"] [data-testid="column"] {
            width: 33.33% !important;
            flex: 1 1 33.33% !important;
            min-width: 33.33% !important;
        }

        /* BUTTON STYLING */
        div.stButton > button {
            width: 100% !important;
            aspect-ratio: 1 / 1 !important;
            font-size: clamp(1.2rem, 4vw, 2rem) !important;
            font-weight: 900 !important;
            background-color: #262730 !important;
            border: 2px solid #555 !important;
            margin: 0px !important;
        }

        /* ACTION BUTTON (Rectangular) */
        .action-container div.stButton > button {
            width: 100% !important;
            height: 55px !important;
            aspect-ratio: auto !important;
            border-radius: 12px !important;
            font-size: 1.2rem !important;
        }
        
        /* Custom Colors for Action Button based on state */
        .reveal-btn button { background-color: #3498db !important; border: none !important; color: white !important; }
        .next-btn button { background-color: #27ae60 !important; border: none !important; color: white !important; }

    </style>
""", unsafe_allow_html=True)

# --- 4. DATA LOADING ---
@st.cache_data
def load_lexicon(filename):
    if not os.path.exists(filename): return None, None
    data, a_map = [], defaultdict(list)
    with open(filename, 'r', encoding='latin-1') as f:
        for line in f:
            p = line.split('\t')
            if len(p) < 6: continue
            word = re.sub(r'[^A-Z]', '', p[0].replace('·', '').upper())
            if not word: continue
            info = {'word': word, 'def': p[1], 'f': p[2], 'b': p[3], 
                    'prob': int(p[4]) if p[4].strip().isdigit() else 999999,
                    'play': int(p[5]) if p[5].strip().isdigit() else 0}
            a_map["".join(sorted(word))].append(info)
    return a_map

alpha_map = load_lexicon("CSW24 2-15.txt")

# --- 5. LOGIC & CALLBACKS ---
# Callbacks update state *before* the app reruns, preventing loops.

def cb_guess(guessed_number):
    st.session_state.last_guess = guessed_number
    st.session_state.answered = True

def cb_reveal():
    st.session_state.last_guess = -1 # Code for "Revealed"
    st.session_state.answered = True
    st.session_state.streak = 0

def cb_next_rack():
    st.session_state.needs_new_rack = True
    st.session_state.answered = False
    st.session_state.last_guess = None

def find_anagrams(rack):
    results, seen = [], set()
    base = rack.replace('?', '')
    for char_code in range(65, 91):
        sub = "".join(sorted(base + chr(char_code)))
        for m in alpha_map.get(sub, []):
            if m['word'] not in seen: results.append(m); seen.add(m['word'])
    return results

def trigger_new_rack():
    if not st.session_state.filtered_alphas:
        # Fallback if no filters
        st.session_state.filtered_alphas = [a for a in alpha_map.keys() if len(a) == 7]

    # Generate Logic
    st.session_state.is_phony = random.random() < 0.20
    rack = random.choice(st.session_state.filtered_alphas)
    
    # Blank Handling
    if random.random() < 0.20:
        arr = list(rack)
        arr[random.randint(0, len(arr)-1)] = '?'
        rack = "".join(sorted(arr))
    
    # Phony Handling
    if st.session_state.is_phony:
        for _ in range(20): # Try 20 times to make a valid phony
            v, c = 'AEIOU', 'BCDFGHJKLMNPQRSTVWXYZ'
            arr = list(rack); idx = random.randint(0, len(arr)-1)
            if arr[idx] == '?': continue
            arr[idx] = random.choice([x for x in v if x != arr[idx]]) if arr[idx] in v else random.choice([x for x in c if x != arr[idx]])
            test = "".join(sorted(arr))
            # Check if it actually HAS no solutions
            sols = find_anagrams(test) if '?' in test else alpha_map.get(test, [])
            if not sols:
                rack = test
                break
    
    # Update State
    st.session_state.display_alpha = rack
    st.session_state.current_solutions = find_anagrams(rack) if '?' in rack else alpha_map.get(rack, [])
    st.session_state.current_rack_id = random.randint(1000, 9999) # New ID resets button state
    st.session_state.needs_new_rack = False

# --- 6. KEYBOARD LISTENER ---
components.html(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.key >= '0' && e.key <= '8') {
            const btns = Array.from(doc.querySelectorAll('button'));
            const label = e.key === '8' ? '8+' : e.key;
            const target = btns.find(b => b.innerText === label);
            if (target) target.click();
        } else if (e.key === 'Enter') {
            // Clicks the Action Button (Reveal or Next)
            const action = Array.from(doc.querySelectorAll('button')).find(b => 
                b.innerText.includes('Reveal') || b.innerText.includes('Next')
            );
            if (action) action.click();
        }
    });
    </script>
    """,
    height=0,
)

# --- 7. MAIN APP FLOW ---

# Load initial rack if needed
if alpha_map and st.session_state.needs_new_rack:
    trigger_new_rack()

# Sidebar
st.sidebar.metric("Streak", st.session_state.streak)
with st.sidebar.form("settings"):
    length = st.number_input("Word Length", 2, 15, 7)
    mode = st.radio("Focus", ["Probability", "Playability"], horizontal=True)
    mn, mx = st.columns(2)
    min_v = mn.number_input("Min", 0, 200000, 0)
    max_v = mx.number_input("Max", 0, 200000, 40000)
    
    if st.form_submit_button("Apply"):
        # Filter Logic
        param = 'prob' if mode == "Probability" else 'play'
        st.session_state.filtered_alphas = [a for a, words in alpha_map.items() 
                                          if len(a) == length and any(min_v <= w[param] <= max_v for w in words)]
        st.session_state.needs_new_rack = True
        st.rerun()

# Layout
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.markdown(f"<div class='rack-text'>{st.session_state.display_alpha}</div>", unsafe_allow_html=True)
    
    # 3x3 BUTTON GRID
    # We use nested columns here. The CSS above forces these to be 33% width.
    # Note: We pass args to callback to avoid lambdas (better performance)
    
    # Row 1
    c1, c2, c3 = st.columns(3)
    c1.button("0", key=f"b0_{st.session_state.current_rack_id}", on_click=cb_guess, args=(0,))
    c2.button("1", key=f"b1_{st.session_state.current_rack_id}", on_click=cb_guess, args=(1,))
    c3.button("2", key=f"b2_{st.session_state.current_rack_id}", on_click=cb_guess, args=(2,))
    
    # Row 2
    c4, c5, c6 = st.columns(3)
    c4.button("3", key=f"b3_{st.session_state.current_rack_id}", on_click=cb_guess, args=(3,))
    c5.button("4", key=f"b4_{st.session_state.current_rack_id}", on_click=cb_guess, args=(4,))
    c6.button("5", key=f"b5_{st.session_state.current_rack_id}", on_click=cb_guess, args=(5,))
    
    # Row 3
    c7, c8, c9 = st.columns(3)
    c7.button("6", key=f"b6_{st.session_state.current_rack_id}", on_click=cb_guess, args=(6,))
    c8.button("7", key=f"b7_{st.session_state.current_rack_id}", on_click=cb_guess, args=(7,))
    c9.button("8+", key=f"b8_{st.session_state.current_rack_id}", on_click=cb_guess, args=(8,))

    # SINGLE ACTION BUTTON
    st.write("") # Spacer
    if not st.session_state.answered:
        st.markdown('<div class="action-container reveal-btn">', unsafe_allow_html=True)
        st.button("Reveal Answer", on_click=cb_reveal)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="action-container next-btn">', unsafe_allow_html=True)
        st.button("Next Rack", on_click=cb_next_rack)
        st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    # RESULTS DISPLAY
    if st.session_state.answered:
        real_count = len(st.session_state.current_solutions)
        user_guess = st.session_state.last_guess
        
        # Check Correctness
        is_correct = False
        if user_guess == real_count: is_correct = True
        if user_guess == 8 and real_count >= 8: is_correct = True
        
        if user_guess == -1:
            st.info(f"Answer Revealed: {real_count} solutions.")
        elif is_correct:
            st.success(f"CORRECT! ({real_count})")
            # Update Streak only if we haven't scored this rack yet
            if st.session_state.last_scored_id != st.session_state.display_alpha:
                st.session_state.streak += 1
                st.session_state.last_scored_id = st.session_state.display_alpha
                # We do NOT rerun here, we let the user click "Next Rack"
        else:
            disp = str(user_guess) if user_guess < 8 else "8+"
            st.error(f"WRONG. Actual: {real_count} | You: {disp}")
            st.session_state.streak = 0

        # Show Solutions
        if st.session_state.current_solutions:
            for sol in sorted(st.session_state.current_solutions, key=lambda x: x['word']):
                with st.expander(f"📖 {sol['word']}", expanded=True):
                    st.write(f"**Hooks:** `[{sol['f']}]` {sol['word']} `[{sol['b']}]`")
                    st.caption(f"Prob: {sol['prob']} | Play: {sol['play']}")
                    if st.sidebar.checkbox("Definitions", True, key="defs"):
                         st.write(f"*{sol['def']}*")
        else:
            st.info("Rack was a PHONY (0 valid words).")