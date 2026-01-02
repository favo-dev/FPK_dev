import pickle 
from supabase import create_client
import json
import pickle 
import ast

# UPDATE THIS!
# -----------------
tag = "ABU" # |||||
# -----------------

master = "C:/Users/andre/OneDrive/Documenti/FM/Hub/"
folder = "C:/Users/andre/OneDrive/Documenti/FM/Results_repository/F1/"
with open(folder + tag + "/result_matrix.pkl", "rb") as f:
    results = pickle.load(f)
with open(folder + tag + "/race_final.pkl", "rb") as f:
    race_results = pickle.load(f)
    
url = "https://koffsyfgevaannnmjkvl.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtvZmZzeWZnZXZhYW5ubm1qa3ZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ3NDg5MjMsImV4cCI6MjA3MDMyNDkyM30.-i7xenYn2i2Q4pPx5py1A-QZOKL0vk2SwWf3PhMofjk"
supabase = create_client(url, key)

response = supabase.table("calls_f1").select("*").execute().data
with open(master + "calls_f1.json", "w", encoding="utf-8") as f:
    json.dump(response, f, ensure_ascii=False, indent=4)

with open(master + "calls_f1.json", "r", encoding="utf-8") as f:
    calls = json.load(f)

response = supabase.table("rules_f1").select("*").execute().data
with open(master + "rules_f1.json", "w", encoding="utf-8") as f:
    json.dump(response, f, ensure_ascii=False, indent=4)

with open(master + "rules_f1.json", "r", encoding="utf-8") as f:
    rules = json.load(f)

# -------- SPRINT RACE --------------------------------------------------------

if results.get('Sprint race'):
    called = []
    real = []
    with open(folder + tag + "/sprint_final.pkl", "rb") as f:
        sprint_results = pickle.load(f)
    for team in calls:
            called.append(team['first'])
            called.append(team['second'])
    with open(folder + tag + "/called.pkl", "wb") as f:
        pickle.dump(called, f)
    for driver in sprint_results:
            real.append(driver[0])
            
    
    # Check: i piloti convocati rientrano tra quelli che hanno preso parte alla gara (anche se ritirati)?
    missing = [elem for elem in called if elem not in real]
    reserve = []
    for guy in missing:
        for team in calls:
            if guy in team['first'] or guy in team['second']:
                reserve.append([team['reserve'], team['team']])
    seen = []
    rreserve = []
    for sublist in reserve:
        if sublist not in seen:
            rreserve.append(sublist)
            seen.append(sublist)
 
    for n in range(len(called)):
        if called[n] in missing:
            for who in calls:
                if who['first'] in called[n] or who['second'] in called[n]:
                    team_missing = who['team']
                    continue           
            for who in rreserve:
                if who[1] in team_missing and who[0] not in called:
                    called[n] = who[0]
                    
    # Check: i piloti convocati hanno terminato la gara?
    retired = []
    for driver in called:
        for pilot in sprint_results:
            if driver in pilot[0] and pilot[4] == -99:
                retired.append(driver)
    retired = list(set(retired))
    
    rretired = []
    for who in retired:
        for team in calls:
            if team['first'] in who or team['second'] in who:
                rretired.append([who, team['team']])
    
    reserve = []
    for team in rretired:
        for who in calls:
            if who['team'] in team:
                reserve.append([who['reserve'], who['team']])
    seen = []
    rreserve = []
    for sublist in reserve:
        if sublist not in seen:
            rreserve.append(sublist)
            seen.append(sublist)
    
    for name in rretired:
        for i, who in enumerate(called):
            if name[0] in who:
                team_needed = name[1]
                for guy in rreserve:
                    if team_needed in guy[1]:
                        called[i] = guy[0]  # aggiorni direttamente l’elemento nella lista

    
    sprint_standings = []
    for who in called:
        for who2 in sprint_results:
            if who in who2[0]:
                sprint_standings.append(who2)
    
    points = ast.literal_eval(rules[14].get("value"))
    while len(points) < len(called):
        points.append(0)
    sprint_standings = sorted(sprint_standings, key=lambda row: (-row[-1], row[1]))
    sprint_standings = [
        (sf + [sp]) if isinstance(sf, list) else [sf, sp]
        for sf, sp in zip(sprint_standings, points)
        ]
    file = folder + tag + "/sprint_standings.pkl"
    with open(file, "wb") as tbw:
            pickle.dump(sprint_standings, tbw)   
            
# ------- MAIN RACE -----------------------------------------------------------
called = []
real = []
with open(folder + tag + "/race_final.pkl", "rb") as f:
    race_results = pickle.load(f)
for team in calls:
        called.append(team['first'])
        called.append(team['second'])
for driver in race_results:
        real.append(driver[0])

#%%
# Check: i piloti convocati rientrano tra quelli che hanno preso parte alla gara (anche se ritirati)?
missing = [elem for elem in called if elem not in real]
reserve = []
for guy in missing:
    for team in calls:
        if guy in team['first'] or guy in team['second']:
            reserve.append([team['reserve'], team['team']])
seen = []
rreserve = []
for sublist in reserve:
    if sublist not in seen:
        rreserve.append(sublist)
        seen.append(sublist)

for n in range(len(called)):
    if called[n] in missing:
        for who in calls:
            if who['first'] in called[n] or who['second'] in called[n]:
                team_missing = who['team']
                continue           
        for who in rreserve:
            if who[1] in team_missing and who[0] not in called:
                called[n] = who[0]
                
# Check: i piloti convocati hanno terminato la gara?
retired = []
for driver in called:
    for pilot in race_results:
        if driver in pilot[0] and pilot[4] == -99:
            retired.append(driver)
retired = list(set(retired))

rretired = []
for who in retired:
    for team in calls:
        if team['first'] in who or team['second'] in who:
            rretired.append([who, team['team']])

reserve = []
for team in rretired:
    for who in calls:
        if who['team'] in team:
            reserve.append([who['reserve'], who['team']])
seen = []
rreserve = []
for sublist in reserve:
    if sublist not in seen:
        rreserve.append(sublist)
        seen.append(sublist)

for name in rretired:
    for i, who in enumerate(called):
        if name[0] in who:
            team_needed = name[1]
            for guy in rreserve:
                if team_needed in guy[1]:
                    called[i] = guy[0]  # aggiorni direttamente l’elemento nella lista


standings = []
for who in called:
    for who2 in race_results:
        if who in who2[0]:
            standings.append(who2)

points = ast.literal_eval(rules[4].get("value"))
while len(points) < len(called):
    points.append(0)
standings = sorted(standings, key=lambda row: (-row[-1], row[1]))
standings = [
    (sf + [sp]) if isinstance(sf, list) else [sf, sp]
    for sf, sp in zip(standings, points)
    ]

file = folder + tag + "/standings.pkl"
with open(file, "wb") as tbw:
        pickle.dump(standings, tbw)  
        
file = folder + tag + "/called.pkl"
with open(file, "wb") as tbw:
        pickle.dump(called, tbw)  
        
        
            


        
            
                
    

