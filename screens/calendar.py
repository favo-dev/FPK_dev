import streamlit as st
from datetime import datetime, timedelta
from supabase import create_client
from logic.functions import (
    normalize_category,
    render_badges,
    fix_mojibake,
    results_exist,
    sprint_pole,
    get_results,
    format_name,
    build_pilot_colors,
    render_table,
)
import pandas as pd
import pickle
import io
import numpy as np

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --------------------- CALENDAR SCREEN ----------------------------------------------------

def calendar_screen(user):
    races_f1 = supabase.from_("championship_f1_new").select("*").execute().data or []
    races_mgp = supabase.from_("championship_mgp_new").select("*").execute().data or []

    all_races = []
    for race in races_f1:
        race["category"] = "F1"
        all_races.append(race)
    for race in races_mgp:
        race["category"] = "MGP"
        all_races.append(race)

    for race in all_races:
        race["name"] = fix_mojibake(race.get("name", race.get("ID", "Unknown Race")))
        race["circuit"] = fix_mojibake(race.get("circuit", "Circuit unknown"))
        race["when_dt"] = datetime.strptime(race["when"], "%Y-%m-%d")

    # ordina tutte le gare cronologicamente
    all_races.sort(key=lambda r: r["when_dt"])

    # raggruppa per raceweek e assegna il numero RW
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

    # assegna numero originale di raceweek (partendo da 1)
    for idx, rw in enumerate(raceweeks, start=1):
        for r in rw:
            r["_rw_number"] = idx

    # identifica gara appena conclusa e prossima gara
    today = datetime.now().date()
    past_rw_idx = None
    next_rw_idx = None
    for idx, rw in enumerate(raceweeks):
        rw_date = rw[0]["when_dt"].date()
        if rw_date <= today:
            past_rw_idx = idx
        elif rw_date > today and next_rw_idx is None:
            next_rw_idx = idx

    # costruisci ordine di visualizzazione (prima la gara appena conclusa e la prossima, poi tutte le altre)
    display_order = []
    seen = set()
    if past_rw_idx is not None:
        display_order.append(raceweeks[past_rw_idx])
        seen.add(past_rw_idx)
    if next_rw_idx is not None and next_rw_idx not in seen:
        display_order.append(raceweeks[next_rw_idx])
        seen.add(next_rw_idx)
    for idx, rw in enumerate(raceweeks):
        if idx not in seen:
            display_order.append(rw)

    st.title("Race Calendar")

    # render dei raceweeks
    for rw in display_order:
        rw_number = rw[0].get("_rw_number", "?")
        race_date = rw[0]["when_dt"].date()
        if race_date < today:
            rw_status = "| ✅ Completed"
        elif today <= race_date <= today + timedelta(days=2):
            rw_status = "| 🔄 Undergoing"
        elif today + timedelta(days=2) < race_date <= today + timedelta(days=7):
            rw_status = "| 📅 Upcoming"
        else:
            rw_status = ""

        with st.container():
            st.markdown(f"""
                <div style="border:2px solid white;border-radius:10px;padding:15px;margin-bottom:30px;background-color:#222;">
                    <h3 style="margin-top:0;">Raceweek #{rw_number} - {rw[0]['when_dt'].strftime('%d %b %Y')} {rw_status}</h3>
                </div>
            """, unsafe_allow_html=True)

            for race in rw:
                race_name = race.get("name", race.get("ID", "Unknown ID"))
                circuit = race.get("circuit", "Circuit unknown")
                category = race["category"]
                race_id = race.get("ID", f"{category}_{race['when']}")

                race_day = race["when_dt"].date()
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
                    st.markdown(
                        f"<div style='margin-left:10px'>📍 <b>[{category}]</b> {race_name} — <i>{circuit}</i> {status_text}</div>",
                        unsafe_allow_html=True,
                    )
                with cols[1]:
                    if st.button("Results", key=f"results_{race_id}_{category}"):
                        with st.spinner("Checking results availability..."):
                            try:
                                available = results_exist(race, race.get("tag"), user)
                            except Exception as e:
                                available = False
                                st.error(f"Errore nel controllo risultati: {e}")
                        if not available:
                            st.warning("Results are not available yet!")
                        else:
                            st.session_state.selected_race = race
                            st.session_state.screen = "race_results"
                            st.rerun()



# --------------------- RACE RESULTS SCREEN ----------------------------------------------------

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
    teams = supabase.from_("teams").select("*").execute().data or []
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
        sprint_data = get_results(race_tag, race["category"], True, user)
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

    race_data = get_results(race_tag, race["category"], False, user)
    if race_data:
        race_data = [[np.nan if x == -99 else x for x in row] for row in race_data]
        st.subheader("🏁 Race Results")
        df_race = get_df(race_data, race["category"])
        render_table(df_race)
    else:
        st.info("No race data available.")

    alldata = get_all(race_tag, race["category"])

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

    gp_list = None
    if isinstance(alldata, dict):
        for candidate_key in ("Grand Prix", "grand prix", "grand_prix", "GrandPrix", "GP", "gp"):
            if candidate_key in alldata and alldata[candidate_key]:
                gp_list = alldata[candidate_key]
                break

    if gp_list and isinstance(gp_list, (list, tuple)):
        for d in gp_list:
            try:
                if not isinstance(d, (list, tuple)):
                    continue
                name_fixed = None
                if len(d) > 0 and d[0] is not None:
                    name_fixed = fix_mojibake(d[0]) if isinstance(d[0], str) else d[0]

                def is_flag_true(val):
                    if val is True:
                        return True
                    if val is False or val is None:
                        return False
                    sval = str(val).strip().lower()
                    return sval in ("1", "true", "yes", "y", "t")

                if len(d) > 1 and (d[2] == 1 or str(d[1]).strip() == "1") and name_fixed:
                    labels["Pole position"] = name_fixed

                if len(d) > 6 and is_flag_true(d[8]) and name_fixed:
                    labels["Fastest lap"] = name_fixed

                if "Driver of the Day" in labels and len(d) > 8 and is_flag_true(d[10]) and name_fixed:
                    labels["Driver of the Day"] = name_fixed

                if len(d) > 8 and is_flag_true(d[9]) and name_fixed:
                    if "Fastest pit-stop" in labels:
                        labels["Fastest pit-stop"] = name_fixed
                    elif "Top speed" in labels:
                        labels["Top speed"] = name_fixed

            except Exception as e:
                print(f"Warning parsing GP row: {e} -- row: {d}")

    if labels:
        render_badges(labels, pilot_colors, race.get("category"))

    # ----------------------------------------------------------------------------------------------

    if st.button("🔙 Back"):
        st.session_state.screen = "calendar"
        st.rerun()
