import os
from dotenv import load_dotenv
from src.sb import get_client
from src.intensive_cleaner import intensive_clean_markdown

load_dotenv()


def run_inspection():
    print("🚀 Connecting to Supabase to fetch raw crawled records...")
    sb_client = get_client()

    response = sb_client.table("crawled_pages").select("url, markdown").execute()
    records = response.data

    if not records:
        print("❌ No data found in your table. Double-check your table name.")
        return

    print(f"📊 Found {len(records)} records. Setting up local 'cleaned_output' directory...")
    os.makedirs("cleaned_output", exist_ok=True)

    for idx, record in enumerate(records):
        url = record.get("url")
        raw_markdown = record.get("markdown") or ""
        cleaned_data = intensive_clean_markdown(raw_markdown)

        safe_filename = url.replace("https://", "").replace("/", "_").strip("_")
        if not safe_filename:
            safe_filename = f"page_{idx}"
        filepath = f"cleaned_output/{safe_filename}.txt"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"SOURCE URL: {url}\n")
            f.write("=" * 60 + "\n\n")
            f.write(cleaned_data)

    print(f"🎉 Done! Cleaned text files are ready inside the 'cleaned_output/' folder.")


if __name__ == "__main__":
    run_inspection()
