import os
from typing import List, Any
from langchain_core.documents import Document

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHROMA_PERSIST_DIR = os.path.join(PROJECT_ROOT, "chroma_db")

def build_or_load_vector_store(documents: List[Document] = None, force_rebuild: bool = False) -> Any:
    """
    Initializes ChromaDB. If persistent storage exists and force_rebuild is False,
    loads existing DB. Otherwise, indexes documents into a new vector database.
    """
    from langchain_community.vectorstores import Chroma
    from app.ai.embeddings import get_embedding_model
    embeddings = get_embedding_model()


    persist_dir = CHROMA_PERSIST_DIR
    if (os.environ.get('VERCEL') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME')) and (force_rebuild or not os.path.exists(persist_dir)):
        persist_dir = os.path.join('/tmp', 'chroma_db')
    
    if not force_rebuild and os.path.exists(CHROMA_PERSIST_DIR) and len(os.listdir(CHROMA_PERSIST_DIR)) > 0:
        print(f"Loading existing ChromaDB from disk: {CHROMA_PERSIST_DIR}...")
        vector_store = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embeddings
        )
    else:
        if not documents:
            raise ValueError("No documents provided to build the vector store.")
        print(f"Building new ChromaDB vector store at {persist_dir}...")
        vector_store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=persist_dir
        )
        print("ChromaDB build complete.")
        
    return vector_store