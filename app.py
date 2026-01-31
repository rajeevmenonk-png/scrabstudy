import streamlit as st
import random
import re
import os
from collections import defaultdict
import streamlit.components.v1 as components

# --- CONFIG ---
st.set_page_config(page_title="Scrabble Anagram Pro", layout="wide")

if 'state' not in st.session_state:
    st.session_state.state = {
        'streak': 0, 'display_alpha': None, 'answered': False, 
        'current_solutions': [], 'is_phony': False, 'last_guess': None, 
        'last_scored_id': None, 'needs_new_rack': True,
        'filtered_alphas': [], 'current_rack_id': 0
    }

st.markdown("""
    <style>
        .rack-text {
            text-align: center; letter-spacing: 5px; color: #f1c40f; 
            font-size: clamp(2.5rem, 6vw, 4.5rem); font-weight: 900;
            white-space: nowrap; margin-bottom: 20px;
        }
        .reveal-btn button { background-color: #3498db !important; color: white !important; width: 100%; }
        .next-btn button { background-color: #27ae60 !important; color: white !important; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# --- DATA ---
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
            info = (word, p[1], p[2], p[3], int(p[4]) if p[4].strip().isdigit() else 999999, int(p[5]) if p[5].strip().isdigit() else 0)
            temp_map["".join(sorted(word))].append(info)
    return dict(temp_map)

alpha_map = load_lexicon("CSW24 2-15.txt")

# --- LOGIC ---
def cb_reveal():
    st.session_state.state['last_guess'] = -1
    st.session_state.state['answered'] = True
    st.session_state.state['streak'] = 0

def cb_next():
    st.session_state.state['needs_new_rack'] = True
    st.session_state.state['answered'] = False
    st.session_state.state['last_guess'] = None

def find_anagrams(rack):
    results, seen = [], set()
    base = rack.replace('?', '')
    for char_code in range(65, 91):
        sub = "".join(sorted(base + chr(char_code)))
        for m in alpha_map.get(sub, []):
            if m[0] not in seen: results.append(m); seen.add(m[0])
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
        'current_rack_id': random.randint(1000, 9999),
        'needs_new_rack': False
    })

# --- UI ---
st.sidebar.metric("Streak", st.session_state.state['streak'])
show_defs = st.sidebar.checkbox("Show Definitions", True)
with st.sidebar.form("settings"):
    length = st.number_input("Len", 2, 15, 7)
    mode = st.radio("Focus", ["Prob", "Play"], horizontal=True)
    mn, mx = st.columns(2)
    v_min, v_max = mn.number_input("Min", 0, 200000, 0), mx.number_input("Max", 0, 200000, 40000)
    if st.form_submit_button("Apply"):
        param = 4 if mode == "Prob" else 5
        st.session_state.state['filtered_alphas'] = [a for a, words in alpha_map.items() 
            if len(a) == length and any(v_min <= w[param] <= v_max for w in words)]
        st.session_state.state['needs_new_rack'] = True
        st.rerun()

col_l, col_r = st.columns([1, 1], gap="large")

with col_l:
    st.markdown(f"<div class='rack-text'>{st.session_state.state['display_alpha']}</div>", unsafe_allow_html=True)
    
    # NATIVE PILLS (Handles layout automatically)
    selection = st.pills("Count:", ["0", "1", "2", "3", "4", "5", "6", "7", "8+"], selection_mode="single", key=f"pills_{st.session_state.state['current_rack_id']}")
    
    if selection and not st.session_state.state['answered']:
        val = 8 if selection == "8+" else int(selection)
        st.session_state.state['last_guess'] = val
        st.session_state.state['answered'] = True
        st.rerun()

    st.write("")
    if not st.session_state.state['answered']:
        st.markdown('<div class="reveal-btn">', unsafe_allow_html=True)
        st.button("Reveal Answer", on_click=cb_reveal)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="next-btn">', unsafe_allow_html=True)
        st.button("Next Rack", on_click=cb_next)
        st.markdown('</div>', unsafe_allow_html=True)

with col_r:
    s = st.session_state.state
    if s['answered']:
        real = len(s['current_solutions'])
        ug = s['last_guess']
        is_cor = (ug == real) or (ug == 8 and real >= 8)
        if ug == -1: st.info(f"Revealed: {real}")
        elif is_cor:
            st.success(f"CORRECT! ({real})")
            if s['last_scored_id'] != s['display_alpha']:
                st.session_state.state['streak'] += 1
                st.session_state.state['last_scored_id'] = s['display_alpha']
        else:
            st.error(f"WRONG. Actual: {real}")
            st.session_state.state['streak'] = 0
            
        if s['current_solutions']:
            for sol in sorted(s['current_solutions'], key=lambda x: x[0]):
                with st.expander(f"📖 {sol[0]}", expanded=True):
                    st.write(f"**Hooks:** `[{sol[2]}]` {sol[0]} `[{sol[3]}]`")
                    st.caption(f"Prob: {sol[4]} | Play: {sol[5]}")
                    if show_defs: st.write(f"*{sol[1]}*")
        else:
            st.info("PHONY.")