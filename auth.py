import streamlit as st
import json
import datetime
from logic.knock import load_teams, save_teams, load_pilot
from argon2.exceptions import VerifyMismatchError
import os
import time




# Funzione per capire se una password è già hashata argon2
def is_hashed(pw):
    # Gli hash argon2 iniziano con "$argon2"
    return isinstance(pw, str) and pw.startswith("$argon2")

# Assicuriamoci che tutte le password siano hashate
def ensure_hashed_passwords(teams, master, ph):
    teams = load_teams(master)
    changed = False
    for team in teams:
        pw = team.get("password", "")
        if pw and not is_hashed(pw):
            team["password"] = ph.hash(pw)
            changed = True
            
    if changed:
        filepath = os.path.join(master + 'data/class.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(teams, f, indent=4, ensure_ascii=False)
    return changed

def color_to_rgb(hex_color):
    return [int(hex_color[i:i+2], 16) for i in (1, 3, 5)]

def login_or_register(master):
    st.title("Welcome to FPK")
    teams = load_teams(master)
    mail_to_team = {team["mail"]: team for team in teams}

    st.subheader("Login")
    mode = st.radio("Select one:", ["Access", "Registration"])

    if mode == "Access":
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Access"):
            if email in mail_to_team:
                team = mail_to_team[email]
                if password == team["password"]:
                    st.session_state.user = team
                    st.session_state.logged_in = True
                    st.rerun()
                    return True
                else:
                    st.error("Wrong password. Please contact +39 3664306339 for help")
            else:
                st.error("E-mail is not associated to any account")
        return False

    elif mode == "Registration":
        with open(master + "data/racers_f1.json", "r",encoding="utf-8") as f:
            f1_drivers = json.load(f)
        with open(master + "data/racers_mgp.json", "r",encoding="utf-8") as f:
            motogp_riders = json.load(f)
        
        f1_options = [d["ID"] for d in f1_drivers if d.get("go", False)]
        motogp_options = [r["ID"] for r in motogp_riders if r.get("go", False)]
        
        st.info("Please fill out the form:")
        with st.form("new_team"):
            who = st.text_input("Name and Surname")
            name = st.text_input("Team name")
            mail = st.text_input("Email")
            password = st.text_input("Password", type="password")
            main_color = st.color_picker("Principal color")
            second_color = st.color_picker("Secondary color") 
            selected_f1 = st.multiselect("Select 3 F1 drivers", f1_options, max_selections=3)
            selected_motogp = st.multiselect("Select 3 MotoGP riders", motogp_options, max_selections=3)
            create = st.form_submit_button("Create team")

        if create:
            if mail in mail_to_team:
                st.error("A team associated to this email is already in use")
                return False
            if not all([who.strip(), name.strip(), mail.strip(), password.strip()]):
                st.error("All fields must be filled.")
                return False 
            if len(selected_motogp) != 3 or len(selected_f1) != 3:
                st.error("You must select exactly 3 MotoGP and 3 F1 riders.")
                return False

            new_team = {
                "ID": f"team{len(teams) + 1}",
                "who": who,
                "name": name,
                "mail": mail,
                "main color": color_to_rgb(main_color),
                "second color": color_to_rgb(second_color),
                "F1": selected_f1,
                "MotoGP": selected_motogp,
                "password": password,
                "foundation": datetime.datetime.now().year
            }
            teams.append(new_team)
            save_teams(master, teams)
            st.session_state.user = new_team
            st.session_state.logged_in = True
            st.rerun()

            return True
        return False
    
    
    
    
    
    
#____________________________________________________________________________

def login_and_reg(master, ph, teams):
    st.title("Welcome to FPK")
    # Prepariamo i dati per autenticazione
    ID = [team["ID"] for team in teams]
    usernames = [team["mail"] for team in teams]
    names = [team["who"] for team in teams]
    hashed_passwords = [team["password"] for team in teams]

    # Costruiamo dict credenziali per login
    credentials = {
        "usernames": {
            usernames[i]: {
                "name": names[i],
                "password": hashed_passwords[i],
                "id": ID[i]
            }
            for i in range(len(teams))
        }
    }

    # Funzione di login personalizzata con argon2
    def login(credentials, teams):
        st.subheader("Login")
        username = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Continue", key = "1"):
            if username in credentials["usernames"]:
                hashed_pw = credentials["usernames"][username]["password"]
                try:
                    if ph.verify(hashed_pw, password):
                        for team in teams:
                            if username in team["mail"]:
                                st.session_state.user = team
                        st.session_state.logged_in = True
                        st.rerun()
                        return True

                    else:
                        st.error("Wrong password!")
                        return False
                except VerifyMismatchError:
                    st.error("Wrong password!")
                    return False
            else:
                st.error("E-mail is not associated to an existing account!")
                return False
        return None
    
    # Funzione registrazione con hashing
    def register(teams):
        with st.expander("New account"):
            st.subheader("Registration")
            f1_drivers = load_pilot(master, "F1")
            mgp_riders = load_pilot(master, "MGP")
            f1_options = [d["ID"] for d in f1_drivers if d.get("go", False)]
            mgp_options = [r["ID"] for r in mgp_riders if r.get("go", False)]
            who = st.text_input("Name and Surname", key="reg_who")
            name = st.text_input("Team name", key="reg_name")
            mail = st.text_input("E-mail", key="reg_mail")
            password = st.text_input("Password", type="password", key="reg_pw")
            main_color = st.color_picker("Principal color")
            second_color = st.color_picker("Secondary color") 
            selected_f1 = st.multiselect("Select 3 F1 drivers", f1_options, max_selections=3)
            selected_mgp = st.multiselect("Select 3 MotoGP riders", mgp_options, max_selections=3)
            if st.button("Continue", key = "2"):
                if mail in credentials["usernames"]:
                    st.error("E-mail is already associated to an existing account!")
                elif not all([who.strip(), mail.strip(), password.strip()]):
                    st.error("All fields shall be filled!")
                elif len(selected_mgp) != 3 or len(selected_f1) != 3:
                    st.error("You must select exactly 3 MotoGP and 3 F1 riders.")
                    return False
                else:
                    hashed_pw = ph.hash(password)
                    new_team = {
                        "ID": f"team{len(teams)+1}",
                        "who": who,
                        "name": name,
                        "mail": mail,
                        "password": hashed_pw,
                        "main color": color_to_rgb(main_color),
                        "second color": color_to_rgb(second_color),
                        "F1": selected_f1,
                        "MotoGP": selected_mgp,
                        "foundation": datetime.datetime.now().year
                    }
                    teams.append(new_team)
                    save_teams(master, teams)
                    teams = load_teams(master)
                    st.toast("Team created! You can now log-in!")
                    
                    

    # Uso
    auth_status = login(credentials, teams)
    if not auth_status:
        register(teams)

    
        
        
   