import streamlit as st
import asyncio
import os
import sys
from dotenv import load_dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

# Carica variabili d'ambiente
load_dotenv()

# Configurazione Pagina Streamlit
st.set_page_config(page_title="Ark Nova AI Assistant", page_icon="🐘", layout="centered")

st.title("🐘 Ark Nova AI Assistant")
st.markdown("""
Questa applicazione ti permette di interrogare le carte e il regolamento di **Ark Nova** 
usando un agente AI potenziato da MCP (Model Context Protocol).
""")

# --- Configurazione MCP e Agente ---
DB_URI = "postgresql://user:password@localhost:5433/db_destinazione"

llm_gemini = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", # o "gemini-1.5-pro" per analisi ancora più profonde
    temperature=0,
    vertexai=True,
    )

# Inizializziamo lo stato della chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Funzione per eseguire l'agente
async def get_ai_response(user_input):
    with open("db_map.md", "r") as f:
        db_map = f.read()
        
    try:

    
        client = MultiServerMCPClient(
        {
            "cards": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["mcp_ark.py"],
                "env": {**os.environ, "DB_URI": DB_URI}
                
            },
            "rules": {
                "transport": "stdio",
                "command": sys.executable,
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
            ("human", user_input)]

        agent = create_agent(
            llm_gemini,
            tools
        )
        
        system_prompt = f"""Sei un esperto di Ark Nova. Rispondi in italiano.
        Il database è in inglese. Mappa DB: {db_map}
        Quando filtri per nomi, regioni o categorie: usa confronti case-insensitive (ILIKE) e, se l'utente scrive in italiano, traduci in inglese o usa una condizione OR con entrambe le varianti.
        Per gli animali filtrati per continente, preferisci il tool get_animals_by_continent. Se devi scrivere SQL, ricorda che continents è un array JSON: usa jsonb_array_elements_text(continents::jsonb) con ILIKE 'Africa%' per includere anche valori come 'Africa x2'; non usare l'operatore jsonb ? per questi filtri perché richiede match esatto.
        Per gli animali filtrati per tipo, preferisci get_animals_by_type: types può contenere valori come 'Sea Animal 2'. Per sponsor filtrati per icona ottenuta, preferisci get_sponsors_by_icon: icons_gained può contenere valori combinati come '1 Herbivore + 1 Rock'.
        """
            
            # Prepariamo la cronologia per l'agente (opzionale, semplificato qui)
        messages = [("system", system_prompt)]
        for msg in st.session_state.messages:
            role = "human" if msg["role"] == "user" else "assistant"
            messages.append((role, msg["content"]))
        
        messages.append(("user", user_input))
        
        result = await agent.ainvoke({"messages": messages})
        return result["messages"][-1].content
    except Exception as e:
        return f"Errore: {str(e)}"

# Visualizzazione della cronologia
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input dell'utente
if prompt := st.chat_input("Chiedi qualcosa su Ark Nova..."):
    # Aggiungi messaggio utente
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Genera risposta dell'AI
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("🐘 *L'elefante sta pensando...*")
        
        # Eseguiamo la logica async in Streamlit
        response = asyncio.run(get_ai_response(prompt))
        
        message_placeholder.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

st.sidebar.info("Ark Nova RAG v1.0 - powered by LangChain & MCP")
