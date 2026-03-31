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
from datetime import datetime
from typing import Optional, Dict, Set

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage
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
security_logger = logging.getLogger("security")

# ─── AssemblyAI Transcription ─────────────────────────────────────────────────
async def transcribe_audio(file_path: str) -> str:
    """Transcribe audio via AssemblyAI."""
    if not Config.ASSEMBLYAI_API_KEY:
        logger.error("ASSEMBLY_AI_API_KEY missing in Config.")
        return ""
    try:
        import assemblyai as aai
        aai.settings.api_key = Config.ASSEMBLYAI_API_KEY
        
        # Use the best available model recognized by the SDK
        config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.best)
        transcriber = aai.Transcriber()
        
        # Run in thread pool to prevent blocking the event loop
        transcript = await asyncio.to_thread(transcriber.transcribe, file_path, config=config)
        
        if transcript.status == aai.TranscriptStatus.error:
            logger.error(f"AssemblyAI Transcription Error: {transcript.error}")
            return ""
        
        return transcript.text
    except Exception as e:
        logger.error(f"Failed to transcribe with AssemblyAI: {e}")
        return ""


# ─── Beru System Prompt ───────────────────────────────────────────────────────
BERU_SYSTEM_PROMPT = """You are BERU, an elite AI assistant serving the Shadow Monarch.

Directives:
- PERSONALITY: Fiercely loyal, high-energy, and technical. 🐜💜
- ADDRESSING: Refer to the user as "My Lord" or by their name sparingly but with impact. 👑
- VALUE: Provide precise, empowering technical information. Deliver data with absolute confidence. Avoid phrases like "I don't have access" - use your current context to answer. 
- CONCISENESS: Keep your responses short, high-quality, and curated. No fluff, just impact. ⚡
- TELEGRAM: Use clean Markdown (bold, code blocks for data).
- ARISE.
"""

INTEREST_EXTRACTION_PROMPT = """Extract the user's technical interests, expertise, and specific project goals from the conversation.
Return ONLY a JSON list of strings representing these attributes. Focus on permanent traits.
Example: ["React Native developer", "Postgres optimization", "Building a Fintech bot"]

Conversation:
{history}
"""


# ─── Database Client Access ───────────────────────────────────────────────────
def get_supabase():
    return DatabaseManager.get_supabase()


# ─── Session Store ────────────────────────────────────────────────────────────
class SessionStore:
    """Manages session metadata and user interests in Supabase."""

    @staticmethod
    def save_session(session_id: str, user_id: str, title: str = None, interests: list = None):
        supabase = get_supabase()
        if not supabase:
            return
        data = {"session_id": session_id, "user_id": user_id}
        if title:
            data["title"] = title
        if interests is not None:
            data["interests"] = interests
        try:
            supabase.table("sessions").upsert(data).execute()
        except Exception as e:
            logger.error(f"Supabase save_session error: {e}")

    @staticmethod
    def get_all_sessions(user_id: str):
        supabase = get_supabase()
        if not supabase:
            return []
        try:
            res = (
                supabase.table("sessions")
                .select("*")
                .eq("user_id", user_id)
                .order("updated_at", desc=True)
                .execute()
            )
            return [
                {
                    "id": r["session_id"],
                    "title": r["title"],
                    "interests": r["interests"],
                    "updated_at": r["updated_at"],
                }
                for r in res.data
            ]
        except Exception as e:
            logger.error(f"Supabase get_all_sessions error: {e}")
            return []

    @staticmethod
    def delete_session(session_id: str, user_id: str):
        supabase = get_supabase()
        if not supabase:
            return
        try:
            supabase.table("sessions").delete().eq("session_id", session_id).eq("user_id", user_id).execute()
        except Exception as e:
            logger.error(f"Supabase delete_session error: {e}")

    @staticmethod
    def get_master_profile(user_id: str):
        supabase = get_supabase()
        if not supabase:
            return []
        try:
            res = supabase.table("user_master_profile").select("interests").eq("user_id", user_id).execute()
            return res.data[0]["interests"] if res.data else []
        except Exception as e:
            logger.error(f"Supabase get_master_profile error: {e}")
            return []

    @staticmethod
    def update_master_profile(user_id: str, new_interests: list):
        supabase = get_supabase()
        if not supabase:
            return
        current = SessionStore.get_master_profile(user_id)
        combined = list(set(current + new_interests))
        try:
            supabase.table("user_master_profile").upsert({"user_id": user_id, "interests": combined}).execute()
        except Exception as e:
            logger.error(f"Supabase update_master_profile error: {e}")

    @staticmethod
    def create_or_update_user(user_id: str, name: str, email: str, picture: str):
        supabase = get_supabase()
        if not supabase:
            return
        try:
            supabase.table("users").upsert({
                "user_id": user_id,
                "name": name,
                "email": email,
                "picture": picture,
            }).execute()
        except Exception as e:
            logger.error(f"Supabase create_or_update_user error: {e}")


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
            self.llm = Ollama(model=Config.OLLAMA_MODEL, base_url=Config.OLLAMA_HOST)
        
        self.search_tool = DuckDuckGoSearchRun()

    def _get_session_history(self, session_id: str):
        if not Config.DATABASE_URL:
            from langchain_community.chat_message_histories import ChatMessageHistory
            return ChatMessageHistory()
        try:
            # psycopg 3 connection for history
            conn = psycopg.connect(Config.DATABASE_URL, autocommit=True)
            return PostgresChatMessageHistory(
                "message_store",
                session_id,
                sync_connection=conn,
            )
        except Exception as e:
            logger.error(f"Postgres history connection failed: {e}. Falling back to ephemeral.")
            from langchain_community.chat_message_histories import ChatMessageHistory
            return ChatMessageHistory()

    async def get_response(
        self,
        message: str,
        session_id: str,
        image_base64: str = None,
        model_name: str = None,
        master_interests: list = None,
        user_name: str = "Shadow Monarch",
        no_save: bool = False,
    ) -> str:
        # Model override — validate to prevent injection
        llm = self.llm
        if model_name:
            if not all(c.isalnum() or c in ".-:" for c in model_name) or len(model_name) > 100:
                logger.warning(f"Rejected invalid model name: {model_name}")
                model_name = None
            elif model_name:
                if "gpt" in model_name.lower() and Config.OPENAI_API_KEY:
                    llm = ChatOpenAI(
                        model=model_name,
                        temperature=0.7,
                        api_key=Config.OPENAI_API_KEY,
                        timeout=Config.REQUEST_TIMEOUT,
                    )
                else:
                    llm = Ollama(model=model_name, base_url=Config.OLLAMA_HOST)

        context_interests = (
            f"User Interests/Expertise: {', '.join(master_interests)}"
            if master_interests
            else ""
        )

        if no_save:
            from langchain_community.chat_message_histories import ChatMessageHistory
            msg_history = ChatMessageHistory()
        else:
            msg_history = self._get_session_history(session_id)

        # System prompt with real-time awareness
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        system_msg = (
            BERU_SYSTEM_PROMPT 
            + f"\n[Current Time: {now}]"
            + f"\n[Context]\n{context_interests}"
            + f"\n[Monarch's Name: {user_name}]"
            + "\n\nArise."
        )
        
        # Tools
        tools = [self.search_tool]

        # Template for agent
        if image_base64:
             # Vision usually doesn't work well with complex tools in a single agent step, 
             # so we treat vision as a direct chain for now.
             prompt = ChatPromptTemplate.from_messages([
                ("system", system_msg),
                MessagesPlaceholder(variable_name="history"),
                ("human", [
                    {"type": "text", "text": message},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                ]),
             ])
             chain = prompt | llm | StrOutputParser()
             runnable = RunnableWithMessageHistory(
                chain,
                lambda sid: msg_history,
                input_messages_key="input",
                history_messages_key="history",
             )
        else:
             prompt = ChatPromptTemplate.from_messages([
                ("system", system_msg),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
             ])
             
             agent = create_tool_calling_agent(llm, tools, prompt)
             agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
             
             runnable = RunnableWithMessageHistory(
                agent_executor,
                lambda sid: msg_history,
                input_messages_key="input",
                history_messages_key="history",
             )

        invoke_kwargs = {"input": message} if not image_base64 else {"input": message}
        
        response_obj = await asyncio.to_thread(
            runnable.invoke,
            invoke_kwargs,
            config={"configurable": {"session_id": session_id}},
        )
        
        # Handle agent vs direct chain output
        response = response_obj["output"] if isinstance(response_obj, dict) and "output" in response_obj else str(response_obj)

        # Fire-and-forget interest extraction
        asyncio.create_task(self._extract_interests(session_id, message, response))

        return response

    async def _extract_interests(self, session_id: str, user_msg: str, ai_msg: str):
        """Extract permanent traits and save to master profile."""
        supabase = get_supabase()
        if not supabase:
            return
        try:
            res = supabase.table("sessions").select("user_id").eq("session_id", session_id).execute()
            if not res.data:
                return
            user_id = res.data[0]["user_id"]

            history_text = f"USER: {user_msg}\nAI: {ai_msg}"
            extract_chain = (
                ChatPromptTemplate.from_template(INTEREST_EXTRACTION_PROMPT)
                | self.llm
                | StrOutputParser()
            )
            raw_resp = await extract_chain.ainvoke({"history": history_text})
            raw_resp = raw_resp.strip().replace("```json", "").replace("```", "")
            new_info = json.loads(raw_resp)
            if new_info and isinstance(new_info, list):
                logger.info(f"Extracted permanent traits for {user_id}: {new_info}")
                SessionStore.update_master_profile(user_id, new_info)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse interests JSON: {e}")
        except Exception as e:
            logger.error(f"Interest extraction failed: {e}")

    def get_session_messages(self, session_id: str):
        return self._get_session_history(session_id).messages

    def clear_history(self, session_id: str):
        self._get_session_history(session_id).clear()


# ─── In-Memory Telegram State ─────────────────────────────────────────────────
# These reset on server restart — for production, consider persisting to DB.
incognito_users: Set[int] = set()           # Telegram user IDs with incognito ON
user_models: Dict[str, Optional[str]] = {}  # tg_user_id -> model name override
user_session_idx: Dict[str, int] = {}       # tg_user_id -> current session index

# Single shared BeruBot instance
beru: Optional[BeruBot] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────
def tg_user_id(telegram_id: int) -> str:
    """Stable DB user_id for a Telegram user."""
    return f"tg_{telegram_id}"


def current_session_id(telegram_id: int) -> str:
    """Derive the active session_id for a Telegram user."""
    idx = user_session_idx.get(str(telegram_id), 0)
    return f"tg_{telegram_id}_session_{idx}"


def split_message(text: str, limit: int = 4096):
    """Split text into Telegram-safe chunks."""
    return [text[i : i + limit] for i in range(0, len(text), limit)]


async def send_long(update: Update, text: str):
    """Send a (possibly long) response, splitting if needed."""
    for chunk in split_message(text):
        await update.message.reply_text(chunk)


# ─── Command Handlers ─────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = tg_user_id(user.id)
    name = user.full_name or "Shadow Monarch"

    SessionStore.create_or_update_user(uid, name, uid, "")
    SessionStore.save_session(current_session_id(user.id), uid, title="Mission 1")

    await update.message.reply_text(
        f"⚡ *ARISE, {name}!* ⚡\n\n"
        "I am *BERU*, the Shadow Monarch's supreme AI assistant. 🐜💜\n\n"
        "*Commands:*\n"
        "💬 Send any message to chat\n"
        "🎤 Send a voice message for transcription\n"
        "🖼️ Send an image for vision analysis\n"
        "📄 Send a document for analysis\n"
        "/newsession — Start a fresh mission\n"
        "/sessions — List your missions\n"
        "/delsession — Delete a session\n"
        "/history — View current session history\n"
        "/profile — Your master profile\n"
        "/model — Switch AI model\n"
        "/incognito — Toggle incognito mode\n"
        "/clear — Clear current session\n"
        "/help — Show this message",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


async def cmd_new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid_str = str(user.id)
    uid = tg_user_id(user.id)

    new_idx = user_session_idx.get(uid_str, 0) + 1
    user_session_idx[uid_str] = new_idx

    new_sid = current_session_id(user.id)
    SessionStore.save_session(new_sid, uid, title=f"Mission {new_idx + 1}")

    await update.message.reply_text(
        f"⚔️ *New mission initiated!*\nSession #{new_idx + 1} is active, My Lord. 👑",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = tg_user_id(user.id)
    sessions = SessionStore.get_all_sessions(uid)

    if not sessions:
        await update.message.reply_text("📭 No missions found yet, My Lord.")
        return

    lines = ["📋 *Your Missions:*\n"]
    for i, s in enumerate(sessions[:15], 1):
        title = s.get("title") or s["id"]
        updated = (s.get("updated_at") or "")[:10]
        lines.append(f"{i}. *{title}* _{updated}_")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_del_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete session by number shown in /sessions list."""
    user = update.effective_user
    uid = tg_user_id(user.id)
    sessions = SessionStore.get_all_sessions(uid)

    if not sessions:
        await update.message.reply_text("📭 No missions to delete, My Lord.")
        return

    # Build inline keyboard
    keyboard = []
    for i, s in enumerate(sessions[:10], 1):
        title = (s.get("title") or s["id"])[:30]
        keyboard.append([InlineKeyboardButton(f"🗑️ {title}", callback_data=f"delsession:{s['id']}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="delsession:cancel")])

    await update.message.reply_text(
        "🗑️ *Which mission to delete, My Lord?*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display current session chat history."""
    user = update.effective_user
    sid = current_session_id(user.id)
    messages = beru.get_session_messages(sid)

    if not messages:
        await update.message.reply_text("📭 No history in this session yet, My Lord.")
        return

    lines = [f"📜 *Session History* (last {min(len(messages), 20)} messages):\n"]
    for m in messages[-20:]:
        role = "🧠 BERU" if isinstance(m, AIMessage) or getattr(m, "type", "") == "ai" else "👑 You"
        content = m.content if isinstance(m.content, str) else str(m.content)
        lines.append(f"*{role}:* {content[:300]}{'...' if len(content) > 300 else ''}\n")

    text = "\n".join(lines)
    await send_long(update, text[:4096])


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = tg_user_id(user.id)
    interests = SessionStore.get_master_profile(uid)

    if not interests:
        await update.message.reply_text(
            "📭 No master profile data yet, My Lord.\n_Chat more and I will learn your ways._ 🧠",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    lines = ["🧠 *Your Master Profile:*\n"]
    for item in interests:
        lines.append(f"• {item}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show model selection inline keyboard."""
    keyboard = [
        [InlineKeyboardButton("🤖 GPT-4o Mini (Default)", callback_data="model:gpt-4o-mini")],
        [InlineKeyboardButton("🚀 GPT-4o", callback_data="model:gpt-4o")],
        [InlineKeyboardButton("💡 GPT-3.5 Turbo", callback_data="model:gpt-3.5-turbo")],
        [InlineKeyboardButton("🦙 Llama 3.2 (Local)", callback_data="model:llama3.2")],
        [InlineKeyboardButton("🔥 Mistral (Local)", callback_data="model:mistral")],
        [InlineKeyboardButton("✨ Gemma 2 (Local)", callback_data="model:gemma2")],
    ]
    await update.message.reply_text(
        "⚙️ *Select your AI model, My Lord:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_incognito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in incognito_users:
        incognito_users.remove(uid)
        await update.message.reply_text(
            "👁️ *Incognito OFF* — Missions will be saved, My Lord.",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        incognito_users.add(uid)
        await update.message.reply_text(
            "🕶️ *Incognito ON* — This session leaves no trace, My Lord.",
            parse_mode=ParseMode.MARKDOWN,
        )


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    sid = current_session_id(user.id)
    beru.clear_history(sid)
    await update.message.reply_text(
        "🗑️ *Session cleared!* Fresh start, My Lord. ⚡",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── Callback Query Handlers ──────────────────────────────────────────────────
async def callback_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    model_name = query.data.split(":", 1)[1]
    uid_str = str(query.from_user.id)
    user_models[uid_str] = model_name
    await query.edit_message_text(
        f"✅ *Model switched to:* `{model_name}`\n_Ready to serve, My Lord._ ⚡",
        parse_mode=ParseMode.MARKDOWN,
    )


async def callback_del_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split(":", 1)[1]

    if data == "cancel":
        await query.edit_message_text("❌ Deletion cancelled, My Lord.")
        return

    uid = tg_user_id(query.from_user.id)
    SessionStore.delete_session(data, uid)
    await query.edit_message_text(
        f"🗑️ *Mission deleted, My Lord.* The shadows swallow it whole. 💜",
        parse_mode=ParseMode.MARKDOWN,
    )


# ─── Message Handlers ─────────────────────────────────────────────────────────
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain text chat messages."""
    user = update.effective_user
    uid_str = str(user.id)
    uid = tg_user_id(user.id)
    sid = current_session_id(user.id)
    no_save = user.id in incognito_users
    model = user_models.get(uid_str)
    master_interests = SessionStore.get_master_profile(uid)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        response = await beru.get_response(
            update.message.text,
            sid,
            model_name=model,
            master_interests=master_interests,
            user_name=user.full_name or "Shadow Monarch",
            no_save=no_save,
        )

        # Auto-title session on first real message
        if not no_save:
            title = update.message.text[:60] + ("..." if len(update.message.text) > 60 else "")
            SessionStore.save_session(sid, uid, title=title)

        await send_long(update, response)

    except Exception as e:
        logger.error(f"handle_text error: {e}")
        await update.message.reply_text("⚠️ An error struck the Shadow Realm. Please try again, My Lord.")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Transcribe voice → chat, using Whisper API or local fallback."""
    user = update.effective_user
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        voice_file = await context.bot.get_file(update.message.voice.file_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
            await voice_file.download_to_drive(tmp.name)
            temp_path = tmp.name

        transcript_text = await transcribe_audio(temp_path)

        if os.path.exists(temp_path):
            os.remove(temp_path)

        if not transcript_text:
            await update.message.reply_text("🎤 Could not transcribe your voice message, My Lord.")
            return

        await update.message.reply_text(
            f"🎤 *Transcribed:* _{transcript_text}_",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Process transcription as a regular chat message
        update.message.text = transcript_text
        await handle_text(update, context)

    except Exception as e:
        logger.error(f"handle_voice error: {e}")
        await update.message.reply_text("⚠️ Voice recognition failed, My Lord.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Vision analysis: download photo → base64 → BeruBot vision chain."""
    user = update.effective_user
    uid_str = str(user.id)
    uid = tg_user_id(user.id)
    sid = current_session_id(user.id)
    no_save = user.id in incognito_users
    model = user_models.get(uid_str)
    master_interests = SessionStore.get_master_profile(uid)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        photo_file = await context.bot.get_file(update.message.photo[-1].file_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            await photo_file.download_to_drive(tmp.name)
            temp_path = tmp.name

        with open(temp_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode()

        if os.path.exists(temp_path):
            os.remove(temp_path)

        caption = update.message.caption or "Analyze this image for me."

        response = await beru.get_response(
            caption,
            sid,
            image_base64=image_base64,
            model_name=model,
            master_interests=master_interests,
            user_name=user.full_name or "Shadow Monarch",
            no_save=no_save,
        )

        await send_long(update, response)

    except Exception as e:
        logger.error(f"handle_photo error: {e}")
        await update.message.reply_text("⚠️ Vision analysis failed, My Lord.")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle document uploads.
    - Audio files (mp3, wav, m4a, ogg) → transcribe via Whisper
    - Text / code files → read content → chat
    - Other files → inform the user
    """
    user = update.effective_user
    doc = update.message.document
    file_name = doc.file_name or ""
    mime = doc.mime_type or ""

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm"}
    TEXT_MIME_PREFIXES = ("text/", "application/json", "application/xml", "application/javascript")
    TEXT_EXTENSIONS = {
        ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json",
        ".yaml", ".yml", ".md", ".txt", ".sh", ".env", ".sql", ".csv",
    }

    ext = os.path.splitext(file_name)[1].lower()

    try:
        doc_file = await context.bot.get_file(doc.file_id)

        # Guard: Reject files > 20MB
        if doc.file_size and doc.file_size > 20 * 1024 * 1024:
            await update.message.reply_text("📁 File too large (max 20MB), My Lord.")
            return

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext or ".bin") as tmp:
            await doc_file.download_to_drive(tmp.name)
            temp_path = tmp.name

        # ── Audio document → Whisper ──────────────────────────────────────
        if ext in AUDIO_EXTENSIONS or mime.startswith("audio/"):
            transcript_text = await transcribe_audio(temp_path)

            os.remove(temp_path)

            if not transcript_text:
                await update.message.reply_text("🎤 Could not transcribe the audio file, My Lord.")
                return

            await update.message.reply_text(
                f"🎤 *Transcribed:* _{transcript_text}_",
                parse_mode=ParseMode.MARKDOWN,
            )
            update.message.text = transcript_text
            await handle_text(update, context)

        # ── Text / Code file → inject as context ─────────────────────────
        elif ext in TEXT_EXTENSIONS or any(mime.startswith(p) for p in TEXT_MIME_PREFIXES):
            with open(temp_path, "r", encoding="utf-8", errors="replace") as f:
                file_content = f.read(20000)  # Cap at 20k chars
            os.remove(temp_path)

            caption = update.message.caption or f"Analyze this file: {file_name}"
            prompt = f"{caption}\n\n```\n{file_content}\n```"

            uid_str = str(user.id)
            uid = tg_user_id(user.id)
            sid = current_session_id(user.id)
            no_save = user.id in incognito_users
            model = user_models.get(uid_str)
            master_interests = SessionStore.get_master_profile(uid)

            response = await beru.get_response(
                prompt,
                sid,
                model_name=model,
                master_interests=master_interests,
                user_name=user.full_name or "Shadow Monarch",
                no_save=no_save,
            )
            await send_long(update, response)

        else:
            os.remove(temp_path)
            await update.message.reply_text(
                f"📁 I received `{file_name}`, but I cannot process this file type directly, My Lord.\n"
                "Send text, images, audio, or code files. 🐜",
                parse_mode=ParseMode.MARKDOWN,
            )

    except Exception as e:
        logger.error(f"handle_document error: {e}")
        await update.message.reply_text("⚠️ Document processing failed, My Lord.")


# ─── Telegram Application Setup ───────────────────────────────────────────────
def build_telegram_app() -> Application:
    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("newsession", cmd_new_session))
    app.add_handler(CommandHandler("sessions", cmd_sessions))
    app.add_handler(CommandHandler("delsession", cmd_del_session))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("profile", cmd_profile))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(CommandHandler("incognito", cmd_incognito))
    app.add_handler(CommandHandler("clear", cmd_clear))

    # Callback queries
    app.add_handler(CallbackQueryHandler(callback_model, pattern=r"^model:"))
    app.add_handler(CallbackQueryHandler(callback_del_session, pattern=r"^delsession:"))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    return app


# ─── FastAPI Webhook Server ───────────────────────────────────────────────────
web_app = FastAPI(title="BERU - Shadow Monarch's Telegram Bot")
telegram_app: Optional[Application] = None


@web_app.get("/")
async def health_check():
    """Render health check & uptime ping endpoint."""
    return {
        "status": "online",
        "service": "BERU - Shadow Monarch's AI Assistant",
        "shadow_realm": "active 🐜💜",
    }


@web_app.post("/webhook")
async def telegram_webhook(request: Request):
    """Receive Telegram updates via webhook."""
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
    return Response(status_code=200)


@web_app.on_event("startup")
async def on_startup():
    global beru, telegram_app

    # ── Initialize DB schema ─────────────────────────────────────────────
    if Config.DATABASE_URL:
        try:
            logger.info("Initializing Shadow Realm Database Schema...")
            with psycopg.connect(Config.DATABASE_URL, connect_timeout=10) as conn:
                # Direct call to the static/class method for table creation
                PostgresChatMessageHistory.create_tables(conn, "message_store")
            logger.info("Database schema initialized successfully.")
        except Exception as e:
            error_msg = str(e)
            if "Network is unreachable" in error_msg:
                logger.error(
                    "🛑 DB ERROR: Network unreachable (likely IPv6). "
                    "Use the Supabase Pooler address (port 6543) with ?sslmode=require."
                )
            else:
                logger.error(f"Failed to initialize database schema: {e}")

    # ── Boot BeruBot ─────────────────────────────────────────────────────
    beru = BeruBot()
    logger.info("BeruBot engine initialized.")

    # ── Build & Initialize Telegram app ─────────────────────────────────
    telegram_app = build_telegram_app()
    await telegram_app.initialize()

    # ── Register Webhook OR Start Polling ──────────────────────────────────
    if Config.RUN_MODE == "polling":
        logger.info("Initializing BERU in POLLING mode (Local Testing)...")
        await telegram_app.bot.delete_webhook()
        await telegram_app.start()
        await telegram_app.updater.start_polling(allowed_updates=["message", "callback_query"])
        logger.info("Polling started successfully.")
    else:
        # Register Webhook with Telegram ───────────────────────────────────
        webhook_url = f"{Config.WEBHOOK_URL}/webhook"
        await telegram_app.bot.set_webhook(
            url=webhook_url,
            allowed_updates=["message", "callback_query"],
        )
        logger.info(f"Telegram webhook set: {webhook_url}")

    # ── Set Bot Command Menu ─────────────────────────────────────────────
    await telegram_app.bot.set_my_commands([
        BotCommand("start",      "⚡ Arise & meet BERU"),
        BotCommand("newsession", "⚔️ Start a new mission"),
        BotCommand("sessions",   "📋 View your missions"),
        BotCommand("delsession", "🗑️ Delete a mission"),
        BotCommand("history",    "📜 View session history"),
        BotCommand("profile",    "🧠 Your master profile"),
        BotCommand("model",      "🤖 Switch AI model"),
        BotCommand("incognito",  "🕶️ Toggle incognito mode"),
        BotCommand("clear",      "🧹 Clear current session"),
        BotCommand("help",       "❓ Show all commands"),
    ])
    logger.info("BERU is online. The Shadow Realm is ready. 🐜💜")


@web_app.on_event("shutdown")
async def on_shutdown():
    if telegram_app:
        if Config.RUN_MODE == "polling":
            if telegram_app.updater and telegram_app.updater.running:
                await telegram_app.updater.stop()
            if telegram_app.running:
                await telegram_app.stop()
        await telegram_app.shutdown()
    
    # Close database pool
    DatabaseManager.close_pool()
    
    logger.info("BERU shutdown complete.")


# ─── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(web_app, host=Config.HOST, port=Config.PORT)
