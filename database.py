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

            # Probe and get effective URL from config
            conninfo = Config.get_psycopg_database_url()
            if not conninfo:
                logger.warning("Postgres pool disabled: no working connection after probe.")
                return None

            try:
                # prepare_threshold=None: required for Supabase pooler / PgBouncer transaction mode
                cls._pool = ConnectionPool(
                    conninfo=conninfo,
                    min_size=Config.DB_POOL_MIN,
                    max_size=Config.DB_POOL_MAX,
                    kwargs=Config.psycopg_connect_kwargs(),
                )
                logger.info("Database connection pool initialized.")
            except Exception as e:
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
