max_vel_sprint = "Marco Bezzecchi"
max_vel_gp = "Joan Mir"
sprint_pole_time = 88809

import os
import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pickle
import pandas as pd
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
folder = "C:/Users/andre/OneDrive/Documenti/FM/Results_repository/MGP/"
url = "https://koffsyfgevaannnmjkvl.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtvZmZzeWZnZXZhYW5ubm1qa3ZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ3NDg5MjMsImV4cCI6MjA3MDMyNDkyM30.-i7xenYn2i2Q4pPx5py1A-QZOKL0vk2SwWf3PhMofjk"
supabase = create_client(url, key)
sprint_results = []

response = supabase.table("championship_mgp").select("*").execute().data
with open(master + "championship_mgp.json", "w", encoding="utf-8") as f:
    json.dump(response, f, ensure_ascii=False, indent=4)

with open(master + "championship_mgp.json", "r", encoding="utf-8") as f:
    championship_mgp = json.load(f)

response = supabase.table("marks_mgp_new").select("*").execute().data
with open(master + "marks_mgp_new.json", "w", encoding="utf-8") as f:
    json.dump(response, f, ensure_ascii=False, indent=4)

with open(master + "marks_mgp_new.json", "r", encoding="utf-8") as f:
    marks_mgp_new = json.load(f)

response = supabase.table("circuits_mgp").select("*").execute().data
with open(master + "circuits_mgp.json", "w", encoding="utf-8") as f:
    json.dump(response, f, ensure_ascii=False, indent=4)

with open(master + "circuits_mgp.json", "r", encoding="utf-8") as f:
    circuits_mgp = json.load(f)
    
response = supabase.table("calls_mgp").select("*").execute().data
with open(master + "calls_mgp.json", "w", encoding="utf-8") as f:
    json.dump(response, f, ensure_ascii=False, indent=4)

with open(master + "calls_mgp.json", "r", encoding="utf-8") as f:
    calls_mgp = json.load(f)

response = supabase.table("racers_mgp").select("*").execute().data
with open(master + "racers_mgp.json", "w", encoding="utf-8") as f:
    json.dump(response, f, ensure_ascii=False, indent=4)

with open(master + "racers_mgp.json", "r", encoding="utf-8") as f:
    racers_mgp = json.load(f)
    
# ------- MAIN ----------------------------------------------------------------
# Identify race, save rtr and qtr

for race in championship_mgp:
    if race['status']:
        tag = race['tag']
        break

for gp in circuits_mgp:
    if gp['gp'] == tag:
        rtr = gp['rtr']
        qtr = gp['qtr']
        continue

this_season_racers = [driver["ID"] for driver in marks_mgp_new]
url = "https://" + race["url_race"]
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.1 Safari/537.36"
    )
}

url = "https://" + race["url_race"]

response = requests.get(url, headers=headers)

if response.status_code == 200:
    tables = pd.read_html(response.text)

#%%
# ------ Sprint race ----------------------------------------------------------

if race["sprint"]: 
    sprint_race_results = tables[22]
    sprint_race_results = sprint_race_results.values.tolist()

    # Obtain final sprint race positions of all pilots
    sprint_race_positions = [
        [driver, places[0]]
        for driver in this_season_racers
        for places in sprint_race_results
        if str(driver) in unicodedata.normalize("NFKC", places[2])
    ]
      
    # Obtain quali positions for the drivers                    
    sprint_quali_positions = sprint_race_positions
    
#%%
    sprint_fastest_lap = sprint_race_results[-2][0].split("–")[1].split("(")[0].strip(" ")
    sprint_time = tmstmp2s(sprint_fastest_lap.replace(":","."))

    sprint_driver = sprint_race_results[-2][0].split("-")[0].split("(")[0].split(":")[1]
    sprint_driver = sprint_driver.strip(" ")
#%%    
    for racer in sprint_quali_positions:
        if int(racer[1]) == 1:
            sprint_poleman = racer[0]
    fixer = []
    for driver in sprint_race_positions:
        if "Fastest" not in driver[1]:
            fixer.append(driver)
    sprint_race_positions = fixer
            

    # Obtain bonus for sprint race

    for driver in sprint_quali_positions:
        name, pos = driver[0], driver[1]

        if int(pos) > 12:
            sprint_results.append([name, "Q1"])
        else:
            sprint_results.append([name, "Q2"])
        
    for driver in sprint_results:
        if sprint_poleman in driver[0]:
            driver.append(True)
        else:
            driver.append(False)
    
    for driver in sprint_results:
        if int(sprint_pole_time) < int(qtr) and driver[0] in sprint_poleman:
            driver.append(True)
            upd = supabase.table("circuits_mgp").update({"qtr": int(sprint_pole_time)}).eq("ID", race['circuit']).execute()

        else:
            driver.append(False)

    for driver in sprint_results:
        for racer in racers_mgp: 
            if driver[0] in racer['ID']:
                team = racer['real_team'] 
                continue
        for racer in racers_mgp: 
            if team == racer['real_team'] and racer['ID'] not in driver[0]:
                teammate = racer['ID'] 
                continue
        for racer in sprint_quali_positions:
            if driver[0] == racer[0]:
                driver_quali_pos = racer[1]
                #print(f"{racer[0]} qualified {racer[1]}, ")
        teammate_quali_pos = 99
        for racer in sprint_quali_positions:
            if teammate == racer[0]:
                teammate_quali_pos = racer[1]
                #print(f"his teammate {racer[0]} qualified {teammate_quali_pos}")

        if int(driver_quali_pos) < int(teammate_quali_pos):
            driver.append(True)
            #print(f"Dunque ha battuto il compagno: lui {driver_quali_pos} vs compagno {teammate_quali_pos}\n")
        else:
            driver.append(False)
            #print(f"Dunque NON ha battuto il compagno: lui {driver_quali_pos} vs compagno {teammate_quali_pos}\n")
        for racer in sprint_race_positions:
            if driver[0] == racer[0]:
                try:
                    driver_race_pos = int(racer[1])
                    print(f"{racer[0]} classified {driver_race_pos}, ")
                    continue
                except:
                    driver_race_pos = 99
                    print(f"{racer[0]} retired, ")
        teammate_race_pos = 99
        for racer in sprint_race_positions:
            if teammate == racer[0]:
                try:
                    teammate_race_pos = int(racer[1])
                    print(f"while his teammate {racer[0]} classified {teammate_race_pos}, ")
                    continue
                except:
                    teammate_race_pos = 99
                    print(f"while his teammate {racer[0]} retired, ")
        if int(driver_race_pos) < int(teammate_race_pos):
            driver.append(True)
            print(f"Dunque ha battuto il compagno: lui {driver_race_pos} vs compagno {teammate_race_pos}\n")
        else:
            driver.append(False)
            print(f"Dunque NON ha battuto il compagno: lui {driver_race_pos} vs compagno {teammate_race_pos}\n")

        if driver_race_pos != 99:
            driver.append(int(driver_quali_pos) - driver_race_pos)
        else:
            driver.append(0)
        for racer in sprint_race_positions:
            if driver[0] in racer[0]:
                driver.append(racer[1])
        if driver[0] in sprint_driver:
            driver.append(True)
        else:
            driver.append(False)
        if driver[0] in max_vel_sprint:
            driver.append(True)
        else:
            driver.append(False)
            
    file = folder + tag + "/sprint_poleposition.pkl"
    with open(file, "wb") as tbw:
        pickle.dump(sprint_poleman, tbw)       

            
        
#%%
#---------- Principal race ----------------------------------------------------
race_results = tables[24]
race_results = race_results.values.tolist()
fastest_lap = race_results[-2][0].split("–")[1].split("(")[0].strip(" ")
time = tmstmp2s(fastest_lap.replace(":","."))

driver = race_results[-2][0].split("-")[0].split("(")[0].split(":")[1]
fastest_driver = driver.strip(" ")

# Obtain final race positions of all pilots
race_positions = [
    [driver, places[0]]
    for driver in this_season_racers
    for places in race_results 
    if str(driver) in unicodedata.normalize("NFKC", places[2]) and not "Fastest" in places[0]
]


quali_positions = sprint_quali_positions
poleman = sprint_poleman

# Obtain Q, pole and qtr bonus
results = []

for driver in quali_positions:
    name, pos = driver[0], driver[1]

    if int(pos) >= 13:
        results.append([name, "Q1"])
    else:
        results.append([name, "Q2"])
    
for driver in results:
    if poleman in driver[0]:
        driver.append(True)
    else:
        driver.append(False)

for driver in results:
    if int(sprint_pole_time) < int(qtr) and driver[0] in poleman:
        driver.append(True)
    else:
        driver.append(False)

for driver in results:
    for racer in racers_mgp: 
        if driver[0] in racer['ID']:
            team = racer['real_team'] 
            continue
    for racer in racers_mgp: 
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
    if int(driver_quali_pos) < int(teammate_quali_pos):
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
    if int(driver_race_pos) < int(teammate_race_pos):
        driver.append(True)
    else:
        driver.append(False)
    if driver_race_pos != 99:
        driver.append(int(driver_quali_pos) - driver_race_pos)
    else:
        driver.append(0) 
    for racer in race_positions:
        if driver[0] in racer[0]:
            driver.append(racer[1])
    if driver[0] in unicodedata.normalize("NFKC", fastest_driver):
        driver.append(True)
    else:
        driver.append(False)
    if driver[0] in max_vel_gp:
        driver.append(True)
    else:
        driver.append(False)
    if driver[0] in unicodedata.normalize("NFKC", fastest_driver) and int(time) < int(rtr):
        upd = supabase.table("circuits_mgp").update({"rtr": int(time)}).eq("ID", race['circuit']).execute()
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
stag = tag + year  # es. "SJPN25"

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

# fetch record
res = supabase.table("racers_mgp").select("poles").eq("ID", sprint_poleman).execute()
if not res.data:
    raise RuntimeError(f"Record con ID={sprint_poleman} non trovato.")
row = res.data[0]

sp_list = normalize_to_list(row.get("poles"))
stag_list = normalize_to_list(stag)

# Per ogni item: rimuovi tutte le occorrenze esistenti e poi append --> garantisce che sia ultimo
for item in stag_list:
    # rimuovi ogni occorrenza (se presente)
    sp_list = [v for v in sp_list if v != item]
    # append come ultimo
    sp_list.append(item)

# aggiorna (supabase client convertirà la lista Python in JSON/JSONB)
upd = supabase.table("racers_mgp").update({"poles": sp_list}).eq("ID", sprint_poleman).execute()
print("update:", getattr(upd, "data", None), " error:", getattr(upd, "error", None))


