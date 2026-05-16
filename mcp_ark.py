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


ANIMAL_ABILITY_DETAILS_SQL = """
LEFT JOIN LATERAL (
    SELECT jsonb_agg(
        jsonb_strip_nulls(
            jsonb_build_object(
                'raw_name', ability_parts.raw_ability,
                'ability_name', ab.ability_name,
                'effect', ab.effect,
                'expansion', ab.expansion
            )
        )
        ORDER BY ability_parts.ordinality
    ) AS ability_details
    FROM (
        SELECT
            (ability_item.ability_index * 1000 + part.part_index) AS ordinality,
            trim(part.value) AS raw_ability,
            lower(
                regexp_replace(
                    regexp_replace(trim(part.value), '\\s*:\\s*', ': ', 'g'),
                    '\\s+',
                    ' ',
                    'g'
                )
            ) AS normalized_name
        FROM jsonb_array_elements_text(a.abilities::jsonb)
            WITH ORDINALITY AS ability_item(value, ability_index)
        CROSS JOIN LATERAL regexp_split_to_table(ability_item.value, '\\s*(?:/|\\n|,)\\s*')
            WITH ORDINALITY AS part(value, part_index)
        WHERE lower(trim(part.value)) <> 'none'
    ) AS ability_parts
    LEFT JOIN abilities ab ON ab.normalized_name = ability_parts.normalized_name
) AS ability_lookup ON TRUE
"""

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
        SELECT
            a.card_id,
            a.name,
            a.cost,
            a.types,
            a.continents,
            a.enclosure,
            a.requirements,
            a.abilities,
            COALESCE(ability_lookup.ability_details, '[]'::jsonb) AS ability_details,
            a.bonuses
        FROM animals a
        {ANIMAL_ABILITY_DETAILS_SQL}
        WHERE EXISTS (
            SELECT 1
            FROM jsonb_array_elements_text(a.continents::jsonb) AS c(value)
            WHERE c.value ILIKE :continent_prefix
        )
        ORDER BY a.{order_by} {direction}, a.name ASC
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
        SELECT
            a.card_id,
            a.name,
            a.cost,
            a.types,
            a.continents,
            a.enclosure,
            a.requirements,
            a.abilities,
            COALESCE(ability_lookup.ability_details, '[]'::jsonb) AS ability_details,
            a.bonuses
        FROM animals a
        {ANIMAL_ABILITY_DETAILS_SQL}
        WHERE EXISTS (
            SELECT 1
            FROM jsonb_array_elements_text(a.types::jsonb) AS t(value)
            WHERE t.value ILIKE :type_prefix
        )
        ORDER BY a.{order_by} {direction}, a.name ASC
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
    
# ─── TOOL DI RICERCA NEL REGOLAMENTO ─────────────────────────────────────────

@mcp.tool()
def search_rules(query: str, n_results: int = 10):
    """
    Cerca nel regolamento di Ark Nova per domande su meccaniche, fasi (Pausa Caffè) e icone.
    """
    import psycopg2
    from langchain_ollama import OllamaEmbeddings
    from langchain_postgres.vectorstores import PGVector

    n_results = max(1, min(int(n_results), 10))

    # 1. Ricerca vettoriale. Se Ollama non e' disponibile, non deve fallire
    # tutto il tool: passiamo al fallback keyword sotto.
    vector_results = []
    vector_error = None
    try:
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        
        vector_store = PGVector(
            collection_name="manuale_regole",
            connection=DB_URI,
            embeddings=embeddings,
            use_jsonb=True
        )

        vector_results = vector_store.similarity_search(query, k=n_results)
    except Exception as e:
        vector_error = str(e)

    vector_texts = {doc.page_content for doc in vector_results}

    # 2. Ricerca keyword come fallback (cerca le parole chiave direttamente nel testo)
    keyword_results = []
    try:
        conn = psycopg2.connect(DB_URI)
        cur = conn.cursor()
        
        # Prendi le parole significative dalla query (>3 caratteri)
        keywords = [w for w in query.split() if len(w) > 3]
        if not keywords:
            raise ValueError("Nessuna keyword significativa per la ricerca testuale.")

        like_clauses = " OR ".join([f"e.document ILIKE %s" for _ in keywords])
        params = [f"%{kw}%" for kw in keywords]
        
        cur.execute(f"""
            SELECT e.document, e.cmetadata
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'manuale_regole'
            AND ({like_clauses})
            LIMIT %s
        """, params + [n_results])
        
        for doc_text, metadata in cur.fetchall():
            if doc_text not in vector_texts:  # evita duplicati
                keyword_results.append({
                    "sezione": metadata.get("Header 2", "Generale") if metadata else "Generale",
                    "sotto_sezione": metadata.get("Header 3", "") if metadata else "",
                    "contenuto": doc_text,
                    "fonte": "keyword"
                })
        cur.close()
        conn.close()
    except Exception as e:
        pass  # fallback silenzioso se la keyword search fallisce

    # 3. Unisci i risultati (vector first, poi keyword)
    output = []
    for doc in vector_results:
        output.append({
            "sezione": doc.metadata.get("Header 2", "Generale"),
            "sotto_sezione": doc.metadata.get("Header 3", ""),
            "contenuto": doc.page_content,
            "fonte": "vettoriale"
        })
    output.extend(keyword_results)

    if vector_error:
        output.append({
            "sezione": "Nota tecnica",
            "sotto_sezione": "",
            "contenuto": (
                "La ricerca vettoriale non e' disponibile perche' Ollama non e' raggiungibile; "
                "sono stati usati solo eventuali risultati keyword."
            ),
            "fonte": "sistema"
        })

    if not output:
        return json.dumps({"nota": "Nessun frammento trovato.", "errore_vettoriale": vector_error}, ensure_ascii=False)

    return json.dumps(output, ensure_ascii=False)

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
