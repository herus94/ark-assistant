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
from langchain_openrouter import ChatOpenRouter

load_dotenv()
DB_URI = os.getenv("DB_URI", "postgresql://user:password@localhost:5433/db_destinazione")

# llm = ChatGoogleGenerativeAI(
#     model="gemini-2.5-flash", # o "gemini-1.5-pro" per analisi ancora più profonde
#     temperature=0,
#     vertexai=True,
#     )

llm = ChatOpenRouter(
    model="deepseek/deepseek-v4-flash",
    temperature=0,
    api_key=os.getenv("OPENROUTER_KEY")
)

# ─── AGENTE UNICO ────────────────────────────────────────────────────────────

async def agente_unico(domanda: str, db_map) -> str:


    client = MultiServerMCPClient(
        {
            "cards": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["mcp_ark.py"],
                "env": {**os.environ, "DB_URI": DB_URI}
                
            },
        }
        )
    
    tools = await client.get_tools()
    
    messaggi = [("system", f"""
        Sei un assistente esperto di Ark Nova. Rispondi in italiano e resta ancorato
        alle regole e ai dati disponibili: se non sei sicuro, dillo esplicitamente.
        
        Hai accesso a:
        1) Tool SQL per query libere sulle carte, con accesso a tutte le tabelle del database (animali, sponsor, progetti di conservazione, punteggi finali...)
        2) Tool search_rules per interrogare il regolamento e il glossario caricati nel database vettoriale.
        
        Mappa del Database: {db_map}
        IMPORTANTE: 
        Sii efficiente. Se i tool ti danno informazioni sufficienti, smetti di chiamarli e rispondi.
        Non inventare regole, componenti o termini che non appartengono ad Ark Nova.
        Evita in particolare concetti non presenti nel gioco come "passare" come azione standard,
        "tessera Inizio", "mulligan", "reazioni", "turni/round fissi", valuta "¥" o consigli basati
        su fasi numerate non previste dal regolamento.
        Per domande su regole, setup, fasi di gioco, termini, icone o strategia generale,
        usa search_rules prima di rispondere, salvo che la risposta sia già chiaramente
        presente nella conversazione.

        Quando filtri per nomi, regioni o categorie: usa confronti case-insensitive (ILIKE) e, se l'utente scrive in italiano, traduci in inglese o usa una condizione OR con entrambe le varianti (es. 'Europa' OR 'Europe').
        Per gli animali filtrati per continente, preferisci il tool get_animals_by_continent. Se devi scrivere SQL, ricorda che continents è un array JSON: usa jsonb_array_elements_text(continents::jsonb) con ILIKE 'Africa%' per includere anche valori come 'Africa x2'; non usare l'operatore jsonb ? per questi filtri perché richiede match esatto.
        Per gli animali filtrati per tipo, preferisci get_animals_by_type: types può contenere valori come 'Sea Animal 2'. Per sponsor filtrati per icona ottenuta, preferisci get_sponsors_by_icon: icons_gained può contenere valori combinati come '1 Herbivore + 1 Rock'.
        Quando restituisci elenchi di carte o dati comparabili, usa tabelle Markdown valide: una riga header, una riga separatrice con almeno tre trattini per colonna, e una riga per record. Non mettere testo extra dentro le righe della tabella.
        
        Se la domanda è strategica, distingui sempre tra regole certe ed euristiche.
        Per domande strategiche rispondi SEMPRE con questa struttura:
        1. Regole certe dal regolamento
        2. Euristiche consigliate
        3. Dipende dal contesto
        Non mescolare regole ed euristiche nello stesso punto.
        Non inventare una build generica. Se mancano mano iniziale, progetti base visibili,
        mappa e numero giocatori, dai solo consigli generali e segnala che dipendono dal contesto.
        Per l'early game, privilegia consigli solidi di Ark Nova: scegliere 4 carte iniziali giocabili,
        costruire recinti in funzione degli animali realmente giocabili, aumentare Attrazione per le entrate,
        usare Associazione per Università/Collaborazioni utili, e puntare a un primo Progetto di Conservazione
        quando la mano e le icone lo rendono realistico.
        Non essere troppo prolisso: rispondi in modo chiaro e sintetico, evitando di dilungarti su dettagli non richiesti. Se la domanda è semplice, rispondi in modo diretto senza aggiungere spiegazioni lunghe. Se la domanda è complessa, suddividi la risposta in punti chiari e concisi.
        Per consigli generali senza dati specifici della partita, dai una risposta breve: massimo 2 sezioni e 6-8 bullet totali.
        
        """),
        ("human", domanda)]

    agent = create_agent(
        llm,
        tools
    )
    
    # Passiamo il dizionario con la chiave "messages" come richiesto da LangGraph
    risultato = await agent.ainvoke({"messages": messaggi})
    
    # Restituiamo il contenuto dell'ultimo messaggio. Alcuni provider possono
    # chiudere una run dopo i tool con un messaggio finale vuoto: in quel caso
    # chiediamo al modello una sintesi finale senza ulteriori tool.
    risposta_finale = risultato["messages"][-1].content
    if isinstance(risposta_finale, str) and risposta_finale.strip():
        return risposta_finale

    fallback_messages = [
        *risultato["messages"],
        HumanMessage(content=(
            "Hai già ricevuto i risultati dei tool. Ora rispondi alla domanda "
            "dell'utente in italiano, in modo sintetico, senza chiamare altri tool. "
            "Se la domanda è strategica, usa la struttura richiesta: "
            "1. Regole certe dal regolamento; 2. Euristiche consigliate; "
            "3. Dipende dal contesto."
        )),
    ]
    fallback = await llm.ainvoke(fallback_messages)
    return fallback.content

# ─── MAIN ────────────────────────────────────────────────────────────────────

async def main():
    
    
    with open("db_map.md", "r") as f:
        db_map = f.read()
        
    domanda = f"""cosa succede durante la pausa caffè??"""

    risposta = await agente_unico(domanda, db_map)
    print("Risposta finale:")
    print(risposta)

if __name__ == "__main__":
    asyncio.run(main())
