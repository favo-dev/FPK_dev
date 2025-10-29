def your_team_screen(user):
    st.header("Your Team")

    st.markdown(
        f"<div style='width:100%;max-width:900px;height:10px;background:linear-gradient(90deg,{safe_rgb_to_hex(user.get('main color','255,0,0'))},{safe_rgb_to_hex(user.get('second color','0,0,255'))});border-radius:12px;box-shadow:0 3px 8px rgba(0,0,0,.15);margin-bottom:1.5rem'></div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style='max-width:700px;
                    background:#333;
                    border-radius:14px;
                    padding:20px;
                    color:white;
                    font-size:1.2rem;
                    display:flex;
                    justify-content:space-around;
                    margin-bottom:1.8rem;
                    box-shadow:0 4px 10px rgba(0,0,0,.4)'>
            <div><strong>Founded in:</strong> {user.get('foundation','N/A')}</div>
            <div><strong>League:</strong> {user.get('league','N/A')}</div>
            <div><strong>Location:</strong> {user.get('where','N/A')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div style='max-width:900px;
                    background:#f9f9f9;
                    border-radius:14px;
                    box-shadow:0 4px 12px rgba(0,0,0,.07);
                    padding:20px;
                    display:grid;
                    grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
                    gap:18px;
                    font-size:1.1rem;
                    color:#222;
                    margin-bottom:2.5rem'>
            <div><strong>FF1:</strong> {user.get('ff1','N/A')}</div>
            <div><strong>FMGP:</strong> {user.get('fmgp','N/A')}</div>
            <div><strong>FPK:</strong> {user.get('fm','N/A')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.session_state.setdefault("selected_driver", None)
    st.session_state.setdefault("customizing", False)

    # dati racer (restano per eventuali usi)
    f1_data = supabase.from_("racers_f1_new").select("*").execute().data or []
    mgp_data = supabase.from_("racers_mgp_new").select("*").execute().data or []

    st.subheader("Options")

    st.markdown(""" 
    <style>
    /* Call-ups & Customize: bordo azzurro e testo in grassetto */
    div.stButton>button[key="btn_callups"],
    div.stButton>button[key="open_custom"],
    div.stButton>button[key="close_custom"] {
        font-weight: 700 !important;
        border: 2px solid #1e90ff !important; /* azzurro */
    }

    /* Exit: bordo rosso e testo in grassetto */
    div.stButton>button[key="exit_button"] {
        font-weight: 700 !important;
        border: 2px solid #d93025 !important; /* rosso */
    }

    /* Mantieni testo leggibile anche se lo sfondo è il default di Streamlit */
    div.stButton>button[key="btn_callups"],
    div.stButton>button[key="open_custom"],
    div.stButton>button[key="close_custom"],
    div.stButton>button[key="exit_button"] {
        color: inherit !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- controllo: quante righe 'teams' ha questo user? (per abilitare "Change league")
    user_uuid = user.get("UUID")
    teams_rows_for_user = []
    try:
        if user_uuid:
            teams_rows_for_user = supabase.from_("teams").select("ID,league").eq("UUID", user_uuid).execute().data or []
    except Exception:
        teams_rows_for_user = []
    teams_count = len(teams_rows_for_user)
    has_multiple_teams = teams_count > 1

    # Ora 4 colonne: Call-ups | Customize | Change league (condizionale) | Exit
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    if col1.button("Call-ups", key="btn_callups"):
        st.session_state.screen = "callups"
        st.rerun()

    if not st.session_state.customizing:
        if col2.button("Customize team", key="open_custom"):
            st.session_state.customizing = True
            st.rerun()
    else:
        if col2.button("Close customization", key="close_custom"):
            st.session_state.customizing = False
            st.rerun()

    # Change league: visibile SOLO se l'utente ha più di una squadra
    if has_multiple_teams:
        if col3.button("Change league", key="change_league"):
            # salva la schermata corrente nella cronologia e vai alla schermata di selezione leagues
            hist = st.session_state.get("screen_history", [])
            hist.append(st.session_state.get("screen", "team"))
            st.session_state["screen_history"] = hist
            # porta l'utente alla schermata di selezione league (nel tuo progetto la schermata è 'leagues')
            st.session_state.screen = "leagues"
            st.rerun()
    else:
        # mostra un pulsante disabilitato/placeholder (meglio che niente), oppure un testo esplicativo
        col3.markdown("<div style='opacity:0.6; padding-top:6px; text-align:center'>Change league</div>", unsafe_allow_html=True)

    # Exit
    if col4.button("Exit", key="exit_button"):
        st.session_state.screen = "confirm_exit"
        st.rerun()

    st.markdown("---")

    # --- customization panel (se attivo) ---
    if st.session_state.customizing:
        st.markdown("### Customize your profile")
        st.markdown("<div style='border:2px solid #ddd;padding:2rem;border-radius:16px;max-width:700px;background:#fff;box-shadow:0 4px 14px rgba(0,0,0,.05);margin-bottom:3rem'>", unsafe_allow_html=True)
        update_user_field(user, "mail", "New email", supabase, SUPABASE_SERVICE_ROLE_KEY)
        update_user_field(user, "who", "New name", supabase)
        update_user_field(user, "name", "Team name", supabase)
        update_user_field(user, "where", "Location", supabase)
        new_main = st.color_picker("Principal color", value=safe_rgb_to_hex(user.get("main color", [255,255,255])))
        if st.button("Save principal color", use_container_width=True):
            supabase.table("teams").update({"main color": color_to_rgb(new_main)}).eq("who", user["who"]).eq("league", user["league"]).execute()
            st.success("Principal color updated!")
        new_second = st.color_picker("Second color", value=safe_rgb_to_hex(user.get("second color", [0,0,0])))
        if st.button("Save second color", use_container_width=True):
            supabase.table("teams").update({"second color": color_to_rgb(new_second)}).eq("who", user["who"]).eq("league", user["league"]).execute()
            st.success("Secondary color updated!")
        st.markdown("</div>", unsafe_allow_html=True)

    # --- racers display ---

    def morpher(name, prefix, idx):
        base = re.sub(r"\W+", "_", name).strip("_").lower() or f"r{idx}"
        return f"{prefix}_{base}_{idx}"

    st.subheader("F1 Drivers")
    raw_f1 = user.get("F1", [])
    f1_riders = normalize_riders(raw_f1)
    if f1_riders:
        num_cols = 4
        for i in range(0, len(f1_riders), num_cols):
            cols = st.columns(num_cols)
            for j, r in enumerate(f1_riders[i:i+num_cols]):
                key = morpher(r, "f1", i+j)
                if cols[j].button(r, key=key):
                    st.session_state.screen_history.append(st.session_state.screen)
                    st.session_state.selected_driver = r
                    st.session_state.selected_category = "F1"
                    st.session_state.screen = "racer_detail"
                    st.rerun()
    else:
        st.write("No F1 riders selected")

    st.subheader("MotoGP Riders")
    raw_mgp = user.get("MotoGP", [])
    mgp_riders = normalize_riders(raw_mgp)
    if mgp_riders:
        num_cols = 4
        for i in range(0, len(mgp_riders), num_cols):
            cols = st.columns(num_cols)
            for j, r in enumerate(mgp_riders[i:i+num_cols]):
                key = morpher(r, "mgp", i+j)
                if cols[j].button(r, key=key):
                    st.session_state.screen_history.append(st.session_state.screen)
                    st.session_state.selected_driver = r
                    st.session_state.selected_category = "MotoGP"
                    st.session_state.screen = "racer_detail"
                    st.rerun()
    else:
        st.write("No MotoGP riders selected")
