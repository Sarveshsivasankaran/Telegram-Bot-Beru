import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

class Config:
    # ── Telegram Bot ────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    RUN_MODE: str = os.getenv("RUN_MODE", os.getenv("TELEGRAM_RUN_MODE", "webhook"))

    # ── AI / LLM Providers ──────────────────────────────────────────────
    OPENAI_API_KEY:    str   = os.getenv("OPENAI_API_KEY", "")
    
    # AssemblyAI (Transcription replacement)
    ASSEMBLYAI_API_KEY: str = os.getenv("ASSEMBLYAI_API_KEY", "")
    
    # Ollama (Local)
    OLLAMA_HOST:       str   = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL:      str   = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    # Global Timeouts
    REQUEST_TIMEOUT:   int   = int(os.getenv("REQUEST_TIMEOUT", "60"))

    # ── Database (Postgres) ──────────────────────────────────────────────
    DATABASE_URL:      str   = os.getenv("DATABASE_URL", "")
    DB_POOL_MIN:       int   = int(os.getenv("DB_POOL_MIN", "1"))
    DB_POOL_MAX:       int   = int(os.getenv("DB_POOL_MAX", "10"))

    # ── Supabase (Session Store) ──────────────────────────────────────────
    SUPABASE_URL:      str   = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    # ── Server ────────────────────────────────────────────────────────────
    HOST:              str   = os.getenv("HOST", "0.0.0.0")
    PORT:              int   = int(os.getenv("PORT", "8000"))
