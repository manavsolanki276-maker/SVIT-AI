import os
import math
from typing import List, Tuple, Any, Optional, Dict
from langchain_core.documents import Document

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHROMA_PERSIST_DIR = os.path.join(PROJECT_ROOT, "chroma_db")


class InMemoryFallbackVectorStore:
    """Fast, pure-Python in-memory vector store for serverless and development execution."""
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

    def add_documents(self, documents: List[Document], ids: List[str] = None) -> List[str]:
        """Appends new documents and computes their embeddings."""
        if not documents:
            return []
        texts = [d.page_content for d in documents]
        try:
            new_embs = self.embedding_function.embed_documents(texts)
        except Exception:
            new_embs = [[0.0] * 384 for _ in texts]

        self.documents.extend(documents)
        self.doc_embeddings.extend(new_embs)
        return ids or [str(i) for i in range(len(self.documents) - len(documents), len(self.documents))]

    def delete(self, ids: Optional[List[str]] = None, where: Optional[dict] = None) -> None:
        """Deletes documents matching ID list or metadata filter."""
        new_docs = []
        new_embs = []
        for doc, emb in zip(self.documents, self.doc_embeddings):
            remove = False
            if where:
                matched = True
                for k, v in where.items():
                    if doc.metadata.get(k) != v:
                        matched = False
                        break
                if matched:
                    remove = True
            if not remove:
                new_docs.append(doc)
                new_embs.append(emb)

        self.documents = new_docs
        self.doc_embeddings = new_embs

    def get(self, where: Optional[dict] = None) -> Dict[str, Any]:
        """Retrieves documents matching metadata filter."""
        matched_docs = []
        for doc in self.documents:
            if where:
                matched = True
                for k, v in where.items():
                    if doc.metadata.get(k) != v:
                        matched = False
                        break
                if matched:
                    matched_docs.append(doc)
            else:
                matched_docs.append(doc)
        return {
            "documents": [d.page_content for d in matched_docs],
            "metadatas": [d.metadata for d in matched_docs]
        }

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
    Initializes ChromaDB with automatic in-memory fallback for fast testing and serverless environments.
    """
    from app.ai.embeddings import get_embedding_model
    embeddings = get_embedding_model()

    is_test = bool(os.environ.get('FAST_EMBEDDINGS') or os.environ.get('TEST_MODE') or os.environ.get('TESTING'))
    if not is_test:
        try:
            from flask import current_app
            if current_app and current_app.config.get('TESTING'):
                is_test = True
        except Exception:
            pass

    if is_test:
        if not documents:
            try:
                from app.ai.loader import load_csv_knowledge_base
                from app.ai.chunker import chunk_documents
                raw_docs = load_csv_knowledge_base()
                documents = chunk_documents(raw_docs)
            except Exception:
                documents = []
        return InMemoryFallbackVectorStore(documents, embeddings)

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
    except Exception:
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


def add_documents_to_vector_store(vector_store: Any, documents: List[Document]) -> Any:
    """Safely adds new documents to the vector store."""
    if not documents:
        return
    if hasattr(vector_store, 'add_documents'):
        return vector_store.add_documents(documents)
    elif hasattr(vector_store, '_collection'):
        # Raw Chroma collection
        from app.ai.embeddings import get_embedding_model
        emb_fn = get_embedding_model()
        texts = [d.page_content for d in documents]
        metadatas = [d.metadata for d in documents]
        embs = emb_fn.embed_documents(texts)
        ids = [f"{d.metadata.get('document_id', 'doc')}_{i}" for i, d in enumerate(documents)]
        vector_store._collection.add(
            documents=texts,
            embeddings=embs,
            metadatas=metadatas,
            ids=ids
        )


def delete_documents_from_vector_store(vector_store: Any, document_id: str) -> bool:
    """Safely removes all vector embeddings and chunks associated with document_id."""
    if not document_id:
        return False

    success = False
    # 1. Try vector_store.delete(where={"document_id": document_id})
    if hasattr(vector_store, 'delete'):
        try:
            vector_store.delete(where={"document_id": document_id})
            success = True
        except Exception:
            pass

    # 2. Try raw Chroma collection delete
    if hasattr(vector_store, '_collection'):
        try:
            vector_store._collection.delete(where={"document_id": document_id})
            success = True
        except Exception:
            pass

    return success