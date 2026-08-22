import os
import math
from typing import List, Tuple, Any, Optional
from langchain_core.documents import Document

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHROMA_PERSIST_DIR = os.path.join(PROJECT_ROOT, "chroma_db")


class InMemoryFallbackVectorStore:
    """Fast, pure-Python in-memory vector store for serverless execution."""
    def __init__(self, documents: List[Document], embedding_function):
        self.documents = documents or []
        self.embedding_function = embedding_function
        self.doc_embeddings = []
        if self.documents and self.embedding_function:
            texts = [d.page_content for d in self.documents]
            try:
                self.doc_embeddings = self.embedding_function.embed_documents(texts)
            except Exception:
                self.doc_embeddings = [[0.0] * 384 for _ in texts]

    def similarity_search_with_score(self, query: str, k: int = 10, filter: Optional[dict] = None) -> List[Tuple[Document, float]]:
        if not self.documents:
            return []

        try:
            q_vec = self.embedding_function.embed_query(query)
        except Exception:
            q_vec = [0.0] * 384

        scored = []
        for doc, d_vec in zip(self.documents, self.doc_embeddings):
            if filter:
                matched = True
                for k_filt, v_filt in filter.items():
                    doc_val = doc.metadata.get(k_filt)
                    if isinstance(v_filt, dict) and "$in" in v_filt:
                        if doc_val not in v_filt["$in"]:
                            matched = False
                            break
                    elif doc_val != v_filt:
                        matched = False
                        break
                if not matched:
                    continue

            dot = sum(a * b for a, b in zip(q_vec, d_vec))
            score = max(0.0, 1.0 - dot)
            scored.append((doc, score))

        scored.sort(key=lambda x: x[1])
        return scored[:k]


def build_or_load_vector_store(documents: List[Document] = None, force_rebuild: bool = False) -> Any:
    """
    Initializes ChromaDB with automatic in-memory fallback for serverless environments.
    """
    from app.ai.embeddings import get_embedding_model
    embeddings = get_embedding_model()

    try:
        from langchain_community.vectorstores import Chroma
        persist_dir = CHROMA_PERSIST_DIR
        if (os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME')) and (force_rebuild or not os.path.exists(persist_dir)):
            persist_dir = os.path.join('/tmp', 'chroma_db')
        
        if not force_rebuild and os.path.exists(CHROMA_PERSIST_DIR) and len(os.listdir(CHROMA_PERSIST_DIR)) > 0:
            return Chroma(
                persist_directory=CHROMA_PERSIST_DIR,
                embedding_function=embeddings
            )
        elif documents:
            return Chroma.from_documents(
                documents=documents,
                embedding=embeddings,
                persist_directory=persist_dir
            )
    except Exception as e:
        pass

    if not documents:
        try:
            from app.ai.loader import load_csv_knowledge_base
            from app.ai.chunker import chunk_documents
            raw_docs = load_csv_knowledge_base()
            documents = chunk_documents(raw_docs)
        except Exception:
            documents = []

    return InMemoryFallbackVectorStore(documents, embeddings)