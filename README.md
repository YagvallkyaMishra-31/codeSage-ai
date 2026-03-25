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

---

## 🚀 Production Deployment Guide

Deploying CodeSage AI requires hosting the **FastAPI Backend** and the **Vite Frontend** separately. Because local LLMs like Ollama require GPUs and high RAM (which are expensive to host), it is highly recommended to switch to a hosted LLM API (like Groq, OpenAI, or Anthropic) for the production deployment.

### 1. Update Backend for Production (Optional but Recommended)
If you want to run this online without paying for a heavy GPU server:
1. Update `llm_client.py` to use a cloud provider instead of Local Ollama (e.g., replace the `requests.post(OLLAMA_URL)` logic with Groq or OpenAI SDK).
2. Update `backend/requirements.txt` to include `groq` or `openai`.

### 2. Deploy Backend (Render / Railway)
Render is a great free/low-cost platform for FastAPI.

1. Create an account on [Render](https://render.com).
2. Click **New +** → **Web Service** → Connect your GitHub repository.
3. Use the following settings:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables:
   - (If using a cloud LLM) `OPENAI_API_KEY` or `GROQ_API_KEY`
5. Click **Deploy**. Once deployed, copy your backend URL (e.g., `https://codesage-backend.onrender.com`).

### 3. Deploy Frontend (Vercel / Netlify)
Vercel is the best platform for Vite/React applications.

1. Create an account on [Vercel](https://vercel.com).
2. Click **Add New Project** → Import your GitHub repository.
3. Configure the Project:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Expand **Environment Variables** and add:
   - `VITE_API_URL` = `<YOUR_RENDER_BACKEND_URL>` (e.g., `https://codesage-backend.onrender.com`)
5. Click **Deploy**.

### 4. Configure CORS
Once everything is deployed, make sure your backend explicitly allows the Vercel frontend URL.
In `backend/app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-vercel-app.vercel.app"], # Add Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
Commit and push this change to redeploy the backend. You're now live! 🎉
