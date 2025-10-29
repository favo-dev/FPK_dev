# screens/home.py
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

# -------------------------------------------------------------------------------------------
# SUPABASE CLIENT
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def _get_logo_url():
    """
    Try to obtain a signed URL for a private file, fallback to public path.
    Adjust bucket/path to your storage layout.
    """
    try:
        bucket = supabase.storage.from_("figures")
        # Adjust filename/path to your actual stored path
        signed = bucket.create_signed_url("new_favicon.svg", expires_in=60)
        # depending on client, keys differ
        if isinstance(signed, dict):
            return signed.get("signedURL") or signed.get("signed_url") or None
        return None
    except Exception:
        # fallback public path (ensure the file is public in Supabase storage)
        return "https://koffsyfgevaannnmjkvl.supabase.co/storage/v1/object/public/figures/new_favicon.svg"


def home_screen(user):
    # protection: if user is None, show message and avoid crash
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

    options = list(screen_to_nav.values())

    # If nav_selection is not valid, reset to default
    current_nav = st.session_state.get("nav_selection")
    if current_nav not in options:
        st.session_state["nav_selection"] = options[0]
        current_nav = options[0]

    # provide unique key to avoid duplicate-element id
    selection = st.sidebar.selectbox(
        "Navigate",
        options,
        index=options.index(current_nav),
        key="main_nav_select"
    )

    logo_url = _get_logo_url()
    if logo_url:
        try:
            # use_column_width deprecated in some versions; use width param if needed
            st.sidebar.image(logo_url, use_container_width=True)
        except Exception:
            # ignore image loading errors
            pass

    if selection != st.session_state.nav_selection:
        st.session_state.nav_selection = selection
        st.session_state.screen = nav_to_screen.get(selection, "team")
        st.rerun()

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
        show_racer_screen()
    elif st.session_state.screen == "racers":
        racers_screen(user)
    elif st.session_state.screen == "roll":
        roll_screen(user)
    elif st.session_state.screen == "confirm_exit":
        from screens.confirm_exit import confirm_exit_screen  # lazy import to avoid circular problems
        confirm_exit_screen()
    elif st.session_state.screen == "racer_detail":
        show_racer_screen()
