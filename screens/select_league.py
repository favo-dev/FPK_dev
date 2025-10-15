import html as _html
import streamlit as st
from supabase import create_client, Client
from logic.functions import go_to_screen
from screens.home import home_screen

# -------------------------------------------------------------------------------------------
# --------------------- SUPABASE CLIENT -----------------------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --------------------- LEAGUE SCREEN -------------------------------------------------------
def league_screen(user):
    if st.session_state.screen == "team":
        your_team_screen(user)
    st.title("League hub")
    st.subheader("Your leagues")

    player_uuid = user.get("UUID")
    if not player_uuid:
        st.warning("UUID not found for this user.")
        return

    teams_rows = supabase.from_("teams").select("league").eq("UUID", player_uuid).execute().data or []
    league_ids = list({row.get("league") for row in teams_rows if row.get("league")})

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

    if not league_ids:
        st.markdown('<div class="no-results">You are not enrolled in any league yet.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")
        choice = st.radio("Select:", ["Join", "Create"])
        if choice == "Join":
            st.write("→ Join a new league (coming soon)")
        elif choice == "Create":
            st.write("→ Create your own league (coming soon)")
        return

    rows = []
    for lid in league_ids:
        league_data = supabase.from_("leagues").select("*").eq("ID", lid).limit(1).execute().data or []
        if not league_data:
            league_data = supabase.from_("leagues").select("*").eq("id", lid).limit(1).execute().data or []
            if not league_data:
                league_data = supabase.from_("leagues").select("*").eq("name", lid).limit(1).execute().data or []

        if league_data:
            league = league_data[0]
            name = league.get("name") or league.get("ID") or league.get("id") or str(lid)
            location = league.get("where") or league.get("location") or league.get("city") or "N/A"
            foundation = league.get("foundation") or league.get("founded") or league.get("foundation_year") or "N/A"
        else:
            name = str(lid)
            location = "N/A"
            foundation = "N/A"

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
            f'<div class="col-location" title="{_html.escape(r["location"])}">{r["location"]}</div>'
            f'<div class="col-foundation" title="{_html.escape(r["foundation"])}">{r["foundation"]}</div>'
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
            resp = supabase.from_("teams") \
                .select("*") \
                .eq("UUID", player_uuid) \
                .eq("league", selected_league) \
                .limit(1) \
                .execute()

            rows = resp.data or []
            if len(rows) > 0:
                st.session_state["user"] = rows[0]
            else:
                st.session_state["user"] = None
        
            st.session_state["screen"] = "team"
            st.rerun()

            
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    choice = st.radio("Select:", ["Join", "Create"])
    if choice == "Join":
        st.write("→ Join a new league (coming soon)")
    elif choice == "Create":
        st.write("→ Create your own league (coming soon)")
