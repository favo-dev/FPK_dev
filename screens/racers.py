import html as _html
from supabase import create_client
import streamlit as st
from logic.functions import parse_list_field, normalize_fullname_for_keys, safe_rgb_to_hex

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --------------------- RACERS SCREEN ----------------------------------------------------

def racers_screen(user):
    from urllib.parse import quote_plus

    st.title("Racers")

    # handle query params navigation verso dettagli pilota
    q = st.query_params
    if "pilot" in q:
        sel_pilot = q.get("pilot", [""])[0]
        sel_cat = q.get("category", [""])[0] if "category" in q else ""
        if sel_pilot:
            st.session_state["selected_pilot"] = sel_pilot
            st.session_state["selected_category"] = sel_cat
            st.query_params.clear()
            st.session_state["screen"] = "pilot_details"
            st.rerun()

    # --- fetch base tables
    teams = supabase.from_("class").select("*").execute().data or []
    racers_f1 = supabase.from_("racers_f1_new").select("*").execute().data or []
    racers_mgp = supabase.from_("racers_mgp_new").select("*").execute().data or []

    # league id dell'utente (per fetch delle stats)
    league_id = str(user.get("league")) if isinstance(user, dict) and user.get("league") is not None else None

    # --- costruisci mapping team FPK per pilota
    pilot_to_fpk = {}
    for t in teams:
        team_name = t.get("name") or t.get("Name") or ""
        for key, val in t.items():
            if not key:
                continue
            kl = key.lower()
            # riconosciamo campi che contengono piloti/driver lists (adattalo se necessario)
            if kl in ("f1", "f1drivers", "drivers_f1", "drivers") or "motogp" in kl or kl in ("mgp", "moto", "moto_gp"):
                members = parse_list_field(val)
                for m in members:
                    k = normalize_fullname_for_keys(m)
                    pilot_to_fpk[k.lower()] = team_name

    # --- unisci tutti i racers in un'unica lista e aggiungi _category
    all_racers = []
    for r in racers_f1:
        r["_category"] = "F1"
        all_racers.append(r)
    for r in racers_mgp:
        r["_category"] = "MotoGP"
        all_racers.append(r)

    # --- prepara liste di player_id per fetch bulk delle stats per categoria
    f1_ids = [str(r.get("ID") or r.get("id") or r.get("name") or "").strip() for r in racers_f1 if (r.get("ID") or r.get("id") or r.get("name"))]
    mgp_ids = [str(r.get("ID") or r.get("id") or r.get("name") or "").strip() for r in racers_mgp if (r.get("ID") or r.get("id") or r.get("name"))]

    # --- fetch bulk stats per categoria (mapping player_id -> stats row)
    stats_f1_map = {}
    stats_mgp_map = {}
    try:
        if league_id and f1_ids:
            resp = (
                supabase
                .from_("league_f1_stats")
                .select("*")
                .eq("league_id", league_id)
                .in_("player_id", f1_ids)
                .execute()
            )
            for r in (resp.data or []):
                key = str(r.get("player_id") or "").strip()
                stats_f1_map[key] = r
    except Exception:
        stats_f1_map = {}

    try:
        if league_id and mgp_ids:
            resp = (
                supabase
                .from_("league_mgp_stats")
                .select("*")
                .eq("league_id", league_id)
                .in_("player_id", mgp_ids)
                .execute()
            )
            for r in (resp.data or []):
                key = str(r.get("player_id") or "").strip()
                stats_mgp_map[key] = r
    except Exception:
        stats_mgp_map = {}

    # helper per convertire valori numerici/assenti
    def parse_value(v):
        if v is None:
            return 0
        try:
            return float(str(v).replace(",", "."))
        except Exception:
            return 0

    # --- prepara le righe da visualizzare
    rows = []
    for r in all_racers:
        # identifica l'id (usato come player_id nelle stats)
        rid = r.get("ID") or r.get("name") or r.get("id") or ""
        rid_str = str(rid).strip()
        cat = r.get("_category", "")

        # colori
        main_raw = r.get("main_color") or r.get("main color") or r.get("mainColor")
        second_raw = r.get("second_color") or r.get("second color") or r.get("secondColor")
        main_hex = safe_rgb_to_hex(main_raw)
        second_hex = safe_rgb_to_hex(second_raw or main_raw)

        # nome + pill colore
        name_html = (
            '<div style="display:flex;align-items:center;gap:10px;">'
            f'<span style="display:inline-block;width:20px;height:20px;'
            f'background-color:{main_hex};border:2px solid {second_hex};'
            f'border-radius:4px;flex:0 0 20px;"></span>'
            f'<div style="display:inline-block;white-space:normal;"><b>{_html.escape(rid_str)}</b></div>'
            '</div>'
        )

        # team real / FPK
        real_team = r.get("real_team") or r.get("real team") or ""
        value_int = int(round(parse_value(r.get("Value") or r.get("value") or 0)))
        fpk_key = normalize_fullname_for_keys(rid_str)
        fpk_team = pilot_to_fpk.get(fpk_key.lower(), "")

        # --- prendi stats dalla mappa corretta in base alla categoria
        stats_map = stats_f1_map if cat == "F1" else stats_mgp_map
        s = stats_map.get(rid_str, {}) if stats_map is not None else {}

        # campi di stats comuni (fallback a 0)
        convocations = int(parse_value(s.get("convocations"))) if s.get("convocations") is not None else 0
        dnf = int(parse_value(s.get("DNF") or s.get("dnf"))) if (s.get("DNF") is not None or s.get("dnf") is not None) else 0
        wins = int(parse_value(s.get("wins"))) if s.get("wins") is not None else 0
        sprint_wins = int(parse_value(s.get("sprint_wins"))) if s.get("sprint_wins") is not None else 0
        poles = int(parse_value(s.get("poles"))) if s.get("poles") is not None else 0
        sprint_poles = int(parse_value(s.get("sprint_poles"))) if s.get("sprint_poles") is not None else 0
        podiums = int(parse_value(s.get("podiums"))) if s.get("podiums") is not None else 0
        sub = int(parse_value(s.get("sub"))) if s.get("sub") is not None else 0
        historical_wins = int(parse_value(s.get("historical_wins"))) if s.get("historical_wins") is not None else 0
        historical_poles = int(parse_value(s.get("historical_poles"))) if s.get("historical_poles") is not None else 0
        historical_sprint_wins = int(parse_value(s.get("historical_sprint_wins"))) if s.get("historical_sprint_wins") is not None else 0


        rows.append({
            "Pilota_html": name_html,
            "Pilota_raw": rid_str,
            "Categoria": cat,
            "Team reale": _html.escape(real_team),
            "Team FPK": _html.escape(fpk_team),
            "Valore": value_int,
            # includi stats raw per eventuali usi successivi
            "stats": {
                "convocations": convocations,
                "DNF": dnf,
                "wins": wins,
                "sprint_wins": sprint_wins,
                "poles": poles,
                "sprint_poles": sprint_poles,
                "podiums": podiums,
                "sub": sub,
                "historical_wins": historical_wins,
                "historical_poles": historical_poles,
                "historical_sprint_wins": historical_sprint_wins
            },
        })

    # ordina per Valore (come prima)
    rows_sorted = sorted(rows, key=lambda x: x["Valore"], reverse=True)

    # --- Filters UI (uguale a prima) ---
    with st.expander("Filters", expanded=False):
        search_name = st.text_input("Search:")
        category_filter = st.selectbox("Category:", options=["All", "F1", "MotoGP"], index=0)
        min_value = st.number_input("Minimum value:", min_value=0, value=0, step=1)

    # compatibilità con il comportamento esistente: usa i valori locali se presenti
    search_name = locals().get("search_name", "") or ""
    category_filter = locals().get("category_filter", "All") or "All"
    min_value = locals().get("min_value", 0) or 0

    # --- filtra le righe
    filtered_rows = []
    for r in rows_sorted:
        if search_name and search_name.lower() not in r["Pilota_raw"].lower():
            continue
        if category_filter != "All" and r["Categoria"] != category_filter:
            continue
        if r["Valore"] < min_value:
            continue
        filtered_rows.append(r)

    # --- stile e rendering (uguale a prima), ma mostriamo anche la stats_line sotto il nome
    st.markdown(
        """
    <style>
      .racers-container { font-family: sans-serif; color: #fff; }
      .header-row { display: flex; gap: 12px; padding: 10px 16px; font-weight: 700; background: #000; color: #fff; border-radius: 10px; align-items:center; }
      .row-box { display: flex; gap: 16px; padding: 14px 20px; align-items: center; border-radius: 18px; margin: 10px 0; background: linear-gradient(180deg,#1f1f1f,#171717); border: 1px solid rgba(255,255,255,0.03); min-height: 80px; }
      .row-box .col-name { flex: 4; font-weight: 700; color: #fff; overflow: visible; text-overflow: ellipsis; white-space: normal; }
      .row-box .col-team { flex: 3; color: #ddd; overflow: visible; text-overflow: ellipsis; white-space: normal; line-height: 1.3; }
      .row-box .col-fpk { flex: 3; color: #bbb; overflow: visible; text-overflow: ellipsis; white-space: normal; line-height: 1.3; }
      .row-box .col-value { flex: 1; min-width: 100px; text-align: right; font-weight: 600; color: #fff; margin-right: 8px; }
      .stats-line { color: #aaa; font-size: 12px; margin-top: 6px; }
      div.stButton > button { padding: 6px 10px !important; border-radius: 14px !important; min-width: 80px; white-space: nowrap; font-weight: 600; height: 32px; line-height: 16px; }
      .stButton { display: flex; align-items: center; justify-content: flex-end; height: 80px; }
      .no-results { color: #ddd; padding: 12px 0; }
      .header-row .h-col { padding: 0 8px; }
    </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="racers-container">', unsafe_allow_html=True)

    left_hcol, btn_hcol = st.columns([0.84, 0.16])
    header_html = (
        '<div class="header-row">'
        '<div style="width:40px"></div>'
        '<div class="h-col" style="flex:4">Racer</div>'
        '<div class="h-col" style="flex:3">Real team</div>'
        '<div class="h-col" style="flex:3">FPK team</div>'
        '<div class="h-col" style="flex:1; text-align:right; min-width:100px">Value</div>'
        '</div>'
    )
    left_hcol.markdown(header_html, unsafe_allow_html=True)
    btn_hcol.markdown('<div style="height:80px;display:flex;align-items:center;justify-content:center;font-weight:700"></div>', unsafe_allow_html=True)

    if not filtered_rows:
        st.markdown('<div class="no-results">No racers match the filters.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        return

    for i, r in enumerate(filtered_rows):
        # include stats_line sotto il nome
        row_html = (
            '<div class="row-box">'
            f'<div style="width:40px"></div>'
            f'<div class="col-name" title="{_html.escape(r["Pilota_raw"])}">{r["Pilota_html"]}'
            f'<div class="stats-line">{_html.escape(r["stats_line"])}</div>'
            f'</div>'
            f'<div class="col-team" title="{_html.escape(r["Team reale"])}">{r["Team reale"]}</div>'
            f'<div class="col-fpk" title="{_html.escape(r["Team FPK"])}">{r["Team FPK"]}</div>'
            f'<div class="col-value">{int(r["Valore"]):,}</div>'
            '</div>'
        )

        left_col, btn_col = st.columns([0.84, 0.16])
        left_col.markdown(row_html, unsafe_allow_html=True)

        key = f"open_racer_{i}_{r['Pilota_raw']}"
        if btn_col.button("Info", key=key):
            st.session_state["selected_pilot"] = r["Pilota_raw"]
            st.session_state["selected_category"] = r["Categoria"]
            hist = st.session_state.get("screen_history", [])
            hist.append("racers")
            st.session_state["screen_history"] = hist
            st.session_state["screen"] = "pilot_details"
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
