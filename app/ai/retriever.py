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


def retrieve_context_tiered(
    vector_store, 
    query: str, 
    source_weights: List[Tuple[str, float]], 
    top_k: int = 8
) -> List[Tuple[Document, float]]:
    """
    High-speed Single-Pass ChromaDB & In-Memory Retriever:
    1. Checks LRU memory cache
    2. Performs multi-source query for weighted sources
    3. Retrieves relevant admin-uploaded knowledge documents
    4. De-duplicates and ranks top_k matches
    """
    cache_key = f"{query.strip().lower()}_{str(source_weights)}_{top_k}"
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

    # 2. Check for matching Admin Documents in the vector store
    try:
        admin_doc_results = vector_store.similarity_search_with_score(
            query, 
            k=top_k, 
            filter={"source_type": "admin_document"}
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