import os
import asyncpg  # type: ignore
from dotenv import load_dotenv  # type: ignore


load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_NAME = os.getenv("DB_NAME", "chatbot_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

async def ensure_database_exists():
    """Connect to default postgres DB and auto-create DB_NAME if it doesn't exist."""
    try:
        sys_conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            database="postgres",
            host=DB_HOST,
            port=DB_PORT
        )
        db_exists = await sys_conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", DB_NAME
        )
        if not db_exists:
            print(f"Database '{DB_NAME}' does not exist. Auto-creating database '{DB_NAME}'...")
            await sys_conn.execute(f'CREATE DATABASE "{DB_NAME}"')
            print(f"✅ Database '{DB_NAME}' created successfully!")
        await sys_conn.close()
    except Exception as err:
        print(f"Notice during database check: {err}")

async def get_db_pool():
    await ensure_database_exists()
    try:
        return await asyncpg.create_pool(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT
        )
    except Exception as e:
        print(f"PostgreSQL pool connection failed: {e}")
        return None



async def init_db(pool):
    if not pool:
        print("Cannot initialize DB: pool is None")
        return

    async with pool.acquire() as conn:
        # Check if pgvector extension can be created
        has_vector_ext = False
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            has_vector_ext = True
            print("✅ PostgreSQL pgvector extension enabled!")
        except Exception as e:
            print(f"⚠️ pgvector extension not installed in PostgreSQL ({e}). Using JSONB vector fallback.")

        await conn.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

        # Create bots table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id VARCHAR(100) NOT NULL,
                bot_name VARCHAR(100) NOT NULL,
                api_key VARCHAR(64) UNIQUE NOT NULL,
                system_prompt TEXT DEFAULT 'You are a helpful customer support assistant for this website.',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create bot embeddings table for RAG
        if has_vector_ext:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_embeddings (
                    id BIGSERIAL PRIMARY KEY,
                    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    embedding VECTOR(768),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)
            try:
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS bot_embeddings_hnsw_idx 
                    ON bot_embeddings USING hnsw (embedding vector_cosine_ops);
                """)
            except Exception as idx_err:
                print(f"Notice: HNSW index creation notice: {idx_err}")
        else:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS bot_embeddings (
                    id BIGSERIAL PRIMARY KEY,
                    bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    embedding JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
            """)

        # Create leads table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create chat logs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_logs (
                id BIGSERIAL PRIMARY KEY,
                bot_id UUID REFERENCES bots(id) ON DELETE CASCADE,
                lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("✅ Database tables (bots, bot_embeddings, leads, chat_logs) initialized successfully!")


