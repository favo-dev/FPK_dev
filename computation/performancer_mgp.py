import pickle 
from supabase import create_client
import json
import ast


# UPDATE THIS!
# -----------------
tag = "POR" # |||||
# -----------------

master = "C:/Users/andre/OneDrive/Documenti/FM/Hub/"
folder = "C:/Users/andre/OneDrive/Documenti/FM/Results_repository/MGP/"

with open(folder + tag + "/result_matrix.pkl", "rb") as f:
    results = pickle.load(f)

url = "https://koffsyfgevaannnmjkvl.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtvZmZzeWZnZXZhYW5ubm1qa3ZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTQ3NDg5MjMsImV4cCI6MjA3MDMyNDkyM30.-i7xenYn2i2Q4pPx5py1A-QZOKL0vk2SwWf3PhMofjk"
supabase = create_client(url, key)

response = supabase.table("rules_mgp").select("*").execute().data
with open(master + "rules_mgp.json", "w", encoding="utf-8") as f:
    json.dump(response, f, ensure_ascii=False, indent=4)

with open(master + "rules_mgp.json", "r", encoding="utf-8") as f:
    rules = json.load(f)

response = supabase.table("marks_mgp_new").select("*").execute().data
with open(master + "marks_mgp.json", "w", encoding="utf-8") as f:
    json.dump(response, f, ensure_ascii=False, indent=4)

with open(master + "marks_mgp.json", "r", encoding="utf-8") as f:
    marks = json.load(f)
#%%
# ------ SPRINT RACE ----------------------------------------------------------

if results.get('Sprint race'):
    sprint_points = []
    for driver in results['Sprint race']:
        sprint_points.append(driver[0])
    
    POS = []
    for driver in results['Sprint race']:
        try:
            POS.append(int(driver[7]))
        except:
            POS.append(99)
    
    POINTS = []
    for driver in results['Sprint race']:
        try:
            if int(driver[7]) == 1:
                POINTS.append(6)
            elif int(driver[7]) == 2:
                POINTS.append(5)
            elif int(driver[7]) == 3:
                POINTS.append(4)
            elif int(driver[7]) == 4:
                POINTS.append(3)
            elif int(driver[7]) == 5:
                POINTS.append(2)
            elif int(driver[7]) == 6:
                POINTS.append(1)
            else:
                POINTS.append(0)
        except:
            POINTS.append(0)
                
        
    TOT = []
        
    for driver in results['Sprint race']:
        tot = 0
        if 'Q2' in driver[1]:
            tot += float(rules[7].get("value"))
        if driver[2]:
            tot += float(rules[6].get("value"))
        if driver[3]:
            tot += float(rules[8].get("value"))
        if driver[4]:
            tot += float(rules[0].get("value"))
        if driver[5]:
            tot += float(rules[12].get("value"))
        try:
            if float(driver[6]) < 0:
                tot += int(driver[6]) * float(rules[5].get("value"))
        except:
            tot += 0
        try:
            if float(driver[6]) >= 0 and float(driver[7]) <= float(rules[3].get("value")):
                tot += int(driver[6]) * float(rules[5].get("value"))
        except:
            tot += 0
        if driver[8]:
            tot += float(rules[1].get("value"))
        if driver[9]:
            tot += float(rules[11].get("value"))
        TOT.append(tot)
        
    PERF = [x + y for x, y in zip(POINTS, TOT)]
    
    FINAL = [[a, b, c, d, e] for [a, b, c, d, e] in zip(sprint_points, POS, POINTS, TOT, PERF)]

# regola speciale per POS == 99
    for driver in FINAL:
        if int(driver[1]) == 99:
            driver[4] = -99

# ordina: prima per ultima colonna (desc), poi per colonna 1 (asc)
    SPRINT_FINAL = sorted(FINAL, key=lambda row: (-row[-1], row[1]))
    file = folder + tag + "/sprint_final.pkl"
    with open(file, "wb") as tbw:
        pickle.dump(SPRINT_FINAL, tbw)    
#%%
        

# ------ MAIN RACE ----------------------------------------------------------


points = []
for driver in results['Grand Prix']:
    points.append(driver[0])
    
POS = []
for driver in results['Grand Prix']:
    try:
            POS.append(int(driver[7]))
    except:
            POS.append(99)
    
POINTS = []
for driver in results['Grand Prix']:
    for mark in marks:
        if driver[0] in mark.get('ID'):
            try:
                POINTS.append(float(mark.get(tag)))
            except:
                try:
                    check = int(driver[7])
                    POINTS.append(6)
                except:
                    POINTS.append(-99)
#%%
TOT = []
        
for driver in results['Grand Prix']:
    tot = 0
    if 'Q2' in driver[1]:
        tot += float(rules[7].get("value"))
    if driver[2]:
        tot += float(rules[6].get("value"))
    if driver[3]:
        tot += float(rules[8].get("value"))
    if driver[4]:
        tot += float(rules[0].get("value"))
    if driver[5]:
        tot += float(rules[12].get("value"))
    try:
        if float(driver[6]) < 0:
            tot += int(driver[6]) * float(rules[5].get("value"))
    except:
        tot += 0
    try:
        if float(driver[6]) >= 0 and float(driver[7]) <= float(rules[3].get("value")):
            tot += int(driver[6]) * float(rules[5].get("value"))
    except:
        tot += 0
    if driver[8]:
        tot += float(rules[1].get("value"))
    if driver[9]:
        tot += float(rules[11].get("value"))
    if driver[10]:
        tot += float(rules[9].get("value"))
    TOT.append(tot)
        
PERF = [x + y for x, y in zip(POINTS, TOT)]

FINAL = [[a, b, c, d, e] for [a, b, c, d, e] in zip(points, POS, POINTS, TOT, PERF)]

# regola speciale per POS == 99
for driver in FINAL:
        if int(driver[1]) == 99:
            driver[4] = -99

# ordina: prima per ultima colonna (desc), poi per colonna 1 (asc)
RACE_FINAL = sorted(FINAL, key=lambda row: (-row[-1], row[1]))

file = folder + tag + "/race_final.pkl"
with open(file, "wb") as tbw:
        pickle.dump(RACE_FINAL, tbw)    


    

        
    
                
  