import streamlit as st
import random
import re
import os
from collections import defaultdict
import streamlit.components.v1 as components

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Scrabble Anagram Pro", layout="wide")

# --- 2. SESSION STATE ---
default_values = {
    'streak': 0, 'display_alpha': None, 'answered': False, 
    'current_solutions': [], 'is_phony': False, 'last_guess': None, 
    'last_scored_id': None, 'needs_new_rack': True,
    'filtered_alphas': [], 'current_rack_id': 0
}
for key, val in default_values.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- 3. CSS (THE MOBILE FIX) ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
        
        .rack-text {
            text-align: center; letter-spacing: 5px; color: #f1c40f; 
            font-size: clamp(2.5rem, 6vw, 4.5rem); font-weight: 900;
            white-space: nowrap; margin-bottom: 20px;
        }

        /* --- NUCLEAR MOBILE GRID FIX --- */
        /* 1. Force the horizontal block to NEVER wrap */
        [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            flex-direction: row !important;
        }

        /* 2. Force the columns to shrink below their default minimum */
        [data-testid="column"] {
            min-width: 0px !important;
            flex: 1 1 0px !important;
            width: 33.33% !important;
            padding: 2px !important; /* Tighten gaps on mobile */
        }

        /* 3. Chunky Buttons */
        div.stButton > button {
            width: 100% !important;
            aspect-ratio: 1 / 1 !important;
            font-size: clamp(1.2rem, 5vw, 2.2rem) !important;
            font-weight: 900 !important;
            background-color: #262730 !important;
            border: 2px solid #555 !important;
            margin: 0px !important;
            padding: 0px !important;
        }
        
        /* Action Button Styling */
        .reveal-btn button { background-color: #3498db !important; color: white !important; height: 55px !important; aspect-ratio: auto !important; }
        .next-btn button { background-color: #27ae60 !important; color: white !important; height: 55px !important; aspect-ratio: auto !important; }

    </style>
""", unsafe_allow_html=True)

# --- 4. DATA ---
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

# --- 5. CALLBACKS ---
def cb_guess(val):
    st.session_state.last_guess = val
    st.session_state.answered = True

def cb_reveal():
    st.session_state.last_guess = -1
    st.session_state.answered = True
    st.session_state.streak = 0

def cb_next():
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
        st.session_state.filtered_alphas = [a for a in alpha_map.keys() if len(a) == 7]
    
    st.session_state.is_phony = random.random() < 0.20
    rack = random.choice(st.session_state.filtered_alphas)
    if random.random() < 0.20:
        arr = list(rack); arr[random.randint(0, len(arr)-1)] = '?'
        rack = "".join(sorted(arr))
    
    if st.session_state.is_phony:
        for _ in range(20):
            v, c = 'AEIOU', 'BCDFGHJKLMNPQRSTVWXYZ'
            arr = list(rack); idx = random.randint(0, len(arr)-1)
            if arr[idx] == '?': continue
            arr[idx] = random.choice([x for x in v if x != arr[idx]]) if arr[idx] in v else random.choice([x for x in c if x != arr[idx]])
            test = "".join(sorted(arr))
            if not (find_anagrams(test) if '?' in test else alpha_map.get(test, [])):
                rack = test; break

    st.session_state.display_alpha = rack
    st.session_state.current_solutions = find_anagrams(rack) if '?' in rack else alpha_map.get(rack, [])
    st.session_state.current_rack_id = random.randint(1000, 9999)
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

# --- 7. MAIN LAYOUT ---
if alpha_map and st.session_state.needs_new_rack:
    trigger_new_rack()

st.sidebar.metric("Streak", st.session_state.streak)
show_defs = st.sidebar.checkbox("Show Definitions", True) # Fixed: Outside loop

with st.sidebar.form("settings"):
    length = st.number_input("Len", 2, 15, 7)
    mode = st.radio("Focus", ["Prob", "Play"], horizontal=True)
    mn, mx = st.columns(2)
    v_min, v_max = mn.number_input("Min", 0, 200000, 0), mx.number_input("Max", 0, 200000, 40000)
    if st.form_submit_button("Apply"):
        param = 'prob' if mode == "Prob" else 'play'
        st.session_state.filtered_alphas = [a for a, words in alpha_map.items() 
            if len(a) == length and any(v_min <= w[param] <= v_max for w in words)]
        st.session_state.needs_new_rack = True
        st.rerun()

col_l, col_r = st.columns([1, 1], gap="large")

with col_l:
    st.markdown(f"<div class='rack-text'>{st.session_state.display_alpha}</div>", unsafe_allow_html=True)
    
    # GRID: 0-2
    c1, c2, c3 = st.columns(3)
    c1.button("0", key=f"b0_{st.session_state.current_rack_id}", on_click=cb_guess, args=(0,))
    c2.button("1", key=f"b1_{st.session_state.current_rack_id}", on_click=cb_guess, args=(1,))
    c3.button("2", key=f"b2_{st.session_state.current_rack_id}", on_click=cb_guess, args=(2,))
    
    # GRID: 3-5
    c4, c5, c6 = st.columns(3)
    c4.button("3", key=f"b3_{st.session_state.current_rack_id}", on_click=cb_guess, args=(3,))
    c5.button("4", key=f"b4_{st.session_state.current_rack_id}", on_click=cb_guess, args=(4,))
    c6.button("5", key=f"b5_{st.session_state.current_rack_id}", on_click=cb_guess, args=(5,))
    
    # GRID: 6-8+
    c7, c8, c9 = st.columns(3)
    c7.button("6", key=f"b6_{st.session_state.current_rack_id}", on_click=cb_guess, args=(6,))
    c8.button("7", key=f"b7_{st.session_state.current_rack_id}", on_click=cb_guess, args=(7,))
    c9.button("8+", key=f"b8_{st.session_state.current_rack_id}", on_click=cb_guess, args=(8,))

    st.write("")
    if not st.session_state.answered:
        st.markdown('<div class="reveal-btn">', unsafe_allow_html=True)
        st.button("Reveal Answer", on_click=cb_reveal)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="next-btn">', unsafe_allow_html=True)
        st.button("Next Rack", on_click=cb_next)
        st.markdown('</div>', unsafe_allow_html=True)

with col_r:
    if st.session_state.answered:
        real = len(st.session_state.current_solutions)
        ug = st.session_state.last_guess
        
        is_cor = (ug == real) or (ug == 8 and real >= 8)
        if ug == -1: st.info(f"Revealed: {real}")
        elif is_cor:
            st.success(f"CORRECT! ({real})")
            if st.session_state.last_scored_id != st.session_state.display_alpha:
                st.session_state.streak += 1
                st.session_state.last_scored_id = st.session_state.display_alpha
        else:
            st.error(f"WRONG. Actual: {real}")
            st.session_state.streak = 0
            
        if st.session_state.current_solutions:
            for s in sorted(st.session_state.current_solutions, key=lambda x: x['word']):
                with st.expander(f"📖 {s['word']}", expanded=True):
                    st.write(f"**Hooks:** `[{s['f']}]` {s['word']} `[{s['b']}]`")
                    st.caption(f"Prob: {s['prob']} | Play: {s['play']}")
                    if show_defs: st.write(f"*{s['def']}*")
        else:
            st.info("PHONY.")