import streamlit as st
from screens.your_team import your_team_screen
from screens.callups import callup_screen
from screens.calendar import calendar_screen, race_results_screen
from screens.standings import standings_screen
from screens.championship import championship_screen, show_rules_screen, edit_rules_screen
from screens.show_racers import show_racer_screen
from screens.racers import racers_screen
from screens.roll import roll_screen
from supabase import create_client
from logic.functions import go_to_screen

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --------------------- HOME SCREEN ----------------------------------------------------

def home_screen(user):
    # protezione: se user è None, mostra un messaggio e non crashare
    if not user:
        st.warning("Profilo non selezionato. Torna alla schermata precedente o scegli un profilo.")
        return

    st.sidebar.markdown(f"""
    <div style="font-size:24px;">
        {user.get('who','')}<br>
        <i>{user.get('name','')}</i>
    </div>
    """, unsafe_allow_html=True)

    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.screen = "team"
        st.session_state.screen_history = []
        st.session_state.nav_selection = "Your team"

    screen_to_nav = {
        "team": "Your team",
        "standings": "Standings",
        "championship": "Championship",
        "calendar": "Calendar",
        "racers": "Racers",
        "roll": "Roll of Honor"
    }
    nav_to_screen = {v: k for k, v in screen_to_nav.items()}

    # Options list
    options = list(screen_to_nav.values())

    # Ensure nav_selection is valid; if not, set to first option (safe default)
    current_nav = st.session_state.get("nav_selection")
    if current_nav not in options:
        # fallback: pick sensible default
        st.session_state["nav_selection"] = options[0]
        current_nav = options[0]

    # IMPORTANT: provide a unique key to avoid StreamlitDuplicateElementId
    selection = st.sidebar.selectbox(
        "Navigate",
        options,
        index=options.index(current_nav),
        key="main_nav_select"   # <-- unique key added
    )

    logo_url = "https://koffsyfgevaannnmjkvl.supabase.co/storage/v1/object/sign/figures/new_favicon.svg?token=..."
    st.sidebar.image(logo_url, width='stretch')

    if selection != st.session_state.nav_selection:
        st.session_state.nav_selection = selection
        st.session_state.screen = nav_to_screen[selection]
        st.rerun()
        
    if "compute_results_open" not in st.session_state:
        st.session_state.compute_results_open = False

    if "compute_category" not in st.session_state:
        st.session_state.compute_category = None

    if "compute_race_id" not in st.session_state:
        st.session_state.compute_race_id = None

    # routing
    if st.session_state.screen == "team":
        your_team_screen(user)
    elif st.session_state.screen == "callups":
        callup_screen(user)
    elif st.session_state.screen == "calendar":
        calendar_screen(user)
    elif st.session_state.screen == "race_results":
        race_results_screen(user, st.session_state.get("selected_race", {}))
    elif st.session_state.screen == "standings":
        standings_screen(user)
    elif st.session_state.screen == "championship":
        championship_screen(user)
    elif st.session_state.screen in ["rules_f1", "rules_mgp"]:
        show_rules_screen(st.session_state.rules_data, st.session_state.screen)
    elif st.session_state.screen == "pilot_details":
        show_racer_screen(user)
    elif st.session_state.screen == "racers":
        racers_screen(user)
    elif st.session_state.screen == "roll":
        roll_screen(user)
    elif st.session_state.screen == "confirm_exit":
        confirm_exit_screen()
    elif st.session_state.screen == "racer_detail":
        show_racer_screen(user)
    elif st.session_state.screen == "edit_rules":
        edit_rules_screen()



# --------------------- EXIT SCREEN ----------------------------------------------------

def confirm_exit_screen():
     st.header("Exit Confirmation")
     st.warning("Are you sure you want to log out from this profile?")

     col1, col2 = st.columns(2)

     with col1:
         if st.button("Continue", key="confirm_exit_yes"):
             st.session_state.logged_in = False
             st.session_state.go = False
             st.session_state.screen = "team"  
             st.rerun()

     with col2:
         if st.button("Abort", key="confirm_exit_no"):
             st.session_state.screen = "team"
             st.rerun()
