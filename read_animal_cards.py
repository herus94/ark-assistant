import re
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator

class Enclosure(BaseModel):
    size: int
    rock: int = 0
    water: int = 0

class Requirements(BaseModel):
    symbols: Dict[str, int] = Field(default_factory=dict)
    reputation: int = 0
    partner_zoo: bool = False
    university: bool = False
    level_2_card_required: Optional[str] = None

class Bonus(BaseModel):
    appeal: int = 0
    conservation: int = 0
    reputation: int = 0

class AnimalCard(BaseModel):
    card_id: int
    name: str
    latin_name: Optional[str]
    cost: int
    types: List[str] # Lista di tag (es. ["Predator", "Predator"]) per contare i simboli
    continents: List[str]
    enclosure: Enclosure
    requirements: Requirements
    abilities: List[str]
    bonuses: Bonus
    
def parse_enclosure_string(val: str) -> Enclosure:
    val = str(val).upper().strip()
    # Estrae la taglia (primo numero)
    size_match = re.search(r'^(\d+)', val)
    size = int(size_match.group(1)) if size_match else 0
    
    # Conta le R (Rock) e le W (Water)
    # Se trovi '3R' -> 1 Rock. Se trovi '4WW' -> 2 Water.
    rock = val.count('R')
    water = val.count('W')
    
    # Caso speciale Marine World (es. "Aq 3")
    if "AQ" in val:
        aq_match = re.search(r'AQ (\d+)', val)
        size = int(aq_match.group(1)) if aq_match else size
        
    return Enclosure(size=size, rock=rock, water=water)

def parse_multi_type(val: str) -> List[str]:
    # Trasforma "Predator x2" in ["Predator", "Predator"]
    # Trasforma "Predator/Bear" in ["Predator", "Bear"]
    parts = re.split(r'[/,]', str(val))
    results = []
    for p in parts:
        p = p.strip()
        if ' x' in p:
            name, count = p.split(' x')
            results.extend([name.strip()] * int(count))
        else:
            results.append(p)
    return results

def parse_bonuses(val: str) -> Bonus:
    # Trasforma "6/1/0" in Bonus(appeal=6, conservation=1, reputation=0)
    try:
        parts = [int(x) for x in str(val).split('/')]
        return Bonus(appeal=parts[0], conservation=parts[1], reputation=parts[2])
    except:
        return Bonus()
    
import pandas as pd

# Carica il file Excel completo
file_path = "arknovaanimals_VM_v2.xlsx" # Assicurati che il nome sia corretto

# Legge tutto il file creando un dizionario di DataFrames
# Le chiavi del dizionario saranno i nomi dei fogli (es. "Animals", "Sponsors", ecc.)
xls = pd.read_excel(file_path, sheet_name=None)

df_animals = xls["Animals"]
df_sponsors = xls["Sponsors"]
df_conservation = xls["Conservation"]
df_scoring = xls["Final Scoring"]

print(f"Fogli trovati: {list(xls.keys())}")
print(f"Righe in Animals: {len(df_animals)}")

animal_cards = []

for _, row in df_animals.iterrows():
    # 1. Parsing Recinto (usa la funzione che abbiamo definito)
    enclosure_data = parse_enclosure_string(str(row["Enclosure size (Rock/Water)"]))
    
    # 2. Parsing Requisiti
    req_str = str(row["Reqs"])
    reqs = Requirements(
        partner_zoo="Partner zoo" in req_str,
        university="University" in req_str,
        reputation=int(re.search(r'Reputation (\d+)', req_str).group(1)) if "Reputation" in req_str else 0
    )
    
    # Parsing simboli (es: Asia x3)
    sym_matches = re.findall(r'(\w+)\s+x(\d+)', req_str)
    for sym, count in sym_matches:
        reqs.symbols[sym] = int(count)

    # 3. Parsing Tipi (usa la funzione definita prima)
    # Attenzione: assicurati che la colonna nel CSV si chiami esattamente "Type"
    types_list = parse_multi_type(str(row["Type"]))

    # 4. Creazione Oggetto
    card = AnimalCard(
        card_id=int(row["Card #"]),
        name=row["Animal Card Name"],
        latin_name=row["Animal Latin name"] if pd.notna(row["Animal Latin name"]) else None,
        cost=int(row["Cost"]),
        types=types_list,
        continents=str(row["Continent"]).split('/') if pd.notna(row["Continent"]) else [],
        enclosure=enclosure_data,
        requirements=reqs,
        abilities=[row["Ability"]] if pd.notna(row["Ability"]) else [],
        bonuses=parse_bonuses(str(row["Bonuses (A/C/R)"]))
    )
    animal_cards.append(card)

# Salviamo tutto in un file JSON per poterlo usare in seguito
import json
with open("animal_cards.json", "w") as f:
    json.dump([card.dict() for card in animal_cards], f, indent=4)