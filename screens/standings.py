import streamlit as st
import ast
import pandas as pd
from supabase import create_client
import re
from logic.functions import (
    parse_color_field,
    render_standings_custom,
    build_normalized_team_set,
    build_points_dict,
    load_standings_from_buckets,
    load_table,
)

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --------------------- STANDINGS SCREEN ----------------------------------------------------

def standings_screen(user=None):
    loading_placeholder = st.empty()
    loading_placeholder.info("⏳ Loading...")

    standings_data = load_standings_from_buckets(["F1", "MGP"])
    
    teams = load_table("class")
    pen_list = load_table("penalty")
    rules_f1_list = load_table("rules_f1")
    rules_mgp_list = load_table("rules_mgp")
    loading_placeholder.empty()
    penalty_map = {}
    for item in pen_list:
        team_key = item.get("team") or item.get("team_id") or item.get("ID")
        if not team_key:
            continue
        def to_list(value):
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                return [v.strip() for v in value.split(",") if v.strip()]
            return []
        penalty_map[team_key] = {
            "penalty_f1": to_list(item.get("penalty_f1", [])),
            "penalty_mgp": to_list(item.get("penalty_mgp", []))
        }

    penalty_points_f1 = next((float(item["value"]) for item in rules_f1_list if item.get("rule") == "Penalty points for late call-ups"), 0.0)
    penalty_points_mgp = next((float(item["value"]) for item in rules_mgp_list if item.get("rule") == "Penalty points for late call-ups"), 0.0)

    team_points = {}
    penalty_points_dict = {}
    standings_f1 = {}
    standings_mgp = {}
    bucket_map = {"F1": "F1", "MotoGP": "MGP"}

    per_race_points = {"F1": {}, "MGP": {}}
    for bucket_key, races in standings_data.items():
        for race_tag, race_data in races.items():
            pts_dict = {}
            d1 = build_points_dict(race_data.get("standings"), use_full_name=(bucket_key == "MGP"))
            d2 = build_points_dict(race_data.get("sprint_standings"), use_full_name=(bucket_key == "MGP"))
            keys = set(d1.keys()) | set(d2.keys())
            for k in keys:
                pts_dict[k] = d1.get(k, 0) + d2.get(k, 0)
            per_race_points[bucket_key][race_tag] = pts_dict

    for team in teams:
        team_name = team.get("ID") or team.get("id") or team.get("team_id") or team.get("name")
        if not team_name:
            continue
        team_points[team_name] = {"F1": {}, "MotoGP": {}}
        penalty_points_dict[team_name] = {"F1": 0, "MotoGP": 0}
        total_f1_points = 0.0
        total_mgp_points = 0.0

        def ensure_list(value):
            if value is None:
                return []
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                return [v.strip() for v in value.split(",") if v.strip()]
            return [value]

        f1_items = ensure_list(team.get("F1")) + ensure_list(team.get("others"))
        mgp_items = ensure_list(team.get("MotoGP")) + ensure_list(team.get("others"))

        team_drivers_f1_set = build_normalized_team_set(f1_items, use_full_name=False)
        team_drivers_mgp_set = build_normalized_team_set(mgp_items, use_full_name=True)


        for series in ["F1", "MotoGP"]:
            bucket_key = bucket_map.get(series, "MGP")
            series_races = per_race_points.get(bucket_key, {})
            penalty_points_value = penalty_points_f1 if series == "F1" else penalty_points_mgp
            penalty_key = "penalty_f1" if series == "F1" else "penalty_mgp"
            team_set = team_drivers_f1_set if series == "F1" else team_drivers_mgp_set

            for race_tag, race_pts_dict in series_races.items():
                pts = sum(race_pts_dict.get(d, 0) for d in team_set)
                penalty_list = penalty_map.get(team_name, {}).get(penalty_key, [])
                if race_tag in penalty_list:
                    pts += penalty_points_value
                    penalty_points_dict[team_name][series] += penalty_points_value
                team_points[team_name][series][race_tag] = pts
                if series == "F1":
                    total_f1_points += pts
                else:
                    total_mgp_points += pts

        standings_f1[team_name] = int(total_f1_points)
        standings_mgp[team_name] = int(total_mgp_points)


    def create_standings_table(standings_dict, teams_list, series_name):
        rows = []
        for t in teams_list:
            team_id = t.get("ID") or t.get("id") or t.get("team_id") or t.get("name")
            pts = int(standings_dict.get(team_id, 0))
            penal = int(penalty_points_dict.get(team_id, {}).get(series_name, 0))
            rows.append({"Team": t.get("name") or team_id, "Pts": pts, "Penalty": penal})
        df = pd.DataFrame(rows)
        if df.empty:
            return df
        df = df.sort_values(by="Pts", ascending=False).reset_index(drop=True)
        df["Position"] = df.index + 1
        leader_points = df["Pts"].iloc[0]
        df["Gap from previous"] = (df["Pts"].shift(1).fillna(df["Pts"].iloc[0]) - df["Pts"]).clip(lower=0).astype(int)
        df["Gap from leader"] = (leader_points - df["Pts"]).astype(int)
        return df[["Position", "Team", "Pts", "Penalty", "Gap from previous", "Gap from leader"]]

    standings_f1_table = create_standings_table(standings_f1, teams, "F1")
    standings_mgp_table = create_standings_table(standings_mgp, teams, "MotoGP")

    combined_rows = []
    for t in teams:
        id_key = t.get("ID") or t.get("id") or t.get("team_id") or t.get("name")
        total_pts = standings_f1.get(id_key, 0) + standings_mgp.get(id_key, 0)
        total_pen = penalty_points_dict.get(id_key, {}).get("F1", 0) + penalty_points_dict.get(id_key, {}).get("MotoGP", 0)
        combined_rows.append({"Team": t.get("name") or id_key, "Pts": int(total_pts), "Penalty": int(total_pen)})

    standings_combined_table = pd.DataFrame(combined_rows)
    if not standings_combined_table.empty:
        standings_combined_table = standings_combined_table.sort_values(by="Pts", ascending=False).reset_index(drop=True)
        standings_combined_table["Position"] = standings_combined_table.index + 1
        leader_points_combined = standings_combined_table["Pts"].iloc[0]
        standings_combined_table["Gap from previous"] = (
            standings_combined_table["Pts"].shift(1).fillna(standings_combined_table["Pts"].iloc[0]) - standings_combined_table["Pts"]
        ).clip(lower=0).astype(int)
        standings_combined_table["Gap from leader"] = (leader_points_combined - standings_combined_table["Pts"]).astype(int)

    render_standings_custom(standings_f1_table, teams, "FF1")
    st.markdown("<hr style='border:2px solid #000; margin:20px 0;'>", unsafe_allow_html=True)
    render_standings_custom(standings_mgp_table, teams, "FMGP")
    st.markdown("<hr style='border:2px solid #000; margin:20px 0;'>", unsafe_allow_html=True)
    render_standings_custom(standings_combined_table, teams, "FPK")

    return {
        "team_points": team_points,
        "penalty_points_dict": penalty_points_dict,
        "standings_f1": standings_f1,
        "standings_mgp": standings_mgp,
        "standings_overall": {k: standings_f1.get(k,0) + standings_mgp.get(k,0) for k in set(list(standings_f1.keys()) + list(standings_mgp.keys()))}
    }
