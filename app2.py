import streamlit as st
from supabase import create_client
from screens.select_league import league_screen


# -------------------------------------------------------------------------------------------
# SUPABASE CLIENT (usato per ensure function)
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def _ensure_session_user_row():
    """
    Ensure st.session_state['user'] contains a teams row matching the current selected_league + UUID
    This is run before rendering league_screen/home_screen to avoid empty views after navigation.
    """
    try:
        sess_user = st.session_state.get("user")
        player_uuid = None
        # prefer UUID as present in session user dict
        if isinstance(sess_user, dict) and sess_user.get("UUID"):
            player_uuid = sess_user.get("UUID")
        else:
            # fallback: maybe stored in session as player_uuid
            player_uuid = st.session_state.get("player_uuid") or (sess_user.get("uuid") if isinstance(sess_user, dict) else None)

        sel_league = st.session_state.get("selected_league")

        # try to fetch exact row for UUID+league (try both column names)
        if player_uuid and sel_league:
            rows = []
            try:
                resp = supabase.from_("teams").select("*").eq("UUID", player_uuid).eq("league", sel_league).limit(1).execute()
                rows = resp.data or []
            except Exception:
                rows = []
            if not rows:
                try:
                    resp = supabase.from_("teams").select("*").eq("uuid", player_uuid).eq("league", sel_league).limit(1).execute()
                    rows = resp.data or []
                except Exception:
                    rows = []

            if rows:
                st.session_state["user"] = rows[0]
                return

        # fallback: if no selected_league but we have uuid, take first available team row
        if player_uuid and not sel_league:
            try:
                any_rows = supabase.from_("teams").select("*").or_(f"UUID.eq.{player_uuid},uuid.eq.{player_uuid}").limit(1).execute().data or []
                if any_rows:
                    st.session_state["user"] = any_rows[0]
                    st.session_state["selected_league"] = any_rows[0].get("league")
            except Exception:
                pass
    except Exception:
        # never crash the whole app for this
        pass


# --------------------------------------------------------------------
# Minimal top-level flow (keep your original login/registration logic here)
# This example assumes you set st.session_state.logged_in somewhere else.
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.screen_history = []
    st.session_state.selected_league = None

if st.session_state.logged_in:
    # ensure session user row is fresh for selected_league before rendering screens
    _ensure_session_user_row()
    # league_screen will route to home_screen (or directly to home if go==True)
    league_screen(st.session_state.get("user"))
else:
    st.title("Login / Registration")
    st.write("Please implement your login/registration here.")
