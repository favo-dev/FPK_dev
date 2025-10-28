import html as _html
from supabase import create_client
import streamlit as st
from datetime import datetime, timezone
from logic.functions import normalize_riders

# -------------------------------------------------------------------------------------------
# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --------------------- CALL-UP SCREEN ----------------------------------------------------

def callup_screen(user):
    """
    Nuova logica:
    - legge la league dell'utente (user) e i campi team_constituent_* e active_*
    - popola/aggiorna la riga in calls_f1_new / calls_mgp_new con uuid == user['UUID']
    - mostra dinamicamente A selectboxes per gli active slots (A = active_*) e R = N - A
      selectboxes per le riserve dove N = team_constituent_*.
    - aggiorna Supabase al submit
    """

    if st.session_state.get("force_rerun", False):
        st.session_state.force_rerun = False
        st.rerun()

    st.header("Call-ups")

    def fetch_team_map():
        """Try to map class.team -> class.name, with sensible fallbacks."""
        try:
            class_rows = supabase.from_("class_new").select("team,name").execute().data
            if class_rows:
                return {r.get("team"): r.get("name") for r in class_rows if r.get("team") is not None}
        except Exception:
            pass
        try:
            class_rows = supabase.from_("class").select("ID,name").execute().data
            if class_rows:
                return {r.get("ID"): r.get("name") for r in class_rows}
        except Exception:
            pass
        try:
            teams_rows = supabase.from_("teams").select("team,name,ID").execute().data
            if teams_rows:
                mapping = {}
                for r in teams_rows:
                    key = r.get("team") if r.get("team") is not None else r.get("ID")
                    mapping[key] = r.get("name")
                return mapping
        except Exception:
            pass
        return {}

    def ensure_calls_row(table_name, user_uuid, league_id=None):
        """
        Ensure a row exists in calls_*_new for this user's uuid.
        Returns the row dict (freshly read).
        """
        try:
            resp = supabase.from_(table_name).select("*").eq("uuid", user_uuid).limit(1).execute()
            rows = resp.data or []
            if rows:
                return rows[0]
            # if no row exists, create a minimal one (uuid + league if available)
            base = {"uuid": user_uuid}
            if league_id:
                base["league"] = league_id
            ins = supabase.from_(table_name).insert([base]).execute()
            if getattr(ins, "error", None):
                # insertion failed, but return the base to avoid crashes
                return base
            return (ins.data or [base])[0]
        except Exception:
            return {"uuid": user_uuid}

    # helper to build update payload with variable active/reserve fields
    def build_calls_payload_from_selections(active_selected, reserve_selected):
        """
        active_selected: list ordered ['Driver A', 'Driver B', ...] (len A)
        reserve_selected: list ordered ['Res A', 'Res B', ...] (len R)
        returns dict mapping column names -> values
        """
        payload = {}
        # map active slots
        active_cols = ["first", "second", "third", "fourth"]
        for i, v in enumerate(active_selected):
            if i < len(active_cols):
                payload[active_cols[i]] = v
        # fill remaining active cols with empty string / None if not used
        for j in range(len(active_selected), len(active_cols)):
            payload[active_cols[j]] = None

        # reserves mapping
        reserve_cols = ["reserve", "reserve_two", "reserve_three", "reserve_four"]
        for i, v in enumerate(reserve_selected):
            if i < len(reserve_cols):
                payload[reserve_cols[i]] = v
        # clear extra reserve cols if not used
        for j in range(len(reserve_selected), len(reserve_cols)):
            payload[reserve_cols[j]] = None

        return payload

    def render_section(category_name, champ_code, user_key, calls_table_name, league):
        """Render UI for a specific category (F1 / MotoGP) and handle saving."""
        st.subheader(category_name)

    # drivers available from user's profile
        drivers = user.get(user_key, []) or []
        drivers = normalize_riders(drivers)

    # league settings for this category
        if champ_code == "F1":
            N = league.get("team_constituent_f1") or league.get("team_constituent") or None
            A = league.get("active_f1") if league.get("active_f1") is not None else 0
        else:
            N = league.get("team_constituent_mgp") or None
            A = league.get("active_mgp") if league.get("active_mgp") is not None else league.get("active_gp", 0)

        try:
            N = int(N) if N is not None else None
        except Exception:
            N = None
        try:
            A = int(A) if A is not None else 0
        except Exception:
            A = 0

    # sanity bounds
        if N is None:
            st.warning(f"League configuration missing team size for {category_name}.")
            return
        if N < 1:
            st.warning(f"Invalid team size ({N}) for {category_name}.")
            return
        if A < 0:
            A = 0
        if A > 4:
            A = 4
        if A > N:
            A = N

        R = max(0, N - A)  # number of reserves

        if len(drivers) < N:
            st.error(f"Hai solo {len(drivers)} piloti disponibili ma la squadra richiede {N}. Aggiorna la tua rosa prima.")

    # ensure calls row exists
        user_uuid = user.get("UUID")
        calls_row = ensure_calls_row(calls_table_name, user_uuid, league.get("ID"))

        st.markdown(f"**Team size:** {N} — **Active slots:** {A} — **Reserves:** {R}")

    # prepare keys and session defaults
        active_keys = [f"{calls_table_name}_active_{i}" for i in range(A)]
        reserve_keys = [f"{calls_table_name}_reserve_{i}" for i in range(R)]

    # initialize defaults in session_state if missing (but do it BEFORE creating widgets)
        for i, k in enumerate(active_keys):
            existing_val = None
            if i == 0:
                existing_val = calls_row.get("first")
            elif i == 1:
                existing_val = calls_row.get("second")
            elif i == 2:
                existing_val = calls_row.get("third")
            elif i == 3:
                existing_val = calls_row.get("fourth")
            default_val = existing_val if existing_val else (drivers[i] if i < len(drivers) else "")
            st.session_state.setdefault(k, default_val)

        for i, k in enumerate(reserve_keys):
            existing_val = None
            if i == 0:
                existing_val = calls_row.get("reserve")
            elif i == 1:
                existing_val = calls_row.get("reserve_two")
            elif i == 2:
                existing_val = calls_row.get("reserve_three")
            elif i == 3:
                existing_val = calls_row.get("reserve_four")
            default_val = existing_val if existing_val else (drivers[A + i] if (A + i) < len(drivers) else "")
            st.session_state.setdefault(k, default_val)

        st.write("")  # spacing

    # Build ordered selection UI ensuring uniqueness
        chosen = []

    # Active selects
        active_selected = []
        for i, k in enumerate(active_keys):
        # options exclude already chosen ones
            opts = [d for d in drivers if d not in chosen]
            cur = st.session_state.get(k, "")
            if cur and cur not in opts:
                opts = [cur] + opts
        # safe index computation
            try:
                idx = opts.index(cur) if cur in opts else 0
            except Exception:
                idx = 0
            label = ["First", "Second", "Third", "Fourth"][i] if i < 4 else f"Active {i+1}"
        # create widget (do NOT assign into st.session_state here)
            val = st.selectbox(f"{label} ({category_name})", opts, index=idx, key=k)
        # val is now stored in st.session_state[k] by Streamlit
            if val:
                chosen.append(val)
            active_selected.append(val)

    # Reserve selects
        reserve_selected = []
        for i, k in enumerate(reserve_keys):
            opts = [d for d in drivers if d not in chosen]
            cur = st.session_state.get(k, "")
            if cur and cur not in opts:
                opts = [cur] + opts
            try:
                idx = opts.index(cur) if cur in opts else 0
            except Exception:
                idx = 0
            label = ["Reserve", "Reserve Two", "Reserve Three", "Reserve Four"][i] if i < 4 else f"Reserve {i+1}"
            val = st.selectbox(f"{label} ({category_name})", opts, index=idx, key=k)
            if val:
                chosen.append(val)
            reserve_selected.append(val)

        st.write("")  # spacing

    # Save button handling
        save_key = f"save_{calls_table_name}_{user_uuid}"
        if st.button(f"Save {category_name} Call-up", key=save_key):
            all_selected = [v for v in (active_selected + reserve_selected) if v]
            if len(all_selected) < (A + R):
                st.error(f"Devi selezionare tutti i {A + R} piloti richiesti ({A} attivi + {R} riserve).")
                return
            if len(set(all_selected)) < len(all_selected):
                st.error("Devi selezionare piloti distinti, senza duplicati.")
                return

            payload = build_calls_payload_from_selections(active_selected, reserve_selected)
            payload["when"] = datetime.now(timezone.utc).isoformat()

            try:
                upd = supabase.table(calls_table_name).update(payload).eq("uuid", user_uuid).execute()
                if getattr(upd, "error", None) or (upd.data is None or len(upd.data) == 0):
                # fallback: insert (include uuid + league)
                    to_insert = dict(payload)
                    to_insert["uuid"] = user_uuid
                    if league and league.get("ID"):
                        to_insert["league"] = league.get("ID")
                    ins = supabase.from_(calls_table_name).insert([to_insert]).execute()
                    if getattr(ins, "error", None):
                        st.error(f"Insert failed: {ins.error}")
                        return
                    st.success("Call-up saved (insert).")
                    return
                st.success("Call-up updated successfully.")
            except Exception as e:
                st.error(f"Exception while saving call-up: {e}")


    # --- top-level: determine user's league ---
    # the user's league might be stored in user['league'] or user['league_id'] or in session selected_league
    user_league_id = user.get("league") or user.get("league_id") or st.session_state.get("selected_league")
    if not user_league_id:
        st.warning("League not found for this user (user['league'] missing). Cannot apply league-specific rules.")
        # Still attempt to render a simple fallback: use default N=3, A=1
        league_row = {"ID": None, "team_constituent_f1": 3, "team_constituent_mgp": 3, "active_f1": 1, "active_mgp": 1}
    else:
        league_resp = supabase.from_("leagues").select("*").eq("ID", user_league_id).limit(1).execute()
        league_rows = league_resp.data or []
        if league_rows:
            league_row = league_rows[0]
        else:
            st.warning(f"League '{user_league_id}' not found in DB; using defaults.")
            league_row = {"ID": user_league_id, "team_constituent_f1": 3, "team_constituent_mgp": 3, "active_f1": 1, "active_mgp": 1}

    # render F1 section and connect it to calls_f1_new
    render_section("F1", "F1", "F1", "calls_f1_new", league_row)

    st.markdown(
        """
        <hr style="
            border: 1.5px solid #555;
            margin: 40px 0 30px 0;
            border-radius: 5px;
        ">
        """,
        unsafe_allow_html=True,
    )

    # render MotoGP section and connect it to calls_mgp_new
    render_section("MotoGP", "MGP", "MotoGP", "calls_mgp_new", league_row)




    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("Back to team"):
        st.session_state.screen = "team"
        st.rerun()
