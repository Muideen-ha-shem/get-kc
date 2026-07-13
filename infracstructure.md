# Infrastructure Overview

## Frontend Infrastructure

- **React**: Builds the interactive single-page user interface and component structure.
- **TypeScript**: Provides type safety and better developer experience in the frontend code.
- **Vite**: Serves the development server and builds the production frontend bundle.
- **Tailwind CSS**: Delivers the utility-first styling system used for layout, spacing, color, and responsive design.
- **Framer Motion**: Adds UI animation effects and transitions for the chat experience and page elements.
- **Lucide React**: Supplies iconography across buttons, navigation, and status cards.
- **Browser Fetch API**: Sends POST requests from the client to the backend `/chat` endpoint.
- **CSS / Responsive Layout**: Supports mobile-friendly, enterprise-style UI, cards, and chat overlay.
- **Environment Variable `VITE_API_BASE_URL`**: Optionally configures backend endpoint for the client.

## Backend Infrastructure

- **Python**: Implements the backend server logic and knowledge retrieval workflows.
- **FastAPI**: Provides the REST API framework for the `/chat` endpoint and health route.
- **Uvicorn**: Runs the ASGI web server for the FastAPI application in development.
- **python-dotenv**: Loads `.env` configuration values for API keys and environment settings.
- **Pydantic**: Validates request and response payloads for the chat API.
- **CORS Middleware**: Enables browser-based access from the frontend origin.
- **Groq API**: Generates the final LLM response based on retrieved context and prompts.
- **Google Gemini Embeddings**: Converts user questions into vector embeddings for semantic search.
- **Supabase Vector Search**: Executes knowledge retrieval via the `match_documents` RPC against stored content vectors.
- **Supabase/PostgreSQL**: Stores knowledge base chunks and metadata, powering RAG search.
- **Request/Response JSON**: Handles chat payloads and response formatting between frontend and backend.

## Supporting Infrastructure Files

- **`.env`**: Stores sensitive API keys and service configuration values like `GROQ_API_KEY`, `GOOGLE_API_KEY`, and Supabase credentials.
- **`requirements.txt`**: Lists backend Python dependencies required to run FastAPI, Groq, Google embeddings, and Supabase.
- **`frontend/package.json`**: Lists frontend dependencies and scripts for Vite, React, TypeScript, Tailwind, and development commands.
- **`README.md`**: Documents architecture, setup, and the expected service flow for the whole application.
