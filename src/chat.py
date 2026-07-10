import os
from typing import Any

from dotenv import load_dotenv
from groq import Groq
from google import genai
from google.genai import types

try:
    from sb import get_client
except ImportError:  # pragma: no cover - supports package execution
    from src.sb import get_client

load_dotenv()


def ask_knowledge_base(question: str) -> dict[str, Any]:
    sb_client = get_client()

    print(f"\n🔍 Converting question to vector via Native Google Cloud: '{question}'")

    try:
        ai_client = genai.Client()
        embedding_response = ai_client.models.embed_content(
            model="gemini-embedding-001",
            contents=question,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768,
            ),
        )
        question_vector = embedding_response.embeddings[0].values
        print(f"Embedding length: {len(question_vector)}")
    except Exception as embedding_error:
        print(f"❌ Native Google Cloud Embedding failed: {embedding_error}")
        return {
            "answer": "I’m unable to process the request right now because the embedding service is unavailable.",
            "sources": [],
            "error": str(embedding_error),
        }

    print("🧠 Searching Supabase vector index for matches...")
    rpc_response = sb_client.rpc(
        "match_documents",
        {
            "query_embedding": question_vector,
            "match_threshold": 0.2,
            "match_count": 3,
        },
    ).execute()

    print(f"Embedding length: {len(question_vector)}")

    if rpc_response.data is None:
        print(rpc_response)
        return {
            "answer": "I couldn’t retrieve any relevant context from the knowledge base right now.",
            "sources": [],
            "error": "No retrieval data returned",
        }

    matched_chunks = rpc_response.data
    print(rpc_response.data)

    if not matched_chunks:
        print("❌ No matching knowledge base context found.")
        return {
            "answer": "I couldn’t find relevant information in the knowledge base for that question.",
            "sources": [],
            "error": "No matching context found",
        }

    context_text = ""
    sources: set[str] = set()
    for idx, match in enumerate(matched_chunks):
        context_text += f"\n[Context {idx + 1}]: {match['chunk_content']}\n"
        sources.add(match['parent_url'])

    print("🤖 Generating grounded answer from Groq Cloud LPU...")

    system_prompt = (
        "You are a strict, helpful corporate assistant. Answer the question using ONLY the provided context blocks. "
        "Look for explicit lists, headers, or bullet points in the context when answering. "
        "If a specific item or list is named directly in the text (such as core values), list them exactly as they appear. "
        "If the answer cannot be found cleanly in the context, say 'I cannot find that in the knowledge base.'\n\n"
        f"Context:\n{context_text}"
    )

    try:
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            print("❌ Error: GROQ_API_KEY is not set in the environment variables.")
            return {
                "answer": "I’m unable to generate a response because the Groq API key is missing.",
                "sources": sorted(sources),
                "error": "Missing GROQ_API_KEY",
            }

        groq_client = Groq(api_key=groq_api_key)

        print("\n" + "=" * 40 + "\n💡 LIVE ANSWER STREAM (GROQ):\n" + "=" * 40)

        completion_stream = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            stream=True,
            temperature=0.1,
            max_tokens=1024,
        )

        answer_parts: list[str] = []
        for chunk in completion_stream:
            if chunk.choices and len(chunk.choices) > 0:
                token = chunk.choices[0].delta.content
                if token:
                    print(token, end="", flush=True)
                    answer_parts.append(token)

        answer = "".join(answer_parts).strip()
        print("\n" + "=" * 40)
        print("\n🌐 SOURCES USED:")
        for source in sorted(sources):
            print(f" - {source}")

        return {
            "answer": answer or "I couldn’t generate a grounded response from the available context.",
            "sources": sorted(sources),
            "error": None,
        }
    except Exception as e:
        print(f"\n❌ Failed to reach Groq chat endpoint: {e}")
        return {
            "answer": "I’m sorry, I’m having trouble generating a response right now.",
            "sources": sorted(sources),
            "error": str(e),
        }


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