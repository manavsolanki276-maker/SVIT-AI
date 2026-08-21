"""
app/ai/retriever.py
Optimized ChromaDB context retrieval with single-pass multi-source filtering and in-memory LRU search cache.
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
    High-speed Single-Pass ChromaDB Retriever:
    1. Checks LRU memory cache
    2. Performs a single multi-source $in query if sources specified
    3. Falls back to general_faq only if needed
    """
    cache_key = f"{query.strip().lower()}_{str(source_weights)}_{top_k}"
    cached = _get_from_cache(cache_key)
    if cached is not None:
        return cached

    if source_weights:
        source_names = [s[0] for s in source_weights]
        
        try:
            if len(source_names) == 1:
                search_filter = {"source": source_names[0]}
            else:
                search_filter = {"source": {"$in": source_names}}

            results = vector_store.similarity_search_with_score(
                query, 
                k=top_k, 
                filter=search_filter
            )
            
            if results:
                _put_to_cache(cache_key, results)
                return results

        except Exception as e:
            # Fallback in case $in operator is unsupported by underlying vector store version
            for source_file, _ in sorted(source_weights, key=lambda x: x[1], reverse=True):
                try:
                    results = vector_store.similarity_search_with_score(
                        query, 
                        k=top_k, 
                        filter={"source": source_file}
                    )
                    if results:
                        _put_to_cache(cache_key, results)
                        return results
                except Exception:
                    pass

    # Targeted Fallback: Search general_faq.csv
    try:
        fallback_results = vector_store.similarity_search_with_score(
            query, 
            k=top_k, 
            filter={"source": "general_faq.csv"}
        )
        if fallback_results:
            _put_to_cache(cache_key, fallback_results)
            return fallback_results
    except Exception:
        pass

    # Ultimate safety net
    final_results = vector_store.similarity_search_with_score(query, k=top_k)
    _put_to_cache(cache_key, final_results)
    return final_results