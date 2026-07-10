# filepath: src/chat.py
import os
import json
from dotenv import load_dotenv
from sb import get_client
from langchain_ollama import OllamaEmbeddings
from groq import Groq

load_dotenv()

def ask_knowledge_base(question: str):
    sb_client = get_client()
    
    # 1. Initialize the same embedding model we used to upload data
    embeddings_client = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url="http://localhost:11434"
    )
    
    print(f"\n🔍 Converting question to vector: '{question}'")
    question_vector = embeddings_client.embed_query(question)
    
    # 2. Query Supabase using our new match_documents SQL function
    print("🧠 Searching Supabase vector index for matches...")
    rpc_response = sb_client.rpc("match_documents", {
        "query_embedding": question_vector,
        "match_threshold": 0.5, # Return anything with at least 30% contextual similarity
        "match_count": 5         # Pull top 5 most matching paragraphs
    }).execute()
    
    matched_chunks = rpc_response.data
    
    if not matched_chunks:
        print("❌ No matching knowledge base context found.")
        return
        
    # 3. Combine matched paragraphs into a neat reference context block
    context_text = ""
    sources = set()
    for idx, match in enumerate(matched_chunks):
        context_text += f"\n[Context {idx+1}]: {match['chunk_content']}\n"
        sources.add(match['parent_url'])
        
    # 4. Prompt a local Chat Model (e.g. deepseek-r1) to synthesize the answer
    print("🤖 Generating grounded answer from local LLM...")
    
    system_prompt = (
        "You are a helpful assistant. Answer the question using ONLY the following context blocks. "
        "You are a strict, helpful corporate assistant. Answer the question using ONLY the provided context blocks. "
        "Look for explicit lists, headers, or bullet points in the context when answering. "
        "If a specific item or list is named directly in the text (such as core values), list them exactly as they appear. "
        "If the answer cannot be found cleanly in the context, say 'I cannot find that in the knowledge base.'\n\n"
        f"Context:\n{context_text}"
    )
    
    try:

        # Initialised Groq client with API key from environment variable
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            print("❌ Error: GROQ_API_KEY is not set in the environment variables.")
            return
        
        groq_client = Groq(api_key=groq_api_key)
        
        print("\n" + "="*40 + "\n💡 LIVE ANSWER STREAM(GROQ):\n" + "="*40)
        
        # Open a streaming context block instead of a standard blocking post request
        completion_stream = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            stream=True,
            temperature=0.1,
            max_tokens=1024
        )
            
            # Read and print tokens immediately as they are streamed down from the cloud
        for chunk in completion_stream:
            # Safely catch chunk text deltas
            token = chunk.choices[0].delta.content
            if token:
                print(token, end="", flush=True)
                    
        print("\n" + "="*40)
        print("\n🌐 SOURCES USED:")
        for source in sources:
            print(f" - {source}")
            
    except Exception as e:
        print(f"\n❌ Failed to reach chat model endpoint: {e}")

if __name__ == "__main__":
    # Continuous conversation loop so the script doesn't exit after one answer
    print("🤖 Ha-Shem RAG System Initialized. Type 'exit' or 'quit' to close.")
    while True:
        user_query = input("\n💬 What will you like to know about Ha-Shem Limited: ").strip()
        if user_query.lower() in ['exit', 'quit']:
            print("Goodbye!")
            break
        if not user_query:
            continue
        ask_knowledge_base(user_query)
