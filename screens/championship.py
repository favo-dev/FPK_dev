import streamlit as st
import streamlit.components.v1 as components
from logic.functions import _estimate_rows_height, safe_load_team_list, _render_pilot_buttons, _render_simple_table_html, rgb_to_hex, get_supabase_client

# -------------------------------------------------------------------------------------------


# --------------------- SCREENS ----------------------------------------------

def show_rules_screen(rules_list, screen_name):
    """Mostra le regole in un container isolato (iframe)."""
    st.title("Rules for " + ("F1" if screen_name == "rules_f1" else "MotoGP"))

    if not rules_list:
        st.write("No rules available.")
        return

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

    if st.button("Go back", key="rules_go_back"):
        st.session_state.screen = "championship"
        st.rerun()

def championship_screen(user):
    # Placeholder per il caricamento
    loading_placeholder = st.empty()
    loading_placeholder.info("⏳ Loading...")

    # Carico dati
    teams = supabase.from_("class").select("*").execute().data or []
    not_you = [team for team in teams if team.get("who") != user.get("who")]
    rules_f1 = supabase.from_("rules_f1").select("*").execute().data or []
    rules_mgp = supabase.from_("rules_mgp").select("*").execute().data or []

    # Rimuovo placeholder
    loading_placeholder.empty()

    st.title("Other teams")

    for team in not_you:
        with st.expander(f"{team.get('name','N/A')} - {team.get('who','N/A')}"):
            # Colori (barra responsive)
            main_hex = rgb_to_hex(team.get("main color", [0,0,0]))
            second_hex = rgb_to_hex(team.get("second color", [100,100,100]))
            st.markdown(
                f"""
                <div style='display: flex; align-items: center; gap: 1rem; width:100%;'>
                    <div style='width: 100%; height: 10px; background-color: {main_hex}; border: 2px solid {second_hex}; border-radius: 4px;'></div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Info team
            st.markdown(f"**Founded in**: {team.get('foundation', 'N/A')}")
            st.markdown(f"**Location**: {team.get('where', 'N/A')}")
            st.markdown(f"**FF1**: {team.get('ff1', 'N/A')}")
            st.markdown(f"**Fmgp**: {team.get('fmgp', 'N/A')}")
            st.markdown(f"**FPK**: {team.get('fm', 'N/A')}")
            st.markdown(f"**Mail:** {team.get('mail','N/A')}")

            # --- F1 team ---
            st.markdown("**F1 team:**")
            f1_team = safe_load_team_list(team.get("F1", []))
            if f1_team:
                _render_pilot_buttons(f1_team, "f1", team.get('ID'))

            # --- MotoGP team ---
            st.markdown("**MotoGP team:**")
            mgp_team = safe_load_team_list(team.get("MotoGP", []))
            if mgp_team:
                _render_pilot_buttons(mgp_team, "mgp", team.get('ID'))

    # --- Rules ---
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
            
