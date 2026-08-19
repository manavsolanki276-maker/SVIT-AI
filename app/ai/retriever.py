from typing import List, Tuple, Dict, Any, Optional
from langchain_core.documents import Document

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
    top_k: int = 10
) -> List[Tuple[Document, float]]:
    """
    Searches ChromaDB following weighted source priorities:
    Iterates through sources ordered by weight (e.g. 1.0 -> 0.8 -> 0.3)
    and returns the first source match that yields hits.
    """
    if source_weights:
        # Sort sources descending by weight priority
        sorted_sources = sorted(source_weights, key=lambda x: x[1], reverse=True)
        
        for source_file, weight in sorted_sources:
            results = vector_store.similarity_search_with_score(
                query, 
                k=top_k, 
                filter={"source": source_file}
            )
            # Stop cascading as soon as a primary or secondary match yields context
            if results:
                print(f"🎯 Priority match found in: {source_file} (Weight: {weight})")
                return results

    # Targeted Fallback: Search general_faq.csv to prevent timetable or unmapped noise
    print("⚠️ Fallback: Searching general FAQ collection")
    fallback_results = vector_store.similarity_search_with_score(
        query, 
        k=top_k, 
        filter={"source": "general_faq.csv"}
    )

    if fallback_results:
        return fallback_results

    # Ultimate safety net if general_faq returns empty
    return vector_store.similarity_search_with_score(query, k=top_k)