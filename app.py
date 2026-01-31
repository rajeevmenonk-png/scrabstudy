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
    'filtered_alphas': [], 'lexicon_loaded': False
}
for key, val in state_keys.items():
    if key not in st.session_state:
        st.session_state[key] = val

st.set_page_config(page_title="Scrabble Anagram Pro", layout="wide")

# --- 2. KEYBOARD & MOBILE GRID CSS ---
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
        .block-container { padding-top: 1.5rem; max-width: 1200px; margin: 0 auto; }
        
        /* THE RACK */
        .rack-text {
            text-align: center; 
            letter-spacing: 12px; 
            color: #f1c40f; 
            font-size: clamp(2.5rem, 8vw, 4rem); 
            font-weight: 900;
            margin-bottom: 20px;
        }

        /* TILE GRID (0-8 and 8+) - Forces 3 columns even on Mobile */
        .tile-container {
            display: flex;
            flex-wrap: wrap;
            max-width: 330px;
            margin: 0 auto;
            justify-content: center;
        }
        
        .tile-container div[data-testid="column"] {
            flex: 1 1 30% !important;
            min-width: 30% !important;
            padding: 4px !important;
        }
        
        div.stButton > button {
            aspect-ratio: 1 / 1 !important;
            width: 100% !important;
            font-size: 2.2rem !important;
            font-weight: 900 !important;
            border-radius: 10px !important;
            background-color: #262730 !important;
            border: 2px solid #555 !important;
            box-shadow: 0 4px 0 #111;
        }

        /* CONTROL BUTTONS - Strictly Fixed Small Size */
        .control-panel {
            width: 200px !important;
            margin: 15px auto !important;
        }
        
        .control-panel button {
            height: 48px !important;
            width: 200px !important;
            font-size: 1rem !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            aspect-ratio: auto !important;
        }

        .next-btn button { background-color: #27ae60 !important; color: white !important; border: none !important; box-shadow: 0 3px 0 #1e8449 !important; }
        .skip-btn button { background-color: #c0392b !important; color: white !important; border: none !important; margin-top: 10px; box-shadow: 0 3px 0 #922b21 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. AUTO-LOAD LEXICON ---
@st.cache_data
def load_lexicon_from_file(filename):
    data, alphagram_map = [], defaultdict(list)
    if not os.path.exists(filename):
        return None, None
    with open(filename, 'r', encoding='latin-1') as f:
        for line in f:
            parts = line.split('\t')
            if not parts: continue
            word = re.sub(r'[^A-Z]', '', parts[0].replace('·', '').upper())
            if not word: continue
            d = {'word': word, 'def': parts[1].strip() if len(parts) > 1 else "",
                 'f': parts[2].strip() if len(parts) > 2 else "", 'b': parts[3].strip() if len(parts) > 3 else "",
                 'prob': int(parts[4]) if len(parts) > 4 and parts[4].strip().isdigit() else 999999,
                 'play': int(parts[5]) if len(parts) > 5 and parts[5].strip().isdigit() else 0}
            alpha = "".join(sorted(word))
            data.append(d); alphagram_map[alpha].append(d)
    return data, alphagram_map

# Attempt to load local file automatically
if not st.session_state.lexicon_loaded:
    # Set this to your actual filename on GitHub
    filename = "CSW24 2-15.txt" 
    data, alpha_map = load_lexicon_from_file(filename)
    if data:
        st.session_state.master_data = data
        st.session_state.alpha_map = alpha_map
        st.session_state.valid_alphas = set(alpha_map.keys())
        st.session_state.lexicon_loaded = True

# --- 4. SIDEBAR ---
st.sidebar.metric("Streak", st.session_state.streak)
if not st.session_state.lexicon_loaded:
    st.sidebar.warning("Lexicon file not found in directory.")

with st.sidebar.form("filter_form"):
    st.write("### Quiz Filters")
    w_len = st.number_input("Len", 2, 15, 7)
    c1, c2 = st.columns(2)
    min_p, max_p = c1.number_input("MinP", 0, 100000, 0), c2.number_input("MaxP", 0, 100000, 40000)
    c3, c4 = st.columns(2)
    min_play, max_play = c3.number_input("MinPL", 0, 2000, 0), c4.number_input("MaxPL", 0, 2000, 1000)
    if st.form_submit_button("Apply Filters & Reset"):
        st.session_state.filtered_alphas = [a for a, words in st.session_state.alpha_map.items() 
            if len(a) == w_len and any(min_p <= w['prob'] <= max_p and min_play <= w['play'] <= max_play for w in words)]
        st.session_state.needs_new_rack = True
        st.rerun()

st.session_state.show_defs = st.sidebar.checkbox("Show Definitions", value=True)

# --- 5. GAME LOGIC ---
def find_all_blank_anagrams(rack):
    results, seen = [], set()
    base = rack.replace('?', '')
    for char_code in range(65, 91):
        sub_alpha = "".join(sorted(base + chr(char_code)))
        for m in st.session_state.alpha_map.get(sub_alpha, []):
            if m['word'] not in seen:
                results.append(m); seen.add(m['word'])
    return results

def trigger_new():
    if not st.session_state.get('filtered_alphas'): 
        # Default to length 7 if no filters applied yet
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
            sols = find_all_blank_anagrams(test_rack) if '?' in test_rack else st.session_state.alpha_map.get(test_rack, [])
            if not sols:
                rack = test_rack; break
    st.session_state.display_alpha, st.session_state.current_solutions = rack, (find_all_blank_anagrams(rack) if '?' in rack else st.session_state.alpha_map.get(rack, []))
    st.session_state.answered = False
    st.session_state.needs_new_rack = False

if st.session_state.lexicon_loaded and st.session_state.needs_new_rack:
    trigger_new()

# --- 6. MAIN LAYOUT ---
if st.session_state.lexicon_loaded:
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown(f"<div class='rack-text'>{st.session_state.display_alpha}</div>", unsafe_allow_html=True)
        
        # Tile Grid: Forced 3 columns
        st.markdown('<div class="tile-container">', unsafe_allow_html=True)
        g1, g2, g3 = st.columns(3)
        cols = [g1, g2, g3]
        for i in range(10):
            label = str(i) if i <= 8 else "8+"
            if cols[i % 3].button(label, key=f"btn_{i}"):
                st.session_state.last_guess = i
                st.session_state.answered = True
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Control Panel: Fixed width
        st.markdown('<div class="control-panel">', unsafe_allow_html=True)
        if st.session_state.answered:
            st.markdown('<div class="next-btn">', unsafe_allow_html=True)
            if st.button("Next Rack (Enter)", use_container_width=True, type="primary"):
                st.session_state.needs_new_rack = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="skip-btn">', unsafe_allow_html=True)
        if st.button("Skip Rack", use_container_width=True):
            st.session_state.streak = 0
            st.session_state.needs_new_rack = True
            st.rerun()
        st.markdown('</div></div>', unsafe_allow_html=True)

    with col2:
        if st.session_state.answered:
            real_count = len(st.session_state.current_solutions)
            correct = (st.session_state.last_guess == real_count) or (st.session_state.last_guess == 9 and real_count > 8)
            if correct:
                st.success(f"CORRECT! ({real_count})")
                if st.session_state.last_scored_id != st.session_state.display_alpha:
                    st.session_state.streak += 1; st.session_state.last_scored_id = st.session_state.display_alpha; st.rerun()
            else:
                st.error(f"WRONG. Actual: {real_count} | You: {st.session_state.last_guess if st.session_state.last_guess <= 8 else '8+'}")
                if st.session_state.streak > 0: st.session_state.streak = 0; st.rerun()

            for sol in sorted(st.session_state.current_solutions, key=lambda x: x['word']):
                with st.expander(f"📖 {sol['word']}", expanded=True):
                    if st.session_state.show_defs: st.write(f"*{sol['def']}*")
                    st.write(f"**Hooks:** `[{sol['f']}]` {sol['word']} `[{sol['b']}]`")
                    st.caption(f"Prob: {sol['prob']} | Play: {sol['play']}")