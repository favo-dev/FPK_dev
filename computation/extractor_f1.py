pit = "Charles Leclerc"
dod = "Max Verstappen"
record = False


import os
import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pickle
import json
from supabase import create_client
import unicodedata
import ast

# --------- FUNCTIONS ---------------------------------------------------------

def extract_results(url):
    response = requests.get(url)
    contenuto = response.text

    soup = BeautifulSoup(contenuto, "html.parser")
    table = soup.find('table')
    rows = table.find_all("tr")

    results = []
    for row in rows:
        cells = row.find_all(["td", "th"])
        row_data = [cell.text.strip() for cell in cells]
        results.append(row_data)

    results = [line for line in results if line[0].isdigit() or "NC" in line[0]]

    return results

def tmstmp2s(time):
    result = int(time[0]) * 60000 + int(time[2:4]) * 1000 + int(time[5:8])
    return result

# -------- SUPABASE + HUB SETTINGS --------------------------------------------

master = "C:/Users/andre/OneDrive/Documenti/FM/Hub/"
folder = "C:/Users/andre/OneDrive/Documenti/FM/Results_repository/F1"
url = "https://koffsyfgevaannnmjkvl.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtvZmZzeWZnZXZhYW5ubm1qa3ZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ3NDg5MjMsImV4cCI6MjA3MDMyNDkyM30.-i7xenYn2i2Q4pPx5py1A-QZOKL0vk2SwWf3PhMofjk"
supabase = create_client(url, key)
sprint_results = []

response = supabase.table("championship_f1").select("*").execute().data
with open(master + "championship_f1.json", "w", encoding="utf-8") as f:
    json.dump(response, f, ensure_ascii=False, indent=4)

with open(master + "championship_f1.json", "r", encoding="utf-8") as f:
    championship_f1 = json.load(f)

response = supabase.table("marks_f1_new").select("*").execute().data
with open(master + "marks_f1_new.json", "w", encoding="utf-8") as f:
    json.dump(response, f, ensure_ascii=False, indent=4)

with open(master + "marks_f1_new.json", "r", encoding="utf-8") as f:
    marks_f1_new = json.load(f)

response = supabase.table("circuits_f1").select("*").execute().data
with open(master + "circuits_f1.json", "w", encoding="utf-8") as f:
    json.dump(response, f, ensure_ascii=False, indent=4)

with open(master + "circuits_f1.json", "r", encoding="utf-8") as f:
    circuits_f1 = json.load(f)
    
response = supabase.table("calls_f1").select("*").execute().data
with open(master + "calls_f1.json", "w", encoding="utf-8") as f:
    json.dump(response, f, ensure_ascii=False, indent=4)

with open(master + "calls_f1.json", "r", encoding="utf-8") as f:
    calls_f1 = json.load(f)

response = supabase.table("racers_f1").select("*").execute().data
with open(master + "racers_f1.json", "w", encoding="utf-8") as f:
    json.dump(response, f, ensure_ascii=False, indent=4)

with open(master + "racers_f1.json", "r", encoding="utf-8") as f:
    racers_f1 = json.load(f)
    
# ------- MAIN ----------------------------------------------------------------
# Identify race, save rtr and qtr

for race in championship_f1:
    if race['status']:
        tag = race['tag']
        break

for gp in circuits_f1:
    if gp['gp'] == tag:
        rtr = gp['rtr']
        qtr = gp['qtr']
        continue

this_season_racers = [driver["ID"] for driver in marks_f1_new]


# ------ Sprint race ----------------------------------------------------------
if race["sprint"]:
    url = "https://" + race["url_sprint"]
    sprint_race_results = extract_results(url)

    # Obtain final sprint race positions of all pilots
    sprint_race_positions = [
        [driver, places[0]]
        for driver in this_season_racers
        for places in sprint_race_results
        if str(driver) in unicodedata.normalize("NFKC", places[2])
    ]
        
    # Obtain quali positions for the drivers                    
    url = "https://" + race["url_quali_sprint"] 
    sprint_quali_results = extract_results(url)
    sprint_quali_positions = []

    for driver in this_season_racers:
        for places in sprint_quali_results:
            if str(driver) in unicodedata.normalize("NFKC", places[2]):
                try:
                    pos = int(places[0])   # conversione a intero
                    if pos == 1:
                        sprint_poleman = driver
                        sprint_pole_time = tmstmp2s(places[6])
                except ValueError:
                    raise ValueError(f"❌ Errore: impossibile convertire '{places[0]}' in int")
                sprint_quali_positions.append([driver, pos])

    # Obtain bonus for sprint race

    for driver in sprint_quali_positions:
        name, pos = driver[0], driver[1]

        if pos >= 16:
            sprint_results.append([name, "Q1"])
        elif 11 <= pos <= 15:
            sprint_results.append([name, "Q2"])
        elif pos <= 10:
            sprint_results.append([name, "Q3"])
        
    for driver in sprint_results:
        if sprint_poleman in driver[0]:
            driver.append(True)
        else:
            driver.append(False)
    
    for driver in sprint_results:
        if sprint_pole_time < qtr and driver[0] in sprint_poleman:
            driver.append(True)
            upd = supabase.table("circuits_f1").update({"qtr": int(sprint_pole_time)}).eq("ID", race['circuit']).execute()

        else:
            driver.append(False)

    for driver in sprint_results:
        for racer in racers_f1: 
            if driver[0] in racer['ID']:
                team = racer['real_team'] 
                continue
        for racer in racers_f1: 
            if team == racer['real_team'] and racer['ID'] not in driver[0]:
                teammate = racer['ID'] 
                continue
        for racer in sprint_quali_positions:
            if driver[0] in racer[0]:
                driver_quali_pos = racer[1]
                continue
            if teammate in racer[0]:
                teammate_quali_pos = racer[1]
                continue
        if driver_quali_pos < teammate_quali_pos:
            driver.append(True)
        else:
            driver.append(False)
        for racer in sprint_race_positions:
            if driver[0] in racer[0]:
                try:
                    driver_race_pos = int(racer[1])
                    continue
                except:
                    driver_race_pos = 99
            if teammate in racer[0]:
                try:
                    teammate_race_pos = int(racer[1])
                    continue
                except:
                    teammate_race_pos = 99
        if driver_race_pos < teammate_race_pos:
            driver.append(True)
        else:
            driver.append(False)
        if driver_race_pos != 99:
            driver.append(driver_quali_pos - driver_race_pos)
        else:
            driver.append(0)
        for racer in sprint_race_positions:
            if driver[0] in racer[0]:
                driver.append(racer[1])
    file = folder + tag + "/sprint_poleposition.pkl"
    with open(file, "wb") as tbw:
        sprint_poleman = sprint_poleman+"AAA"
        pickle.dump(sprint_poleman, tbw)  

#---------- Principal race ----------------------------------------------------
url = "https://" + race["url_fst"]
fastest_lap = extract_results(url)
fastest_lap = fastest_lap[0]
fastest_time = fastest_lap[6].replace(":",".")
fastest_time = tmstmp2s(fastest_time)
fastest_driver = fastest_lap[2][:-3]
#%%
url = "https://" + race["url_race"]
race_results = extract_results(url)

# Obtain final race positions of all pilots
race_positions = [
    [driver, places[0]]
    for driver in this_season_racers
    for places in race_results
    if str(driver) in unicodedata.normalize("NFKC", places[2])
]
    
# Obtain quali positions for the drivers                    
url = "https://" + race["url_quali"] 
quali_results = extract_results(url)
#%%
quali_positions = []

for driver in this_season_racers:
    for places in quali_results:
        if str(driver) in unicodedata.normalize("NFKC", places[2]):
            try:
                pos = int(places[0])   # conversione a intero
                if pos == 1:
                    poleman = driver
                    pole_time = tmstmp2s(places[6])
            except ValueError:
                raise ValueError(f"❌ Errore: impossibile convertire '{places[0]}' in int")
            quali_positions.append([driver, pos])

# Obtain Q, pole and qtr bonus
results = []

for driver in quali_positions:
    name, pos = driver[0], driver[1]

    if pos >= 16:
        results.append([name, "Q1"])
    elif 11 <= pos <= 15:
        results.append([name, "Q2"])
    elif pos <= 10:
        results.append([name, "Q3"])
    
for driver in results:
    if poleman in driver[0]:
        driver.append(True)
    else:
        driver.append(False)

for driver in results:
    if pole_time < qtr and driver[0] in poleman:
        driver.append(True)
        upd = supabase.table("circuits_f1").update({"qtr": int(pole_time)}).eq("ID", race['circuit']).execute()
    else:
        driver.append(False)

for driver in results:
    for racer in racers_f1: 
        if driver[0] in racer['ID']:
            team = racer['real_team'] 
            continue
    for racer in racers_f1: 
        if team == racer['real_team'] and racer['ID'] not in driver[0]:
            teammate = racer['ID'] 
            continue
    for racer in quali_positions:
        if driver[0] in racer[0]:
            driver_quali_pos = racer[1]
            continue
        if teammate in racer[0]:
            teammate_quali_pos = racer[1]
            continue
    if driver_quali_pos < teammate_quali_pos:
        driver.append(True)
    else:
        driver.append(False)
    for racer in race_positions:
        if driver[0] in racer[0]:
            try:
                driver_race_pos = int(racer[1])
                continue
            except:
                driver_race_pos = 99
        if teammate in racer[0]:
            try:
                teammate_race_pos = int(racer[1])
                continue
            except:
                teammate_race_pos = 99
    if driver_race_pos < teammate_race_pos:
        driver.append(True)
    else:
        driver.append(False)
    if driver_race_pos != 99:
        driver.append(driver_quali_pos - driver_race_pos)
    else:
        driver.append(0) 
    for racer in race_positions:
        if driver[0] in racer[0]:
            driver.append(racer[1])
    if driver[0] in unicodedata.normalize("NFKC", fastest_driver):
        driver.append(True)
    else:
        driver.append(False)
    if driver[0] in unicodedata.normalize("NFKC", fastest_driver) and fastest_time < rtr:
        upd = supabase.table("circuits_f1").update({"rtr": int(fastest_time)}).eq("ID", race['circuit']).execute()
        driver.append(True)
    else:
        driver.append(False)
    if driver[0] in unicodedata.normalize("NFKC", dod):
        driver.append(True)
    else:
        driver.append(False)
    if driver[0] in unicodedata.normalize("NFKC", pit):
        driver.append(True)
    else:
        driver.append(False)
    if driver[0] in unicodedata.normalize("NFKC", pit) and record:
        driver.append(True)
    else:
        driver.append(False)
        
# Results dump
files = {"Grand Prix": results, "Sprint race": sprint_results}

file = folder + tag + "/result_matrix.pkl"
with open(file, "wb") as tbw:
    pickle.dump(files, tbw)       





#%%

year = str(datetime.now().year)[2:]
stag = "S" + tag + year  # es. "SJPN25"

def normalize_to_list(value):
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
        try:
            parsed = json.loads(s)
            return normalize_to_list(parsed)
        except Exception:
            pass
        try:
            parsed = ast.literal_eval(s)
            return normalize_to_list(parsed)
        except Exception:
            pass
        return [s]
    return [str(value)]
#%%
# fetch record
res = supabase.table("racers_f1").select("sprint_poles").eq("ID", sprint_poleman).execute()
if not res.data:
    raise RuntimeError(f"Record con ID={sprint_poleman} non trovato.")
row = res.data[0]

sp_list = normalize_to_list(row.get("sprint_poles"))
stag_list = normalize_to_list(stag)

# Per ogni item: rimuovi tutte le occorrenze esistenti e poi append --> garantisce che sia ultimo
for item in stag_list:
    # rimuovi ogni occorrenza (se presente)
    sp_list = [v for v in sp_list if v != item]
    # append come ultimo
    sp_list.append(item)

# aggiorna (supabase client convertirà la lista Python in JSON/JSONB)
upd = supabase.table("racers_f1").update({"sprint_poles": sp_list}).eq("ID", sprint_poleman).execute()
print("update:", getattr(upd, "data", None), " error:", getattr(upd, "error", None))


#%% Update race/poleposition

year = str(datetime.now().year)[2:]
tag = tag + year  # es. "JPN" -> "JPN25"

# helper: normalizza qualsiasi input in una lista di stringhe piane
def normalize_to_list(value):
    if value is None:
        return []
    # se è già lista, ricorsivamente normalizza e appiattisci
    if isinstance(value, list):
        out = []
        for v in value:
            out.extend(normalize_to_list(v))
        return out
    # stringhe: prova JSON, poi literal_eval (repr Python), poi fallback
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return []
        # prova JSON (es. '["a","b"]')
        try:
            parsed = json.loads(s)
            return normalize_to_list(parsed)
        except Exception:
            pass
        # prova repr Python (es. "['a','b']")
        try:
            parsed = ast.literal_eval(s)
            return normalize_to_list(parsed)
        except Exception:
            pass
        # fallback: singolo valore stringa
        return [s]
    # altri tipi scalari
    return [str(value)]

# fetch record
res = supabase.table("racers_f1").select("poles").eq("ID", poleman).execute()
if not res.data:
    raise RuntimeError(f"Record con ID={poleman} non trovato.")
row = res.data[0]

poles_list = normalize_to_list(row.get("poles"))
tag_list = normalize_to_list(tag)

# aggiungi preservando ordine e evitando duplicati
for item in tag_list:
    if item not in poles_list:
        poles_list.append(item)

# aggiorna (supabase client convertirà la lista Python in JSON/JSONB)
upd = supabase.table("racers_f1").update({"poles": poles_list}).eq("ID", poleman).execute()
print("update:", getattr(upd, "data", None), " error:", getattr(upd, "error", None))
