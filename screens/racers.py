import html as _html
from supabase import create_client
import streamlit as st
from logic.functions import parse_list_field, normalize_fullname_for_keys, safe_rgb_to_hex, get_supabase_client

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

supabase = get_supabase_client()

# --------------------- RACERS SCREEN ----------------------------------------------------

def racers_screen(user):
    from urllib.parse import quote_plus

    st.title("Racers")

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

    teams = supabase.from_("class").select("*").execute().data or []
    racers_f1 = supabase.from_("racers_f1").select("*").execute().data or []
    racers_mgp = supabase.from_("racers_mgp").select("*").execute().data or []

    pilot_to_fpk = {}
    for t in teams:
        team_name = t.get("name") or t.get("Name") or ""
        for key, val in t.items():
            if not key:
                continue
            kl = key.lower()
            if kl in ("f1", "f1drivers", "drivers_f1", "drivers") or "motogp" in kl or kl in ("mgp", "moto", "moto_gp"):
                members = parse_list_field(val)
                for m in members:
                    k = normalize_fullname_for_keys(m)
                    pilot_to_fpk[k.lower()] = team_name

    all_racers = []
    for r in racers_f1:
        r["_category"] = "F1"
        all_racers.append(r)
    for r in racers_mgp:
        r["_category"] = "MotoGP"
        all_racers.append(r)

    def parse_value(v):
        if v is None:
            return 0
        try:
            return float(str(v).replace(",", "."))
        except:
            return 0

    rows = []
    for r in all_racers:
        rid = r.get("ID") or r.get("name") or r.get("id") or ""
        rid_str = str(rid).strip()
        cat = r.get("_category", "")

        main_raw = r.get("main_color") or r.get("main color") or r.get("mainColor")
        second_raw = r.get("second_color") or r.get("second color") or r.get("secondColor")
        main_hex = safe_rgb_to_hex(main_raw)
        second_hex = safe_rgb_to_hex(second_raw or main_raw)

        name_html = (
            '<div style="display:flex;align-items:center;gap:10px;">'
            f'<span style="display:inline-block;width:20px;height:20px;'
            f'background-color:{main_hex};border:2px solid {second_hex};'
            f'border-radius:4px;flex:0 0 20px;"></span>'
            f'<div style="display:inline-block;white-space:normal;"><b>{_html.escape(rid_str)}</b></div>'
            '</div>'
        )

        real_team = r.get("real_team") or r.get("real team") or ""
        value_int = int(round(parse_value(r.get("Value") or r.get("value") or 0)))
        fpk_key = normalize_fullname_for_keys(rid_str)
        fpk_team = pilot_to_fpk.get(fpk_key.lower(), "")

        rows.append({
            "Pilota_html": name_html,
            "Pilota_raw": rid_str,
            "Categoria": cat,
            "Team reale": _html.escape(real_team),
            "Team FPK": _html.escape(fpk_team),
            "Valore": value_int
        })

    rows_sorted = sorted(rows, key=lambda x: x["Valore"], reverse=True)

    with st.expander("Filters", expanded=False):
        search_name = st.text_input("Search:")
        category_filter = st.selectbox("Category:", options=["All", "F1", "MotoGP"], index=0)
        min_value = st.number_input("Minimum value:", min_value=0, value=0, step=1)

    search_name = locals().get("search_name", "") or ""
    category_filter = locals().get("category_filter", "All") or "All"
    min_value = locals().get("min_value", 0) or 0

    filtered_rows = []
    for r in rows_sorted:
        if search_name and search_name.lower() not in r["Pilota_raw"].lower():
            continue
        if category_filter != "All" and r["Categoria"] != category_filter:
            continue
        if r["Valore"] < min_value:
            continue
        filtered_rows.append(r)

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
        row_html = (
            '<div class="row-box">'
            f'<div style="width:40px"></div>'
            f'<div class="col-name" title="{_html.escape(r["Pilota_raw"])}">{r["Pilota_html"]}</div>'
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
