import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
from logic.functions import _estimate_rows_height, safe_load_team_list, _render_pilot_buttons, _render_simple_table_html, safe_rgb_to_hex

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

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


# --------------------- CHAMPIONSHIP SCREEN ----------------------------------------------------

def championship_screen(user):
    loading_placeholder = st.empty()
    loading_placeholder.info("⏳ Loading...")

    teams = supabase.from_("teams").select("*").eq("league", str(user["league"])).execute().data or []    
    not_you = [team for team in teams if team.get("who") != user.get("who")]
    rules_f1 = supabase.from_("rules_f1_new").select("*").eq("league", str(user["league"])).execute().data or []
    rules_mgp = supabase.from_("rules_mgp_new").select("*").eq("league", str(user["league"])).execute().data or []

    loading_placeholder.empty()

    st.title("Other teams")

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
            
