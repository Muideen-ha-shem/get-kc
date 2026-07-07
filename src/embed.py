# The embed_documents function in embed.py, processes and stores crawled web content into our Supabase vector database:

# cleaned HTML produced by Crawl4AI
# splits it into semantically meaningful chunks using HTML headers
# embeds each chunk using the nomic-embed-text model via a locally running Ollama instance.
# These embeddings, along with associated metadata, are stored in the Supabase documents table using LangChain’s SupabaseVectorStore. This setup enables efficient semantic search and retrieval, which is crucial for building RAG applications.

from langchain_community.vectorstores import SupabaseVectorStore

from langchain_text_splitters import HTMLSemanticPreservingSplitter  # Preserves HTML structure while splitting

from langchain_ollama import OllamaEmbeddings  # Interface for embedding with Ollama models

from langchain_core.documents import Document
# from langchain.docstore.document import Document  # Document object used by LangChain

from supabase import Client



def embed_documents(result:dict, supabase_client:Client):

    """

    Splits a crawled HTML document into semantic chunks, generates embeddings using an Ollama model,

    and stores the resulting vectors in a Supabase vector store.

    """



    # Define which HTML headers to split on (semantic chunking)

    headers_to_split_on = [

        ('h1', 'header1'),

        ('h2', 'header2'),

        ('h3', 'header3'),

    ]



    # Create the text splitter with a max chunk size

    text_splitter = HTMLSemanticPreservingSplitter(

        headers_to_split_on=headers_to_split_on,

        max_chunk_size=1000

    )



    # Split the cleaned HTML into smaller semantically meaningful chunks

    docs = text_splitter.split_text(result['cleaned_html'])



    # Add metadata and unique IDs to each chunked document

    for i, doc in enumerate(docs):

        doc.metadata = {

            'metadata': result['metadata'],

            'url': result['url'],

        }

        doc.id = result['url'] + '__' + str(i)  # Unique ID for each chunk



    # Initialize the Ollama embeddings model (using nomic-embed-text)

    embeddings = OllamaEmbeddings(model="nomic-embed-text")



    # Store the embedded documents into Supabase vector store for later retrieval

    vector_store = SupabaseVectorStore.from_documents(

        docs,                         # List of chunked documents

        embeddings,                   # Embedding model

        client=supabase_client,       # Supabase client connection

        table_name="documents",       # Target table for vector storage

        query_name="match_documents", # Name of the query function for retrieval (see init sql)

    )


#     Putting it all together: with main.py we:

# perform a breadth first crawl of the domain we set
# for each page of the domain we:
# extract properties that we write into crawled_pages (one-page one-row)
# chunk the extracted text using LangChain’s semantically preserving HTMLSemanticPreservingSplitter splitter
# embed the text chunks with Ollama’s nomic-embed-text model
# write chunks and some metadata to Supabase table documents
# The crawled_pages holds useful extracted data such as

# internal and external url links, text, raw html
# metadata: title, author etc
# crawl specific data: depth (crawl depth) and parent-url
# Crawl4AI also extracts Open Graph data
# The documents table will hold several rows per page, one for each chunk that got embedded.