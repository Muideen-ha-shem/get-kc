# filepath: src/upload_vectors.py
import os
from dotenv import load_dotenv
from sb import get_client  # Imports your existing Supabase configuration helper
from chunk import split_into_semantic_chunks
from langchain_ollama import OllamaEmbeddings

load_dotenv()

def run_vector_pipeline():
    input_dir = "cleaned_output"
    
    # 1. Verify the local source folder is present
    if not os.path.exists(input_dir):
        print(f"❌ Error: The folder '{input_dir}' does not exist.")
        return
        
    files = [f for f in os.listdir(input_dir) if f.endswith(".txt")]
    if not files:
        print(f"❌ Error: No text files found inside '{input_dir}'.")
        return

    # 2. Connect to your active services
    print("🔌 Connecting to Supabase...")
    sb_client = get_client()

    print("🧠 Initializing local Ollama connection (nomic-embed-text)...")
    # This targets your running Docker container on port 11434
    embeddings_client = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url="http://localhost:11434"
    )

    print(f"🚀 Found {len(files)} files locally. Beginning Vector Generation loop...")

    for filename in files:
        file_path = os.path.join(input_dir, filename)
        
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # Parse out the tracking header URL from the pure text body
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
        
        # Sift text into semantic paragraph chunks
        chunks = split_into_semantic_chunks(cleaned_text)
        print(f"\n📄 Processing '{filename}' -> Generated {len(chunks)} text chunks.")

        for i, chunk in enumerate(chunks):
            try:
                # 3. Request Ollama to turn this specific text string into math coordinates
                print(f"   ↳ Generating embedding vector for chunk {i+1}/{len(chunks)}...")
                vector_embedding = embeddings_client.embed_query(chunk)
                
                # 4. Construct payload matching your new Supabase table schema
                payload = {
                    "parent_url": url,
                    "chunk_content": chunk,
                    "embedding": vector_embedding
                }
                
                # 5. Insert directly into Supabase. If the chunk already exists, catch it and skip.
                sb_client.table("documentation_chunks").insert(payload).execute()
                
            except Exception as e:
                # Check if this error is an absolute duplicate key violation (code 23505)
                # We pull the code attribute safely from Supabase API exceptions
                err_code = getattr(e, 'code', None) or (isinstance(e, dict) and e.get('code'))
                
                if err_code == '23505' or 'duplicate key' in str(e).lower():
                    print(f"   ↳ Chunk {i+1} already exists in database. Skipping safely...")
                    continue
                else:
                    print(f"❌ Failed to vectorise chunk {i+1} for {url}: {e}")
                    print("💡 Ensure Docker Desktop is active and 'docker start ollama' was run.")
                    return


    print("\n🎉 Success! Your production RAG database is populated with clean vector coordinates.")

if __name__ == "__main__":
    run_vector_pipeline()
