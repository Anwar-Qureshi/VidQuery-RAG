# VidQuery AI - YouTube RAG Extension

🚀 **An open-source Chrome Extension that injects a local RAG AI directly into YouTube videos.**

I built VidQuery to solve a massive bottleneck in AI development: **YouTube's aggressive bot-protection IP bans**. Most server-side YouTube RAG apps fail or require expensive rotating proxies. I completely bypassed this by shifting the transcript extraction to the client-edge (via a Chrome Extension) and utilizing a decoupled Python backend for the RAG pipeline.

---

## 🏗️ Architecture Design

This project is perfectly decoupled into two distinct architectures:

### 1. The Client-Edge Scraper (Chrome Extension)
*   **Native DOM Traversal**: Instead of failing against YouTube's IP blocks on the server, `content.js` silently intercepts the `ytInitialPlayerResponse` JSON natively inside the user's logged-in browser session. It parses the caption XML and sends the massive raw text string to the backend. **This makes the app 100% immune to YouTube IP bans.**
*   **SPA Event Hooks**: Implements custom event listeners for `yt-navigate-finish` to ensure flawless UI resets across YouTube's Single Page Application (SPA) architecture without ever reloading the page.
*   **Aesthetics**: Designed with a premium Glassmorphism dark-mode UI with smooth micro-animations.

### 2. The Vector Engine (Python FastAPI)
*   **Framework**: High-performance FastAPI server running locally (or deployable to the cloud).
*   **LangChain & FAISS**: Ingests massive transcript strings, splits them intelligently using `RecursiveCharacterTextSplitter`, and embeds them into an in-memory **FAISS** vector database using HuggingFace `all-MiniLM-L6-v2`.
*   **Inference**: Utilizes the **Groq API** (`llama-3.1-8b-instant`) to execute lightning-fast contextual queries against the vector store using LangChain Expression Language (LCEL) pipelines.

---

## 🛠️ Tech Stack
*   **Frontend**: Vanilla HTML / JS / CSS (Chrome Extension V3)
*   **Backend**: Python, FastAPI, Uvicorn
*   **AI Engine**: LangChain, FAISS, HuggingFace Embeddings, Groq (Llama-3)

---

## 💻 Local Setup Instructions

### Backend (Python)
1. Clone the repository and navigate to the project root.
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `.\venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux)
4. Install dependencies: `pip install -r requirements.txt`
5. Create a `.env` file and add your Groq API key: `GROQ_API_KEY=your_key_here`
6. Run the server: `python main.py`

### Frontend (Chrome Extension)
1. Go to `chrome://extensions/` in your browser.
2. Turn on **"Developer mode"** in the top right.
3. Click **"Load unpacked"** and select the `extension/` folder from this repository.
4. Pin the extension, open any YouTube video, hit the ✨ button, and "Process Video".
