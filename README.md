# 🌒 BERU — Telegram AI Assistant (Shadow Realm Edition)

<p align="center">
  <a href="https://t.me/MATSARBOT">
    <img src="https://github.com/user-attachments/assets/4bbf92fa-c183-4935-8bbc-81dae3778c7b" width="300" alt="Beru AI">
  </a>
  <br>
  <b><a href="https://t.me/MATSARBOT">🔗 Arise & Command Beru on Telegram</a></b>
</p>

---

## 🐲 Overview

**Beru** is an advanced, production-ready Telegram bot powered by **LangChain** and **OpenAI**. Inspired by the Shadow Monarch's loyal marshal, this assistant provides intelligent conversation, real-time web search, visual recognition, and high-fidelity speech-to-text transcription. It is built to be resilient, featuring persistent memory and multi-model support.

---

## 🛠️ Technical Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Webhook Server)
- **AI Engine**: [LangChain](https://www.langchain.com/) (Agentic Workflows)
- **Models**: GPT-4o, GPT-4o Mini, GPT-3.5 Turbo (Cloud) | Ollama (Local)
- **Database**: [Supabase](https://supabase.com/) / [PostgreSQL](https://www.postgresql.org/) (Persistent History & User Profiles)
- **Transcription**: [AssemblyAI Universal-3-Pro](https://www.assemblyai.com/)
- **Search**: DuckDuckGo Search API
- **Language**: Python 3.10+

---

## ✨ Core Features

- **🧠 Persistent Memory**: Remembers your conversations across sessions using PostgreSQL. Context is maintained even if the server restarts.
- **🔍 Internet Intelligence**: Integrated with **Duckduckgo Search** to provide real-time facts and answer questions about modern events.
- **🖼️ Vision Analysis**: Send any image, and Beru will provide a detailed analysis using GPT-4o's vision capabilities.
- **🎤 Universal Speech Recognition**: Send **Voice Messages** or **Round Video Notes**. Beru transcribes them instantly with high accuracy.
- **🤖 Model Switching**: On-the-fly switching between AI models via an interactive inline menu.
- **🕶️ Incognito Mode**: Chat privately without updating your user profile in the database.
- **🌟 Session Management**: Start fresh conversations anytime using `/new` to archive old context.

---

## 📜 Commands

| Command | Action |
| :--- | :--- |
| `/start` | Welcome message and list of available powers. |
| `/model` | 🤖 Switch between GPT-4o, Mini, and Default models. |
| `/new` | 🌟 Start a fresh conversation (archives current context). |
| `/profile` | 🧠 View your saved profile data from the Shadow Realm. |
| `/incognito`| 🕶️ Toggle private mode (no user metadata tracking). |
| `/clear` | 🧹 Wipe the current session's chat history. |
| `/help` | ❓ Get detailed command descriptions. |

---

## 🚀 Setup & Deployment

### 1. Prerequisite: Database
Execute the SQL in `tg_users.sql` in your **Supabase SQL Editor** to initialize the following:
- `tg_users`: User metadata (name, email, profile status).
- `tg_message_store`: Raw LangChain message history.

### 2. Environment Variables (`.env`)
Create a `.env` file with the following keys:

```env
TELEGRAM_BOT_TOKEN=your_token
WEBHOOK_URL=https://your-app.onrender.com
DATABASE_URL=postgresql://postgres.ref:password@host:6543/postgres?sslmode=require
OPENAI_API_KEY=sk-proj-...
ASSEMBLYAI_API_KEY=your_key
RUN_MODE=webhook  # Use 'polling' for local development
```

### 3. Deploy to Render
1. Connect your GitHub repository to **Render**.
2. Select **Web Service**.
3. **Runtime**: `Python 3`
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command**: `python main.py`

---

## 💻 Local Development

For testing without a public URL:
1. Install dependencies: `pip install -r requirements.txt`
2. Set `RUN_MODE=polling` in `.env`.
3. Run the application: `python main.py`
4. The bot will now listen for messages directly from Telegram servers.

---

**Arise.** 🐜💜

