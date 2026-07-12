# Ha-Shem AI Support Platform

A modern, intelligent customer support platform powered by AI that leverages Retrieval-Augmented Generation (RAG) to provide real-time, knowledge-grounded responses. Built with a React/TypeScript frontend and Python FastAPI backend.

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
	- [Linux Setup](#linux-setup)
	- [Windows Setup](#windows-setup)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Usage](#usage)
- [Project Structure](#project-structure)

---

## ✨ Features

### 🤖 Intelligent Chat Interface
- **Real-time Streaming Responses**: Watch assistant replies appear character-by-character in real-time
- **Markdown Formatting**: Automatically converts markdown bold (`**text**`) to properly styled text
- **Source Attribution**: Each answer includes clickable links to the knowledge base sources
- **Context-Aware Responses**: Uses RAG to ground all answers in your company's knowledge base

### 📚 Knowledge Management
- **Vector Embeddings**: Questions converted to embeddings via Google Gemini API
- **Semantic Search**: Supabase vector database finds the most relevant content chunks
- **Grounded Answers**: Groq API generates responses based only on provided context
- **Multi-Source Support**: Aggregates information from multiple knowledge base sources

### 💼 Professional UX
- **Responsive Design**: Beautiful, modern interface built with React, TypeScript, and Tailwind CSS
- **Smooth Animations**: Framer Motion brings the interface to life
- **Mobile-Friendly**: Fully responsive chat interface for all device sizes
- **Suggested Actions**: Quick-access buttons for common queries

### 🔐 Security & Performance
- **CORS Support**: Secure cross-origin communication
- **API Rate Limiting**: Efficient request handling
- **Error Handling**: Graceful fallbacks for unavailable services

---

## 🏗️ Architecture

```
Ha-Shem AI Support Platform
├── Backend (FastAPI)
│   ├── Vector Embedding (Google Gemini)
│   ├── Vector Database (Supabase PostgreSQL + pgvector)
│   ├── LLM Generation (Groq API)
│   └── Context Retrieval Engine
└── Frontend (React + TypeScript + Vite)
		├── Real-time Chat UI
		├── Message Streaming
		├── Source Attribution
		└── Responsive Design
```

**Data Flow**:
1. User asks a question → Frontend sends to backend
2. Backend converts question to embedding (Google Gemini)
3. Supabase vector search finds relevant knowledge chunks
4. Groq generates a grounded response using context
5. Response streams back with source links

---

## 📋 Prerequisites

### Required
- **Python 3.9+** (for backend)
- **Node.js 16+** (for frontend)
- **Git**

### API Keys Needed (Free or Paid)
- **Groq API Key** - for LLM generation ([https://console.groq.com](https://console.groq.com))
- **Google Gemini API Key** - for embeddings ([https://ai.google.dev](https://ai.google.dev))
- **Supabase Account** - for vector database ([https://supabase.com](https://supabase.com))

---

## 🚀 Installation & Setup

### Linux Setup

#### Step 1: Clone the Repository

```bash
# Navigate to your desired directory
cd ~/Desktop  # or any preferred location

# Clone the repository
git clone https://github.com/Muideen-ha-shem/get-kc.git
cd get-kc
```

#### Step 2: Set Up Python Backend

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt
```

#### Step 3: Configure Environment Variables

```bash
# Create a .env file in the root directory
cat > .env << 'EOF'
# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here

# Google Gemini API Configuration
GOOGLE_API_KEY=your_google_gemini_api_key_here

# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key

# FastAPI Server Configuration
API_HOST=127.0.0.1
API_PORT=8000
EOF

# Edit the file and add your actual API keys
nano .env  # or use your preferred editor
```

#### Step 4: Set Up Node.js Frontend

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Set up frontend environment (optional, auto-detects backend)
# Default backend: http://127.0.0.1:8000
```

#### Step 5: Run the Application

**Terminal 1 - Start Backend:**
```bash
# From project root with venv activated
python -m src.api.app  # if using module execution

# OR directly run uvicorn
uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 - Start Frontend:**
```bash
cd frontend
npm run dev
```

**Access the Application:**
- Frontend: `http://localhost:5173`
- API Health Check: `http://localhost:8000/health`

---

### Windows Setup

#### Step 1: Clone the Repository

```cmd
# Open Command Prompt or PowerShell
# Navigate to your desired directory
cd Desktop  # or any preferred location

# Clone the repository
git clone https://github.com/Muideen-ha-shem/get-kc.git
cd get-kc
```

#### Step 2: Set Up Python Backend

```cmd
# Create a virtual environment
python -m venv venv

# Activate the virtual environment (Command Prompt)
venv\Scripts\activate

# OR if using PowerShell
# venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt
```

#### Step 3: Configure Environment Variables

**Option A: Using Command Prompt**
```cmd
# Create a .env file
echo. > .env

# Edit with Notepad (add the variables below)
notepad .env
```

**Option B: Using PowerShell**
```powershell
# Create a .env file with content
@"
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_gemini_api_key_here
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
API_HOST=127.0.0.1
API_PORT=8000
"@ | Out-File -FilePath .env -Encoding UTF8
```

**Add to .env file:**
```
GROQ_API_KEY=your_groq_api_key_here
GOOGLE_API_KEY=your_google_gemini_api_key_here
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
API_HOST=127.0.0.1
API_PORT=8000
```

#### Step 4: Set Up Node.js Frontend

```cmd
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install
```

#### Step 5: Run the Application

**Terminal 1 - Start Backend:**
```cmd
# Make sure venv is activated
venv\Scripts\activate

# Start the FastAPI server
uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 - Start Frontend:**
```cmd
cd frontend
npm run dev
```

**Access the Application:**
- Frontend: `http://localhost:5173`
- API Health Check: `http://localhost:8000/health`

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GROQ_API_KEY` | API key for Groq LLM service | `gsk_xxxxx` |
| `GOOGLE_API_KEY` | API key for Google Gemini embeddings | `AIzaxxxxx` |
| `SUPABASE_URL` | Supabase project URL | `https://xxxxx.supabase.co` |
| `SUPABASE_KEY` | Supabase anonymous key | `eyJhbGc...` |
| `API_HOST` | Backend server host | `127.0.0.1` |
| `API_PORT` | Backend server port | `8000` |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server health check |
| `/chat` | POST | Send a message and get AI response |

**Chat Request Format:**
```json
{
	"message": "What are Ha-Shem's core services?"
}
```

**Chat Response Format:**
```json
{
	"answer": "Ha-Shem provides enterprise AI solutions including **support automation**, **cloud services**, and **business process automation**.",
	"sources": [
		"https://ha-shem.com/about-us",
		"https://ha-shem.com/services"
	]
}
```

---

## 🎯 Running the Application

### Quick Start (After Initial Setup)

**Linux:**
```bash
# Terminal 1
source venv/bin/activate
uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2
cd frontend && npm run dev
```

**Windows:**
```cmd
REM Terminal 1
venv\Scripts\activate
uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload

REM Terminal 2
cd frontend && npm run dev
```

### Production Build

```bash
# Frontend build
cd frontend
npm run build
# Output in frontend/dist/

# Backend deployment (use production ASGI server)
pip install gunicorn
gunicorn src.api.app:app
```

---

## 💬 Usage

### Chat Interface Features

1. **Ask Questions**: Type any question about Ha-Shem's services, products, or company info
2. **View Streaming Responses**: Watch the AI assistant respond in real-time
3. **Access Sources**: Click on source links below each answer to verify information
4. **Use Quick Actions**: Click suggested prompts for common queries
5. **Format Support**: Answers automatically bold important terms using `**text**`

### Example Queries

- "Tell me about Ha-Shem Limited"
- "What products do you offer?"
- "How can I schedule a demo?"
- "What are your support options?"
- "Explore cloud services"

---

## 📁 Project Structure

```
get-kc/
├── README.md                          # Documentation
├── requirements.txt                   # Python dependencies
├── .env                               # Environment variables (create this)
│
├── src/                               # Backend source code
│   ├── api/
│   │   ├── app.py                     # FastAPI application setup
│   │   ├── schemas.py                 # Request/response schemas
│   │   ├── routes/
│   │   │   └── chat.py                # Chat endpoint
│   │   └── services/
│   │       ├── retrieval.py           # Vector search & retrieval
│   │       └── generator.py           # LLM response generation
│   ├── sb.py                          # Supabase client setup
│   ├── chat.py                        # Standalone chat script
│   └── [other utility scripts]
│
├── frontend/                          # React TypeScript frontend
│   ├── src/
│   │   ├── App.tsx                    # Main chat application
│   │   └── index.css                  # Tailwind styles
│   ├── public/
│   │   └── logo/                      # Ha-Shem branding
│   ├── package.json                   # Node.js dependencies
│   ├── vite.config.ts                 # Vite configuration
│   ├── tailwind.config.js             # Tailwind CSS config
│   └── tsconfig.json                  # TypeScript configuration
│
├── cleaned_output/                    # Processed knowledge base content
└── final_chunks_inspection/           # Chunked content for vector DB
```

---

## 🛠️ Troubleshooting

### Common Issues

**"ModuleNotFoundError: No module named 'src'"**
```bash
# Ensure you're in the project root when running
cd /path/to/get-kc
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

**"Connection refused" when accessing frontend**
- Ensure backend is running on port 8000
- Check VITE_API_BASE_URL is correctly set (defaults to localhost:8000)

**"GROQ_API_KEY not found"**
- Verify .env file exists in project root
- Ensure you've added the actual API key (not just placeholder text)

**Port already in use**
```bash
# Change port (Linux/Mac)
uvicorn src.api.app:app --host 127.0.0.1 --port 8001

# Windows - find and kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

---

## 📦 Key Dependencies

**Backend:**
- `fastapi` - Web framework
- `groq` - LLM API client
- `google-genai` - Google Gemini embeddings
- `supabase` - Vector database client

**Frontend:**
- `react` - UI framework
- `typescript` - Type safety
- `tailwindcss` - Styling
- `framer-motion` - Animations
- `vite` - Build tool

---

## 📝 License

This project is part of Ha-Shem Limited's AI support platform initiative.

---

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all environment variables are set correctly
3. Ensure all dependencies are installed
4. Check that both services (backend + frontend) are running

---

## 🎉 Happy Testing!

You're all set to test the Ha-Shem AI Support Platform locally. Start with the quick start commands and enjoy exploring the intelligent chat experience!
