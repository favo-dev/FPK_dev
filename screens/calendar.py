import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta
from logic.style import render_table
from logic.utilities import (
    normalize_category,
    render_badges,
    fix_mojibake,
    results_exist,
    sprint_pole,
    get_results,
    format_name,
    build_pilot_colors,
)
import pandas as pd
import pickle
import io
import numpy as np

# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --------------------- CALENDAR SCREEN -------------------------------------
def calendar_screen(user):
    races_f1 = supabase.from_("championship_f1").select("*").execute().data or []
    races_mgp = supabase.from_("championship_mgp").select("*").execute().data or []

    all_races = []
    for race in races_f1:
        race["category"] = "F1"
        all_races.append(race)
    for race in races_mgp:
        race["category"] = "MGP"
        all_races.append(race)

    # --- SANITIZZAZIONE TESTI (fix mojibake / NFC) ---
    for race in all_races:
        # assicurati che name e circuit siano stringhe e riparale se necessario
        race["name"] = fix_mojibake(race.get("name", race.get("ID", "Unknown Race")))
        race["circuit"] = fix_mojibake(race.get("circuit", "Circuit unknown"))
        # when_dt sarà costruito dopo
    # -------------------------------------------------

    for race in all_races:
        race["when_dt"] = datetime.strptime(race["when"], "%Y-%m-%d")
    all_races.sort(key=lambda r: r["when_dt"])

    raceweeks = []
    current_date = None
    current_rw = []
    for race in all_races:
        if race["when_dt"] != current_date:
            if current_rw:
                raceweeks.append(current_rw)
            current_rw = [race]
            current_date = race["when_dt"]
        else:
            current_rw.append(race)
    if current_rw:
        raceweeks.append(current_rw)

    st.title("Race Calendar")
    today = datetime.now().date()
    for i, rw in enumerate(raceweeks, start=1):
        with st.container():
            race_date = rw[0]["when_dt"].date()
            if race_date < today:
                rw_status = "| ✅ Completed"
            elif today <= race_date <= today + timedelta(days=2):
                rw_status = "| 🔄 Undergoing"
            elif today + timedelta(days=2) < race_date <= today + timedelta(days=7):
                rw_status = "| 📅 Upcoming"
            else:
                rw_status = ""
            st.markdown(f"""
                <div style="border:2px solid white;border-radius:10px;padding:15px;margin-bottom:30px;background-color:#222;">
                    <h3 style="margin-top:0;">Raceweek #{i} - {rw[0]['when_dt'].strftime('%d %b %Y')} {rw_status}</h3>
                </div>
            """, unsafe_allow_html=True)

            for race in rw:
                race_name = race.get("name", race.get("ID", "Unknown ID"))
                circuit = race.get("circuit", "Circuit unknown")
                category = race["category"]
                race_id = race.get("ID", f"{category}_{race['when']}")
                race_day = race["when_dt"].date()
                race_tag = race.get("tag")

                # stato come prima...
                if race_day < today:
                    status_text = "| ✅ Completed"
                elif today <= race_day <= today + timedelta(days=2):
                    status_text = "| 🔄 Undergoing"
                elif today + timedelta(days=2) < race_day <= today + timedelta(days=7):
                    status_text = "| 📅 Upcoming"
                else:
                    status_text = ""

                cols = st.columns([0.85, 0.15])
                with cols[0]:
                    # usa le stringhe già "riparate"
                    st.markdown(
                        f"<div style='margin-left:10px'>📍 <b>[{category}]</b> {race_name} — <i>{circuit}</i> {status_text}</div>",
                        unsafe_allow_html=True,
                    )
                with cols[1]:
                    if st.button("Results", key=f"results_{race_id}_{category}"):
                        with st.spinner("Checking results availability..."):
                            try:
                                available = results_exist(race, race_tag)
                            except Exception as e:
                                available = False
                                st.error(f"Errore nel controllo risultati: {e}")
                        if not available:
                            st.warning("Results are not available yet!")
                        else:
                            st.session_state.selected_race = race
                            st.session_state.screen = "race_results"
                            st.rerun()

# --------------------- RACE RESULTS SCREEN ---------------------------------
def race_results_screen(user, race):
    hide_sidebar_style = """
    <style>
    [data-testid="stSidebar"] { display:none; }
    [data-testid="collapsedControl"] { display:none; }
    </style>
    """
    st.markdown(hide_sidebar_style, unsafe_allow_html=True)
    st.header(f"[{race.get('category')}] {race.get('ID')} | Results")

    race_tag = race.get("tag")
    teams = supabase.from_("class").select("*").execute().data or []
    pilot_colors = build_pilot_colors(teams)

    def get_df(data, category):
        if not data:
            return pd.DataFrame(columns=["Position", "Name", "?", "??", "???", "Performance", "Points", "Name with Color"])
        df = pd.DataFrame(data, columns=["Name", "?", "??", "???", "Performance", "Points"])
        df = df.sort_values(by="Performance", ascending=False, na_position="last").reset_index(drop=True)
        df["Performance"] = df["Performance"].apply(lambda x: "DNF" if pd.isna(x) else x)
        df.insert(0, "Position", df.index + 1)
        df["Name with Color"] = df["Name"].apply(lambda n: format_name(n, pilot_colors, category))
        return df

    def get_all(race_tag_local, category_local, file="result_matrix.pkl"):
        try:
            data_bytes = supabase.storage.from_(category_local).download(f"{race_tag_local}/{file}")
            return pickle.load(io.BytesIO(data_bytes))
        except Exception:
            return None

    if race.get("sprint"):
        sprint_data = get_results(race_tag, race["category"], True)
        pole = sprint_pole(race_tag, race["category"])
        if "F1" in race["category"]:
            pole = pole[:-3]
        if sprint_data:
            sprint_data = [[np.nan if x == -99 else x for x in row] for row in sprint_data]
            st.subheader("🏁 Sprint Race Results")
            df_sprint = get_df(sprint_data, race["category"])
            render_table(df_sprint)
            if pole:
                render_badges({"Pole position": pole}, pilot_colors, race.get("category"))
            st.markdown("<div style='margin-bottom:40px'></div>", unsafe_allow_html=True)
        else:
            st.info("No sprint data available.")

    race_data = get_results(race_tag, race["category"], False)
    if race_data:
        race_data = [[np.nan if x == -99 else x for x in row] for row in race_data]
        st.subheader("🏁 Race Results")
        df_race = get_df(race_data, race["category"])
        render_table(df_race)
    else:
        st.info("No race data available.")

    # -------------------------- robust handling for Grand Prix badges --------------------------
    alldata = get_all(race_tag, race["category"])

    # default labels depending on normalized category
    cat_norm = normalize_category(race.get("category") or "")
    if cat_norm == "f1":
        labels = {
            "Pole position": "n/a",
            "Fastest lap": "n/a",
            "Driver of the Day": "n/a",
            "Fastest pit-stop": "n/a",
        }
    else:
        labels = {
            "Pole position": "n/a",
            "Fastest lap": "n/a",
            "Top speed": "n/a",
        }

    # try to find the GP list under several possible keys
    gp_list = None
    if isinstance(alldata, dict):
        for candidate_key in ("Grand Prix", "grand prix", "grand_prix", "GrandPrix", "GP", "gp"):
            if candidate_key in alldata and alldata[candidate_key]:
                gp_list = alldata[candidate_key]
                break

    # if gp_list is present and is a sequence, iterate safely
    if gp_list and isinstance(gp_list, (list, tuple)):
        for d in gp_list:
            try:
                # ensure d is a sequence
                if not isinstance(d, (list, tuple)):
                    continue
                # name (index 0)
                name_fixed = None
                if len(d) > 0 and d[0] is not None:
                    name_fixed = fix_mojibake(d[0]) if isinstance(d[0], str) else d[0]

                # helper to interpret truthy flags robustly
                def is_flag_true(val):
                    if val is True:
                        return True
                    if val is False or val is None:
                        return False
                    sval = str(val).strip().lower()
                    return sval in ("1", "true", "yes", "y", "t")

                # Pole position: d[1] == 1
                if len(d) > 1 and (d[2] == 1 or str(d[1]).strip() == "1") and name_fixed:
                    labels["Pole position"] = name_fixed

                # Fastest lap: d[6] truthy
                if len(d) > 6 and is_flag_true(d[8]) and name_fixed:
                    labels["Fastest lap"] = name_fixed

                # Driver of the Day: d[8] truthy (F1 only)
                if "Driver of the Day" in labels and len(d) > 8 and is_flag_true(d[10]) and name_fixed:
                    labels["Driver of the Day"] = name_fixed

                # Fastest pit-stop / Top speed: d[9] truthy
                if len(d) > 9 and is_flag_true(d[11]) and name_fixed:
                    if "Fastest pit-stop" in labels:
                        labels["Fastest pit-stop"] = name_fixed
                    elif "Top speed" in labels:
                        labels["Top speed"] = name_fixed

            except Exception as e:
                # non blocchiamo l'intero rendering per un singolo record malformato
                print(f"Warning parsing GP row: {e} -- row: {d}")

    # call render_badges always (will show 'n/a' if nothing found)
    if labels:
        render_badges(labels, pilot_colors, race.get("category"))
    # -----------------------------------------------------------------------------------------

    if st.button("🔙 Back"):
        st.session_state.screen = "calendar"
        st.rerun()

