import streamlit as st
import ast
import json
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
    st.subheader("Compute results")

    # ---- Categoria ----
    category = st.selectbox(
        "Select category",
        ["F1", "MotoGP"],
        index=0 if st.session_state.compute_category is None else ["F1", "MotoGP"].index(st.session_state.compute_category)
    )
    st.session_state.compute_category = category

    # ---- Tabella championship corretta ----
    table_name = "championship_f1_new" if category == "F1" else "championship_mgp_new"

    # ---- Fetch gare ----
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
        st.warning("No races available for this category.")
        return

    # ---- Selezione gara ----
    race_id = st.selectbox(
        "Select race",
        races,
        index=0 if st.session_state.compute_race_id is None else max(0, races.index(st.session_state.compute_race_id))
    )
    st.session_state.compute_race_id = race_id

    # ---- Azioni ----
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Cancel", key="compute_cancel"):
            st.session_state.compute_results_open = False
            st.session_state.compute_category = None
            st.session_state.compute_race_id = None
            st.rerun()

    with col2:
        if st.button("Confirm compute", key="compute_confirm"):
            run_compute_results(
                league_id=league_id,
                category=category,
                race_id=race_id
            )
            st.success(f"Results computed for {category} – race {race_id}")
            st.session_state.compute_results_open = False
            st.rerun()
            
def run_compute_results(league_id: str, category: str, race_id: str):
    """
    Punto di ingresso unico per il calcolo risultati.
    Qui puoi:
    - chiamare una RPC Postgres
    - oppure fare calcoli Python + update su Supabase
    """
    try:
        # ESEMPIO RPC (consigliato se hai logica DB):
        # supabase.rpc(
        #     "compute_results",
        #     {
        #         "league_id": league_id,
        #         "category": category.lower(),
        #         "race_id": race_id
        #     }
        # ).execute()

        # Placeholder
        print(f"Computing {category} results for race {race_id} (league {league_id})")

    except Exception as e:
        st.error(f"Compute failed: {e}")

def compute_results_for_league(league_id: str):
    """
    Placeholder per la logica di calcolo. 
    Se hai una funzione RPC lato DB chiamata 'compute_results' che accetta league_id, viene invocata.
    Altrimenti ritorna un dict di esempio; sostituisci con la tua logica.
    """
    if not league_id:
        return {"error": "league_id mancante"}
    try:
        # se hai una RPC Postgres chiamata compute_results(league_id uuid) la puoi usare:
        resp = supabase.rpc("compute_results", {"league_id": league_id}).execute()
        # resp potrebbe avere .data o .error a seconda della libreria
        return resp
    except Exception:
        # fallback: semplicemente ritorna un valore di successo simulato
        return {"data": f"Compute simulated for league {league_id}"}


# --------------------- CHAMPIONSHIP SCREEN ----------------------------------------------------

def championship_screen(user):
    loading_placeholder = st.empty()
    loading_placeholder.info("Loading...")

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

    # recupera user_uuid e league_id dallo user passato
    user_uuid = (user.get("UUID") or user.get("uuid")) if isinstance(user, dict) else None
    league_id = str(user.get("league")) if isinstance(user, dict) and user.get("league") is not None else None

    # verifica se è presidente (usa la funzione helper)
    is_president = user_is_president(user_uuid, league_id)

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

# -------------------- COMPUTE RESULTS --------------------

    if is_president:
        st.markdown("")
        if st.button("Compute results", key="compute_results_btn"):
            st.session_state.compute_results_open = True
            st.rerun()

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

