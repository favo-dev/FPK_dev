import streamlit as st
from supabase import create_client
from datetime import datetime, timezone
from logic.functions import normalize_riders
import pandas as pd

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --------------------- CALL-UP SCREEN ----------------------------------------------------

def callup_screen(user):
    if st.session_state.get("force_rerun", False):
        st.session_state.force_rerun = False
        st.rerun()

    st.header("Call-ups")

    def fetch_team_map():
        """Fetch mapping from class.team -> class.name.
        Falls back to class.ID -> name and then to a generic teams table if necessary.
        This implements exactly the logic you specified: the `team` value stored in
        `calls_f1.team` / `calls_mgp.team` will be looked up against `class.team`.
        Returns a dict {team_key: team_name}.
        """
        # Primary attempt: class table with (team, name)
        try:
            class_rows = supabase.from_("class").select("team,name").execute().data
            if class_rows:
                return {r.get("team"): r.get("name") for r in class_rows if r.get("team") is not None}
        except Exception:
            pass

        # Secondary attempt: class table with (ID, name) - for schemas that use ID as key
        try:
            class_rows = supabase.from_("class").select("ID,name").execute().data
            if class_rows:
                return {r.get("ID"): r.get("name") for r in class_rows}
        except Exception:
            pass

        # Tertiary attempt: teams table (try team or ID as key)
        try:
            teams_rows = supabase.from_("teams").select("team,name,ID").execute().data
            if teams_rows:
                mapping = {}
                for r in teams_rows:
                    key = r.get("team") if r.get("team") is not None else r.get("ID")
                    mapping[key] = r.get("name")
                return mapping
        except Exception:
            pass

        # If nothing found, return empty map
        return {}

    def display_calls_table(table_name, team_map, caption=None):
        """Fetch the calls table, replace team IDs with names using team_map and show as a table.
        """
        try:
            calls = supabase.from_(table_name).select("*").execute().data or []
        except Exception:
            calls = []

        # If no rows, show a small message
        if not calls:
            st.info(f"Nessuna chiamata disponibile per {table_name}.")
            return

        # Replace team ids with names when possible
        processed = []
        for r in calls:
            row = dict(r)  # copy
            team_id = row.get("team")
            # If team is already a dict/object (e.g. supabase foreign relation), try to extract name
            if isinstance(team_id, dict):
                name = team_id.get("name") or team_id.get("Name") or str(team_id)
            else:
                name = team_map.get(team_id, team_id)
            row["team"] = name
            processed.append(row)

        # Reorder columns if possible to show the most relevant first
        df = pd.DataFrame(processed)
        preferred_order = ["team", "first", "second", "reserve", "when"]
        cols = [c for c in preferred_order if c in df.columns] + [c for c in df.columns if c not in preferred_order]
        df = df[cols]

        if caption:
            st.markdown(f"**{caption}**")
        st.dataframe(df)

    def display_race_section(champ_name, champ_code, user_key, callup_key):
        st.subheader(champ_name)


        if "F1" in champ_code:
            champ = supabase.from_("championship_f1").select("*").execute().data
            howmany = 0
            for element in champ:
                if element['number'] >= howmany:
                    howmany = element['number']
            for race in champ:
                if race["status"] is True:
                    next_race = race
                    break

        if "MGP" in champ_code:
            champ = supabase.from_("championship_mgp").select("*").execute().data
            howmany = 0
            for element in champ:
                if element['number'] >= howmany:
                    howmany = element['number']
            for race in champ:
                if race["status"] is True:
                    next_race = race
                    break

        limit_dt = datetime.fromisoformat(next_race["limit"])
        if limit_dt.tzinfo is None:
            limit_dt = limit_dt.replace(tzinfo=timezone.utc)

        now_utc = datetime.now(timezone.utc)
        delta = limit_dt - now_utc

        st.markdown(f"""
            <div style="
                background-color: #2f2f2f;
                color: #eee;
                padding: 12px;
                border-radius: 10px;
                margin-bottom: 10px;
                border: 2px solid red;
                font-weight: bold;
            ">
                Next race: {next_race['ID']} ({next_race['number']}/{howmany})
            </div>
        """, unsafe_allow_html=True)

        remaining_seconds = delta.total_seconds()
        if remaining_seconds < 0:

            days = hours = minutes = seconds = 0
            progress = 1.0
            color_bar = "#dc3545"  
            st.markdown(f"""
                <div style="
                    background-color: #444;
                    border-radius: 20px;
                    overflow: hidden;
                    height: 18px;
                    margin-bottom: 6px;
                ">
                    <div style="
                        width: {100*progress:.1f}%;
                        height: 100%;
                        background-color: {color_bar};
                        transition: width 0.4s ease;
                    "></div>
                </div>
                <div style="color:#ddd; font-weight:600; margin-bottom: 12px;">
                    Remaining time: {days} days, {hours} hours, {minutes} minutes, {seconds} seconds
                </div>
                <div style="
                    background-color: #3a1a1a;
                    color: #ff6666;
                    padding: 10px;
                    border-radius: 8px;
                    margin-bottom: 10px;
                    font-weight: bold;
                ">
                    Time is up - call-ups are no longer available
                </div>
            """, unsafe_allow_html=True)
            return

        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        WEEK = 7 * 24 * 3600
        if remaining_seconds > WEEK:
            progress = 0.0
        else:
            progress = max(0.0, min(1.0, 1.0 - (remaining_seconds / WEEK)))


        TH_2_DAYS = 48 * 3600
        TH_1_DAY = 24 * 3600
        TH_2_HOURS = 2 * 3600
        TH_30_MIN = 30 * 60


        if remaining_seconds <= TH_30_MIN:
            color_bar = "#dc3545" 
        elif remaining_seconds <= TH_2_HOURS:
            color_bar = "#ff9800" 
        elif remaining_seconds <= TH_1_DAY:
            color_bar = "#ffc107" 
        else:
            color_bar = "#28a745" 

        st.markdown(f"""
            <div style="
                background-color: #444;
                border-radius: 20px;
                overflow: hidden;
                height: 18px;
                margin-bottom: 6px;
            ">
                <div style="
                    width: {100*progress:.1f}%;
                    height: 100%;
                    background-color: {color_bar};
                    transition: width 0.4s ease;
                "></div>
            </div>
            <div style="color:#ddd; font-weight:600; margin-bottom: 12px;">
                Remaining time: {days} days, {hours} hours, {minutes} minutes, {seconds} seconds
            </div>
        """, unsafe_allow_html=True)

        drivers = user.get(user_key, [])
        drivers = normalize_riders(drivers)
        if len(drivers) < 3:
            st.error("Devi avere almeno 3 piloti nel team per scegliere First/Second/Reserve.")
            return

        k1 = f"{callup_key}_1"
        k2 = f"{callup_key}_2"
        k3 = f"{callup_key}_3"

        if k1 not in st.session_state or st.session_state[k1] not in drivers:
            st.session_state[k1] = drivers[0]
        if k2 not in st.session_state or st.session_state[k2] not in drivers:
            st.session_state[k2] = drivers[1] if len(drivers) > 1 else drivers[0]
        if k3 not in st.session_state or st.session_state[k3] not in drivers:
            st.session_state[k3] = drivers[2] if len(drivers) > 2 else drivers[0]

        st.selectbox(
            "First " + ("driver" if champ_code == "F1" else "rider"),
            drivers,
            key=k1
        )
        st.selectbox(
            "Second " + ("driver" if champ_code == "F1" else "rider"),
            drivers,
            key=k2
        )
        st.selectbox(
            "Reserve " + ("driver" if champ_code == "F1" else "rider"),
            drivers,
            key=k3
        )

        if st.button(f"Save {champ_name} Call-up"):
            selected = [st.session_state[k1], st.session_state[k2], st.session_state[k3]]
            if len(set(selected)) < 3:
                st.error("You shall select three different pilots")
            else:
                now_str = datetime.now(timezone.utc).isoformat()
                if "f1" in callup_key:
                    supabase.table("calls_f1").update({"first": st.session_state[k1]}).eq("team", user["ID"]).execute()
                    supabase.table("calls_f1").update({"second": st.session_state[k2]}).eq("team", user["ID"]).execute()
                    supabase.table("calls_f1").update({"reserve": st.session_state[k3]}).eq("team", user["ID"]).execute()
                    supabase.table("calls_f1").update({"when": now_str}).eq("team", user["ID"]).execute()
                    st.success("Operation completed!")

                if "mgp" in callup_key:
                    supabase.table("calls_mgp").update({"first": st.session_state[k1]}).eq("team", user["ID"]).execute()
                    supabase.table("calls_mgp").update({"second": st.session_state[k2]}).eq("team", user["ID"]).execute()
                    supabase.table("calls_mgp").update({"reserve": st.session_state[k3]}).eq("team", user["ID"]).execute()
                    supabase.table("calls_mgp").update({"when": now_str}).eq("team", user["ID"]).execute()
                    st.success("Operation completed!")

        st.markdown("""
            <style>
            div.stButton > button {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 0.4em 1.2em;
                border-radius: 8px;
                font-weight: 600;
            }
            div.stButton > button:hover {
                background-color: #0056b3;
                color: white;
            }
            </style>
        """, unsafe_allow_html=True)

        # --- display the calls table under the button ---
        team_map = fetch_team_map()
        if "f1" in callup_key:
            display_calls_table("calls_f1", team_map, caption="Tabella calls_f1")
        if "mgp" in callup_key:
            display_calls_table("calls_mgp", team_map, caption="Tabella calls_mgp")

    display_race_section("F1", "F1", "F1", "f1")

    st.markdown("""
        <hr style="
            border: 1.5px solid #555;
            margin: 40px 0 30px 0;
            border-radius: 5px;
        ">
    """, unsafe_allow_html=True)

    display_race_section("MotoGP", "MGP", "MotoGP", "mgp")

    # -------------------------------------------------------------------------------------------


    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("Back to team"):
        st.session_state.screen = "team"
        st.rerun()
