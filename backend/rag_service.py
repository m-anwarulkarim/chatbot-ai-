import io
import json
import os
import uuid
import httpx  # type: ignore
import docx  # type: ignore
import pypdf  # type: ignore
from bs4 import BeautifulSoup  # type: ignore # pyfly: ignore [missing-import]
from typing import AsyncGenerator, List, Optional


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.2")


async def generate_embedding(text: str) -> List[float]:
    """Generate 768-dim vector embedding using local Ollama model."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text}
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]


def compute_cosine_similarity(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = sum(a * a for a in v1) ** 0.5
    norm2 = sum(b * b for b in v2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


async def search_similar_chunks(pool, bot_id: str, query_embedding: List[float], limit: int = 3) -> List[str]:
    """Execute raw SQL vector cosine distance query (<=>) in PostgreSQL pgvector, or JSONB fallback."""
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
    
    async with pool.acquire() as conn:
        try:
            rows = await conn.fetch("""
                SELECT content, (embedding <=> $1::vector) as distance
                FROM bot_embeddings
                WHERE bot_id = $2::uuid
                ORDER BY embedding <=> $1::vector
                LIMIT $3;
            """, embedding_str, bot_id, limit)
            return [row["content"] for row in rows]
        except Exception:
            rows = await conn.fetch("""
                SELECT content, embedding
                FROM bot_embeddings
                WHERE bot_id = $1::uuid;
            """, bot_id)
            
            scored_chunks = []
            for row in rows:
                emb_data = row["embedding"]
                if isinstance(emb_data, str):
                    emb_vec = json.loads(emb_data)
                elif isinstance(emb_data, list):
                    emb_vec = emb_data
                else:
                    continue
                score = compute_cosine_similarity(query_embedding, emb_vec)
                scored_chunks.append((score, row["content"]))
            
            scored_chunks.sort(key=lambda x: x[0], reverse=True)
            return [content for _, content in scored_chunks[:limit]]


async def add_knowledge_chunk(pool, bot_id: str, content: str):
    """Generate vector embedding and store chunk into PostgreSQL."""
    embedding = await generate_embedding(content)
    embedding_str = "[" + ",".join(map(str, embedding)) + "]"
    
    async with pool.acquire() as conn:
        try:
            await conn.execute("""
                INSERT INTO bot_embeddings (bot_id, content, embedding)
                VALUES ($1::uuid, $2, $3::vector);
            """, bot_id, content, embedding_str)
        except Exception:
            await conn.execute("""
                INSERT INTO bot_embeddings (bot_id, content, embedding)
                VALUES ($1::uuid, $2, $3::jsonb);
            """, bot_id, content, json.dumps(embedding))



async def stream_chat_response(
    pool, 
    bot_id: str, 
    system_prompt: str, 
    user_query: str,
    lead_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Retrieve context via RAG, stream LLM tokens from local Ollama, and log conversation into chat_logs."""
    try:
        # 1. Get query embedding
        query_vector = await generate_embedding(user_query)
        
        # 2. Search Postgres pgvector
        relevant_chunks = await search_similar_chunks(pool, bot_id, query_vector, limit=3)
        context_text = "\n---\n".join(relevant_chunks) if relevant_chunks else "No specific website data found."
    except Exception as e:
        context_text = f"Note: Vector retrieval skipped ({e})"
    
    # 3. Construct Augmented Prompt
    full_system_prompt = (
        f"{system_prompt}\n\n"
        f"Answer the customer's question strictly based on the following website context:\n"
        f"{context_text}\n\n"
        f"If the answer is not in the context, politely state that you do not have that specific information."
    )
    
    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": user_query}
        ],
        "stream": True
    }
    
    full_response_acc = ""
    
    # 4. Stream response tokens from Ollama
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/chat", json=payload) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            token = data.get("message", {}).get("content", "")
                            if token:
                                full_response_acc += token
                                yield token
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        full_response_acc = f"Error connecting to local Ollama LLM: {str(e)}"
        yield full_response_acc

    # 5. Log chat to PostgreSQL chat_logs table
    if pool and full_response_acc:
        try:
            async with pool.acquire() as conn:
                lead_uuid = uuid.UUID(lead_id) if lead_id else None
                await conn.execute("""
                    INSERT INTO chat_logs (bot_id, lead_id, user_message, bot_response)
                    VALUES ($1::uuid, $2, $3, $4);
                """, uuid.UUID(bot_id), lead_uuid, user_query, full_response_acc)
        except Exception as err:
            print(f"Failed to log chat into PostgreSQL: {err}")


# --- Web Auto-Crawler Helpers ---

async def scrape_website_text(url: str) -> str:
    """Fetch website HTML and extract clean readable text body."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Remove script, style, header, footer elements
    for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        element.decompose()
        
    text = soup.get_text(separator=" ", strip=True)
    return text


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """Split clean text into overlapping chunks for embedding."""
    words = text.split()
    if not words:
        return []
    
    chunks = []
    current_index = 0
    total_words = len(words)
    
    # Estimate ~150 words per chunk (~800 characters)
    words_per_chunk = max(30, chunk_size // 5)
    overlap_words = max(5, overlap // 5)
    
    while current_index < total_words:
        end_index = min(current_index + words_per_chunk, total_words)
        chunk_str = " ".join(words[current_index:end_index])
        if len(chunk_str.strip()) > 20:
            chunks.append(chunk_str.strip())
        current_index += (words_per_chunk - overlap_words)
        
    return chunks


async def crawl_and_embed_website(pool, bot_id: str, url: str) -> int:
    """Crawl URL, extract text, chunk content, and embed into Postgres pgvector."""
    raw_text = await scrape_website_text(url)
    if not raw_text or len(raw_text.strip()) < 50:
        raise ValueError("Could not extract meaningful text content from the provided URL.")
        
    chunks = chunk_text(raw_text)
    chunk_count = 0
    
    for chunk in chunks:
        await add_knowledge_chunk(pool, bot_id, f"Source URL ({url}): {chunk}")
        chunk_count += 1
        
    return chunk_count


# --- Document Parser Helpers (PDF, DOCX, TXT) ---

def parse_document_text(file_bytes: bytes, filename: str) -> str:
    """Extract text from PDF, DOCX, or TXT file bytes."""
    ext = os.path.splitext(filename)[1].lower()
    text = ""
    
    if ext == ".pdf":
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    elif ext == ".docx":
        doc = docx.Document(io.BytesIO(file_bytes))
        for para in doc.paragraphs:
            if para.text:
                text += para.text + "\n"
    elif ext in [".txt", ".md", ".csv"]:
        text = file_bytes.decode("utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Supported formats: .pdf, .docx, .txt, .md")
        
    return text.strip()


async def process_and_embed_document(pool, bot_id: str, file_bytes: bytes, filename: str) -> int:
    """Parse document bytes, chunk text, and store embeddings into PostgreSQL pgvector."""
    extracted_text = parse_document_text(file_bytes, filename)
    if not extracted_text or len(extracted_text) < 20:
        raise ValueError("Document appears to be empty or contains no readable text.")
        
    chunks = chunk_text(extracted_text)
    chunk_count = 0
    
    for chunk in chunks:
        await add_knowledge_chunk(pool, bot_id, f"Document ({filename}): {chunk}")
        chunk_count += 1
        
    return chunk_count
