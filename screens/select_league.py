import html as _html
import json
import hashlib
import uuid
from datetime import datetime
import streamlit as st
from supabase import create_client, Client
from logic.functions import go_to_screen
from screens.home import home_screen

# -------------------------------------------------------------------------------------------
# --------------------- SUPABASE CLIENT -----------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# init session keys
if "go" not in st.session_state:
    st.session_state.go = False
if "league_visibility" not in st.session_state:
    st.session_state.league_visibility = "Public"
if "league_pw_input" not in st.session_state:
    st.session_state.league_pw_input = ""
# keep other form-related keys initially empty to avoid KeyError
for k in ("league_name", "league_location", "team_name", "team_location", "main_color_hex", "second_color_hex"):
    if k not in st.session_state:
        st.session_state[k] = ""

# -------------------------------------------------------------------------------------------
# --------------------- UTILITY -------------------------------------------------------------
def hex_to_rgb(hex_color: str):
    """Converte colore esadecimale (es. #00CAFF) in lista [R,G,B]"""
    if not hex_color:
        return None
    s = hex_color.strip().lstrip("#")
    if len(s) == 3:
        s = "".join([c * 2 for c in s])
    if len(s) != 6:
        return None
    try:
        r = int(s[0:2], 16)
        g = int(s[2:4], 16)
        b = int(s[4:6], 16)
        return [r, g, b]
    except Exception:
        return None

# -------------------------------------------------------------------------------------------
# --------------------- CREA TEAM -----------------------------------------------------------
def build_team(user, league_id, team_name, main_color_rgb, second_color_rgb, team_location, foundation):
    """
    Crea una riga nella tabella `teams`.
    Usa i nomi di colonna esatti (con spazio) che hai in Supabase:
    "main color" e "second color".
    """
    if not user:
        st.error("User non disponibile. Impossibile creare la squadra.")
        return None

    if not team_name:
        st.error("Inserisci il nome della squadra.")
        return None
    if not team_location:
        st.error("Inserisci la location della squadra.")
        return None

    def valid_color_list(col):
        return (
            isinstance(col, list)
            and len(col) == 3
            and all(isinstance(v, int) and 0 <= v <= 255 for v in col)
        )

    if not valid_color_list(main_color_rgb):
        st.error("Colore principale non valido. Usa il color picker.")
        return None
    if not valid_color_list(second_color_rgb):
        st.error("Colore secondario non valido. Usa il color picker.")
        return None

    new_team = {
        "who": user.get("who"),
        "name": team_name.strip(),
        "mail": user.get("mail"),
        # ATTENZIONE: nomi colonna con spazi come nel tuo DB
        "main color": main_color_rgb,
        "second color": second_color_rgb,
        "where": team_location.strip(),
        "foundation": foundation,
        "UUID": user.get("UUID"),
        "league": league_id,
    }

    insert_resp = supabase.from_("teams").insert(new_team).execute()
    if getattr(insert_resp, "error", None):
        st.error(f"Errore nella creazione della squadra: {insert_resp.error}")
        return None

    try:
        inserted_row = (insert_resp.data or [None])[0]
    except Exception:
        inserted_row = None
    if not inserted_row:
        inserted_row = new_team

    st.success(f"Team '{team_name}' created")
    st.session_state["user"] = inserted_row
    return inserted_row

# -------------------------------------------------------------------------------------------
# --------------------- LEAGUE SCREEN -------------------------------------------------------
def league_screen(user):
    # se il flag go è attivo, mostra la home e stoppa il resto
    if st.session_state.go:
        home_screen(user)
        st.stop()

    st.title("League hub")
    st.subheader("Your leagues")

    player_uuid = user.get("UUID")
    if not player_uuid:
        st.warning("UUID not found for this user.")
        return

    teams_rows = supabase.from_("teams").select("league").eq("UUID", player_uuid).execute().data or []
    league_ids = list({row.get("league") for row in teams_rows if row.get("league")})

    # --- STYLE --------------------------------------------------------------------------
    st.markdown(
        """
    <style>
      .league-container { font-family: sans-serif; color: #fff; }
      .header-row { display: flex; gap: 16px; padding: 12px 20px; font-weight: 700; background: #000; color: #fff; border-radius: 12px; align-items:center; }
      .row-box { display: flex; gap: 18px; padding: 16px 22px; align-items: center; border-radius: 18px; margin: 12px 0; background: linear-gradient(180deg,#1f1f1f,#171717); border: 1px solid rgba(255,255,255,0.03); min-height: 76px; }
      .row-box .col-name { flex: 5; font-weight: 700; color: #fff; overflow: visible; text-overflow: ellipsis; white-space: normal; }
      .row-box .col-location { flex: 4; color: #ddd; overflow: visible; text-overflow: ellipsis; white-space: normal; line-height: 1.3; }
      .row-box .col-foundation { flex: 3; color: #bbb; overflow: visible; text-overflow: ellipsis; white-space: normal; line-height: 1.3; }
      .row-box .col-members { flex: 0 0 120px; text-align: right; font-weight: 600; color: #fff; margin-right: 8px; }

      /* header column sizing */
      .header-row .h-col { padding: 0 10px; }
      .header-row .h-name { flex: 5; }
      .header-row .h-location { flex: 4; }
      .header-row .h-foundation { flex: 3; }
      .header-row .h-members { flex: 0 0 120px; text-align:right; }

      /* bottone Info perfettamente centrato e non sovrapposto */
      .stButton { 
          display: flex; 
          align-items: center; 
          justify-content: center; 
          height: 76px; 
          margin-left: 12px; 
          margin-right: 12px;
      }
      div.stButton > button { 
          padding: 6px 14px !important; 
          border-radius: 14px !important; 
          min-width: 90px; 
          white-space: nowrap; 
          font-weight: 600; 
          height: 36px; 
          line-height: 16px; 
      }

      .no-results { color: #ddd; padding: 12px 0; }
    </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="league-container">', unsafe_allow_html=True)

    # header
    left_hcol, btn_hcol = st.columns([0.90, 0.10])
    header_html = (
        '<div class="header-row">'
        '<div style="width:40px"></div>'
        '<div class="h-col h-name">Name</div>'
        '<div class="h-col h-location">Location</div>'
        '<div class="h-col h-foundation">Foundation</div>'
        '<div class="h-col h-members">Members</div>'
        '</div>'
    )
    left_hcol.markdown(header_html, unsafe_allow_html=True)
    btn_hcol.markdown('<div style="height:76px;"></div>', unsafe_allow_html=True)

    # --- VISUALIZZA LEAGUES ESISTENTI ---------------------------------------------------
    if not league_ids:
        st.markdown('<div class="no-results">You are not enrolled in any league yet.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")
    else:
        rows = []
        for lid in league_ids:
            league_data = supabase.from_("leagues").select("*").eq("ID", lid).limit(1).execute().data or []
            if league_data:
                league = league_data[0]
                name = league.get("name") or league.get("ID") or str(lid)
                location = league.get("where") or "N/A"
                foundation = league.get("foundation") or "N/A"
            else:
                name, location, foundation = str(lid), "N/A", "N/A"

            class_rows = supabase.from_("teams").select("who").eq("league", lid).execute().data or []
            members_count = len(class_rows)

            rows.append({
                "id": lid,
                "name": _html.escape(str(name)),
                "location": _html.escape(str(location)),
                "foundation": _html.escape(str(foundation)),
                "members": members_count
            })

        rows_sorted = sorted(rows, key=lambda x: x["members"], reverse=True)

        for i, r in enumerate(rows_sorted):
            row_html = (
                '<div class="row-box">'
                f'<div style="width:40px"></div>'
                f'<div class="col-name" title="{_html.escape(r["name"])}"><b>{r["name"]}</b></div>'
                f'<div class="col-location">{r["location"]}</div>'
                f'<div class="col-foundation">{r["foundation"]}</div>'
                f'<div class="col-members">{r["members"]}</div>'
                '</div>'
            )
            left_col, btn_col = st.columns([0.90, 0.10])
            left_col.markdown(row_html, unsafe_allow_html=True)

            key = f"open_league_{i}_{r['id']}"
            if btn_col.button("Go to", key=key):
                st.session_state["selected_league"] = r["id"]
                hist = st.session_state.get("screen_history", [])
                hist.append("leagues")
                st.session_state["screen_history"] = hist

                selected_league = st.session_state["selected_league"]
                resp = supabase.from_("teams").select("*").eq("UUID", player_uuid).eq("league", selected_league).limit(1).execute()
                rows = resp.data or []
                st.session_state["user"] = rows[0] if rows else None
                st.session_state.go = True
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")

    # --- CREA NUOVA LEAGUE + TEAM -------------------------------------------------------
    choice = st.radio("Select:", ["Join", "Create"])
    if choice == "Join":
        st.markdown("### Join an existing league")

    # --- STEP 1: lookup della league per ID
        with st.form("join_league_lookup_form"):
            st.write("**Insert the League ID you want to join**")
            join_league_id = st.text_input("League name (ID)", key="join_league_id")
            lookup_submit = st.form_submit_button("Find league")

        if lookup_submit:
            lid = (st.session_state.get("join_league_id") or "").strip()
            if not lid:
                st.error("Please provide a league ID to search.")
            else:
            # cerca la league
                resp = supabase.from_("leagues").select("*").eq("ID", lid).limit(1).execute()
                league_data = resp.data or []
                if not league_data:
                    st.error(f"League with ID '{lid}' not found.")
                else:
                # prima di salvare la league trovata, verifica se l'utente è già iscritto
                    already_resp = supabase.from_("teams").select("*").eq("UUID", player_uuid).eq("league", lid).limit(1).execute()
                    already_rows = already_resp.data or []
                    if already_rows:
                    # utente già iscritto: mostra messaggio e offri link per aprire la propria squadra
                        st.error("You are already enrolled in this league.")
                    # non salvare join_league_found — lascia il form pulito
                    else:
                    # non è ancora iscritto: salva league trovata e mostra il form di join
                        st.session_state["join_league_found"] = league_data[0]
                    # reset eventuali vecchi valori di join per evitare artefatti
                        for k in ("join_league_pw_input","join_team_name","join_team_location","join_main_color_hex","join_second_color_hex"):
                            if k in st.session_state:
                                st.session_state.pop(k, None)
                        st.rerun()

    # --- se è stata trovata una league, mostra il form di join + team creation
        league = st.session_state.get("join_league_found")
        if league:
            st.markdown("#### League found")
            st.markdown(f"- **ID:** `{_html.escape(str(league.get('ID') or ''))}`")
            st.markdown(f"- **Location:** {_html.escape(str(league.get('where') or 'N/A'))}")
            st.markdown(f"- **Foundation:** {_html.escape(str(league.get('foundation') or 'N/A'))}")
            is_private = bool(league.get("pwrd"))  # se pwrd è non-empty -> privata

        # bottone per cercare un'altra league (reset)
            if st.button("Search another league", key="reset_join_search"):
            # puliamo tutte le chiavi relative al join
                for k in ("join_league_found","join_league_id","join_league_pw_input","join_team_name","join_team_location","join_main_color_hex","join_second_color_hex"):
                    st.session_state.pop(k, None)
                st.rerun()

            st.markdown("---")
            st.markdown("### Create your team in this league")

        # form per la creazione della team e join della league
            with st.form("join_league_form"):
                if is_private:
                    st.info("This league is private — enter the league password to join.")
                    pw_input = st.text_input("League password", type="password", key="join_league_pw_input")
                else:
                    st.write("This league is public — no password required to join.")

            # team fields (usiamo key-specific per non interferire con il form 'create' esistente)
                join_team_name = st.text_input("Team name", key="join_team_name")
                join_team_location = st.text_input(
                    "Team location (where)",
                    value=league.get("where") or "",
                    key="join_team_location"
                )
                join_main_color_hex = st.color_picker("Main color", value="#00CAFF", key="join_main_color_hex")
                join_second_color_hex = st.color_picker("Second color", value="#FFFFFF", key="join_second_color_hex")

                submit_join = st.form_submit_button("Join league & create team")

            if submit_join:
            # validazioni client-side
                team_name_val = (st.session_state.get("join_team_name") or "").strip()
                team_location_val = (st.session_state.get("join_team_location") or "").strip()
                pw_val = st.session_state.get("join_league_pw_input", "") or ""
                league_id = league.get("ID")

                if not team_name_val:
                    st.error("Please provide a team name.")
                elif not team_location_val:
                    st.error("Please provide a team location.")
                else:
                # ricontrollo safety: evitare che nel frattempo l'utente sia stato iscritto
                    check_resp = supabase.from_("teams").select("*").eq("UUID", player_uuid).eq("league", league_id).limit(1).execute()
                    if check_resp.data:
                        st.error("You are already enrolled in this league.")
                    else:
                    # se la league è privata, controlla password (hash SHA256 come durante la creazione)
                        stored_pw_hash = league.get("pwrd") or ""
                        if stored_pw_hash:
                            if not pw_val:
                                st.error("Please provide the league password.")
                            else:
                                entered_hash = hashlib.sha256(pw_val.encode("utf-8")).hexdigest()
                                if entered_hash != stored_pw_hash:
                                    st.error("Incorrect league password.")
                                else:
                                # password OK -> crea team
                                    main_color_rgb = hex_to_rgb(st.session_state.get("join_main_color_hex", "#00CAFF"))
                                    second_color_rgb = hex_to_rgb(st.session_state.get("join_second_color_hex", "#FFFFFF"))
                                    if main_color_rgb is None or second_color_rgb is None:
                                        st.error("Errore nella conversione dei colori. Riprova.")
                                    else:
                                        team_inserted = build_team(
                                            user,
                                            league_id,
                                            team_name_val,
                                            main_color_rgb,
                                            second_color_rgb,
                                            team_location_val,
                                            league.get("foundation"),
                                        )
                                        if team_inserted:
                                        # pulisco il form di join così non rimane visibile nelle sessioni successive
                                            for k in ("join_league_found","join_league_id","join_league_pw_input","join_team_name","join_team_location","join_main_color_hex","join_second_color_hex"):
                                                st.session_state.pop(k, None)
                                            st.success(f"Joined league '{league_id}' and created team '{team_name_val}'.")
                                            hist = st.session_state.get("screen_history", [])
                                            hist.append("leagues")
                                            st.session_state["screen_history"] = hist
                                            st.session_state["nav_selection"] = "Your team"
                                            st.session_state["screen"] = "team"
                                            st.session_state["selected_league"] = league_id
                                            st.session_state.go = True
                                            st.rerun()
                                        else:
                                            st.error("Team creation failed after joining league.")
                        else:
                        # league pubblica -> crea team direttamente
                            main_color_rgb = hex_to_rgb(st.session_state.get("join_main_color_hex", "#00CAFF"))
                            second_color_rgb = hex_to_rgb(st.session_state.get("join_second_color_hex", "#FFFFFF"))
                            if main_color_rgb is None or second_color_rgb is None:
                                st.error("Errore nella conversione dei colori. Riprova.")
                            else:
                                team_inserted = build_team(
                                    user,
                                    league_id,
                                    team_name_val,
                                    main_color_rgb,
                                    second_color_rgb,
                                    team_location_val,
                                    league.get("foundation"),
                                )
                                if team_inserted:
                                # pulisco il form di join così non rimane visibile nelle sessioni successive
                                    for k in ("join_league_found","join_league_id","join_league_pw_input","join_team_name","join_team_location","join_main_color_hex","join_second_color_hex"):
                                        st.session_state.pop(k, None)
                                    st.success(f"Joined league '{league_id}' and created team '{team_name_val}'.")
                                    hist = st.session_state.get("screen_history", [])
                                    hist.append("leagues")
                                    st.session_state["screen_history"] = hist
                                    st.session_state["nav_selection"] = "Your team"
                                    st.session_state["screen"] = "team"
                                    st.session_state["selected_league"] = league_id
                                    st.session_state.go = True
                                    st.rerun()
                                else:
                                    st.error("Team creation failed after joining league.")



    elif choice == "Create":
        st.markdown("### Create league & team")

        # ---- Radio FUORI dal form: immediata sincronizzazione
        # il risultato viene memorizzato in st.session_state.league_visibility
        visibility = st.radio("Visibility", ["Public", "Private"], index=0, key="league_visibility")

        # unico form che contiene i campi della league e della team (ma la radio è fuori)
        with st.form("create_league_and_team_form"):
            st.write("**League data**")
            league_name = st.text_input("League name (ID)", help="Unique identifier of the league", key="league_name")
            league_location = st.text_input("League location", help="City / place", key="league_location")

            # renderizza il campo password SOLO se la visibility impostata (fuori) è Private
            if st.session_state.get("league_visibility", "Public") == "Private":
                pw_input = st.text_input(
                    "Password for private league",
                    type="password",
                    help="Set a password to allow joining (only for private leagues)",
                    key="league_pw_input"
                )
            else:
                # assicura che non ci siano valori residui
                st.session_state["league_pw_input"] = ""

            st.write("---")
            st.write("**Team data**")
            team_name = st.text_input("Team name", help="Name of your team", key="team_name")
            team_location = st.text_input(
                "Team location (where)",
                value=st.session_state.get("league_location", "") or "",
                help="City / place",
                key="team_location"
            )
            main_color_hex = st.color_picker("Main color", value="#00CAFF", help="Choose main team color", key="main_color_hex")
            second_color_hex = st.color_picker("Second color", value="#FFFFFF", help="Choose secondary team color", key="second_color_hex")

            submit_all = st.form_submit_button("Create league and team")

        # Quando l'utente preme Create (submit_all è True), valida e salva
        if submit_all:
            # leggere i valori dal form attraverso session_state (widget hanno key)
            league_name_val = st.session_state.get("league_name", "").strip()
            league_location_val = st.session_state.get("league_location", "").strip()
            visibility_val = st.session_state.get("league_visibility", "Public")
            pw_val = st.session_state.get("league_pw_input", "") or ""
            team_name_val = st.session_state.get("team_name", "").strip()
            team_location_val = st.session_state.get("team_location", "").strip()

            # validazioni
            if not league_name_val:
                st.error("Please provide a league name.")
            elif not league_location_val:
                st.error("Please provide a league location.")
            elif visibility_val == "Private" and not pw_val:
                st.error("Please provide a password for private league.")
            elif not team_name_val:
                st.error("Please provide a team name.")
            elif not team_location_val:
                st.error("Please provide a team location.")
            else:
                league_id = league_name_val
                # check esistenza league
                exists_resp = supabase.from_("leagues").select("ID").eq("ID", league_id).limit(1).execute()
                if exists_resp.data:
                    st.error(f"A league with ID '{league_id}' already exists. Choose a different name.")
                else:
                    pw_hash = hashlib.sha256(pw_val.encode("utf-8")).hexdigest() if visibility_val == "Private" else ""
                    # foundation comune (month + year in English)
                    foundation = datetime.now().strftime("%B %Y")  # es. "October 2025"
                    president_uuid = user.get("UUID") if user else None

                    new_league = {
                        "ID": league_id,
                        "where": league_location_val,
                        "pwrd": pw_hash,
                        "foundation": foundation,
                        "president": president_uuid,
                    }

                    insert_resp = supabase.from_("leagues").insert(new_league).execute()
                    if getattr(insert_resp, "error", None):
                        st.error(f"Error creating league: {insert_resp.error}")
                    else:
                        st.success(f"League '{league_id}' created successfully.")
                        st.session_state["selected_league"] = league_id

                        # ------------------ NUOVE OPERAZIONI RICHIESTE ------------------
                        def copy_rules_from_template(table_name, src_league, dest_league):
                            try:
                                resp = supabase.from_(table_name).select("*").eq("league", src_league).execute()
                            except Exception as e:
                                st.error(f"Exception reading {table_name}: {e}")
                                return

                            if getattr(resp, "error", None):
                                st.error(f"Error reading {table_name}: {resp.error}")
                                return

                            rows = resp.data or []
                            if not rows:
                                st.info(f"No rows found in {table_name} for league '{src_league}'.")
                                return

                            insert_rows = []
                            for r in rows:
        # copia tutti i campi tranne possibili PK / timestamps
                                new_r = {}
                                for k, v in r.items():
            # escludiamo colonne comunemente generate dal DB
                                    if k.lower() in ("id", "uuid", "created_at", "updated_at"):
                                        continue
                                    new_r[k] = v
        # sovrascriviamo la league con quella nuova
                                new_r["league"] = dest_league
        # generiamo un nuovo id (UUID) per la riga inserita
                                new_r["id"] = str(uuid.uuid4())
                                insert_rows.append(new_r)

                            if not insert_rows:
                                st.info(f"No rows to insert for {table_name} after filtering.")
                                return

                            try:
                                ins = supabase.from_(table_name).insert(insert_rows).execute()
                            except Exception as e:
                                st.error(f"Exception inserting into {table_name}: {e}")
                                return

                            if getattr(ins, "error", None):
                                st.error(f"Error inserting into {table_name}: {ins.error}")
                            else:
                                inserted = ins.data or []
                                st.info(f"Copied {len(inserted)} rows into {table_name} for league '{dest_league}'.")


                        TEMPLATE_LEAGUE = "Fantamotori"
                        copy_rules_from_template("rules_mgp_new", TEMPLATE_LEAGUE, league_id)
                        copy_rules_from_template("rules_f1_new", TEMPLATE_LEAGUE, league_id)

                        try:
                            roh_row = {
                                "id": str(uuid.uuid4()),
                                "year": datetime.now().year,
                                "league": league_id
                            }
                            roh_ins = supabase.from_("roll_of_honor_new").insert(roh_row).execute()
                            if getattr(roh_ins, "error", None):
                                st.error(f"Error inserting into roll_of_honor_new: {roh_ins.error}")
                            else:
                                st.info(f"Inserted roll_of_honor_new row for year {roh_row['year']}.")
                        except Exception as e:
                            st.error(f"Exception inserting roll_of_honor_new: {e}")

                        try:
                            penalty_row = {
                                "id": str(uuid.uuid4()),
                                "uuid": user.get("UUID"),
                                "league": league_id
                            }
                            pen_ins = supabase.from_("penalty_new").insert(penalty_row).execute()
                            if getattr(pen_ins, "error", None):
                                st.error(f"Error inserting into penalty_new: {pen_ins.error}")
                            else:
                                st.info("Inserted penalty_new row for league.")
                        except Exception as e:
                            st.error(f"Exception inserting penalty_new: {e}")

                        try:
    # prepara riga per calls_f1_new
                            call_row_f1 = {
                                "id": str(uuid.uuid4()),
                                "uuid": player_uuid,
                                "league": league_id
                            }

                            cf1_ins = supabase.from_("calls_f1_new").insert([call_row_f1]).execute()
                            if getattr(cf1_ins, "error", None):
                                st.error(f"Error inserting into calls_f1_new: {cf1_ins.error}")
                            else:
        # mostra i dettagli restituiti (se presenti)
                                inserted_f1 = (cf1_ins.data or [])
                            
    # prepara riga per calls_mgp_new (uuid diverso)
                            call_row_mgp = {
                                "id": str(uuid.uuid4()),
                                "uuid": user.get("UUID"),
                                "league": league_id
                            }

                            cmgp_ins = supabase.from_("calls_mgp_new").insert([call_row_mgp]).execute()
                            if getattr(cmgp_ins, "error", None):
                                st.error(f"Error inserting into calls_mgp_new: {cmgp_ins.error}")
                            else:
                                inserted_mgp = (cmgp_ins.data or [])

                        except Exception as e:
                            st.error(f"Exception inserting into calls tables: {e}")

                        def create_stats_for_series(league_id, racers_table, stats_table, player_col="id", player_field_in_stats="player_id"):
                            """
                            Inserisce in stats_table una riga per ogni racer presente in racers_table con go == True.
                            - racers_table: es. "racers_f1_new" o "racers_mgp_new"
                            - stats_table: es. "league_f1_stats" o "league_mgp_stats"
                            - player_col: colonna nella tabella racers (di solito "id")
                            - player_field_in_stats: campo in stats_table dove salvare l'id del giocatore (di solito "player_id")
                            Nota: non includiamo "uuid" perchè lo genera il DB/Supabase automaticamente.
                             """
                            try:
                                racers_resp = supabase.from_(racers_table).select(player_col).eq("go", True).execute()
                                if getattr(racers_resp, "error", None):
                                    st.warning(f"Warning fetching racers from {racers_table}: {racers_resp.error}")
                                    racer_rows = []
                                else:
                                    racer_rows = racers_resp.data or []

                                player_ids = [r.get(player_col) for r in racer_rows if r.get(player_col)]

                                if player_ids:
                                    stats_rows = [{ "league_id": league_id, player_field_in_stats: pid } for pid in player_ids]
                                    insert_stats_resp = supabase.from_(stats_table).insert(stats_rows).execute()
                                    if getattr(insert_stats_resp, "error", None):
                                        st.error(f"Errore inserimento {stats_table}: {insert_stats_resp.error}")
                                    else:
                                        inserted = insert_stats_resp.data or []
                                        st.info(f"Create {len(inserted)} righe in {stats_table} per la league '{league_id}'.")
                                else:
                                    st.info(f"Nessun racer in {racers_table} con go == True trovato — nessuna riga creata in {stats_table}.")
                            except Exception as e:
                                st.error(f"Eccezione durante creazione {stats_table}: {e}")

# chiama la funzione per F1 (compatibile col codice esistente)
                        create_stats_for_series(league_id, "racers_f1_new", "league_f1_stats", player_col="id", player_field_in_stats="player_id")

# chiama la funzione per MotoGP
                        create_stats_for_series(league_id, "racers_mgp_new", "league_mgp_stats", player_col="id", player_field_in_stats="player_id")


# Colori HEX → RGB
                        main_color_rgb = hex_to_rgb(st.session_state.get("main_color_hex", "#00CAFF"))
                        second_color_rgb = hex_to_rgb(st.session_state.get("second_color_hex", "#FFFFFF"))

                        if main_color_rgb is None or second_color_rgb is None:
                            st.error("Errore nella conversione dei colori. Riprova.")
                        else:
    # crea la squadra (usa nomi colonna con spazi come nel tuo DB)
                            team_inserted = build_team(
                                st.session_state.get("user"),
                                league_id,
                                team_name_val,
                                main_color_rgb,
                                second_color_rgb,
                                team_location_val,
                                foundation,
                            )

                            if team_inserted:
        # aggiorna cronologia e nav, poi torna alla home (team)
                                hist = st.session_state.get("screen_history", [])
                                hist.append("leagues")
                                st.session_state["screen_history"] = hist
                                st.session_state["nav_selection"] = "Your team"
                                st.session_state["screen"] = "team"
                                st.session_state["selected_league"] = league_id
                                st.session_state.go = True
                                st.rerun()
                            else:
                                st.error("League created, but team creation failed.")
                            
