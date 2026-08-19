from typing import Dict, List

class ConversationMemory:
    """
    In-memory session buffer to keep track of recent user & assistant interactions.
    """
    def __init__(self, max_history: int = 6):
        self.sessions: Dict[str, List[Dict[str, str]]] = {}
        self.max_history = max_history

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        return self.sessions.get(session_id, [])

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append({"role": role, "content": content})
        
        # Keep only recent memory
        if len(self.sessions[session_id]) > self.max_history:
            self.sessions[session_id] = self.sessions[session_id][-self.max_history:]

    def format_history_for_prompt(self, session_id: str) -> str:
        history = self.get_history(session_id)
        if not history:
            return "No previous context."
        
        formatted = []
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            formatted.append(f"{role}: {msg['content']}")
        return "\n".join(formatted)

memory_manager = ConversationMemory()