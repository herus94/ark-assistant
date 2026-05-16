from mcp.server.fastmcp import FastMCP
import pandas as pd
from sqlalchemy import create_engine, text
import datetime
from datetime import timedelta
import os
from dotenv import load_dotenv
import sys
import json

load_dotenv()
mcp = FastMCP("ARK NOVA MCP")

DB_URI = os.getenv("DB_URI") 

if not DB_URI:
    # Questo log apparirà nei log di Railway se la variabile è vuota
    print("ERRORE: Variabile DB_URI non trovata!", file=sys.stderr)

engine = create_engine(DB_URI)

import httpx
import time

# ─── DISCOVERY DATABASE ──────────────────────────────────────────────────────

CONTINENT_ALIASES = {
    "africa": "Africa",
    "europa": "Europe",
    "europe": "Europe",
    "asia": "Asia",
    "australia": "Australia",
    "americhe": "Americas",
    "america": "Americas",
    "americas": "Americas",
    "america del nord": "Americas",
    "america del sud": "Americas",
}

ANIMAL_TYPE_ALIASES = {
    "predatore": "Predator",
    "predatori": "Predator",
    "predator": "Predator",
    "orso": "Bear",
    "orsi": "Bear",
    "bear": "Bear",
    "erbivoro": "Herbivore",
    "erbivori": "Herbivore",
    "herbivore": "Herbivore",
    "primate": "Primate",
    "primati": "Primate",
    "rettile": "Reptile",
    "rettili": "Reptile",
    "reptile": "Reptile",
    "uccello": "Bird",
    "uccelli": "Bird",
    "bird": "Bird",
    "animale da fattoria": "Pet",
    "animali da fattoria": "Pet",
    "pet": "Pet",
    "animale marino": "Sea Animal",
    "animali marini": "Sea Animal",
    "sea animal": "Sea Animal",
}


def _normalize_continent(continent: str) -> str:
    return CONTINENT_ALIASES.get(continent.strip().lower(), continent.strip())


def _normalize_animal_type(animal_type: str) -> str:
    return ANIMAL_TYPE_ALIASES.get(animal_type.strip().lower(), animal_type.strip())

@mcp.tool()
def get_db_schemas():
    """
    Lista tutti gli schema disponibili nel database.
    Chiamare SEMPRE prima di execute_sql se non si conosce lo schema esatto della tabella.
    """
    result = pd.read_sql_query(text("""
        SELECT schema_name 
        FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        ORDER BY schema_name
    """), engine)
    return json.dumps(result["schema_name"].tolist())


@mcp.tool()
def get_db_tables(schema: str):
    """
    Lista tutte le tabelle e le colonne di uno schema specifico.
    Chiamare con il nome dello schema ottenuto da get_db_schemas.
    Restituisce per ogni tabella: nome tabella e lista colonne con tipo di dato.
    Usare per costruire query SQL corrette prima di chiamare execute_sql.
    """
    result = pd.read_sql_query(text("""
        SELECT 
            table_name,
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema = :schema
        ORDER BY table_name, ordinal_position
    """), engine, params={"schema": schema})

    if result.empty:
        return json.dumps({"nota": f"Nessuna tabella trovata nello schema '{schema}'"})

    tabelle = {}
    for _, row in result.iterrows():
        t = row["table_name"]
        if t not in tabelle:
            tabelle[t] = []
        tabelle[t].append({"colonna": row["column_name"], "tipo": row["data_type"]})

    output = []
    for nome_tabella, colonne in tabelle.items():
        output.append({
            "tabella": f"{schema}.{nome_tabella}",
            "colonne": colonne
        })

    return json.dumps(output)


# ─── ANIMALS HELPERS ─────────────────────────────────────────────────────────

@mcp.tool()
def get_animals_by_continent(continent: str, limit: int = 20, order_by: str = "cost", descending: bool = True):
    """
    Restituisce animali filtrati per continente, includendo icone multiple come 'Africa x2'.
    Usa questo tool per domande tipo: animali più costosi/economici di un continente.
    Parametri:
    - continent: nome continente in italiano o inglese (es. Africa, Europa, Americas)
    - limit: numero massimo di risultati
    - order_by: una tra cost, name, card_id
    - descending: True per ordine decrescente, False per crescente
    """
    continent = _normalize_continent(continent)
    order_by = order_by if order_by in {"cost", "name", "card_id"} else "cost"
    direction = "DESC" if descending else "ASC"
    limit = max(1, min(int(limit), 100))

    query = text(f"""
        SELECT card_id, name, cost, types, continents, enclosure, requirements, abilities, bonuses
        FROM animals
        WHERE EXISTS (
            SELECT 1
            FROM jsonb_array_elements_text(continents::jsonb) AS c(value)
            WHERE c.value ILIKE :continent_prefix
        )
        ORDER BY {order_by} {direction}, name ASC
        LIMIT :limit
    """)

    try:
        df = pd.read_sql_query(
            query,
            engine,
            params={"continent_prefix": f"{continent}%", "limit": limit},
        )
        if df.empty:
            return json.dumps({"nota": f"Nessun animale trovato per il continente '{continent}'."})
        return json.dumps(df.to_dict(orient="records"), default=str)
    except Exception as e:
        return json.dumps({"errore": str(e)})


@mcp.tool()
def get_animals_by_type(animal_type: str, limit: int = 20, order_by: str = "cost", descending: bool = True):
    """
    Restituisce animali filtrati per tipo, includendo valori con quantità come 'Sea Animal 2'.
    Usa questo tool per domande tipo: animali marini più costosi, rettili più economici, ecc.
    Parametri:
    - animal_type: tipo in italiano o inglese (es. Rettile, Predator, Sea Animal)
    - limit: numero massimo di risultati
    - order_by: una tra cost, name, card_id
    - descending: True per ordine decrescente, False per crescente
    """
    animal_type = _normalize_animal_type(animal_type)
    order_by = order_by if order_by in {"cost", "name", "card_id"} else "cost"
    direction = "DESC" if descending else "ASC"
    limit = max(1, min(int(limit), 100))

    query = text(f"""
        SELECT card_id, name, cost, types, continents, enclosure, requirements, abilities, bonuses
        FROM animals
        WHERE EXISTS (
            SELECT 1
            FROM jsonb_array_elements_text(types::jsonb) AS t(value)
            WHERE t.value ILIKE :type_prefix
        )
        ORDER BY {order_by} {direction}, name ASC
        LIMIT :limit
    """)

    try:
        df = pd.read_sql_query(
            query,
            engine,
            params={"type_prefix": f"{animal_type}%", "limit": limit},
        )
        if df.empty:
            return json.dumps({"nota": f"Nessun animale trovato per il tipo '{animal_type}'."})
        return json.dumps(df.to_dict(orient="records"), default=str)
    except Exception as e:
        return json.dumps({"errore": str(e)})


@mcp.tool()
def get_sponsors_by_icon(icon: str, limit: int = 20):
    """
    Restituisce sponsor filtrati per icone ottenute, includendo valori combinati come
    '1 Herbivore + 1 Rock' o quantità/plurali come '2 Rocks'.
    Usa questo tool per domande tipo: sponsor che danno icone acqua, roccia, ricerca, ecc.
    """
    icon = icon.strip()
    limit = max(1, min(int(limit), 100))

    query = text("""
        SELECT card_id, name, sponsor_strength, icons_gained, instant_bonus, continuing_bonus, end_game_bonus
        FROM sponsors
        WHERE EXISTS (
            SELECT 1
            FROM jsonb_array_elements_text(icons_gained::jsonb) AS i(value)
            WHERE i.value ILIKE :icon_match
        )
        ORDER BY card_id ASC
        LIMIT :limit
    """)

    try:
        df = pd.read_sql_query(
            query,
            engine,
            params={"icon_match": f"%{icon}%", "limit": limit},
        )
        if df.empty:
            return json.dumps({"nota": f"Nessuno sponsor trovato per l'icona '{icon}'."})
        return json.dumps(df.to_dict(orient="records"), default=str)
    except Exception as e:
        return json.dumps({"errore": str(e)})


# ─── EXECUTE SQL ─────────────────────────────────────────────────────────────

@mcp.tool()
def execute_sql(query: str):
    """
    Esegui una query SQL in sola lettura sul database.
    Usare per qualsiasi dato non coperto dai tool pre-calcolati.
    IMPORTANTE: usa sempre il nome completo schema.tabella (es. it_dev_log.t_l1_fatturato_cdc).
    Se non conosci lo schema o le colonne, chiama prima get_db_schemas e get_db_tables.
    Restituisce i risultati come lista di dizionari JSON.
    """
    # Blocca operazioni di scrittura
    query_upper = query.strip().upper()
    for keyword in ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER", "TRUNCATE"):
        if keyword in query_upper:
            return json.dumps({"errore": f"Operazione '{keyword}' non consentita — sola lettura."})

    try:
        df = pd.read_sql_query(text(query), engine)
        if df.empty:
            return json.dumps({"nota": "Query eseguita correttamente, nessun risultato trovato."})
        return json.dumps(df.to_dict(orient="records"), default=str)
    except Exception as e:
        return json.dumps({"errore": str(e), "suggerimento": "Verifica schema e nomi colonne con get_db_schemas e get_db_tables."})


if __name__ == "__main__":
    mcp.run()
