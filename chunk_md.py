import os

from dotenv import load_dotenv
from langchain_postgres.vectorstores import PGVector
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from sqlalchemy import create_engine, text

from embeddings import get_embeddings


load_dotenv()

connection_string = os.getenv("DB_URI") or os.getenv("DB_URL") or os.getenv("DATABASE_URL")
if not connection_string:
    raise RuntimeError(
        "Connessione DB non trovata. Imposta DB_URI, DB_URL o DATABASE_URL nel file .env."
    )

with create_engine(connection_string).begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]

# Step 1: split per header (preserva i metadati di sezione)
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on,
    strip_headers=False  # mantieni gli header nel testo del chunk
)

# Step 2: risplit i chunk troppo lunghi, con overlap per non perdere contesto
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,  # sovrapposizione per non spezzare concetti a metà
)

markdown_files = [
    ("regolamento/Ark_Nova.md", "regolamento"),
    ("regolamento/Glossario.md", "glossario"),
]

final_splits = []

for file_path, source in markdown_files:
    with open(file_path, "r") as f:
        markdown_document = f.read()

    md_header_splits = markdown_splitter.split_text(markdown_document)

    for doc in md_header_splits:
        doc.metadata["source"] = source
        doc.metadata["file_path"] = file_path

    file_splits = text_splitter.split_documents(md_header_splits)

    # Filtra chunk quasi vuoti (solo immagini markdown)
    file_splits = [
        doc for doc in file_splits
        if len(doc.page_content.strip()) > 100  # scarta chunk troppo corti
    ]

    final_splits.extend(file_splits)
    print(f"Chunk {source}: {len(file_splits)}")

print(f"Chunk totali: {len(final_splits)}")


# 1. Inizializzazione embeddings configurabile
embeddings = get_embeddings()

# 2. Caricamento su Postgres
# LangChain gestisce automaticamente l'estrazione del testo e l'invio dei vettori
vector_store = PGVector.from_documents(
    documents=final_splits,
    embedding=embeddings,
    collection_name="manuale_regole",
    connection=connection_string,
    pre_delete_collection=True,
    use_jsonb=True # Utile per mantenere i metadati Header 1, 2, 3 interrogabili
)

print("Regolamento e glossario caricati correttamente.")
