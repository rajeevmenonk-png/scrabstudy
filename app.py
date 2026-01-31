import streamlit as st
import random
import re
import os
from collections import defaultdict
import streamlit.components.v1 as components

# --- 1. INITIALIZATION ---
state_keys = {
    'streak': 0, 'display_alpha': None, 'answered': False, 
    'current_solutions': [], 'is_phony': False, 'last_guess': None, 
    'last_scored_id': None, 'needs_new_rack': True, 'show_defs': True,
    'filtered_alphas': [], 'lexicon_loaded': False, 'current_rack_id': 0
}
for key, val in state_keys.items():
    if key not in st.session_state:
        st.session_state[key] = val

st.set_page_config(page_title="Scrabble Anagram Pro", layout="wide")

# --- 2. KEYBOARD & MOBILE LAYOUT FIXES ---
components.html(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.key >= '0' && e.key <= '8') {
            const btns = Array.from(doc.querySelectorAll('button'));
            const targetLabel = e.key === '8' ? '8+' : e.key;
            const targetBtn = btns.find(b => b.innerText === targetLabel);
            if (targetBtn) targetBtn.click();
        } else if (e.key === 'Enter') {
            const actionBtn = Array.from(doc.querySelectorAll('button')).find(b => 
                b.innerText.includes('Reveal') || b.innerText.includes('Next Rack')
            );
            if (actionBtn) actionBtn.click();
        }
    });
    </script>
    """,
    height=0,
)

st.markdown("""
    <style>
        .block-container { padding-top: 1rem; max-width: 1200px; margin: 0 auto; }
        
        .rack-text {
            text-align: center; 
            letter-spacing: 12px; 
            color: #f1c40f; 
            font-size: clamp(2.5rem, 8vw, 4.2rem); 
            font-weight: 900;
            white-space: nowrap !important;
            margin-bottom: 20px;
        }

        /* --- FORCE 3-COLUMN GRID ON MOBILE --- */
        /* This overrides Streamlit's default "stack on mobile" behavior */
        [data-testid="column"] {
            width: 33.33% !important;
            flex: 1 1 33.33% !important;
            min-width: 33.33% !important;
        }
        
        /* Container for the 3x3 grid */
        .grid-container {
            max-width: 320px;
            margin: 0 auto;
        }

        /* Number Buttons (Chunky Squares) */
        div.stButton > button {
            aspect-ratio: 1 / 1 !important;
            width: 100% !important;
            font-size: 2rem !important;
            font-weight: 900 !important;
            background-color: #262730 !important;
            border: 2px solid #555 !important;
            box-shadow: 0 4px 0 #111;
            padding: 0 !important;
        }

        /* ACTION BUTTON (Standard Rectangular) */
        .action-area { width: 220px; margin: 20px auto; }
        .action-area button {
            width: 220px !important;
            height: 55px !important;
            font-size: 1.1rem !important;
            font-weight: 700 !important;
            aspect-ratio: auto !important;
            border-radius: 8px !important;
        }
        
        .reveal-btn button { background-color: #3498db !important; color: white !important; }
        .next-btn button { background-color: #27ae60 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. AUTO-LOAD LEXICON ---
@st.cache_data
def load_lexicon(filename):
    if not os.path.exists(filename): return None, None
    data, a_map = [], defaultdict(list)
    with open(filename, 'r', encoding='latin-1') as f:
        for line in f:
            p = line.split('\t')
            if len(p) < 7: continue
            word = re.sub(r'[^A-Z]', '', p[0].replace('·', '').upper())
            if not word: continue
            info = {'word': word, 'def': p[1].strip(), 'f': p[2].strip(), 'b': p[3].strip(),
                    'prob': int(p[4]) if p[4].strip().isdigit() else 999999,
                    'play': int(p[5]) if p[5].strip().isdigit() else 0}
            data.append(info); a_map["".join(sorted(word))].append(info)
    return data, a_map

if not st.session_state.lexicon_loaded:
    data, a_map = load_lexicon("CSW24 2-15.txt")
    if data:
        st.session_state.master_data, st.session_state.alpha_map = data, a_map
        st.session_state.lexicon_loaded = True

# --- 4. SIDEBAR ---
st.sidebar.metric("Streak", st.session_state.streak)

with st.sidebar.form("filter_form"):
    st.write("### Settings")
    w_len = st.number_input("Word Length", 2, 15, 7)
    mode = st.radio("Focus", ["Probability Rank", "Playability Rating"], horizontal=True)
    c1, c2 = st.columns(2)
    v_min, v_max = c1.number_input("Min", 0, 200000, 0), c2.number_input("Max", 0, 200000, 40000 if mode == "Probability Rank" else 1000)
    
    if st.form_submit_button("Apply & Reset"):
        param = 'prob' if mode == "Probability Rank" else 'play'
        st.session_state.filtered_alphas = [a for a, words in st.session_state.alpha_map.items() 
            if len(a) == w_len and any(v_min <= w[param] <= v_max for w in words)]
        st.session_state.needs_new_rack, st.session_state.answered = True, False
        st.rerun()

st.sidebar.checkbox("Show Definitions", True, key="defs_toggle")

# --- 5. GAME LOGIC ---
def find_anagrams(rack):
    results, seen = [], set()
    base = rack.replace('?', '')
    for char_code in range(65, 91):
        sub = "".join(sorted(base + chr(char_code)))
        for m in st.session_state.alpha_map.get(sub, []):
            if m['word'] not in seen: results.append(m); seen.add(m['word'])
    return results

def trigger_new():
    if not st.session_state.get('filtered_alphas'):
        st.session_state.filtered_alphas = [a for a, words in st.session_state.alpha_map.items() if len(a) == 7]
    
    st.session_state.is_phony = random.random() < 0.20
    use_blank = random.random() < 0.20
    base = random.choice(st.session_state.filtered_alphas)
    rack = base
    if use_blank:
        arr = list(base); arr[random.randint(0, len(arr)-1)] = '?'
        rack = "".join(sorted(arr))
    
    if st.session_state.is_phony:
        for _ in range(25):
            v, c = 'AEIOU', 'BCDFGHJKLMNPQRSTVWXYZ'
            arr = list(rack); idx = random.randint(0, len(arr)-1)
            if arr[idx] == '?': continue
            arr[idx] = random.choice([x for x in v if x != arr[idx]]) if arr[idx] in v else random.choice([x for x in c if x != arr[idx]])
            test_rack = "".join(sorted(arr))
            if not (find_anagrams(test_rack) if '?' in test_rack else st.session_state.alpha_map.get(test_rack, [])):
                rack = test_rack; break
            
    st.session_state.display_alpha = rack
    st.session_state.current_solutions = find_anagrams(rack) if '?' in rack else st.session_state.alpha_map.get(rack, [])
    st.session_state.answered, st.session_state.needs_new_rack, st.session_state.last_guess = False, False, None
    st.session_state.current_rack_id = random.randint(0, 9999)

if st.session_state.lexicon_loaded and st.session_state.needs_new_rack: trigger_new()

# --- 6. MAIN LAYOUT ---
if st.session_state.lexicon_loaded:
    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        st.markdown(f"<div class='rack-text'>{st.session_state.display_alpha}</div>", unsafe_allow_html=True)
        
        # --- 3x3 PERFECT GRID (0-8) ---
        # We use a container class to constrain width
        st.markdown('<div class="grid-container">', unsafe_allow_html=True)
        for row in range(3):
            cols = st.columns(3) # The CSS above forces these to STAY horizontal
            for col in range(3):
                i = row * 3 + col
                label = str(i) if i < 8 else "8+"
                # Unique key ensures buttons reset when rack changes
                if cols[col].button(label, key=f"btn_{i}_{st.session_state.current_rack_id}"):
                    st.session_state.last_guess = i
                    st.session_state.answered = True
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # --- ACTION BUTTON ---
        st.markdown('<div class="action-area">', unsafe_allow_html=True)
        if not st.session_state.answered:
            st.markdown('<div class="reveal-btn">', unsafe_allow_html=True)
            if st.button("Reveal Answer (Enter)", key="reveal_btn"):
                st.session_state.answered = True
                st.session_state.last_guess = -1 # Special code for "Given Up"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="next-btn">', unsafe_allow_html=True)
            if st.button("Next Rack (Enter)", key="next_btn"):
                st.session_state.needs_new_rack = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_r:
        if st.session_state.answered:
            real_count = len(st.session_state.current_solutions)
            
            # Logic for Correctness
            is_correct = False
            if st.session_state.last_guess == -1:
                st.info(f"Answer Revealed. There were {real_count} solutions.")
                st.session_state.streak = 0
            elif st.session_state.last_guess == real_count:
                is_correct = True
            elif st.session_state.last_guess == 8 and real_count >= 8: # Logic for 8+
                is_correct = True
            
            if is_correct:
                st.success(f"CORRECT! ({real_count})")
                if st.session_state.last_scored_id != st.session_state.display_alpha:
                    st.session_state.streak += 1
                    st.session_state.last_scored_id = st.session_state.display_alpha
                    st.rerun()
            elif st.session_state.last_guess != -1:
                disp_guess = str(st.session_state.last_guess) if st.session_state.last_guess < 8 else "8+"
                st.error(f"WRONG. Actual: {real_count} | You: {disp_guess}")
                st.session_state.streak = 0; st.rerun()

            for sol in sorted(st.session_state.current_solutions, key=lambda x: x['word']):
                with st.expander(f"📖 {sol['word']}", expanded=True):
                    if st.session_state.get('defs_toggle'): st.write(f"*{sol['def']}*")
                    st.write(f"**Hooks:** `[{sol['f']}]` {sol['word']} `[{sol['b']}]`")
                    st.caption(f"Prob: {sol['prob']} | Play: {sol['play']}")
            if not st.session_state.current_solutions: st.info("Rack was a PHONY.")