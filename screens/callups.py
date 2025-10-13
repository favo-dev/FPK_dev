import streamlit as st
from supabase import create_client
from datetime import datetime, timezone
from logic.functions import normalize_riders

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

        if delta.total_seconds() < 0:
            st.markdown(f"""
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

        first_limit = datetime.fromisoformat(champ[0]["limit"])
        if first_limit.tzinfo is None:
            first_limit = first_limit.replace(tzinfo=timezone.utc)

        total_duration = (limit_dt - first_limit).total_seconds()
        elapsed = total_duration - delta.total_seconds()
        progress = max(0, min(1, elapsed / total_duration))

        red = int(255 * progress)
        green = int(255 * (1 - progress))
        color_bar = f"rgb({red}, {green}, 0)"

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
