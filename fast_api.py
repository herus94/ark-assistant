# main.py (FastAPI)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from ark_rag_v2 import agente_unico

app = FastAPI(title="Ark Nova AI Assistant API")

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    question: str

with open("db_map.md", "r") as f:
    db_map = f.read()

@app.get("/")
async def read_index():
    return FileResponse("index.html")

@app.post("/chat")
async def chat(query: Query):
    # Qui inserisci la logica dell'agente che abbiamo scritto
    risposta = await agente_unico(query.question, db_map)
    return {"answer": risposta}