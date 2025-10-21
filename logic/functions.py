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

# --------------------- SUPABASE CLIENT --------------------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

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
    try:
        res = supabase.from_(name).select("*").execute()
        return res.data or []
    except Exception:
        return []

# -------------------------------------------------------------------------------------------

def list_all(bucket: str, path: str = "") -> List[dict]:
    all_items = []
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

# --- Helpers per parsing/errore (robusti per diverse versioni supabase-py) ---
def _extract_error(resp):
    """
    Estrae un errore (stringa / oggetto) da una risposta supabase-py-like.
    Restituisce None se non trova errori.
    """
    if resp is None:
        return None
    # oggetti con attributo .error
    err = getattr(resp, "error", None)
    if err:
        return err
    # dict-like
    try:
        if isinstance(resp, dict):
            # possibile chiave 'error' o 'message'
            return resp.get("error") or resp.get("message")
    except Exception:
        pass
    return None

def _extract_data(resp):
    """
    Estrae la parte 'data' o equivalente dalla risposta.
    Restituisce None se non riesce a trovare dati.
    """
    if resp is None:
        return None
    # oggetti con .data
    data = getattr(resp, "data", None)
    if data is not None:
        return data
    # dict-like
    if isinstance(resp, dict):
        # preferenze per strutture comuni
        return resp.get("data") or resp.get("session") or resp.get("user") or resp
    # fallback: oggetti con .user o .session come attributi
    if hasattr(resp, "user"):
        return getattr(resp, "user")
    if hasattr(resp, "session"):
        return getattr(resp, "session")
    return None

def _extract_session_from_signin(signin_resp):
    """
    Dalla risposta di sign_in_with_password cerca di estrarre
    access_token, refresh_token, e l'oggetto session intero.
    Restituisce (access_token, refresh_token, session_obj) o (None, None, None).
    """
    data = _extract_data(signin_resp) or {}
    session = None

    # formato comune: {'session': {...}, 'user': {...}}
    if isinstance(data, dict):
        session = data.get("session") or data.get("data", {}).get("session") or data.get("session", {})

    # fallback a attributi dell'oggetto
    if not session:
        session = getattr(signin_resp, "session", None)

    if not session:
        return None, None, None

    access = session.get("access_token") or session.get("accessToken") or session.get("access-token")
    refresh = session.get("refresh_token") or session.get("refreshToken") or session.get("refresh-token")
    return access, refresh, session

# --- Re-auth flow (form) che imposta session e aggiorna l'email in Auth ---
def reauth_and_update_email(user, new_email, supabase_client):
    """
    Chiede password in un form (usa st.form per evitare rerun indesiderati),
    esegue sign_in_with_password, set_session(access, refresh) e poi update_user.
    Ritorna True se l'update Auth è stato avviato/andato a buon fine, False altrimenti.
    - user: dict contenente almeno 'mail'
    - new_email: email desiderata
    - supabase_client: il client supabase (es. la variabile globale supabase)
    """
    if not user or not user.get("mail"):
        st.error("Informazioni utente mancanti (mail).")
        return False

    st.markdown("#### Re-auth required")
    with st.form(key="reauth_form", clear_on_submit=False):
        pw = st.text_input("Inserisci la tua password attuale per ri-autenticarti", type="password", key="reauth_password")
        submit = st.form_submit_button("Re-authenticate & finish email change")

    # se form non inviato, ritorna None -> caller deve continuare l'esecuzione normalmente
    if not submit:
        return None

    if not pw:
        st.error("Devi inserire la password.")
        return False

    # 1) sign in
    try:
        signin_resp = supabase_client.auth.sign_in_with_password({"email": user.get("mail"), "password": pw})
    except Exception as e:
        st.error(f"sign_in_with_password exception: {e}")
        return False

    st.write("DEBUG: signin_resp:", _extract_data(signin_resp))
    signin_err = _extract_error(signin_resp)
    if signin_err:
        st.error(f"Re-auth failed: {signin_err}")
        return False

    # 2) estrai access/refresh token
    access_token, refresh_token, session_obj = _extract_session_from_signin(signin_resp)
    if not access_token or not refresh_token:
        st.error("Login OK ma non ho trovato access_token/refresh_token nella risposta. Controlla la versione di supabase-py.")
        st.write("DEBUG session object:", session_obj)
        return False

    st.write("DEBUG: access_token trovato, lunghezza:", len(access_token))

    # 3) Imposta la sessione nel client supabase (più varianti per compatibilità)
    set_ok = False
    try:
        # modalità moderna: passiamo un dict
        try:
            set_resp = supabase_client.auth.set_session({"access_token": access_token, "refresh_token": refresh_token})
            set_err = _extract_error(set_resp)
            st.write("DEBUG set_session resp:", _extract_data(set_resp))
            if set_err:
                st.warning(f"set_session returned error: {set_err}")
            else:
                set_ok = True
        except Exception as e:
            st.write("DEBUG: set_session(dict) raised:", e)

        if not set_ok:
            # fallback: set_session(access, refresh)
            try:
                set_resp2 = supabase_client.auth.set_session(access_token, refresh_token)
                set_err2 = _extract_error(set_resp2)
                st.write("DEBUG set_session fallback resp:", _extract_data(set_resp2))
                if set_err2:
                    st.warning(f"set_session fallback returned error: {set_err2}")
                else:
                    set_ok = True
            except Exception as e2:
                st.write("DEBUG: set_session(access, refresh) raised:", e2)
    except Exception as e:
        st.error(f"Errore durante set_session: {e}")
        return False

    if not set_ok:
        st.error("Non sono riuscito a impostare la sessione nel client Supabase; non posso aggiornare l'Auth.")
        st.write("Opzione alternativa: usa un endpoint server con la service_role key per forzare l'aggiornamento.")
        return False

    st.info("Sessione impostata correttamente nel client — provo ad aggiornare l'email in Auth...")

    # 4) aggiorna l'email nell'Auth
    try:
        auth_update_resp = supabase_client.auth.update_user({"email": new_email})
    except Exception as e:
        st.error(f"auth.update_user() exception: {e}")
        return False

    st.write("DEBUG auth_update_resp:", _extract_data(auth_update_resp))
    auth_err = _extract_error(auth_update_resp)
    if auth_err:
        st.error(f"Errore aggiornamento Auth: {auth_err}")
        return False

    st.success("Email aggiornata in Auth (controlla le email per eventuali conferme).")
    return True

# --- Funzione principale richiesta: update_user_field ---
def update_user_field(user, field, label, supabase_client, update_profiles_table=False, profiles_table_name="profiles"):
    """
    UI + logica per aggiornare un singolo campo dell'user.
    - user: dict con almeno 'who' e 'mail' (se stai aggiornando mail)
    - field: nome della colonna da aggiornare (es. 'mail', 'name', ecc.)
    - label: etichetta mostrata all'utente (es. "Email")
    - supabase_client: istanza del client supabase (es. supabase)
    - update_profiles_table: se True, aggiorna anche la tabella profiles_table_name (opzionale)
    """
    if not user:
        st.error("User non disponibile.")
        return

    temp_key = f"{field}_temp"
    input_key = f"{field}_input"
    save_key = f"save_{field}"

    # inizializza temp
    if temp_key not in st.session_state:
        st.session_state[temp_key] = user.get(field, "") or ""

    # widget input
    new_val = st.text_input(label, value=st.session_state[temp_key], key=input_key)
    st.session_state[temp_key] = new_val

    # salva
    if st.button(f"Save {label}", key=save_key, use_container_width=True):
        # semplici validazioni
        if not new_val or (field == "mail" and "@" not in new_val):
            st.error(f"Insert a valid {label.lower()}!")
            return

        # 1) aggiorna tabelle custom
        try:
            resp_class = supabase_client.from_("class_new").update({field: new_val}).eq("who", user["who"]).execute()
            resp_teams = supabase_client.from_("teams").update({field: new_val}).eq("who", user["who"]).execute()
        except Exception as e:
            st.error(f"DB update exception: {e}")
            return

        err_class = _extract_error(resp_class)
        err_teams = _extract_error(resp_teams)
        if err_class or err_teams:
            st.error(f"Database update error: {err_class or err_teams}")
            st.write("resp_class debug:", _extract_data(resp_class))
            st.write("resp_teams debug:", _extract_data(resp_teams))
            return

        # opzionale: aggiorna la tabella profiles se richiesta (mantieni coerenza)
        if update_profiles_table:
            try:
                resp_profiles = supabase_client.from_(profiles_table_name).update({field: new_val}).eq("id", user.get("id")).execute()
                err_profiles = _extract_error(resp_profiles)
                if err_profiles:
                    st.warning(f"Warning updating profiles table: {err_profiles}")
                    st.write("resp_profiles debug:", _extract_data(resp_profiles))
            except Exception as e:
                st.warning(f"Exception updating profiles table: {e}")

        # 2) Se non è email, abbiamo finito
        if field != "mail":
            user[field] = new_val
            st.session_state["user"] = user
            st.success(f"{label} updated!")
            if temp_key in st.session_state:
                del st.session_state[temp_key]
            return

        # 3) Se è email: proviamo ad aggiornare l'Auth
        # prima controlliamo se c'è sessione attiva
        try:
            get_user_resp = supabase_client.auth.get_user()
        except Exception as e:
            get_user_resp = None
            st.write("DEBUG get_user() exception:", e)

        get_user_err = _extract_error(get_user_resp)
        if get_user_resp and not get_user_err:
            # c'è sessione: proviamo direttamente ad aggiornare
            st.info("Sessione attiva: provo ad aggiornare Auth...")
            try:
                auth_update_resp = supabase_client.auth.update_user({"email": new_val})
            except Exception as e:
                st.error(f"auth.update_user() exception: {e}")
                return

            st.write("DEBUG auth_update_resp:", _extract_data(auth_update_resp))
            auth_err = _extract_error(auth_update_resp)
            if auth_err:
                st.error(f"Errore aggiornamento Auth: {auth_err}")
                return

            st.success("Email aggiornata in Auth (controlla le email per eventuali conferme).")
            user["mail"] = new_val
            st.session_state["user"] = user
            if temp_key in st.session_state:
                del st.session_state[temp_key]
            return
        else:
            # sessione mancante → flusso di re-auth (form)
            st.warning("Auth session missing! Devo ri-autenticarti per aggiornare l'email.")
            ok = reauth_and_update_email(user, new_val, supabase_client)
            # reauth_and_update_email ritorna:
            # - None se l'utente non ha ancora inviato il form (non dobbiamo fare altro)
            # - False se fallito
            # - True se update andato a buon fine
            if ok is None:
                # l'utente non ha ancora inviato il form: non mostrare ulteriori messaggi
                return
            if ok is False:
                st.error("Re-auth o update Auth fallito. Vedi i messaggi di debug sopra.")
                return
            # ok == True: l'email è stata aggiornata in Auth
            user["mail"] = new_val
            st.session_state["user"] = user
            st.success("Email aggiornata correttamente.")
            if temp_key in st.session_state:
                del st.session_state[temp_key]
            return

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

# -----------------------------------------------------------------------------------------------

def avg_to_hex(avg):
    if avg is None:
        return "#666666"
    min_avg = 4.5
    max_avg = 8.0
    col_low = "#6a0d1a"   
    col_high = "#00b300"   
    r1, g1, b1 = hex_to_rgb(col_low)
    r2, g2, b2 = hex_to_rgb(col_high)
    t = (float(avg) - min_avg) / (max_avg - min_avg)
    t = max(0.0, min(1.0, t))
    r = r1 + (r2 - r1) * t
    g = g1 + (g2 - g1) * t
    b = b1 + (b2 - b1) * t
    return safe_rgb_to_hex((r, g, b))

# -----------------------------------------------------------------------------------------------

def render_table(df):
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
