from typing import Any

from .orchestrator.chat_orchestrator import chat_orchestrator


def ask_knowledge_base(question: str) -> dict[str, Any]:
    """Compatibility wrapper around the orchestrated chat pipeline."""
    return chat_orchestrator.process_request(question)


if __name__ == "__main__":
    print("🤖 Ha-Shem RAG System Initialized. Type 'exit' or 'quit' to close.")
    while True:
        user_query = input("\n💬 What will you like to know about Ha-Shem Limited: ").strip()
        if user_query.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        if not user_query:
            continue
        result = ask_knowledge_base(user_query)
        if result.get("answer"):
            print(f"\n🧠 Answer: {result['answer']}")