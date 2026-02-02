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

        /* Action Buttons */
        .reveal-btn button { background-color: #3498db !important; color: white !important; width: 100%; height: 50px; border-radius: 12px; border: none; font-weight: bold; font-size: 1.1rem; }
        .next-btn button { background-color: #27ae60 !important; color: white !important; width: 100%; height: 50px; border-radius: 12px; border: none; font-weight: bold; font-size: 1.1rem; }
        
        /* Pill Styling Enhancement */
        div[data-baseweb="select"] > div { font-weight: bold; }
        
        /* Help Text */
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

# --- SMART FILTER LOGIC ---
def check_smart_filter(word, query):
    if not query: return True
    query = query.upper().strip()
    
    # 1. Prefix (e.g., ^UN)
    if query.startswith("^"):
        return word.startswith(query[1:])
    
    # 2. Suffix (e.g., ING$)
    if query.endswith("$"):
        return word.endswith(query[:-1])
    
    # 3. Vowel Count (e.g., 5v)
    if 'V' in query and query[:-1].isdigit():
        vowels = sum(1 for c in word if c in 'AEIOU')
        target = int(query[:-1])
        return vowels == target
    
    # 4. Consonant Count (e.g., 5c)
    if 'C' in query and query[:-1].isdigit():
        cons = sum(1 for c in word if c not in 'AEIOU')
        target = int(query[:-1])
        return cons == target

    # 5. Default: Contains ANY of the letters (e.g., JQZ)
    # Check if the word contains at least one of the letters in query
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

if alpha_map and st.session_state.state['needs_new_rack']:
    if not st.session_state.state['filtered_alphas']:
        # Fallback
        st.session_state.state['filtered_alphas'] = [a for a in alpha_map.keys() if len(a) == 7]
    
    # --- SMART PHONY LOGIC ---
    # Length-dependent frequency
    # Short words (<=6) are harder to spot, so we keep phonies common (20%)
    # Long words (8+) are easier to spot, so we lower phonies (10%)
    filtered_list = st.session_state.state['filtered_alphas']
    if filtered_list:
        sample_len = len(filtered_list[0])
        phony_chance = 0.20 if sample_len <= 6 else (0.15 if sample_len == 7 else 0.10)
    else:
        phony_chance = 0.15

    st.session_state.state['is_phony'] = random.random() < phony_chance
    rack = random.choice(filtered_list)
    
    # Blank Handling
    if random.random() < 0.20:
        arr = list(rack); arr[random.randint(0, len(arr)-1)] = '?'
        rack = "".join(sorted(arr))
    
    # Phony Generation (Swapping)
    if st.session_state.state['is_phony']:
        for _ in range(30):
            v, c = 'AEIOU', 'BCDFGHJKLMNPQRSTVWXYZ'
            arr = list(rack); idx = random.randint(0, len(arr)-1)
            if arr[idx] == '?': continue
            # Swap Vowel->Vowel or Consonant->Consonant for realism
            source = v if arr[idx] in v else c
            arr[idx] = random.choice([x for x in source if x != arr[idx]])
            test = "".join(sorted(arr))
            # Verify it's actually invalid
            if not (find_anagrams(test) if '?' in test else alpha_map.get(test, [])):
                rack = test; break
                
    st.session_state.state.update({
        'display_alpha': rack,
        'current_solutions': find_anagrams(rack) if '?' in rack else alpha_map.get(rack, []),
        'needs_new_rack': False
    })

# --- 4. KEYBOARD LISTENER (ENTER ONLY) ---
# Since pills don't support 0-9 keyboard input natively, we focus on Enter for flow
components.html(
    """
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.target.tagName === 'INPUT') return;
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

with st.sidebar.form("settings"):
    st.write("### Smart Filter")
    length = st.number_input("Word Length", 2, 15, 7)
    
    # SMART QUERY INPUT
    smart_query = st.text_input("Pattern (e.g. ^UN, ING$, 5v, JQZ)", "")
    st.markdown("""
    <div class="filter-help">
    <b>^UN</b> : Starts with UN<br>
    <b>ING$</b> : Ends with ING<br>
    <b>5v / 5c</b> : 5 Vowels or Consonants<br>
    <b>JQZ</b> : Contains J, Q, or Z
    </div>
    """, unsafe_allow_html=True)
    
    mode = st.radio("Rank By", ["Prob", "Play"], horizontal=True)
    c1, c2 = st.columns(2)
    v_min, v_max = c1.number_input("Min", 0, 200000, 0), c2.number_input("Max", 0, 200000, 40000)
    
    if st.form_submit_button("Apply & Reset"):
        param = 4 if mode == "Prob" else 5
        filtered = []
        
        # We must iterate items to check word properties (for starts/ends with)
        for a, words in alpha_map.items():
            if len(a) != length: continue
            
            # Check if ANY word in this alphagram group matches the Smart Filter
            # If at least one word matches, we include the rack.
            match_found = False
            for w in words:
                # w[0] is the word string
                # w[param] is prob or play value
                if (v_min <= w[param] <= v_max) and check_smart_filter(w[0], smart_query):
                    match_found = True
                    break
            
            if match_found:
                filtered.append(a)
                
        st.session_state.state['filtered_alphas'] = filtered
        st.session_state.state['needs_new_rack'] = True
        st.rerun()

col_l, col_r = st.columns([1, 1], gap="large")

with col_l:
    st.markdown(f"<div class='rack-text'>{st.session_state.state['display_alpha']}</div>", unsafe_allow_html=True)
    
    # NATIVE PILLS (0-9+)
    selection = st.pills(
        "Solution Count:", 
        options=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9+"], 
        selection_mode="single", 
        key=f"pills_{st.session_state.state['current_rack_id']}",
        label_visibility="collapsed"
    )
    
    if selection and not st.session_state.state['answered']:
        val = 9 if selection == "9+" else int(selection)
        st.session_state.state['last_guess'] = val
        st.session_state.state['answered'] = True
        st.rerun()

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