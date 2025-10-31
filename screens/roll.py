import ast
import json
import html as html_lib
import streamlit as st
from supabase import create_client

# -------------------------------------------------------------------------------------------
# Config Supabase
# -------------------------------------------------------------------------------------------
SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY")
if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise RuntimeError("Mancano le credenziali Supabase in st.secrets (SUPABASE_URL / SUPABASE_ANON_KEY).")

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# -------------------------------------------------------------------------------------------
# Utility parsing e sicurezza
# -------------------------------------------------------------------------------------------
def safe_parse_color(val):
    """Ritorna sempre [r,g,b] o [0,0,0] se non valido."""
    fallback = [0, 0, 0]
    if val is None:
        return fallback
    # lista/tupla già pronta
    if isinstance(val, (list, tuple)) and len(val) >= 3:
        try:
            r, g, b = int(val[0]), int(val[1]), int(val[2])
            return [max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))]
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
        # try python literal
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
                    return [max(0, min(255, int(parts[0]))),
                            max(0, min(255, int(parts[1]))),
                            max(0, min(255, int(parts[2])))]
                except Exception:
                    pass
    return fallback

def rgb_to_css(rgb):
    return f"rgb({rgb[0]}, {rgb[1]}, {rgb[2]})"

def safe_parse_drivers(raw):
    """Ritorna sempre una lista di stringhe drivers (anche vuota)."""
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
        # comma separated fallback
        if "," in s:
            return [p.strip() for p in s.split(",") if p.strip()]
        return [s]
    # other types -> cast to str
    return [str(raw)]

def escape(s):
    try:
        return html_lib.escape(str(s))
    except Exception:
        return str(s)

# -------------------------------------------------------------------------------------------
# Interfaccia: Roll screen (funzionalità principale come richiesto)
# -------------------------------------------------------------------------------------------
def roll_screen(user):
    """
    Mostra la Roll of Honor per la league di `user`.
    Requisito: prendi TUTTE le righe da roll_of_honor_new e teams dove league == user['league'].
    Mappatura id->name ora associa le chiavi UUID/uuid (dalla tabella teams) al loro name.
    """
    # il set_page_config dovrebbe essere chiamato una sola volta; proviamo tranquillamente
    try:
        st.set_page_config(layout="wide")
    except Exception:
        pass

    st.title("Roll of Honor")

    league_id = user.get("league")
    if league_id is None:
        st.error("user['league'] non definito.")
        return

    # Query difensive ma esatte come richiesto
    try:
        resp = supabase.from_("roll_of_honor_new").select("*").eq("league", str(league_id)).execute()
        roll_data = resp.data or []
    except Exception as e:
        st.error(f"Errore fetch roll_of_honor_new: {e}")
        roll_data = []

    try:
        resp2 = supabase.from_("teams").select("*").eq("league", str(league_id)).execute()
        teams = resp2.data or []
    except Exception as e:
        st.error(f"Errore fetch teams: {e}")
        teams = []

    # Se non ci sono righe, segnaliamo all'utente (comportamento robusto)
    if not roll_data:
        st.info("Nessuna voce trovata in 'roll_of_honor_new' per questa league.")
        return

    # Costruiamo lookup delle teams: proviamo più chiavi possibili (ora includiamo UUID/uuid)
    team_info_by_id = {}
    team_info_by_name = {}
    # mappatura diretta id->name (utile se vuoi usare la mappa id->name)
    id_to_name = {}

    for t in teams:
        possible_ids = []
        # includiamo esplicitamente UUID/uuid oltre ai campi comuni
        for key in ("UUID", "uuid", "ID", "id", "team_id", "who"):
            if key in t and t.get(key) is not None:
                possible_ids.append(str(t.get(key)))
        # anche il nome come id alternativo
        if t.get("name"):
            possible_ids.append(str(t.get("name")))
            team_info_by_name[str(t.get("name"))] = t
        # popola map id->team e id->name
        for pid in possible_ids:
            team_info_by_id[pid] = t
            # salva anche la mappatura id->name (sovrascrive se doppioni, ma è ok)
            id_to_name[pid] = t.get("name")

    # funzione per risolvere riferimento a team (entry può contenere id, UUID, name o altro)
    def resolve_team(ref):
        if ref is None:
            return None
        sref = str(ref)
        # match diretto nelle mappe
        if sref in team_info_by_id:
            return team_info_by_id[sref]
        if sref in team_info_by_name:
            return team_info_by_name[sref]
        # match coerente provando a confrontare stringhe/int-like
        for k, v in team_info_by_id.items():
            if k == sref:
                return v
            try:
                if int(k) == int(sref):
                    return v
            except Exception:
                pass
        # non trovato
        return None

    # utile helper per ottenere name direttamente da un riferimento (usa id_to_name)
    def resolve_name(ref):
        if ref is None:
            return None
        sref = str(ref)
        if sref in id_to_name:
            return id_to_name[sref]
        # fallback: try resolve_team and return name
        t = resolve_team(ref)
        if t:
            return t.get("name")
        return None

    # raccolta anni e ordinamento desc (preserviamo comportamento originale: selectbox)
    anni = sorted({entry.get("year") for entry in roll_data if entry.get("year") is not None}, reverse=True)
    if not anni:
        st.info("Nessun anno disponibile nelle voci.")
        return

    # selectbox anno
    anno_scelto = st.selectbox("Select a year", options=anni, index=0)
    # trova la prima entry per anno scelto (come prima)
    entry = next((e for e in roll_data if e.get("year") == anno_scelto), None)
    if not entry:
        st.error(f"Anno {anno_scelto} non trovato (incoerenza dati).")
        return

    # helpers render (rispettano il comportamento iniziale)
    def render_color_box(main_color_raw, second_color_raw):
        main = safe_parse_color(main_color_raw)
        second = safe_parse_color(second_color_raw)
        return f"""
        <div style='width:100%; height:25px; background-color: {rgb_to_css(main)}; border: 3px solid {rgb_to_css(second)}; border-radius:5px; margin-bottom:10px;'></div>
        """

    def render_driver_box(drivers, label):
        items = "".join([f"<li>{escape(d)}</li>" for d in drivers]) if drivers else "<li>N/A</li>"
        return f"""
        <div style='background-color:#2c2c2c; color:white; padding:16px 20px; border-radius:10px; margin-top:12px;'>
            <strong>{escape(label)}:</strong>
            <ul style='margin:6px 0 0 22px; padding:0;'>{items}</ul>
        </div>
        """

    def render_section_header(title, team_name):
        return f"""
        <div style='text-align:center; padding:0 10px;'>
            <h3 style='margin-bottom:6px; font-size:22px;'>{escape(title)}</h3>
            <hr style='margin:6px 0; border:0; height:1px; background:#ddd;'/>
            <div style='font-size:18px; font-weight:bold;'>{escape(team_name or "N/A")}</div>
            <hr style='margin:6px 0 12px 0; border:0; height:1px; background:#ddd;'/>
        </div>
        """

    # Layout colonne come prima
    colL, col_ff1, col_fpk, col_fmgp, colR = st.columns([1.5, 4, 5, 4, 1.5])

    # Left crown (usa URL se presente nella entry, altrimenti usa un'immagine fissa)
    with colL:
        try:
            url_left = entry.get("left_crown_url") or 'https://koffsyfgevaannnmjkvl.supabase.co/storage/v1/object/sign/figures/crown_left.png'
            st.image(url_left, use_container_width=True)
        except Exception:
            # se l'URL scaduto o non valido, non rompiamo l'app
            pass

    # FF1 column: risolvi usando resolve_team che ora considera UUID/uuid
    with col_ff1:
        team_ref = entry.get("ff1")
        # Se ff1 è un id che deve essere mappato a teams.UUID, resolve_team lo troverà grazie a UUID nella mappa
        team = resolve_team(team_ref)
        if team:
            st.markdown(render_color_box(team.get("main color"), team.get("second color")), unsafe_allow_html=True)
            st.markdown(render_section_header("FF1", team.get("name")), unsafe_allow_html=True)

            drivers = safe_parse_drivers(entry.get("ff1_team", []))
            st.markdown(render_driver_box(drivers, "Drivers"), unsafe_allow_html=True)
        else:
            # proviamo a risolvere solo il name direttamente (se ad es. id_to_name è popolata)
            name_guess = resolve_name(team_ref)
            if name_guess:
                st.markdown(render_section_header("FF1", name_guess), unsafe_allow_html=True)
                drivers = safe_parse_drivers(entry.get("ff1_team", []))
                st.markdown(render_driver_box(drivers, "Drivers"), unsafe_allow_html=True)
            else:
                st.warning(f"Team FF1 non risolto per riferimento: {team_ref}")

    # FPK column
    with col_fpk:
        team_ref = entry.get("fpk")
        team = resolve_team(team_ref)
        if team:
            st.markdown(render_color_box(team.get("main color"), team.get("second color")), unsafe_allow_html=True)
            st.markdown(render_section_header("FPK", team.get("name")), unsafe_allow_html=True)

            drivers = safe_parse_drivers(entry.get("fpk_team", []))
            st.markdown(render_driver_box(drivers, "Pilots"), unsafe_allow_html=True)
        else:
            name_guess = resolve_name(team_ref)
            if name_guess:
                st.markdown(render_section_header("FPK", name_guess), unsafe_allow_html=True)
                drivers = safe_parse_drivers(entry.get("fpk_team", []))
                st.markdown(render_driver_box(drivers, "Pilots"), unsafe_allow_html=True)
            else:
                st.warning(f"Team FPK non risolto per riferimento: {team_ref}")

    # FMGP column
    with col_fmgp:
        team_ref = entry.get("fmgp")
        team = resolve_team(team_ref)
        if team:
            st.markdown(render_color_box(team.get("main color"), team.get("second color")), unsafe_allow_html=True)
            st.markdown(render_section_header("FMGP", team.get("name")), unsafe_allow_html=True)

            drivers = safe_parse_drivers(entry.get("fmgp_team", []))
            st.markdown(render_driver_box(drivers, "Riders"), unsafe_allow_html=True)
        else:
            name_guess = resolve_name(team_ref)
            if name_guess:
                st.markdown(render_section_header("FMGP", name_guess), unsafe_allow_html=True)
                drivers = safe_parse_drivers(entry.get("fmgp_team", []))
                st.markdown(render_driver_box(drivers, "Riders"), unsafe_allow_html=True)
            else:
                st.warning(f"Team FMGP non risolto per riferimento: {team_ref}")

    # Right crown
    with colR:
        try:
            url_right = entry.get("right_crown_url") or 'https://koffsyfgevaannnmjkvl.supabase.co/storage/v1/object/sign/figures/crown_right.png'
            st.image(url_right, use_container_width=True)
        except Exception:
            pass

    # Footer informativo
    st.caption(f"Mostrando anno: {escape(anno_scelto)} — voci totali: {len(roll_data)}")
