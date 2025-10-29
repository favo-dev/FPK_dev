import os
import sys
import datetime
from supabase import create_client
import streamlit as st
from logic.functions import hex_to_rgb
from logic.auth import (
    register,
    login,
    logout,
    clone_repo,
    send_email_brevo,
    encrypt_email,
    decrypt_email,
    generate_direct_recovery_link_and_send,
    _get_first,
    is_valid_password,
    _extract_name,          
    )
from screens.select_league import league_screen

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN non trovato nelle variabili d'ambiente!")

REPO_URL = f"https://{GITHUB_TOKEN}@github.com/favo-dev/FPK_dev.git"
CLONE_DIR = "FPK_dev"
clone_repo(CLONE_DIR, REPO_URL)
sys.path.insert(0, os.path.abspath(CLONE_DIR))

# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
teams = supabase.table("class_new").select("*").execute()

STREAMLIT_URL = os.environ.get("STREAMLIT_URL", "https://fantapaddock-work-in-progress.streamlit.app")
# -------------------------------------------------------------------------------------------

defaults = {
    "go": False,
    "league_visibility": "Public",
    "league_pw_input": "",
    "league_name": "",
    "league_location": "",
    "team_name": "",
    "team_location": "",
    "main_color_hex": "#00CAFF",
    "second_color_hex": "#FFFFFF",
    "screen_history": [],
    "nav_selection": "Your team",
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v
st.set_page_config(
    page_title="FPK Dev",
    page_icon="https://koffsyfgevaannnmjkvl.supabase.co/storage/v1/object/public/icons/FAVLINK_192.png",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -------------------------------------------------------------------------------------------

MANIFEST_URL = "https://koffsyfgevaannnmjkvl.supabase.co/storage/v1/object/public/icons/manifest.json"
SW_URL = f"{STREAMLIT_URL}/app/static/service-worker.js"

st.markdown(f"""
<link rel="manifest" href="{MANIFEST_URL}">
<meta name="theme-color" content="#e10600">
""", unsafe_allow_html=True)

st.markdown(f"""
<script>
if ('serviceWorker' in navigator) {{
  navigator.serviceWorker.register('{SW_URL}', {{scope: '/app/'}})
    .then(() => console.log("✅ Service Worker registrato"))
    .catch(err => console.log("❌ Service Worker error:", err));
}}
</script>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------------------------------

for key in [
    "logged_in",
    "user",
    "email_for_recovery",
    "show_recovery",
    "show_reset_password",
    "reset_token",
    "reset_email",
]:
    if key not in st.session_state:
        st.session_state[key] = False if "logged_in" in key or "show" in key else None

# -------------------------------------------------------------------------------------------

qp = st.query_params
token_val = _get_first(qp, "token")
encrypted_email_val = _get_first(qp, "email")
type_val = _get_first(qp, "type")

if type_val == "recovery" and token_val and encrypted_email_val:
    if not st.session_state.get("show_reset_password"):
        st.session_state.show_reset_password = True
        st.session_state.reset_token = token_val
        st.session_state.reset_email = decrypt_email(encrypted_email_val)
        st.rerun()

# -------------------------------------------------------------------------------------------

if st.session_state.show_reset_password:
    st.header("Reset your password")
    with st.form("reset_password_form"):
        new_password = st.text_input("New password", type="password")
        confirm_password = st.text_input("Confirm new password", type="password")
        submitted = st.form_submit_button("Reset Password")

        if submitted:
            if new_password != confirm_password:
                st.error("Passwords do not match!")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters!")
            else:
                try:
                    SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
                    supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

                    users_list = supabase_admin.auth.admin.list_users()
                    user_data = next(
                        (u for u in users_list if u.email == st.session_state.reset_email),
                        None,
                    )

                    if not user_data:
                        st.error("Utente non trovato!")
                        st.stop()

                    user_id = user_data.id
                    supabase_admin.auth.admin.update_user_by_id(
                        user_id,
                        {"password": new_password},
                    )

                    st.success("Password cambiata con successo!")

                    st.session_state.show_reset_password = False
                    st.session_state.reset_token = None
                    st.session_state.reset_email = None

                    st.rerun()

                except Exception as e:
                    st.error(f"Error updating password: {e}")

# -------------------------------------------------------------------------------------------
# --- Ensure session user row is fresh for selected_league before rendering screens ---
def _ensure_session_user_row():
    try:
        sess_user = st.session_state.get("user")  # può essere None o dict
        player_uuid = None
        if isinstance(sess_user, dict) and sess_user.get("UUID"):
            player_uuid = sess_user.get("UUID")
        else:
            # prova a prendere UUID dall'account corrente (se lo salvi altrove)
            player_uuid = st.session_state.get("player_uuid") or (sess_user.get("uuid") if isinstance(sess_user, dict) else None)

        sel_league = st.session_state.get("selected_league")

        # se abbiamo uuid + league, fetch dalla tabella teams (try both UUID/uuid)
        if player_uuid and sel_league:
            try:
                resp = supabase.from_("teams").select("*").eq("UUID", player_uuid).eq("league", sel_league).limit(1).execute()
                rows = resp.data or []
            except Exception:
                rows = []
            if not rows:
                try:
                    resp = supabase.from_("teams").select("*").eq("uuid", player_uuid).eq("league", sel_league).limit(1).execute()
                    rows = resp.data or []
                except Exception:
                    rows = []

            if rows:
                st.session_state["user"] = rows[0]
                return

        # fallback: se non c'è selected_league ma c'è un UUID, prendi la prima riga disponibile
        if player_uuid and not sel_league:
            try:
                any_rows = supabase.from_("teams").select("*").or_(f"UUID.eq.{player_uuid},uuid.eq.{player_uuid}").limit(1).execute().data or []
                if any_rows:
                    st.session_state["user"] = any_rows[0]
                    st.session_state["selected_league"] = any_rows[0].get("league")
            except Exception:
                pass
    except Exception:
        pass

if st.session_state.logged_in:
    league_screen(st.session_state.user)
     _ensure_session_user_row()
else:
    st.title("Login / Registration")
    choice = st.radio("Select:", ["Login", "Registration"]) 

    col1, col2 = st.columns([1, 2])

    with col1:
        st.image(
            "https://koffsyfgevaannnmjkvl.supabase.co/storage/v1/object/sign/figures/FM-1.png?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV9hNTU1ZWI5ZC03NmZjLTRiMjUtOGIwMC05ZDQ4ZTRhNGNhMDEiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJmaWd1cmVzL0ZNLTEucG5nIiwiaWF0IjoxNzU4NzA2NzI2LCJleHAiOjE3OTAyNDI3MjZ9.x5MLW8w-pm5t3syML6baJDlVjukNoz21880DjZMd3Js",
            width='stretch'
        )

    # --- Colonna destra: form login o registrazione
    with col2:
    
        if choice == "Login":
            with st.form("login_form"):
                email = st.text_input(
                    "Email", value=st.session_state.email_for_recovery or ""
                )
                password = st.text_input("Password", type="password")
                login_submitted = st.form_submit_button("Continue")

                if login_submitted:
                    user, logged_in = login(email, password, supabase, teams)
                    if logged_in:
                        st.session_state.user = user
                        st.session_state.logged_in = True
                        st.session_state.show_recovery = False
                        st.session_state.email_for_recovery = None
                        st.rerun()
                    else:
                        email_exists = any(
                            team.get("mail") == email for team in teams.data
                        )
                        if email_exists:
                            st.warning("Wrong password. Do you want to retrieve it?")
                            st.session_state.email_for_recovery = email
                            st.session_state.show_recovery = True
                        else:
                            st.warning("Email is not registered!")
                            st.session_state.show_recovery = False
                            st.session_state.email_for_recovery = None

            if st.session_state.show_recovery:
                if st.button("Retrieve password"):
                    try:
                        direct_link = generate_direct_recovery_link_and_send(
                            st.session_state.email_for_recovery
                        )
                        st.success("Check your email for the reset link!")
                        st.session_state.show_recovery = False
                    except Exception as e:
                        st.error(f"Error sending recovery email: {e}")

        else:
            with st.form("registration_form"):
                name = st.text_input("Your Name", key="reg_name")
                place = st.text_input("Location", key="reg_place")
                email = st.text_input("Email", key="reg_email")
                password = st.text_input("Password", type="password", key="reg_password")
                register_submitted = st.form_submit_button("Register")

                if register_submitted:
                    email_exists = any(team.get("mail") == email for team in teams.data)
                    if email_exists:
                        st.warning("This email is already registered. Please log in instead.")
                        st.stop()

                    if not is_valid_password(password):
                        st.warning(
                            "Invalid password. It must be at least 8 characters long, "
                            "contain at least one letter and one number."
                        )
                        st.stop()

                    user, success = register(email, password, supabase)
                    if not success or user is None:
                        st.error("Registration failed. Please try again.")
                        st.stop()
                    user_uuid = user.id

                    try:
                        supabase.table("class_new").insert({
                            "UUID": user_uuid,
                            "who": name,
                            "mail": email,
                            "where": place,
                        }).execute()
                    except Exception as e:
                        st.error(f"Errore salvataggio su DB: {e}")
                        st.stop()
                    st.success("Registration successful! Please log in.")







































