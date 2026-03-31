import logging
from psycopg_pool import ConnectionPool
from supabase import create_client, Client
from config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    _pool = None
    _supabase_client = None

    @classmethod
    def get_pool(cls) -> ConnectionPool:
        if cls._pool is None:
            if not Config.DATABASE_URL:
                logger.warning("DATABASE_URL not set. Connection pool disabled.")
                return None
            
            try:
                # Senior Fix: Use the ConnectionPool with a timeout and clear error messages
                # for common Render/Supabase IPv6 issues.
                cls._pool = ConnectionPool(
                    conninfo=Config.DATABASE_URL,
                    min_size=Config.DB_POOL_MIN,
                    max_size=Config.DB_POOL_MAX,
                    kwargs={
                        "autocommit": True,
                        "prepare_threshold": 0,
                        "connect_timeout": 10
                    }
                )
                logger.info("Database connection pool initialized.")
            except Exception as e:
                error_msg = str(e)
                if "Network is unreachable" in error_msg:
                    logger.error("🛑 SHADOW REALM ERROR: Network is unreachable (IPv6 issue).")
                    logger.error("💡 TIP: Render uses IPv4. Switch your DATABASE_URL to use the Supabase Pooler (Port 6543).")
                else:
                    logger.error(f"Failed to initialize database pool: {e}")
                return None
        return cls._pool

    @classmethod
    def get_supabase(cls) -> Client:
        if cls._supabase_client is None:
            if Config.SUPABASE_URL and Config.SUPABASE_SERVICE_KEY:
                try:
                    cls._supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
                    logger.info("Supabase client initialized.")
                except Exception as e:
                    logger.error(f"Failed to initialize Supabase client: {e}")
            else:
                logger.warning("Supabase credentials missing.")
        return cls._supabase_client

    @classmethod
    def close_pool(cls):
        if cls._pool:
            cls._pool.close()
            logger.info("Database connection pool closed.")
            cls._pool = None
