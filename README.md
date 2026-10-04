# Enterprise AI Chatbot SaaS Platform (Self-Hosted RAG)

A 100% self-hosted, custom AI chatbot SaaS platform where website owners can train custom AI assistants on their website content (manual text, web crawler, PDF/DOCX documents), embed a 1-line JavaScript widget, capture customer leads (Name & Email), and manage chat logs in real-time.

## 🚀 Tech Stack
- **AI Engine:** Local Ollama (`llama3.2` LLM + `nomic-embed-text` Embeddings)
- **Backend:** FastAPI (Python) + Raw `asyncpg` + PostgreSQL (Vector Search & Fallback)
- **Frontend Admin Panel:** Astro 5 + Svelte 5 + Tailwind CSS
- **Embed Widget:** Standalone Vanilla JS (`widget/widget.js`)

## 📁 Project Structure
```text
├── backend/       # FastAPI server & RAG pipeline
├── frontend/      # Astro 5 + Svelte 5 admin dashboard
├── widget/        # Embeddable JS floating widget
└── .gitignore
```

## 🛠️ Quick Start

### 1. Start Ollama Models
```bash
ollama run nomic-embed-text
ollama run llama3.2
```

### 2. Start Backend API Server
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
Backend server runs at `http://localhost:8000`.

### 3. Start Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
Dashboard runs at `http://localhost:4321`.
