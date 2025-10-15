import html as _html
import json
import hashlib
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

if "go" not in st.session_state:
    st.session_state.go = False


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
    """Crea una riga nella tabella teams."""
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
        "main color": main_color_rgb,       # jsonb
        "second color": second_color_rgb,   # jsonb
        "where": team_location.strip(),
        "foundation": foundation,
        "UUID": user.get("UUID"),
        "league": league_id,
    }

    insert_resp = supabase.from_("teams").insert(new_team).execute()
    if getattr(insert_resp, "error", None):
        st.error(f"Errore nella creazione della squadra: {insert_resp.error}")
        return None

    inserted_row = None
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
      .header-row { display: flex; gap: 16px; padding: 12px 20px; font-weight: 700;
                    background: #000; color: #fff; border-radius: 12px; align-items:center; }
      .row-box { display: flex; gap: 18px; padding: 16px 22px; align-items: center;
                 border-radius: 18px; margin: 12px 0;
                 background: linear-gradient(180deg,#1f1f1f,#171717);
                 border: 1px solid rgba(255,255,255,0.03); min-height: 76px; }
      .row-box .col-name { flex: 5; font-weight: 700; color: #fff; overflow: visible; }
      .row-box .col-location { flex: 4; color: #ddd; }
      .row-box .col-foundation { flex: 3; color: #bbb; }
      .row-box .col-members { flex: 0 0 120px; text-align: right; font-weight: 600; color: #fff; }
      .header-row .h-col { padding: 0 10px; }
      .header-row .h-name { flex: 5; }
      .header-row .h-location { flex: 4; }
      .header-row .h-foundation { flex: 3; }
      .header-row .h-members { flex: 0 0 120px; text-align:right; }
      .stButton { display: flex; align-items: center; justify-content: center;
                  height: 76px; margin-left: 12px; margin-right: 12px; }
      div.stButton > button { padding: 6px 14px !important; border-radius: 14px !important;
                              min-width: 90px; white-space: nowrap; font-weight: 600;
                              height: 36px; line-height: 16px; }
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
        st.write("→ Join a new league (coming soon)")

    elif choice == "Create":
        st.markdown("### Create league & team")

        with st.form("create_league_and_team_form"):
            st.write("**League data**")
            league_name = st.text_input("League name (ID)", help="Unique identifier of the league")
            league_location = st.text_input("League location", help="City / place")
            visibility = st.radio("Visibility", ["Public", "Private"], index=0)

            pw_input = ""
            if visibility == "Private":
                pw_input = st.text_input("Password for private league", type="password", help="Set a password to allow joining")

            st.write("---")
            st.write("**Team data**")
            team_name = st.text_input("Team name", help="Name of your team")
            team_location = st.text_input("Team location", value=league_location or "", help="City / place")
            main_color_hex = st.color_picker("Main color", value="#00CAFF", help="Choose main team color")
            second_color_hex = st.color_picker("Second color", value="#FFFFFF", help="Choose secondary team color")

            submit_all = st.form_submit_button("Create league and team")

        if submit_all:
            # validazioni
            if not league_name:
                st.error("Please provide a league name.")
            elif not league_location:
                st.error("Please provide a league location.")
            elif visibility == "Private" and not pw_input:
                st.error("Please provide a password for private league.")
            elif not team_name:
                st.error("Please provide a team name.")
            elif not team_location:
                st.error("Please provide a team location.")
            else:
                league_id = league_name.strip()
                exists_resp = supabase.from_("leagues").select("ID").eq("ID", league_id).limit(1).execute()
                if exists_resp.data:
                    st.error(f"A league with ID '{league_id}' already exists. Choose a different name.")
                else:
                    pw_hash = hashlib.sha256(pw_input.encode("utf-8")).hexdigest() if visibility == "Private" else ""
                    foundation = datetime.now().strftime("%B %Y")  # es. "October 2025"
                    president_uuid = user.get("UUID") if user else None

                    new_league = {
                        "ID": league_id,
                        "where": league_location,
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

                        # Colori HEX → RGB
                        main_color_rgb = hex_to_rgb(main_color_hex)
                        second_color_rgb = hex_to_rgb(second_color_hex)

                        if main_color_rgb is None or second_color_rgb is None:
                            st.error("Errore nella conversione dei colori. Riprova.")
                        else:
                            team_inserted = build_team(
                                st.session_state.get("user"),
                                league_id,
                                team_name,
                                main_color_rgb,
                                second_color_rgb,
                                team_location,
                                foundation,
                            )

                            if team_inserted:
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

        
