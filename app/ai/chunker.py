from typing import List
from langchain_core.documents import Document

def chunk_documents(documents: List[Document], chunk_size: int = 450, chunk_overlap: int = 50) -> List[Document]:
    """
    Splits documents into smaller semantic chunks (300-500 characters).
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} text chunks from {len(documents)} original documents.")
    return chunks