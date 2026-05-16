from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

with open("regolamento/Ark_Nova.md", "r") as f:
    markdown_document = f.read()

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
md_header_splits = markdown_splitter.split_text(markdown_document)

# Step 2: risplit i chunk troppo lunghi, con overlap per non perdere contesto
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,  # sovrapposizione per non spezzare concetti a metà
)
final_splits = text_splitter.split_documents(md_header_splits)

# Filtra chunk quasi vuoti (solo immagini markdown)
final_splits = [
    doc for doc in final_splits 
    if len(doc.page_content.strip()) > 100  # scarta chunk troppo corti
]

print(f"Chunk totali: {len(final_splits)}")


from langchain_ollama import OllamaEmbeddings
from langchain_postgres.vectorstores import PGVector

# 1. Inizializzazione del modello locale (768 dimensioni)
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# 2. Stringa di connessione (modifica con i tuoi parametri)
connection_string = "postgresql://user:password@localhost:5433/db_destinazione"

# 3. Caricamento su Postgres
# LangChain gestisce automaticamente l'estrazione del testo e l'invio dei vettori
vector_store = PGVector.from_documents(
    documents=md_header_splits,
    embedding=embeddings,
    collection_name="manuale_regole",
    connection=connection_string,
    use_jsonb=True # Utile per mantenere i metadati Header 1, 2, 3 interrogabili
)

print("Regolamento caricato correttamente. Ora l'AI può 'ragionare' sulle regole!")