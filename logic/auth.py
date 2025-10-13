import streamlit as st
import os
from supabase import create_client
import subprocess
from urllib.parse import urlparse, parse_qsl
import requests
from cryptography.fernet import Fernet
from logic.functions import get_supabase_client

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
            return None, False
        else:
            return None, False
    except Exception:
        return None, False


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

def clone_repo(CLONE_DIR, REPO_URL):
    if not os.path.exists(CLONE_DIR):
        print("Cloning repository...")
        subprocess.check_call(["git", "clone", REPO_URL, CLONE_DIR])

# -------------------------------------------------------------------------------------------

def logout():
    supabase = get_supabase_client()
    supabase.auth.sign_out()
    st.session_state.logged_in = False
    st.session_state.user = None
    st.success("Logout effettuato.")
    st.rerun()

# -------------------------------------------------------------------------------------------

def send_email_brevo(to_email: str, subject: str, body_text: str):
    """
    Invia email usando Brevo.
    - Se SUPABASE_FUNCTION_URL e PROXY_SECRET sono presenti, invia la richiesta a quella Function (consigliato).
    - Altrimenti usa direttamente la Brevo API con BREVO_API_KEY taken from env.
    """
    # mittente (puoi configurarlo via env)
    EMAIL_FROM = os.environ.get("EMAIL_FROM", "noreply@fantapaddock.app")
    FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Fantapaddock")

    # preferisci chiamare la Supabase Edge Function (proxy)?
    SUPABASE_FN = os.environ.get("SUPABASE_FUNCTION_URL")
    PROXY_SECRET = os.environ.get("PROXY_SECRET")

    if SUPABASE_FN and PROXY_SECRET:
        # Chiamata al proxy su Supabase (Edge Function)
        try:
            headers = {
                "x-proxy-secret": PROXY_SECRET,
                "Content-Type": "application/json",
            }
            payload = {"to": to_email, "subject": subject, "html": body_text}
            resp = requests.post(SUPABASE_FN, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            st.error(f"Errore invio email via Supabase Function: {e}")
            raise

    # fallback -> invio diretto a Brevo (server-side)
    BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
    if not BREVO_API_KEY:
        err = "Nessuna SUPABASE_FUNCTION_URL/proxy trovato e BREVO_API_KEY mancante."
        st.error(err)
        raise RuntimeError(err)

    try:
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "api-key": BREVO_API_KEY,
            "Content-Type": "application/json",
        }
        # Brevo accetta htmlContent e textContent
        payload = {
            "sender": {"email": EMAIL_FROM, "name": FROM_NAME},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": body_text,
            "textContent": body_text,
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Errore invio email via Brevo API: {e}")
        raise

# -------------------------------------------------------------------------------------------

def encrypt_email(email: str) -> str:
    key = os.environ["FERNET_KEY"].encode()
    f = Fernet(key)
    return f.encrypt(email.encode()).decode()

# -------------------------------------------------------------------------------------------

def decrypt_email(token: str) -> str:
    key = os.environ["FERNET_KEY"].encode()
    f = Fernet(key)
    return f.decrypt(token.encode()).decode()

# -------------------------------------------------------------------------------------------

def generate_direct_recovery_link_and_send(email: str):
    SUPABASE_URL = os.environ["SUPABASE_URL"]
    SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    STREAMLIT_URL = os.environ.get("STREAMLIT_URL", "https://fantapaddock.streamlit.app")

    supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    resp = supabase_admin.auth.admin.generate_link({"type": "recovery", "email": email})

    # --- action_link ---
    link = None
    if hasattr(resp, "properties") and hasattr(resp.properties, "action_link"):
        link = resp.properties.action_link
    elif isinstance(resp, dict) and "action_link" in resp:
        link = resp["action_link"]

    if not link:
        raise RuntimeError(f"Impossibile estrarre action_link. Resp: {resp}")

    parsed = urlparse(link)
    params = dict(parse_qsl(parsed.query))
    token = params.get("token")

    encrypted_email = encrypt_email(email)
    direct_link = f"{STREAMLIT_URL}?token={token}&email={encrypted_email}&type=recovery"

    subject = "Reset password - Fantapaddock"
    body = f"""Ciao,

hai richiesto il reset della password. Clicca qui per procedere:

{direct_link}

Se non hai richiesto questo reset, ignora questa email.

— Il team Fantapaddock
"""
    send_email_brevo(email, subject, body)
    return direct_link

# -------------------------------------------------------------------------------------------

def _get_first(qp, k):
    v = qp.get(k)
    if v is None:
        return None
    return v[0] if isinstance(v, (list, tuple)) else v

# -------------------------------------------------------------------------------------------

def is_valid_password(password: str) -> bool:
    return (
        len(password) >= 8
        and any(c.isalpha() for c in password)
        and any(c.isdigit() for c in password)
    )

# -------------------------------------------------------------------------------------------

def _extract_name(row):
                if not row or not isinstance(row, dict):
                    return None
                return (
                    row.get("name")
                    or row.get("Name")
                    or row.get("nome")
                    or row.get("full_name")
                    or row.get("fullName")
                    or row.get("fullname")
                    or row.get("display_name")
                    or row.get("displayName")
                    or row.get("ID")
                    or row.get("id")
                )

# -------------------------------------------------------------------------------------------

