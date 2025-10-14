import html as _html
import streamlit as st
from supabase import create_client, Client
from logic.functions import go_to_screen

# -------------------------------------------------------------------------------------------
# --------------------- SUPABASE CLIENT -----------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --------------------- LEAGUE SCREEN -------------------------------------------------------
def league_screen(user):
    st.title("League hub")
    st.subheader("Your leagues")

    player_uuid = user.get("UUID")
    if not player_uuid:
        st.warning("UUID not found for this user.")
        return

    # prendi tutte le league collegate al giocatore nella tabella 'teams'
    teams_rows = supabase.from_("teams").select("league").eq("UUID", player_uuid).execute().data or []
    league_ids = list({row.get("league") for row in teams_rows if row.get("league")})

    # stile (coerente con racers_screen)
    st.markdown(
        """
    <style>
      .league-container { font-family: sans-serif; color: #fff; }
      .header-row { display: flex; gap: 12px; padding: 10px 16px; font-weight: 700; background: #000; color: #fff; border-radius: 10px; align-items:center; }
      .row-box { display: flex; gap: 16px; padding: 14px 20px; align-items: center; border-radius: 18px; margin: 10px 0; background: linear-gradient(180deg,#1f1f1f,#171717); border: 1px solid rgba(255,255,255,0.03); min-height: 64px; }
      .row-box .col-name { flex: 4; font-weight: 700; color: #fff; overflow: visible; text-overflow: ellipsis; white-space: normal; }
      .row-box .col-location { flex: 3; color: #ddd; overflow: visible; text-overflow: ellipsis; white-space: normal; line-height: 1.3; }
      .row-box .col-foundation { flex: 2; color: #bbb; overflow: visible; text-overflow: ellipsis; white-space: normal; line-height: 1.3; }
      .row-box .col-members { flex: 1; min-width: 80px; text-align: right; font-weight: 600; color: #fff; margin-right: 8px; }
      div.stButton > button { padding: 6px 10px !important; border-radius: 14px !important; min-width: 80px; white-space: nowrap; font-weight: 600; height: 32px; line-height: 16px; }
      .stButton { display: flex; align-items: center; justify-content: flex-end; height: 64px; }
      .no-results { color: #ddd; padding: 12px 0; }
      .header-row .h-col { padding: 0 8px; }
    </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="league-container">', unsafe_allow_html=True)

    # intestazione tabella (solo header — il titolo "Your leagues" è già scritto sopra)
    left_hcol, btn_hcol = st.columns([0.84, 0.16])
    header_html = (
        '<div class="header-row">'
        '<div style="width:40px"></div>'
        '<div class="h-col" style="flex:4">Name</div>'
        '<div class="h-col" style="flex:3">Location</div>'
        '<div class="h-col" style="flex:2">Foundation</div>'
        '<div class="h-col" style="flex:1; text-align:right; min-width:80px">Members</div>'
        '</div>'
    )
    left_hcol.markdown(header_html, unsafe_allow_html=True)
    btn_hcol.markdown('<div style="height:64px;display:flex;align-items:center;justify-content:center;font-weight:700"></div>', unsafe_allow_html=True)

    if not league_ids:
        st.markdown('<div class="no-results">You are not enrolled in any league yet.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        # separatore e opzioni Join/Create
        st.markdown("---")
        choice = st.radio("Select:", ["Join", "Create"])
        if choice == "Join":
            st.write("→ Join a new league (coming soon)")
        elif choice == "Create":
            st.write("→ Create your own league (coming soon)")
        return

    # costruisci i dati delle righe
    rows = []
    for lid in league_ids:
        # prova a prendere i dettagli della lega (supporta più nomi di campo)
        league_data = supabase.from_("leagues").select("*").eq("id", lid).limit(1).execute().data or []
        if not league_data:
            # se non trovato per id, prova per campo 'ID' o per nome
            league_data = supabase.from_("leagues").select("*").eq("ID", lid).limit(1).execute().data or []
            if not league_data:
                league_data = supabase.from_("leagues").select("*").eq("name", lid).limit(1).execute().data or []

        if league_data:
            league = league_data[0]
            name = league.get("name") or league.get("ID") or league.get("id") or str(lid)
            location = league.get("where") or league.get("location") or league.get("city") or "N/A"
            foundation = league.get("foundation") or league.get("founded") or league.get("foundation_year") or "N/A"
        else:
            # fallback se la ricerca non restituisce nulla
            name = str(lid)
            location = "N/A"
            foundation = "N/A"

        # conta i membri nella tabella 'class_new' per la league considerata
        class_rows = supabase.from_("class_new").select("id").eq("league", lid).execute().data or []
        members_count = len(class_rows)

        rows.append({
            "id": lid,
            "name": _html.escape(str(name)),
            "location": _html.escape(str(location)),
            "foundation": _html.escape(str(foundation)),
            "members": members_count
        })

    # ordina (opzionale) per numero membri desc
    rows_sorted = sorted(rows, key=lambda x: x["members"], reverse=True)

    # render righe in stile simile a racers_screen
    for i, r in enumerate(rows_sorted):
        row_html = (
            '<div class="row-box">'
            f'<div style="width:40px"></div>'
            f'<div class="col-name" title="{_html.escape(r["name"])}"><b>{r["name"]}</b></div>'
            f'<div class="col-location" title="{_html.escape(r["location"])}">{r["location"]}</div>'
            f'<div class="col-foundation" title="{_html.escape(r["foundation"])}">{r["foundation"]}</div>'
            f'<div class="col-members">{r["members"]}</div>'
            '</div>'
        )

        left_col, btn_col = st.columns([0.84, 0.16])
        left_col.markdown(row_html, unsafe_allow_html=True)

        # bottone Info per aprire dettaglio lega
        key = f"open_league_{i}_{r['id']}"
        if btn_col.button("Info", key=key):
            # imposta stato e vai al dettaglio (pattern simile a racers_screen)
            st.session_state["selected_league"] = r["id"]
            hist = st.session_state.get("screen_history", [])
            hist.append("leagues")
            st.session_state["screen_history"] = hist
            st.session_state["screen"] = "league_details"
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # separatore e opzioni Join/Create
    st.markdown("---")
    choice = st.radio("Select:", ["Join", "Create"])
    if choice == "Join":
        st.write("→ Join a new league (coming soon)")
    elif choice == "Create":
        st.write("→ Create your own league (coming soon)")
