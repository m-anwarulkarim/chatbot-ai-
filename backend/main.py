import os
import secrets
from fastapi import FastAPI, HTTPException, UploadFile, File  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.responses import StreamingResponse, FileResponse  # type: ignore
from pydantic import BaseModel  # type: ignore
from typing import Optional
from contextlib import asynccontextmanager


from database import get_db_pool, init_db
from rag_service import add_knowledge_chunk, stream_chat_response, crawl_and_embed_website, process_and_embed_document


db_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    # Initialize DB connection pool
    db_pool = await get_db_pool()
    try:
        await init_db(db_pool)
    except Exception as e:
        print(f"Warning: Database initialization error (make sure PostgreSQL is running): {e}")
    yield
    if db_pool:
        await db_pool.close()

app = FastAPI(title="Self-Hosted Custom AI Chatbot SaaS", lifespan=lifespan)

# Enable CORS for all origins so client websites can embed the chatbot widget
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schemas
class CreateBotRequest(BaseModel):
    user_id: Optional[str] = "user_enterprise"
    bot_name: str
    system_prompt: Optional[str] = "You are a helpful customer support AI."

class KnowledgeAddRequest(BaseModel):
    content: str

class CrawlRequest(BaseModel):
    url: str

class CreateLeadRequest(BaseModel):
    api_key: str
    name: str
    email: str

class ChatQueryRequest(BaseModel):
    api_key: str
    message: str
    lead_id: Optional[str] = None

@app.get("/widget.js")
async def get_widget():
    widget_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "widget", "widget.js"))
    if os.path.exists(widget_path):
        return FileResponse(widget_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="widget.js file not found")

@app.get("/")
def read_root():
    return {"status": "online", "message": "Self-Hosted Custom AI Chatbot SaaS API is running"}

@app.post("/api/bots")
async def create_bot(req: CreateBotRequest):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database connection is not available. Please ensure PostgreSQL is running.")
    
    api_key = f"bot_key_{secrets.token_hex(16)}"
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO bots (user_id, bot_name, api_key, system_prompt)
            VALUES ($1, $2, $3, $4)
            RETURNING id, bot_name, api_key, system_prompt, created_at;
        """, req.user_id, req.bot_name, api_key, req.system_prompt)
        
        return {
            "id": str(row["id"]),
            "bot_name": row["bot_name"],
            "api_key": row["api_key"],
            "system_prompt": row["system_prompt"],
            "created_at": str(row["created_at"])
        }

@app.post("/api/leads")
async def create_lead(req: CreateLeadRequest):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database connection is not available. Please ensure PostgreSQL is running.")
    async with db_pool.acquire() as conn:
        bot = await conn.fetchrow("SELECT id FROM bots WHERE api_key = $1", req.api_key)
        if not bot:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        
        bot_id = bot["id"]
        row = await conn.fetchrow("""
            INSERT INTO leads (bot_id, name, email)
            VALUES ($1, $2, $3)
            RETURNING id, name, email, created_at;
        """, bot_id, req.name, req.email)
        
        return {
            "status": "success",
            "lead_id": str(row["id"]),
            "name": row["name"],
            "email": row["email"]
        }

@app.get("/api/bots/{bot_id}/leads")
async def get_bot_leads(bot_id: str):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database connection is not available. Please ensure PostgreSQL is running.")
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, name, email, created_at FROM leads WHERE bot_id = $1::uuid ORDER BY created_at DESC", bot_id)
        return [
            {
                "id": str(r["id"]),
                "name": r["name"],
                "email": r["email"],
                "created_at": str(r["created_at"])
            } for r in rows
        ]

@app.get("/api/bots/{bot_id}/logs")
async def get_bot_logs(bot_id: str):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database connection is not available. Please ensure PostgreSQL is running.")
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT cl.id, cl.user_message, cl.bot_response, cl.created_at, l.name as lead_name, l.email as lead_email
            FROM chat_logs cl
            LEFT JOIN leads l ON cl.lead_id = l.id
            WHERE cl.bot_id = $1::uuid
            ORDER BY cl.created_at DESC
            LIMIT 100;
        """, bot_id)
        return [
            {
                "id": r["id"],
                "user_message": r["user_message"],
                "bot_response": r["bot_response"],
                "created_at": str(r["created_at"]),
                "lead_name": r["lead_name"],
                "lead_email": r["lead_email"]
            } for r in rows
        ]


@app.post("/api/bots/{bot_id}/knowledge")
async def add_knowledge(bot_id: str, req: KnowledgeAddRequest):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database connection is not available. Please ensure PostgreSQL is running.")
    try:
        await add_knowledge_chunk(db_pool, bot_id, req.content)
        return {"status": "success", "message": "Knowledge chunk embedded & stored successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bots/{bot_id}/crawl")
async def crawl_website(bot_id: str, req: CrawlRequest):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database connection is not available. Please ensure PostgreSQL is running.")
    try:
        chunk_count = await crawl_and_embed_website(db_pool, bot_id, req.url)
        return {
            "status": "success", 
            "message": f"Successfully crawled {req.url} and embedded {chunk_count} text chunks into PostgreSQL vector DB.",
            "chunks_embedded": chunk_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bots/{bot_id}/upload-document")
async def upload_document(bot_id: str, file: UploadFile = File(...)):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database connection is not available. Please ensure PostgreSQL is running.")
    try:
        content_bytes = await file.read()
        chunk_count = await process_and_embed_document(db_pool, bot_id, content_bytes, file.filename)
        return {
            "status": "success",
            "message": f"Successfully parsed '{file.filename}' and embedded {chunk_count} text chunks into PostgreSQL vector DB.",
            "filename": file.filename,
            "chunks_embedded": chunk_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/chat")
async def chat_endpoint(req: ChatQueryRequest):
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database connection is not available. Please ensure PostgreSQL is running.")
    
    # Validate API key
    async with db_pool.acquire() as conn:
        bot = await conn.fetchrow("SELECT id, system_prompt FROM bots WHERE api_key = $1", req.api_key)
        if not bot:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        
        bot_id = str(bot["id"])
        system_prompt = bot["system_prompt"]
        
    return StreamingResponse(
        stream_chat_response(db_pool, bot_id, system_prompt, req.message, lead_id=req.lead_id),
        media_type="text/event-stream"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

