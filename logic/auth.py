from supabase import create_client, Client
from gotrue.errors import AuthApiError
import streamlit as st
from urllib.parse import urlparse, parse_qs

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

def reset_password_with_token(supabase, access_token):
    st.title("Reset Password")

    # Form per inserire la nuova password due volte
    with st.form("reset_password_form"):
        new_password = st.text_input("Nuova password", type="password")
        confirm_password = st.text_input("Conferma nuova password", type="password")
        submitted = st.form_submit_button("Cambia password")

        if submitted:
            if new_password != confirm_password:
                st.warning("Le password non coincidono.")
            elif len(new_password) < 6:
                st.warning("La password deve essere almeno di 6 caratteri.")
            else:
                try:
                    # Chiamata supabase per aggiornare la password con il token
                    response = supabase.auth.api.update_user(access_token, {"password": new_password})
                    if response.get("error"):
                        st.error(f"Errore: {response['error']['message']}")
                    else:
                        st.success("Password aggiornata con successo! Puoi ora effettuare il login.")
                except Exception as e:
                    st.error(f"Errore durante il reset password: {e}")

# -----------------------------------------------------------------------------------------
