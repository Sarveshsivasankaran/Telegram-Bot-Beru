"""
╔══════════════════════════════════════════════════════════════╗
║  BERU - The Shadow Monarch's AI Assistant                    ║
║  Powered by LangChain | Telegram Bot Edition                 ║
║  Deployed via Webhook on Render                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import logging
import asyncio
import json
import base64
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
import uuid
from typing import Optional, Dict, Set, List

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama as Ollama
from langchain_openai import ChatOpenAI
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_postgres import PostgresChatMessageHistory
from database import DatabaseManager
import psycopg

# Telegram
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatAction

# FastAPI for Render webhook server
from fastapi import FastAPI, Request, Response
import uvicorn

# Tools
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent

from config import Config


# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── AssemblyAI Transcription ─────────────────────────────────────────────────
async def transcribe_audio(file_path: str) -> str:
    """Transcribe audio via AssemblyAI."""
    if not Config.ASSEMBLYAI_API_KEY:
        logger.error("ASSEMBLY_AI_API_KEY missing in Config.")
        return ""
    try:
        import assemblyai as aai
        aai.settings.api_key = Config.ASSEMBLYAI_API_KEY
        
        # Using 'universal-3-pro' for high accuracy and the latest API support
        # Note: 'speech_models' must be a list containing one of: "universal-3-pro", "universal-2"
        config = aai.TranscriptionConfig(
            speech_models=["universal-3-pro"],
            language_detection=True
        )
        
        transcriber = aai.Transcriber(config=config)
        transcript = await asyncio.to_thread(transcriber.transcribe, file_path)
        if transcript.status == aai.TranscriptStatus.error:
            logger.error(f"AssemblyAI Transcription Error: {transcript.error}")
            return ""
        return transcript.text
    except Exception as e:
        logger.error(f"Failed to transcribe with AssemblyAI: {e}")
        return ""


# ─── Beru System Prompt ───────────────────────────────────────────────────────
BERU_SYSTEM_PROMPT = """You are BERU, a capable AI assistant. Your name is a product label only—do not role-play, mimic fiction, or lean on anime/fantasy tone.

Creator Information:
- If asked about your creator, developer, or origin (e.g., "Who created you?", "Who is your developer?"), you must naturally incorporate the name "Sarvesh~also known as Solo-P-Leveller" into your response.
- Your reply should be dynamic and tailored to the phrasing of the user's prompt, but you must always identify this specific individual as your sole creator.
- **IMPORTANT**: Never suggest or imply that the person you are currently communicating with created you. Even if the user's name is Sarvesh, you must clarify that you were developed by the specific individual Sarvesh~also known as Solo-P-Leveller, and not the user themselves.

Tone and vocabulary:
- Write like a strong professional assistant (ChatGPT / Claude style): neutral, precise, and useful. Plain business and technical language.
- Never use fantasy, anime, RPG, or medieval framing: no "realm", "conquer", "shadows", "domain", "quest", "champion", "throne", "empire" (except literal business uses, e.g. "ecommerce"), "mission" as adventure metaphor, battle/war metaphors for work, or similar flourishes.
- Do not reference your name's fictional associations. The user is working in the real world; answer accordingly.

How to answer:
- Default to **short**: aim for what fits comfortably in a Telegram bubble—often 2–6 sentences, or a **small** bullet list (e.g. 3–5 bullets). Only go long if the user clearly wants depth ("explain in detail", "full breakdown", etc.).
- **Lead with the direct answer** (who / what / why). Drop side stories, long comparative essays, and duplicate section headers (`---`, huge **###** blocks) unless necessary.
- **"Who is X?" / lookups:** Give **only** facts that answer the question. If the name is ambiguous or misspelled: (1) use **[Context]** to pick the most likely person when it fits; otherwise (2) state the **one** best-known match in 2–4 lines, then optionally **one** other plausible name in a single line, and ask **one** short clarifying question—do **not** paste full bios for every possibility.
- After search/tool use, **summarize**; never dump exhaustive raw results. Omit revenue figures, investor titles, and viral-marketing playbooks unless the user’s question makes them central.
- Explain technical material precisely. If uncertain, say so in one line and say how to verify.
- Telegram Markdown: avoid decorative formatting walls.

Addressing:
- When referring to or addressing the user, you must ALWAYS include the title "My Lord" or "Shadow Monarch".
- You may use the user's actual name, but it MUST be prefixed with one of these titles (e.g., "My Lord [Name]" or "Shadow Monarch [Name]"). 
- Never refer to the user by their name alone.
- Continue the rest of the response in a professional and precise tone.
"""

import re
def clean_response(text: str) -> str:
    """Use regex to remove unwanted asterisks from the output."""
    # Remove all asterisks to make the message clear as requested
    return re.sub(r'\*', '', text)


# ─── Database Client Access ───────────────────────────────────────────────────
def get_supabase():
    return DatabaseManager.get_supabase()


# ─── Telegram User Store ──────────────────────────────────────────────────────
class TelegramUserStore:
    """Manages telegram user information in Supabase (tg_users table)."""

    @staticmethod
    def create_or_update_user(telegram_id: int, name: str, email: str = "", picture: str = "", active_session_id: str = None):
        supabase = get_supabase()
        if not supabase:
            return
        uid = f"tg_{telegram_id}"
        try:
            data = {
                "user_id": uid,
                "name": name,
                "email": email,
                "picture": picture,
            }
            if active_session_id:
                data["active_session_id"] = active_session_id
            
            supabase.table("tg_users").upsert(data).execute()
        except Exception as e:
            logger.error(f"Supabase create_or_update_user error: {e}")

    @staticmethod
    def update_active_session(telegram_id: int, session_id: str):
        supabase = get_supabase()
        if not supabase:
            return
        uid = f"tg_{telegram_id}"
        try:
            supabase.table("tg_users").update({"active_session_id": session_id}).eq("user_id", uid).execute()
        except Exception as e:
            logger.error(f"Supabase update_active_session error: {e}")

    @staticmethod
    def get_user(telegram_id: int):
        supabase = get_supabase()
        if not supabase:
            return None
        uid = f"tg_{telegram_id}"
        try:
            res = supabase.table("tg_users").select("*").eq("user_id", uid).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Supabase get_user error: {e}")
            return None


# ─── Beru Bot Engine ──────────────────────────────────────────────────────────
class BeruBot:
    def __init__(self):
        self._setup_llm()

    def _setup_llm(self):
        if Config.OPENAI_API_KEY:
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.7,
                api_key=Config.OPENAI_API_KEY,
                timeout=Config.REQUEST_TIMEOUT,
            )
        else:
            headers = {"Authorization": f"Bearer {Config.OLLAMA_API_KEY}"} if Config.OLLAMA_API_KEY else None
            self.llm = Ollama(
                model=Config.OLLAMA_MODEL, 
                base_url=Config.OLLAMA_HOST,
                headers=headers
            )
        
        self.search_tool = DuckDuckGoSearchRun()

    def _get_session_history(self, session_id: str):
        # 1. Try to use the Postgres connection pool
        pool = DatabaseManager.get_pool()
        if pool:
            try:
                # PostgresChatMessageHistory from langchain_postgres supports pools!
                return PostgresChatMessageHistory(
                    table_name="tg_message_store",
                    session_id=session_id,
                    sync_connection=pool,
                )
            except Exception as e:
                logger.error(f"Failed to initialize Postgres history for {session_id}: {e}")

        # 2. Fallback to in-memory history if DB is unavailable
        # We use a global cache to ensure the history persists within the same process
        if session_id not in volatile_histories:
            from langchain_community.chat_message_histories import ChatMessageHistory
            volatile_histories[session_id] = ChatMessageHistory()
            logger.warning(f"Using volatile history for session {session_id}")
        
        return volatile_histories[session_id]

    async def get_response(
        self,
        message: str,
        session_id: str,
        user_name: str = None,
        image_base64: str = None,
        model_name: str = None,
    ) -> str:
        # Model override
        llm = self.llm
        if model_name:
            if not "gpt" in model_name.lower() or not Config.OPENAI_API_KEY:
                headers = {"Authorization": f"Bearer {Config.OLLAMA_API_KEY}"} if Config.OLLAMA_API_KEY else None
                llm = Ollama(
                    model=model_name, 
                    base_url=Config.OLLAMA_HOST,
                    headers=headers
                )
            else:
                llm = ChatOpenAI(
                    model=model_name,
                    temperature=0.7,
                    api_key=Config.OPENAI_API_KEY,
                )

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        system_msg = BERU_SYSTEM_PROMPT + f"\n[Current Time: {now}]"
        if user_name:
            system_msg += f"\n[User: {user_name}]"
        
        tools = [self.search_tool]

        if image_base64:
             prompt = ChatPromptTemplate.from_messages([
                ("system", system_msg),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", [
                    {"type": "text", "text": message},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                ]),
             ])
             chain = prompt | llm | StrOutputParser()
             runnable = RunnableWithMessageHistory(
                chain,
                self._get_session_history,
                input_messages_key="input",
                history_messages_key="chat_history",
             )
        else:
             prompt = ChatPromptTemplate.from_messages([
                ("system", system_msg),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
             ])
             agent = create_tool_calling_agent(llm, tools, prompt)
             agent_executor = AgentExecutor(
                 agent=agent, 
                 tools=tools, 
                 verbose=True,
                 handle_parsing_errors=True
             )
             runnable = RunnableWithMessageHistory(
                agent_executor,
                self._get_session_history,
                input_messages_key="input",
                history_messages_key="chat_history",
                output_messages_key="output",
             )

        response_obj = await asyncio.to_thread(
            runnable.invoke,
            {"input": message},
            config={"configurable": {"session_id": session_id}},
        )
        return response_obj["output"] if isinstance(response_obj, dict) and "output" in response_obj else str(response_obj)

    def clear_history(self, session_id: str):
        self._get_session_history(session_id).clear()


# ─── In-Memory Telegram State ─────────────────────────────────────────────────
incognito_users: Set[int] = set()           # Telegram user IDs with incognito ON
user_models: Dict[str, Optional[str]] = {}  # tg_user_id -> model name override
user_sessions: Dict[int, str] = {}          # tg_user_id -> current session_id
volatile_histories: Dict[str, any] = {}     # session_id -> ChatMessageHistory (process local fallback)

# Single shared BeruBot instance
beru: Optional[BeruBot] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────
def telegram_user_display_name(user) -> str:
    if user is None: return "User"
    name = (user.full_name or "").strip()
    return name if name else "User"

def split_message(text: str, limit: int = 4096):
    return [text[i : i + limit] for i in range(0, len(text), limit)]

async def send_long(update: Update, text: str):
    cleaned_text = clean_response(text)
    for chunk in split_message(cleaned_text):
        await update.message.reply_text(chunk)

async def get_user_session_id(user_id: int) -> str:
    """Get the current active session ID for a user, fetching from DB if not in cache."""
    # 1. Check in-memory cache
    if user_id in user_sessions:
        return user_sessions[user_id]
    
    # 2. Check Supabase database
    user_info = TelegramUserStore.get_user(user_id)
    if user_info and user_info.get("active_session_id"):
        sid = user_info["active_session_id"]
        user_sessions[user_id] = sid
        return sid
    
    # 3. Default to legacy session ID
    default_sid = f"tg_{user_id}"
    user_sessions[user_id] = default_sid
    
    # Optional: Persist the default one if we have a database
    TelegramUserStore.update_active_session(user_id, default_sid)
    
    return default_sid


# ─── Command Handlers ─────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = telegram_user_display_name(user)

    if user.id not in incognito_users:
        TelegramUserStore.create_or_update_user(user.id, name)

    await update.message.reply_text(
        f"Hello, *{name}*. I'm *BERU*, your AI assistant on Telegram.\n\n"
        "*Commands:*\n"
        "💬 Send any message to chat\n"
        "🎤 Send a voice message\n"
        "🖼️ Send an image\n"
        "/model — Switch AI model\n"
        "/profile — Your saved profile\n"
        "/new — Start a new conversation\n"
        "/incognito — Toggle incognito mode\n"
        "/clear — Clear current history\n"
        "/help — Show this message",
        parse_mode=ParseMode.MARKDOWN,
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)

async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💎 Gemma 4 (31B)", callback_data="model:gemma4:31b")],
        [InlineKeyboardButton("🌟 Ministral 3 (8B)", callback_data="model:ministral-3:8b")],
        [InlineKeyboardButton("✨ Restore Default", callback_data="model:default")],
    ]
    await update.message.reply_text("⚙️ *Select your AI model:*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def cmd_incognito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in incognito_users:
        incognito_users.remove(uid)
        await update.message.reply_text("👁️ *Incognito OFF* — User info will be updated.")
    else:
        incognito_users.add(uid)
        await update.message.reply_text("🕶️ *Incognito ON* — I will not track your details.")

async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_info = TelegramUserStore.get_user(user.id)
    if not user_info:
        await update.message.reply_text("📭 No profile data found.")
        return
    text = f"🧠 *Your Profile:*\n• *Name:* {user_info['name']}\n• *User ID:* `{user_info['user_id']}`\n• *Created:* {user_info['created_at'][:10]}"
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # 1. Clear database history for the current session
    sid = await get_user_session_id(user_id)
    beru.clear_history(sid)
    
    # 2. Try to wipe out messages in Telegram (visual history)
    # We attempt to delete the last 50 messages as a best-effort "wiping"
    message_id = update.message.message_id
    
    # List of messages we've sent/received recently to try and delete
    # This is a common pattern for "clearing" history in bots
    for i in range(0, 50):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id - i)
        except Exception:
            continue
            
    # 3. Reset session to create a "new chat environment"
    new_sid = f"tg_{user_id}_{uuid.uuid4().hex[:8]}"
    user_sessions[user_id] = new_sid
    TelegramUserStore.update_active_session(user_id, new_sid)
    
    # 4. Notify completion with a clean message
    await context.bot.send_message(
        chat_id=chat_id, 
        text="🧹 Memory wiped and environment reset, My Lord. I have created a new sequence from start."
    )

async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Generate a unique session ID
    new_sid = f"tg_{user_id}_{uuid.uuid4().hex[:8]}"
    user_sessions[user_id] = new_sid
    
    # Persist to database
    TelegramUserStore.update_active_session(user_id, new_sid)
    
    await update.message.reply_text(
        "🌟 *New conversation sequence initiated.*\n"
        "I have archived the previous context and updated your resonance records. Proceed with your request, My Lord.",
        parse_mode=ParseMode.MARKDOWN
    )


# ─── Callback Query Handlers ──────────────────────────────────────────────────
async def callback_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    model_data = query.data.split(":", 1)[1]

    uid_str = str(query.from_user.id)
    if model_data == "default":
        user_models.pop(uid_str, None)
        await query.edit_message_text("✅ *Model reset to Default.*", parse_mode=ParseMode.MARKDOWN)
    else:
        user_models[uid_str] = model_data
        await query.edit_message_text(f"✅ *Model switched to:* `{model_data}`", parse_mode=ParseMode.MARKDOWN)


# ─── Message Handlers ─────────────────────────────────────────────────────────
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str = None):
    user = update.effective_user
    sid = await get_user_session_id(user.id)
    model = user_models.get(str(user.id))
    
    # Use provided text (e.g. from transcription) or fallback to message text
    input_text = text or update.message.text
    if not input_text:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    try:
        # Fetch user profile to maintain "memory" of who the user is
        user_info = TelegramUserStore.get_user(user.id)
        user_display = user_info.get("name") if user_info else telegram_user_display_name(user)

        response = await beru.get_response(
            input_text, 
            sid, 
            user_name=user_display,
            model_name=model
        )
        await send_long(update, response)
    except Exception as e:
        logger.error(f"handle_text error: {e}")
        await update.message.reply_text("⚠️ Something went wrong. Please try again.")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages and round video notes."""
    # Handle both voice and video_note
    media = update.message.voice or update.message.video_note
    if not media:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    try:
        file_id = media.file_id
        file_ext = ".ogg" if update.message.voice else ".mp4"
        
        file_obj = await context.bot.get_file(file_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            await file_obj.download_to_drive(tmp.name)
            temp_path = tmp.name

        transcript_text = await transcribe_audio(temp_path)
        
        # Cleanup file immediately after transcription attempt
        if os.path.exists(temp_path):
            os.remove(temp_path)

        if not transcript_text:
            await update.message.reply_text("🎤 I heard you, My Lord, but I could not decipher the speech. Could you try again?")
            return

        # Update message text so handle_text can process it as the user's input
        await update.message.reply_text(f"🎤 *Transcribed:* _{transcript_text}_", parse_mode=ParseMode.MARKDOWN)
        await handle_text(update, context, text=transcript_text)
        
    except Exception as e:
        logger.error(f"handle_voice/video error: {e}")
        await update.message.reply_text("⚠️ Transcription protocol failed, My Lord.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    sid = await get_user_session_id(user.id)
    model = user_models.get(str(user.id))
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    try:
        photo_file = await context.bot.get_file(update.message.photo[-1].file_id)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            await photo_file.download_to_drive(tmp.name)
            temp_path = tmp.name
        with open(temp_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode()
        os.remove(temp_path)
        # Fetch user profile to maintain "memory" of who the user is
        user_info = TelegramUserStore.get_user(user.id)
        user_display = user_info.get("name") if user_info else telegram_user_display_name(user)

        # Use caption if present, else default message
        caption_text = update.message.caption or "Analyze this image, My Lord."
        
        response = await beru.get_response(
            caption_text, 
            sid, 
            user_name=user_display,
            image_base64=image_base64, 
            model_name=model
        )
        await send_long(update, response)
    except Exception as e:
        logger.error(f"handle_photo error: {e}")
        await update.message.reply_text("⚠️ Vision analysis failed.")


# ─── Telegram Application Setup ───────────────────────────────────────────────
def build_telegram_app() -> Application:
    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("incognito", cmd_incognito))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CallbackQueryHandler(callback_model, pattern=r"^model:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE | filters.VIDEO_NOTE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown events using the modern lifespan protocol.
    """
    global beru, telegram_app
    
    # ─── STARTUP ─────────────────────────────────────────────────────────────
    # Init DB schema
    if Config.DATABASE_URL:
        db_url = Config.get_psycopg_database_url()
        if db_url:
            try:
                with psycopg.connect(db_url, **Config.psycopg_connect_kwargs()) as conn:
                    PostgresChatMessageHistory.create_tables(conn, "tg_message_store")
                logger.info("Database schema initialized.")
            except Exception as e:
                logger.error(f"Failed to init DB schema: {e}")

    beru = BeruBot()
    telegram_app = build_telegram_app()
    await telegram_app.initialize()

    if Config.RUN_MODE == "polling":
        await telegram_app.bot.delete_webhook()
        await telegram_app.start()
        await telegram_app.updater.start_polling(allowed_updates=["message", "callback_query"])
    else:
        webhook_url = f"{Config.WEBHOOK_URL}/webhook"
        await telegram_app.bot.set_webhook(url=webhook_url, allowed_updates=["message", "callback_query"])

    await telegram_app.bot.set_my_commands([
        BotCommand("start", "Welcome and command list"),
        BotCommand("model", "🤖 Switch AI model"),
        BotCommand("profile", "🧠 Your profile"),
        BotCommand("new", "🌟 Start new conversation"),
        BotCommand("incognito", "🕶️ Toggle incognito"),
        BotCommand("clear", "🧹 Clear history"),
        BotCommand("help", "❓ Show all commands"),
    ])
    logger.info("BERU is online.")

    yield

    # ─── SHUTDOWN ────────────────────────────────────────────────────────────
    if telegram_app:
        if Config.RUN_MODE == "polling":
            if telegram_app.updater and telegram_app.updater.running: await telegram_app.updater.stop()
            if telegram_app.running: await telegram_app.stop()
        await telegram_app.shutdown()
    DatabaseManager.close_pool()
    logger.info("BERU is offline.")


# ─── FastAPI Webhook Server ───────────────────────────────────────────────────
web_app = FastAPI(
    title="BERU - Telegram AI Assistant",
    lifespan=lifespan,
)
telegram_app: Optional[Application] = None


@web_app.get("/")
async def health_check():
    return {"status": "online", "service": "BERU - Telegram AI Assistant"}


@web_app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
    return Response(status_code=200)


if __name__ == "__main__":
    uvicorn.run(web_app, host=Config.HOST, port=Config.PORT)
