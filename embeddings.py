import os

from langchain_core.embeddings import Embeddings


class LocalSentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def get_embeddings():
    provider = os.getenv("EMBEDDINGS_PROVIDER", "local").strip().lower()

    if provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key and not os.getenv("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = gemini_key

        return GoogleGenerativeAIEmbeddings(
            model=os.getenv("GOOGLE_EMBEDDING_MODEL", "models/text-embedding-004")
        )

    if provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"))

    if provider == "local":
        return LocalSentenceTransformerEmbeddings(
            os.getenv(
                "LOCAL_EMBEDDING_MODEL",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            )
        )

    raise ValueError(
        "EMBEDDINGS_PROVIDER non supportato. Usa 'local', 'google' oppure 'ollama'."
    )
