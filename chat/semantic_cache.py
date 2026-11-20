"""Cache semântico de dúvidas independentes; consultas ao balcão não são gravadas."""
import hashlib
import logging
import math
import os
import re
import threading
import time
import unicodedata
from pathlib import Path

from knowledge import KNOWLEDGE_VERSION

logger = logging.getLogger(__name__)


def normalize(text):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", text.lower())
                            if not unicodedata.combining(c)).split())


def topic(question):
    anchors = re.findall(r"\b(proporcao|extracao|acidez|amargor|moagem|temperatura|sensorial|docura)\b", normalize(question))
    return ":".join(sorted(set(anchors)))


def eligible(question, history):
    """Restrição conservadora: sem contexto, números, referências a registros ou negação."""
    text = normalize(question)
    if history or re.search(r"\d", text):
        return False
    if re.search(r"\b(nao|nunca|sem|exceto|menos|nenhum|meu|minha|esse|essa|este|esta|isso|ele|ela|aqui|hoje|agora|ontem|melhor|pior|media|ranking|id|catalogo|estoque|preco|registr\w*|degustac\w*|disponiv\w*|cadastr\w*|compare)\b", text):
        return False
    # Somente famílias conceituais revisadas; evita cache de cumprimentos e recusas.
    return bool(topic(question))


class SemanticCache:
    def __init__(self, model_name=None, path=None, threshold=None, ttl=None):
        self.model_name = model_name or os.getenv("CACHE_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        self.path = path or os.getenv("CACHE_PATH", "/app/data/cache")
        self.threshold = float(threshold if threshold is not None else os.getenv("CACHE_DISTANCE", "0.20"))
        self.ttl = int(ttl if ttl is not None else os.getenv("CACHE_TTL_SECONDS", "86400"))
        if not 0 <= self.threshold <= 2 or self.ttl <= 0:
            raise ValueError("Configuração de cache inválida.")
        self.model = self.collection = None
        self.state = "disabled" if os.getenv("CACHE_ENABLED", "true").lower() != "true" else "starting"
        self.lock = threading.Lock()

    def start(self):
        if self.state == "disabled":
            return
        try:
            os.environ.setdefault("USE_TF", "0")
            os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
            from sentence_transformers import SentenceTransformer
            import chromadb

            self.model = SentenceTransformer(self.model_name, device="cpu")
            Path(self.path).mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=self.path)
            suffix = hashlib.sha256((KNOWLEDGE_VERSION + self.model_name).encode()).hexdigest()[:16]
            self.collection = client.get_or_create_collection(
                name=f"cafeteria_{suffix}", embedding_function=None,
                configuration={"hnsw": {"space": "cosine"}},
            )
            self.state = "ready"
        except Exception:
            self.state = "unavailable"
            logger.warning("Cache semântico indisponível; o chat continuará com o LLM.", exc_info=False)

    def lookup(self, question, model):
        if self.state != "ready":
            return None
        try:
            with self.lock:
                if not self.collection.count():
                    return None
                vector = self.model.encode(question, normalize_embeddings=True).tolist()
                found = self.collection.query(query_embeddings=[vector], n_results=1,
                                              where={"$and": [{"model": model}, {"topic": topic(question)}]},
                                              include=["metadatas", "distances"])
                distances = (found.get("distances") or [[]])[0]
                entries = (found.get("metadatas") or [[]])[0]
                if not distances or not entries:
                    return None
                item, distance = entries[0], distances[0]
                if not math.isfinite(distance) or distance > self.threshold:
                    return None
                if time.time() - item["created_at"] >= self.ttl:
                    return None
                return {"answer": item["answer"], "distance": distance}
        except Exception:
            logger.warning("Falha na consulta ao cache; usando LLM.")
            return None

    def store(self, question, answer, model):
        if self.state != "ready" or not answer.strip():
            return False
        try:
            with self.lock:
                vector = self.model.encode(question, normalize_embeddings=True).tolist()
                identifier = hashlib.sha256((normalize(question) + model).encode()).hexdigest()
                self.collection.upsert(ids=[identifier], embeddings=[vector], documents=[question],
                                       metadatas=[{"answer": answer, "model": model, "topic": topic(question),
                                                   "created_at": time.time()}])
            return True
        except Exception:
            logger.warning("Falha na gravação do cache; resposta preservada.")
            return False
