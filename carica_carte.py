import json
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, ARRAY
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()
# Connessione al tuo container Postgres
#DB_URL = "postgresql://user:password@localhost:5433/db_destinazione"
DB_URL = os.getenv("DB_URI")
engine = create_engine(DB_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

# --- Definizione Modelli ---
class Animal(Base):
    __tablename__ = 'animals'
    card_id = Column(Integer, primary_key=True)
    name = Column(String)
    latin_name = Column(String)
    cost = Column(Integer)
    types = Column(JSON)
    continents = Column(JSON)
    enclosure = Column(JSON)
    requirements = Column(JSON)
    abilities = Column(JSON)
    bonuses = Column(JSON)

class Sponsor(Base):
    __tablename__ = 'sponsors'
    card_id = Column(Integer, primary_key=True)
    name = Column(String)
    sponsor_strength = Column(Float)
    requirements = Column(JSON)
    icons_gained = Column(JSON)
    instant_bonus = Column(String)
    continuing_bonus = Column(String)
    end_game_bonus = Column(String)

class Conservation(Base):
    __tablename__ = 'conservation_projects'
    card_id = Column(Integer, primary_key=True)
    name = Column(String)
    activity_required = Column(String)
    size_required = Column(JSON)
    conservation_points = Column(JSON)
    requirements_text = Column(String)

class Scoring(Base):
    __tablename__ = 'final_scoring'
    card_id = Column(Integer, primary_key=True)
    name = Column(String)
    required_tiers = Column(JSON)
    points_tiers = Column(JSON)
    additional_details = Column(String)

# --- Creazione Tabelle ---
Base.metadata.create_all(engine)

# --- Funzione Ingestion ---
def ingest_json(filename, model_class):
    with open(filename, 'r') as f:
        data = json.load(f)
        for entry in data:
            # Creiamo l'oggetto DB direttamente dal dict del JSON
            # Nota: assicura che le chiavi del JSON corrispondano ai nomi colonna
            record = model_class(**entry)
            session.merge(record) # 'merge' inserisce o aggiorna se ID esiste
    session.commit()
    print(f"Ingestione di {filename} completata.")

if __name__ == "__main__":
    ingest_json("animal_cards.json", Animal)
    ingest_json("sponsor_cards.json", Sponsor)
    ingest_json("conservation_projects_cards.json", Conservation)
    ingest_json("final_scoring_cards.json", Scoring)