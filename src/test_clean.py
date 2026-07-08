import os
from dotenv import load_dotenv
from sb import get_client  # Imports your existing Supabase configuration helper
from intensive_cleaner import intensive_clean_markdown

load_dotenv()

def run_inspection():
    print("🚀 Connecting to Supabase to fetch raw crawled records...")
    sb_client = get_client()
    
    # 1. Fetch your existing raw crawl data
    # Change 'crawled_pages' to your exact old table name if it differs
    response = sb_client.table("crawled_pages").select("url, markdown").execute()
    records = response.data
    
    if not records:
        print("❌ No data found in your table. Double-check your table name.")
        return

    print(f"📊 Found {len(records)} records. Setting up local 'cleaned_output' directory...")
    os.makedirs("cleaned_output", exist_ok=True)

    # 2. Iterate and process the records one by one
    for idx, record in enumerate(records):
        url = record.get("url")
        raw_markdown = record.get("markdown") or ""
        
        # Pass data through our rigorous filter
        cleaned_data = intensive_clean_markdown(raw_markdown)
        
        # Create a clean file name using the web address slug
        safe_filename = url.replace("https://", "").replace("/", "_").strip("_")
        if not safe_filename:
            safe_filename = f"page_{idx}"
        filepath = f"cleaned_output/{safe_filename}.txt"
        
        # 3. Save to file for clear inspection
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"SOURCE URL: {url}\n")
            f.write("=" * 60 + "\n\n")
            f.write(cleaned_data)
            
    print(f"🎉 Done! Cleaned text files are ready inside the 'cleaned_output/' folder.")

if __name__ == "__main__":
    run_inspection()
