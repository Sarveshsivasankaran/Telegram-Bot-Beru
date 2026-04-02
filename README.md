# 🌒 BERU — Telegram AI Assistant (Shadow Realm Edition)

**Beru** is a powerful, standalone Telegram bot powered by **LangChain**, designed for the Shadow Monarch. It features persistent chat history, image vision analysis, and voice transcription, deployed as a robust web service.

---

## 📸 Core Features

- **🧠 Persistent Memory**: Remembers your conversations across sessions using Supabase and LangChain's `PostgresChatMessageHistory`.
- **🖼️ Vision Analysis**: Send any image, and Beru will analyze it using GPT-4o Vision or local vision models.
- **🎤 Voice Transcription**: Send a voice message, and Beru will transcribe it using **AssemblyAI** before responding.
- **🔍 Internet Intelligence**: Integrated with **DuckDuckGo Search** for real-time information retrieval.
- **🤖 Model Switching**: Swap between cloud models (GPT-4o, GPT-3.5) or local models (Llama 3.2 via Ollama) on the fly.
- **🕶️ Incognito Mode**: Chat privately without updating your user profile in the database.

---

## 🚀 Quick Deployment (Render)

### 1. Database Setup
Execute the SQL in `tg_users.sql` in your **Supabase SQL Editor**:
- This creates the `tg_users` table for user metadata.
- This creates the `tg_message_store` table for chat history persistence.

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
| `WEBHOOK_URL` | Your Render URL (e.g., `https://beru-bot.onrender.com`). |
| `DATABASE_URL` | Your Supabase Postgres connection string (Port 6543 for pooler). |
| `SUPABASE_URL` | Your Supabase Project API URL. |
| `SUPABASE_SERVICE_KEY` | Your Supabase `service_role` key. |
| `OPENAI_API_KEY` | (Optional) For GPT-4o and Vision features. |
| `ASSEMBLYAI_API_KEY` | (Optional) For high-quality voice transcription. |
| `OLLAMA_HOST` | (Optional) For connecting to a local Ollama instance. |

---

## 📜 Commands

- `/start`: Initiate your mission with Beru.
- `/model`: 🤖 Switch between available AI models (GPT-4o, GPT-4o Mini, GPT-3.5 Turbo).
- `/profile`: 🧠 View your saved profile information from the Shadow Realm.
- `/incognito`: 🕶️ Toggle private mode (no user metadata updates).
- `/clear`: 🧹 Wipe your current chat history from the persistent store.
- `/help`: ❓ Get a detailed list of all commands.

**Arise.** 🐜💜
