import streamlit as st
import ast
import pickle
import pandas as pd
import io
from datetime import datetime
import json
from pathlib import Path
import streamlit.components.v1 as components
from supabase import create_client
from logic.functions import (
    _estimate_rows_height,
    safe_load_team_list,
    _render_pilot_buttons,
    _render_simple_table_html,
    safe_rgb_to_hex
)

# -------------------------------------------------------------------------------------------
# SUPABASE CLIENT
# -------------------------------------------------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# -------------------------------------------------------------------------------------------
# SESSION STATE INIT
# -------------------------------------------------------------------------------------------
if "screen" not in st.session_state:
    st.session_state.screen = "championship"

if "compute_results_open" not in st.session_state:
    st.session_state.compute_results_open = False

if "compute_category" not in st.session_state:
    st.session_state.compute_category = None

if "compute_race_id" not in st.session_state:
    st.session_state.compute_race_id = None

# --------------------- RULES SCREEN ----------------------------------------------------

def show_rules_screen(rules_list, screen_name):
    """
    Mostra le regole passate in rules_list. Se l'utente corrente è il presidente
    della league corrispondente mostra anche il pulsante "Change rules".
    - screen_name è "rules_f1" oppure "rules_mgp"
    """
    st.title("Rules for " + ("F1" if screen_name == "rules_f1" else "MotoGP"))

    # recupera l'user dalla sessione (la app salva la riga 'teams' in st.session_state['user'])
    user = st.session_state.get("user") or {}
    user_uuid = (user.get("UUID") or user.get("uuid")) if isinstance(user, dict) else None
    league_id = str(user.get("league")) if isinstance(user, dict) and user.get("league") is not None else None

    # check: è il presidente della league?
    is_president = False
    if user_uuid and league_id:
        try:
            lr = supabase.from_("leagues").select("president,ID").eq("ID", league_id).limit(1).execute()
            lrows = lr.data or []
            if lrows:
                league_row = lrows[0]
                # president potrebbe essere stored come UUID o come who; facciamo confronto stringa pulita
                pres = league_row.get("president")
                if pres is not None and str(pres) == str(user_uuid):
                    is_president = True
        except Exception:
            # non blockiamo la visualizzazione se la fetch fallisce
            is_president = False

    if not rules_list:
        st.write("No rules available.")
    else:
        rows = []
        for rule in rules_list:
            if isinstance(rule, dict):
                bonus = rule.get("rule", "N/A")
                value = rule.get("value", "N/A")
            else:
                bonus = rule
                value = ""
            if isinstance(value, (list, tuple)):
                value_str = ", ".join(str(v) for v in value)
            else:
                value_str = str(value)
            rows.append((bonus, value_str))

        container_html = f"""
        <div style='width:100%; background:#222; border-radius:10px; box-shadow:0 4px 10px rgba(0,0,0,0.35); overflow:visible; font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial; padding-bottom:8px;'>
            <div style='background:linear-gradient(90deg,#111,#0e0e0e); padding:8px 12px; font-weight:700; font-size:13px; color:#fff;'>Rules</div>
            { _render_simple_table_html(rows) }
        </div>
        """

        est_height, needs_scroll = _estimate_rows_height(rows,
                                                         container_width_px=900,
                                                         left_pct=0.70,
                                                         right_pct=0.30,
                                                         avg_char_px=7.0,
                                                         line_height_px=18,
                                                         vertical_padding_px=28,
                                                         min_h=90,
                                                         max_h=8000,
                                                         safety_mul=1.15,
                                                         per_row_padding_px=1)

        components.html(container_html, height=est_height, scrolling=needs_scroll)

    # pulsanti in basso: Go back sempre; Change rules solo per il presidente
    cols = st.columns([1, 1])
    with cols[0]:
        if st.button("Go back", key=f"rules_go_back_{screen_name}"):
            st.session_state.screen = "championship"
            st.rerun()

    with cols[1]:
        if is_president:
            label = "Change rules"
            # key unica basata su screen_name per evitare collisioni tra F1/MotoGP
            if st.button(label, key=f"change_rules_btn_{screen_name}"):
                # imposta lo stato per entrare in modalità editing; il consumer dovrà gestire 'edit_rules'
                st.session_state["rules_edit_target"] = screen_name  # "rules_f1" o "rules_mgp"
                st.session_state["screen"] = "edit_rules"
                # puoi anche passare le regole correnti in session_state se vuoi prepopolare il form:
                st.session_state["rules_edit_data"] = rules_list
                st.rerun()
        else:
            # spazio vuoto per mantenere layout coerente (opzionale)
            st.markdown("<div style='opacity:.6; text-align:center; padding-top:6px'>Only president can change</div>", unsafe_allow_html=True)

def check_storage_folder(category: str, race_id: str):
    """
    Returns (is_empty: bool, tag: str | None, error: str | None)
    """

    table_name = (
        "championship_f1_new"
        if category == "F1"
        else "championship_mgp_new"
    )

    bucket_name = "F126" if category == "F1" else "MGP26"

    try:
        # Recupero tag dalla tabella campionato
        resp = (
            supabase
            .from_(table_name)
            .select("tag")
            .eq("ID", race_id)
            .single()
            .execute()
        )

        if not resp.data or "tag" not in resp.data:
            return False, None, "Race tag not found."

        tag = resp.data["tag"]

        # Lista contenuto cartella
        files = (
            supabase
            .storage
            .from_(bucket_name)
            .list(path=tag)
        )

        # Cartella vuota = nessun file
        is_empty = not files or len(files) == 0

        return is_empty, tag, None

    except Exception as e:
        return False, None, str(e)

def user_is_president(user_uuid: str, league_id: str) -> bool:
    """Ritorna True se user_uuid corrisponde al campo 'president' della league con ID = league_id."""
    if not user_uuid or not league_id:
        return False
    try:
        lr = supabase.from_("leagues").select("president,ID").eq("ID", league_id).limit(1).execute()
        lrows = lr.data or []
        if not lrows:
            return False
        pres = lrows[0].get("president")
        return pres is not None and str(pres) == str(user_uuid)
    except Exception:
        # non bloccare l'UI in caso di problemi con la fetch
        return False

def compute_results_menu(league_id: str):

    category = st.selectbox(
        "Select category",
        ["F1", "MotoGP"],
        index=0 if st.session_state.compute_category is None
        else ["F1", "MotoGP"].index(st.session_state.compute_category),
        key="compute_category_select"
    )

    if st.session_state.compute_category != category:
        st.session_state.compute_category = category
        st.session_state.compute_race_id = None

    table_name = (
        "championship_f1_new"
        if category == "F1"
        else "championship_mgp_new"
    )

    try:
        races_resp = (
            supabase
            .from_(table_name)
            .select("ID")
            .order("ID")
            .execute()
        )
        races = [r["ID"] for r in (races_resp.data or [])]
    except Exception as e:
        st.error(f"Error loading races: {e}")
        return

    if not races:
        st.warning("No races available.")
        return

    race_index = 0
    if (
        st.session_state.compute_race_id is not None
        and st.session_state.compute_race_id in races
    ):
        race_index = races.index(st.session_state.compute_race_id)

    race_id = st.selectbox(
        "Select race",
        races,
        index=race_index,
        key="compute_race_select"
    )

    st.session_state.compute_race_id = race_id

    # ---- STORAGE CHECK ----
    is_empty, tag, error = check_storage_folder(category, race_id)

    if error:
        st.error(error)
        return

    if is_empty:
        st.warning(
            f"The storage folder '{tag}' is empty. "
            "Please upload the required files before computing results."
        )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel"):
            st.session_state.compute_results_open = False
            st.session_state.compute_category = None
            st.session_state.compute_race_id = None
            st.rerun()

    with col2:
        if st.button("Confirm compute", disabled=is_empty):
            raceweek_computer(tag, category, league_id)

            st.success(f"Results computed for {category} – race {race_id}")

def raceweek_computer(tag, cat, league):
    url = SUPABASE_URL
    key = SUPABASE_ANON_KEY
    if cat == "MotoGP":
        cat = "MGP"
    user = st.session_state.get("user") or {}
    user_uuid = (user.get("UUID") or user.get("uuid")) if isinstance(user, dict) else None

    # -----------------------
    # Bucket mapping
    # -----------------------
    
    bucket_map = {
        "F1": "F126",
        "MGP": "MGP26"
    }

    if cat not in bucket_map:
        raise ValueError(f"Category not valid: {cat}")

    bucket_name = bucket_map[cat]

    # -----------------------
    # Download pickle
    # -----------------------
    
    file_path = f"{tag}/result_matrix.pkl"

    try:
        file_bytes = supabase.storage.from_(bucket_name).download(file_path)
    except Exception as e:
        raise FileNotFoundError(
            f"Impossibile scaricare {file_path} dal bucket {bucket_name}"
        ) from e

    results = pickle.loads(file_bytes)

    # -----------------------
    # Table mapping
    # -----------------------
    
    table_map = {
        "F1": {
            "marks": "marks_f1_new",
            "rules": "rules_f1_new",
            "calls": "calls_f1_hist"
    },
        "MGP": {
            "marks": "marks_mgp_new",
            "rules": "rules_mgp_new",
            "calls": "calls_mgp_hist"
        }
    }

    marks_table = table_map[cat]["marks"]
    rules_table = table_map[cat]["rules"]
    calls_table = table_map[cat]["calls"]
    

    # -----------------------
    # Fetch tables
    # -----------------------
    
    marks_response = supabase.table(marks_table).select("*").execute()
    rules_response = (supabase.table(rules_table).select("*").order("rule", desc=False).execute())
    calls_response = supabase.table(calls_table).select("*").execute()
    starter_number_response = supabase.table("leagues").select("*").execute()

    marks = marks_response.data
    rules = rules_response.data
    rules = [item for item in rules if item["league"] == league]
    calls = calls_response.data
    calls = [item for item in calls if item["tag"] == tag and item["league"] == league]
    starter_number = starter_number_response.data
    starter_number = [item for item in starter_number if item["ID"] == league]
    
    # -----------------------
    # Functions
    # -----------------------
    
    def assign_points(drivers, prules, index=0, points=None):
            if points is None:
                points = []

    
            if index >= len(drivers):
                return points

            driver = drivers[index]
            try:
                pos = int(driver[7])
                if 1 <= pos <= len(prules):
                    points.append(prules[pos - 1])
                else:
                    points.append(0)  
            except (ValueError, IndexError):
                points.append(0)
                
    
            return assign_points(drivers, prules, index + 1, points)
        
    # -------------------------------------------------------------------------
    
    def build_filtered_final(final_results, calls_dict):
        filtered_final = []
    
        race_map = {racer[0]: racer for racer in final_results}

        used_drivers = set()

        for call in calls_dict.values():

            for starter in call["starters"]:
                racer = race_map.get(starter)

                if racer is None:
                    continue

                if racer[1] != 99:
                    if starter not in used_drivers:
                        filtered_final.append(racer)
                        used_drivers.add(starter)

                else:
                    for reserve in call["reserves"]:
                        reserve_racer = race_map.get(reserve)

                        if reserve_racer is None:
                            continue

                        if reserve_racer[1] != 99 and reserve not in used_drivers:
                            filtered_final.append(reserve_racer)
                            used_drivers.add(reserve)
                            break


        filtered_final = sorted(
            filtered_final,
            key=lambda row: (-row[-1], row[1])
            )

        return filtered_final
    
    # -------------------------------------------------------------------------    
    
    def update_record_lists(player_id, category, league, tag):
        if player_id is None: 
            return
        table = "league_mgp_stats" if category == "MGP" else "league_f1_stats"
        tag = tag + str(datetime.now().year)[2:]
        response = (
            supabase
            .table(table)
            .select("convocations")
            .eq("player_id", player_id)
            .eq("league_id", league)
            .single()
            .execute()
            )

        if not response.data:
            return  

        tags = response.data.get("convocations") or []

 
        if tag in tags:
            tags.remove(tag)

 
        tags.append(tag)

 
        (
            supabase
            .table(table)
            .update({"convocations": tags})
            .eq("player_id", player_id)
            .eq("league_id", league)
            .execute()
            )
    
    # -------------------------------------------------------------------------
        
    def update_sub_lists(player_id, category, league, tag):
        if player_id is None: 
            return
        table = "league_mgp_stats" if category == "MGP" else "league_f1_stats"
        tag = tag + str(datetime.now().year)[2:]
        response = (
            supabase
            .table(table)
            .select("sub")
            .eq("player_id", player_id)
            .eq("league_id", league)
            .single()
            .execute()
            )

        if not response.data:
            return  

        tags = response.data.get("sub") or []

 
        if tag in tags:
            tags.remove(tag)

 
        tags.append(tag)

 
        (
            supabase
            .table(table)
            .update({"sub": tags})
            .eq("player_id", player_id)
            .eq("league_id", league)
            .execute()
            )
    
    # -------------------------------------------------------------------------
    
    def update_dnf(player_id, category, league, tag):
        if player_id is None:
            return

        table = "league_mgp_stats" if category == "MGP" else "league_f1_stats"
        tag = f"{tag}{str(datetime.now().year)[2:]}"

        res = (
            supabase
            .table(table)
            .select("dnf")
            .eq("player_id", player_id)
            .eq("league_id", league)
            .single()
            .execute()
            )

        if not res.data:
            return

        tags = res.data.get("dnf") or []

        if tag in tags:
            tags.remove(tag)

        tags.append(tag)
        
        (
            supabase
            .table(table)
            .update({"dnf": tags})
            .eq("player_id", player_id)
            .eq("league_id", league)
            .execute()
            )
    
    # -------------------------------------------------------------------------
        
    def update_podiums(player_id, category, league, tag):
        if player_id is None:
            return

        table = "league_mgp_stats" if category == "MGP" else "league_f1_stats"
        tag = f"{tag}{str(datetime.now().year)[2:]}"

        res = (
            supabase
            .table(table)
            .select("podiums")
            .eq("player_id", player_id)
            .eq("league_id", league)
            .single()
            .execute()
            )

        if not res.data:
            return

        tags = res.data.get("podiums") or []

        if tag in tags:
            tags.remove(tag)

        tags.append(tag)
        
        (
            supabase
            .table(table)
            .update({"podiums": tags})
            .eq("player_id", player_id)
            .eq("league_id", league)
            .execute()
            )
    
    # -------------------------------------------------------------------------
        
    def update_wins(player_id, category, league, tag):
        if player_id is None:
            return

        table = "league_mgp_stats" if category == "MGP" else "league_f1_stats"
        tag = f"{tag}{str(datetime.now().year)[2:]}"

        res = (
            supabase
            .table(table)
            .select("wins")
            .eq("player_id", player_id)
            .eq("league_id", league)
            .single()
            .execute()
            )

        if not res.data:
            return

        tags = res.data.get("wins") or []

        if tag in tags:
            tags.remove(tag)

        tags.append(tag)
        
        (
            supabase
            .table(table)
            .update({"wins": tags})
            .eq("player_id", player_id)
            .eq("league_id", league)
            .execute()
            )
    
    # -------------------------------------------------------------------------

    def cancel_this_tag(player_id, cat, league, tag):
        table = "league_mgp_stats" if cat == "MGP" else "league_f1_stats"
        tag = f"{tag}{str(datetime.now().year)[2:]}"

        res = (
            supabase
            .table(table)
            .select("convocations, sub, dnf, wins, podiums")
            .eq("player_id", player_id)
            .eq("league_id", league)
            .single()
            .execute()
            )
        
        if not res.data:
            return

        updates = {}

        for field in ("convocations", "sub", "dnf", "wins", "podiums"):
            tags = res.data.get(field) or []
            if tag in tags:
                tags.remove(tag)
                updates[field] = tags

        if updates:
            (
                supabase
                .table(table)
                .update(updates)
                .eq("player_id", player_id)
                .eq("league_id", league)
                .execute()
                )
            
            
    # -------------------------
    # ------ SPRINT RACE
    # -------------------------
    
    
    SPRINT_FINAL = []
    if results.get('Sprint race'):
        sprint_points = []
        for driver in results['Sprint race']:
            sprint_points.append(driver[0])
        
        POS = []
        for driver in results['Sprint race']:
            try:
                POS.append(int(driver[7]))
            except:
                POS.append(99)
                      
        POINTS = []
        if cat == "F1":
            prules = ast.literal_eval(rules[14]["value"])
            POINTS = assign_points(results['Sprint race'], prules)
        
        if cat == "MGP":
            prules = ast.literal_eval(rules[11]["value"])
            POINTS = assign_points(results['Sprint race'], prules)
       
        TOT = []
        
        if cat == "F1":
            for driver in results['Sprint race']:
                tot = 0
                if 'Q2' in driver[1]:
                    tot += float(rules[10].get("value"))
                if 'Q3' in driver[1]:
                    tot += float(rules[11].get("value"))
                if driver[2]:
                    tot += float(rules[9].get("value"))
                if driver[3]:
                    tot += float(rules[12].get("value"))
                if driver[4]:
                    tot += float(rules[0].get("value"))
                if driver[5]:
                    tot += float(rules[16].get("value"))
                try:
                    if float(driver[6]) < 0:
                        tot += int(driver[6]) * float(rules[8].get("value"))
                except:
                    tot += 0
                try:
                    if float(driver[6]) >= 0 and float(driver[7]) <= float(rules[5].get("value")):
                        tot += int(driver[6]) * float(rules[8].get("value"))
                except:
                    tot += 0
                TOT.append(tot)
                
        if cat == "MGP":
            for driver in results['Sprint race']:
                tot = 0
                if 'Q2' in driver[1]:
                    tot += float(rules[7].get("value"))
                if driver[2]:
                    tot += float(rules[6].get("value"))
                if driver[3]:
                    tot += float(rules[8].get("value"))
                if driver[4]:
                    tot += float(rules[0].get("value"))
                if driver[5]:
                    tot += float(rules[14].get("value"))
                try:
                    if float(driver[6]) < 0:
                        tot += int(driver[6]) * float(rules[5].get("value"))
                except:
                    tot += 0
                try:
                    if float(driver[6]) >= 0 and float(driver[7]) <= float(rules[3].get("value")):
                        tot += int(driver[6]) * float(rules[5].get("value"))
                except:
                    tot += 0
                if driver[8]:
                    tot += float(rules[1].get("value"))
                if driver[9]:
                    tot += float(rules[13].get("value"))
                TOT.append(tot)
            
        PERF = [x + y for x, y in zip(POINTS, TOT)]
        
        FINAL = [[a, b, c, d, e] for [a, b, c, d, e] in zip(sprint_points, POS, POINTS, TOT, PERF)]

        for driver in FINAL:
            if int(driver[1]) == 99:
                driver[4] = -99        
        SPRINT_FINAL = sorted(FINAL, key=lambda row: (-row[-1], row[1]))
            
        
        
    # ------ MAIN RACE ----------------------------------------------------------

    points = []
    for driver in results['Grand Prix']:
        points.append(driver[0])
        
    POS = []
    for driver in results['Grand Prix']:
        try:
                POS.append(int(driver[7]))
        except:
                POS.append(99)
        
    POINTS = []
    for driver in results['Grand Prix']:
        for mark in marks:
            if driver[0] in mark.get('ID'):
                try:
                    POINTS.append(float(mark.get(tag)))
                except:
                    try:
                        check = int(driver[7])
                        POINTS.append(6)
                    except:
                        POINTS.append(-99)
    
    TOT = []
     
    if cat == "F1":
        for driver in results['Grand Prix']:
            tot = 0
            if 'Q2' in driver[1]:
                tot += float(rules[10].get("value"))
            if 'Q3' in driver[1]:
                tot += float(rules[11].get("value"))
            if driver[2]:
                tot += float(rules[9].get("value"))
            if driver[3]:
                tot += float(rules[12].get("value"))
            if driver[4]:
                tot += float(rules[0].get("value"))
            if driver[5]:
                tot += float(rules[16].get("value"))
            try:
                if float(driver[6]) < 0:
                    tot += int(driver[6]) * float(rules[8].get("value"))
            except:
                tot += 0
            try:
                if float(driver[6]) >= 0 and float(driver[7]) <= float(rules[5].get("value")):
                    tot += int(driver[6]) * float(rules[8].get("value"))
            except:
                tot += 0
            if driver[8]:
                tot += float(rules[3].get("value"))
            if driver[9]:
                tot += float(rules[13].get("value"))
            if driver[10]:
                tot += float(rules[2].get("value"))
            if driver[11]:
                tot += float(rules[1].get("value"))

            if driver[12]:
                tot += float(rules[6].get("value"))
            TOT.append(tot)
            
        PERF = [x + y for x, y in zip(POINTS, TOT)]
        
        
    if cat == "MGP":
        for driver in results['Grand Prix']:
            tot = 0
            if 'Q2' in driver[1]:
                tot += float(rules[7].get("value"))
            if driver[2]:
                tot += float(rules[6].get("value"))
            if driver[3]:
                tot += float(rules[9].get("value"))
            if driver[4]:
                tot += float(rules[0].get("value"))
            if driver[5]:
                tot += float(rules[14].get("value"))
            try:
                if float(driver[6]) < 0:
                    tot += int(driver[6]) * float(rules[5].get("value"))
            except:
                tot += 0
            try:
                if float(driver[6]) >= 0 and float(driver[7]) <= float(rules[3].get("value")):
                    tot += int(driver[6]) * float(rules[5].get("value"))
            except:
                tot += 0
            if driver[8]:
                tot += float(rules[1].get("value"))
            if driver[9]:
                tot += float(rules[13].get("value"))
            if driver[10]:
                tot += float(rules[9].get("value"))
            if driver[11]:
                tot += float(rules[10].get("value"))
            TOT.append(tot)
            
        PERF = [x + y for x, y in zip(POINTS, TOT)]

    FINAL = [[a, b, c, d, e] for [a, b, c, d, e] in zip(points, POS, POINTS, TOT, PERF)]

    for driver in FINAL:
            if int(driver[1]) == 99:
                driver[4] = -99

    RACE_FINAL = sorted(FINAL, key=lambda row: (-row[-1], row[1]))

    
    calls_dict = {}

    for row in calls:
        uuid = row["uuid"]

        calls_dict[uuid] = {
            "starters": [
                row.get("first"),
                row.get("second"),
                row.get("third"),
                row.get("fourth"),
                ],
            "reserves": [
                row.get("reserve"),
                row.get("reserve_two"),
                row.get("reserve_three"),
                row.get("reserve_four"),
                ]
            }
    
    FILTERED_SPRINT_FINAL = build_filtered_final(SPRINT_FINAL, calls_dict)
    
    FILTERED_RACE_FINAL = build_filtered_final(RACE_FINAL, calls_dict)
    
    if cat == "F1":
        sprint_race_points = ast.literal_eval(rules[15]["value"])
        race_points = ast.literal_eval(rules[4]["value"])
    
    if cat == "MGP":
        sprint_race_points = ast.literal_eval(rules[12]["value"])
        race_points = ast.literal_eval(rules[2]["value"])

    while len(sprint_race_points) < len(FILTERED_SPRINT_FINAL):
        sprint_race_points.append(0)

    for i, racer in enumerate(FILTERED_SPRINT_FINAL):
        racer.append(sprint_race_points[i])
        
    while len(race_points) < len(FILTERED_RACE_FINAL):
        race_points.append(0)

    for i, racer in enumerate(FILTERED_RACE_FINAL):
        racer.append(race_points[i])
    



    for racer in results["Grand Prix"]:
        cancel_this_tag(racer[0], cat, league, tag)
        
    for racer in calls:
        update_record_lists(racer["first"], cat, league, tag)
        update_record_lists(racer["second"], cat, league, tag)
        update_record_lists(racer["third"], cat, league, tag)
        update_record_lists(racer["fourth"], cat, league, tag)
        for driver in FILTERED_RACE_FINAL:
            if racer["reserve"] == driver[0]:
                update_sub_lists(racer["reserve"], cat, league, tag)
            if racer["reserve_two"] == driver[0]:
                update_sub_lists(racer["reserve"], cat, league, tag)
            if racer["reserve_three"] == driver[0]:
                update_sub_lists(racer["reserve"], cat, league, tag)
            if racer["reserve_four"] == driver[0]:
                update_sub_lists(racer["reserve"], cat, league, tag)
                
    finished_drivers = {driver[0] for driver in FILTERED_RACE_FINAL}
    for racer in calls:
        for key in ("first", "second", "third", "fourth"):
            pid = racer.get(key)

            if pid is None:
                continue

            if pid not in finished_drivers:
                update_dnf(pid, cat, league, tag)
    
    update_podiums(FILTERED_RACE_FINAL[0][0], cat, league, tag)
    update_podiums(FILTERED_RACE_FINAL[1][0], cat, league, tag)
    update_podiums(FILTERED_RACE_FINAL[2][0], cat, league, tag)
    update_wins(FILTERED_RACE_FINAL[0][0], cat, league, tag)
            
    teams = supabase.table("teams").select("*").execute()
    teams = teams.data
    
    if cat == "F1":
        table = "points_per_race_f1"
        points = supabase.table(table).select("*").execute()
        points = points.data
    elif cat == "MGP":
        table = "points_per_race_mgp"
        points = supabase.table(table).select("*").execute()
        points = points.data
        
    for team in teams:
        if team["league"] == league:
            tot = 0           
            if cat == "F1":
                pilots = ast.literal_eval(team["F1"])
            elif cat == "MGP":
                pilots =  ast.literal_eval(team["MotoGP"])
            for pilot in pilots:
                for driver in FILTERED_SPRINT_FINAL:
                    if driver[0] == pilot:
                        tot = tot + driver[5]
                        continue
                for driver in FILTERED_RACE_FINAL:
                    if driver[0] == pilot:
                        tot = tot + driver[5]
                        continue

            response = (
                supabase
                .table(table)
                .update({
                    tag: float(tot)
                })
                .eq("league", league)
                .eq("id", team["UUID"])
                 .execute()
            ) 

            if cat == "F1":
                category = "F126"
            elif cat == "MGP":
                category = "MGP26"
            else:
                raise ValueError(f"cat non valida: {cat}")
    
            filename = f"sprint_standings_{league}.pkl"
            storage_path = f"{tag}/{filename}"

            buffer = io.BytesIO()
            pickle.dump(FILTERED_SPRINT_FINAL, buffer, protocol=pickle.HIGHEST_PROTOCOL)
            file_bytes = buffer.getvalue()

    
            supabase.storage.from_(category).upload(
                storage_path,
                file_bytes,
                file_options={
                    "content-type": "application/octet-stream",
                    "upsert": "true"
                }
            )
    
    return    

# --------------------- CHAMPIONSHIP SCREEN ----------------------------------------------------

def championship_screen(user):
    loading_placeholder = st.empty()
    loading_placeholder.info("Loading...")

    league_id = str(user.get("league"))
    user_uuid = user.get("UUID") or user.get("uuid")

    # Recupera tutti i team della league
    teams = supabase.from_("teams").select("*").eq("league", league_id).execute().data or []
    not_you = [team for team in teams if team.get("who") != user.get("who")]

    # Recupera le regole F1/MotoGP per la league
    rules_f1 = supabase.from_("rules_f1_new").select("*").eq("league", league_id).execute().data or []
    rules_mgp = supabase.from_("rules_mgp_new").select("*").eq("league", league_id).execute().data or []

    loading_placeholder.empty()

    st.title("Other teams")

    # Visualizza tutti gli altri team
    for team in not_you:
        with st.expander(f"{team.get('name','N/A')} - {team.get('who','N/A')}"):
            main_hex = safe_rgb_to_hex(team.get("main color", [0,0,0]))
            second_hex = safe_rgb_to_hex(team.get("second color", [100,100,100]))
            st.markdown(
                f"""
                <div style='display: flex; align-items: center; gap: 1rem; width:100%;'>
                    <div style='width: 100%; height: 10px; background-color: {main_hex}; border: 2px solid {second_hex}; border-radius: 4px;'></div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.markdown(f"**Founded in**: {team.get('foundation', 'N/A')}")
            st.markdown(f"**Location**: {team.get('where', 'N/A')}")
            st.markdown(f"**FF1**: {team.get('ff1', 'N/A')}")
            st.markdown(f"**Fmgp**: {team.get('fmgp', 'N/A')}")
            st.markdown(f"**FPK**: {team.get('fm', 'N/A')}")
            st.markdown(f"**Mail:** {team.get('mail','N/A')}")

            st.markdown("**F1 team:**")
            f1_team = safe_load_team_list(team.get("F1", []))
            if f1_team:
                _render_pilot_buttons(f1_team, "f1", team.get('ID'))

            st.markdown("**MotoGP team:**")
            mgp_team = safe_load_team_list(team.get("MotoGP", []))
            if mgp_team:
                _render_pilot_buttons(mgp_team, "mgp", team.get('ID'))

    st.title("Rules")

    # Controlla se l'utente è presidente
    is_president = user_is_president(user_uuid, league_id)

    # Pulsanti per regole
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Rules - F1", key="rules_f1_button"):
            st.session_state.screen = "rules_f1"
            st.session_state.rules_data = rules_f1
            st.rerun()
    with col2:
        if st.button("Rules - MotoGP", key="rules_mgp_button"):
            st.session_state.screen = "rules_mgp"
            st.session_state.rules_data = rules_mgp
            st.rerun()

    # Bottone Compute results visibile solo al presidente
    if is_president:
        st.markdown("")  # spazio
        st.title("Compute raceweek")
        
        if st.button("Compute results", key="compute_results_btn"):
            st.session_state.compute_results_open = True
            st.rerun()

    # Mostra il menu compute results se aperto
    if is_president and st.session_state.compute_results_open:
        compute_results_menu(league_id)

def edit_rules_screen():
    """
    Schermata per modificare le rules (F1 o MotoGP) per la league dell'utente.
    Si aspetta che st.session_state["rules_edit_target"] sia "rules_f1" o "rules_mgp"
    e che st.session_state["user"] contenga la riga 'teams' con 'league' e 'UUID'.
    """

    # --- safety checks / contesto ---
    user = st.session_state.get("user") or {}
    user_uuid = (user.get("UUID") or user.get("uuid")) if isinstance(user, dict) else None
    league_id = str(user.get("league")) if isinstance(user, dict) and user.get("league") is not None else None
    target = st.session_state.get("rules_edit_target")  # "rules_f1" o "rules_mgp"
    if not target or target not in ("rules_f1", "rules_mgp"):
        st.error("Editing target non definito. Torna indietro e riprova.")
        if st.button("Go back"):
            st.session_state.screen = "championship"
            st.rerun()
        return

    # only president may edit - double-check
    is_president = False
    if user_uuid and league_id:
        try:
            lr = supabase.from_("leagues").select("president,ID").eq("ID", league_id).limit(1).execute()
            lrows = lr.data or []
            if lrows:
                league_row = lrows[0]
                pres = league_row.get("president")
                if pres is not None and str(pres) == str(user_uuid):
                    is_president = True
        except Exception:
            is_president = False

    if not is_president:
        st.error("Only the league president can change the rules.")
        if st.button("Back"):
            st.session_state.screen = "championship"
            st.rerun()
        return

    # choose table name
    table_name = "rules_f1_new" if target == "rules_f1" else "rules_mgp_new"
    st.title("Edit rules — " + ("F1" if target == "rules_f1" else "MotoGP"))

    # fetch current rules rows for this league
    try:
        rows_resp = supabase.from_(table_name).select("*").eq("league", league_id).execute()
        rules_rows = rows_resp.data or []
    except Exception as e:
        st.error(f"Error fetching rules: {e}")
        rules_rows = []

    # define special multi-value fields (accept arrays)
    MULTI_FIELDS = {
        "Grand Prix points distribution",
        "Sprint Race points distribution"
    }

    # Build UI inside a form to batch validate and submit
    form = st.form(key=f"edit_rules_form_{table_name}")
    inputs = []
    # preserve order: iterate rules_rows
    total = len(rules_rows)
    for i, r in enumerate(rules_rows):
        rule_label = str(r.get("rule") or r.get("name") or f"rule_{i}")
        raw_value = r.get("value")
        # try to detect if stored as JSON/list
        if isinstance(raw_value, (list, tuple)):
            current_value = raw_value
        else:
            # try parse JSON or Python-literal if string
            if isinstance(raw_value, str):
                s = raw_value.strip()
                try:
                    parsed = json.loads(s)
                    current_value = parsed
                except Exception:
                    try:
                        parsed = ast.literal_eval(s)
                        current_value = parsed
                    except Exception:
                        current_value = s
            else:
                current_value = raw_value

        key_base = f"editrules_{table_name}_{i}"
        if rule_label in MULTI_FIELDS:
            # show text area with JSON representation of list
            if isinstance(current_value, (list, tuple)):
                prefill = json.dumps(current_value)
            else:
                # if it's a plain number or string, show as single-element list string as reminder
                prefill = json.dumps(current_value) if not (isinstance(current_value, str) and current_value == "") else "[]"

            form.markdown(f"**{rule_label}**")
            val = form.text_area(f"Values (JSON array) — max length 22", value=prefill, key=key_base + "_multi", help="Insert a JSON array of numbers, e.g. [25,18,15,...]")
            inputs.append({
                "id": r.get("id"),
                "rule": rule_label,
                "type": "multi",
                "raw": val,
                "orig": r
            })
        else:
            # numeric single value: try to get float default
            default_num = None
            if isinstance(current_value, (int, float)):
                default_num = float(current_value)
            else:
                # try to parse numeric from str
                try:
                    default_num = float(str(current_value))
                except Exception:
                    default_num = 0.0
            form.markdown(f"**{rule_label}**")
            # show number_input WITHOUT repeating the label; restrict to 2 decimals in the UI
            # key stays unique per row
            val = form.number_input(
                "",  # label omitted because already shown above
                value=default_num,
                key=key_base + "_num",
                format="%.2f",
                step=0.01
            )
            inputs.append({
                "id": r.get("id"),
                "rule": rule_label,
                "type": "numeric",
                "raw": val,
                "orig": r
            })

        # inserisci un divisore tra questo campo e il successivo, tranne dopo l'ultimo
        if i < total - 1:
            form.markdown("<hr style='border:0; height:1px; background:#444; margin:12px 0;'/>", unsafe_allow_html=True)

    # Add buttons
    colc1, colc2 = form.columns([1, 1])
    with colc1:
        cancel = form.form_submit_button("Cancel")
    with colc2:
        confirm = form.form_submit_button("Confirm changes")

    # Handle Cancel
    if cancel:
        # restore to rules display screen
        st.session_state.screen = target  # e.g. "rules_f1" or "rules_mgp"
        # refresh rules_data from DB
        try:
            new_rules = supabase.from_(table_name).select("*").eq("league", league_id).execute().data or []
            st.session_state["rules_data"] = new_rules
        except Exception:
            pass
        st.rerun()
        return

    # Handle Confirm
    if confirm:
        # Validation loop
        errors = []
        updates = []  # tuples (id_or_None, payload_dict)
        for item in inputs:
            rid = item["id"]
            rule_name = item["rule"]
            if item["type"] == "numeric":
                raw_val = item["raw"]
                # raw_val comes from number_input; round to 2 decimals to avoid float noise
                try:
                    rounded = round(float(raw_val), 2)
                    # store as int if integer after rounding
                    if float(rounded).is_integer():
                        store_val = int(rounded)
                    else:
                        store_val = rounded
                except Exception:
                    errors.append(f"Value for '{rule_name}' is not numeric.")
                    continue
                payload = {"rule": rule_name, "value": store_val, "league": league_id}
                updates.append((rid, payload))
            else:
                # multi: parse text to list of numbers
                txt = item["raw"]
                if txt is None or str(txt).strip() == "":
                    parsed_list = []
                else:
                    try:
                        # allow JSON or python literal
                        try:
                            parsed = json.loads(txt)
                        except Exception:
                            parsed = ast.literal_eval(txt)
                        if not isinstance(parsed, (list, tuple)):
                            raise ValueError("Must be a list/array")
                        # convert elements to numbers and round to 2 decimals
                        parsed_list = []
                        for idx_e, e in enumerate(parsed):
                            if isinstance(e, (int, float)):
                                n = float(e)
                            else:
                                # try parse numeric from string
                                try:
                                    n = float(str(e))
                                except Exception:
                                    raise ValueError(f"Element #{idx_e} of '{rule_name}' is not numeric: {e}")
                            # round to 2 decimals
                            rn = round(n, 2)
                            if float(rn).is_integer():
                                parsed_list.append(int(rn))
                            else:
                                parsed_list.append(rn)
                    except Exception as ex:
                        errors.append(f"Invalid array for '{rule_name}': {ex}")
                        continue

                if len(parsed_list) > 22:
                    errors.append(f"Array for '{rule_name}' too long ({len(parsed_list)} > 22).")
                    continue
                payload = {"rule": rule_name, "value": parsed_list, "league": league_id}
                updates.append((rid, payload))

        if errors:
            for e in errors:
                st.error(e)
            st.warning("Fix errors before confirming.")
            return

        # Perform DB updates/inserts
        failed = []
        succeeded = []
        for rid, payload in updates:
            try:
                if rid:
                    # update existing row
                    resp_upd = supabase.from_(table_name).update(payload).eq("id", rid).execute()
                    if getattr(resp_upd, "error", None):
                        failed.append((rid, getattr(resp_upd, "error")))
                    else:
                        succeeded.append(rid)
                else:
                    # insert new row
                    ins = supabase.from_(table_name).insert([payload]).execute()
                    if getattr(ins, "error", None):
                        failed.append((None, getattr(ins, "error")))
                    else:
                        succeeded.append(ins.data or [])
            except Exception as exc:
                failed.append((rid, str(exc)))

        if failed:
            st.error(f"Some updates failed: {failed}")
            # still try to reload and return
        else:
            st.success("Rules updated successfully.")

        # refresh rules data in session and go back to view
        try:
            refreshed = supabase.from_(table_name).select("*").eq("league", league_id).execute().data or []
            st.session_state["rules_data"] = refreshed
        except Exception:
            pass

        st.session_state.screen = target  # back to rules view (rules_f1 / rules_mgp)
        st.rerun()
