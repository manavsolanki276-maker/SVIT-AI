import os
from typing import List
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from app.ai.embeddings import get_embedding_model

CHROMA_PERSIST_DIR = "chroma_db"

def build_or_load_vector_store(documents: List[Document] = None, force_rebuild: bool = False) -> Chroma:
    """
    Initializes ChromaDB. If persistent storage exists and force_rebuild is False,
    loads existing DB. Otherwise, indexes documents into a new vector database.
    """
    embeddings = get_embedding_model()
    
    if not force_rebuild and os.path.exists(CHROMA_PERSIST_DIR) and len(os.listdir(CHROMA_PERSIST_DIR)) > 0:
        print("Loading existing ChromaDB from disk...")
        vector_store = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embeddings
        )
    else:
        if not documents:
            raise ValueError("No documents provided to build the vector store.")
        print("Building new ChromaDB vector store...")
        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )
        print("ChromaDB build complete and saved to disk.")
        
    return vector_store