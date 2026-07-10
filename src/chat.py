import os
from dotenv import load_dotenv
from sb import get_client
from groq import Groq
from google import genai
from google.genai import types

load_dotenv()

def ask_knowledge_base(question: str):
    sb_client = get_client()
    
    print(f"\n🔍 Converting question to vector via Native Google Cloud: '{question}'")
    
    try:
        # 2. Initialize the direct client (safely pulls GOOGLE_API_KEY from environment)
        ai_client = genai.Client()
        
        # 3. Call Google directly. This avoids the LangChain string-formatting bug completely.
        embedding_response = ai_client.models.embed_content(
            model="gemini-embedding-001",
            contents=question,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768  # Sets exactly 768 dimensions for your Supabase DB
            )
        )
        
        # Extract the raw floating-point number list array
        question_vector = embedding_response.embeddings[0].values

        print(f"Embedding length: {len(question_vector)}")
        
    except Exception as embedding_error:
        print(f"❌ Native Google Cloud Embedding failed: {embedding_error}")
        return

    # 2. Query Supabase using your match_documents SQL function
    print("🧠 Searching Supabase vector index for matches...")
    rpc_response = sb_client.rpc("match_documents", {
        "query_embedding": question_vector,
        "match_threshold": 0.2, # Return anything with at least 50% contextual similarity
        "match_count": 3         # Pull top 5 most matching paragraphs
    }).execute()

    print(f"Embedding length: {len(question_vector)}")
    
    if rpc_response.data is None:
        print(rpc_response)
        return

    matched_chunks = rpc_response.data

    print(rpc_response.data)
    
    if not matched_chunks:
        print("❌ No matching knowledge base context found.")
        return
        
    # 3. Combine matched paragraphs into a neat reference context block
    context_text = ""
    sources = set()
    for idx, match in enumerate(matched_chunks):
        context_text += f"\n[Context {idx+1}]: {match['chunk_content']}\n"
        sources.add(match['parent_url'])
        
    # 4. Prompt a Cloud Chat Model via Groq to synthesize the answer
    print("🤖 Generating grounded answer from Groq Cloud LPU...")
    
    system_prompt = (
        "You are a strict, helpful corporate assistant. Answer the question using ONLY the provided context blocks. "
        "Look for explicit lists, headers, or bullet points in the context when answering. "
        "If a specific item or list is named directly in the text (such as core values), list them exactly as they appear. "
        "If the answer cannot be found cleanly in the context, say 'I cannot find that in the knowledge base.'\n\n"
        f"Context:\n{context_text}"
    )
    
    try:
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            print("❌ Error: GROQ_API_KEY is not set in the environment variables.")
            return
        
        groq_client = Groq(api_key=groq_api_key)
        
        print("\n" + "="*40 + "\n💡 LIVE ANSWER STREAM (GROQ):\n" + "="*40)
        
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
            
        for chunk in completion_stream:
            if chunk.choices and len(chunk.choices) > 0:
                token = chunk.choices[0].delta.content
                if token:
                    print(token, end="", flush=True)
                    
        print("\n" + "="*40)
        print("\n🌐 SOURCES USED:")
        for source in sources:
            print(f" - {source}")
            
    except Exception as e:
        print(f"\n❌ Failed to reach Groq chat endpoint: {e}")

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