import ast
import html as _html
import json
import re
import unicodedata
import io
import pickle
import numpy as np
import pandas as pd
import streamlit as st
from typing import Any, List, Dict
from supabase import create_client



# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

#TABLE_SPACING_PX = 0.5
#DEFAULT_ROW_PADDING = '4px 10px'

# -------------------------
# Correzioni manuali globali
# -------------------------
MANUAL_CORRECTIONS = {
    "ferman aldeguer": "fermin aldeguer",
    "maverick viaales": "maverick vinales",
    "jorge martan": "jorge martin",
    "raaol fernandez": "raul fernandez",
}

# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def get_supabase_client():
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(supabase_url, supabase_key)

# -------------------------------------------------------------------------------------------

def make_safe_key(*args):
    key = "_".join(str(a) for a in args)
    key = re.sub(r"[^a-zA-Z0-9_]", "_", key)
    return key

# -------------------------------------------------------------------------------------------

def go_to_screen(new_screen):
    st.session_state.setdefault("screen_history", [])
    if "screen" in st.session_state:
        st.session_state.screen_history.append(st.session_state.screen)
    st.session_state.screen = new_screen
    st.rerun()

# -------------------------------------------------------------------------------------------

def _parse_display_value(raw):
    if raw is None:
        return "N/A"
    if isinstance(raw, (list, tuple)):
        return ", ".join(str(x) for x in raw) if raw else "0"
    if isinstance(raw, dict):
        try:
            return json.dumps(raw, ensure_ascii=False)
        except Exception:
            return str(raw)
    if isinstance(raw, str):
        s = raw.strip()
        try:
            parsed = json.loads(s)
            return _parse_display_value(parsed)
        except Exception:
            pass
        try:
            parsed = ast.literal_eval(s)
            return _parse_display_value(parsed)
        except Exception:
            pass
        return s or "N/A"
    return str(raw)

# -------------------------------------------------------------------------------------------

def _count_items_like_list(raw):
    if raw is None:
        return 0
    if isinstance(raw, (list, tuple)):
        return len(raw)
    if isinstance(raw, str):
        s = raw.strip()
        try:
            parsed = ast.literal_eval(s)
            if isinstance(parsed, (list, tuple)):
                return len(parsed)
        except Exception:
            pass
        if "," in s:
            parts = [p.strip() for p in s.split(",") if p.strip()]
            return len(parts)
    return 0

# -------------------------------------------------------------------------------------------

def _estimate_rows_height(rows,
                          container_width_px=1000,
                          left_pct=0.65,
                          right_pct=0.35,
                          avg_char_px=7.0,
                          line_height_px=18,
                          vertical_padding_px=6,   
                          min_h=24,                
                          max_h=8000,
                          safety_mul=1.0,          
                          per_row_padding_px=0):
    left_w = int(container_width_px * left_pct) - 32
    right_w = int(container_width_px * right_pct) - 32
    left_chars_per_line = max(20, int(left_w / max(1.0, avg_char_px)))
    right_chars_per_line = max(10, int(right_w / max(1.0, avg_char_px)))

# -------------------------------------------------------------------------------------------

    def _count_wrapped_lines(text, chars_per_line):
        if not text:
            return 1
        s = re.sub(r"\s+", " ", str(text).strip())
        if not s:
            return 1
        tokens = s.split(' ')
        lines = 0
        cur = 0
        for token in tokens:
            token_len = len(token) + 1
            if cur + token_len > chars_per_line:
                lines += 1
                cur = token_len
            else:
                cur += token_len
        if cur > 0:
            lines += 1
        return max(1, lines)

    total_px = 0
    for label, value in rows:
        lab_lines = _count_wrapped_lines(label, left_chars_per_line)
        val_lines = _count_wrapped_lines(value, right_chars_per_line)
        row_lines = max(lab_lines, val_lines)
        total_px += row_lines * line_height_px + per_row_padding_px

    est = int(vertical_padding_px + total_px)
    est = int(est * safety_mul)
    if est < min_h:
        est = min_h
    needs_scroll = False
    if est > max_h:
        needs_scroll = True
        est = max_h
    return est, needs_scroll

# -------------------------------------------------------------------------------------------

def safe_load_team_list(raw):
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            return ast.literal_eval(raw)
        except Exception:
            return [raw]
    return []

# -------------------------------------------------------------------------------------------

def normalize(name):
    if not isinstance(name, str):
        return ""
    s = unicodedata.normalize("NFKD", name)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]", "", s)
    return s

# -------------------------------------------------------------------------------------------
    
def normalize_category(cat):
    if not isinstance(cat, str):
        return ""
    s = cat.strip().lower()
    if s in ("f1", "formula1", "formula 1"):
        return "f1"
    if s in ("motogp", "mgp", "moto", "moto gp", "motorbike", "moto-gp"):
        return "motogp"
    if "f1" in s:
        return "f1"
    if "mgp" in s or "motogp" in s or "moto" in s:
        return "motogp"
    return s

# -------------------------------------------------------------------------------------------

def normalize_fullname_for_keys(name):
        if not isinstance(name, str):
            return ""
        s = unicodedata.normalize("NFC", name).strip()
        if "," in s:
            parts = [p.strip() for p in s.split(",") if p.strip()]
            if len(parts) >= 2:
                s = parts[1] + " " + parts[0]
            else:
                s = parts[0]
        s = re.sub(r"\s+", " ", s)
        return unicodedata.normalize("NFC", s)

# -------------------------------------------------------------------------------------------
    
def parse_list_field(v):
        if v is None:
            return []
        if isinstance(v, (list, tuple)):
            return [str(x).strip() for x in v]
        if isinstance(v, str):
            s = v.strip()
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, (list, tuple)):
                    return [str(x).strip() for x in parsed]
                if isinstance(parsed, str):
                    return [parsed.strip()]
            except Exception:
                pass
            try:
                parsed = json.loads(s)
                if isinstance(parsed, (list, tuple)):
                    return [str(x).strip() for x in parsed]
                if isinstance(parsed, str):
                    return [parsed.strip()]
            except Exception:
                pass
            if "," in s:
                return [item.strip().strip("'\"") for item in s.split(",") if item.strip()]
            return [s.strip().strip("'\"")]
        return []

# -------------------------------------------------------------------------------------------

def fix_mojibake(s):
    try:
        if not isinstance(s, str):
            return s
        s_nfc = unicodedata.normalize("NFC", s)
        if "Ã" in s_nfc or "Â" in s_nfc:
            try:
                repaired = s_nfc.encode("latin-1").decode("utf-8")
                return unicodedata.normalize("NFC", repaired)
            except Exception:
                return s_nfc
        return s_nfc
    except Exception:
        return s

# -------------------------------------------------------------------------------------------

def build_pilot_colors(teams):
    pilot_colors = {}
    combined_pilots = []

    cat_variants = {
        "F1": ["F1", "f1", "formula1", "drivers_f1", "drivers"],
        "MotoGP": ["MotoGP", "motogp", "MGP", "mgp", "moto", "moto gp"]
    }

# -------------------------------------------------------------------------------------------

    def parse_color(raw):
        """Gestisce stringa, lista, tuple o jsonb di colore."""
        if raw is None:
            return "#888888"
        if isinstance(raw, str):
            try:
                
                val = ast.literal_eval(raw)
                return safe_rgb_to_hex(val)
            except Exception:
                return safe_rgb_to_hex(raw)
        return safe_rgb_to_hex(raw)

    for team in teams:
        main_raw = (
            team.get("main color") or team.get("main_color") or
            team.get("mainColor") or team.get("main")
        )
        second_raw = (
            team.get("second color") or team.get("second_color") or
            team.get("secondColor") or team.get("second")
        )

        main_hex = parse_color(main_raw)
        second_hex = parse_color(second_raw)

        for cat_label, variants in cat_variants.items():
            raw_pilots = None
            for v in variants:
                if v in team and team[v]:
                    raw_pilots = team[v]
                    break
                for k in team.keys():
                    if k.lower() == v.lower() and team.get(k):
                        raw_pilots = team[k]
                        break
                if raw_pilots:
                    break

            if not raw_pilots:
                continue

            try:
                if isinstance(raw_pilots, str):
                    raw_pilots_eval = ast.literal_eval(raw_pilots)
                else:
                    raw_pilots_eval = raw_pilots
                if isinstance(raw_pilots_eval, (str, int)):
                    raw_pilots_eval = [raw_pilots_eval]
                if not isinstance(raw_pilots_eval, (list, tuple)):
                    raw_pilots_eval = [raw_pilots_eval]
            except Exception:
                raw_pilots_eval = [raw_pilots] if raw_pilots else []

            for p in raw_pilots_eval:
                if isinstance(p, dict):
                    p_str = p.get("name") or p.get("fullname") or str(p)
                else:
                    p_str = str(p)
                combined_pilots.append((p_str, cat_label, main_hex, second_hex))

   
    for pilot, cat_label, main_hex, second_hex in combined_pilots:
        cat_norm = normalize_category(cat_label)
        parsed_name = normalize_fullname_for_keys(pilot) 
        parts = parsed_name.split()
        surname = parts[-1] if parts else parsed_name

        if cat_norm == "motogp":
            key_full = normalize(parsed_name) 
            key_surname = normalize(surname) 
            display = surname
            pilot_colors[(cat_norm, key_full)] = (main_hex, second_hex, display)
            pilot_colors[(cat_norm, key_surname)] = (main_hex, second_hex, display)
        else:
            key = normalize(surname)
            display = surname
            pilot_colors[(cat_norm, key)] = (main_hex, second_hex, display)

    return pilot_colors

# -------------------------------------------------------------------------------------------

def color_box_html(main, second):
    return (
        f'<span style="display:inline-block;width:16px;height:16px;'
        f'background-color:{main};border:2px solid {second};margin-right:8px;'
        f'vertical-align:middle;border-radius:3px;"></span>'
    )

# -------------------------------------------------------------------------------------------

def format_name(fullname, pilot_colors, category):
    try:
        if fullname is None or (isinstance(fullname, float) and np.isnan(fullname)):
            return ""
        cat_norm = normalize_category(category or "")
        parsed_name = normalize_fullname_for_keys(str(fullname))
        parts = parsed_name.split()
        surname = parts[-1] if parts else parsed_name

        if cat_norm == "motogp":
            key = normalize(parsed_name) 
        else:
            key = normalize(surname)

        main, second, display = pilot_colors.get((cat_norm, key), (None, None, None))
        if (display is None or display == "") and cat_norm == "motogp":
            fallback = pilot_colors.get((cat_norm, normalize(surname)))
            if fallback:
                main, second, display = fallback

        if display is None:
            display = surname
            main, second = "#888888", "#444444"


        display = fix_mojibake(display)
        return f"{color_box_html(main, second)}{display}"
    except Exception as e:
        print("Errore in format_name:", e, fullname, category)
        return str(fullname)

# -------------------------------------------------------------------------------------------

def get_color(fullname, pilot_colors, category):
    try:
        cat_norm = normalize_category(category or "")
        parsed_name = normalize_fullname_for_keys(str(fullname))
        parts = parsed_name.split()
        surname = parts[-1] if parts else parsed_name

        if cat_norm == "motogp":
            keys_to_try = [normalize(parsed_name), normalize(surname)]
        else:
            keys_to_try = [normalize(surname)]

        for k in keys_to_try:
            v = pilot_colors.get((cat_norm, k))
            if v:
                raw_color = v[0]  
                rgb = parse_color_field(raw_color)
                if rgb:
                    return safe_rgb_to_hex(rgb)

        return "#888888"
    except Exception as e:
        print(f"[get_color] Errore per {fullname}: {e}")
        return "#888888"

# -------------------------------------------------------------------------------------------

def get_results(race, category, sprint):
    file_path = f"{race}/sprint_standings.pkl" if sprint else f"{race}/standings.pkl"
    bucket_name = category
    supabase = get_supabase_client()
    try:
        data_bytes = supabase.storage.from_(bucket_name).download(file_path)
        return pickle.load(io.BytesIO(data_bytes))
    except Exception as e:
        print(f"Errore nel download di {file_path} dal bucket {bucket_name}: {e}")
        return None

# -------------------------------------------------------------------------------------------
        
def sprint_pole(race, category):
    file_path = f"{race}/sprint_poleposition.pkl"
    bucket_name = category
    supabase = get_supabase_client()
    try:
        data_bytes = supabase.storage.from_(bucket_name).download(file_path)
        return pickle.load(io.BytesIO(data_bytes))
    except Exception as e:
        print(f"Errore nel download di {file_path} dal bucket {bucket_name}: {e}")
        return None

# -------------------------------------------------------------------------------------------

def results_exist(race, tag):
    try:
        data = get_results(tag, race["category"], False)
        if not data:
            return False
        for row in data:
            if any(x != -99 and x is not None for x in row):
                return True
        return False
    except Exception as e:
        print(f"Errore in results_exist: {e}")
        return False

# -------------------------------------------------------------------------------------------

def normalize_riders(raw):
    if isinstance(raw, str):
        s = raw.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                parsed = ast.literal_eval(s)
                if isinstance(parsed, list):
                    return [p.strip(" '\"") for p in parsed if isinstance(p, str)]
            except Exception:
                pass
        if "," in s:
            return [p.strip(" '\"") for p in s.split(",") if p.strip()]
        return [s.strip(" '\"")] if s else []

    if isinstance(raw, list):
        if not raw:
            return []
        if isinstance(raw[0], list):
            return [p.strip(" '\"") for p in raw[0] if isinstance(p, str)]
        if len(raw) == 1 and isinstance(raw[0], str):
            return normalize_riders(raw[0])
        return [p.strip(" '\"") for p in raw if isinstance(p, str)]

    return []

# -------------------------------------------------------------------------------------------

def parse_color_field(value):
    if value is None:
        return None

    if isinstance(value, (list, tuple)):
        if len(value) >= 3:
            try:
                r = value[0]; g = value[1]; b = value[2]
                if any(isinstance(x, float) and 0.0 <= x <= 1.0 for x in (r,g,b)):
                    r, g, b = [int(round(float(x) * 255)) for x in (r,g,b)]
                else:
                    r, g, b = [int(round(float(x))) for x in (r,g,b)]
                return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
            except Exception:
                return None

    if isinstance(value, dict):
        for keys in (("r","g","b"), ("R","G","B"), ("0","1","2")):
            try:
                r = value.get(keys[0])
                g = value.get(keys[1])
                b = value.get(keys[2])
                if r is not None and g is not None and b is not None:
                    if any(isinstance(x, float) and 0.0 <= x <= 1.0 for x in (r,g,b)):
                        r, g, b = [int(round(float(x) * 255)) for x in (r,g,b)]
                    else:
                        r, g, b = [int(round(float(x))) for x in (r,g,b)]
                    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
            except Exception:
                continue
        try:
            vals = list(value.values())
            if len(vals) >= 3:
                r,g,b = vals[0], vals[1], vals[2]
                if any(isinstance(x, float) and 0.0 <= x <= 1.0 for x in (r,g,b)):
                    r, g, b = [int(round(float(x) * 255)) for x in (r,g,b)]
                else:
                    r, g, b = [int(round(float(x))) for x in (r,g,b)]
                return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
        except Exception:
            return None

    if isinstance(value, str):
        s = value.strip()
        if re.match(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$", s):
            if len(s) == 4:
                s = "#" + "".join(ch*2 for ch in s[1:])
            try:
                r = int(s[1:3], 16); g = int(s[3:5], 16); b = int(s[5:7], 16)
                return (r,g,b)
            except Exception:
                return None
        m = re.match(r"rgb\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*\)", s, flags=re.I)
        if m:
            r,g,b = m.group(1), m.group(2), m.group(3)
            try:
                r,g,b = float(r), float(g), float(b)
                if max(r,g,b) <= 1.0:
                    r,g,b = [int(round(x*255)) for x in (r,g,b)]
                else:
                    r,g,b = [int(round(x)) for x in (r,g,b)]
                return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
            except Exception:
                pass
        try:
            parsed = json.loads(s)
            return parse_color_field(parsed)
        except Exception:
            try:
                parsed = ast.literal_eval(s)
                return parse_color_field(parsed)
            except Exception:
                pass
        nums = re.findall(r"[0-9]+(?:\.[0-9]+)?", s)
        if len(nums) >= 3:
            try:
                r,g,b = float(nums[0]), float(nums[1]), float(nums[2])
                if max(r,g,b) <= 1.0:
                    r,g,b = [int(round(x*255)) for x in (r,g,b)]
                else:
                    r,g,b = [int(round(x)) for x in (r,g,b)]
                return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
            except Exception:
                pass
    return None

# -------------------------------------------------------------------------------------------

def safe_unpickle(data_bytes):
    if data_bytes is None:
        return None
    try:
        if not isinstance(data_bytes, (bytes, bytearray)):
            return data_bytes
        return pickle.loads(data_bytes)
    except Exception:
        try:
            text = data_bytes.decode("utf-8")
            return text
        except Exception:
            return None

# -------------------------------------------------------------------------------------------

def normalize_name(name):
    if not name:
        return ""
    name = str(name).strip().lower()
    name = unicodedata.normalize('NFKD', name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = re.sub(r"[^a-z\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name

# -------------------------------------------------------------------------------------------

def clean_team_drivers(raw_drivers):
    if raw_drivers is None:
        return []
    
    if isinstance(raw_drivers, list):
        return [normalize_name(str(d).strip()) for d in raw_drivers if d]
    if not isinstance(raw_drivers, str):
        return []
    cleaned = raw_drivers.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    names = re.findall(r"'([^']+)'|\"([^\"]+)\"", cleaned)
    drivers = [normalize_name(t[0] if t[0] else t[1]) for t in names]
    if not drivers and cleaned:
        drivers = [normalize_name(d.strip().strip("'\"")) for d in cleaned.split(",") if d.strip()]
    return drivers

# -------------------------------------------------------------------------------------------

def extract_driver_and_points(elem: Any, f1_mode=True):
    if isinstance(elem, (list, tuple)) and len(elem) >= 6:
        raw_name = str(elem[0])
        name = raw_name.split()[-1] if f1_mode else raw_name
        name = normalize_name(name)
        try:
            pts = int(elem[5])
        except Exception:
            try:
                pts = float(elem[5])
            except Exception:
                pts = 0
        return name, pts
    if isinstance(elem, dict):
        raw_name = elem.get("name") or elem.get("driver") or elem.get("driver_name") or elem.get("pilot")
        if not raw_name:
            return None, 0
        name = raw_name.split()[-1] if f1_mode else raw_name
        name = normalize_name(name)
        pts = elem.get("points") or elem.get("pts") or elem.get("Points") or 0
        try:
            pts = int(pts)
        except Exception:
            try:
                pts = float(pts)
            except Exception:
                pts = 0
        return name, pts
    return None, 0

# -------------------------------------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def load_table(name: str):
    supabase = get_supabase_client()
    try:
        res = supabase.from_(name).select("*").execute()
        return res.data or []
    except Exception:
        return []

# -------------------------------------------------------------------------------------------

def list_all(bucket: str, path: str = "") -> List[dict]:
    all_items = []
    supabase = get_supabase_client()
    limit = 100
    offset = 0

    while True:
        try:
            batch = supabase.storage.from_(bucket).list(path, {"limit": limit, "offset": offset}) or []
        except Exception as e:
            st.warning(f"Errore nel listare {bucket}/{path} con offset {offset}: {e}")
            break

        if not batch:
            break

        all_items.extend(batch)
        if len(batch) < limit:  # ultimo blocco
            break
        offset += limit

    return all_items

# -------------------------------------------------------------------------------------------

def load_standings_from_buckets(buckets: List[str] = ["F1", "MGP"]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    standings_data: Dict[str, Dict[str, Dict[str, Any]]] = {}
    supabase = get_supabase_client()

    for bucket in buckets:
        standings_data[bucket] = {}

        race_folders = list_all(bucket, "")
        race_names = [r["name"].rstrip("/") for r in race_folders if r.get("name")]

        for race_name in race_names:
            race_dict = {}
            files = list_all(bucket, race_name)
            file_names = [f["name"] for f in files if "name" in f]
            file_names_lower = [fn.lower() for fn in file_names]

            main_file = next((fn for fn, fn_l in zip(file_names, file_names_lower)
                              if fn_l.endswith("standings.pkl") and "sprint" not in fn_l), None)
            sprint_file = next((fn for fn, fn_l in zip(file_names, file_names_lower)
                                if fn_l.endswith("sprint_standings.pkl")), None)

            if main_file:
                try:
                    b = supabase.storage.from_(bucket).download(f"{race_name}/{main_file}")
                    race_dict["standings"] = safe_unpickle(b)
                except Exception as e:
                    st.warning(f"Errore {bucket}/{race_name}/{main_file}: {e}")
                    race_dict["standings"] = None
            else:
                race_dict["standings"] = None

            if sprint_file:
                try:
                    b = supabase.storage.from_(bucket).download(f"{race_name}/{sprint_file}")
                    race_dict["sprint_standings"] = safe_unpickle(b)
                except Exception as e:
                    st.warning(f"Errore {bucket}/{race_name}/{sprint_file}: {e}")
                    race_dict["sprint_standings"] = None
            else:
                race_dict["sprint_standings"] = None

            standings_data[bucket][race_name] = race_dict

    return standings_data

# -------------------------------------------------------------------------------------------

def build_points_dict(category_data: Any, use_full_name: bool) -> Dict[str, float]:
    points: Dict[str, float] = {}
    if not category_data:
        return points
    for elem in category_data:
        name, pts = extract_driver_and_points(elem, f1_mode=not use_full_name)
        if not name:
            continue
        name_norm = normalize_name(name)
        name_norm = MANUAL_CORRECTIONS.get(name_norm, name_norm)
        points[name_norm] = points.get(name_norm, 0) + float(pts)
    return points

# -------------------------------------------------------------------------------------------

def build_normalized_team_set(team_drivers: Any, use_full_name: bool) -> set:
    team_drivers_clean = clean_team_drivers(team_drivers)
    if use_full_name:
        normalized = [normalize_name(d) for d in team_drivers_clean]
    else:
        normalized = [normalize_name(d.split()[-1]) for d in team_drivers_clean if isinstance(d, str) and d.strip()]
    normalized = [MANUAL_CORRECTIONS.get(n, n) for n in normalized]
    return set(normalized)

# -------------------------------------------------------------------------------------------

def update_user_field(user, field, label):
    if f"{field}_temp" not in st.session_state:
        st.session_state[f"{field}_temp"] = user.get(field, "")
    supabase = get_supabase_client()
    new_val = st.text_input(label, value=st.session_state[f"{field}_temp"], key=f"{field}_input")
    st.session_state[f"{field}_temp"] = new_val  # aggiorna subito session_state

    if st.button(f"Save {label}", key=f"save_{field}", use_container_width=True):
        if not new_val:
            st.error(f"Insert a valid {label.lower()}!")
            return
        try:
            upd_resp = supabase.table("class").update({field: new_val}).eq("ID", user["ID"]).execute()
        except Exception as e:
            st.error(f"Error: {e}")
            return

        resp_err, resp_status = getattr(upd_resp, "error", None), getattr(upd_resp, "status_code", None)
        if resp_err or (resp_status and resp_status >= 400):
            st.error(f"Error: {resp_err or getattr(upd_resp,'data',None)}")
            return

        # Aggiorna localmente l'oggetto user
        user[field] = new_val
        st.success(f"{label} updated!")

        # Rimuovi temporaneo per future modifiche
        del st.session_state[f"{field}_temp"]

# -------------------------------------------------------------------------------------------

def hex_to_rgb(hex_color: str) -> list[int]:
                        hex_color = (hex_color or "").lstrip("#")
                        if len(hex_color) != 6:
                            return [0, 0, 0]
                        return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
# -------------------------------------------------------------------------------------------

def render_results_table(df):
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;padding:5px 0;font-weight:600;border-bottom:1px solid #ccc;">
        <div style="width:90px;">Position</div>
        <div style="flex:1;">Pilot</div>
        <div style="width:150px;text-align:left;">Performance score</div>
        <div style="width:80px;text-align:right;">Points</div>
    </div>
    """, unsafe_allow_html=True)
    for _, row in df.iterrows():
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;padding:5px 4px;">
            <div style="width:90px;">{row['Position']}</div>
            <div style="flex:1;">{row['Name with Color']}</div>
            <div style="width:150px;">{row['Performance']}</div>
            <div style="width:80px;text-align:right;">{row['Points']}</div>
        </div>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------------------------

def safe_rgb_to_hex(color):
    try:
        if not color:
            return "#888888"

        # Se è una stringa
        if isinstance(color, str):
            s = color.strip()
            if s.startswith("#") and len(s) in (4, 7):
                return s
            # Cerca numeri nella stringa
            nums = re.findall(r"\d{1,3}", s)
            if len(nums) >= 3:
                r, g, b = int(nums[0]), int(nums[1]), int(nums[2])
                return "#{:02x}{:02x}{:02x}".format(r, g, b)

        # Se è lista o tupla di almeno 3 elementi
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            r, g, b = int(color[0]), int(color[1]), int(color[2])
            return "#{:02x}{:02x}{:02x}".format(r, g, b)

        # Se è un dizionario JSONB
        if isinstance(color, dict):
            keys = {k.lower(): k for k in color.keys()}
            if {"r","g","b"}.issubset(keys):
                r, g, b = int(color[keys["r"]]), int(color[keys["g"]]), int(color[keys["b"]])
                return "#{:02x}{:02x}{:02x}".format(r, g, b)

    except Exception as e:
        print(f"Errore in safe_rgb_to_hex: {e}")

    return "#888888"

# -------------------------------------------------------------------------------------------

def _render_simple_table_html(rows, spacing_px=None, row_padding=None):
    spacing = 0 if spacing_px is None else spacing_px   # 0 di default (nessun margin-bottom extra)
    padding = '2px 8px' if row_padding is None else row_padding  

    rows_html = ""
    for label, value in rows:
        label_esc = _html.escape(str(label))
        value_esc = _html.escape(str(value))
        rows_html += f"""
        <div style='display:flex; justify-content:space-between; align-items:flex-start;
                    padding:{padding}; border-top:1px solid rgba(255,255,255,0.06);'>
            <div style='font-size:13px; font-weight:600; color:#dcdcdc;
                        max-width:65%; white-space:pre-wrap; word-break:break-word;
                        overflow-wrap:anywhere; line-height:1.2;'>{label_esc}</div>
            <div style='font-size:14px; font-weight:700; color:#ffffff; text-align:right;
                        max-width:35%; white-space:pre-wrap; word-break:break-word;
                        overflow-wrap:anywhere; line-height:1.2;'>{value_esc}</div>
        </div>
        """

    table_html = f"""
    <div style='width:100%; background:#222; border-radius:8px;
                box-shadow:0 2px 6px rgba(0,0,0,0.12);
                overflow:hidden;
                height:auto;
                font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
                margin-bottom:{spacing}px;'>
        {rows_html}
    </div>
    """
    return table_html

# -------------------------------------------------------------------------------------------

def render_standings_custom(df, teams, title):
    st.markdown(f"<h2 style='color:#ffffff; background-color:#222222; font-size:28px; font-weight:bold; padding: 4px 8px; border-radius:4px;'>{title}</h2>", unsafe_allow_html=True)
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex; font-weight:700; border-bottom:2px solid #ccc; padding-bottom:6px; margin-bottom:8px;">
        <div style="width:30px;">Pos</div>
        <div style="width:30px;"></div>
        <div style="flex-grow:1;">Team</div>
        <div style="width:60px; text-align:right;">Points</div>
        <div style="width:80px; text-align:right;">Penalty</div>
        <div style="width:100px; text-align:right;">Gap (previous)</div>
        <div style="width:80px; text-align:right;">Gap (leader)</div>
    </div>
    """, unsafe_allow_html=True)
    for _, row in df.iterrows():
        team_name = row["Team"]
        team_info = next((t for t in teams if (t.get("name") == team_name) or (t.get("ID") == team_name) or (t.get("id") == team_name)), None)
        main_raw = None
        second_raw = None
        if team_info:
    # prova varie chiavi possibili (nel caso la colonna si chiami con nomi diversi)
            for key in ("main color", "main_color", "mainColor", "mainColorRGB"):
                if key in team_info:
                    main_raw = parse_color_field(team_info.get(key))
                    break
            for key in ("second color", "second_color", "secondColor", "accent color"):
                if key in team_info:
                    second_raw = parse_color_field(team_info.get(key))
                    break

        color_main = safe_rgb_to_hex(main_raw) if main_raw is not None else safe_rgb_to_hex([0,0,0])
        color_second = safe_rgb_to_hex(second_raw) if second_raw is not None else safe_rgb_to_hex([100,100,100])
        st.markdown(f"""
        <div style="display:flex; align-items:center; margin-bottom:8px; padding-bottom:4px; border-bottom:1px solid #eee;">
            <div style="width:30px;">{row['Position']}</div>
            <div style="width:20px; height:20px; background-color:{color_main}; border: 2px solid {color_second}; border-radius:4px; margin-right:10px;"></div>
            <div style="flex-grow:1;">{team_name}</div>
            <div style="width:60px; text-align:right;">{row['Pts']}</div>
            <div style="width:80px; text-align:right; color:red;">{row['Penalty']}</div>
            <div style="width:100px; text-align:right; color:gray;">{row['Gap from previous']}</div>
            <div style="width:80px; text-align:right; color:#555;">{row['Gap from leader']}</div>
        </div>
        """, unsafe_allow_html=True)

# -------------------------------------------------------------------------------------------

def render_badges(data_dict, pilot_colors, category):
    st.markdown("<hr style='margin:20px 0;'>", unsafe_allow_html=True)
    st.markdown('<div style="display:flex;flex-wrap:wrap;gap:12px;margin-top:8px">', unsafe_allow_html=True)
    for label, name in data_dict.items():
        surname = name.split()[-1] if isinstance(name, str) and name != "n/a" else name
        color = get_color(name, pilot_colors, category)
        st.markdown(f"""
        <div style="background-color:#111111;color:#fff;font-size:0.9em;border-left:4px solid {color};
                    padding:8px 12px;border-radius:6px;">
            <strong>{label}:</strong> {surname}
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------------------------

def _render_pilot_buttons(pilot_list, prefix_key, team_id=None):
    """Renderizza i pulsanti dei piloti in righe responsive (max 4 colonne per riga)."""
    max_cols = 4
    for i in range(0, len(pilot_list), max_cols):
        row = pilot_list[i:i+max_cols]
        cols = st.columns(len(row))
        for j, pilot in enumerate(row):
            pilot_name = str(pilot)
            key = make_safe_key(prefix_key, team_id or "", i+j, pilot_name)
            with cols[j]:
                if st.button(pilot_name, key=key):
                    st.session_state["selected_pilot"] = pilot_name
                    st.session_state["selected_category"] = "F1" if prefix_key == "f1" else "MGP"
                    go_to_screen("pilot_details")
                    st.rerun()
                    
# -----------------------------------------------------------------------------------------------

def extract_votes_from_record(mr):
        """Estrae una lista di numeri (float) dai campi del record marks."""
        if not mr:
            return []
        nums = []

        list_field_candidates = ("votes", "voti", "marks", "scores", "voti_gara", "gara_voti", "results")
        for cand in list_field_candidates:
            if cand in mr and mr[cand] is not None:
                try:
                    lst = parse_list_field(mr[cand])
                except Exception:
                    
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

        for k, v in mr.items():
            if not k or str(k).lower() in ("id", "name", "nome", "driver", "pilot", "pilota"):
                continue
            if v is None:
                continue
            if isinstance(v, (int, float)):
                nums.append(float(v))
                continue
            s = str(v).strip()
            if not s or s.lower() in INVALID_TOKENS:
                continue

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

            found = re.findall(r"-?\d+(?:[.,]\d+)?", s)
            if found:
                for tok in found:
                    try:
                        nums.append(float(tok.replace(",", ".")))
                    except:
                        pass
                continue

            cleaned = re.sub(r"[^\d\.\-\,]+", "", s).replace(",", ".")
            try:
                if cleaned not in ("", ".", "-", "-."):
                    nums.append(float(cleaned))
            except:
                pass

        return nums

# -----------------------------------------------------------------------------------------------

    def compute_stats_from_marks_record(mr, threshold):
        votes = extract_votes_from_record(mr)
        if not votes:
            return None
        nums = [float(x) for x in votes if str(x).strip() != ""]
        if not nums:
            return None
        avg = sum(nums) / len(nums)
        suff_cnt = sum(1 for x in nums if x >= threshold)
        pct = 100.0 * suff_cnt / len(nums)
        return {"avg": avg, "count": len(nums), "suff_count": suff_cnt, "pct": pct}
