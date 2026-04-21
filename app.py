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
        .rack-text {
            text-align: center; letter-spacing: 5px; color: #f1c40f; 
            font-size: clamp(2.5rem, 6vw, 4.5rem); font-weight: 900;
            white-space: nowrap; margin-bottom: 20px;
        }
        .reveal-btn button { background-color: #3498db !important; color: white !important; width: 100%; height: 50px; border-radius: 12px; border: none; font-weight: bold; font-size: 1.1rem; }
        .next-btn button { background-color: #27ae60 !important; color: white !important; width: 100%; height: 50px; border-radius: 12px; border: none; font-weight: bold; font-size: 1.1rem; }
        .filter-help { font-size: 0.8rem; color: #888; margin-bottom: 10px; }
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

def check_smart_filter(word, query):
    if not query: return True
    query = query.upper().strip()
    if query.startswith("^"): return word.startswith(query[1:])
    if query.endswith("$"): return word.endswith(query[:-1])
    if 'V' in query and query[:-1].isdigit():
        return sum(1 for c in word if c in 'AEIOU') == int(query[:-1])
    if 'C' in query and query[:-1].isdigit():
        return sum(1 for c in word if c not in 'AEIOU') == int(query[:-1])
    return any(char in word for char in query)

# --- GAME CALLBACKS ---
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

# --- RACK GENERATION ---
if alpha_map and st.session_state.state['needs_new_rack']:
    filtered_list = st.session_state.state['filtered_alphas'] or [a for a in alpha_map.keys() if len(a) == 7]
    
    sample_len = len(filtered_list[0])
    phony_chance = 0.20 if sample_len <= 6 else (0.15 if sample_len == 7 else 0.10)
    st.session_state.state['is_phony'] = random.random() < phony_chance
    rack = random.choice(filtered_list)
    
    if random.random() < 0.20:
        arr = list(rack); arr[random.randint(0, len(arr)-1)] = '?'
        rack = "".join(sorted(arr))
    
    if st.session_state.state['is_phony']:
        for _ in range(30):
            v, c = 'AEIOU', 'BCDFGHJKLMNPQRSTVWXYZ'
            arr = list(rack); idx = random.randint(0, len(arr)-1)
            if arr[idx] == '?': continue
            source = v if arr[idx] in v else c
            arr[idx] = random.choice([x for x in source if x != arr[idx]])
            test = "".join(sorted(arr))
            if not (find_anagrams(test) if '?' in test else alpha_map.get(test, [])):
                rack = test; break
                
    st.session_state.state.update({
        'display_alpha': rack,
        'current_solutions': find_anagrams(rack) if '?' in rack else alpha_map.get(rack, []),
        'needs_new_rack': False
    })

# --- 4. SIDEBAR SETTINGS ---
study_mode = st.sidebar.radio("Study Mode", ["Anagrams", "Hooks"], horizontal=True)
st.sidebar.metric("Streak", st.session_state.state['streak'])
show_defs = st.sidebar.checkbox("Show Definitions", True)

with st.sidebar.form("settings"):
    st.write("### Smart Filter")
    length = st.number_input("Word Length", 2, 15, 7)
    smart_query = st.text_input("Pattern (e.g. ^UN, ING$, 5v, JQZ)", "")
    mode = st.radio("Rank By", ["Prob", "Play"], horizontal=True)
    c1, c2 = st.columns(2)
    v_min, v_max = c1.number_input("Min", 0, 200000, 0), c2.number_input("Max", 0, 200000, 40000)
    
    if st.form_submit_button("Apply & Reset"):
        param = 4 if mode == "Prob" else 5
        filtered = [a for a, words in alpha_map.items() if len(a) == length and any((v_min <= w[param] <= v_max) and check_smart_filter(w[0], smart_query) for w in words)]
        st.session_state.state['filtered_alphas'] = filtered
        st.session_state.state['needs_new_rack'] = True
        st.rerun()

# --- 5. UI LAYOUT ---
components.html("<script>const doc = window.parent.document; doc.addEventListener('keydown', function(e) { if (e.target.tagName === 'INPUT') return; if (e.key === 'Enter') { const action = Array.from(doc.querySelectorAll('button')).find(b => b.innerText.includes('Reveal') || b.innerText.includes('Next') || b.innerText.includes('Check')); if (action) action.click(); } });</script>", height=0)

col_l, col_r = st.columns([1, 1], gap="large")

with col_l:
    st.markdown(f"<div class='rack-text'>{st.session_state.state['display_alpha']}</div>", unsafe_allow_html=True)
    
    if study_mode == "Hooks":
        if st.session_state.state['is_phony']:
            st.warning("PHONY rack. No hooks to study.")
        elif st.session_state.state['current_solutions']:
            sol = st.session_state.state['current_solutions'][0]
            c1, c2 = st.columns(2)
            u_f = c1.text_input("Front Hooks", key=f"f_{st.session_state.state['current_rack_id']}").upper().strip()
            u_b = c2.text_input("Back Hooks", key=f"b_{st.session_state.state['current_rack_id']}").upper().strip()
            
            if st.button("Check Hooks (Enter)"):
                st.session_state.state['answered'] = True
                if set(u_f) == set(sol[2].strip()) and set(u_b) == set(sol[3].strip()):
                    st.success("Perfect!")
                    st.session_state.state['streak'] += 1
                else:
                    st.error(f"Actual: Front [{sol[2]}] Back [{sol[3]}]")
                    st.session_state.state['streak'] = 0
    else:
        selection = st.pills("Count:", ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9+"], selection_mode="single", key=f"p_{st.session_state.state['current_rack_id']}", label_visibility="collapsed")
        if selection and not st.session_state.state['answered']:
            st.session_state.state['last_guess'] = 9 if selection == "9+" else int(selection)
            st.session_state.state['answered'] = True
            st.rerun()

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
        if study_mode == "Anagrams" and s['last_guess'] is not None:
            if (s['last_guess'] == real) or (s['last_guess'] == 9 and real >= 9):
                st.success(f"CORRECT! ({real})")
                if s['last_scored_id'] != s['display_alpha']:
                    st.session_state.state['streak'] += 1
                    s['last_scored_id'] = s['display_alpha']
            elif s['last_guess'] != -1:
                st.error(f"WRONG. Actual: {real}")
        
        for sol in sorted(s['current_solutions'], key=lambda x: x[0]):
            with st.expander(f"📖 {sol[0]}", expanded=True):
                st.write(f"**Hooks:** `[{sol[2]}]` {sol[0]} `[{sol[3]}]`")
                if show_defs: st.write(f"*{sol[1]}*")