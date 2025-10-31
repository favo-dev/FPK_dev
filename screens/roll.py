import ast
import streamlit as st
from supabase import create_client


# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --------------------- ROLL SCREEN ----------------------------------------------------

def roll_screen(user):
    st.set_page_config(layout="wide") 

    data = supabase.from_("roll_of_honor_new").select("*").eq("league", str(user['league'])).execute().data or []
    teams = supabase.from_("teams").select("*").eq("league", str(user['league'])).execute().data or []

    team_info = {team["name"]: team for team in teams}

    anni = [entry["year"] for entry in data]
    anno_scelto = st.selectbox("Select a year", sorted(anni, reverse=True))
    entry = next((item for item in data if item["year"] == anno_scelto), None)

    def render_color_box(main_color, second_color):
        if isinstance(main_color, str):
            try:
                main_color = ast.literal_eval(main_color)
            except Exception:
                main_color = [0, 0, 0]
        if isinstance(second_color, str):
            try:
                second_color = ast.literal_eval(second_color)
            except Exception:
                second_color = [0, 0, 0]

        main_rgb = f'rgb({main_color[0]}, {main_color[1]}, {main_color[2]})'
        border_rgb = f'rgb({second_color[0]}, {second_color[1]}, {second_color[2]})'
        html = f"""
        <div style='
            width: 100%;
            height: 25px;
            background-color: {main_rgb};
            border: 3px solid {border_rgb};
            border-radius: 5px;
            margin-bottom: 10px;
        '></div>
        """
        return html

    def render_driver_box(drivers, label):
        items = "".join([f"<li>{driver}</li>" for driver in drivers])
        html = f"""
        <div style='
            background-color: #2c2c2c;
            color: white;
            padding: 16px 20px;
            border-radius: 10px;
            margin-top: 12px;
        '>
            <strong>{label}:</strong>
            <ul style='margin: 0; padding-left: 22px;'>{items}</ul>
        </div>
        """
        return html

    def render_section_header(title, team_name):
        html = f"""
        <div style='text-align: center; padding: 0 10px;'>
            <h3 style='margin-bottom: 6px; font-size: 22px;'>{title}</h3>
            <hr style='margin: 6px 0;'>
            <div style='font-size: 18px; font-weight: bold;'>{team_name}</div>
            <hr style='margin: 6px 0 12px 0;'>
        </div>
        """
        return html

    if entry:
        colL, col_ff1, col_fpk, col_fmgp, colR = st.columns([1.5, 4, 5, 4, 1.5])

        with colL:
            url = 'https://koffsyfgevaannnmjkvl.supabase.co/storage/v1/object/sign/figures/crown_left.png?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV9hNTU1ZWI5ZC03NmZjLTRiMjUtOGIwMC05ZDQ4ZTRhNGNhMDEiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJmaWd1cmVzL2Nyb3duX2xlZnQucG5nIiwiaWF0IjoxNzU4NjM0ODQwLCJleHAiOjE3OTAxNzA4NDB9.0KqyfJ_YUfMS2h8t8yyxDlBvlyE3qU-awXx8Qu1cfEg'
            st.image(url, use_container_width=True)

        with col_ff1:
            team_id = entry.get("ff1")
            team = team_info.get(team_id)
            if team:
                st.markdown(render_color_box(team["main color"], team["second color"]), unsafe_allow_html=True)
                st.markdown(render_section_header("FF1", team["name"]), unsafe_allow_html=True)

                drivers_raw = entry.get("ff1_team", [])
                if isinstance(drivers_raw, str):
                    try:
                        drivers = ast.literal_eval(drivers_raw)
                    except Exception:
                        drivers = [drivers_raw]
                else:
                    drivers = drivers_raw

                st.markdown(render_driver_box(drivers, "Drivers"), unsafe_allow_html=True)
            else:
                st.warning("Team info missing")

        with col_fpk:
            team_id = entry.get("fpk")
            team = team_info.get(team_id)
            if team:
                st.markdown(render_color_box(team["main color"], team["second color"]), unsafe_allow_html=True)
                st.markdown(render_section_header("FPK", team["name"]), unsafe_allow_html=True)

                drivers_raw = entry.get("fpk_team", [])
                if isinstance(drivers_raw, str):
                    try:
                        drivers = ast.literal_eval(drivers_raw)
                    except Exception:
                        drivers = [drivers_raw]
                else:
                    drivers = drivers_raw

                st.markdown(render_driver_box(drivers, "Pilots"), unsafe_allow_html=True)
            else:
                st.warning("Team info missing")

        with col_fmgp:
            team_id = entry.get("fmgp")
            team = team_info.get(team_id)
            if team:
                st.markdown(render_color_box(team["main color"], team["second color"]), unsafe_allow_html=True)
                st.markdown(render_section_header("FMGP", team["name"]), unsafe_allow_html=True)

                drivers_raw = entry.get("fmgp_team", [])
                if isinstance(drivers_raw, str):
                    try:
                        drivers = ast.literal_eval(drivers_raw)
                    except Exception:
                        drivers = [drivers_raw]
                else:
                    drivers = drivers_raw

                st.markdown(render_driver_box(drivers, "Riders"), unsafe_allow_html=True)
            else:
                st.warning("Team info missing")


        with colR:
            url = 'https://koffsyfgevaannnmjkvl.supabase.co/storage/v1/object/sign/figures/crown_right.png?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV9hNTU1ZWI5ZC03NmZjLTRiMjUtOGIwMC05ZDQ4ZTRhNGNhMDEiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJmaWd1cmVzL2Nyb3duX3JpZ2h0LnBuZyIsImlhdCI6MTc1ODYzNDk0MCwiZXhwIjoxNzkwMTcwOTQwfQ.jlKnqtWCEzti0EF2CBNibYnd830pbwPXs2-hWZwQlfU'
            st.image(url, use_container_width=True)

    else:
        st.error("Year not found")
