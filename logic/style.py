import ast
import streamlit as st

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

def color_to_rgb(hex_color):
    return [int(hex_color[i:i+2], 16) for i in (1, 3, 5)]
    
# -------------------------------------------------------------------------------------------

def render_table(df):
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


