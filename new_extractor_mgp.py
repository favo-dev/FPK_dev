max_vel_sprint = "Marco Bezzecchi"
max_vel_gp = "Marco Bezzecchi"






































import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pickle
import json
import pandas as pd











# -----------------------------------------------------------------------------


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

#------------------------------------------------------------------------------

# ------------ DATA ACQUISITION ----------------------------------------------- 
new_master = "C:/Users/andre/OneDrive/Documenti/FM/FPK 1.0.0/"
from logic.knock import load_teams, load_pilot, load_championship, load_circuits, load_calls, load_rules, load_marks

classlist = load_teams(new_master)
mgp = load_pilot(new_master, "MGP")
races = load_championship(new_master, "MGP")
circuits = load_circuits(new_master, "MGP")

current_race = next(r for r in races if r["status"])
ID = current_race["tag"]
current_circuit = next(c for c in circuits if c["gp"] == ID)
calls = load_calls(new_master, "MGP")

main_flag, sprint_flag = True, True

# -----------------------------------------------------------------------------

starters, bench = {}, {}
starters2, bench2 = [], []

starters = {
    team: [info["first_mgp"], info["second_mgp"]]
    for team, info in calls.items()
    if info["first_mgp"] or info["second_mgp"]
}

bench = {
    team: [info["reserve_mgp"]]
    for team, info in calls.items()
    if info["reserve_mgp"] 
}

starters2 = [name for drivers in starters.values() for name in drivers]
bench2 = [name for drivers in bench.values() for name in drivers]



url = "https://" + current_race["url_race"]

tables = pd.read_html(url)
race_results = tables[22]

race_results = race_results.values.tolist()

race_positions = [
    [driver, next((places[0] for places in race_results if driver == places[2]), "DQ")]
    for driver in starters2
]


# ----------------------------------------------------------------------------
# -------------------- SPRINT RACE --------------------------------------------
# -----------------------------------------------------------------------------
if current_race["sprint"]:

    sprint_race_results = tables[19]

    sprint_race_results = sprint_race_results.values.tolist()
    # Obtain final race positions of starters
    sprint_race_positions = [
    [driver, next((places[0] for places in sprint_race_results if driver in places[2]), "DQ")]
    for driver in starters2
    ]

# Check if all starters finish their race
    ill =""
    for racer in sprint_race_positions:
        if "Ret" in racer[1] or "DQ" in racer[1] or "NC" in racer[1]:# check if a starter did not finish the race
            for team in starters.keys():
                for driver in starters[team]:
                    if racer[0] in driver:
                        substitute = (str(bench[team]).strip("['']"))
                        for subracer in sprint_race_results:
                            if substitute in subracer[2] and team not in ill:
                                    sprint_race_positions[sprint_race_positions.index(racer)] = [substitute, subracer[0]]
                                    ill = team
                            
    sprint_final_drivers = [line[0] for line in sprint_race_positions]

    doubles = {}
    for elem in sprint_final_drivers:
        if elem in doubles:
            doubles[elem] += 1
        else:
            doubles[elem] = 1     
    rep = []
    for elem, count in doubles.items():
        if count > 1:
            rep.append(elem)
            
    for elem in rep:
        teamdnf=2*bench2.index(elem)
        sprint_final_drivers[teamdnf]=starters2[teamdnf]
      
    sprint_race_positions = [line[1] for line in sprint_race_positions]
    sprint_race_positions = [ "99" if elem == "Ret" or elem == "DQ" or elem == "DNS" else elem for elem in sprint_race_positions]
    sprint_race_positions = [int(x) for x in sprint_race_positions]

    if len(sprint_race_positions) == len(starters2) and [type(x) is int for x in sprint_race_positions]:
        sprint_flag = True
        
    if len(sprint_final_drivers) != len(starters2):
        sprint_flag = False

    # Obtain quali positions for the final drivers 
    sprint_quali_results = tables[14].values.tolist()
    
    sprint_poleman = "n/a"
    sprint_quali_positions = []
    for driver in sprint_final_drivers:
        for result in sprint_quali_results:
            if driver in result[2]:
                if result[0]=="Ret" or result[0]=="DQ":
                    sprint_quali_positions.append(1+int(backup[0]))
                else:
                    sprint_quali_positions.append(int(result[0]))
                    if result[0]=="1" or result[0]==1:
                        sprint_poletime = result[6]
                        sprint_poleman = result[2]
                break
            backup = result
      
    if len(sprint_quali_positions) != len(starters2):
        sprint_flag = False
             
    # Obtain positions delta
    sprint_results = [[a,b,c] for a,b,c in zip(sprint_final_drivers,sprint_race_positions,sprint_quali_positions)]

    sprint_ovtk = []
    for driver in sprint_results:
        if driver[1] != 99:
            tot = driver[2] - driver[1] #* bonus_ovtk
            if tot >= 0: #and int(driver[1]) <= min_ovtk:
                sprint_ovtk.append(tot)
            elif tot >= 0: #and int(driver[1]) > min_ovtk:
                sprint_ovtk.append(0)
            elif tot < 0:
                sprint_ovtk.append(tot)
        else:
            sprint_ovtk.append(0)

    if len(sprint_ovtk) != len(starters2):
        sprint_flag = False

    # Obtain QB and WOT
    sprint_QB = []  # quali position of the teammate of each final pilot
    sprint_WOT = []  # final position of the teammate of each final pilot

    for racer in sprint_results:
        for inquired in mgp:
            if racer[0] in inquired["ID"]:
                team = inquired["real_team"]
                found_teammate = False  # inizialmente assumiamo che il teammate non sia trovato

                for inquired2 in mgp:
                    if inquired2["real_team"] == team and inquired2["go"] and racer[0] not in inquired2["ID"]:
                        teammate = inquired2["ID"]
                        found_teammate = True  # teammate trovato

                        index = 0
                        found_quali = False
                        for driver in sprint_quali_results:
                            index += 1
                            if teammate in driver[2]:
                                if driver[0] == "Ret" or driver[0] == "NC":
                                    sprint_QB.append(index)
                                else:
                                    sprint_QB.append(driver[0])
                                found_quali = True
                                break
                        if not found_quali:
                            sprint_QB.append("99")  # teammate non trovato nelle qualifiche

                        found_race = False
                        for driver in sprint_race_results:
                            if teammate in driver[2]:
                                sprint_WOT.append(driver[0])
                                found_race = True
                                break
                        if not found_race:
                            sprint_WOT.append("DQ")
                        break  # esci dal ciclo dei compagni una volta trovato
                if not found_teammate:
                    sprint_QB.append("99")
                    sprint_WOT.append("99")


                            
    sprint_WOT = [ "99" if elem == "Ret" or elem == "DQ" or elem == "NC" else elem for elem in sprint_WOT]
    teammate_QB = sprint_QB
    sprint_QB = [int(v1) < int(v2) for v1, v2 in zip(sprint_quali_positions, sprint_QB)]
    if len(sprint_QB) != len(starters2):
        sprint_flag = False
    sprint_WOT = [int(v1) < int(v2) for v1, v2 in zip(sprint_race_positions, sprint_WOT)]
    if len(sprint_WOT) != len(starters2):
        sprint_flag = False
        
    # Fastest lap
    sprint_fastest_lap = sprint_race_results[-2][0].split("–")[1].split("(")[0].strip(" ")
    sprint_time = sprint_fastest_lap.replace(":",".")

    sprint_driver = sprint_race_results[-2][0].split("-")[0].split("(")[0].split(":")[1]
    sprint_driver = sprint_driver.strip(driver[0]).strip(" ")
   
    sprint_FST = []
    for who in sprint_results:
        if sprint_driver in who[0]:
            sprint_FST.append(True)
        else:
            sprint_FST.append(False)
    
    if len(sprint_FST) != len(starters2):
        sprint_flag = False
    
    sprint_TS = []
    for who in sprint_results:
        if max_vel_sprint in who[0]:
            sprint_TS.append(True)
        else:
            sprint_TS.append(False)

    if len(sprint_TS) != len(starters2):
        sprint_flag = False

# Check if all starters finish their race
ill =""
for racer in race_positions:
    if "Ret" in racer[1] or "DQ" in racer[1] or "DNS" in racer[1]:# check if a starter did not finish the race
        for team in starters.keys():
            for driver in starters[team]:
                if racer[0] in driver:
                    substitute = (str(bench[team]).strip("['']"))
                    for subracer in race_results:
                        if substitute in subracer[2] and team not in ill:
                            race_positions[race_positions.index(racer)] = [substitute, subracer[0]]
                            ill = team

                        
final_drivers = [line[0] for line in race_positions]

doubles = {}
for elem in final_drivers:
    if elem in doubles:
        doubles[elem] += 1
    else:
        doubles[elem] = 1     
rep = []
for elem, count in doubles.items():
    if count > 1:
        rep.append(elem)
        
for elem in rep:
    teamdnf=2*bench2.index(elem)
    final_drivers[teamdnf]=starters2[teamdnf]

if len(final_drivers) != len(starters2):
    main_flag = False

race_positions = [line[1] for line in race_positions]
race_positions = [ "99" if elem == "Ret" or elem == "DQ" or elem == "DNS" else elem for elem in race_positions]
race_positions = [int(x) for x in race_positions]

if len(race_positions) == len(starters2) and [type(x) is int for x in race_positions]:
    main_flag = True

# Obtain quali positions for the final drivers                    
quali_results = sprint_quali_results

# Obtain quali positions of actual racers
quali_positions = []
real_poleman = "n/a"

for driver in final_drivers:
    found = False  # Per controllare se il driver è stato trovato
    for result in quali_results:
        if driver in result[2]:
            found = True
            if result[0] == "Ret" or result[0] == "DQ":
                quali_positions.append(1 + int(backup[0]))
            else:
                quali_positions.append(int(result[0]))
                if result[0] == "1" or result[0] == 1:
                    poletime = result[6]
                    real_poleman = result[2]
            break
        backup = result
    
    # Se non è mai stato trovato, uso il backup
    if not found:
        quali_positions.append(99)

#%%       
if len(quali_positions) != len(starters2):
    main_flag = False


# Obtain positions delta
results = [[a,b,c] for a,b,c in zip(final_drivers,race_positions,quali_positions)]

ovtk = []
for driver in results:
    if driver[1] != 99:
        tot = driver[2] - driver[1] #* bonus_ovtk
        if tot >= 0: #and int(driver[1]) <= min_ovtk:
            ovtk.append(tot)
        elif tot >= 0: #and int(driver[1]) > min_ovtk:
            ovtk.append(0)
        elif tot < 0:
            ovtk.append(tot)
    else:
        ovtk.append(0)

if len(ovtk) != len(starters2):
   main_flag = False
   
   
# Obtain QB and WOT
QB = []  # quali position of the teammate of each final pilot
WOT = []  # final position of the teammate of each final pilot

for racer in results:
    for inquired in mgp:
        if racer[0] in inquired["ID"]:
            team = inquired["real_team"]
            found_teammate = False  # inizialmente assumiamo che il teammate non sia trovato

            for inquired2 in mgp:
                if inquired2["real_team"] == team and inquired2["go"] and racer[0] not in inquired2["ID"]:
                    teammate = inquired2["ID"]
                    found_teammate = True

                    index = 0
                    found_quali = False
                    for driver in quali_results:
                        index += 1
                        if teammate == driver[2]:
                            if driver[0] == "Ret":
                                QB.append(index)
                            else:
                                QB.append(driver[0])
                            found_quali = True
                            break
                    if not found_quali:
                        QB.append("99")  # teammate non trovato nelle qualifiche

                    found_race = False
                    for driver in race_results:
                        if teammate == driver[2]:
                            WOT.append(driver[0])
                            found_race = True
                            break
                    if not found_race:
                        WOT.append("DQ")
                    break  # esci dal ciclo una volta trovato un teammate valido

            if not found_teammate:
                QB.append("99")
                WOT.append("99")

              
WOT = [ "99" if elem == "Ret" or elem == "DQ" or elem == "DNS" else elem for elem in WOT]

QB = [int(v1) < int(v2) for v1, v2 in zip(quali_positions, QB)]
if len(QB) != len(starters2):
    main_flag = False
WOT = [int(v1) < int(v2) for v1, v2 in zip(race_positions, WOT)]
if len(WOT) != len(starters2):
    main_flag = False
#%%
# Fastest lap
fastest_lap = race_results[-2][0].split("–")[1].split("(")[0].strip(" ")
time = fastest_lap.replace(":",".")

time_rtr = tmstmp2s(time)
reference = current_circuit["rtr"]

driver = race_results[-2][0].split("–")[0].split("(")[0].split(":")[1]
driver = driver.strip(driver[0])

if time_rtr <= reference:
    for a in circuits:
        if a["gp"] == ID:
            a["rtr"] = time_rtr   
        
    with open(new_master + "data/circuits_mgp.json", "w") as file:
        json.dump(circuits, file, indent=4)               
    print("Nuovo record del circuito in gara. circuits.mgp aggiornato")

FST = []
RTR = []
for who in results:
    if driver in who[0]:
        FST.append(True)
        if time_rtr <= reference:
            RTR.append(True)
        else:
            RTR.append(False)
    else:
        FST.append(False)
        RTR.append(False)
        
if len(FST) != len(starters2):
    main_flag = False
if len(RTR) != len(starters2):
    main_flag = False
    
TS = []
for who in results:
    if max_vel_gp in who[0]:
        TS.append(True)
    else:
        TS.append(False)

if len(TS) != len(starters2):
    main_flag = False
    
# -----------------------------------------------------------------------------

# Save & Export Raw Data
results = [[name, quali_pos, race_pos, delta, qb, wot, fst, rtr, ts] for name, quali_pos, race_pos, delta, qb, wot, fst, rtr, ts in zip(final_drivers, quali_positions, race_positions, ovtk, QB, WOT, FST, RTR, TS)]
if current_race["sprint"]:
    results2 = [[name, quali_pos, race_pos, delta, qb, wot, fst, ts] for name, quali_pos, race_pos, delta, qb, wot, fst, ts in zip(sprint_final_drivers, sprint_quali_positions, sprint_race_positions, sprint_ovtk, sprint_QB, sprint_WOT, sprint_FST, sprint_TS)]
else:
    results2 = []
    
results = {"Grand Prix": results, "Sprint race": results2}

file = new_master + "results/MGP/"+ ID + "/result_matrix.pkl"
with open(file, "wb") as tbw:
    pickle.dump(results, tbw)   

# -----------------------------------------------------------------------------

# Apply championship rules
rules = load_rules(new_master,"MGP")


if current_race["sprint"]:
    bonus_sprint = []
    for driver in results["Sprint race"]:
        perf = 0
        if driver[1] == 1:
            perf = perf + int(rules["Pole position"])
            if tmstmp2s(sprint_poletime) <= current_circuit["qtr"]:
                perf = perf + int(rules["Qualifying track record"])
                
                for a in circuits:
                    if a["gp"] == ID:
                        a["qtr"] = tmstmp2s(sprint_poletime)   
                        
                with open(new_master + "data/circuits_mgp.json", "w") as file:
                    json.dump(circuits, file, indent=4)               
                print("Nuovo record del circuito in qualifica. circuits_mgp.json aggiornato")
                
        if driver[1] < 13:
            perf = perf + int(rules["Q2"])
        if driver[3] < 0:
            perf = perf + float(rules["Points per gained/lost position"])*driver[3]
        if driver[3] > 0 and driver[2] <= int(rules["Minimum race position to receive positive overtake bonus"]):
            perf = perf + float(rules["Points per gained/lost position"])*driver[3]           
        if driver[4] == True:
            perf = perf + int(rules["Beating the teammate in qualifying"])
        if driver[5] == True:
            perf = perf + int(rules["Win on teammate"])
        if driver[6] == True:
            perf = perf + int(rules["Fastest race lap"])
        if driver[7] == True:
            perf = perf + int(rules["Top speed"])
        bonus_sprint.append(perf)
    
    marks_sprint =  []
    lines = load_marks(new_master, "MotoGP", True)
                         
    
    for driver in sprint_final_drivers:
        for who in lines:
            if driver in who:
                marks_sprint.append(lines.get(who))
    lines2 = lines

    total_sprint = []
    for value in range(0,len(bonus_sprint)):
        total_sprint.append(float(bonus_sprint[value] + marks_sprint[value]))

    performance_sprint = [sprint_final_drivers, sprint_race_positions, marks_sprint, bonus_sprint, total_sprint]
    for i in range(0,len(performance_sprint[0])):
        if performance_sprint[1][i] == 99:
            performance_sprint[4][i] = -99
            
    
    performance_sprint = list(map(list, zip(*performance_sprint)))
    file = new_master + "results/MGP/"+ ID + "/sprint_performance_matrix.pkl"
    with open(file, 'wb') as f:
        pickle.dump(performance_sprint, f)

    standings_sprint = sorted(performance_sprint, key=lambda x: (x[-1], -x[1]), reverse = True)
    points_sprint = rules["Sprint Race points distribution"]
    standings_sprint = list(map(list, zip(*standings_sprint)))
    standings_sprint.append(points_sprint)
    standings_sprint = list(map(list, zip(*standings_sprint)))

    file = new_master + "results/MGP/"+ ID + "/sprint_standings.pkl"
    with open(file, 'wb') as f:
        pickle.dump(standings_sprint, f)

    file = new_master + "results/MGP/"+ ID + "/sprint_final_starters.pkl"
    with open(file, 'wb') as f:
        pickle.dump(sprint_final_drivers, f)

    file = new_master + "results/MGP/"+ ID + "/sprint_poleposition.pkl"
    with open(file, 'wb') as f:
        pickle.dump(sprint_poleman, f)
        
bonus = []
for driver in results["Grand Prix"]:
    perf = 0
    if driver[1] == 1:
        perf = perf + int(rules["Pole position"])
        if tmstmp2s(poletime) <= current_circuit["qtr"]:
            perf = perf + int(rules["Qualifying track record"])
            
            for a in circuits:
                if a["gp"] == ID:
                    a["qtr"] = tmstmp2s(poletime)   
                    
            with open(new_master + "data/circuits_mgp.json", "w") as file:
                json.dump(circuits, file, indent=4)               
            print("Nuovo record del circuito in qualifica. circuits_mgp.json aggiornato")
    
    if driver[1] < 13:
        perf = perf + int(rules["Q2"])
    if driver[3] < 0:
        perf = perf + float(rules["Points per gained/lost position"])*driver[3]
    if driver[3] > 0 and driver[2] <= int(rules["Minimum race position to receive positive overtake bonus"]):
        perf = perf + float(rules["Points per gained/lost position"])*driver[3]           
    if driver[4] == True:
        perf = perf + int(rules["Beating the teammate in qualifying"])
    if driver[5] == True:
        perf = perf + int(rules["Win on teammate"])
    if driver[6] == True:
        perf = perf + int(rules["Fastest race lap"])
    if driver[7] == True:
        perf = perf + int(rules["Race track record"])
        
        for a in circuits:
            if a["gp"] == ID:
                a["rtr"] = time_rtr   
                
        with open(new_master + "data/circuits_mgp.json", "w") as file:
            json.dump(circuits, file, indent=4)               
        print("Nuovo record del circuito in gara. circuits.mgp aggiornato")
    
    if driver[8] == True:
        perf = perf + int(rules["Top speed"])
    bonus.append(perf)
    
marks = []
lines = load_marks(new_master, "MotoGP", False)
#%%
for driver in final_drivers:
    for who in lines:
        for who2 in results["Grand Prix"]:
            if driver in who and who2[0] in who and who2[2] != 99 and lines[who] != -1:
                marks.append(lines.get(who))
            elif driver in who and who2[0] in who and who2[2] != 99 and lines[who] == -1:
                marks.append(6)
            elif driver in who and who2[0] in who and who2[2] == 99:
                marks.append(lines.get(who))


total = []
for value in range(0,len(bonus)):
    total.append(float(bonus[value] + marks[value]))

performance = [final_drivers, race_positions, marks, bonus, total]
for i in range(0,len(performance[0])):
    if performance[1][i] == 99:
        performance[4][i] = -99

performance = list(map(list, zip(*performance)))

file = new_master + "results/MGP/"+ ID + "/performance_matrix.pkl"
with open(file, 'wb') as f:
    pickle.dump(performance, f)

standings = sorted(performance, key=lambda x: (x[-1], -x[1]), reverse = True)
points = rules["Grand Prix points distribution"]
standings = list(map(list, zip(*standings)))
standings.append(points)
standings = list(map(list, zip(*standings)))

file = new_master + "results/MGP/"+ ID + "/standings.pkl"
with open(file, 'wb') as f:
    pickle.dump(standings, f)

file = new_master + "results/MGP/"+ ID + "/starters.pkl"
with open(file, 'wb') as f:
    pickle.dump(starters2, f)

file = new_master + "results/MGP/"+ ID + "/bench.pkl"
with open(file, 'wb') as f:
    pickle.dump(bench2, f)
    
file = new_master + "results/MGP/"+ ID + "/final_starters.pkl"
with open(file, 'wb') as f:
    pickle.dump(final_drivers, f)

file = new_master + "results/MGP/"+ ID + "/poleposition.pkl"
with open(file, 'wb') as f:
    pickle.dump(real_poleman, f)

file = new_master + "results/MGP/"+ ID + "/marks.pkl"
with open(file, 'wb') as f:
    pickle.dump(lines, f)
    
if current_race["sprint"]:
    file = new_master + "results/MGP/"+ ID + "/sprint_marks.pkl"
    with open(file, 'wb') as f:
        pickle.dump(lines2, f)
    



















        
                
