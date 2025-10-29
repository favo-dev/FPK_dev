# screens/your_team.py
import ast
import re
import json
import html as _html
from supabase import create_client
import streamlit as st
from logic.functions import safe_rgb_to_hex, hex_to_rgb, normalize_riders, update_user_field, _parse_display_value, color_to_rgb
from screens.show_racers import show_racer_screen

# -------------------------------------------------------------------------------------------
# SUPABASE CLIENT
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
SUPABASE_SERVICE_ROLE_KEY = st.secrets.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def your_team_screen(user):
    st.header("Your Team")

    # --- BEGIN: ensure selected_league and st.session_state.user are fresh ---
    try:
        player_uuid = None
        # prefer st.session_state.user if available
        if isinstance(st.session_state.get("user"), dict) and st.session_state["user"].get("UUID"):
            player_uuid = st.session_state["user"].get("UUID")
        elif isinstance(user, dict) and user.get("UUID"):
            player_uuid = user.get("UUID")

        sel_league = st.session_state.get("selected_league") or (user.get("league") if isinstance(user, dict) else None)

        def _fetch_team_row_for(uuid_val, league_val):
            if not uuid_val or not league_val:
                return None
            try:
                resp = supabase.from_("teams").select("*").eq("UUID", uuid_val).eq("league", league_val).limit(1).execute()
                rows = resp.data or []
                if rows:
                    return rows[0]
            except Exception:
                pass
            try:
                resp = supabase.from_("teams").select("*").eq("uuid", uuid_val).eq("league", league_val).limit(1).execute()
                rows = resp.data or []
                if rows:
                    return rows[0]
            except Exception:
                pass
            return None

        changed = False

        if player_uuid and sel_league:
            team_row = _fetch_team_row_for(player_uuid, sel_league)
            if team_row:
                if st.session_state.get("user") != team_row:
                    st.session_state["user"] = team_row
                    user = team_row
                    changed = True
            else:
                # try to find any team row for this uuid and pick the first as fallback
                try:
                    fallback_rows = supabase.from_("teams").select("*").or_(f"UUID.eq.{player_uuid},uuid.eq.{player_uuid}").limit(10).execute().data or []
                except Exception:
                    fallback_rows = []
                if fallback_rows:
                    first = fallback_rows[0]
                    new_league = first.get("league")
                    st.session_state["selected_league"] = new_league
                    st.session_state["user"] = first
                    user = first
                    changed = True
                else:
                    if st.session_state.get("user") is not None:
                        st.session_state["user"] = None
                        changed = True
        else:
            # no selected league: try to resolve it from passed user or DB
            if player_uuid:
                if isinstance(user, dict) and user.get("league"):
                    st.session_state["selected_league"] = user.get("league")
                    st.session_state["user"] = user
                    changed = True
                else:
                    try:
                        any_rows = supabase.from_("teams").select("*").or_(f"UUID.eq.{player_uuid},uuid.eq.{player_uuid}").limit(10).execute().data or []
                    except Exception:
                        any_rows = []
                    if any_rows:
                        first = any_rows[0]
                        st.session_state["selected_league"] = first.get("league")
                        st.session_state["user"] = first
                        user = first
                        changed = True
    except Exception:
        changed = False

    # If we changed session_state and app already initialized, rerun once so UI rebuilds
    if changed and st.session_state.get("initialized", False):
        st.experimental_rerun()
    # --- END ensure ---

    # If still no user row, inform user and return
    if not isinstance(user, dict) or not user.get("UUID"):
        st.warning("No team selected for this profile. Use 'Change league' or create/join a team.")
        # provide the change league button to help
        col_a, col_b = st.columns([1, 1])
        if col_b.button("Change league", key="change_league_no_user"):
            st.session_state.screen_history = st.session_state.get("screen_history", []) + [st.session_state.get("screen", "team")]
            st.session_state["selected_league"] = None
            st.session_state["screen"] = "leagues"
            st.experimental_rerun()
        return

    # ---------- UI Top band ----------
    st.markdown(
        f"<div style='width:100%;max-width:900px;height:10px;background:linear-gradient(90deg,{safe_rgb_to_hex(user.get('main color','255,0,0'))},{safe_rgb_to_hex(user.get('second color','0,0,255'))});border-radius:12px;box-shadow:0 3px 8px rgba(0,0,0,.15);margin-bottom:1.5rem'></div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style='max-width:700px;
                    background:#333;
                    border-radius:14px;
                    padding:20px;
                    color:white;
                    font-size:1.2rem;
                    display:flex;
                    justify-content:space-around;
                    margin-bottom:1.8rem;
                    box-shadow:0 4px 10px rgba(0,0,0,.4)'>
            <div><strong>Founded in:</strong> {user.get('foundation','N/A')}</div>
            <div><strong>League:</strong> {user.get('league','N/A')}</div>
            <div><strong>Location:</strong> {user.get('where','N/A')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style='max-width:900px;
                    background:#f9f9f9;
                    border-radius:14px;
                    box-shadow:0 4px 12px rgba(0,0,0,.07);
                    padding:20px;
                    display:grid;
                    grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
                    gap:18px;
                    font-size:1.1rem;
                    color:#222;
                    margin-bottom:2.5rem'>
            <div><strong>FF1:</strong> {user.get('ff1','N/A')}</div>
            <div><strong>FMGP:</strong> {user.get('fmgp','N/A')}</div>
            <div><strong>FPK:</strong> {user.get('fm','N/A')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.session_state.setdefault("selected_driver", None)
    st.session_state.setdefault("customizing", False)

    # fetch racers data if needed (kept for backward compatibility)
    try:
        f1_data = supabase.from_("racers_f1_new").select("*").execute().data or []
        mgp_data = supabase.from_("racers_mgp_new").select("*").execute().data or []
    except Exception:
        f1_data = []
        mgp_data = []

    st.subheader("Options")

    st.markdown(""" 
    <style>
    /* Call-ups & Customize: bordo azzurro e testo in grassetto */
    div.stButton>button[key="btn_callups"],
    div.stButton>button[key="open_custom"],
    div.stButton>button[key="close_custom"] {
        font-weight: 700 !important;
        border: 2px solid #1e90ff !important; /* azzurro */
    }

    /* Exit: bordo rosso e testo in grassetto */
    div.stButton>button[key="exit_button"] {
        font-weight: 700 !important;
        border: 2px solid #d93025 !important; /* rosso */
    }

    /* Mantieni testo leggibile anche se lo sfondo è il default di Streamlit */
    div.stButton>button[key="btn_callups"],
    div.stButton>button[key="open_custom"],
    div.stButton>button[key="close_custom"],
    div.stButton>button[key="exit_button"] {
        color: inherit !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # how many teams does this player have?
    user_uuid = user.get("UUID")
    teams_count = 0
    try:
        if user_uuid:
            # try uppercase column
            resp = supabase.from_("teams").select("UUID", count="exact").eq("UUID", user_uuid).execute()
            if getattr(resp, "count", None) is not None:
                teams_count = resp.count or 0
            else:
                teams_count = len(resp.data or [])
            # fallback lowercase if zero
            if teams_count == 0:
                resp2 = supabase.from_("teams").select("uuid", count="exact").eq("uuid", user_uuid).execute()
                if getattr(resp2, "count", None) is not None:
                    teams_count = resp2.count or 0
                else:
                    teams_count = len(resp2.data or [])
    except Exception:
        teams_count = teams_count

    has_multiple_teams = teams_count > 1

    # layout: 4 cols (Call-ups / Customize / Change league / Exit)
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    if col1.button("Call-ups", key="btn_callups"):
        st.session_state.screen = "callups"
        st.rerun()

    if not st.session_state.customizing:
        if col2.button("Customize team", key="open_custom"):
            st.session_state.customizing = True
            st.rerun()
    else:
        if col2.button("Close customization", key="close_custom"):
            st.session_state.customizing = False
            st.rerun()

    # Change league
    if has_multiple_teams:
        if col3.button("Change league", key="change_league"):
            # record history and navigate to leagues selection
            hist = st.session_state.get("screen_history", [])
            hist.append(st.session_state.get("screen", "team"))
            st.session_state["screen_history"] = hist

            # clear selected league so leagues screen shows choices
            st.session_state["selected_league"] = None
            st.session_state["user"] = None
            st.session_state["go"] = False
            # do not set nav_selection to a value unknown to the main nav
            st.session_state["nav_selection"] = None

            st.session_state["screen"] = "leagues"
            st.experimental_rerun()
    else:
        col3.markdown("<div style='opacity:0.6; padding-top:6px; text-align:center'>Change league</div>", unsafe_allow_html=True)

    if col4.button("Exit", key="exit_button"):
        st.session_state.screen = "confirm_exit"
        st.rerun()

    st.markdown("---")

    # customization panel
    if st.session_state.customizing:
        st.markdown("### Customize your profile")
        st.markdown("<div style='border:2px solid #ddd;padding:2rem;border-radius:16px;max-width:700px;background:#fff;box-shadow:0 4px 14px rgba(0,0,0,.05);margin-bottom:3rem'>", unsafe_allow_html=True)
        update_user_field(user, "mail", "New email", supabase, SUPABASE_SERVICE_ROLE_KEY)
        update_user_field(user, "who", "New name", supabase)
        update_user_field(user, "name", "Team name", supabase)
        update_user_field(user, "where", "Location", supabase)
        new_main = st.color_picker("Principal color", value=safe_rgb_to_hex(user.get("main color", [255,255,255])))
        if st.button("Save principal color", use_container_width=True):
            supabase.table("teams").update({"main color": color_to_rgb(new_main)}).eq("who", user["who"]).eq("league", user["league"]).execute()
            st.success("Principal color updated!")
        new_second = st.color_picker("Second color", value=safe_rgb_to_hex(user.get("second color", [0,0,0])))
        if st.button("Save second color", use_container_width=True):
            supabase.table("teams").update({"second color": color_to_rgb(new_second)}).eq("who", user["who"]).eq("league", user["league"]).execute()
            st.success("Secondary color updated!")
        st.markdown("</div>", unsafe_allow_html=True)

    # racers display
    def morpher(name, prefix, idx):
        base = re.sub(r"\W+", "_", name).strip("_").lower() or f"r{idx}"
        return f"{prefix}_{base}_{idx}"

    st.subheader("F1 Drivers")
    raw_f1 = user.get("F1", [])
    f1_riders = normalize_riders(raw_f1)
    if f1_riders:
        num_cols = 4
        for i in range(0, len(f1_riders), num_cols):
            cols = st.columns(num_cols)
            for j, r in enumerate(f1_riders[i:i+num_cols]):
                key = morpher(r, "f1", i+j)
                if cols[j].button(r, key=key):
                    st.session_state.screen_history.append(st.session_state.screen)
                    st.session_state.selected_driver = r
                    st.session_state.selected_category = "F1"
                    st.session_state.screen = "racer_detail"
                    st.rerun()
    else:
        st.write("No F1 riders selected")

    st.subheader("MotoGP Riders")
    raw_mgp = user.get("MotoGP", [])
    mgp_riders = normalize_riders(raw_mgp)
    if mgp_riders:
        num_cols = 4
        for i in range(0, len(mgp_riders), num_cols):
            cols = st.columns(num_cols)
            for j, r in enumerate(mgp_riders[i:i+num_cols]):
                key = morpher(r, "mgp", i+j)
                if cols[j].button(r, key=key):
                    st.session_state.screen_history.append(st.session_state.screen)
                    st.session_state.selected_driver = r
                    st.session_state.selected_category = "MotoGP"
                    st.session_state.screen = "racer_detail"
                    st.rerun()
    else:
        st.write("No MotoGP riders selected")
