-- 🌓 BERU — Telegram Database Schema (Standalone)
-- Execute this in your Supabase SQL Editor to prepare your Shadow Realm.

-- 1. Telegram Users
CREATE TABLE IF NOT EXISTS tg_users (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT,
    picture TEXT,
    active_session_id TEXT, -- Tracks the current conversation session
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Telegram LangChain Message Store
CREATE TABLE IF NOT EXISTS tg_message_store (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    message JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_tg_message_store_session_id ON tg_message_store(session_id);
