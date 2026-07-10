import os
from typing import Any

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


def generate_answer(question: str, context_text: str, sources: list[str]) -> dict[str, Any]:
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("Missing GROQ_API_KEY")

    system_prompt = (
        "You are a strict, helpful corporate assistant. Answer the question using ONLY the provided context blocks. "
        "Look for explicit lists, headers, or bullet points in the context when answering. "
        "If a specific item or list is named directly in the text (such as core values), list them exactly as they appear. "
        "If the answer cannot be found cleanly in the context, say 'I cannot find that in the knowledge base.'\n\n"
        f"Context:\n{context_text}"
    )

    groq_client = Groq(api_key=groq_api_key)
    completion = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        stream=False,
        temperature=0.1,
        max_tokens=1024,
    )

    answer = completion.choices[0].message.content or ""
    return {
        "answer": answer.strip() or "I couldn’t generate a grounded response from the available context.",
        "sources": sources,
    }
