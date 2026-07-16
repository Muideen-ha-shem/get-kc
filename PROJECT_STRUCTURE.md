# Project Structure

## Repository Root
- .env
- .gitignore
- package.json
- package-lock.json
- requirements.txt
- README.md
- README_COMPREHENSIVE.md
- PROJECT_STRUCTURE.md
- Ha-Shem_AI_Support_Platform_Architecture.md
- infracstructure.md
- node_modules/
- venv/

## Application Source
- src/
  - __init__.py
  - chat.py
  - chat_cli.py
  - chunk.py
  - chunk_runner.py
  - crawl.py
  - intensive_cleaner.py
  - test_clean.py
  - upload_vectors.py
  - api/
    - __init__.py
    - app.py
    - schemas.py
    - routes/
      - __init__.py
      - chat.py
    - services/
      - __init__.py
      - embeddings.py
      - generator.py
      - retrieval.py
  - config/
    - __init__.py
    - settings.py
  - infrastructure/
    - __init__.py
    - database/
      - __init__.py
      - supabase.py
  - orchestrator/
    - __init__.py
    - chat_orchestrator.py
  - services/
    - __init__.py
    - documents/
      - __init__.py
      - document_service.py
    - knowledge/
      - __init__.py
      - knowledge_service.py
    - support/
      - __init__.py
      - support_service.py
  - shared/
    - __init__.py
    - logging.py
  - final_chunks_inspection/

## Scripts and Utilities
- scripts/
  - __init__.py
  - chunk_runner.py
  - crawl.py
  - data/
  - test_clean.py
  - upload_vectors.py

## Frontend
- frontend/
  - index.html
  - package.json
  - package-lock.json
  - postcss.config.js
  - public/
  - src/
    - App.tsx
    - main.tsx
    - styles.css
    - vite-env.d.ts
  - tailwind.config.js
  - tsconfig.app.json
  - tsconfig.json
  - tsconfig.node.json
  - vite.config.js
  - vite.config.ts

## Data and Output Folders
- cleaned_output/
- final_chunks_inspection/
- scripts/data/

## Tests
- tests/
  - test_chat_refactor.py

## Notes
- The backend now follows a layered structure with API, orchestrator, services, infrastructure, shared utilities, and configuration modules.
- Legacy compatibility modules remain in place for now, but the preferred execution path is the orchestrator and service-based flow.
