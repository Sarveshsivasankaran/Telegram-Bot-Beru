# 🌒 BERU — Standalone Telegram Bot

**Beru** is now a completely independent Telegram bot project. This version is optimized for **Vercel (Serverless)** and **Render (Web Service)**, providing the Shadow Monarch with a persistent memory-driven AI assistant on mobile.

---

## 📸 Vision Features
Unlike the standard web interface, this standalone bot is specialized for visual missions:
- **Image Processing**: Send a photo to Beru, and he will analyze it instantly.
- **Contextual Memory**: Beru remembers your interests and past image-based missions.

---

## 🚀 Standalone Deployment

### 1. Database Setup (Standalone)
1. Run the SQL in `telegram_bot/schema_telegram.sql` in your Supabase SQL Editor. 
   - This creates `tg_users`, `tg_sessions`, `tg_user_master_profile`, and `tg_message_store`.
2. This ensures your Telegram bot data is separated from the web app.

### 2. Deployment (e.g., Vercel / Render)
1. Point your deployment to this `telegram_bot/` subdirectory.
2. Install dependencies:
   ```bash
   pip install -r telegram_bot/requirements.txt
   ```
3. Set your **Environment Variables** (see below).

### 3. Linking the Webhook (CRITICAL)
Once your bot is deployed (e.g., `https://beru-ai-bot.onrender.com`), visit:
`https://your-bot-url.com/api/telegram/setup`
This will automatically link your Telegram bot to your new server.

---

## 🔑 Environment Variables
Create a `.env` file with these keys (an example is provided in `.env`):

- `OPENAI_API_KEY`: Required for Image Vision.
- `TELEGRAM_BOT_TOKEN`: From @BotFather.
- `TELEGRAM_WEBHOOK_URL`: Your deployed URL + `/api/telegram/webhook`.
- `DATABASE_URL`: Postgres connection for chat history.
- `SUPABASE_URL` & `SUPABASE_SERVICE_KEY`: For session management.
- `TG_BOT_PORT`: Port to listen on (default 8001).

---

## 📜 Commands
- `/start`: Initiate your mission with Beru.
- `/help`: Detailed guidance from the Shadow Monarch's loyal assistant.
- **Simply Send a Photo**: Activate Beru's vision system.

**Arise.** 🐜💜
