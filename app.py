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

# --- 2. KEYBOARD & MOBILE WIDTH OVERRIDES ---
components.html(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.key >= '0' && e.key <= '9') {
            const btns = Array.from(doc.querySelectorAll('button'));
            const targetLabel = e.key === '9' ? '8+' : e.key;
            const targetBtn = btns.find(b => b.innerText === targetLabel);
            if (targetBtn) targetBtn.click();
        } else if (e.key === 'Enter') {
            // Enter hits the single Action Button regardless of its label
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
        .block-container { padding: 1rem; max-width: 100%; }
        
        .rack-text {
            text-align: center; 
            letter-spacing: 12px; 
            color: #f1c40f; 
            font-size: clamp(2rem, 10vw, 4.2rem); 
            font-weight: 900;
            white-space: nowrap;
            margin-bottom: 20px;
        }

        /* MOBILE FIX: 3 columns using percentages to avoid overflow */
        .flex-grid {
            display: flex !important;
            flex-wrap: wrap !important;
            width: 100% !important;
            max-width: 300px !important; /* Smaller max-width for mobile portrait */
            margin: 0 auto !important;
        }
        
        .flex-grid div[data-testid="column"] {
            flex: 1 1 31% !important; /* Forces 3 items per row */
            min-width: 31% !important;
            padding: 4px !important;
        }

        div.stButton > button {
            aspect-ratio: 1 / 1 !important;
            width: 100% !important;
            font-size: clamp(1.2rem, 5vw, 2rem) !important;
            font-weight: 900 !important;
            background-color: #262730 !important;
            border: 2px solid #555 !important;
        }

        /* CONTEXT ACTION BUTTON: Standard Size */
        .action-panel { width: 220px !important; margin: 15px auto !important; }
        .action-panel button {
            height: 50px !important;
            width: 220px !important;
            font-size: 1.1rem !important;
            font-weight: 700 !important;
            aspect-ratio: auto !important;
            border-radius: 8px !important;
        }
        .reveal-style button { background-color: #3498db !important; color: white !important; }
        .next-style button { background-color: #27ae60 !important; color: white !important; }
        .skip-btn button { background-color: #c0392b !important; color: white !important; height: 40px !important; margin-top: 10px; }
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
    w_len = st.number_input("Word Length", 2, 15, 7)
    mode = st.radio("Study Focus:", ["Probability Rank", "Playability Rating"], horizontal=True)
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
def find_all_anagrams(rack):
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
            if not (find_all_anagrams(test_rack) if '?' in test_rack else st.session_state.alpha_map.get(test_rack, [])):
                rack = test_rack; break
    st.session_state.display_alpha = rack
    st.session_state.current_solutions = find_all_anagrams(rack) if '?' in rack else st.session_state.alpha_map.get(rack, [])
    st.session_state.answered, st.session_state.needs_new_rack, st.session_state.last_guess = False, False, None
    st.session_state.current_rack_id = random.randint(0, 9999)

if st.session_state.lexicon_loaded and st.session_state.needs_new_rack: trigger_new()

# --- 6. MAIN LAYOUT ---
if st.session_state.lexicon_loaded:
    col_l, col_r = st.columns([1, 1], gap="large")
    with col_l:
        st.markdown(f"<div class='rack-text'>{st.session_state.display_alpha}</div>", unsafe_allow_html=True)
        
        # 3-Column Tile Grid
        st.markdown('<div class="flex-grid">', unsafe_allow_html=True)
        for i in range(10):
            label = str(i) if i <= 8 else "8+"
            if st.columns(3)[i % 3].button(label, key=f"t_{i}_{st.session_state.current_rack_id}"):
                st.session_state.last_guess, st.session_state.answered = i, True
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # --- UNIVERSAL ACTION BUTTON LOGIC ---
        st.markdown('<div class="action-panel">', unsafe_allow_html=True)
        if not st.session_state.answered:
            st.markdown('<div class="reveal-style">', unsafe_allow_html=True)
            if st.button("Reveal Answer (Enter)", key="reveal_btn"):
                st.session_state.answered, st.session_state.last_guess = True, -1 # -1 = No guess made
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="next-style">', unsafe_allow_html=True)
            if st.button("Next Rack (Enter)", key="next_btn"):
                st.session_state.needs_new_rack = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="skip-btn">', unsafe_allow_html=True)
        if st.button("Skip Rack", key="skip_btn"):
            st.session_state.streak, st.session_state.needs_new_rack = 0, True
            st.rerun()
        st.markdown('</div></div>', unsafe_allow_html=True)

    with col_r:
        if st.session_state.answered:
            real_count = len(st.session_state.current_solutions)
            if st.session_state.last_guess == -1:
                st.info(f"Answer revealed: {real_count} word(s).")
                st.session_state.streak = 0
            elif (st.session_state.last_guess == real_count) or (st.session_state.last_guess == 9 and real_count > 8):
                st.success(f"CORRECT! ({real_count})")
                if st.session_state.last_scored_id != st.session_state.display_alpha:
                    st.session_state.streak += 1; st.session_state.last_scored_id = st.session_state.display_alpha; st.rerun()
            else:
                st.error(f"WRONG. Actual: {real_count} | You: {st.session_state.last_guess if st.session_state.last_guess <= 8 else '8+'}")
                st.session_state.streak = 0; st.rerun()

            for sol in sorted(st.session_state.current_solutions, key=lambda x: x['word']):
                with st.expander(f"📖 {sol['word']}", expanded=True):
                    if st.session_state.get('defs_toggle'): st.write(f"*{sol['def']}*")
                    st.write(f"**Hooks:** `[{sol['f']}]` {sol['word']} `[{sol['b']}]` ")
                    st.caption(f"Prob: {sol['prob']} | Play: {sol['play']}")
            if not st.session_state.current_solutions: st.info("Rack was a PHONY.")