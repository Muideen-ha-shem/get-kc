# filepath: scripts/upload_vectors.py
import os
from dotenv import load_dotenv
from src.sb import get_client
from src.chunk import split_into_semantic_chunks
from google import genai
from google.genai import types

from scripts.product_metadata import product_metadata_for_url

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

    # cleaned_output/ is regenerated in full every run (test_clean.py has no
    # incremental mode), so without this, every already-uploaded URL gets
    # re-embedded and immediately discarded on the duplicate-key catch below
    # — wasted embedding API calls/quota for no effect. Skip URLs that
    # already have at least one chunk uploaded. (If an earlier run was
    # interrupted partway through a URL's chunks, this could in principle
    # skip finishing it — the per-chunk duplicate-key catch further down
    # remains as a correctness fallback for that case; just re-run without
    # this file present, or clear its rows, to force a full re-upload.)
    print("🔎 Checking which URLs are already uploaded...")
    existing_urls: set[str] = set()
    page_size = 1000
    offset = 0
    while True:
        page = (
            sb_client.table("documentation_chunks")
            .select("parent_url")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        if not page.data:
            break
        existing_urls.update(row["parent_url"] for row in page.data if row.get("parent_url"))
        if len(page.data) < page_size:
            break
        offset += page_size
    print(f"   ↳ {len(existing_urls)} URLs already have uploaded chunks.")

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

        if url in existing_urls:
            print(f"\n⏭️  Skipping '{filename}' — {url} already uploaded.")
            continue

        cleaned_text = "".join(content_lines).strip()
        chunks = split_into_semantic_chunks(cleaned_text)
        print(f"\n📄 Processing '{filename}' -> Generated {len(chunks)} text chunks.")

        # Only attaches product/category/source_type when the URL matches a
        # known product domain (see product_metadata.py) — for anything
        # else (e.g. general ha-shem.com content) this is an empty dict, so
        # the insert payload below is byte-identical to before this change
        # unless you're actually uploading SPIDIFY/ZivaAIRA content AND have
        # run scripts/sql/002_product_knowledge_schema.sql first.
        metadata = product_metadata_for_url(url)
        product_fields = {k: v for k, v in metadata.items() if v is not None}

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
                    **product_fields,
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
