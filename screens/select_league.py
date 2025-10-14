import streamlit as st
from supabase import create_client
from logic.functions import go_to_screen

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --------------------- LEAGUE SCREEN ----------------------------------------------------

def league_screen(user):
  st.title("League hub")
  
    choice = st.radio("Select:", ["Join", "Create"]) 
