from llama_cloud import LlamaCloud
from dotenv import load_dotenv
import os

# Carichiamo le variabili d'ambiente dal file .env
load_dotenv()

client = LlamaCloud(api_key=os.getenv("LLAMA_CLOUD_API_KEY"))
file = client.files.create(file="regolamento/Glossario.pdf", purpose="parse")
result = client.parsing.parse(file_id=file.id, tier="agentic", version="latest", expand=["markdown_full"])

# Salviamo il risultato in un file markdown
with open("regolamento/Glossario.md", "w") as f:
    f.write(result.markdown_full)