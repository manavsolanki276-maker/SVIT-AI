"""
app/ai/retriever.py
Optimized ChromaDB & In-Memory context retrieval with single-pass multi-source filtering,
admin document ingestion awareness, and LRU search caching.
"""
from typing import List, Tuple, Dict, Any, Optional
from langchain_core.documents import Document
from collections import OrderedDict

# LRU Cache for Vector Searches to make repeated or similar queries instant
_VECTOR_CACHE: OrderedDict[str, List[Tuple[Document, float]]] = OrderedDict()
_MAX_CACHE_SIZE = 128


def _get_from_cache(cache_key: str) -> Optional[List[Tuple[Document, float]]]:
    if cache_key in _VECTOR_CACHE:
        _VECTOR_CACHE.move_to_end(cache_key)
        return _VECTOR_CACHE[cache_key]
    return None


def _put_to_cache(cache_key: str, results: List[Tuple[Document, float]]) -> None:
    if len(_VECTOR_CACHE) >= _MAX_CACHE_SIZE:
        _VECTOR_CACHE.popitem(last=False)
    _VECTOR_CACHE[cache_key] = results


def clear_vector_cache() -> None:
    """Clears the in-memory retrieval vector cache upon dataset mutation."""
    _VECTOR_CACHE.clear()


def retrieve_context(vector_store, query: str, top_k: int = 10, filter: dict = None):
    """
    Retrieves relevant document chunks from the vector store with optional metadata filtering.
    """
    search_kwargs = {"k": top_k}
    if filter:
        search_kwargs["filter"] = filter

    results = vector_store.similarity_search_with_score(query, **search_kwargs)
    
    # Fallback: If filtered search returns no matches, retry with safety fallback
    if not results and filter:
        results = vector_store.similarity_search_with_score(
            query, 
            k=top_k, 
            filter={"source": "general_faq.csv"}
        )

    return results


def retrieve_by_module(vector_store, query: str, module: str, k: int = 5) -> List[Tuple[Document, float]]:
    """
    Strict page-specific RAG retrieval: Retrieves only document chunks matching the specified module/namespace.
    Guarantees zero cross-module contamination for scoped queries and automated verification tests.
    """
    if not vector_store or not module:
        return []

    # Map aliases if needed
    module_norm = str(module).strip().lower()
    if module_norm in ["admissions", "admission_info"]:
        module_norm = "admission"
    elif module_norm in ["buses", "transport", "transportation"]:
        module_norm = "bus"
    elif module_norm in ["academic", "syllabus_info"]:
        module_norm = "syllabus"
    elif module_norm in ["teachers", "teacher"]:
        module_norm = "faculty"

    # Search with filter
    results = []
    try:
        results = vector_store.similarity_search_with_score(
            query,
            k=k,
            filter={"rag_namespace": module_norm}
        )
    except Exception:
        pass

    if not results:
        try:
            results = vector_store.similarity_search_with_score(
                query,
                k=k,
                filter={"module": module_norm}
            )
        except Exception:
            pass

    # Strict isolation guarantee: ensure no chunk from a foreign namespace leaks through
    isolated_results = []
    for doc, score in results:
        doc_ns = doc.metadata.get("rag_namespace") or doc.metadata.get("module")
        if doc_ns and doc_ns.lower() == module_norm:
            isolated_results.append((doc, score))

    isolated_results.sort(key=lambda x: x[1])
    return isolated_results[:k]


def retrieve_context_tiered(
    vector_store, 
    query: str, 
    source_weights: List[Tuple[str, float]], 
    top_k: int = 8,
    target_module: Optional[str] = None
) -> List[Tuple[Document, float]]:
    """
    High-speed Single-Pass ChromaDB & In-Memory Retriever:
    1. Checks LRU memory cache
    2. Performs multi-source query for weighted sources
    3. Retrieves relevant admin-uploaded knowledge documents isolated by module/namespace
    4. De-duplicates and ranks top_k matches
    """
    cache_key = f"{query.strip().lower()}_{str(source_weights)}_{top_k}_{str(target_module)}"
    cached = _get_from_cache(cache_key)
    if cached is not None:
        return cached

    results = []

    # 1. Query weighted knowledge base sources if specified
    if source_weights:
        source_names = [s[0] for s in source_weights]
        try:
            if len(source_names) == 1:
                search_filter = {"source": source_names[0]}
            else:
                search_filter = {"source": {"$in": source_names}}

            routed_results = vector_store.similarity_search_with_score(
                query, 
                k=top_k, 
                filter=search_filter
            )
            if routed_results:
                results.extend(routed_results)
        except Exception:
            for source_file, _ in sorted(source_weights, key=lambda x: x[1], reverse=True):
                try:
                    r = vector_store.similarity_search_with_score(
                        query, 
                        k=top_k, 
                        filter={"source": source_file}
                    )
                    if r:
                        results.extend(r)
                except Exception:
                    pass

    # 2. Check for matching Admin Documents in the vector store (scoped by module if given)
    try:
        admin_filter = {"source_type": "admin_document"}
        if target_module:
            norm_mod = target_module.strip().lower()
            admin_filter["rag_namespace"] = norm_mod
        
        admin_doc_results = vector_store.similarity_search_with_score(
            query, 
            k=top_k, 
            filter=admin_filter
        )
        
        # If target_module was specified but no results with rag_namespace, try with module key
        if not admin_doc_results and target_module:
            admin_doc_results = vector_store.similarity_search_with_score(
                query,
                k=top_k,
                filter={"source_type": "admin_document", "module": norm_mod}
            )

        if admin_doc_results:
            for doc, score in admin_doc_results:
                # Active admin documents get priority boost over static historical CSVs
                results.append((doc, score * 0.7))
    except Exception:
        pass

    # 3. Targeted Fallback: Search general_faq.csv and full index if needed
    if not results:
        try:
            fallback_results = vector_store.similarity_search_with_score(
                query, 
                k=top_k, 
                filter={"source": "general_faq.csv"}
            )
            if fallback_results:
                results.extend(fallback_results)
        except Exception:
            pass

    if not results:
        try:
            results = vector_store.similarity_search_with_score(query, k=top_k)
        except Exception:
            results = []

    # 4. De-duplicate results and sort by distance score
    seen_contents = set()
    unique_results = []
    for doc, score in sorted(results, key=lambda x: x[1]):
        content_snippet = doc.page_content.strip()[:100]
        if content_snippet not in seen_contents:
            seen_contents.add(content_snippet)
            unique_results.append((doc, score))

    final_results = unique_results[:top_k]
    _put_to_cache(cache_key, final_results)
    return final_results