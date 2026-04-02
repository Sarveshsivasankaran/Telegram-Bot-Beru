import json
import os
import re
import threading
import time
from typing import ClassVar
from urllib.parse import quote, urlparse, urlunparse

from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

_AGENT_DEBUG_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug-95eba8.log")

def _agent_debug_log(
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict,
    run_id: str = "pre-fix",
) -> None:
    # #region agent log
    try:
        payload = {
            "sessionId": "95eba8",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
            "runId": run_id,
        }
        with open(_AGENT_DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str) + "\n")
    except Exception:
        pass
    # #endregion

_url_probe_lock = threading.Lock()

class Config:
    _psycopg_probe_complete: ClassVar[bool] = False
    _psycopg_effective_url: ClassVar[str] = ""

    # ── Telegram Bot ────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    RUN_MODE: str = os.getenv("RUN_MODE", os.getenv("TELEGRAM_RUN_MODE", "webhook"))

    # ── AI / LLM Providers ──────────────────────────────────────────────
    OPENAI_API_KEY:    str   = os.getenv("OPENAI_API_KEY", "")
    ASSEMBLYAI_API_KEY: str = os.getenv("ASSEMBLYAI_API_KEY", "")
    OLLAMA_HOST:       str   = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL:      str   = os.getenv("OLLAMA_MODEL", "llama3.2")
    REQUEST_TIMEOUT:   int   = int(os.getenv("REQUEST_TIMEOUT", "60"))

    # ── Database (Postgres) ──────────────────────────────────────────────
    DATABASE_URL:      str   = os.getenv("DATABASE_URL", "")
    DB_POOL_MIN:       int   = int(os.getenv("DB_POOL_MIN", "1"))
    DB_POOL_MAX:       int   = int(os.getenv("DB_POOL_MAX", "10"))
    DB_CONNECT_TIMEOUT: int   = int(os.getenv("DB_CONNECT_TIMEOUT", "15"))

    @classmethod
    def supabase_project_ref(cls) -> str:
        """Project ref from SUPABASE_URL (https://xxxx.supabase.co) or SUPABASE_PROJECT_REF."""
        m = re.search(r"https://([a-z0-9-]+)\.supabase\.co", (cls.SUPABASE_URL or "").strip(), re.I)
        if m:
            return m.group(1)
        return (os.getenv("SUPABASE_PROJECT_REF") or "").strip()

    @classmethod
    def _normalize_supabase_pooler_username(cls, url: str) -> str:
        """Supabase transaction pooler (port 6543) requires user postgres.<project_ref>."""
        try:
            raw = url.replace("postgresql+asyncpg://", "postgresql://")
            parsed = urlparse(raw)
        except Exception:
            return url

        host = (parsed.hostname or "").lower()
        port = parsed.port or 5432
        user = parsed.username or ""

        if "pooler.supabase.com" not in host or port != 6543:
            return url
        if user.startswith("postgres.") and len(user) > len("postgres."):
            return url
        if user != "postgres":
            return url

        ref = cls.supabase_project_ref()
        if not ref:
            return url

        new_user = f"postgres.{ref}"
        password = parsed.password or ""
        user_enc = quote(new_user, safe="")
        auth = f"{user_enc}:{quote(password, safe='')}" if password else user_enc
        netloc = f"{auth}@{parsed.hostname}:{port}"
        return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

    @classmethod
    def resolved_database_url(cls) -> str:
        url = (cls.DATABASE_URL or "").strip()
        if not url: return ""
        url = cls._normalize_supabase_pooler_username(url)
        lowered = url.lower()
        if "sslmode=" in lowered: return url
        if "supabase.co" in lowered or "pooler.supabase.com" in lowered:
            sep = "&" if "?" in url else "?"
            return f"{url}{sep}sslmode=require"
        return url

    @classmethod
    def direct_supabase_database_url(cls) -> str:
        ref = cls.supabase_project_ref()
        raw = (cls.DATABASE_URL or "").strip()
        if not ref or not raw: return ""
        try:
            parsed = urlparse(raw.replace("postgresql+asyncpg://", "postgresql://"))
            password = parsed.password or ""
            if not password: return ""
            host = f"db.{ref}.supabase.co"
            auth = f"postgres:{quote(password, safe='')}"
            return urlunparse(("postgresql", f"{auth}@{host}:5432", "/postgres", "", "sslmode=require", ""))
        except Exception: return ""

    @classmethod
    def _pooler_url_same_host_new_port(cls, url: str, new_port: int) -> str:
        try:
            p = urlparse(url.replace("postgresql+asyncpg://", "postgresql://"))
            host = (p.hostname or "").lower()
            if "pooler.supabase.com" not in host: return ""
            user, pw = p.username or "", p.password or ""
            auth = f"{quote(user, safe='')}:{quote(pw, safe='')}" if pw else quote(user, safe="")
            return urlunparse((p.scheme, f"{auth}@{p.hostname}:{new_port}", p.path, p.params, p.query, p.fragment))
        except Exception: return ""

    @classmethod
    def get_psycopg_database_url(cls) -> str:
        with _url_probe_lock:
            if cls._psycopg_probe_complete: return cls._psycopg_effective_url
            cls._psycopg_probe_complete = True
            primary = cls.resolved_database_url()
            if not primary: return ""

            import psycopg
            kwargs = cls.psycopg_connect_kwargs()

            def _try(url: str) -> bool:
                if not url: return False
                try:
                    with psycopg.connect(url, **kwargs) as conn:
                        conn.execute("SELECT 1")
                    cls._psycopg_effective_url = url
                    return True
                except Exception: return False

            if _try(primary): return cls._psycopg_effective_url
            session_url = cls._pooler_url_same_host_new_port(primary, 5432)
            if session_url != primary and _try(session_url): return cls._psycopg_effective_url
            direct = cls.direct_supabase_database_url()
            if _try(direct): return cls._psycopg_effective_url

            cls._psycopg_effective_url = ""
            return ""

    @classmethod
    def psycopg_connect_kwargs(cls) -> dict:
        return {
            "autocommit": True,
            "prepare_threshold": None,
            "connect_timeout": cls.DB_CONNECT_TIMEOUT,
        }

    # ── Supabase ──────────────────────────────────────────────────────────
    SUPABASE_URL:      str   = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    # ── Server ────────────────────────────────────────────────────────────
    HOST:              str   = os.getenv("HOST", "0.0.0.0")
    PORT:              int   = int(os.getenv("PORT", "8000"))
