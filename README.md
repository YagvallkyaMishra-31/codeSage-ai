# CodeSage AI — AI-Powered Debugging Assistant

CodeSage AI is an advanced debugging assistant that uses **Retrieval-Augmented Generation (RAG)** to provide deep insights into your codebase. It analyzes your repository context to identify root causes and suggest actionable fixes for complex bugs.

## 🚀 Now Fully Offline with Ollama

CodeSage AI now supports **local LLM inference using Ollama**, allowing you to work completely offline without worrying about OpenAI quota limits or API costs.

### Prerequisites

1.  **Install Ollama**: Download and install from [ollama.com](https://ollama.com).
2.  **Pull the Model**:
    ```bash
    ollama pull llama3.2:3b
    ```
3.  **Ensure Ollama is Running**: The Ollama server must be active before starting the backend.

### Setup & Installation

#### 1. Backend Setup
```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Unix/MacOS
source venv/bin/activate
pip install -r requirements.txt
```

#### 2. Configure Environment
Update `backend/.env`:
```env
LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

#### 3. Run Application
- **Start Backend**: `uvicorn app.main:app --reload --port 8000`
- **Start Frontend**: `cd frontend && npm run dev`

### Features
- **Repository Indexing**: Clones and indexes your codebase into a FAISS vector store.
- **Debug Assistant**: Analyzes stack traces and logs using local LLM + repository context.
- **Activity History**: Tracks and logs all debugging sessions for later review.
- **Premium UI**: Modern, responsive dashboard with real-time stats.

## 🛠️ Tech Stack
- **Backend**: FastAPI, LangChain, FAISS, SentenceTransformers, Ollama.
- **Frontend**: React, Lucide Icons, Vanilla CSS.
- **Storage**: SQLite (Metadata), FAISS (Vector Space).
