import os
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from ...shared.customer_copy import GENERATION_FAILED_FALLBACK

load_dotenv()


def generate_answer(question: str, context_text: str, sources: list[str]) -> dict[str, Any]:
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("Missing GROQ_API_KEY")

    system_prompt = (
        "You are a strict, helpful corporate assistant. Answer the question using ONLY the provided context blocks. "
        "Look for explicit lists, headers, or bullet points in the context when answering. "
        "If a specific item or list is named directly in the text (such as core values), list them exactly as they appear. "
        "You are talking directly to a customer, not a developer — never describe your own process or say things "
        "like 'the context', 'the evidence', or 'the knowledge base'. If the answer cannot be found cleanly in the "
        "context, acknowledge what the customer is asking and offer to help them further instead of just refusing.\n\n"
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
        "answer": answer.strip() or GENERATION_FAILED_FALLBACK,
        "sources": sources,
    }
