import ast
import html as _html
from supabase import create_client
import streamlit as st
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from logic.functions import normalize_riders

# -------------------------------------------------------------------------------------------
# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Helper timezone (Italian time)
IT_TZ = ZoneInfo("Europe/Rome")

# --------------------- CALL-UP SCREEN ----------------------------------------------------

def callup_screen(user):
    """
    - Legge la league dell'utente e le impostazioni (team_constituent_*, active_*)
    - Legge i piloti SOLO dalla riga `teams` con UUID == user['UUID'] E league == user_league
    - Popola / aggiorna la riga in calls_f1_new / calls_mgp_new con uuid+league
    - Mostra la barra di avanzamento / countdown per la prossima gara
    - Mostra la tabella dei convocati (calls_f1_new / calls_mgp_new) di tutte le squadre sotto il pulsante
    """

    if st.session_state.get("force_rerun", False):
        st.session_state.force_rerun = False
        st.rerun()

    st.header("Call-ups")

    # ---------------- helpers ----------------
    def fetch_team_map():
        """Map class.team -> class.name (fallbacks)."""
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

    # helper name formatter (cleans brackets/quotes and formats First / Last)
    def clean_raw_name(n):
        if n is None:
            return ""
        s = str(n).strip()
        # if looks like a Python list string, try to literal_eval; otherwise strip outer brackets and quotes
        if s.startswith("[") and s.endswith("]"):
            # attempt to extract single element if someone stored a whole list into a field by mistake
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, (list, tuple)) and len(parsed) == 1:
                    s = str(parsed[0]).strip()
                else:
                    # if it's multiple elements, join them with comma (fallback)
                    s = ", ".join([str(x).strip() for x in parsed]) if isinstance(parsed, (list, tuple)) else s
            except Exception:
                s = s[1:-1].strip()
        # remove surrounding quotes if present
        if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
            s = s[1:-1].strip()
        # final cleanup of stray brackets/quotes
        s = s.strip().strip("[]").strip().strip('\'"')
        return s

    def format_name_for_display(name_raw):
        nm = clean_raw_name(name_raw)
        if not nm:
            return ""
        parts = nm.split()
        if len(parts) == 1:
            return _html.escape(parts[0])
        lower = nm.lower()
        if lower == 'fabio di giannantonio':
            first = _html.escape(parts[0])
            last = _html.escape(' '.join(parts[1:]))
            return f"<span class='name-first'>{first}</span><span class='name-last'>{last}</span>"
        first = _html.escape(parts[0])
        last = _html.escape(" ".join(parts[1:]))
        return f"<span class='name-first'>{first}</span><span class='name-last'>{last}</span>"

    def display_calls_table(table_name, team_map, caption=None, prev_limit_iso=None, league_id=None, champ_code=None):
        """
        Renders styled list of rows from `table_name` (calls_f1_new / calls_mgp_new).
        - Filtra per league se league_id è fornito.
        - Prima colonna: teams.name trovata cercando una riga in teams con UUID == calls_row['uuid'] e league == calls_row['league'].
        - Colonne dinamiche: in base alla configurazione di lega (N, A) mostra First/Second/... e First Reserve/Second Reserve/...
        - prev_limit_iso: se fornito, le righe con when < prev_limit_iso mostrano N/A (eccetto Team).
        """
        try:
            q = supabase.from_(table_name).select("*")
            if league_id:
                q = q.eq("league", league_id)
            calls = q.execute().data or []
        except Exception:
            calls = []

        if not calls:
            st.info(f"Nessuna chiamata disponibile per {table_name}.")
            return

        # get league config (N, A) if possible (fallback to defaults)
        N = None
        A = 0
        if league_id:
            try:
                lr = supabase.from_("leagues").select("*").eq("ID", league_id).limit(1).execute().data or []
                if lr:
                    lr0 = lr[0]
                    if champ_code == "F1":
                        N = lr0.get("team_constituent_f1") or lr0.get("team_constituent")
                        A = lr0.get("active_f1") if lr0.get("active_f1") is not None else 0
                    else:
                        N = lr0.get("team_constituent_mgp") or lr0.get("team_constituent")
                        A = lr0.get("active_mgp") if lr0.get("active_mgp") is not None else lr0.get("active_gp", 0)
            except Exception:
                pass

        # fallbacks and sanitization
        try:
            N = int(N) if N is not None else None
        except Exception:
            N = None
        try:
            A = int(A) if A is not None else 0
        except Exception:
            A = 0
        if N is None:
            N = 4  # best-effort fallback
        if A < 0:
            A = 0
        if A > 4:
            A = 4
        if A > N:
            A = N
        R = max(0, N - A)

        # build active/reserve field lists (max 4 supported)
        ACTIVE_FIELDS = ["first", "second", "third", "fourth"][:N]
        RESERVE_FIELDS = ["reserve", "reserve_two", "reserve_three", "reserve_four"][:R]

        # CSS
        st.markdown(
            """
        <style>
          .racers-container { font-family: sans-serif; color: #fff; }
          .header-row { display: flex; gap: 12px; padding: 10px 16px; font-weight: 700; background: #000; color: #fff; border-radius: 10px; align-items:center; }
          .row-box { display: flex; gap: 16px; padding: 12px 18px; align-items: center; border-radius: 12px; margin: 10px 0; background: linear-gradient(180deg,#1f1f1f,#171717); border: 1px solid rgba(255,255,255,0.03); min-height: 56px; }
          .row-box .col-team { flex: 6; font-weight: 700; color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
          .row-box .col-first { flex: 2; color: #ddd; overflow: hidden; text-overflow: ellipsis; white-space: normal; }
          .row-box .col-second { flex: 2; color: #ddd; overflow: hidden; text-overflow: ellipsis; white-space: normal; }
          .row-box .col-reserve { flex: 2; color: #ddd; overflow: hidden; text-overflow: ellipsis; white-space: normal; }
          .row-box .col-date { flex: 1; min-width: 140px; text-align: right; color: #fff; font-weight: 600; }
          .header-row .h-col { padding: 0 8px; }
          .name-first { display:block; font-size:14px; line-height:1.05; }
          .name-last { display:block; font-size:14px; line-height:1.05; opacity:0.95; }
        </style>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="racers-container">', unsafe_allow_html=True)

        if caption:
            st.markdown(f"<h4 style='margin:6px 0 10px 0;color:#fff;font-weight:700'>{_html.escape(caption)}</h4>", unsafe_allow_html=True)

        # build header columns dynamically
        header_cols_html = f'<div class="header-row"><div class="h-col" style="flex:6">Team</div>'
        labels_active = ["First", "Second", "Third", "Fourth"]
        for i in range(A):
            header_cols_html += f'<div class="h-col" style="flex:2">{labels_active[i]}</div>'
        labels_res = ["First Reserve", "Second Reserve", "Third Reserve", "Fourth Reserve"]
        for i in range(R):
            header_cols_html += f'<div class="h-col" style="flex:2">{labels_res[i]}</div>'
        header_cols_html += '<div class="h-col" style="flex:1; text-align:right; min-width:140px">Date</div></div>'
        st.markdown(header_cols_html, unsafe_allow_html=True)

        # prefetch teams by uuid for this league
        teams_by_uuid = {}
        try:
            if league_id:
                teams_rows = supabase.from_("teams").select("UUID,name,league").eq("league", league_id).execute().data or []
            else:
                teams_rows = supabase.from_("teams").select("UUID,name,league").execute().data or []
            for t in teams_rows:
                key = t.get("UUID")
                if key:
                    teams_by_uuid[key] = t.get("name") or teams_by_uuid.get(key)
        except Exception:
            teams_by_uuid = {}

        # parse prev_limit into aware dt (UTC assumed if naive)
        prev_limit_dt = None
        if prev_limit_iso:
            try:
                prev_limit_dt = datetime.fromisoformat(str(prev_limit_iso))
                if prev_limit_dt.tzinfo is None:
                    prev_limit_dt = prev_limit_dt.replace(tzinfo=timezone.utc)
            except Exception:
                prev_limit_dt = None

        for r in calls:
            # determine team name
            team_name = None
            try:
                calls_owner_uuid = r.get("uuid")
                if calls_owner_uuid:
                    team_name = teams_by_uuid.get(calls_owner_uuid)
                if not team_name:
                    team_field = r.get("team")
                    if isinstance(team_field, dict):
                        team_name = team_field.get("name") or team_field.get("Name") or str(team_field)
                    else:
                        team_name = team_map.get(team_field, team_field)
                if not team_name:
                    team_name = f"{_html.escape(str(r.get('uuid') or r.get('team') or 'Unknown'))}"
            except Exception:
                team_name = str(r.get("team") or r.get("uuid") or "Unknown")

            # build each cell value according to fields lists
            active_values = []
            for f in ACTIVE_FIELDS[:A]:
                v = r.get(f) or ""
                active_values.append(v)
            reserve_values = []
            for f in RESERVE_FIELDS[:R]:
                v = r.get(f) or ""
                reserve_values.append(v)

            # when / date formatting and prev_limit check
            when_raw = r.get("when") or r.get("When") or ""
            date_str = _html.escape(str(when_raw))

            show_na = False
            try:
                if prev_limit_dt and when_raw:
                    when_dt = datetime.fromisoformat(str(when_raw))
                    if when_dt.tzinfo is None:
                        when_dt = when_dt.replace(tzinfo=timezone.utc)
                    if when_dt < prev_limit_dt:
                        show_na = True
            except Exception:
                show_na = False

            if show_na:
                active_values = ["N/A"] * A
                reserve_values = ["N/A"] * R
                date_str = "N/A"
            else:
                try:
                    dt = datetime.fromisoformat(str(when_raw))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    dt_it = dt.astimezone(IT_TZ)
                    date_str = dt_it.strftime('%H:%M:%S, %d/%m/%Y')
                except Exception:
                    pass

            # format each name cell using format_name_for_display
            def fmt_cell(x):
                return format_name_for_display(x) if x and x != "N/A" else _html.escape(str(x or ""))

            # assemble row HTML
            row_html = '<div class="row-box">'
            row_html += f'<div class="col-team" title="{_html.escape(str(team_name))}">{_html.escape(str(team_name))}</div>'

            for i, val in enumerate(active_values):
                cls = "col-first" if i == 0 else ("col-second" if i == 1 else "col-reserve")
                row_html += f'<div class="{cls}" title="{_html.escape(str(val))}">{fmt_cell(val)}</div>'

            for i, val in enumerate(reserve_values):
                row_html += f'<div class="col-reserve" title="{_html.escape(str(val))}">{fmt_cell(val)}</div>'

            row_html += f'<div class="col-date">{_html.escape(date_str)}</div>'
            row_html += '</div>'

            st.markdown(row_html, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    def ensure_calls_row(table_name, user_uuid, league_id=None):
        """
        Ensure a row exists in calls_*_new for this user's uuid AND league.
        Returns the row dict (freshly read).
        """
        try:
            q = supabase.from_(table_name).select("*").eq("uuid", user_uuid)
            if league_id:
                q = q.eq("league", league_id)
            resp = q.limit(1).execute()
            rows = resp.data or []
            if rows:
                return rows[0]
            base = {"uuid": user_uuid}
            if league_id:
                base["league"] = league_id
            ins = supabase.from_(table_name).insert([base]).execute()
            if getattr(ins, "error", None):
                return base
            return (ins.data or [base])[0]
        except Exception:
            return {"uuid": user_uuid, "league": league_id}

    def build_calls_payload_from_selections(active_selected, reserve_selected):
        payload = {}
        active_cols = ["first", "second", "third", "fourth"]
        for i, v in enumerate(active_selected):
            if i < len(active_cols):
                payload[active_cols[i]] = v
        for j in range(len(active_selected), len(active_cols)):
            payload[active_cols[j]] = None

        reserve_cols = ["reserve", "reserve_two", "reserve_three", "reserve_four"]
        for i, v in enumerate(reserve_selected):
            if i < len(reserve_cols):
                payload[reserve_cols[i]] = v
        for j in range(len(reserve_selected), len(reserve_cols)):
            payload[reserve_cols[j]] = None

        return payload

    def read_team_row_for_user(user_uuid, league_id):
        """Read the row in 'teams' for this user uuid and league. Returns the row dict or None."""
        try:
            resp = supabase.from_("teams").select("*").eq("UUID", user_uuid).eq("league", league_id).limit(1).execute()
            rows = resp.data or []
            return rows[0] if rows else None
        except Exception:
            return None

    def extract_drivers_from_team_row(row, category_key):
        """Extract list of drivers from teams row for the category (only from this row)."""
        if not row:
            return []
        if category_key == "F1":
            candidates = ["F1", "f1", "F1drivers", "drivers_f1", "drivers"]
        else:
            candidates = ["MotoGP", "MGP", "mgp", "MotoGPdrivers", "drivers_mgp", "moto", "moto_gp"]
        for key in candidates:
            val = row.get(key)
            if val:
                # If already a list, normalize directly
                if isinstance(val, list):
                    return normalize_riders(val)
                # If string, try to parse as Python literal (e.g. "['Name1','Name2']") safely
                if isinstance(val, str):
                    s = val.strip()
                    # try literal_eval (handles Python-list-like strings)
                    try:
                        parsed = ast.literal_eval(s)
                        if isinstance(parsed, (list, tuple)):
                            parts = [str(x).strip() for x in parsed if x is not None and str(x).strip()]
                            if parts:
                                return normalize_riders(parts)
                    except Exception:
                        # fallback: remove outer brackets and quotes then split on commas
                        if s.startswith("[") and s.endswith("]"):
                            s_inner = s[1:-1]
                        else:
                            s_inner = s
                        # split and strip surrounding quotes/spaces
                        parts = [p.strip().strip("'\"") for p in s_inner.split(",") if p.strip()]
                        if parts:
                            return normalize_riders(parts)
        return []

    # ---------------- section renderer ----------------
    def render_section(category_name, champ_code, user_key, calls_new_table, calls_public_table):
        """
        calls_new_table: where to save (calls_f1_new / calls_mgp_new)
        calls_public_table: (unused for now) kept for compatibility
        """
        st.subheader(category_name)

        # user and league
        user_uuid = user.get("UUID")
        league_id = user.get("league") or user.get("league_id") or st.session_state.get("selected_league")

        # read team row for this user+league (drivers MUST come from here)
        team_row = read_team_row_for_user(user_uuid, league_id)
        drivers = extract_drivers_from_team_row(team_row, category_name)
        drivers = normalize_riders(drivers)

        # league settings
        if champ_code == "F1":
            champ_table = "championship_f1_new"
            N = None
            A = 0
        else:
            champ_table = "championship_mgp_new"
            N = None
            A = 0

        # load league row
        league_row = None
        if league_id:
            try:
                resp = supabase.from_("leagues").select("*").eq("ID", league_id).limit(1).execute()
                lr = resp.data or []
                if lr:
                    league_row = lr[0]
            except Exception:
                league_row = None

        if league_row:
            if champ_code == "F1":
                N = league_row.get("team_constituent_f1") or league_row.get("team_constituent")
                A = league_row.get("active_f1") if league_row.get("active_f1") is not None else 0
            else:
                N = league_row.get("team_constituent_mgp")
                A = league_row.get("active_mgp") if league_row.get("active_mgp") is not None else league_row.get("active_gp", 0)

        # fallbacks in case league not found
        try:
            N = int(N) if N is not None else None
        except Exception:
            N = None
        try:
            A = int(A) if A is not None else 0
        except Exception:
            A = 0

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
        R = max(0, N - A)

        # if drivers empty, block (require team row to include pilots)
        if not drivers:
            st.error("Nessun pilota trovato per il tuo team in questa lega. Assicurati che la riga in `teams` (UUID + league) contenga i piloti per questa categoria.")
            return

        # ensure calls_new row exists (scoped to league)
        calls_row = ensure_calls_row(calls_new_table, user_uuid, league_id)

        # — show next race name and progress bar (pull championship table)
        next_race = None
        howmany = 0
        try:
            champ = supabase.from_(champ_table).select("*").execute().data or []
            for element in champ:
                if element.get('number', 0) >= howmany:
                    howmany = element.get('number', 0)
            for race in champ:
                if race.get("status") is True:
                    next_race = race
                    break
        except Exception:
            champ = []
            next_race = None

        if next_race:
            # compute limit dt as aware (assume UTC if naive)
            try:
                limit_dt = datetime.fromisoformat(next_race["limit"])
                if limit_dt.tzinfo is None:
                    limit_dt = limit_dt.replace(tzinfo=timezone.utc)
            except Exception:
                limit_dt = None

            if limit_dt:
                now_utc = datetime.now(timezone.utc)
                delta = limit_dt - now_utc
                remaining_seconds = delta.total_seconds()
            else:
                remaining_seconds = None

            # render race box
            st.markdown(f"""
                <div style="
                    background-color: #2f2f2f;
                    color: #eee;
                    padding: 12px;
                    border-radius: 10px;
                    margin-bottom: 10px;
                    border: 2px solid red;
                    font-weight: bold;
                ">
                    Next race: {_html.escape(next_race.get('ID',''))} ({next_race.get('number','')}/{howmany})
                </div>
            """, unsafe_allow_html=True)

            # progress logic (week window)
            WEEK = 7 * 24 * 3600
            if remaining_seconds is None:
                progress = 0.0
            elif remaining_seconds < 0:
                progress = 1.0
            elif remaining_seconds > WEEK:
                progress = 0.0
            else:
                progress = max(0.0, min(1.0, 1.0 - (remaining_seconds / WEEK)))

            # color thresholds
            TH_30_MIN = 30 * 60
            TH_2_HOURS = 2 * 3600
            TH_1_DAY = 24 * 3600

            if remaining_seconds is None:
                color_bar = "#28a745"
                days = hours = minutes = seconds = 0
            elif remaining_seconds < 0:
                color_bar = "#dc3545"
                days = hours = minutes = seconds = 0
            else:
                if remaining_seconds <= TH_30_MIN:
                    color_bar = "#dc3545"
                elif remaining_seconds <= TH_2_HOURS:
                    color_bar = "#ff9800"
                elif remaining_seconds <= TH_1_DAY:
                    color_bar = "#ffc107"
                else:
                    color_bar = "#28a745"
                days = delta.days
                hours, remainder = divmod(delta.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)

            st.markdown(f"""
                <div style="
                    background-color: #444;
                    border-radius: 20px;
                    overflow: hidden;
                    height: 18px;
                    margin-bottom: 6px;
                ">
                    <div style="
                        width: {100*progress:.1f}%;
                        height: 100%;
                        background-color: {color_bar};
                        transition: width 0.4s ease;
                    "></div>
                </div>
                <div style="color:#ddd; font-weight:600; margin-bottom: 12px;">
                    Remaining time: {days} days, {hours} hours, {minutes} minutes, {seconds} seconds
                </div>
            """, unsafe_allow_html=True)

        # prepare select keys and defaults
        active_keys = [f"{calls_new_table}_active_{i}" for i in range(A)]
        reserve_keys = [f"{calls_new_table}_reserve_{i}" for i in range(R)]

        for i, k in enumerate(active_keys):
            existing_val = None
            if calls_row:
                try:
                    existing_val = calls_row.get(["first","second","third","fourth"][i])
                except Exception:
                    existing_val = None
            default_val = existing_val if existing_val else (drivers[i] if i < len(drivers) else "")
            st.session_state.setdefault(k, default_val)

        for i, k in enumerate(reserve_keys):
            existing_val = None
            if calls_row:
                try:
                    existing_val = calls_row.get(["reserve","reserve_two","reserve_three","reserve_four"][i])
                except Exception:
                    existing_val = None
            default_val = existing_val if existing_val else (drivers[A + i] if (A + i) < len(drivers) else "")
            st.session_state.setdefault(k, default_val)

        st.write("")  # spacing

        # build ordered selects with uniqueness (do NOT pass index -> avoid Streamlit warning)
        chosen = []
        active_selected = []
        for i, k in enumerate(active_keys):
            opts = [d for d in drivers if d not in chosen]
            cur = st.session_state.get(k, "")
            if cur and cur not in opts:
                opts = [cur] + opts
            label = ["First", "Second", "Third", "Fourth"][i] if i < 4 else f"Active {i+1}"
            val = st.selectbox(f"{label} ({category_name})", opts, key=k)
            if val:
                chosen.append(val)
            active_selected.append(val)

        reserve_selected = []
        for i, k in enumerate(reserve_keys):
            opts = [d for d in drivers if d not in chosen]
            cur = st.session_state.get(k, "")
            if cur and cur not in opts:
                opts = [cur] + opts
            label = ["Reserve", "Reserve Two", "Reserve Three", "Reserve Four"][i] if i < 4 else f"Reserve {i+1}"
            val = st.selectbox(f"{label} ({category_name})", opts, key=k)
            if val:
                chosen.append(val)
            reserve_selected.append(val)

        st.write("")

        # save
        save_key = f"save_{calls_new_table}_{user_uuid}"
        if st.button(f"Save {category_name} Call-up", key=save_key):
            all_selected = [v for v in (active_selected + reserve_selected) if v]
            if len(all_selected) < (A + R):
                st.error(f"You shall select {A + R} racers ({A} actives + {R} reserves).")
            elif len(set(all_selected)) < len(all_selected):
                st.error("You shall select different racers.")
            else:
                payload = build_calls_payload_from_selections(active_selected, reserve_selected)
                payload["when"] = datetime.now(timezone.utc).isoformat()
                try:
                    upd = supabase.table(calls_new_table).update(payload).eq("uuid", user_uuid).eq("league", league_id).execute()
                    if getattr(upd, "error", None) or (getattr(upd, "data", None) is None or len(upd.data) == 0):
                        to_insert = dict(payload)
                        to_insert["uuid"] = user_uuid
                        if league_id:
                            to_insert["league"] = league_id
                        ins = supabase.from_(calls_new_table).insert([to_insert]).execute()
                        if getattr(ins, "error", None):
                            st.error(f"Insert failed: {ins.error}")
                        else:
                            st.success("Call-up saved (insert).")
                    else:
                        st.success("Call-up updated successfully.")
                except Exception as e:
                    st.error(f"Exception while saving call-up: {e}")

        # --- display calls table of other teams (public) under the button ---
        team_map = fetch_team_map()

        # determine prev_limit_iso: the latest race with status False before current True one
        prev_limit_iso = None
        try:
            prev_candidates = [x for x in champ if x.get('number') < (next_race.get('number') if next_race else -1) and x.get('status') is False]
            if prev_candidates:
                prev_race = max(prev_candidates, key=lambda z: z.get('number', 0))
                prev_limit_iso = prev_race.get('limit')
        except Exception:
            prev_limit_iso = None

        if calls_public_table:
            caption = "Call-ups | F1" if champ_code == "F1" else "Call ups | MotoGP"
            # show the *new* calls table filtered to this league so the UI reflects calls_f1_new / calls_mgp_new
            display_calls_table(calls_new_table, team_map, caption=caption, prev_limit_iso=prev_limit_iso, league_id=league_id, champ_code=champ_code)

    # --- top-level: determine user's league and render sections ---
    user_league_id = user.get("league") or user.get("league_id") or st.session_state.get("selected_league")
    if not user_league_id:
        st.warning("League not found for this user (user['league'] missing). Cannot apply league-specific rules.")
        league_row = {"ID": None, "team_constituent_f1": 3, "team_constituent_mgp": 3, "active_f1": 1, "active_mgp": 1}
    else:
        league_resp = supabase.from_("leagues").select("*").eq("ID", user_league_id).limit(1).execute()
        league_rows = league_resp.data or []
        if league_rows:
            league_row = league_rows[0]
        else:
            st.warning(f"League '{user_league_id}' not found in DB; using defaults.")
            league_row = {"ID": user_league_id, "team_constituent_f1": 3, "team_constituent_mgp": 3, "active_f1": 1, "active_mgp": 1}

    # render F1 (save into calls_f1_new, show calls_f1 table)
    render_section("F1", "F1", "F1", "calls_f1_new", "calls_f1")

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

    # render MotoGP (save into calls_mgp_new, show calls_mgp table)
    render_section("MotoGP", "MGP", "MotoGP", "calls_mgp_new", "calls_mgp")

    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("Back to team"):
        st.session_state.screen = "team"
        st.rerun()
