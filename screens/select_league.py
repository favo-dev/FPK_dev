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

    # 1) prendi tutte le league collegate al giocatore nella tabella 'teams'
    resp = (
        supabase.table("teams")
        .select("league")
        .eq("UUID", player_uuid)
        .execute()
    )

    # estrai id unici delle leghe
    league_ids = list({row.get("league") for row in (resp.data or []) if row.get("league")})

    if not league_ids:
        st.info("You are not enrolled in any league yet.")
    else:
        # costruisci righe HTML per la tabella
        rows_html = ""
        for lid in league_ids:
            # tenta di ottenere i dettagli della lega dalla tabella 'leagues'
            league_resp = (
                supabase.table("leagues")
                .select("*")
                .eq("ID", lid)
                .limit(1)
                .execute()
            )

            if league_resp.error:
                # in caso di errore, mostra comunque la raw id
                name = str(lid)
                location = "N/A"
                foundation = "N/A"
            elif not league_resp.data:
                # se non trova per id, usa il valore raw (potrebbe essere già un nome)
                name = str(lid)
                location = "N/A"
                foundation = "N/A"
            else:
                league = league_resp.data[0]
                # tenta di recuperare i campi con fallback
                name = league.get("name") or league.get("id") or str(lid)
                # la colonna 'where' potrebbe avere nome riservato; usiamo .get
                location = league.get("where") or league.get("location") or "N/A"
                foundation = league.get("foundation") or league.get("founded") or "N/A"

            # conta i membri: numero di teams che hanno teams.league == lid
            members_resp = (
                supabase.table("teams")
                .select("ID")
                .eq("league", lid)
                .execute()
            )
            if members_resp.error:
                members = "?"
            else:
                members = len(members_resp.data) if members_resp.data else 0

            # aggiungi riga (Name, Location, Foundation, Members)
            rows_html += (
                "<tr>"
                f"<td style='padding:10px;border-bottom:1px solid rgba(255,255,255,0.06)'>{name}</td>"
                f"<td style='padding:10px;border-bottom:1px solid rgba(255,255,255,0.06)'>{location}</td>"
                f"<td style='padding:10px;border-bottom:1px solid rgba(255,255,255,0.06)'>{foundation}</td>"
                f"<td style='padding:10px;border-bottom:1px solid rgba(255,255,255,0.06);text-align:center'>{members}</td>"
                "</tr>"
            )

        # stile e wrapper della tabella
        table_html = f"""
        <div style='max-width:900px;background:#333;border-radius:12px;padding:14px;color:white;
                    box-shadow:0 6px 18px rgba(0,0,0,0.35);margin-bottom:1.8rem'>
          <div style='font-weight:600;margin-bottom:8px;font-size:1.05rem'>Your leagues</div>
          <div style='overflow-x:auto'>
            <table style='width:100%;border-collapse:collapse'>
              <thead>
                <tr>
                  <th style='text-align:left;padding:10px 10px 8px 10px;color:rgba(255,255,255,0.85);font-weight:600'>Name</th>
                  <th style='text-align:left;padding:10px 10px 8px 10px;color:rgba(255,255,255,0.85);font-weight:600'>Location</th>
                  <th style='text-align:left;padding:10px 10px 8px 10px;color:rgba(255,255,255,0.85);font-weight:600'>Foundation</th>
                  <th style='text-align:center;padding:10px 10px 8px 10px;color:rgba(255,255,255,0.85);font-weight:600'>Members</th>
                </tr>
              </thead>
              <tbody>
                {rows_html}
              </tbody>
            </table>
          </div>
        </div>
        """

        st.markdown(table_html, unsafe_allow_html=True)

    # separatore e opzioni Join/Create
    st.markdown("---")
    choice = st.radio("Select:", ["Join", "Create"])
    if choice == "Join":
        st.write("→ Join a new league (coming soon)")
    elif choice == "Create":
        st.write("→ Create your own league (coming soon)")
