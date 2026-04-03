# 🌒 BERU — Telegram AI Assistant (Shadow Realm Edition)

**Beru** is a powerful, standalone Telegram bot powered by **LangChain**, designed for the Shadow Monarch. It features persistent chat history, image vision analysis, and voice/video transcription, deployed as a robust web service.

---

## 📸 Core Features

- **🧠 Persistent Memory**: Remembers your conversations across sessions using Supabase/Postgres and LangChain's `PostgresChatMessageHistory`.
- **🖼️ Vision Analysis**: Send any image, and Beru will analyze it using GPT-4o Vision.
- **🎤 Speech Recognition**: Supports **Voice Messages** and **Round Video Notes**. Transcribed using **AssemblyAI (Universal-3-Pro)** with automatic language detection.
- **🔍 Internet Intelligence**: Integrated with **DuckDuckGo Search** for real-time information retrieval (Beru searches the web for you).
- **🤖 Model Switching**: Swap between cloud models (GPT-4o, GPT-4o Mini) on the fly via a sleek inline menu.
- **🕶️ Incognito Mode**: Chat privately without updating your user profile in the database.
- **🚀 FAST & Modern**: Built with **FastAPI** using the latest `lifespan` protocol for reliable startup/shutdown behavior.

---

## 🚀 Quick Deployment (Render)

### 1. Database Setup
Execute the SQL in `tg_users.sql` in your **Supabase SQL Editor**:
- **Table:** `tg_users` — Stores user metadata (name, email, profile status).
- **Table:** `tg_message_store` — Stores the raw LangChain message history.

### 2. Render Web Service Deployment
1. Connect your repository to **Render**.
2. Select **Web Service**.
3. Use the following configuration:
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Environment Variables**: Add the keys from your `.env` (see below).

---

## 🔑 Key Configuration (.env)

| Variable | Description |
| :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather. |
| `WEBHOOK_URL` | Your Render URL (e.g., `https://telegram-bot-beru.onrender.com`). |
| `DATABASE_URL` | Your Supabase Postgres connection string (Port 6543 for pooler). |
| `SUPABASE_URL` | Your Supabase Project API URL. |
| `SUPABASE_SERVICE_KEY` | Your Supabase `service_role` key (for user profile management). |
| `OPENAI_API_KEY` | (Required) For GPT-4o and Vision features. |
| `ASSEMBLYAI_API_KEY` | (Required) For high-quality voice/video transcription. |
| `RUN_MODE` | Set to `webhook` for production (Render) or `polling` for local testing. |

---

## 📜 Commands

- `/start`: Initiate your mission with Beru and register your user profile.
- `/model`: 🤖 Switch between available AI models (GPT-4o, GPT-4o Mini, GPT-3.5 Turbo).
- `/profile`: 🧠 View your saved profile information from the Shadow Realm.
- `/incognito`: 🕶️ Toggle private mode (no user metadata updates).
- `/clear`: 🧹 Wipe your current chat history from the persistent store.
- `/help`: ❓ Get a detailed list of all commands.

**Arise.** 🐜💜
