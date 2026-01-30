import streamlit as st
import random
import re
from collections import defaultdict
import streamlit.components.v1 as components

# --- 1. INITIALIZATION ---
state_keys = {
    'streak': 0, 'display_alpha': None, 'answered': False, 
    'current_solutions': [], 'is_phony': False, 'last_guess': None, 
    'last_scored_id': None, 'needs_new_rack': True, 'show_defs': True,
    'filtered_alphas': []
}
for key, val in state_keys.items():
    if key not in st.session_state:
        st.session_state[key] = val

st.set_page_config(page_title="Scrabble Anagram Pro", layout="wide")

# --- 2. KEYBOARD LISTENER ---
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
        .block-container { padding-top: 1rem; }
        [data-testid="stSidebar"] { min-width: 220px; max-width: 260px; }
        
        /* THE RACK */
        .alphagram-text {
            text-align: center; 
            letter-spacing: 12px; 
            color: #f1c40f; 
            font-size: 3.8rem; 
            font-weight: 900;
            margin-bottom: 20px;
        }

        /* BUTTON CONSTRAINTS - Prevents giant buttons */
        .center-wrap {
            max-width: 350px;
            margin: 0 auto;
        }

        /* NUMBER TILES: Chunky & Square */
        div.stButton > button {
            aspect-ratio: 1 / 1 !important;
            width: 100% !important;
            font-size: 2rem !important;
            font-weight: 900 !important;
            border-radius: 12px !important;
            background-color: #262730 !important;
            border: 2px solid #555 !important;
            box-shadow: 0 5px 0 #111;
            margin-bottom: 5px;
        }
        
        div.stButton > button:hover { border-color: #f1c40f !important; color: #f1c40f !important; }

        /* NEXT & SKIP: Regular size, not giant */
        .control-btns div.stButton > button {
            aspect-ratio: auto !important;
            height: 55px !important;
            font-size: 1.2rem !important;
            box-shadow: 0 4px 0 #1e8449;
        }

        .next-btn button { background-color: #27ae60 !important; color: white !important; border: none !important; }
        .skip-btn button { background-color: #c0392b !important; color: white !important; border: none !important; box-shadow: 0 4px 0 #922b21 !important; height: 45px !important; font-size: 1rem !important; }
    </style>
""", unsafe_allow_html=True)

# --- 3. DATA & LOGIC ---
@st.cache_data
def load_lexicon(file_content):
    data, alphagram_map = [], defaultdict(list)
    lines = file_content.decode("latin-1").splitlines()
    for line in lines:
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

# --- 4. SIDEBAR ---
st.sidebar.metric("Streak", st.session_state.streak)
uploaded_file = st.sidebar.file_uploader("Upload Lexicon", type="txt", label_visibility="collapsed")

if uploaded_file:
    if 'master_data' not in st.session_state:
        st.session_state.master_data, st.session_state.alpha_map = load_lexicon(uploaded_file.getvalue())
        st.session_state.valid_alphas = set(st.session_state.alpha_map.keys())

    with st.sidebar.form("filter_form"):
        w_len = st.number_input("Len", 2, 15, 7)
        c1, c2 = st.columns(2)
        min_p, max_p = c1.number_input("MinP", 0, 100000, 0), c2.number_input("MaxP", 0, 100000, 40000)
        c3, c4 = st.columns(2)
        min_play, max_play = c3.number_input("MinPL", 0, 2000, 0), c4.number_input("MaxPL", 0, 2000, 1000)
        if st.form_submit_button("Apply Filters"):
            st.session_state.filtered_alphas = [a for a, words in st.session_state.alpha_map.items() 
                if len(a) == w_len and any(min_p <= w['prob'] <= max_p and min_play <= w['play'] <= max_play for w in words)]
            st.session_state.needs_new_rack = True
            st.rerun()

    if not st.session_state.filtered_alphas and 'master_data' in st.session_state:
        st.session_state.filtered_alphas = [a for a, words in st.session_state.alpha_map.items() if len(a) == 7]

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
        if not st.session_state.filtered_alphas: return
        st.session_state.is_phony = random.random() < 0.20
        use_blank = random.random() < 0.20
        base = random.choice(st.session_state.filtered_alphas)
        rack = base
        if use_blank:
            arr = list(base); arr[random.randint(0, len(arr)-1)] = '?'
            rack = "".join(sorted(arr))
        if st.session_state.is_phony:
            for _ in range(20):
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

    if st.session_state.needs_new_rack: trigger_new()

    # --- 6. MAIN LAYOUT ---
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown(f"<div class='alphagram-text'>{st.session_state.display_alpha}</div>", unsafe_allow_html=True)
        
        st.markdown('<div class="center-wrap">', unsafe_allow_html=True)
        if not st.session_state.answered:
            # 3-column grid for tiles
            g1, g2, g3 = st.columns(3)
            rows = [g1, g2, g3]
            for i in range(10):
                label = str(i) if i <= 8 else "8+"
                if rows[i % 3].button(label, key=f"btn_{i}"):
                    st.session_state.last_guess = i
                    st.session_state.answered = True
                    st.rerun()
        else:
            st.markdown('<div class="control-btns next-btn">', unsafe_allow_html=True)
            if st.button("Next Rack (Enter)", use_container_width=True, type="primary"):
                st.session_state.needs_new_rack = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="control-btns skip-btn">', unsafe_allow_html=True)
        if st.button("Skip / Reset Streak", use_container_width=True):
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
                    st.caption(f"Prob: {sol['prob']} | PL: {sol['play']}")
            if not st.session_state.current_solutions: st.info("Rack was a PHONY.")