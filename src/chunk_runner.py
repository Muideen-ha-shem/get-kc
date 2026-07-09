# filepath: src/chunk_runner.py
import os
from chunk import split_into_semantic_chunks

def run_local_file_chunking():
    input_dir = "cleaned_output"
    output_dir = "final_chunks_inspection"
    
    # Verify the cleaned text directory is present on your system
    if not os.path.exists(input_dir):
        print(f"❌ Error: The folder '{input_dir}' does not exist. Run your intensive cleaning script first.")
        return
        
    files = [f for f in os.listdir(input_dir) if f.endswith(".txt")]
    if not files:
        print(f"❌ Error: No text files found inside '{input_dir}'.")
        return

    print(f"📁 Found {len(files)} clean text files locally. Segmenting your knowledge base...")
    os.makedirs(output_dir, exist_ok=True)

    for filename in files:
        file_path = os.path.join(input_dir, filename)
        
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        # Separate out the tracking URL header from the pure web text body
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
        
        # Pass the plain clean text block directly into your core module logic
        chunks = split_into_semantic_chunks(cleaned_text)
        
        # Save output for clear, direct visual review
        output_file_path = os.path.join(output_dir, f"chunked_{filename}")
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(f"🌐 PAGE SOURCE URL: {url}\n")
            f.write(f"🧩 SEGMENTED CHUNK COUNT: {len(chunks)}\n")
            f.write("=" * 60 + "\n\n")
            
            for i, chunk in enumerate(chunks):
                f.write(f"=========================================\n")
                f.write(f"📝 CHUNK {i+1} of {len(chunks)} | Size: {len(chunk)} chars\n")
                f.write(f"=========================================\n")
                f.write(chunk)
                f.write("\n\n")
                
        print(f"✅ Chunked: {filename} -> Generated {len(chunks)} visual text blocks.")

    print(f"\n🎉 Process Complete! Review your structured blocks inside: '{output_dir}/'")

if __name__ == "__main__":
    run_local_file_chunking()
