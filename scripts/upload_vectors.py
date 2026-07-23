# filepath: scripts/upload_vectors.py
import os
from dotenv import load_dotenv
from src.sb import get_client
from src.chunk import split_into_semantic_chunks
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client()


def run_vector_pipeline():
    input_dir = "cleaned_output"

    if not os.path.exists(input_dir):
        print(f"❌ Error: The folder '{input_dir}' does not exist.")
        return

    files = [f for f in os.listdir(input_dir) if f.endswith(".txt")]
    if not files:
        print(f"❌ Error: No text files found inside '{input_dir}'.")
        return

    print("🔌 Connecting to Supabase...")
    sb_client = get_client()

    print("🧠 Initializing Google GenAI embeddings client...")
    embeddings_client = genai.Client()

    print(f"🚀 Found {len(files)} files locally. Beginning Vector Generation loop...")

    for filename in files:
        file_path = os.path.join(input_dir, filename)

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        url = "Unknown URL"
        content_lines = []
        for line in lines:
            if line.startswith("SOURCE URL:"):
                url = line.replace("SOURCE URL:", "").strip()
            elif line.startswith("========================================"):
                continue
            else:
                content_lines.append(line)

        cleaned_text = "".join(content_lines).strip()
        chunks = split_into_semantic_chunks(cleaned_text)
        print(f"\n📄 Processing '{filename}' -> Generated {len(chunks)} text chunks.")

        for i, chunk in enumerate(chunks):
            try:
                print(f"   ↳ Generating embedding vector for chunk {i+1}/{len(chunks)}...")
                embedding_response = embeddings_client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=chunk,
                    config=types.EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT",
                        output_dimensionality=768,
                    ),
                )
                vector_embedding = embedding_response.embeddings[0].values
                assert len(vector_embedding) == 768

                payload = {
                    "parent_url": url,
                    "chunk_content": chunk,
                    "embedding": vector_embedding,
                }

                sb_client.table("documentation_chunks").insert(payload).execute()

            except Exception as e:
                err_code = getattr(e, 'code', None) or (isinstance(e, dict) and e.get('code'))

                if err_code == '23505' or 'duplicate key' in str(e).lower():
                    print(f"   ↳ Chunk {i+1} already exists in database. Skipping safely...")
                    continue
                else:
                    print(f"❌ Failed to vectorise chunk {i+1} for {url}: {e}")
                    print("💡 Check your GOOGLE_API_KEY and Gemini API quota.")
                    return

    print("\n🎉 Success! Your production RAG database is populated with clean vector coordinates.")


if __name__ == "__main__":
    run_vector_pipeline()
