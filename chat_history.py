# chat_history.py
# Manages multi-turn conversation memory using LangChain message objects.
#
# How it works:
#   - Every user question is stored as a HumanMessage
#   - Every LLM response is stored as an AIMessage
#   - The full list is passed into the LangChain prompt each turn
#   - This gives Mistral memory of the entire conversation

from langchain_core.messages import HumanMessage, AIMessage


class ChatHistory:
    """
    Stores the full conversation as a list of LangChain message objects.
    Pass .get_history() directly into the LangChain prompt's chat_history slot.
    """

    def __init__(self):
        self._messages: list = []

    def add_user_message(self, question: str):
        """Call this AFTER the LLM responds (not before) to keep history clean."""
        self._messages.append(HumanMessage(content=question))

    def add_ai_message(self, response: str):
        """Store the raw LLM response string as an AIMessage."""
        self._messages.append(AIMessage(content=response))

    def get_history(self) -> list:
        """Returns the full list of messages for use in the LangChain prompt."""
        return self._messages

    def clear(self):
        """Wipe the conversation — start fresh."""
        self._messages = []

    def summary(self) -> str:
        """Human-readable dump of the conversation so far."""
        if not self._messages:
            return "No conversation history yet."
        lines = []
        for msg in self._messages:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            # Truncate long messages for readability
            content = msg.content[:120] + "..." if len(msg.content) > 120 else msg.content
            lines.append(f"[{role}]: {content}")
        return "\n".join(lines)

    def __len__(self):
        return len(self._messages)