import asyncio
import contextlib
import sys

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
import os
import json

from mcp import ClientSession, StdioServerParameters, stdio_client
from langchain_core.messages import ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_groq import ChatGroq

load_dotenv()
# Recuperiamo la URI dall'ambiente e puliamo
DB_URI = (os.getenv("DB_URI") or "").strip()

if not DB_URI:
    DB_URI = "postgresql://user:password@localhost:5433/db_destinazione"

# llm_gemini = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash", # o "gemini-1.5-pro" per analisi ancora più profonde
#     temperature=0,
#     vertexai=True,
#     )

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    streaming=True,
    api_key=os.getenv("GROQ_KEY")
)

# ─── AGENTE UNICO ────────────────────────────────────────────────────────────

async def agente_unico(domanda: str, db_map) -> str:


    client = MultiServerMCPClient(
        {
            "cards": {
                "transport": "stdio",
                "command": "python3",
                "args": ["mcp_ark.py"],
                "env": {**os.environ, "DB_URI": DB_URI}
                
            },
            "rules": {
                "transport": "stdio",
                "command": "python3",
                "args": ["-m", "graphify.serve", "graphify-out/graph.json"],
                "env": os.environ
            }
        }
        )
    
    tools = await client.get_tools()
    
    messaggi = [("system", f"""
        Sei un esperto del gioco da tavolo
        Ark Nova, e conosci tutte le carte del gioco.
        Il tuo compito è rispondere a domande sulle carte del gioco
        
        Hai accesso a:
        1) Tool SQL per query libere sulle carte, con accesso a tutte le tabelle del database (animali, sponsor, progetti di conservazione, punteggi finali...)
        2) Grafo del regolamento per domande sulle regole, fasi di gioco, icone e meccaniche.
        
        Mappa del Database: {db_map}
        IMPORTANTE: 
        Sii efficiente. Se i tool ti danno informazioni sufficienti, smetti di chiamarli e rispondi.

        Quando filtri per nomi, regioni o categorie: usa confronti case-insensitive (ILIKE) e, se l'utente scrive in italiano, traduci in inglese o usa una condizione OR con entrambe le varianti (es. 'Europa' OR 'Europe').
        
        """),
        ("human", domanda)]

    agent = create_agent(
        llm,
        tools
    )
    
    # Passiamo il dizionario con la chiave "messages" come richiesto da LangGraph
    risultato = await agent.ainvoke({"messages": messaggi})
    
    # Restituiamo il contenuto dell'ultimo messaggio (la risposta finale dell'AI)
    return risultato["messages"][-1].content

# ─── MAIN ────────────────────────────────────────────────────────────────────

async def main():
    
    
    with open("db_map.md", "r") as f:
        db_map = f.read()
        
    domanda = f"""quanti tipi di carte azioni esistono??"""

    risposta = await agente_unico(domanda, db_map)
    print("Risposta finale:")
    print(risposta)

if __name__ == "__main__":
    asyncio.run(main())