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

def standings_screen(user):
    loading_placeholder = st.empty()
    loading_placeholder.info("⏳ Loading...")

    #standings_data = load_standings_from_buckets(user, ["F126", "MGP26"])
    
    teams = load_table("teams")
    pen_list = load_table("penalty_new")
    rules_f1_list = load_table("rules_f1_new")
    rules_mgp_list = load_table("rules_mgp_new")
    points_per_race_f1 = load_table("points_per_race_f1")
    points_per_race_mgp = load_table("points_per_race_mgp")
    
    loading_placeholder.empty()
    penalty_map = {}
    for item in pen_list:
        team_key = item.get("uuid") or item.get("team_id") or item.get("ID")
        if not team_key:
            continue
        def to_list(value):
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                return [v.strip() for v in value.split(",") if v.strip()]
            return []
        if item["league"] == user["league"]:
            penalty_map[team_key] = {
                "penalty_f1": to_list(item.get("penalty_f1", [])),
                "penalty_mgp": to_list(item.get("penalty_mgp", []))
        }

    penalty_points_f1 = next(
        (
            float(item["value"])
            for item in rules_f1_list
            if item.get("rule") == "Penalty points for late call-ups"
            and item.get("league") == user["league"]
        ),
        0.0
    )

    penalty_points_mgp = next(
        (
            float(item["value"])
            for item in rules_mgp_list
            if item.get("rule") == "Penalty points for late call-ups"
            and item.get("league") == user["league"]
        ),
        0.0
    )

    team_points = {}
    penalty_points_dict = {}
          
    for team in teams:
         if team["league"] == user["league"]:
             team_name = team.get("UUID") 
             if not team_name:
                 continue
             team_points[team_name] = {"F1": {}, "MotoGP": {}, "Name": {}}
             penalty_points_dict[team_name] = {"F1": 0, "MotoGP": 0, "Name": {}}

             for player in team_points:
                 for elem in teams:
                     if elem["league"] == user["league"] and elem["UUID"] == player:
                        team_points[player]["Name"] = elem["name"]
                        penalty_points_dict[player]["Name"] = elem["name"]
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
                 
    excluded_keys = {"id", "prim_key", "league"}
    for element in points_per_race_f1:
        for player in team_points:
            if element["league"] == user["league"] and element["id"] == player:
                total = sum(
                    value
                    for key, value in element.items()
                    if key not in excluded_keys and isinstance(value, (int, float))
                )

                team_points[player]["F1"] = total
    
    for element in pen_list:
        for player in team_points:
            if element["league"] == user["league"] and element["uuid"] == player:
                total_pen = element["penalty_f1"] * penalty_points_f1
                penalty_points_dict[player]["F1"] = total_pen
                team_points[player]["F1"] = team_points[player]["F1"] + total_pen
    
    for element in points_per_race_mgp:
        for player in team_points:
            if element["league"] == user["league"] and element["id"] == player:
                total = sum(
                    value
                    for key, value in element.items()
                    if key not in excluded_keys and isinstance(value, (int, float))
                )

                team_points[player]["MotoGP"] = total

    for element in pen_list:
        for player in team_points:
            if element["league"] == user["league"] and element["uuid"] == player:
                total_pen = element["penalty_mgp"] * penalty_points_mgp
                penalty_points_dict[player]["MotoGP"] = total_pen
                team_points[player]["MotoGP"] = team_points[player]["MotoGP"] + total_pen

    
    def create_standings_table(team_points, penalty_points_dict, series_name):
        rows = []

        for team_id, data in team_points.items():
            pts = int(data.get(series_name, 0))
            penal = int(penalty_points_dict.get(team_id, {}).get(series_name, 0))
            name = data.get("Name", team_id)

            rows.append({
                "Team": name,
                "Pts": pts,
                "Penalty": penal
            })

        df = pd.DataFrame(rows)
        if df.empty:
            return df

        df = df.sort_values(by="Pts", ascending=False).reset_index(drop=True)
        df["Position"] = df.index + 1

        leader_points = df["Pts"].iloc[0]
        df["Gap from previous"] = (
            df["Pts"].shift(1).fillna(leader_points) - df["Pts"]
        ).clip(lower=0).astype(int)

        df["Gap from leader"] = (leader_points - df["Pts"]).astype(int)

        return df[
            ["Position", "Team", "Pts", "Penalty", "Gap from previous", "Gap from leader"]
        ]

    standings_f1_table = create_standings_table(team_points, penalty_points_dict, "F1")
    standings_mgp_table = create_standings_table(team_points, penalty_points_dict, "MotoGP")

    combined_rows = []

    for team_id, data in team_points.items():
        total_pts = int(data.get("F1", 0) + data.get("MotoGP", 0))
        total_pen = int(
            penalty_points_dict.get(team_id, {}).get("F1", 0)
            + penalty_points_dict.get(team_id, {}).get("MotoGP", 0)
        )

        combined_rows.append({
            "Team": data.get("Name", team_id),
            "Pts": total_pts,
            "Penalty": total_pen
        })

    standings_combined_table = pd.DataFrame(combined_rows)

    if not standings_combined_table.empty:
        standings_combined_table = (
            standings_combined_table
            .sort_values(by="Pts", ascending=False)
            .reset_index(drop=True)
        )

        standings_combined_table["Position"] = standings_combined_table.index + 1
        leader_points = standings_combined_table["Pts"].iloc[0]

        standings_combined_table["Gap from previous"] = (
            standings_combined_table["Pts"].shift(1).fillna(leader_points)
            - standings_combined_table["Pts"]
        ).clip(lower=0).astype(int)

        standings_combined_table["Gap from leader"] = (
            leader_points - standings_combined_table["Pts"]
        ).astype(int)

    render_standings_custom(standings_f1_table, teams, "FF1")
    st.markdown("<hr style='border:2px solid #000; margin:20px 0;'>", unsafe_allow_html=True)

    render_standings_custom(standings_mgp_table, teams, "FMGP")
    st.markdown("<hr style='border:2px solid #000; margin:20px 0;'>", unsafe_allow_html=True)

    render_standings_custom(standings_combined_table, teams, "FPK")

