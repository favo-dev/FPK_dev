import ast
import html as _html
from supabase import create_client
import streamlit as st
import streamlit.components.v1 as components
import matplotlib.pyplot as plt
from logic.functions import (
    _estimate_rows_height,
    _parse_display_value,
    _count_items_like_list,
    _render_simple_table_html,
    normalize_fullname_for_keys,
    compute_stats_from_marks_record,
    avg_to_hex,  
)

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# --------------------- RACERS SCREEN ----------------------------------------------------

def show_racer_screen(user):
    league_id = user["league"]
    st.write(user)
    st.write(league_id)
    pilot = st.session_state.get("selected_pilot") or st.session_state.get("selected_driver")
    st.markdown("""
    <style>
    h1, h2, h3 { margin-top: 6px !important; margin-bottom: 6px !important; }  
    div.stButton > button { margin-top: 6px !important; margin-bottom: 6px !important; }
    </style>
    """, unsafe_allow_html=True)
    category = st.session_state.get("selected_category", "")

    if not pilot:
        st.warning("Nessun pilota selezionato.")
        return

    try:
        data_f1 = supabase.from_("racers_f1_new").select("*").execute().data or []
        data_mgp = supabase.from_("racers_mgp_new").select("*").execute().data or []
    except Exception:
        data_f1, data_mgp = [], []

    if not category:
        pid = str(pilot)
        found_in_f1 = any((str(p.get("id")) == pid) or (str(p.get("name")) == pid) for p in data_f1)
        found_in_mgp = any((str(p.get("id")) == pid) or (str(p.get("name")) == pid) for p in data_mgp)
        if found_in_f1 and not found_in_mgp:
            category = "F1"
            this_pilot_data = supabase.from_("league_f1_stats").eq("league_id", league_id).eq("player_id", pid).limit(1).execute().data or []
        elif found_in_mgp and not found_in_f1:
            category = "MotoGP"
            this_pilot_data = supabase.from_("league_mgp_stats").eq("league_id", league_id).eq("player_id", pid).limit(1).execute().data or []
        elif found_in_f1 and found_in_mgp:
            category = "F1"
            this_pilot_data = supabase.from_("league_f1_stats").eq("league_id", league_id).eq("player_id", pid).limit(1).execute().data or []

    data = data_f1 if (category or "").upper().startswith("F1") else data_mgp

    pilot_info = next(
        (p for p in data if (str(p.get("id")) == str(pilot)) or (str(p.get("name")) == str(pilot))),
        None
    )
    if not pilot_info:
        st.error(f"Informazioni per il pilota '{pilot}' non trovate.")
        if st.button("Go back"):
            for k in ("selected_pilot", "selected_driver", "selected_category"):
                if k in st.session_state:
                    del st.session_state[k]
            st.session_state.screen = (
                st.session_state.screen_history.pop()
                if st.session_state.get("screen_history")
                else "championship"
            )
            st.rerun()

        return

    # ---------------- PROFILE ------------------------------------------------------------------------
    profile_map_f1 = [
        ("Name", pilot_info.get("name") or pilot_info.get("id")),
        ("Number", pilot_info.get("number") or pilot_info.get("no") or pilot_info.get("race_number")),
        ("Nationality", pilot_info.get("nationality")),
        ("Birthday", pilot_info.get("birth_date")),
        ("Real Team", pilot_info.get("real_team") or pilot_info.get("team") or pilot_info.get("realTeam")),
        ("Power Unit", pilot_info.get("PU") or pilot_info.get("pu") or pilot_info.get("power_unit")),
    ]
    profile_map_mgp = [
        ("Name", pilot_info.get("name") or pilot_info.get("id")),
        ("Number", pilot_info.get("number") or pilot_info.get("no") or pilot_info.get("race_number")),
        ("Nationality", pilot_info.get("nationality")),
        ("Birthday", pilot_info.get("birth_date")),
        ("Real Team", pilot_info.get("real_team") or pilot_info.get("team") or pilot_info.get("realTeam")),
        ("Bike", pilot_info.get("bike") or pilot_info.get("machine") or pilot_info.get("chassis")),
    ]
    profile_map = profile_map_f1 if (category or "").upper().startswith("F1") else profile_map_mgp
    profile_rows = [(label, _parse_display_value(value)) for label, value in profile_map]

    # ---------------- AVERAGE / MARKS -------------------------------------------------------------
    SUFF_THRESHOLD = 6.0

    try:
        marks_f1_rows = supabase.from_("marks_f1_new").select("*").execute().data or []
    except Exception:
        marks_f1_rows = []

    try:
        marks_mgp_rows = supabase.from_("marks_mgp_new").select("*").execute().data or []
    except Exception:
        marks_mgp_rows = []

    def normalize_key(s):
        return normalize_fullname_for_keys(str(s or "")).lower().strip()

    def index_marks_rows(rows):
        idx = {}
        for mr in rows:
            candidates = []
            for k in ("ID", "id", "Name", "name", "pilot", "pilota", "nome"):
                v = mr.get(k)
                if v is not None:
                    candidates.append(str(v))
            for v in mr.values():
                if isinstance(v, str) and v.strip():
                    candidates.append(v.strip())
            for c in candidates:
                nk = normalize_key(c)
                if nk:
                    idx[nk] = mr
        return idx

    marks_idx_f1 = index_marks_rows(marks_f1_rows)
    marks_idx_mgp = index_marks_rows(marks_mgp_rows)

    INVALID_TOKENS = {"", "none", "na", "n/a", "-", "dnf", "did not finish", "—", "nan", "null"}
    is_f1 = (category or "").upper().startswith("F1")
    marks_index_primary = marks_idx_f1 if is_f1 else marks_idx_mgp
    marks_index_other = marks_idx_mgp if is_f1 else marks_idx_f1 

    pilot_name_to_search = str(pilot_info.get("name") or pilot_info.get("ID") or pilot).strip()
    pilot_key = normalize_key(pilot_name_to_search)
    marks_row = marks_index_primary.get(pilot_key)
    fallback_used = False
    if marks_row is None:
        for k in marks_index_primary.keys():
            if pilot_key and pilot_key in k:
                marks_row = marks_index_primary.get(k)
                break
        if marks_row is None:
            for k in marks_index_other.keys():
                if pilot_key and pilot_key in k:
                    marks_row = marks_index_other.get(k)
                    fallback_used = True
                    break

    avg_value, votes_count, suff_count, suff_percent = None, 0, 0, None
    avg_hex = "#666666"
    if marks_row:
        stats = compute_stats_from_marks_record(marks_row, SUFF_THRESHOLD)
        if stats:
            avg_value = stats["avg"]
            votes_count = stats["count"]
            suff_count = stats["suff_count"]
            suff_percent = stats["pct"]

    avg_hex = avg_to_hex(avg_value)

    if fallback_used:
        st.info("Voti trovati nella tabella opposta (fallback). Verifica se il pilota è classificato nella categoria corretta.")

    # ---------------- RENDERING -----------------------------------------------------------------------------------------------
    st.header(f"Details — {pilot}")
    st.markdown("### Driver profile")
    c_profile, c_avg = st.columns([0.65, 0.35])

    html_profile = _render_simple_table_html(profile_rows, spacing_px=2, row_padding='4px 10px')
    profile_height, profile_scroll = _estimate_rows_height(profile_rows,
                                                          container_width_px=1000,
                                                          left_pct=0.65,
                                                          right_pct=0.35,
                                                          avg_char_px=7.0,
                                                          line_height_px=18,
                                                          vertical_padding_px=8,
                                                          min_h=80,
                                                          max_h=8000,
                                                          safety_mul=1.05,
                                                          per_row_padding_px=0)
    with c_profile:
        BUFFER_PX = 40
        components.html(html_profile, height=profile_height + BUFFER_PX, scrolling=True)

    if avg_value is None:
        avg_display = "N/A"
        votes_text = "No votes" if (category or "").upper().startswith("F1") else "N/A"
    else:
        avg_display = f"{avg_value:.1f}"
        votes_text = f"based on {votes_count} race{'s' if votes_count != 1 else ''}"

    avg_box_html = f"""
    <div style="
        display:flex;
        align-items:center;
        justify-content:center;
        flex-direction:column;
        padding:14px;
        border-radius:10px;
        min-height:100px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.4);
        background: linear-gradient(90deg, {avg_hex}, #222 120%);
        color: #fff;
    ">
        <div style="font-size:13px;font-weight:700;opacity:0.95;margin-bottom:4px">Average</div>
        <div style="font-size:28px;font-weight:800;letter-spacing:0.4px;line-height:1">{_html.escape(str(avg_display))}</div>
        <div style="font-size:11px;margin-top:6px;opacity:0.85">{_html.escape(votes_text)}</div>
    </div>
    """
    with c_avg:
        st.markdown(avg_box_html, unsafe_allow_html=True)

    if suff_percent is None:
        donut_color = "#888888"
    elif suff_percent < 50.0:
        donut_color = "#ff2b2b"
    elif suff_percent >= 85.0:
        donut_color = "#00b300"
    else:
        donut_color = "#ff9900"

    fig, ax = plt.subplots(figsize=(1.2, 1.2), dpi=100)
    fig.patch.set_alpha(0.0)
    ax.axis("equal")
    if suff_percent is None:
        sizes = [1.0, 0.0]
        colors = ["#444444", "#222222"]
        center_text_top = "N/A"
        center_text_bottom = ""
    else:
        p = max(0.0, min(100.0, suff_percent))
        sizes = [p, 100.0 - p]
        colors = [donut_color, "#2b2b2b"]
        center_text_top = f"{int(round(p))}%"
        center_text_bottom = f"{suff_count}/{votes_count}"

    wedges, _ = ax.pie(sizes, colors=colors, startangle=90, wedgeprops=dict(width=0.32, edgecolor="none"))
    ax.text(0, 0.45, "Sufficient", ha='center', va='center', fontsize=4, color='white', fontweight='600', fontfamily="Inter")
    ax.text(0, 0.1, center_text_top, ha='center', va='center', fontsize=7, color='white', fontweight='700', fontfamily="Inter")
    ax.text(0, -0.25, center_text_bottom, ha='center', va='center', fontsize=4, color='white', fontweight='600', fontfamily="Inter")
    plt.tight_layout()
    c_avg.pyplot(fig)
    plt.close(fig)

    st.markdown("### Season stats")
    stat_keys_f1 = [
        ("Convocations", "convocations"),
        ("Wins", "wins"),
        ("Sprint wins", "sprint_wins"),
        ("Sprint pole positions", "sprint_poles"),
        ("Poles", "poles"),
        ("Podiums", "podiums"),
        ("DNF", "DNF"),
        ("Substitutions", "sub"),
    ]
    stat_keys_mgp = [
        ("Convocations", "convocations"),
        ("Wins", "wins"),
        ("Sprint wins", "sprint_wins"),
        ("Pole Positions", "poles"),
        ("Podiums", "podiums"),
        ("DNF", "DNF"),
        ("Substitutions", "sub"),
    ]
    stat_keys = stat_keys_f1 if (category or "").upper().startswith("F1") else stat_keys_mgp

    review_rows = []
    for label, key in stat_keys:
        raw = this_pilot_data.get(key)
        display = _parse_display_value(raw)
        count_hint = ""
        try:
            parsed_for_count = (
                raw if isinstance(raw, (list, tuple))
                else (ast.literal_eval(raw) if isinstance(raw, str) and raw.strip().startswith("[") else None)
            )
            if isinstance(parsed_for_count, (list, tuple)):
                count_hint = f"  (x{len(parsed_for_count)})"
        except Exception:
            count_hint = ""
        review_rows.append((label, display + count_hint))

    html_review = _render_simple_table_html(review_rows, spacing_px=2, row_padding='4px 10px')
    review_height, review_scroll = _estimate_rows_height(review_rows,
                                                         container_width_px=1000,
                                                         left_pct=0.65,
                                                         right_pct=0.35,
                                                         avg_char_px=7.0,
                                                         line_height_px=18,
                                                         vertical_padding_px=8,
                                                         min_h=80,
                                                         max_h=8000,
                                                         safety_mul=1.05,
                                                         per_row_padding_px=0)
    components.html(html_review, height=review_height + BUFFER_PX, scrolling=True)

    hist_rows = []
    hist_fields = [
        ("Historical wins", "historical_wins"),
        ("Historical poles", "historical_poles"),
        ("Historical Sprint Wins", "historical_sprint_wins")
    ]
    if (category or "").upper().startswith("F1"):
        hist_fields.append(("Historical Sprint poles", "historical_sprint_poles"))

    for label, field in hist_fields:
        raw = this_pilot_data.get(field)
        display = _parse_display_value(raw)
        count = _count_items_like_list(raw)
        count_hint = f"  (x{count})" if count and count > 0 else ""
        hist_rows.append((label, display + count_hint))

    st.markdown("### Historical")
    html_hist = _render_simple_table_html(hist_rows, spacing_px=2, row_padding='4px 10px')
    hist_height, hist_scroll = _estimate_rows_height(hist_rows,
                                                     container_width_px=1000,
                                                     left_pct=0.65,
                                                     right_pct=0.35,
                                                     avg_char_px=7.0,
                                                     line_height_px=18,
                                                     vertical_padding_px=8,
                                                     min_h=80,
                                                     max_h=8000,
                                                     safety_mul=1.05,
                                                     per_row_padding_px=0)
    components.html(html_hist, height=hist_height + BUFFER_PX, scrolling=True)

    st.markdown("<div style='margin-top:-10px;'></div>", unsafe_allow_html=True)
    if st.button("Go back", key="go_back_racer"):
        for k in ("selected_pilot", "selected_driver", "selected_category"):
            st.session_state.pop(k, None)
        st.session_state.screen = (
            st.session_state.screen_history.pop()
            if st.session_state.get("screen_history")
            else "racers"
        )
        st.rerun()
