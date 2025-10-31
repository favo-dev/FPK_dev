import ast
import json
import streamlit as st
from supabase import create_client

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("Missing Supabase credentials in st.secrets (SUPABASE_URL / SUPABASE_ANON_KEY).")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --------------------- UTILITIES ----------------------------------------------------

def safe_parse_color(val):
    """
    Accetta:
      - una lista/tupla [r,g,b]
      - una stringa JSON o Python literal "[r,g,b]"
      - una stringa tipo "r,g,b"
    Ritorna sempre una lista di 3 int [r,g,b] (clamped 0..255) o [0,0,0] in caso di errore.
    """
    fallback = [0, 0, 0]
    if val is None:
        return fallback
    if isinstance(val, (list, tuple)) and len(val) >= 3:
        try:
            r, g, b = int(val[0]), int(val[1]), int(val[2])
            return [max(0,min(255,r)), max(0,min(255,g)), max(0,min(255,b))]
        except Exception:
            return fallback
    if isinstance(val, str):
        s = val.strip()
        # try JSON
        try:
            parsed = json.loads(s)
            if isinstance(parsed, (list, tuple)) and len(parsed) >= 3:
                return safe_parse_color(parsed)
        except Exception:
            pass
        # try Python literal
        try:
            parsed = ast.literal_eval(s)
            if isinstance(parsed, (list, tuple)) and len(parsed) >= 3:
                return safe_parse_color(parsed)
        except Exception:
            pass
        # try "r,g,b"
        if "," in s:
            parts = [p.strip() for p in s.split(",")]
            if len(parts) >= 3:
                try:
                    return [max(0,min(255,int(parts[0]))), max(0,min(255,int(parts[1]))), max(0,min(255,int(parts[2])))]
                except Exception:
                    pass
    return fallback

def rgb_to_css(rgb):
    return f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"

def safe_parse_drivers(raw):
    """
    Accetta:
      - lista/tuple di driver
      - stringa JSON o Python-literal rappresentante una lista
      - singola stringa (ritorna [string])
    Ritorna sempre una lista (anche vuota).
    """
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(x) for x in raw]
    if isinstance(raw, str):
        s = raw.strip()
        if s == "":
            return []
        # try JSON
        try:
            parsed = json.loads(s)
            if isinstance(parsed, (list, tuple)):
                return [str(x) for x in parsed]
        except Exception:
            pass
        # try ast literal
        try:
            parsed = ast.literal_eval(s)
            if isinstance(parsed, (list, tuple)):
                return [str(x) for x in parsed]
        except Exception:
            pass
        # fallback: single name (comma separated -> split)
        if "," in s:
            return [p.strip() for p in s.split(",") if p.strip()]
        return [s]
    # other types: cast to str
    return [str(raw)]

# --------------------- ROLL SCREEN ----------------------------------------------------

def roll_screen(user):
    # page config should ideally be set once at app start; setting here is okay but call only once
    try:
        st.set_page_config(layout="wide")
    except Exception:
        # already set or not allowed; ignore
        pass

    # header
    st.title("Roll of Honor")

    # defensive fetch from Supabase
    data = []
    teams = []
    try:
        resp = supabase.from_("roll_of_honor_new").select("*").eq("league", str(user.get("league"))).execute()
        data = resp.data or []
    except Exception as e:
        st.error(f"Errore fetching roll_of_honor_new: {e}")
        data = []

    try:
        resp2 = supabase.from_("teams").select("*").eq("league", str(user.get("league"))).execute()
        teams = resp2.data or []
    except Exception as e:
        st.error(f"Errore fetching teams: {e}")
        teams = []

    # debug info (togglable)
    debug = st.session_state.get("debug_roll", False)
    if debug:
        st.write("DEBUG: fetched roll entries:", data)
        st.write("DEBUG: fetched teams:", teams)

    if not data:
        st.info("Nessuna voce trovata nella tabella 'roll_of_honor_new' per questa league.")
        return

    if not teams:
        st.warning("Nessuna squadra trovata nella tabella 'teams' per questa league. Alcune informazioni potrebbero mancare.")

    # build lookup both by ID and name (and 'who' if present)
    team_info_by_id = {}
    team_info_by_name = {}
    for t in teams:
        # possible keys where ID might be stored: 'ID', 'id', 'id_team'...
        tid = t.get("ID") or t.get("id") or t.get("team_id") or t.get("who") or t.get("name")
        if tid is None:
            continue
        team_info_by_id[str(tid)] = t
        # also map by name
        name = t.get("name")
        if name:
            team_info_by_name[str(name)] = t

    # helper to resolve team reference (tries ID first, then name)
    def resolve_team(ref):
        if ref is None:
            return None
        ref_s = str(ref)
        if ref_s in team_info_by_id:
            return team_info_by_id[ref_s]
        if ref_s in team_info_by_name:
            return team_info_by_name[ref_s]
        # sometimes DB might store integer-like but as int; attempt to match by loose equality
        for k, v in team_info_by_id.items():
            if str(k) == ref_s:
                return v
        # not found
        return None

    # collect unique years and sort desc
    anni = sorted({entry.get("year") for entry in data if entry.get("year") is not None}, reverse=True)
    if not anni:
        st.info("Nessun anno disponibile nelle voci di roll_of_honor.")
        return

    anno_scelto = st.selectbox("Select a year", options=anni, index=0 if anni else None)
    # find first matching entry for the chosen year (there might be several: we pick the first)
    entry = next((item for item in data if item.get("year") == anno_scelto), None)

    if not entry:
        st.error(f"Anno {anno_scelto} non trovato nelle voci (incoerenza dati).")
        return

    # Render helpers (use safe parsers)
    def render_color_box(main_color_raw, second_color_raw):
        main_color = safe_parse_color(main_color_raw)
        second_color = safe_parse_color(second_color_raw)
        main_rgb = rgb_to_css(main_color)
        border_rgb = rgb_to_css(second_color)
        html = f"""
        <div style='
            width: 100%;
            height: 28px;
            background-color: {main_rgb};
            border: 3px solid {border_rgb};
            border-radius: 6px;
            margin-bottom: 10px;
        '></div>
        """
        return html

    def render_driver_box(drivers, label):
        items = "".join([f"<li>{st.utils.escape_html(d)}</li>" if hasattr(st, "utils") else "".join([f"<li>{d}</li>" for d in drivers]) for d in drivers])
        # fallback if st.utils.escape_html not available, just produce safe-ish HTML
        if not items:
            items = "<li>N/A</li>"
        html = f"""
        <div style='
            background-color: #2c2c2c;
            color: white;
            padding: 14px 18px;
            border-radius: 8px;
            margin-top: 10px;
        '>
            <strong>{label}:</strong>
            <ul style='margin: 8px 0 0 20px; padding: 0;'>{items}</ul>
        </div>
        """
        return html

    def render_section_header(title, team_name):
        team_name_safe = team_name or "N/A"
        html = f"""
        <div style='text-align: center; padding: 0 8px;'>
            <h3 style='margin-bottom: 6px; font-size: 20px;'>{title}</h3>
            <div style='font-size: 18px; font-weight: 700; margin-bottom: 6px;'>{team_name_safe}</div>
            <hr style='margin: 6px 0 12px 0; border:0; height:1px; background:#444;'/>
        </div>
        """
        return html

    # Layout columns
    colL, col_ff1, col_fpk, col_fmgp, colR = st.columns([1.2, 3.8, 4.5, 3.8, 1.2])

    # Left crown (if available)
    with colL:
        try:
            url_left = entry.get("left_crown_url") or 'https://koffsyfgevaannnmjkvl.supabase.co/storage/v1/object/sign/figures/crown_left.png'
            st.image(url_left, use_container_width=True)
        except Exception:
            pass

    # FF1 column
    with col_ff1:
        team_ref = entry.get("ff1")
        team = resolve_team(team_ref)
        if not team:
            st.warning(f"FF1: team reference '{team_ref}' non risolta.")
        else:
            st.markdown(render_color_box(team.get("main color"), team.get("second color")), unsafe_allow_html=True)
            st.markdown(render_section_header("FF1", team.get("name")), unsafe_allow_html=True)

            drivers = safe_parse_drivers(entry.get("ff1_team", []))
            st.markdown(render_driver_box(drivers, "Drivers"), unsafe_allow_html=True)

    # FPK column
    with col_fpk:
        team_ref = entry.get("fpk")
        team = resolve_team(team_ref)
        if not team:
            st.warning(f"FPK: team reference '{team_ref}' non risolta.")
        else:
            st.markdown(render_color_box(team.get("main color"), team.get("second color")), unsafe_allow_html=True)
            st.markdown(render_section_header("FPK", team.get("name")), unsafe_allow_html=True)

            drivers = safe_parse_drivers(entry.get("fpk_team", []))
            st.markdown(render_driver_box(drivers, "Pilots"), unsafe_allow_html=True)

    # FMGP column
    with col_fmgp:
        team_ref = entry.get("fmgp")
        team = resolve_team(team_ref)
        if not team:
            st.warning(f"FMGP: team reference '{team_ref}' non risolta.")
        else:
            st.markdown(render_color_box(team.get("main color"), team.get("second color")), unsafe_allow_html=True)
            st.markdown(render_section_header("FMGP", team.get("name")), unsafe_allow_html=True)

            drivers = safe_parse_drivers(entry.get("fmgp_team", []))
            st.markdown(render_driver_box(drivers, "Riders"), unsafe_allow_html=True)

    # Right crown
    with colR:
        try:
            url_right = entry.get("right_crown_url") or 'https://koffsyfgevaannnmjkvl.supabase.co/storage/v1/object/sign/figures/crown_right.png'
            st.image(url_right, use_container_width=True)
        except Exception:
            pass

    # optionally show a summary footer or debug
    if debug:
        st.write("Selected entry:", entry)
