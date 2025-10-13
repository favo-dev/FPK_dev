import re
import streamlit as st

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

def color_to_rgb(hex_color):
    return [int(hex_color[i:i+2], 16) for i in (1, 3, 5)]
    
# -------------------------------------------------------------------------------------------

def render_results_table(df):
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;padding:5px 0;font-weight:600;border-bottom:1px solid #ccc;">
        <div style="width:90px;">Position</div>
        <div style="flex:1;">Pilot</div>
        <div style="width:150px;text-align:left;">Performance score</div>
        <div style="width:80px;text-align:right;">Points</div>
    </div>
    """, unsafe_allow_html=True)
    for _, row in df.iterrows():
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;padding:5px 4px;">
            <div style="width:90px;">{row['Position']}</div>
            <div style="flex:1;">{row['Name with Color']}</div>
            <div style="width:150px;">{row['Performance']}</div>
            <div style="width:80px;text-align:right;">{row['Points']}</div>
        </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------------------------

def safe_rgb_to_hex(color):
    try:
        if not color:
            return "#888888"

        # Se è una stringa
        if isinstance(color, str):
            s = color.strip()
            if s.startswith("#") and len(s) in (4, 7):
                return s
            # Cerca numeri nella stringa
            nums = re.findall(r"\d{1,3}", s)
            if len(nums) >= 3:
                r, g, b = int(nums[0]), int(nums[1]), int(nums[2])
                return "#{:02x}{:02x}{:02x}".format(r, g, b)

        # Se è lista o tupla di almeno 3 elementi
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            r, g, b = int(color[0]), int(color[1]), int(color[2])
            return "#{:02x}{:02x}{:02x}".format(r, g, b)

        # Se è un dizionario JSONB
        if isinstance(color, dict):
            keys = {k.lower(): k for k in color.keys()}
            if {"r","g","b"}.issubset(keys):
                r, g, b = int(color[keys["r"]]), int(color[keys["g"]]), int(color[keys["b"]])
                return "#{:02x}{:02x}{:02x}".format(r, g, b)

    except Exception as e:
        print(f"Errore in safe_rgb_to_hex: {e}")

    return "#888888"

# -------------------------------------------------------------------------------------------

def _render_simple_table_html(rows, spacing_px=None, row_padding=None):
    spacing = 0 if spacing_px is None else spacing_px   # 0 di default (nessun margin-bottom extra)
    padding = '2px 8px' if row_padding is None else row_padding  

    rows_html = ""
    for label, value in rows:
        label_esc = _html.escape(str(label))
        value_esc = _html.escape(str(value))
        rows_html += f"""
        <div style='display:flex; justify-content:space-between; align-items:flex-start;
                    padding:{padding}; border-top:1px solid rgba(255,255,255,0.06);'>
            <div style='font-size:13px; font-weight:600; color:#dcdcdc;
                        max-width:65%; white-space:pre-wrap; word-break:break-word;
                        overflow-wrap:anywhere; line-height:1.2;'>{label_esc}</div>
            <div style='font-size:14px; font-weight:700; color:#ffffff; text-align:right;
                        max-width:35%; white-space:pre-wrap; word-break:break-word;
                        overflow-wrap:anywhere; line-height:1.2;'>{value_esc}</div>
        </div>
        """

    table_html = f"""
    <div style='width:100%; background:#222; border-radius:8px;
                box-shadow:0 2px 6px rgba(0,0,0,0.12);
                overflow:hidden;
                height:auto;
                font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
                margin-bottom:{spacing}px;'>
        {rows_html}
    </div>
    """
    return table_html

# -------------------------------------------------------------------------------------------

def render_standings_custom(df, teams, title):
    st.markdown(f"<h2 style='color:#ffffff; background-color:#222222; font-size:28px; font-weight:bold; padding: 4px 8px; border-radius:4px;'>{title}</h2>", unsafe_allow_html=True)
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex; font-weight:700; border-bottom:2px solid #ccc; padding-bottom:6px; margin-bottom:8px;">
        <div style="width:30px;">Pos</div>
        <div style="width:30px;"></div>
        <div style="flex-grow:1;">Team</div>
        <div style="width:60px; text-align:right;">Points</div>
        <div style="width:80px; text-align:right;">Penalty</div>
        <div style="width:100px; text-align:right;">Gap (previous)</div>
        <div style="width:80px; text-align:right;">Gap (leader)</div>
    </div>
    """, unsafe_allow_html=True)
    for _, row in df.iterrows():
        team_name = row["Team"]
        team_info = next((t for t in teams if (t.get("name") == team_name) or (t.get("ID") == team_name) or (t.get("id") == team_name)), None)
        main_raw = None
        second_raw = None
        if team_info:
    # prova varie chiavi possibili (nel caso la colonna si chiami con nomi diversi)
            for key in ("main color", "main_color", "mainColor", "mainColorRGB"):
                if key in team_info:
                    main_raw = parse_color_field(team_info.get(key))
                    break
            for key in ("second color", "second_color", "secondColor", "accent color"):
                if key in team_info:
                    second_raw = parse_color_field(team_info.get(key))
                    break

        color_main = safe_rgb_to_hex(main_raw) if main_raw is not None else safe_rgb_to_hex([0,0,0])
        color_second = safe_rgb_to_hex(second_raw) if second_raw is not None else safe_rgb_to_hex([100,100,100])
        st.markdown(f"""
        <div style="display:flex; align-items:center; margin-bottom:8px; padding-bottom:4px; border-bottom:1px solid #eee;">
            <div style="width:30px;">{row['Position']}</div>
            <div style="width:20px; height:20px; background-color:{color_main}; border: 2px solid {color_second}; border-radius:4px; margin-right:10px;"></div>
            <div style="flex-grow:1;">{team_name}</div>
            <div style="width:60px; text-align:right;">{row['Pts']}</div>
            <div style="width:80px; text-align:right; color:red;">{row['Penalty']}</div>
            <div style="width:100px; text-align:right; color:gray;">{row['Gap from previous']}</div>
            <div style="width:80px; text-align:right; color:#555;">{row['Gap from leader']}</div>
        </div>
        """, unsafe_allow_html=True)

# -------------------------------------------------------------------------------------------

