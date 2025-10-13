from supabase import create_client, Client
from gotrue.errors import AuthApiError
import streamlit as st
from urllib.parse import urlparse, parse_qs

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

def login(email, password, supabase, teams):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})

        if response.user:
            for team in teams.data:
                if team.get("mail") == email:
                    return team, True
        else:
            return False, False
    except Exception:
        return False, False

# -------------------------------------------------------------------------------------------

def register(email, password, supabase):
    response = supabase.auth.sign_up({"email": email, "password": password})
    
    if response.user:
        st.success("Registration confirmed! We've just sent you a confirmation email.")
        return response.user, True
    else:
        # response.error a volte può essere None -> mettiamo un fallback
        error_msg = response.error.message if response.error else "Unknown registration error"
        st.error(error_msg)
        return None, False
        
# -------------------------------------------------------------------------------------------

