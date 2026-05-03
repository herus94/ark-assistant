from typing import List, Optional, Dict, Union
from pydantic import BaseModel, Field
import pandas as pd

from read_animal_cards import Requirements

# Modello migliorato
class SponsorCard(BaseModel):
    card_id: int
    name: str
    sponsor_strength: float # Nota: nel CSV hai 5.0, 4.0
    requirements: Optional[Requirements] = None
    icons_gained: List[str] = [] # Spesso sono liste di icone, non dizionari
    instant_bonus: Optional[str] = None
    continuing_bonus: Optional[str] = None
    # Qui usiamo una stringa o una struttura per gestire il caso "3/6 Research : 1/2 CP"
    end_game_bonus: Optional[str] = None 

class ConservationProjectCard(BaseModel):
    card_id: int
    name: str
    activity_required: str
    # Usiamo List[int] per gestire 5/4/3
    size_required: List[int] = [] 
    conservation_points: List[int] = []
    requirements_text: Optional[str] = None # Molti requisiti sono testuali

class FinalScoringCard(BaseModel):
    card_id: int
    name: str
    # 1/2/4/5 -> List[int]
    required_tiers: List[int] = []
    # 1/2/3/4 -> List[int]
    points_tiers: List[int] = []
    additional_details: Optional[str] = None
    
def parse_slash_list(val: str) -> List[int]:
    """Trasforma '1/2/3' in [1, 2, 3]"""
    if pd.isna(val) or val == "":
        return []
    try:
        # Pulisce eventuali spazi o caratteri strani
        clean_val = str(val).replace(' ', '')
        return [int(x) for x in clean_val.split('/') if x.isdigit()]
    except ValueError:
        return []

# Esempio di utilizzo nel loop
# tiers = parse_slash_list(row["# Required"])

# Carica il file Excel completo
file_path = "arknovaanimals_VM_v2.xlsx" # Assicurati che il nome sia corretto

# Legge tutto il file creando un dizionario di DataFrames
# Le chiavi del dizionario saranno i nomi dei fogli (es. "Animals", "Sponsors", ecc.)
xls = pd.read_excel(file_path, sheet_name=None)

df_sponsors = xls["Sponsors"]
df_conservation = xls["Conservation"]
df_scoring = xls["Final Scoring"]

sponsor_cards = []
conservation_projects_cards = []
final_scoring_cards = []

# --- Funzioni di Parsing Specifiche ---

def parse_sponsor_icons(val) -> List[str]:
    if pd.isna(val) or val == "":
        return []
    # Split per virgola e pulizia spazi
    return [i.strip() for i in str(val).split(',')]

# --- Loop di caricamento ---

# 1. Sponsor Cards
for _, row in df_sponsors.iterrows():
    # Nota: Requirement è complesso, lo teniamo come stringa nella Requirements class 
    # o potremmo estenderla in futuro. Qui passiamo None o un oggetto base.
    card = SponsorCard(
        card_id=int(row["Card #"]),
        name=row["Sponsor Card Name*"],
        sponsor_strength=float(row["Sponsor Strength to play"]) if pd.notna(row["Sponsor Strength to play"]) else 0.0,
        icons_gained=parse_sponsor_icons(row["Icons Gained"]),
        instant_bonus=str(row["Instant Bonus (yellow)"]) if pd.notna(row["Instant Bonus (yellow)"]) else None,
        continuing_bonus=str(row["Continuing Bonus (blue/lavender)"]) if pd.notna(row["Continuing Bonus (blue/lavender)"]) else None,
        end_game_bonus=str(row["End Game Conservation Points (brown)"]) if pd.notna(row["End Game Conservation Points (brown)"]) else None
    )
    sponsor_cards.append(card)

# 2. Conservation Project Cards
for _, row in df_conservation.iterrows():
    card = ConservationProjectCard(
        card_id=int(row["Card #"]),
        name=row["Conservation Project Card Name*"],
        activity_required=str(row["Activity Required"]),
        size_required=parse_slash_list(row["#/size Required"]),
        conservation_points=parse_slash_list(row["Conservation Points"]),
        requirements_text=str(row["Specific Requirements"]) if pd.notna(row["Specific Requirements"]) else None
    )
    conservation_projects_cards.append(card)

# 3. Final Scoring Cards
for _, row in df_scoring.iterrows():
    card = FinalScoringCard(
        card_id=int(row["Card #"]),
        name=row["Scoring Card Name*"],
        required_tiers=parse_slash_list(row["# Required"]),
        points_tiers=parse_slash_list(row["Conservation Points"]),
        additional_details=str(row["Additional Scoring Details"]) if pd.notna(row["Additional Scoring Details"]) else None
    )
    final_scoring_cards.append(card)

print(f"Caricate {len(sponsor_cards)} carte Sponsor, {len(conservation_projects_cards)} progetti, {len(final_scoring_cards)} carte scoring.")

# salviamo in JSON
import json
with open("sponsor_cards.json", "w") as f:
    json.dump([card.dict() for card in sponsor_cards], f, indent=2)
with open("conservation_projects_cards.json", "w") as f:
    json.dump([card.dict() for card in conservation_projects_cards], f, indent=2)
with open("final_scoring_cards.json", "w") as f:
    json.dump([card.dict() for card in final_scoring_cards], f, indent=2)