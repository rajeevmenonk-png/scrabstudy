import streamlit as st
import random
import re
import os
from collections import defaultdict
import streamlit.components.v1 as components

# --- 1. INITIALIZATION ---
# Using a dictionary to manage state to prevent fragmented reruns
if 'state' not in st.session_state:
    st.session_state.state = {
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

st.set_page_config(page_title="Scrabble Anagram Pro", layout="wide")

# --- 2. KEYBOARD LISTENER ---
components.html(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.key >= '0' && e.key <= '9') {
            const btns = Array.from(doc.querySelectorAll('button'));
            const label = e.key === '9' ? '8+' : e.key;
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
        .rack-text {
            text-align: center; letter-spacing: 12px; color: #f1c40f; 
            font-size: clamp(2rem, 8vw, 4rem); font-weight: 900;
            white-space: nowrap; overflow: hidden; margin-bottom: 20px;
        }

        /* --- THE GRID FIX --- */
        /* Targets the div holding our 0-8 buttons specifically */
        .tile-grid {
            display: grid !important;
            grid-template-columns: repeat(3, 1fr) !important;
            gap: 10px !important;
            width: 100% !important;
            max-width: 300px !important;
            margin: 0 auto !important;
        }

        .tile-grid button {
            aspect-ratio: 1 / 1 !important;
            width: 100% !important;
            font-size: 2rem !important;
            font-weight: 900 !important;
            background-color: #262730 !important;
            border: 2px solid #555 !important;
        }

        /* ACTION BUTTON (Reveal/Next) */
        .action-wrap { width: 220px; margin: 20px auto; }
        .action-wrap button {
            height: 50px !important; width: 220px !important;
            font-size: 1.1rem !important; font-weight: 700 !important;
            border-radius: 8px !important;
        }
        .reveal-btn button { background-color: #3498db !important; color: white !important; }
        .next-btn button { background-color: #27ae60 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. DATA LOAD ---
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

# --- 4. CALLBACKS (Fixes the hanging/dimming) ---
def handle_guess(val):
    st.session_state.state['last_guess'] = val
    st.session_state.state['answered'] = True

def handle_reveal():
    st.session_state.state['last_guess'] = -1
    st.session_state.state['answered'] = True
    st.session_state.state['streak'] = 0

def handle_next():
    st.session_state.state['needs_new_rack'] = True

# --- 5. LOGIC ---
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
    if random.random() < 0.20: # Blank
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

# --- 6. UI ---
st.sidebar.metric("Streak", st.session_state.state['streak'])

# Sidebar Filter
with st.sidebar.form("filter"):
    l = st.number_input("Len", 2, 15, 7)
    mode = st.radio("Focus", ["Prob", "Play"], horizontal=True)
    mn, mx = st.columns(2)
    v_min, v_max = mn.number_input("Min", 0, 200000, 0), mx.number_input("Max", 0, 200000, 40000)
    if st.form_submit_button("Apply"):
        param = 'prob' if mode == "Prob" else 'play'
        st.session_state.state['filtered_alphas'] = [a for a, words in alpha_map.items() 
            if len(a) == l and any(v_min <= w[param] <= v_max for w in words)]
        st.session_state.state['needs_new_rack'] = True
        st.rerun()

col_l, col_r = st.columns([1, 1], gap="large")

with col_l:
    st.markdown(f"<div class='rack-text'>{st.session_state.state['display_alpha']}</div>", unsafe_allow_html=True)
    
    # FORCED GRID (Bypasses st.columns for mobile safety)
    st.markdown('<div class="tile-grid">', unsafe_allow_html=True)
    for i in range(10):
        label = str(i) if i <= 8 else "8+"
        st.button(label, key=f"bt_{i}_{st.session_state.state['current_rack_id']}", on_click=handle_guess, args=(i,))
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ACTION AREA
    st.markdown('<div class="action-wrap">', unsafe_allow_html=True)
    if not st.session_state.state['answered']:
        st.markdown('<div class="reveal-btn">', unsafe_allow_html=True)
        st.button("Reveal Answer", on_click=handle_reveal)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="next-btn">', unsafe_allow_html=True)
        st.button("Next Rack", on_click=handle_next)
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_r:
    s = st.session_state.state
    if s['answered']:
        real = len(s['current_solutions'])
        if s['last_guess'] == -1: st.info(f"Revealed: {real}")
        elif (s['last_guess'] == real) or (s['last_guess'] == 9 and real > 8):
            st.success(f"CORRECT! ({real})")
            if s['last_scored_id'] != s['display_alpha']:
                st.session_state.state['streak'] += 1
                st.session_state.state['last_scored_id'] = s['display_alpha']
                st.rerun()
        else:
            st.error(f"WRONG. Actual: {real}")
            st.session_state.state['streak'] = 0; st.rerun()

        for sol in sorted(s['current_solutions'], key=lambda x: x['word']):
            with st.expander(f"📖 {sol['word']}", expanded=True):
                st.write(f"*{sol['def']}*")
                st.write(f"**Hooks:** `[{sol['f']}]` {sol['word']} `[{sol['b']}]`")