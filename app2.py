import os
import sys
import subprocess
from urllib.parse import urlparse, parse_qsl
import datetime
import streamlit as st
from supabase import create_client, Client
from logic.auth import register, login
from screens.home import home_screen
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from cryptography.fernet import Fernet

# --------------------- FUNCTIONS ---------------------------------------------
def clone_repo(CLONE_DIR, REPO_URL):
    if not os.path.exists(CLONE_DIR):
        print("Cloning repository...")
        subprocess.check_call(["git", "clone", REPO_URL, CLONE_DIR])

def logout():
    supabase.auth.sign_out()
    st.session_state.logged_in = False
    st.session_state.user = None
    st.success("Logout effettuato.")
    st.rerun()

def send_email_sendgrid(to_email: str, subject: str, body_text: str):
    SENDGRID_API_KEY = os.environ["SENDGRID_API_KEY"]
    EMAIL_FROM = os.environ.get("EMAIL_FROM", "noreply@fantapaddock.app")
    message = Mail(
        from_email=EMAIL_FROM,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body_text,
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
    except Exception as e:
        st.error(f"Errore invio email: {e}")

# --------------------- EMAIL CRYPTO ------------------------------------------
def encrypt_email(email: str) -> str:
    key = os.environ["FERNET_KEY"].encode()
    f = Fernet(key)
    return f.encrypt(email.encode()).decode()

def decrypt_email(token: str) -> str:
    key = os.environ["FERNET_KEY"].encode()
    f = Fernet(key)
    return f.decrypt(token.encode()).decode()

# --------------------- GENERATE RECOVERY LINK --------------------------------
def generate_direct_recovery_link_and_send(email: str):
    SUPABASE_URL = os.environ["SUPABASE_URL"]
    SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    STREAMLIT_URL = os.environ.get("STREAMLIT_URL", "https://fantapaddock.streamlit.app")

    supabase_admin = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    resp = supabase_admin.auth.admin.generate_link(
        {"type": "recovery", "email": email}
    )

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
    send_email_sendgrid(email, subject, body)
    return direct_link

# --------------------- SETTINGS ----------------------------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN non trovato nelle variabili d'ambiente!")

REPO_URL = f"https://{GITHUB_TOKEN}@github.com/andreafavalli/FPK.git"
CLONE_DIR = "FPK"
clone_repo(CLONE_DIR, REPO_URL)
sys.path.insert(0, os.path.abspath(CLONE_DIR))

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
teams = supabase.table("class").select("*").execute()

st.set_page_config(page_title="FPK 1.0.0 'Vettel'")
st.set_page_config(
    page_icon="https://koffsyfgevaannnmjkvl.supabase.co/storage/v1/object/sign/figures/new_favicon.svg?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV9hNTU1ZWI5ZC03NmZjLTRiMjUtOGIwMC05ZDQ4ZTRhNGNhMDEiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJmaWd1cmVzL25ld19mYXZpY29uLnN2ZyIsImlhdCI6MTc1ODYzODEzNSwiZXhwIjoxNzkwMTc0MTM1fQ.zNy8m0uD7IWJQ4ruDNeZduQmTgnyBYbibFg3T-8D5fQ"
)

# --------------------- SESSION STATE -----------------------------------------
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

# --------------------- QUERY PARAMS HANDLER ----------------------------------
def _get_first(qp, k):
    v = qp.get(k)
    if v is None:
        return None
    return v[0] if isinstance(v, (list, tuple)) else v

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

# --------------------- RESET PASSWORD ----------------------------------------
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

# --------------------- PASSWORD VALIDATION -----------------------------------
def is_valid_password(password: str) -> bool:
    return (
        len(password) >= 8
        and any(c.isalpha() for c in password)
        and any(c.isdigit() for c in password)
    )


# --------------------- MAIN APP ----------------------------------------------
if st.session_state.logged_in:
    # 🏠 HOME SCREEN
    home_screen(st.session_state.user)
else:
    # 🔑 LOGIN / REGISTRAZIONE
    st.title("Login / Registration")
    choice = st.radio("Select:", ["Login", "Registration"])

    # --- Layout a due colonne: immagine a sinistra, form a destra
    col1, col2 = st.columns([1, 2])

    # --- Colonna sinistra: immagine sempre visibile
    with col1:
        st.image(
            "https://koffsyfgevaannnmjkvl.supabase.co/storage/v1/object/sign/figures/FM-1.png?token=eyJraWQiOiJzdG9yYWdlLXVybC1zaWduaW5nLWtleV9hNTU1ZWI5ZC03NmZjLTRiMjUtOGIwMC05ZDQ4ZTRhNGNhMDEiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJmaWd1cmVzL0ZNLTEucG5nIiwiaWF0IjoxNzU4NzA2NzI2LCJleHAiOjE3OTAyNDI3MjZ9.x5MLW8w-pm5t3syML6baJDlVjukNoz21880DjZMd3Js",
            use_container_width=True
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

        else:  # Registration
            # --- Recupero opzioni piloti da Supabase (prima del form)
            try:
                racers_f1_resp = supabase.table("racers_f1").select("*").execute()
                racers_moto_resp = supabase.table("racers_mgp").select("*").execute()
            except Exception as e:
                st.error(f"Errore nel recupero dei piloti: {e}")
                racers_f1_resp = None
                racers_moto_resp = None

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

            f1_options = []
            if racers_f1_resp and getattr(racers_f1_resp, "data", None):
                for r in racers_f1_resp.data:
                    n = _extract_name(r)
                    if n:
                        f1_options.append(n)

            moto_options = []
            if racers_moto_resp and getattr(racers_moto_resp, "data", None):
                for r in racers_moto_resp.data:
                    n = _extract_name(r)
                    if n:
                        moto_options.append(n)

            with st.form("registration_form"):
                name = st.text_input("Your Name", key="reg_name")
                team_name = st.text_input("Team Name", key="reg_team_name")
                place = st.text_input("Location", key="reg_place")
                main_color_hex = st.color_picker("Main Color", "#ff0000", key="reg_main_color")
                second_color_hex = st.color_picker("Secondary Color", "#0000ff", key="reg_second_color")

                st.markdown("### Select 3 F1 drivers")
                f1_selected = st.multiselect(
                    "F1 drivers (select 3)",
                    options=f1_options,
                    key="reg_f1_selection",
                    help="Scegli 3 piloti F1 diversi"
                )

                st.markdown("### Select 3 MotoGP riders")
                moto_selected = st.multiselect(
                    "MotoGP riders (select 3)",
                    options=moto_options,
                    key="reg_moto_selection",
                    help="Scegli 3 piloti MotoGP diversi"
                )

                email = st.text_input("Email", key="reg_email")
                password = st.text_input("Password", type="password", key="reg_password")
                register_submitted = st.form_submit_button("Register")

                if register_submitted:
                    # validazioni base
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

                    # controllo selezioni piloti
                    if len(f1_selected) != 3:
                        st.warning("You shall select 3 F1 drivers.")
                        st.stop()
                    if len(moto_selected) != 3:
                        st.warning("You shall select 3 MotoGP riders.")
                        st.stop()

                    # 1. Creiamo utente in Supabase Auth e raccogliamo UUID
                    user, success = register(email, password, supabase)
                    if not success or user is None:
                        st.error("Registration failed. Please try again.")
                        st.stop()
                    user_uuid = user.id

                    # 2. Calcoliamo nuovo team_id
                    existing_ids = [
                        t.get("ID") or t.get("id") for t in teams.data if (t.get("ID") or t.get("id") or "").startswith("team")
                    ]
                    numbers = []
                    for x in existing_ids:
                        sx = str(x)
                        if sx.startswith("team") and sx.replace("team", "").isdigit():
                            numbers.append(int(sx.replace("team", "")))
                    next_number = max(numbers) + 1 if numbers else 1
                    new_team_id = f"team{next_number}"
                    while any((t.get("ID") == new_team_id or t.get("id") == new_team_id) for t in teams.data):
                        next_number += 1
                        new_team_id = f"team{next_number}"

                    # 3. Convertiamo hex → [R, G, B]
                    def hex_to_rgb_array(hex_color: str) -> list[int]:
                        hex_color = (hex_color or "").lstrip("#")
                        if len(hex_color) != 6:
                            return [0, 0, 0]
                        return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]

                    main_color = hex_to_rgb_array(main_color_hex)
                    second_color = hex_to_rgb_array(second_color_hex)

                    # 4. Prepariamo le stringhe dei piloti
                    f1_txt = str(f1_selected)
                    moto_txt = str(moto_selected)

                    # 5. Inserimento nella tabella class
                    try:
                        supabase.table("class").insert({
                            "ID": new_team_id,
                            "UUID": user_uuid,
                            "who": name,
                            "name": team_name,
                            "mail": email,
                            "main color": main_color,
                            "second color": second_color,
                            "where": place,
                            "foundation": datetime.datetime.now().year,
                            "F1": f1_txt,
                            "MotoGP": moto_txt
                        }).execute()
                    except Exception as e:
                        st.error(f"Errore salvataggio su DB: {e}")
                        st.stop()

                    # 6. Creiamo righe vuote in calls_f1, calls_mgp, penalty
                    try:
                        supabase.table("calls_f1").insert({"team": new_team_id}).execute()
                        supabase.table("calls_mgp").insert({"team": new_team_id}).execute()
                        supabase.table("penalty").insert({"team": new_team_id}).execute()
                    except Exception as e:
                        st.error(f"Errore creazione righe calls/penalty: {e}")
                        st.stop()

                    st.success("Registration successful! Please log in.")


