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

    response = (
        supabase.table("teams")
        .select("league")
        .eq("UUID", player_uuid)
        .execute()
    )

    if response.error:
        st.error(f"Error fetching leagues: {response.error.message}")
    else:
        leagues = [item["league"] for item in response.data if item.get("league")]

        if leagues:
            for lg in leagues:
                st.markdown(
                    f"<div style='background:#333;color:white;padding:10px;border-radius:10px;margin-bottom:8px;font-size:1.1rem;text-align:center;box-shadow:0 3px 8px rgba(0,0,0,.2)'>{lg}</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("You are not enrolled in any league yet.")

    st.markdown("---")

    choice = st.radio("Select:", ["Join", "Create"])

    if choice == "Join":
        st.write("→ Join a new league (coming soon)")
    elif choice == "Create":
        st.write("→ Create your own league (coming soon)")
