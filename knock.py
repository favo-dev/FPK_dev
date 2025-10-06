import json
import os
import pickle

JSON_PATH = "data/class.json"

def load_teams(master):
    if os.path.exists(master + JSON_PATH):
        with open(master + JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

#------------------------------------------------------------------------------

def save_teams(master, teams):
    with open(master + JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(teams, f, indent=4, ensure_ascii=False)
        
#------------------------------------------------------------------------------

def load_pilot(master,category):
    path = "data/"
    if "F1" in category:
        what = "racers_f1.json"
        if os.path.exists(master + path + what):
            with open(master + path + what, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
    if "MGP" in category:
        what = "racers_mgp.json"
        if os.path.exists(master + path + what):
            with open(master + path + what, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

#------------------------------------------------------------------------------

def save_callup(master, user, category,data):
    path = master + "data/"
    
    if "F1" in category:
        path = path + "calls_f1.json"
        with open(path, "r", encoding="utf-8") as f:
            all_data = json.load(f)
    
    if "MGP" in category:
        path = path + "calls_mgp.json"
        with open(path, "r", encoding="utf-8") as f:
            all_data = json.load(f)
   
    all_data[user["ID"]] = data

    with open(path, "w") as f:
        json.dump(all_data, f, indent=4)

#------------------------------------------------------------------------------

def load_championship(master,category):
    if "F1" in category:
        with open(master + "data/championship_f1.json", "r", encoding="utf-8") as f:
            return  json.load(f)
    if "MGP" in category:
        with open(master + "data/championship_mgp.json", "r", encoding="utf-8") as f:
            return  json.load(f)

#------------------------------------------------------------------------------

def load_rules(master,category):
    if "F1" in category:
        with open(master + "data/rules_f1.json", "r", encoding="utf-8") as f:
            return  json.load(f)
    if "MGP" in category:
        with open(master + "data/rules_mgp.json", "r", encoding="utf-8") as f:
            return  json.load(f)

#------------------------------------------------------------------------------

def get_results(master,race, category, sprint):
    if sprint is True:
        if "F1" in category:
            path = master + f"results/F1/{race['tag']}/sprint_standings.pkl"
            with open(path, "rb") as f:
                return pickle.load(f)
        if "MotoGP" in category:
            path = master + f"results/MGP/{race['tag']}/sprint_standings.pkl"
            with open(path, "rb") as f:
                return pickle.load(f)
            
    if sprint is False:               
        if "F1" in category:
            path = master + f"results/F1/{race['tag']}/standings.pkl"
            with open(path, "rb") as f:
                return pickle.load(f)
        if "MotoGP" in category:
            path = master + f"results/MGP/{race['tag']}/standings.pkl"
            with open(path, "rb") as f:
                return pickle.load(f)

#------------------------------------------------------------------------------

def get_all(master,race, category):
    if "F1" in category:
        path = master + f"results/F1/{race['tag']}/result_matrix.pkl"
        with open(path, "rb") as f:
            return pickle.load(f)
    if "MotoGP" in category:
        path = master + f"results/MGP/{race['tag']}/result_matrix.pkl"
        with open(path, "rb") as f:
            return pickle.load(f)

#------------------------------------------------------------------------------

def get_poleman(master,race, category):  
        if "F1" in category:               
            path = master + f"results/F1/{race['tag']}/sprint_poleposition.pkl"
            with open(path, "rb") as f:
                return pickle.load(f)
        if "MotoGP" in category:               
            path = master + f"results/MGP/{race['tag']}/sprint_poleposition.pkl"
            with open(path, "rb") as f:
                return pickle.load(f)
            
#------------------------------------------------------------------------------

def load_circuits(master,category):
    if "F1" in category:
        with open(master + "data/circuits_f1.json", "r", encoding="utf-8") as f:
            return  json.load(f)
    if "MGP" in category:
        with open(master + "data/circuits_mgp.json", "r", encoding="utf-8") as f:
            return  json.load(f)

#------------------------------------------------------------------------------

def load_calls(master,category):
    if "F1" in category:
        with open(master + "data/calls_f1.json", "r", encoding="utf-8") as f:
            return  json.load(f)
    if "MGP" in category:
        with open(master + "data/calls_mgp.json", "r", encoding="utf-8") as f:
            return  json.load(f)
        
#------------------------------------------------------------------------------

def load_marks(master, category, sprint):
    if sprint is True:
        if "F1" in category:
            path = master + "data/marks_sprint_f1.json"
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        if "MotoGP" in category:
            path = master + "data/marks_sprint_mgp.json"
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
            
    if sprint is False:               
        if "F1" in category:
            path = master + "data/marks_f1.json"
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        if "MotoGP" in category:
            path = master + "data/marks_mgp.json"
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

#------------------------------------------------------------------------------
def load_roll(master):
    path = master + "data/roll_of_honor.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

#------------------------------------------------------------------------------
def load_pen(master):
    path = master + "data/penalty.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
    