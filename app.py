import streamlit as st
import random
import re
import os
from collections import defaultdict
import streamlit.components.v1 as components

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Scrabble Anagram Pro", layout="wide")

if 'state' not in st.session_state:
    st.session_state.state = {
        'streak': 0, 'display_alpha': None, 'answered': False, 
        'current_solutions': [], 'is_phony': False, 'last_guess': None, 
        'last_scored_id': None, 'needs_new_rack': True,
        'filtered_alphas': [], 'current_rack_id': 0
    }

# --- 2. CSS STYLING ---
st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
        
        /* ALPHAGRAM */
        .rack-text {
            text-align: center; letter-spacing: 5px; color: #f1c40f; 
            font-size: clamp(2.5rem, 6vw, 4.5rem); font-weight: 900;
            white-space: nowrap; margin-bottom: 20px;
        }

        /* --- FAUX PILLS (Custom Button Row) --- */
        /* This container forces the buttons to sit in a wrapping row */
        .pill-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: center;
            margin-bottom: 20px;
        }

        /* Style the buttons to look like pills/chips */
        .pill-container button {
            width: 45px !important;
            height: 45px !important;
            border-radius: 50% !important; /* Circular/Pill shape */
            font-weight: bold !important;
            font-size: 1.2rem !important;
            padding: 0 !important;
            background-color: #262730 !important;
            border: 2px solid #555 !important;
        }
        
        .reveal-btn button { background-color: #3498db !important; color: white !important; width: 100%; border-radius: 12px; height: 50px; }
        .next-btn button { background-color: #27ae60 !important; color: white !important; width: 100%; border-radius: 12px; height: 50px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. DATA & LOGIC ---
@st.cache_data(ttl=3600)
def load_lexicon(filename):
    if not os.path.exists(filename): return None
    temp_map = defaultdict(list)
    with open(filename, 'r', encoding='latin-1') as f:
        for line in f:
            p = line.split('\t')
            if len(p) < 6: continue
            word = re.sub(r'[^A-Z]', '', p[0].replace('·', '').upper())
            if not word: continue
            # 0=Word, 1=Def, 2=Front, 3=Back, 4=Prob, 5=Play
            info = (word, p[1], p[2], p[3], int(p[4]) if p[4].strip().isdigit() else 999999, int(p[5]) if p[5].strip().isdigit() else 0)
            temp_map["".join(sorted(word))].append(info)
    return dict(temp_map)

alpha_map = load_lexicon("CSW24 2-15.txt")

# Callbacks
def cb_guess(val):
    st.session_state.state['last_guess'] = val
    st.session_state.state['answered'] = True

def cb_reveal():
    st.session_state.state['last_guess'] = -1
    st.session_state.state['answered'] = True
    st.session_state.state['streak'] = 0

def cb_next():
    st.session_state.state['needs_new_rack'] = True
    st.session_state.state['answered'] = False
    st.session_state.state['last_guess'] = None
    st.session_state.state['current_rack_id'] += 1

def find_anagrams(rack):
    results, seen = [], set()
    base = rack.replace('?', '')
    for char_code in range(65, 91):
        sub = "".join(sorted(base + chr(char_code)))
        for m in alpha_map.get(sub, []):
            if m[0] not in seen: results.append(m); seen.add(m[0])
    return results

if alpha_map and st.session_state.state['needs_new_rack']:
    # 1. Apply Filters
    if not st.session_state.state['filtered_alphas']:
        # Fallback
        st.session_state.state['filtered_alphas'] = [a for a in alpha_map.keys() if len(a) == 7]
    
    # 2. Phony Logic (Dynamic Frequency)
    # Shorter words = higher phony chance. Longer words = lower.
    word_len = len(st.session_state.state['filtered_alphas'][0])
    phony_chance = 0.20 if word_len <= 6 else (0.15 if word_len == 7 else 0.10)
    
    st.session_state.state['is_phony'] = random.random() < phony_chance
    rack = random.choice(st.session_state.state['filtered_alphas'])
    
    # 3. Blanks
    if random.random() < 0.20:
        arr = list(rack); arr[random.randint(0, len(arr)-1)] = '?'
        rack = "".join(sorted(arr))
    
    # 4. Generate Phony (On the Fly)
    if st.session_state.state['is_phony']:
        # Try to create a subtle phony (swap 1 char)
        for _ in range(30):
            v, c = 'AEIOU', 'BCDFGHJKLMNPQRSTVWXYZ'
            arr = list(rack); idx = random.randint(0, len(arr)-1)
            if arr[idx] == '?': continue
            # Swap vowel for vowel, cons for cons to make it look realistic
            arr[idx] = random.choice([x for x in v if x != arr[idx]]) if arr[idx] in v else random.choice([x for x in c if x != arr[idx]])
            test = "".join(sorted(arr))
            # Verify it's actually invalid
            if not (find_anagrams(test) if '?' in test else alpha_map.get(test, [])):
                rack = test; break

    st.session_state.state.update({
        'display_alpha': rack,
        'current_solutions': find_anagrams(rack) if '?' in rack else alpha_map.get(rack, []),
        'needs_new_rack': False
    })

# --- 4. KEYBOARD LISTENER (Robust) ---
# Since we are using real buttons again, this will work perfectly.
components.html(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.target.tagName === 'INPUT') return; // Don't trigger when typing in filters
        
        if (e.key >= '0' && e.key <= '9') {
            const btns = Array.from(doc.querySelectorAll('button'));
            const label = e.key === '9' ? '9+' : e.key;
            // Precise match to avoid matching "100" when pressing "1"
            const target = btns.find(b => b.innerText.trim() === label);
            if (target) target.click();
        } 
        
        if (e.key === 'Enter') {
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

# --- 5. UI LAYOUT ---
st.sidebar.metric("Streak", st.session_state.state['streak'])
show_defs = st.sidebar.checkbox("Show Definitions", True)

# --- REVISED FILTER FORM ---
with st.sidebar.form("settings"):
    st.write("### Filter Rules")
    length = st.number_input("Word Length", 2, 15, 7)
    
    # NEW: Natural Language Filter
    contains_filter = st.text_input("Must contain (e.g. JQXZ)", "")
    
    mode = st.radio("Rank By", ["Prob", "Play"], horizontal=True)
    c1, c2 = st.columns(2)
    v_min, v_max = c1.number_input("Min", 0, 200000, 0), c2.number_input("Max", 0, 200000, 40000)
    
    if st.form_submit_button("Apply & Reset"):
        param = 4 if mode == "Prob" else 5
        
        # Logic: Filter by Length AND Range AND (Optional) Letters
        # The 'contains_filter' checks if the alphagram contains ANY of the letters typed
        target_chars = set(contains_filter.upper())
        
        filtered = []
        for a, words in alpha_map.items():
            if len(a) != length: continue
            
            # Check Range
            if not any(v_min <= w[param] <= v_max for w in words): continue
            
            # Check Letters (if user typed something)
            if target_chars:
                if not any(char in a for char in target_chars): continue
            
            filtered.append(a)

        st.session_state.state['filtered_alphas'] = filtered
        st.session_state.state['needs_new_rack'] = True
        st.rerun()

col_l, col_r = st.columns([1, 1], gap="large")

with col_l:
    st.markdown(f"<div class='rack-text'>{st.session_state.state['display_alpha']}</div>", unsafe_allow_html=True)
    
    # --- CUSTOM BUTTON ROW (0-9+) ---
    # We use a CSS container to flow them like pills
    st.markdown('<div class="pill-container">', unsafe_allow_html=True)
    
    # Note: Streamlit buttons cannot be nested directly in HTML div strings easily.
    # So we use st.columns with a special layout or just simple buttons with CSS float.
    # The safest way is using `st.columns` but allowing them to wrap.
    # Since we want 10 buttons, let's use a dense row.
    
    cols = st.columns(10)
    for i in range(10):
        label = str(i) if i < 9 else "9+"
        # Using a unique key ensures state reset
        if cols[i].button(label, key=f"btn_{i}_{st.session_state.state['current_rack_id']}", on_click=cb_guess, args=(i,)):
            pass # Callback handles logic
            
    st.markdown('</div>', unsafe_allow_html=True)

    st.write("")
    if not st.session_state.state['answered']:
        st.markdown('<div class="reveal-btn">', unsafe_allow_html=True)
        st.button("Reveal Answer (Enter)", on_click=cb_reveal)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="next-btn">', unsafe_allow_html=True)
        st.button("Next Rack (Enter)", on_click=cb_next)
        st.markdown('</div>', unsafe_allow_html=True)

with col_r:
    s = st.session_state.state
    if s['answered']:
        real = len(s['current_solutions'])
        ug = s['last_guess']
        is_cor = (ug == real) or (ug == 9 and real >= 9)
        
        if ug == -1: st.info(f"Revealed: {real}")
        elif is_cor:
            st.success(f"CORRECT! ({real})")
            if s['last_scored_id'] != s['display_alpha']:
                st.session_state.state['streak'] += 1
                st.session_state.state['last_scored_id'] = s['display_alpha']
        else:
            g_str = str(ug) if ug < 9 else "9+"
            st.error(f"WRONG. Actual: {real} | You: {g_str}")
            st.session_state.state['streak'] = 0
            
        if s['current_solutions']:
            for sol in sorted(s['current_solutions'], key=lambda x: x[0]):
                with st.expander(f"📖 {sol[0]}", expanded=True):
                    st.write(f"**Hooks:** `[{sol[2]}]` {sol[0]} `[{sol[3]}]`")
                    st.caption(f"Prob: {sol[4]} | Play: {sol[5]}")
                    if show_defs: st.write(f"*{sol[1]}*")
        else:
            st.info("PHONY.")