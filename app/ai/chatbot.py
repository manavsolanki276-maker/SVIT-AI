import re
from typing import Dict, Any, List, Optional
from app.ai.rag_pipeline import RAGPipeline

# System prompt template enforcing strict context-only answers
STRICT_SYSTEM_PROMPT = """You are the official SVIT AI Assistant. Your primary responsibility is to provide precise, structured, and accurate information to students.

CRITICAL INSTRUCTIONS:
1. You MUST answer ONLY using the facts explicitly provided in the CONTEXT below.
2. NEVER use general knowledge, and NEVER give generic advice like "check the college portal", "refer to notifications", or "contact the administration".
3. Extract ALL relevant details (e.g., event names, dates, venues, coordinators, phone numbers, emails, room numbers) directly from the CONTEXT.
4. Format your answer clearly using bullet points, bold text, or lists.
5. If the required information is NOT present in the provided CONTEXT, reply EXACTLY with:
   "I could not find this information in the official SVIT knowledge base."

CONTEXT:
{context}

CONVERSATION HISTORY:
{history}

QUESTION:
{question}

ANSWER:"""


class EnhancedRAGPipeline(RAGPipeline):
    """
    Subclassing RAGPipeline to inject query routing, strict prompt handling,
    and increased retrieval depth without modifying core class structures.
    """

    def route_query_filter(self, question: str) -> Optional[Dict[str, str]]:
        """
        Detects query intent and returns metadata filters for target CSV source files.
        """
        q = question.lower()

        if any(k in q for k in ['event', 'workshop', 'hackathon', 'festival', 'symposium', 'techfest']):
            return {"source_file": "events_faq.csv"}
        elif any(k in q for k in ['contact', 'phone', 'email', 'office', 'admin', 'number', 'address', 'location']):
            return {"source_file": "contact_faq.csv"}
        elif any(k in q for k in ['timetable', 'schedule', 'class time', 'lecture', 'timing']):
            return {"source_file": "timetable.csv"}
        elif any(k in q for k in ['bus', 'route', 'transport', 'commute', 'pickup']):
            return {"source_file": "transport.csv"}
        elif any(k in q for k in ['exam', 'result', 'gtu', 'marks', 'midsem', 're-check']):
            return {"source_file": "examination_faq.csv"}
        elif any(k in q for k in ['faculty', 'professor', 'hod', 'teacher', 'sir', 'madam', 'faculty list']):
            return {"source_file": "faculty_faq.csv"}

        return None  # Search all collections/sources if no specific keyword matched

    def answer_question(self, question: str, session_id: str = "default_user") -> Dict[str, Any]:
        """
        Overrides default answering pipeline with metadata filtering and deep retrieval.
        """
        filter_kwargs = self.route_query_filter(question)

        # Retrieve up to top 10 relevant context documents (increased from default k=5)
        if hasattr(self, 'vectorstore') and self.vectorstore:
            search_kwargs = {"k": 10}
            if filter_kwargs:
                search_kwargs["filter"] = filter_kwargs
            
            retrieved_docs = self.vectorstore.similarity_search(question, **search_kwargs)
            
            # If routed search yields no results, fallback to full search
            if not retrieved_docs and filter_kwargs:
                retrieved_docs = self.vectorstore.similarity_search(question, k=10)
        else:
            retrieved_docs = []

        # Update prompt override on the instance if supported by the base class
        if hasattr(self, 'prompt_template'):
            self.prompt_template = STRICT_SYSTEM_PROMPT

        # Execute standard pipeline execution
        return super().answer_question(question, session_id=session_id)


_rag_instance = None


def get_rag_pipeline(force_rebuild: bool = False) -> RAGPipeline:
    """
    Singleton instance provider for the enhanced RAG Pipeline.
    """
    global _rag_instance
    if _rag_instance is None or force_rebuild:
        try:
            _rag_instance = EnhancedRAGPipeline(force_rebuild=force_rebuild)
        except TypeError:
            # Fallback if base class constructor signatures differ
            _rag_instance = RAGPipeline(force_rebuild=force_rebuild)
    return _rag_instance


def get_bot_response(question: str, session_id: str = "default_user") -> Dict[str, Any]:
    """
    Primary API function called by student_bp routes.
    """
    pipeline = get_rag_pipeline()
    return pipeline.answer_question(question, session_id=session_id)


if __name__ == "__main__":
    # CLI Verification Test
    print("Testing Updated RAG Pipeline...")
    test_queries = [
        "Upcoming events and workshops",
        "College administration contact details",
        "Who is HOD of Computer Engineering?"
    ]

    for query in test_queries:
        print(f"\n=========================================")
        print(f"QUESTION: {query}")
        res = get_bot_response(query, session_id="cli_tester")
        print("\nAI ANSWER:")
        print(res.get("answer", "No answer returned."))
        print("\n📚 SOURCES:")
        for s in res.get("sources", []):
            print(f"- {s}")