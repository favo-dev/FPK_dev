import ast
import html as _html
import re
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
import matplotlib.pyplot as plt
from logic.utilities import (
    _estimate_rows_height,
    _parse_display_value,
    _count_items_like_list,
    _render_simple_table_html,
    parse_list_field,
    normalize_fullname_for_keys,
)

# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


# --------------------- SCREENS ----------------------------------------------
def show_racer_screen():
    # Accept either the canonical selected_pilot or the legacy selected_driver
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

    # Carico dati (una sola volta)
    try:
        data_f1 = supabase.from_("racers_f1").select("*").execute().data or []
        data_mgp = supabase.from_("racers_mgp").select("*").execute().data or []
    except Exception:
        data_f1, data_mgp = [], []

    # Se non ho category esplicita, provo ad inferirla cercando il pilota nelle tabelle
    if not category:
        pid = str(pilot)
        found_in_f1 = any((str(p.get("ID")) == pid) or (str(p.get("name")) == pid) for p in data_f1)
        found_in_mgp = any((str(p.get("ID")) == pid) or (str(p.get("name")) == pid) for p in data_mgp)
        if found_in_f1 and not found_in_mgp:
            category = "F1"
        elif found_in_mgp and not found_in_f1:
            category = "MotoGP"
        elif found_in_f1 and found_in_mgp:
            # ambiguità: preferiamo F1 per compatibilità, ma puoi cambiare il fallback
            category = "F1"
        # se non trovato in nessuna, category resta "" e useremo la MGP fallback più sotto

    # scegli i dati in base alla category (come prima)
    data = data_f1 if (category or "").upper().startswith("F1") else data_mgp

    pilot_info = next(
        (p for p in data if (str(p.get("ID")) == str(pilot)) or (str(p.get("name")) == str(pilot))),
        None
    )
    if not pilot_info:
        st.error(f"Informazioni per il pilota '{pilot}' non trovate.")
        if st.button("Go back"):
    # puliamo i flag di selezione per evitare che restino attivi
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

    # ---------------- PROFILE ----------------
    profile_map_f1 = [
        ("Name", pilot_info.get("name") or pilot_info.get("ID")),
        ("Number", pilot_info.get("number") or pilot_info.get("no") or pilot_info.get("race_number")),
        ("Nationality", pilot_info.get("nationality")),
        ("Birthday", pilot_info.get("birth_date")),
        ("Real Team", pilot_info.get("real_team") or pilot_info.get("team") or pilot_info.get("realTeam")),
        ("Power Unit", pilot_info.get("PU") or pilot_info.get("pu") or pilot_info.get("power_unit")),
    ]
    profile_map_mgp = [
        ("Name", pilot_info.get("name") or pilot_info.get("ID")),
        ("Number", pilot_info.get("number") or pilot_info.get("no") or pilot_info.get("race_number")),
        ("Nationality", pilot_info.get("nationality")),
        ("Birthday", pilot_info.get("birth_date")),
        ("Real Team", pilot_info.get("real_team") or pilot_info.get("team") or pilot_info.get("realTeam")),
        ("Bike", pilot_info.get("bike") or pilot_info.get("machine") or pilot_info.get("chassis")),
    ]
    profile_map = profile_map_f1 if (category or "").upper().startswith("F1") else profile_map_mgp
    profile_rows = [(label, _parse_display_value(value)) for label, value in profile_map]

    # ---------------- AVERAGE / MARKS (UNIFICATO per F1 e MGP) ----------------
    # soglia sufficienza fissa
    SUFF_THRESHOLD = 6.0

    # carico entrambe le tabelle indipendentemente (evita il fallback errato)
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
            # campi comunemente usati
            for k in ("ID", "id", "Name", "name", "pilot", "pilota", "nome"):
                v = mr.get(k)
                if v is not None:
                    candidates.append(str(v))
            # anche qualsiasi stringa dentro il record può contenere il nome (es. 'driver', 'full_name', ecc.)
            for v in mr.values():
                if isinstance(v, str) and v.strip():
                    candidates.append(v.strip())
            # indicizzo
            for c in candidates:
                nk = normalize_key(c)
                if nk:
                    # preferisco ultimo valore (sovrascrive), ma puoi cambiare logica se vuoi il primo match
                    idx[nk] = mr
        return idx

    marks_idx_f1 = index_marks_rows(marks_f1_rows)
    marks_idx_mgp = index_marks_rows(marks_mgp_rows)

    INVALID_TOKENS = {"", "none", "na", "n/a", "-", "dnf", "did not finish", "—", "nan", "null"}

    def extract_votes_from_record(mr):
        """Estrae una lista di numeri (float) dai campi del record marks."""
        if not mr:
            return []
        nums = []

        # primo tentativo: campi list-like espliciti (parse_list_field supporta stringhe tipo "[6,5.5]" o array)
        list_field_candidates = ("votes", "voti", "marks", "scores", "voti_gara", "gara_voti", "results")
        for cand in list_field_candidates:
            if cand in mr and mr[cand] is not None:
                try:
                    lst = parse_list_field(mr[cand])
                except Exception:
                    # fallback ad ast.literal_eval se parse_list_field non funziona
                    try:
                        lst = ast.literal_eval(mr[cand]) if isinstance(mr[cand], str) else list(mr[cand])
                    except Exception:
                        lst = []
                for x in lst:
                    try:
                        nums.append(float(str(x).replace(",", ".")))
                    except Exception:
                        pass
                if nums:
                    return nums

        # altrimenti scorro tutti i campi e provo a estrarre numeri
        for k, v in mr.items():
            if not k or str(k).lower() in ("id", "name", "nome", "driver", "pilot", "pilota"):
                continue
            if v is None:
                continue
            # numerico diretto
            if isinstance(v, (int, float)):
                nums.append(float(v))
                continue
            s = str(v).strip()
            if not s or s.lower() in INVALID_TOKENS:
                continue

            # se sembra una lista testuale
            if s.startswith("[") and s.endswith("]"):
                try:
                    lst = parse_list_field(s)
                except Exception:
                    try:
                        lst = ast.literal_eval(s)
                    except Exception:
                        lst = []
                for x in lst:
                    try:
                        nums.append(float(str(x).replace(",", ".")))
                    except Exception:
                        pass
                continue

            # estraggo tutti i token numerici presenti (es. "6, 5.5" oppure "6/10")
            found = re.findall(r"-?\d+(?:[.,]\d+)?", s)
            if found:
                for tok in found:
                    try:
                        nums.append(float(tok.replace(",", ".")))
                    except:
                        pass
                continue

            # fallback: pulisco e provo a convertire
            cleaned = re.sub(r"[^\d\.\-\,]+", "", s).replace(",", ".")
            try:
                if cleaned not in ("", ".", "-", "-."):
                    nums.append(float(cleaned))
            except:
                pass

        return nums

    def compute_stats_from_marks_record(mr, threshold):
        votes = extract_votes_from_record(mr)
        if not votes:
            return None
        # rimuovo eventuali NaN/inf errati
        nums = [float(x) for x in votes if str(x).strip() != ""]
        if not nums:
            return None
        avg = sum(nums) / len(nums)
        suff_cnt = sum(1 for x in nums if x >= threshold)
        pct = 100.0 * suff_cnt / len(nums)
        return {"avg": avg, "count": len(nums), "suff_count": suff_cnt, "pct": pct}

    # seleziona l'indice corretto in base alla categoria
    is_f1 = (category or "").upper().startswith("F1")
    marks_index_primary = marks_idx_f1 if is_f1 else marks_idx_mgp
    marks_index_other = marks_idx_mgp if is_f1 else marks_idx_f1  # per fallback, se vuoi usarlo

    pilot_name_to_search = str(pilot_info.get("name") or pilot_info.get("ID") or pilot).strip()
    pilot_key = normalize_key(pilot_name_to_search)

    # ricerca record marks nella tabella corretta; se non trovato prova l'altra come fallback (opzionale)
    marks_row = marks_index_primary.get(pilot_key)
    fallback_used = False
    if marks_row is None:
        # tentiamo qualche variante (es. cognome, nome + cognome, id numerico, ecc.)
        # cerco corrispondenze contenute (partial match) nella primary index
        for k in marks_index_primary.keys():
            if pilot_key and pilot_key in k:
                marks_row = marks_index_primary.get(k)
                break
        # fallback nell'altra tabella
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

    # colore a gradiente tra bordeaux (media=4.5) e verde forte (media=8.0)
    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(rgb):
        return "#{:02x}{:02x}{:02x}".format(*[max(0, min(255, int(round(c)))) for c in rgb])

    def avg_to_hex(avg):
        if avg is None:
            return "#666666"
        # definisci i punti di controllo
        min_avg = 4.5
        max_avg = 8.0
        # colori: bordeaux -> verde forte
        col_low = "#6a0d1a"    # bordeaux (per avg = 4.5)
        col_high = "#00b300"   # verde forte (per avg = 8.0)
        r1, g1, b1 = hex_to_rgb(col_low)
        r2, g2, b2 = hex_to_rgb(col_high)
        # normalizza t in [0,1] rispetto a [min_avg, max_avg]
        t = (float(avg) - min_avg) / (max_avg - min_avg)
        t = max(0.0, min(1.0, t))
        r = r1 + (r2 - r1) * t
        g = g1 + (g2 - g1) * t
        b = b1 + (b2 - b1) * t
        return rgb_to_hex((r, g, b))

    avg_hex = avg_to_hex(avg_value)

    # opzionale: mostra un piccolo avviso se abbiamo usato il fallback sull'altra tabella
    if fallback_used:
        st.info("Voti trovati nella tabella opposta (fallback). Verifica se il pilota è classificato nella categoria corretta.")
    # ---------------- fine blocco AVERAGE / MARKS ----------------

    # ---------------- RENDERING ----------------
    st.header(f"Details — {pilot}")
    st.markdown("### Driver profile")
    c_profile, c_avg = st.columns([0.65, 0.35])

    # profile: stima altezza in modo conservativo per evitare scrollbar
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

    # Average box
    if avg_value is None:
        avg_display = "N/A"
        votes_text = "No votes" if (category or "").upper().startswith("F1") else "N/A (not F1)"
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

    # Donut chart (come prima)
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

    # ----- Season stats -----
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
        raw = pilot_info.get(key)
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

    # ----- Historical -----
    hist_rows = []
    hist_fields = [
        ("Historical wins", "historical_wins"),
        ("Historical poles", "historical_poles"),
        ("Historical Sprint Wins", "historical_sprint_wins")
    ]
    if (category or "").upper().startswith("F1"):
        hist_fields.append(("Historical Sprint poles", "historical_sprint_poles"))

    for label, field in hist_fields:
        raw = pilot_info.get(field)
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

    # back
    st.markdown("<div style='margin-top:-10px;'></div>", unsafe_allow_html=True)
    if st.button("Go back to previous", key="go_back_racer"):
        for k in ("selected_pilot", "selected_driver", "selected_category"):
            st.session_state.pop(k, None)
        st.session_state.screen = (
            st.session_state.screen_history.pop()
            if st.session_state.get("screen_history")
            else "racers"
        )
        st.rerun()
