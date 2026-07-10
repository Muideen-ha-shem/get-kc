import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


def embed_query(question: str) -> list[float]:
    ai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    embedding_response = ai_client.models.embed_content(
        model="gemini-embedding-001",
        contents=question,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768,
        ),
    )
    return embedding_response.embeddings[0].values


def embed_document(chunk: str) -> list[float]:
    ai_client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    embedding_response = ai_client.models.embed_content(
        model="gemini-embedding-001",
        contents=chunk,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768,
        ),
    )
    return embedding_response.embeddings[0].values
