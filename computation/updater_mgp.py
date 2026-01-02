import pickle
from supabase import create_client
from datetime import datetime
import json
import ast

# -----------------
tag = "POR"  # |||||
# -----------------

def normalize_to_list(value):
    """Normalizza il valore in una lista di stringhe (gestisce None, list, json string, repr Python)."""
    if value is None:
        return []
    if isinstance(value, list):
        out = []
        for v in value:
            out.extend(normalize_to_list(v))
        return out
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return []
        # prova JSON
        try:
            parsed = json.loads(s)
            return normalize_to_list(parsed)
        except Exception:
            pass
        # prova repr Python (literal_eval)
        try:
            parsed = ast.literal_eval(s)
            return normalize_to_list(parsed)
        except Exception:
            pass
        # fallback: singolo valore stringa
        return [s]
    # altri tipi scalari -> stringa
    return [str(value)]

def merge_unique_preserve_order(existing, additions):
    """Ritorna una lista contenente tutti gli elementi di existing seguiti da quelli di additions non presenti,
       evitando duplicati e preservando l'ordine."""
    if existing is None:
        existing = []
    if additions is None:
        additions = []
    existing_list = normalize_to_list(existing)
    additions_list = normalize_to_list(additions)
    seen = set()
    out = []
    for x in existing_list:
        if x not in seen:
            out.append(x)
            seen.add(x)
    for x in additions_list:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out

# --- Supabase client (tieni la tua URL e key) ---
url = "https://koffsyfgevaannnmjkvl.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtvZmZzeWZnZXZhYW5ubm1qa3ZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ3NDg5MjMsImV4cCI6MjA3MDMyNDkyM30.-i7xenYn2i2Q4pPx5py1A-QZOKL0vk2SwWf3PhMofjk"
supabase = create_client(url, key)

year = str(datetime.now().year)[2:]  # es: "25"
tag = tag + year  # es. "HUN25"
tag_list = normalize_to_list(tag)

# --- Caricamento file .pkl ---
convocated_path = (
    "C:/Users/andre/OneDrive/Documenti/FM/Results_repository/MGP/"
    + tag[:-2]  # usa il tag originale senza year per il path se serve (tu usavi tag prima dell'aggiunta anno)
    + "/called.pkl"
)

with open(convocated_path, "rb") as f:
    convocated = pickle.load(f)

standings_path = (
    "C:/Users/andre/OneDrive/Documenti/FM/Results_repository/MGP/"
    + tag[:-2]
    + "/standings.pkl"
)
with open(standings_path, "rb") as f:
    standings = pickle.load(f)

# --- Utility Supabase: leggi campi multipli in una singola select ---
def fetch_fields(record_id, fields):
    """
    Recupera i campi richiesti per un record (lista di nomi campo).
    Ritorna dizionario (campo -> valore) o None se record non trovato.
    """
    fields_str = ",".join(fields)
    res = supabase.table("racers_mgp").select(fields_str).eq("ID", record_id).execute()
    if not res.data:
        print(f"⚠️ Record non trovato per ID '{record_id}' (select {fields_str})")
        return None
    return res.data[0]

def update_record_lists(record_id, updates):
    """
    updates: dict campo -> lista/valore da aggiungere (non necessariamente list)
    La funzione legge i campi correnti, unisce preservando l'ordine e aggiorna in una singola chiamata.
    """
    # Leggi i campi correnti
    current = fetch_fields(record_id, list(updates.keys()))
    if current is None:
        # possibile scelta: creare il record se non esiste. Qui stampiamo e ritorniamo.
        print(f"Impossibile aggiornare ID '{record_id}' perché non esiste.")
        return

    payload = {}
    changed = False
    for field, additions in updates.items():
        existing_value = current.get(field)
        merged = merge_unique_preserve_order(existing_value, additions)
        # Se il merged è diverso dall'esistente (normalizzato), allora lo aggiungiamo al payload
        norm_existing = normalize_to_list(existing_value)
        if merged != norm_existing:
            payload[field] = merged
            changed = True

    if changed:
        upd_res = supabase.table("racers_mgp").update(payload).eq("ID", record_id).execute()
        # puoi controllare upd_res.status_code o upd_res.error se vuoi
        print(f"✅ Aggiornato ID '{record_id}': {payload}")
    else:
        print(f"ℹ️ Nessuna modifica necessaria per ID '{record_id}'.")

# -------------------- LOGICA PRINCIPALE --------------------

# 1) Per ogni racer in convocated, cerca matching in standings (se racer in who[0]) e aggiungi 'convocations' = tag
for racer in convocated:
    update_record_lists(racer, {"convocations": tag_list})

# 2) Costruisci final = [who[0] for who in standings]
final = []
for who in standings:
    if who[1] != 99:
        final.append(who[0])
    if who[1] == 99:
        final.append(who[0] + "RET")

# 3) Per ogni racer in final che NON è in convocated -> aggiungi 'sub' = tag
for racer in final:
    if racer not in convocated:
        try:
            update_record_lists(racer, {"sub": tag_list})
        except:
            print(f"Ritiro: {racer}")
    if racer[:-3] not in convocated:
        try:
            update_record_lists(racer[:-3], {"sub": tag_list})
        except:
            print(f"Ritiro: {racer}")


# 4) Aggiorna 'wins' per il primo classificato (final[0]) aggiungendo tag
if len(final) >= 1:
    winner = final[0]
    update_record_lists(winner, {"wins": tag_list})

# 5) Aggiorna 'podiums' per i primi 3 classificati (se esistono)
for i in range(min(3, len(final))):
    podium_racer = final[i]
    update_record_lists(podium_racer, {"podiums": tag_list})
   
#6) Aggiorna 'DNF' per i ritirati
for racer in convocated:
    if racer not in final:
        update_record_lists(racer, {"DNF": tag_list})
for racer in final:
    if "RET" in racer:
        update_record_lists(racer[:-3], {"DNF": tag_list})
        

print("Fine aggiornamenti.")

#%% SPRINT RACE
try:
    sprint_standings_path = (
        "C:/Users/andre/OneDrive/Documenti/FM/Results_repository/MGP/"
        + tag[:-2]
        + "/sprint_standings.pkl"
        )
    with open(sprint_standings_path, "rb") as f:
        sprint_standings = pickle.load(f)
        
    # -------------------- LOGICA PRINCIPALE --------------------
    tag = "S"+tag
    tag_list = normalize_to_list(tag)

    # 1) Per ogni racer in convocated, cerca matching in standings (se racer in who[0]) e aggiungi 'convocations' = tag
    for racer in convocated:
        update_record_lists(racer, {"convocations": tag_list})

    # 2) Costruisci final = [who[0] for who in standings]
    final = []
    for who in sprint_standings:
        if who[1] != 99:
            final.append(who[0])
        if who[1] == 99:
            final.append(who[0] + "RET")
            
    # 3) Per ogni racer in final che NON è in convocated -> aggiungi 'sub' = tag
    for racer in final:
        if racer not in convocated:
            try:
                update_record_lists(racer, {"sub": tag_list})
            except:
                print(f"Ritiro: {racer}")
        if racer[:-3] not in convocated:
            try:
                update_record_lists(racer[:-3], {"sub": tag_list})
            except:
                print(f"Ritiro: {racer}")

    # 4) Aggiorna 'wins' per il primo classificato (final[0]) aggiungendo tag
    if len(final) >= 1:
        winner = final[0]
        update_record_lists(winner, {"sprint_wins": tag_list})

    # 5) Aggiorna 'podiums' per i primi 3 classificati (se esistono)
    for i in range(min(3, len(final))):
        podium_racer = final[i]
        update_record_lists(podium_racer, {"podiums": tag_list})
   
    #6) Aggiorna 'DNF' per i ritirati
    for racer in convocated:
        if racer not in final:
            update_record_lists(racer, {"DNF": tag_list})
    for racer in final:
        if "RET" in racer:
            update_record_lists(racer[:-3], {"DNF": tag_list})
            

    print("Fine aggiornamenti.")
    
except:
    print("No sprint")
    
        



    


