import streamlit as st
from screens.your_team import your_team_screen
from screens.callups import callup_screen
from screens.calendar import calendar_screen, race_results_screen
from screens.standings import standings_screen
from screens.championship import championship_screen, show_rules_screen
from screens.show_racers import show_racer_screen
from screens.racers import racers_screen
from screens.roll import roll_screen
from supabase import create_client
from logic.utilities import go_to_screen


SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def home_screen(user):
    # --- Info utente in alto ---
    st.sidebar.markdown(f"""
    <div style="font-size:24px;">
        {user['who']}<br>
        <i>{user['name']}</i>
    </div>
    """, unsafe_allow_html=True)

    # --- Inizializzazione session state ---
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.screen = "team"
        st.session_state.screen_history = []
        st.session_state.nav_selection = "Your team"  

    # --- Mappature tra screen e nomi visualizzati ---
    screen_to_nav = {
        "team": "Your team",
        "standings": "Standings",
        "championship": "Championship",
        "calendar": "Calendar",
        "racers": "Racers",
        "roll": "Roll of Honor"
    }
    nav_to_screen = {v: k for k, v in screen_to_nav.items()}

    # --- Aggiorna selezione sidebar ---
    if "nav_selection" not in st.session_state:
        st.session_state.nav_selection = screen_to_nav.get(st.session_state.screen, "Your team")

    selection = st.sidebar.selectbox(
        "Navigate",
        list(screen_to_nav.values()),
        index=list(screen_to_nav.values()).index(st.session_state.nav_selection)
    )
    logo_url = "https://koffsyfgevaannnmjkvl.supabase.co/storage/v1/object/sign/figures/new_favicon.svg?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV9hNTU1ZWI5ZC03NmZjLTRiMjUtOGIwMC05ZDQ4ZTRhNGNhMDEiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJmaWd1cmVzL25ld19mYXZpY29uLnN2ZyIsImlhdCI6MTc1ODY0MDMyMiwiZXhwIjoxNzkwMTc2MzIyfQ.9G16n08Io42jvpC8rjVxRf1AzmvRIAAB2gaV_oVSuCI"
    st.sidebar.image(logo_url, use_container_width=True)
    if selection != st.session_state.nav_selection:
        st.session_state.nav_selection = selection
        st.session_state.screen = nav_to_screen[selection]
        st.rerun()

    # --- Visualizza la pagina corretta ---
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
        show_racer_screen()
    elif st.session_state.screen == "racers":
        racers_screen(user)
    elif st.session_state.screen == "roll":
        roll_screen(user)
    elif st.session_state.screen == "confirm_exit":
        confirm_exit_screen()
    elif st.session_state.screen == "racer_detail":
        show_racer_screen()


def confirm_exit_screen():
     st.header("Exit Confirmation")
     st.warning("Are you sure you want to log out from this profile?")

     col1, col2 = st.columns(2)

     with col1:
         if st.button("Continue", key="confirm_exit_yes"):
             st.session_state.logged_in = False
             st.session_state.screen = "team"  
             st.rerun()

     with col2:
         if st.button("Abort", key="confirm_exit_no"):
             st.session_state.screen = "team"
             st.rerun()

