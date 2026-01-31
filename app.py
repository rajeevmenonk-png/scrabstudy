import streamlit as st
import random
import re
import os
from collections import defaultdict
import streamlit.components.v1 as components

# --- 1. INITIALIZATION ---
if 'state' not in st.session_state:
    st.session_state.state = {
        'streak': 0, 'display_alpha': None, 'answered': False, 
        'current_solutions': [], 'is_phony': False, 'last_guess': None, 
        'last_scored_id': None, 'needs_new_rack': True,
        'filtered_alphas': [], 'current_rack_id': 0
    }

st.set_page_config(page_title="Scrabble Anagram Pro", layout="wide")

# --- 2. KEYBOARD LISTENER ---
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
                b.innerText.includes('Reveal') || b.innerText.includes('Next Rack')
            );
            if (action) action.click();
        }
    });
    </script>
    """,
    height=0,
)

st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
        
        /* ALPHAGRAM */
        .rack-text {
            text-align: center; 
            letter-spacing: 12px; 
            color: #f1c40f; 
            font-size: clamp(2.5rem, 8vw, 4.5rem); 
            font-weight: 900;
            white-space: nowrap; 
            overflow: visible; 
            margin-bottom: 20px;
        }

        /* --- MOBILE GRID OVERRIDE --- */
        
        /* 1. Target Horizontal Blocks that are INSIDE a column */
        /* This distinguishes the 3x3 grid from the Main Page Layout */
        [data-testid="column"] [data-testid="stHorizontalBlock"] {
            flex-direction: row !important; /* Force Horizontal */
            flex-wrap: nowrap !important;
        }

        /* 2. Target the columns inside that block */
        [data-testid="column"] [data-testid="stHorizontalBlock"] [data-testid="column"] {
            width: 33% !important;
            flex: 1 1 33% !important;
            min-width: 33% !important;
        }

        /* NUMBER BUTTONS: Chunky & Square */
        div.stButton > button {
            aspect-ratio: 1 / 1 !important;
            width: 100% !important;
            font-size: clamp(1.5rem, 5vw, 2.2rem) !important;
            font-weight: 900 !important;
            background-color: #262730 !important;
            border: 2px solid #555 !important;
            padding: 0 !important;
        }

        /* ACTION BUTTON: Standard Rectangular */
        .action-wrap {
            display: flex;
            justify-content: center;
            margin-top: 20px;
            margin-bottom: 20px;
        }
        
        .action-wrap button {
            width: 200px !important;
            height: 55px !important;
            font-size: 1.1rem !important;
            font-weight: 700 !important;
            aspect-ratio: auto !important; /* Not square */
            border-radius: 12px !important;
        }
        
        .reveal-btn button { background-color: #3498db !important; color: white !important; border: none !important; }
        .next-btn button { background-color: #27ae60 !important; color: white !important; border: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. DATA & LOGIC ---
@st.cache_data
def get_lexicon(filename):
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

alpha_map = get_lexicon("CSW24 2-15.txt")

# CALLBACKS
def cb_guess(val):
    st.session_state.state['last_guess'] = val
    st.session_state.state['answered'] = True

def cb_reveal():
    st.session_state.state['last_guess'] = -1 # -1 indicates "Revealed/Skipped"
    st.session_state.state['answered'] = True
    st.session_state.state['streak'] = 0

def cb_next():
    st.session_state.state['needs_new_rack'] = True

def find_anagrams(rack):
    results, seen = [], set()
    base = rack.replace('?', '')
    for char_code in range(65, 91):
        sub = "".join(sorted(base + chr(char_code)))
        for m in alpha_map.get(sub, []):
            if m['word'] not in seen: results.append(m); seen.add(m['word'])
    return results

if alpha_map and st.session_state.state['needs_new_rack']:
    if not st.session_state.state['filtered_alphas']:
        st.session_state.state['filtered_alphas'] = [a for a in alpha_map.keys() if len(a) == 7]
    
    st.session_state.state['is_phony'] = random.random() < 0.20
    rack = random.choice(st.session_state.state['filtered_alphas'])
    if random.random() < 0.20:
        arr = list(rack); arr[random.randint(0, len(arr)-1)] = '?'
        rack = "".join(sorted(arr))
    
    if st.session_state.state['is_phony']:
        for _ in range(20):
            v, c = 'AEIOU', 'BCDFGHJKLMNPQRSTVWXYZ'
            arr = list(rack); idx = random.randint(0, len(arr)-1)
            if arr[idx] == '?': continue
            arr[idx] = random.choice([x for x in v if x != arr[idx]]) if arr[idx] in v else random.choice([x for x in c if x != arr[idx]])
            test = "".join(sorted(arr))
            if not (find_anagrams(test) if '?' in test else alpha_map.get(test, [])):
                rack = test; break
                
    st.session_state.state.update({
        'display_alpha': rack,
        'current_solutions': find_anagrams(rack) if '?' in rack else alpha_map.get(rack, []),
        'answered': False, 'needs_new_rack': False, 'current_rack_id': random.randint(0, 9999)
    })

# --- 4. UI LAYOUT ---
st.sidebar.metric("Streak", st.session_state.state['streak'])

with st.sidebar.form("filter"):
    l = st.number_input("Word Length", 2, 15, 7)
    mode = st.radio("Focus", ["Probability", "Playability"], horizontal=True)
    mn, mx = st.columns(2)
    v_min, v_max = mn.number_input("Min", 0, 200000, 0), mx.number_input("Max", 0, 200000, 40000)
    if st.form_submit_button("Apply"):
        param = 'prob' if mode == "Probability" else 'play'
        st.session_state.state['filtered_alphas'] = [a for a, words in alpha_map.items() 
            if len(a) == l and any(v_min <= w[param] <= v_max for w in words)]
        st.session_state.state['needs_new_rack'] = True
        st.rerun()

col_l, col_r = st.columns([1, 1], gap="large")

with col_l:
    st.markdown(f"<div class='rack-text'>{st.session_state.state['display_alpha']}</div>", unsafe_allow_html=True)
    
    # --- 3x3 GRID (0-7, 8+) ---
    # Row 1
    c1, c2, c3 = st.columns(3)
    c1.button("0", key=f"b0_{st.session_state.state['current_rack_id']}", on_click=cb_guess, args=(0,))
    c2.button("1", key=f"b1_{st.session_state.state['current_rack_id']}", on_click=cb_guess, args=(1,))
    c3.button("2", key=f"b2_{st.session_state.state['current_rack_id']}", on_click=cb_guess, args=(2,))
    
    # Row 2
    c4, c5, c6 = st.columns(3)
    c4.button("3", key=f"b3_{st.session_state.state['current_rack_id']}", on_click=cb_guess, args=(3,))
    c5.button("4", key=f"b4_{st.session_state.state['current_rack_id']}", on_click=cb_guess, args=(4,))
    c6.button("5", key=f"b5_{st.session_state.state['current_rack_id']}", on_click=cb_guess, args=(5,))

    # Row 3
    c7, c8, c9 = st.columns(3)
    c7.button("6", key=f"b6_{st.session_state.state['current_rack_id']}", on_click=cb_guess, args=(6,))
    c8.button("7", key=f"b7_{st.session_state.state['current_rack_id']}", on_click=cb_guess, args=(7,))
    c9.button("8+", key=f"b8_{st.session_state.state['current_rack_id']}", on_click=cb_guess, args=(8,))

    # --- ACTION BUTTON ---
    st.markdown('<div class="action-wrap">', unsafe_allow_html=True)
    if not st.session_state.state['answered']:
        # State: Thinking
        st.markdown('<div class="reveal-btn">', unsafe_allow_html=True)
        st.button("Reveal Answer (Enter)", on_click=cb_reveal)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # State: Reviewing
        st.markdown('<div class="next-btn">', unsafe_allow_html=True)
        st.button("Next Rack (Enter)", on_click=cb_next)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_r:
    s = st.session_state.state
    if s['answered']:
        real = len(s['current_solutions'])
        
        # Determine success/fail
        if s['last_guess'] == -1: 
            st.info(f"Revealed: {real} word(s)")
        elif (s['last_guess'] == real) or (s['last_guess'] == 8 and real >= 8):
            st.success(f"CORRECT! ({real})")
            if s['last_scored_id'] != s['display_alpha']:
                st.session_state.state['streak'] += 1
                st.session_state.state['last_scored_id'] = s['display_alpha']
                st.rerun()
        else:
            guess_str = str(s['last_guess']) if s['last_guess'] < 8 else "8+"
            st.error(f"WRONG. Actual: {real} | You: {guess_str}")
            st.session_state.state['streak'] = 0; st.rerun()

        # Show Words
        if s['current_solutions']:
            for sol in sorted(s['current_solutions'], key=lambda x: x['word']):
                with st.expander(f"📖 {sol['word']}", expanded=True):
                    st.write(f"*{sol['def']}*")
                    st.write(f"**Hooks:** `[{sol['f']}]` {sol['word']} `[{sol['b']}]`")
                    st.caption(f"Prob: {sol['prob']} | Play: {sol['play']}")
        else:
            st.info("Rack was a PHONY.")