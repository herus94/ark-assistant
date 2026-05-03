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

# Recuperiamo la URI dall'ambiente
DB_URI = os.getenv("DB_URI", "postgresql://user:password@localhost:5433/db_destinazione")

print(f"DEBUG: Using DB_URI starting with: {DB_URI.split('@')[-1] if '@' in DB_URI else DB_URI}", file=sys.stderr)

# Railway e molti servizi cloud richiedono 'postgresql+psycopg2://'
if DB_URI.startswith("postgresql://"):
    DB_URI = DB_URI.replace("postgresql://", "postgresql+psycopg2://", 1)

# Se non siamo in locale (non contiene localhost o 127.0.0.1), forziamo SSL
is_local = "localhost" in DB_URI or "127.0.0.1" in DB_URI
if not is_local:
    if "sslmode" not in DB_URI:
        separator = "&" if "?" in DB_URI else "?"
        DB_URI += f"{separator}sslmode=require"
    print("DEBUG: SSL mode enabled for remote connection", file=sys.stderr)
else:
    print("DEBUG: Local connection detected, skipping SSL force", file=sys.stderr)

engine = create_engine(DB_URI)

import httpx
import time

# ─── DISCOVERY DATABASE ──────────────────────────────────────────────────────

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

