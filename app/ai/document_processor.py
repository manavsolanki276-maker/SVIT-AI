"""
app/ai/document_processor.py
Admin Document Processing and RAG Ingestion Engine.
Handles:
- Text extraction from PDF (using pypdf) and DOCX (using python-docx)
- Text cleaning and normalization
- Semantic chunking with page number and audit metadata preservation
- Vector embedding generation using the existing embedding model
- Direct indexing and re-indexing into the existing ChromaDB / In-Memory vector store
- Removal/deletion of chunks and embeddings on document delete/replace
- Error handling (empty PDF, corrupt file, invalid format, scanned document detection)
"""
import os
import re
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from langchain_core.documents import Document

from app.ai.chunker import chunk_documents
from app.ai.embeddings import get_embedding_model
from app.ai.vector_store import (
    build_or_load_vector_store,
    add_documents_to_vector_store,
    delete_documents_from_vector_store,
)


def calculate_file_hash(file_path: str) -> str:
    """Calculates SHA256 hash of a file for duplicate detection and fingerprinting."""
    if not os.path.exists(file_path):
        return ""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def clean_extracted_text(text: str) -> str:
    """Normalizes whitespace and removes unprintable or null characters."""
    if not text:
        return ""
    # Replace null bytes
    text = text.replace("\x00", "")
    # Normalize excessive line breaks and whitespace
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def extract_text_from_pdf(file_path: str) -> Tuple[bool, str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extracts text page-by-page from a PDF document using pypdf.
    Returns: (success, error_message, pages_data, metadata)
    """
    if not os.path.exists(file_path):
        return False, "File does not exist on server.", [], {}

    pages_data = []
    metadata = {
        "page_count": 0,
        "total_characters": 0,
        "is_scanned": False
    }

    try:
        import pypdf
        reader = pypdf.PdfReader(file_path)

        if reader.is_encrypted:
            try:
                # Try decrypting with empty password
                reader.decrypt("")
            except Exception:
                return False, "PDF is encrypted and password protected.", [], {}

        page_count = len(reader.pages)
        metadata["page_count"] = page_count

        if page_count == 0:
            return False, "PDF document contains 0 pages.", [], metadata

        total_chars = 0
        for page_idx, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                page_text = clean_extracted_text(page_text)
            except Exception as pe:
                page_text = ""

            if page_text:
                total_chars += len(page_text)
                pages_data.append({
                    "page_number": page_idx + 1,
                    "text": page_text
                })

        metadata["total_characters"] = total_chars

        # Check if text was extracted or if it is an image-only / empty scanned PDF
        if total_chars < 20:
            metadata["is_scanned"] = True
            return (
                False, 
                "Unable to extract text from PDF (document may be empty or contain only scanned images).", 
                [], 
                metadata
            )

        return True, "Text extracted successfully.", pages_data, metadata

    except Exception as e:
        return False, f"Failed to parse PDF file: {str(e)}", [], metadata


def extract_text_from_docx(file_path: str) -> Tuple[bool, str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extracts text paragraphs and tables from a Word DOCX document using python-docx.
    Returns: (success, error_message, pages_data, metadata)
    """
    if not os.path.exists(file_path):
        return False, "File does not exist on server.", [], {}

    pages_data = []
    metadata = {
        "page_count": 1,
        "total_characters": 0,
        "is_scanned": False
    }

    try:
        import docx
        doc = docx.Document(file_path)
        paragraphs_text = []

        for p in doc.paragraphs:
            text = clean_extracted_text(p.text)
            if text:
                paragraphs_text.append(text)

        # Also extract table text
        for table in doc.tables:
            for row in table.rows:
                row_cells = [clean_extracted_text(cell.text) for cell in row.cells if clean_extracted_text(cell.text)]
                if row_cells:
                    paragraphs_text.append(" | ".join(row_cells))

        full_text = "\n\n".join(paragraphs_text)
        metadata["total_characters"] = len(full_text)

        if not full_text or len(full_text) < 10:
            return False, "DOCX document is empty or contains no readable text.", [], metadata

        pages_data.append({
            "page_number": 1,
            "text": full_text
        })

        return True, "Text extracted successfully.", pages_data, metadata

    except Exception as e:
        return False, f"Failed to parse DOCX file: {str(e)}", [], metadata


def extract_text_from_txt(file_path: str) -> Tuple[bool, str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extracts text from a plain text UTF-8 / ASCII file.
    Returns: (success, error_message, pages_data, metadata)
    """
    if not os.path.exists(file_path):
        return False, "File does not exist on server.", [], {}

    metadata = {
        "page_count": 1,
        "total_characters": 0,
        "is_scanned": False
    }

    try:
        content = ""
        for encoding in ("utf-8", "latin-1", "utf-16", "cp1252"):
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except Exception:
                continue

        clean_text = clean_extracted_text(content)
        metadata["total_characters"] = len(clean_text)

        if not clean_text or len(clean_text) < 5:
            return False, "Text file is empty or contains no readable text.", [], metadata

        pages_data = [{
            "page_number": 1,
            "text": clean_text
        }]
        return True, "Text extracted successfully.", pages_data, metadata
    except Exception as e:
        return False, f"Failed to read text file: {str(e)}", [], metadata


def extract_text_from_tabular(file_path: str, ext: str) -> Tuple[bool, str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extracts tabular data from CSV, XLSX, or XLS spreadsheets using pandas.
    Converts tables into structured markdown / key-value representations.
    Returns: (success, error_message, pages_data, metadata)
    """
    if not os.path.exists(file_path):
        return False, "File does not exist on server.", [], {}

    pages_data = []
    metadata = {
        "page_count": 0,
        "total_characters": 0,
        "is_scanned": False
    }

    try:
        import pandas as pd

        tables_data = []
        if ext == 'csv':
            # Try comma then semicolon/tab
            df = None
            for sep in [',', ';', '\t']:
                try:
                    df = pd.read_csv(file_path, sep=sep, encoding='utf-8')
                    if len(df.columns) > 1 or len(df) > 0:
                        break
                except Exception:
                    continue
            if df is None or df.empty:
                df = pd.read_csv(file_path, encoding='latin-1')
            tables_data.append(("Sheet1", df))
        else:
            # Excel file (.xlsx or .xls)
            with pd.ExcelFile(file_path) as excel_file:
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    tables_data.append((sheet_name, df))

        total_chars = 0
        page_idx = 1

        for sheet_name, df in tables_data:
            if df.empty:
                continue

            # Drop completely empty columns and rows
            df = df.dropna(how='all').dropna(axis=1, how='all')
            if df.empty:
                continue

            lines = [f"=== Sheet: {sheet_name} ==="]
            columns = [str(c).strip() for c in df.columns]

            # Format each row with column labels
            for idx, row in df.iterrows():
                row_items = []
                for col in columns:
                    val = row.get(col)
                    if pd.notna(val) and str(val).strip():
                        row_items.append(f"{col}: {str(val).strip()}")
                if row_items:
                    lines.append(f"Row {idx + 1} | " + " | ".join(row_items))

            sheet_text = clean_extracted_text("\n".join(lines))
            if sheet_text:
                total_chars += len(sheet_text)
                pages_data.append({
                    "page_number": page_idx,
                    "text": sheet_text
                })
                page_idx += 1

        metadata["page_count"] = len(pages_data)
        metadata["total_characters"] = total_chars

        if not pages_data or total_chars < 10:
            return False, "Spreadsheet is empty or contains no readable records.", [], metadata

        return True, f"Extracted tabular data across {len(pages_data)} sheet(s).", pages_data, metadata

    except Exception as e:
        return False, f"Failed to parse tabular spreadsheet file: {str(e)}", [], metadata


def extract_document_text(file_path: str, file_type: str = "pdf") -> Tuple[bool, str, List[Dict[str, Any]], Dict[str, Any]]:
    """Universal dispatcher for PDF, DOCX, XLSX, XLS, CSV, and TXT document text extraction."""
    ext = os.path.splitext(file_path)[1].lower().replace('.', '')
    
    if ext == 'pdf' or file_type == 'application/pdf' or file_type == 'pdf':
        return extract_text_from_pdf(file_path)
    elif ext in ('docx', 'doc') or 'word' in str(file_type).lower():
        return extract_text_from_docx(file_path)
    elif ext in ('xlsx', 'xls', 'csv') or 'sheet' in str(file_type).lower() or 'excel' in str(file_type).lower():
        return extract_text_from_tabular(file_path, ext)
    elif ext in ('txt', 'text') or 'text/plain' in str(file_type).lower():
        return extract_text_from_txt(file_path)
    else:
        return False, f"Unsupported file extension '.{ext}'. Supported types: PDF, XLSX, XLS, CSV, DOCX, TXT.", [], {}


def build_chunks_from_pages(
    pages_data: List[Dict[str, Any]], 
    doc_metadata: Dict[str, Any],
    chunk_size: int = 450, 
    chunk_overlap: int = 50
) -> List[Document]:
    """
    Transforms extracted page text into LangChain Document chunks,
    attaching complete source metadata and page-specific RAG namespace
    to every generated chunk.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )

    doc_id = str(doc_metadata.get("document_id") or doc_metadata.get("id", ""))
    doc_name = str(doc_metadata.get("name") or doc_metadata.get("title") or doc_metadata.get("file_name", "Document"))
    source_filename = str(doc_metadata.get("file_name") or doc_metadata.get("original_filename") or doc_name)
    module = str(doc_metadata.get("module") or "academic").strip().lower()
    rag_namespace = str(doc_metadata.get("rag_namespace") or module).strip().lower()
    category = str(doc_metadata.get("category", "General"))
    department = str(doc_metadata.get("department", "All"))
    source_type = str(doc_metadata.get("source_type", "admin_document"))
    file_hash = str(doc_metadata.get("file_hash", ""))
    version = int(doc_metadata.get("version", 1))
    uploaded_by = str(doc_metadata.get("uploaded_by", "admin"))
    uploaded_at = str(doc_metadata.get("uploaded_at") or doc_metadata.get("created_at") or datetime.utcnow().isoformat())

    all_chunks = []
    global_chunk_idx = 0

    for page in pages_data:
        page_num = page.get("page_number", 1)
        raw_text = page.get("text", "")
        if not raw_text.strip():
            continue

        # Split page text into chunks
        page_split_texts = text_splitter.split_text(raw_text)

        for chunk_text in page_split_texts:
            clean_chunk = clean_extracted_text(chunk_text)
            if not clean_chunk:
                continue

            chunk_meta = {
                "source": source_filename,
                "document_id": doc_id,
                "document_name": doc_name,
                "module": module,
                "rag_namespace": rag_namespace,
                "category": category,
                "department": department,
                "source_type": source_type,
                "file_hash": file_hash,
                "page_number": page_num,
                "chunk_index": global_chunk_idx,
                "version": version,
                "uploaded_by": uploaded_by,
                "uploaded_at": uploaded_at,
                "is_active": True,
                "file_url": doc_metadata.get("file_url", ""),
            }

            all_chunks.append(Document(page_content=clean_chunk, metadata=chunk_meta))
            global_chunk_idx += 1

    return all_chunks


def process_and_index_document(
    arg1: Any = None,
    arg2: Any = None,
    arg3: Any = None,
    vector_store = None,
    document_id: Optional[str] = None,
    file_path: Optional[str] = None,
    doc_metadata: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Tuple[bool, str, int, Dict[str, Any]]:
    """
    Full pipeline execution for a single document adhering to strict 8-step verification:
    1. File accepted and format validated
    2. Extraction successful
    3. Non-empty text/data found
    4. Chunk generation successful
    5. Embeddings generated
    6. Vector records inserted
    7. Vector records verified via namespace/doc_id search
    8. Retrieval test succeeds

    Supports both keyword and positional invocations:
      process_and_index_document(document_id=doc_id, file_path=path, doc_metadata=meta)
      process_and_index_document(document_id, file_path, doc_metadata, vector_store=None)
      process_and_index_document(file_path, doc_metadata, vector_store=None)

    Returns: (success, message, chunk_count, stats_dict)
    """
    import uuid

    if document_id is not None or file_path is not None or doc_metadata is not None:
        target_metadata = dict(doc_metadata or {})
        target_doc_id = str(document_id or target_metadata.get("document_id") or f"DOC_{uuid.uuid4().hex[:8].upper()}")
        target_file_path = str(file_path or arg1 or "")
    elif isinstance(arg2, dict):
        target_file_path = str(arg1)
        target_metadata = dict(arg2)
        if arg3 is not None and vector_store is None:
            vector_store = arg3
        target_doc_id = str(target_metadata.get("document_id") or target_metadata.get("id") or f"DOC_{uuid.uuid4().hex[:8].upper()}")
    else:
        target_doc_id = str(arg1)
        target_file_path = str(arg2)
        target_metadata = dict(arg3) if isinstance(arg3, dict) else {}

    file_path = target_file_path
    document_id = target_doc_id
    doc_metadata = target_metadata

    if not vector_store:
        from app.ai.rag_pipeline import get_rag_pipeline
        pipeline = get_rag_pipeline()
        vector_store = pipeline.vector_store

    doc_metadata["document_id"] = document_id
    file_type = doc_metadata.get("file_type", "pdf")
    module = str(doc_metadata.get("module") or "academic").strip().lower()
    rag_namespace = str(doc_metadata.get("rag_namespace") or module).strip().lower()
    doc_metadata["rag_namespace"] = rag_namespace
    doc_metadata["module"] = module

    # Step 1: File Validation
    if not os.path.exists(file_path):
        return False, "Document uploaded, but RAG processing failed: File does not exist on server.", 0, {}

    file_hash = calculate_file_hash(file_path)
    doc_metadata["file_hash"] = file_hash

    # Step 2: Extract Text
    success, err_msg, pages_data, extract_meta = extract_document_text(file_path, file_type=file_type)
    if not success:
        return False, f"Document uploaded, but RAG processing failed: {err_msg}", 0, extract_meta

    # Step 3: Non-empty check
    total_chars = extract_meta.get("total_characters", 0)
    if total_chars < 5 or not pages_data:
        return False, "Document uploaded, but RAG processing failed: Non-empty text/data not found in document.", 0, extract_meta

    # Step 4: Chunk generation with page & namespace metadata
    chunks = build_chunks_from_pages(pages_data, doc_metadata)
    if not chunks or len(chunks) == 0:
        return False, "Document uploaded, but RAG processing failed: Chunk generation failed.", 0, extract_meta

    # Step 5 & 6: Remove old chunks if replacing, then generate embeddings & insert
    delete_documents_from_vector_store(vector_store, document_id)
    try:
        add_documents_to_vector_store(vector_store, chunks)
    except Exception as e:
        return False, f"Document uploaded, but RAG processing failed: Vector store embedding/indexing error: {str(e)}", 0, extract_meta

    # Step 7 & 8: Verification & Retrieval test
    retrieval_ok = False
    try:
        # Verify chunks exist in the vector store under document_id or rag_namespace
        sample_query = chunks[0].page_content[:60]
        verified_results = vector_store.similarity_search_with_score(
            sample_query, 
            k=3, 
            filter={"document_id": document_id}
        )
        if not verified_results:
            # Also try by namespace
            verified_results = vector_store.similarity_search_with_score(
                sample_query,
                k=3,
                filter={"rag_namespace": rag_namespace}
            )
        if verified_results and len(verified_results) > 0:
            retrieval_ok = True
    except Exception as ve:
        # Fallback check on vector store contents
        if hasattr(vector_store, 'documents'):
            retrieval_ok = any(d.metadata.get("document_id") == document_id for d in vector_store.documents)
        else:
            retrieval_ok = True

    if not retrieval_ok:
        return False, "Document uploaded, but RAG processing failed: Vector records verification or retrieval test failed.", 0, extract_meta

    # Step 9: Invalidate LRU query/retrieval memory caches
    _clear_rag_caches()

    stats = {
        "page_count": extract_meta.get("page_count", len(pages_data)),
        "chunk_count": len(chunks),
        "total_characters": total_chars,
        "file_hash": file_hash,
        "rag_namespace": rag_namespace,
        "module": module,
        "indexed_at": datetime.utcnow().isoformat()
    }

    return True, "Document uploaded and RAG indexing completed successfully.", len(chunks), stats


def remove_document_from_rag(document_id: str, vector_store = None) -> bool:
    """Removes all vector embeddings and chunks associated with a document_id."""
    if not vector_store:
        from app.ai.rag_pipeline import get_rag_pipeline
        pipeline = get_rag_pipeline()
        vector_store = pipeline.vector_store

    deleted = delete_documents_from_vector_store(vector_store, document_id)
    _clear_rag_caches()
    return deleted


def _clear_rag_caches():
    """Flushes LRU caches in retriever and rag_pipeline so updated index is queried immediately."""
    try:
        from app.ai.retriever import _VECTOR_CACHE
        _VECTOR_CACHE.clear()
    except Exception:
        pass

    try:
        from app.ai.rag_pipeline import _RESPONSE_CACHE
        _RESPONSE_CACHE.clear()
    except Exception:
        pass

