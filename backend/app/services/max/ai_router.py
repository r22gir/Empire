"""MAX AI Router - Multi-provider tiered routing: xAI Grok, Claude, Gemini, OpenAI, Groq, OpenClaw, Ollama with streaming & vision."""
import os
import json
import httpx
import base64
import subprocess
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, AsyncGenerator, Tuple
from pathlib import Path
import logging
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

logger = logging.getLogger("max.ai_router")

class AIModel(Enum):
    GROK = "grok"
    CLAUDE = "claude"
    CLAUDE_OPUS = "claude-opus-4-6"
    CLAUDE_SONNET = "claude-sonnet-4-6"
    GROQ = "groq"
    OPENCLAW = "openclaw"
    OLLAMA = "ollama-llama"
    GEMINI = "gemini"
    OPENAI_NANO = "gpt-4.1-nano"
    OPENAI_MINI = "gpt-4o-mini"
    OPENAI_4O = "gpt-4o"


class TaskComplexity(Enum):
    SIMPLE = "simple"      # hi, status, lookup, greeting, thanks, ok, yes, no
    MODERATE = "moderate"   # summary, report, list, CRM, show, recent, brief
    COMPLEX = "complex"    # analyze, calculate, quote, why, explain, compare, strategy
    CRITICAL = "critical"  # fix, edit, code, file, git, build, deploy, read ~/

# ── Conversation model floor ────────────────────────────────────────
# Once a conversation escalates to a tier, it stays at least that tier
# for the rest of the session.  Maps conversation_id → highest complexity.
_COMPLEXITY_ORDER = {TaskComplexity.SIMPLE: 0, TaskComplexity.MODERATE: 1,
                     TaskComplexity.COMPLEX: 2, TaskComplexity.CRITICAL: 3}
_conversation_floors: dict[str, TaskComplexity] = {}


def apply_conversation_floor(conversation_id: str | None, complexity: TaskComplexity) -> TaskComplexity:
    """Enforce model floor: never downgrade within a conversation."""
    if not conversation_id:
        return complexity
    prev = _conversation_floors.get(conversation_id)
    if prev and _COMPLEXITY_ORDER.get(prev, 0) > _COMPLEXITY_ORDER.get(complexity, 0):
        logger.info(f"[floor] Holding {conversation_id[:8]} at {prev.value} (would have been {complexity.value})")
        return prev
    _conversation_floors[conversation_id] = complexity
    return complexity


def classify_complexity(message: str, *, source: str = "", turn_count: int = 0) -> TaskComplexity:
    """Instant complexity classification — keyword matching + message length. No AI call.

    Parameters
    ----------
    source : str
        Where the message came from (e.g. "voice", "web", "telegram").
        Voice input gets escalated to MODERATE minimum.
    turn_count : int
        Number of back-and-forth messages in current session on same topic.
        3+ turns without resolution → escalate to MODERATE.
    """
    msg = message.lower().strip()
    words = msg.split()

    # Greetings set — used by both voice and standard classification
    simple_greetings = {'hi', 'hello', 'hey', 'thanks', 'thank you', 'bye',
                        'good morning', 'good night', 'good evening',
                        "what's up", 'whats up', 'sup', 'yo'}

    # CRITICAL — code/file operations
    critical_keywords = ['fix', 'edit', 'code', 'file', 'git', 'build', 'deploy', 'commit', 'push', 'pull', 'merge', 'rebase', 'scaffold', 'refactor']
    if any(kw in words for kw in critical_keywords) or msg.startswith('read ~/') or msg.startswith('cat ') or '```' in msg:
        return TaskComplexity.CRITICAL

    # ── Escalation checks (floor = MODERATE) ──

    # Memory/search queries need contextual reasoning
    memory_patterns = ['what did i', 'my request', 'find my', 'remember when',
                       'search for', 'look up', 'what was', 'did i ask',
                       'last time', 'previous conversation', 'earlier today',
                       'search our', 'search conversation', 'find conversation']
    if any(p in msg for p in memory_patterns):
        return TaskComplexity.COMPLEX

    # Tool-triggering messages — Gemini Flash can't handle tool results well
    tool_trigger_patterns = [
        'create a task', 'create task', 'add a task', 'new task',
        'create quote', 'create a quote', 'new quote',
        'create invoice', 'send invoice', 'send email',
        'search memory', 'search memories', 'check my',
        'look up customer', 'find customer', 'customer list',
        'schedule', 'set reminder', 'remind me',
        'run report', 'generate report', 'show report',
        'post to', 'send to telegram', 'send message',
        'check my email', 'check email', 'check inbox', 'read my email',
        'any new email', 'unread email', 'new emails', 'check mail',
    ]
    if any(p in msg for p in tool_trigger_patterns):
        return TaskComplexity.MODERATE

    # Voice transcriptions are less structured — need smarter model
    if source == "voice":
        # Only exact greetings stay SIMPLE for voice
        if msg.rstrip('!., ') in simple_greetings:
            return TaskComplexity.SIMPLE
        return TaskComplexity.MODERATE  # everything else from voice → MODERATE min

    # Multi-turn without resolution → escalate
    if turn_count >= 3:
        return TaskComplexity.MODERATE

    # ── Standard classification ──

    # SIMPLE — ONLY exact greetings (Gemini Flash territory)
    # Must be an EXACT match after stripping punctuation — no questions, no requests
    stripped = msg.rstrip('!., ')
    if stripped in simple_greetings:
        return TaskComplexity.SIMPLE

    # COMPLEX — analytical tasks
    complex_keywords = ['analyze', 'analysis', 'calculate', 'quote', 'why', 'explain', 'compare', 'strategy', 'optimize', 'recommend', 'evaluate', 'financial', 'pricing', 'revenue', 'profit']
    if any(kw in msg for kw in complex_keywords):
        return TaskComplexity.COMPLEX

    # MODERATE — everything else (Grok territory)
    return TaskComplexity.MODERATE


@dataclass
class AIMessage:
    role: str
    content: str
    image_path: Optional[str] = None

@dataclass
class AIResponse:
    content: str
    model_used: str
    fallback_used: bool = False

from .system_prompt import get_system_prompt
from .desk_prompt import get_desk_system_prompt
from .token_tracker import token_tracker

# Per-desk model routing — overrides primary model when desk is specified
DESK_MODEL_ROUTING = {
    "codeforge": AIModel.CLAUDE_OPUS,     # Atlas — code quality critical
    "analytics": AIModel.CLAUDE_SONNET,   # Raven — data analysis
    "quality": AIModel.CLAUDE_SONNET,     # Phoenix — accuracy critical
    "innovation": AIModel.CLAUDE_SONNET,  # Spark — creative reasoning
    "forge": AIModel.GROQ,               # Kai — routine ops, speed
    "sales": AIModel.GROQ,              # Aria — needs reasoning, not just lookups
    "costtracker": AIModel.OPENAI_NANO,  # Cipher — basic expense math
    "it": AIModel.GROQ,                  # Orion — health checks routine
    "marketing": AIModel.GROQ,          # Nova — content needs reasoning
    "support": AIModel.OPENAI_MINI,      # Fast responses
    # All others fall through to complexity-based routing
}


class AIRouter:
    def __init__(self):
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.xai_key = os.getenv("XAI_API_KEY", "")
        self.groq_key = os.getenv("GROQ_API_KEY", "")
        self.gemini_key = os.getenv("GOOGLE_GEMINI_API_KEY", "")
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        # Priority: xAI Grok > Claude > Groq > Ollama
        if self.xai_key:
            self.primary_model = AIModel.GROK
        elif self.anthropic_key:
            self.primary_model = AIModel.CLAUDE
        elif self.groq_key:
            self.primary_model = AIModel.GROQ
        else:
            self.primary_model = AIModel.OLLAMA
        self.system_prompt = get_system_prompt()
        self.upload_dir = Path.home() / "empire-repo" / "backend" / "data" / "uploads"
        providers = []
        if self.xai_key: providers.append("Grok")
        if self.anthropic_key: providers.append("Claude")
        if self.groq_key: providers.append("Groq")
        if self.gemini_key: providers.append("Gemini")
        if self.openai_key: providers.append("OpenAI")
        providers += ["OpenClaw", "Ollama"]
        model_names = {AIModel.GROK: "xAI Grok", AIModel.CLAUDE: "Claude 4.6 Sonnet", AIModel.GROQ: "Groq Llama", AIModel.OLLAMA: "Ollama"}
        print(f"[MAX] Primary: {model_names.get(self.primary_model, str(self.primary_model))} | Providers: {', '.join(providers)}")

    def get_available_models(self):
        return [
            {"id": "grok", "name": "xAI Grok", "available": bool(self.xai_key), "primary": self.primary_model == AIModel.GROK, "type": "cloud"},
            {"id": "claude", "name": "Claude 4.6 Sonnet", "available": bool(self.anthropic_key), "primary": self.primary_model == AIModel.CLAUDE, "type": "cloud"},
            {"id": "claude-opus-4-6", "name": "Claude Opus 4.6", "available": bool(self.anthropic_key), "primary": False, "type": "cloud"},
            {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "available": bool(self.anthropic_key), "primary": False, "type": "cloud"},
            {"id": "groq", "name": "Groq Llama 3.3 70B", "available": bool(self.groq_key), "primary": self.primary_model == AIModel.GROQ, "type": "cloud"},
            {"id": "gemini", "name": "Gemini 2.5 Flash", "available": bool(self.gemini_key), "primary": False, "type": "cloud"},
            {"id": "gpt-4.1-nano", "name": "GPT-4.1 Nano", "available": bool(self.openai_key), "primary": False, "type": "cloud"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "available": bool(self.openai_key), "primary": False, "type": "cloud"},
            {"id": "gpt-4o", "name": "GPT-4o", "available": bool(self.openai_key), "primary": False, "type": "cloud"},
            {"id": "openclaw", "name": "OpenClaw AI", "available": True, "primary": False, "type": "local"},
            {"id": "ollama-llama", "name": "Ollama LLaMA 3.1", "available": False, "primary": False, "type": "local"},
        ]

    AUDIO_EXTS = {'.m4a', '.mp3', '.wav', '.ogg', '.flac', '.wma', '.aac'}
    TEXT_EXTS = {'.txt', '.md', '.csv', '.json'}
    CODE_EXTS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.sh', '.yaml', '.yml'}

    def _find_file(self, filename: str) -> Optional[Path]:
        for cat in ['images', 'documents', 'audio', 'other', 'code']:
            path = self.upload_dir / cat / filename
            if path.exists():
                return path
        return None

    def _find_image(self, filename: str) -> Optional[Path]:
        return self._find_file(filename)

    def _is_image(self, path: Path) -> bool:
        return path.suffix.lower() in {'.png', '.jpg', '.jpeg', '.gif', '.webp'}

    def _is_audio(self, path: Path) -> bool:
        return path.suffix.lower() in self.AUDIO_EXTS

    def _is_readable_text(self, path: Path) -> bool:
        return path.suffix.lower() in (self.TEXT_EXTS | self.CODE_EXTS)

    def _is_pdf(self, path: Path) -> bool:
        return path.suffix.lower() == '.pdf'

    def _transcribe_audio(self, path: Path) -> str:
        """Transcribe audio using Groq Whisper API."""
        from app.services.max.stt_service import stt_service
        return stt_service.transcribe_sync(path)

    def _read_text_file(self, path: Path, max_chars: int = 50000) -> str:
        """Read text content from a file, truncating if too large."""
        try:
            text = path.read_text(errors='replace')
            if len(text) > max_chars:
                text = text[:max_chars] + f"\n\n[Truncated — file is {len(text)} chars, showing first {max_chars}]"
            return text
        except Exception as e:
            return f"[Could not read file: {e}]"

    def _read_pdf(self, path: Path, max_chars: int = 50000) -> str:
        """Extract text from a PDF file."""
        try:
            from subprocess import run
            result = run(['pdftotext', str(path), '-'], capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout.strip():
                text = result.stdout.strip()
                if len(text) > max_chars:
                    text = text[:max_chars] + f"\n\n[Truncated — showing first {max_chars} chars]"
                return text
        except Exception:
            pass
        return "[Could not extract PDF text — pdftotext not available]"

    def _process_attachment(self, filename: str) -> Tuple[Optional[Path], Optional[str]]:
        """Process an attached file. Returns (image_path, attachment_text).
        For images: returns the path for vision API.
        For audio/docs/code: returns extracted text content."""
        path = self._find_file(filename)
        if not path:
            return None, None

        if self._is_image(path):
            return path, None
        elif self._is_audio(path):
            transcript = self._transcribe_audio(path)
            return None, f"[Audio transcription of {filename}]\n{transcript}"
        elif self._is_pdf(path):
            text = self._read_pdf(path)
            return None, f"[Contents of {filename}]\n{text}"
        elif self._is_readable_text(path):
            text = self._read_text_file(path)
            return None, f"[Contents of {filename}]\n{text}"
        else:
            return None, f"[Unsupported file type: {path.suffix}]"

    async def _prepend_local_vision_triage(self, messages: List[AIMessage], image_path: Optional[Path]) -> List[AIMessage]:
        """Run lightweight local Ollama vision triage before cloud escalation."""
        if not image_path or not self._is_image(image_path) or not messages:
            return messages

        try:
            from app.services.ollama_vision_router import generate_vision_response, vision_model_order

            _, image_b64 = self._encode_image(image_path)
            prompt = (
                "You are MAX's local lightweight vision triage. Describe the image, "
                "list visible objects/text, call out business-relevant details, and say "
                "what a cloud model should inspect next. Keep it concise and factual."
            )
            analysis, model_used = await generate_vision_response(
                prompt=prompt,
                image_b64=image_b64,
                timeout=60.0,
            )
            if not analysis:
                return messages

            last = messages[-1]
            routing = " -> ".join(vision_model_order())
            local_context = (
                f"[Local Ollama vision triage via {model_used}; route {routing}]\n"
                f"{analysis.strip()}\n\n"
            )
            updated = list(messages)
            updated[-1] = AIMessage(role=last.role, content=local_context + last.content, image_path=last.image_path)
            return updated
        except Exception as e:
            logger.warning(f"Local Ollama vision triage skipped: {e}")
            return messages

    def _encode_image(self, path: Path) -> tuple:
        ext = path.suffix.lower()
        media_types = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.webp': 'image/webp'}
        media_type = media_types.get(ext, 'image/png')
        with open(path, 'rb') as f:
            data = base64.standard_b64encode(f.read()).decode('utf-8')
        return media_type, data

    def _prepare_messages(self, messages: List[AIMessage], image_path: Optional[Path] = None):
        """Prepare system message and API messages for Claude."""
        system_msg = ""
        api_messages = []
        for msg in messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                api_messages.append({"role": msg.role, "content": msg.content})
        if image_path and api_messages:
            media_type, image_data = self._encode_image(image_path)
            last_msg = api_messages[-1]
            api_messages[-1] = {
                "role": last_msg["role"],
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_data}},
                    {"type": "text", "text": last_msg["content"]}
                ]
            }
        return system_msg, api_messages

    def _prepare_openai_messages(self, messages: List[AIMessage], image_path: Optional[Path] = None):
        """Prepare messages in OpenAI-compatible format (used by xAI Grok, OpenAI, Groq)."""
        api_messages = []
        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})
        if image_path and api_messages:
            media_type, image_data = self._encode_image(image_path)
            last_msg = api_messages[-1]
            api_messages[-1] = {
                "role": last_msg["role"],
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_data}"}},
                    {"type": "text", "text": last_msg["content"]}
                ]
            }
        return api_messages

    def _build_complexity_chain(self, complexity: TaskComplexity) -> list:
        """Build provider chain based on task complexity. Returns list of (provider_type, model_override) tuples.

        Routing policy (owner-defined):
        - Gemini Flash: ONLY single-word greetings and vision tasks (SIMPLE)
        - Grok 3 Fast: DEFAULT for all normal conversation (MODERATE)
        - Claude Sonnet: Analysis, quality writing, memory/search (COMPLEX)
        - Claude Opus: Code Mode only (CRITICAL)
        """
        providers_chain = []

        if complexity == TaskComplexity.SIMPLE:
            # SIMPLE: Gemini FREE (greetings only) -> Grok -> Groq -> Sonnet
            if self.gemini_key:
                providers_chain.append(("gemini", None))
            if self.xai_key:
                providers_chain.append(("grok", None))
            if self.groq_key:
                providers_chain.append(("groq", None))
            if self.anthropic_key:
                providers_chain.append(("claude", "claude-sonnet-4-6"))

        elif complexity == TaskComplexity.MODERATE:
            # MODERATE: Grok 3 Fast (DEFAULT) -> Groq -> Sonnet -> Gemini (last resort)
            if self.xai_key:
                providers_chain.append(("grok", None))
            if self.groq_key:
                providers_chain.append(("groq", None))
            if self.anthropic_key:
                providers_chain.append(("claude", "claude-sonnet-4-6"))
            if self.gemini_key:
                providers_chain.append(("gemini", None))

        elif complexity == TaskComplexity.COMPLEX:
            # COMPLEX: Claude Sonnet -> Grok -> GPT-4o -> Groq
            if self.anthropic_key:
                providers_chain.append(("claude", "claude-sonnet-4-6"))
            if self.xai_key:
                providers_chain.append(("grok", None))
            if self.openai_key:
                providers_chain.append(("openai", "gpt-4o"))
            if self.groq_key:
                providers_chain.append(("groq", None))

        else:  # CRITICAL
            # CRITICAL: Claude Opus -> Sonnet -> stop
            if self.anthropic_key:
                providers_chain.append(("claude", "claude-opus-4-6"))
            if self.anthropic_key:
                providers_chain.append(("claude", "claude-sonnet-4-6"))

        return providers_chain

    # ── Non-streaming chat ──────────────────────────────────────────────

    def _log_chat_cost(self, messages: List[AIMessage], response: str, model: str, feature: str = "chat", business: str = "general", tenant_id: str = "founder"):
        """Log cost for a chat completion."""
        try:
            input_text = " ".join(m.content for m in messages if m.content)
            token_tracker.log_chat(model, input_text, response, feature=feature, business=business, source="ai_router", tenant_id=tenant_id)
        except Exception as e:
            logger.debug(f"Cost logging failed: {e}")

    async def _try_provider_chat(self, provider_type: str, model_override: Optional[str], full_messages: List[AIMessage], messages: List[AIMessage], image_path: Optional[Path], fallback: bool, feature: str, business: str, tenant_id: str) -> Optional[AIResponse]:
        """Try a single provider for non-streaming chat. Returns AIResponse on success, None on failure."""
        try:
            if provider_type == "grok":
                logger.info(f"[MAX] Chat via xAI Grok{' (fallback)' if fallback else ''}")
                resp = await self._grok_chat(full_messages, image_path)
                self._log_chat_cost(full_messages, resp, "grok", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="grok", fallback_used=fallback)

            elif provider_type == "claude":
                model_id = model_override or "claude-sonnet-4-6"
                logger.info(f"[MAX] Chat via Claude ({model_id}){' (fallback)' if fallback else ''}")
                resp = await self._claude_chat(full_messages, image_path, model_id=model_id)
                self._log_chat_cost(full_messages, resp, model_id, feature, business, tenant_id)
                return AIResponse(content=resp, model_used=model_id, fallback_used=fallback)

            elif provider_type == "groq":
                logger.info(f"[MAX] Chat via Groq{' (fallback)' if fallback else ''}")
                resp = await self._groq_chat(full_messages)
                self._log_chat_cost(full_messages, resp, "groq-llama-3.3-70b", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="groq-llama-3.3-70b", fallback_used=fallback)

            elif provider_type == "gemini":
                logger.info(f"[MAX] Chat via Gemini 2.5 Flash{' (fallback)' if fallback else ''}")
                resp = await self._gemini_chat(full_messages, image_path)
                self._log_chat_cost(full_messages, resp, "gemini-2.5-flash", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="gemini-2.5-flash", fallback_used=fallback)

            elif provider_type == "openai":
                oai_model = model_override or "gpt-4.1-nano"
                logger.info(f"[MAX] Chat via OpenAI ({oai_model}){' (fallback)' if fallback else ''}")
                resp = await self._openai_chat(full_messages, model=oai_model, image_path=image_path)
                self._log_chat_cost(full_messages, resp, oai_model, feature, business, tenant_id)
                return AIResponse(content=resp, model_used=oai_model, fallback_used=fallback)

            elif provider_type == "openclaw":
                logger.info(f"[MAX] Chat via OpenClaw{' (fallback)' if fallback else ''}")
                resp = await self._openclaw_chat(messages)
                self._log_chat_cost(messages, resp, "openclaw", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="openclaw", fallback_used=fallback)

            elif provider_type == "ollama":
                logger.info(f"[MAX] Chat via Ollama{' (fallback)' if fallback else ''}")
                resp = await self._ollama_chat(full_messages)
                self._log_chat_cost(full_messages, resp, "ollama-llama3.1", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="ollama-llama3.1", fallback_used=fallback)

        except Exception as e:
            logger.warning(f"{provider_type} failed: {type(e).__name__}: {e}")
        return None

    async def chat(self, messages: List[AIMessage], model: Optional[AIModel] = None, image_filename: Optional[str] = None, desk: Optional[str] = None, system_prompt: Optional[str] = None, tenant_id: str = "founder", source: str = "", conversation_id: str = "") -> AIResponse:
        # Per-desk model routing: if no explicit model requested and desk has a preferred model, use it
        if model is None and desk and desk in DESK_MODEL_ROUTING:
            use_model = DESK_MODEL_ROUTING[desk]
        else:
            use_model = model or self.primary_model
        prompt = system_prompt or (get_desk_system_prompt(desk) if desk else self.system_prompt)
        feature = "vision" if image_filename else ("chat" if not desk else "desk_task")
        business = desk or "general"

        image_path = None
        local_attachment_answer = None
        if image_filename:
            image_path, attachment_text = self._process_attachment(image_filename)
            if attachment_text and messages:
                last = messages[-1]
                messages = list(messages)
                messages[-1] = AIMessage(role=last.role, content=attachment_text + "\n\n" + last.content)
                local_attachment_answer = f"MAX read the attached file. Extracted context:\n{attachment_text[:1500]}"
            messages = await self._prepend_local_vision_triage(messages, image_path)
            if image_path and messages and messages[-1].content.startswith("[Local Ollama vision triage"):
                local_attachment_answer = messages[-1].content.split("\n\n", 1)[0]
            if local_attachment_answer and model is None and not desk:
                model_used = "ollama-vision" if image_path else "attachment-reader"
                return AIResponse(content=local_attachment_answer, model_used=model_used, fallback_used=False)

        full_messages = [AIMessage(role="system", content=prompt)] + list(messages)

        # Complexity-based routing (only when no desk override and no explicit model)
        if model is None and not desk:
            complexity = classify_complexity(messages[-1].content if messages else "", source=source)
            complexity = apply_conversation_floor(conversation_id, complexity)
            logger.info(f"[MAX] Classified as {complexity.value}, using tiered chain")
            providers_chain = self._build_complexity_chain(complexity)

            is_first = True
            for provider_type, model_override in providers_chain:
                result = await self._try_provider_chat(provider_type, model_override, full_messages, messages, image_path, not is_first, feature, business, tenant_id)
                is_first = False
                if result:
                    return result

            # If tiered chain exhausted, fall through to legacy chain below
            logger.warning("[MAX] Tiered chain exhausted, falling through to legacy chain")
            if local_attachment_answer:
                model_used = "ollama-vision" if image_path else "attachment-reader"
                return AIResponse(content=local_attachment_answer, model_used=model_used, fallback_used=True)

        # Legacy fallback chain for desk routing / explicit model requests
        # Resolve Claude variants to the base CLAUDE provider for fallback chain
        # but track the specific model requested
        claude_model_id = "claude-sonnet-4-6"  # default Claude model
        if use_model == AIModel.CLAUDE_OPUS:
            claude_model_id = "claude-opus-4-6"
            use_model = AIModel.CLAUDE
        elif use_model == AIModel.CLAUDE_SONNET:
            claude_model_id = "claude-sonnet-4-6"
            use_model = AIModel.CLAUDE
        elif use_model == AIModel.GEMINI:
            # Desk requested Gemini
            try:
                logger.info("[MAX] Chat via Gemini 2.5 Flash (desk)")
                resp = await self._gemini_chat(full_messages, image_path)
                self._log_chat_cost(full_messages, resp, "gemini-2.5-flash", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="gemini-2.5-flash", fallback_used=False)
            except Exception as e:
                logger.warning(f"Gemini failed: {type(e).__name__}: {e}")
                use_model = AIModel.GROQ  # fallback
        elif use_model == AIModel.OPENAI_NANO:
            try:
                logger.info("[MAX] Chat via OpenAI (gpt-4.1-nano) (desk)")
                resp = await self._openai_chat(full_messages, model="gpt-4.1-nano", image_path=image_path)
                self._log_chat_cost(full_messages, resp, "gpt-4.1-nano", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="gpt-4.1-nano", fallback_used=False)
            except Exception as e:
                logger.warning(f"OpenAI nano failed: {type(e).__name__}: {e}")
                use_model = AIModel.GROQ
        elif use_model == AIModel.OPENAI_MINI:
            try:
                logger.info("[MAX] Chat via OpenAI (gpt-4o-mini) (desk)")
                resp = await self._openai_chat(full_messages, model="gpt-4o-mini", image_path=image_path)
                self._log_chat_cost(full_messages, resp, "gpt-4o-mini", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="gpt-4o-mini", fallback_used=False)
            except Exception as e:
                logger.warning(f"OpenAI mini failed: {type(e).__name__}: {e}")
                use_model = AIModel.GROQ
        elif use_model == AIModel.OPENAI_4O:
            try:
                logger.info("[MAX] Chat via OpenAI (gpt-4o) (desk)")
                resp = await self._openai_chat(full_messages, model="gpt-4o", image_path=image_path)
                self._log_chat_cost(full_messages, resp, "gpt-4o", feature, business, tenant_id)
                return AIResponse(content=resp, model_used="gpt-4o", fallback_used=False)
            except Exception as e:
                logger.warning(f"OpenAI 4o failed: {type(e).__name__}: {e}")
                use_model = AIModel.CLAUDE

        # Build ordered provider chain: requested model first, then full fallback
        # Chain: Grok -> Claude -> Groq -> OpenClaw -> Ollama
        all_providers = [AIModel.GROK, AIModel.CLAUDE, AIModel.GROQ, AIModel.OPENCLAW, AIModel.OLLAMA]
        providers = [use_model] + [p for p in all_providers if p != use_model]

        is_first = True
        for provider in providers:
            fallback = not is_first
            is_first = False

            if provider == AIModel.GROK and self.xai_key:
                try:
                    logger.info(f"[MAX] Chat via xAI Grok{' (fallback)' if fallback else ''}")
                    resp = await self._grok_chat(full_messages, image_path)
                    self._log_chat_cost(full_messages, resp, "grok", feature, business, tenant_id)
                    return AIResponse(content=resp, model_used="grok", fallback_used=fallback)
                except Exception as e:
                    logger.warning(f"Grok failed: {type(e).__name__}: {e}")

            elif provider == AIModel.CLAUDE and self.anthropic_key:
                try:
                    logger.info(f"[MAX] Chat via Claude ({claude_model_id}){' (fallback)' if fallback else ''}")
                    resp = await self._claude_chat(full_messages, image_path, model_id=claude_model_id)
                    self._log_chat_cost(full_messages, resp, claude_model_id, feature, business, tenant_id)
                    return AIResponse(content=resp, model_used=claude_model_id, fallback_used=fallback)
                except Exception as e:
                    logger.warning(f"Claude failed: {type(e).__name__}: {e}")

            elif provider == AIModel.GROQ and self.groq_key:
                try:
                    logger.info(f"[MAX] Chat via Groq{' (fallback)' if fallback else ''}")
                    resp = await self._groq_chat(full_messages)
                    self._log_chat_cost(full_messages, resp, "groq-llama-3.3-70b", feature, business, tenant_id)
                    return AIResponse(content=resp, model_used="groq-llama-3.3-70b", fallback_used=fallback)
                except Exception as e:
                    logger.warning(f"Groq failed: {type(e).__name__}: {e}")

            elif provider == AIModel.OPENCLAW:
                try:
                    logger.info(f"[MAX] Chat via OpenClaw{' (fallback)' if fallback else ''}")
                    resp = await self._openclaw_chat(messages)
                    self._log_chat_cost(messages, resp, "openclaw", feature, business, tenant_id)
                    return AIResponse(content=resp, model_used="openclaw", fallback_used=fallback)
                except Exception as e:
                    logger.warning(f"OpenClaw failed: {e}")

            elif provider == AIModel.OLLAMA:
                try:
                    logger.info(f"[MAX] Chat via Ollama{' (fallback)' if fallback else ''}")
                    resp = await self._ollama_chat(full_messages)
                    self._log_chat_cost(full_messages, resp, "ollama-llama3.1", feature, business, tenant_id)
                    return AIResponse(content=resp, model_used="ollama-llama3.1", fallback_used=fallback)
                except Exception as e:
                    logger.warning(f"Ollama failed: {e}")

        return AIResponse(content="All AI providers are unavailable.", model_used="none", fallback_used=True)

    # ── Streaming chat ──────────────────────────────────────────────────

    async def chat_stream(self, messages: List[AIMessage], model: Optional[AIModel] = None, image_filename: Optional[str] = None, desk: Optional[str] = None, system_prompt: Optional[str] = None, tenant_id: str = "founder", source: str = "", conversation_id: str = "") -> AsyncGenerator[tuple[str, str], None]:
        # Per-desk model routing
        if model is None and desk and desk in DESK_MODEL_ROUTING:
            use_model = DESK_MODEL_ROUTING[desk]
        else:
            use_model = model or self.primary_model
        prompt = system_prompt or (get_desk_system_prompt(desk) if desk else self.system_prompt)
        feature = "vision" if image_filename else ("chat/stream" if not desk else "desk_task")
        business = desk or "general"

        image_path = None
        local_attachment_answer = None
        if image_filename:
            image_path, attachment_text = self._process_attachment(image_filename)
            if attachment_text and messages:
                last = messages[-1]
                messages = list(messages)
                messages[-1] = AIMessage(role=last.role, content=attachment_text + "\n\n" + last.content)
                local_attachment_answer = f"MAX read the attached file. Extracted context:\n{attachment_text[:1500]}"
            messages = await self._prepend_local_vision_triage(messages, image_path)
            if image_path and messages and messages[-1].content.startswith("[Local Ollama vision triage"):
                local_attachment_answer = messages[-1].content.split("\n\n", 1)[0]
            if local_attachment_answer and model is None and not desk:
                yield local_attachment_answer, ("ollama-vision" if image_path else "attachment-reader")
                return

        full_messages = [AIMessage(role="system", content=prompt)] + list(messages)

        # Complexity-based routing (only when no desk override and no explicit model)
        if model is None and not desk:
            complexity = classify_complexity(messages[-1].content if messages else "", source=source)
            complexity = apply_conversation_floor(conversation_id, complexity)
            logger.info(f"[MAX] Stream classified as {complexity.value}, using tiered chain")
            providers_chain = self._build_complexity_chain(complexity)

            chain_exhausted = True
            is_first = True
            for provider_type, model_override in providers_chain:
                fallback = not is_first
                is_first = False
                try:
                    if provider_type == "grok":
                        logger.info(f"[MAX] Streaming via xAI Grok{' (fallback)' if fallback else ''}")
                        collected = []
                        async for chunk in self._grok_chat_stream(full_messages, image_path):
                            collected.append(chunk)
                            yield chunk, "grok"
                        self._log_chat_cost(full_messages, "".join(collected), "grok", feature, business, tenant_id)
                        return

                    elif provider_type == "claude":
                        m_id = model_override or "claude-sonnet-4-6"
                        logger.info(f"[MAX] Streaming via Claude ({m_id}){' (fallback)' if fallback else ''}")
                        collected = []
                        async for chunk in self._claude_chat_stream(full_messages, image_path, model_id=m_id):
                            collected.append(chunk)
                            yield chunk, m_id
                        self._log_chat_cost(full_messages, "".join(collected), m_id, feature, business, tenant_id)
                        return

                    elif provider_type == "groq":
                        logger.info(f"[MAX] Streaming via Groq{' (fallback)' if fallback else ''}")
                        collected = []
                        async for chunk in self._groq_chat_stream(full_messages):
                            collected.append(chunk)
                            yield chunk, "groq-llama-3.3-70b"
                        self._log_chat_cost(full_messages, "".join(collected), "groq-llama-3.3-70b", feature, business, tenant_id)
                        return

                    elif provider_type == "gemini":
                        logger.info(f"[MAX] Streaming via Gemini 2.5 Flash{' (fallback)' if fallback else ''}")
                        collected = []
                        async for chunk in self._gemini_chat_stream(full_messages, image_path):
                            collected.append(chunk)
                            yield chunk, "gemini-2.5-flash"
                        self._log_chat_cost(full_messages, "".join(collected), "gemini-2.5-flash", feature, business, tenant_id)
                        return

                    elif provider_type == "openai":
                        oai_model = model_override or "gpt-4.1-nano"
                        logger.info(f"[MAX] Streaming via OpenAI ({oai_model}){' (fallback)' if fallback else ''}")
                        collected = []
                        async for chunk in self._openai_chat_stream(full_messages, model=oai_model, image_path=image_path):
                            collected.append(chunk)
                            yield chunk, oai_model
                        self._log_chat_cost(full_messages, "".join(collected), oai_model, feature, business, tenant_id)
                        return

                except Exception as e:
                    logger.warning(f"{provider_type} stream failed: {type(e).__name__}: {e}")

            # If tiered chain exhausted, fall through to legacy chain
            logger.warning("[MAX] Tiered stream chain exhausted, falling through to legacy chain")
            if local_attachment_answer:
                yield local_attachment_answer, ("ollama-vision" if image_path else "attachment-reader")
                return

        # Legacy fallback chain for desk routing / explicit model requests
        # Resolve Claude variants
        claude_model_id = "claude-sonnet-4-6"
        if use_model == AIModel.CLAUDE_OPUS:
            claude_model_id = "claude-opus-4-6"
            use_model = AIModel.CLAUDE
        elif use_model == AIModel.CLAUDE_SONNET:
            claude_model_id = "claude-sonnet-4-6"
            use_model = AIModel.CLAUDE
        elif use_model == AIModel.GEMINI:
            try:
                logger.info("[MAX] Streaming via Gemini 2.5 Flash (desk)")
                collected = []
                async for chunk in self._gemini_chat_stream(full_messages, image_path):
                    collected.append(chunk)
                    yield chunk, "gemini-2.5-flash"
                self._log_chat_cost(full_messages, "".join(collected), "gemini-2.5-flash", feature, business, tenant_id)
                return
            except Exception as e:
                logger.warning(f"Gemini stream failed: {type(e).__name__}: {e}")
                use_model = AIModel.GROQ
        elif use_model in (AIModel.OPENAI_NANO, AIModel.OPENAI_MINI, AIModel.OPENAI_4O):
            oai_model = use_model.value
            try:
                logger.info(f"[MAX] Streaming via OpenAI ({oai_model}) (desk)")
                collected = []
                async for chunk in self._openai_chat_stream(full_messages, model=oai_model, image_path=image_path):
                    collected.append(chunk)
                    yield chunk, oai_model
                self._log_chat_cost(full_messages, "".join(collected), oai_model, feature, business, tenant_id)
                return
            except Exception as e:
                logger.warning(f"OpenAI stream failed: {type(e).__name__}: {e}")
                use_model = AIModel.GROQ

        # Build ordered provider chain: requested model first, then full fallback
        all_providers = [AIModel.GROK, AIModel.CLAUDE, AIModel.GROQ, AIModel.OPENCLAW, AIModel.OLLAMA]
        providers = [use_model] + [p for p in all_providers if p != use_model]

        for provider in providers:
            if provider == AIModel.GROK and self.xai_key:
                try:
                    logger.info("[MAX] Streaming via xAI Grok")
                    collected = []
                    async for chunk in self._grok_chat_stream(full_messages, image_path):
                        collected.append(chunk)
                        yield chunk, "grok"
                    self._log_chat_cost(full_messages, "".join(collected), "grok", feature, business, tenant_id)
                    return
                except Exception as e:
                    logger.warning(f"Grok stream failed: {e}")

            elif provider == AIModel.CLAUDE and self.anthropic_key:
                try:
                    logger.info(f"[MAX] Streaming via Claude ({claude_model_id})")
                    collected = []
                    async for chunk in self._claude_chat_stream(full_messages, image_path, model_id=claude_model_id):
                        collected.append(chunk)
                        yield chunk, claude_model_id
                    self._log_chat_cost(full_messages, "".join(collected), claude_model_id, feature, business, tenant_id)
                    return
                except Exception as e:
                    logger.warning(f"Claude stream failed: {e}")

            elif provider == AIModel.GROQ and self.groq_key:
                try:
                    logger.info("[MAX] Streaming via Groq")
                    collected = []
                    async for chunk in self._groq_chat_stream(full_messages):
                        collected.append(chunk)
                        yield chunk, "groq-llama-3.3-70b"
                    self._log_chat_cost(full_messages, "".join(collected), "groq-llama-3.3-70b", feature, business, tenant_id)
                    return
                except Exception as e:
                    logger.warning(f"Groq stream failed: {e}")

            elif provider == AIModel.OPENCLAW:
                try:
                    logger.info("[MAX] Streaming via OpenClaw")
                    resp = await self._openclaw_chat(messages)
                    self._log_chat_cost(messages, resp, "openclaw", feature, business, tenant_id)
                    yield resp, "openclaw"
                    return
                except Exception as e:
                    logger.warning(f"OpenClaw stream failed: {e}")

            elif provider == AIModel.OLLAMA:
                try:
                    logger.info("[MAX] Streaming via Ollama")
                    collected = []
                    async for chunk in self._ollama_chat_stream(full_messages):
                        collected.append(chunk)
                        yield chunk, "ollama-llama3.1"
                    self._log_chat_cost(full_messages, "".join(collected), "ollama-llama3.1", feature, business, tenant_id)
                    return
                except Exception as e:
                    logger.warning(f"Ollama stream failed: {e}")

        yield "All AI providers are unavailable.", "error"

    # ── xAI Grok (OpenAI-compatible API) ──────────────────────────────

    async def _grok_chat(self, messages: List[AIMessage], image_path: Optional[Path] = None) -> str:
        api_messages = self._prepare_openai_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.xai_key}", "Content-Type": "application/json"},
                json={"model": "grok-3-fast", "messages": api_messages, "max_tokens": 8192}
            )
            if resp.status_code != 200:
                raise Exception(f"xAI HTTP {resp.status_code}: {resp.text}")
            return resp.json()["choices"][0]["message"]["content"]

    async def _grok_chat_stream(self, messages: List[AIMessage], image_path: Optional[Path] = None) -> AsyncGenerator[str, None]:
        api_messages = self._prepare_openai_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                "https://api.x.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.xai_key}", "Content-Type": "application/json"},
                json={"model": "grok-3-fast", "messages": api_messages, "max_tokens": 8192, "stream": True}
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Exception(f"xAI HTTP {response.status_code}: {error_body.decode()}")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        yield text

    # ── Claude (Anthropic API) ────────────────────────────────────────

    async def _claude_chat(self, messages: List[AIMessage], image_path: Optional[Path] = None, model_id: str = "claude-sonnet-4-6") -> str:
        system_msg, api_messages = self._prepare_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.anthropic_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                json={"model": model_id, "max_tokens": 8192, "system": system_msg, "messages": api_messages}
            )
            if resp.status_code != 200:
                raise Exception(f"HTTP {resp.status_code}: {resp.text}")
            return resp.json().get("content", [{}])[0].get("text", "No response")

    async def _claude_chat_stream(self, messages: List[AIMessage], image_path: Optional[Path] = None, model_id: str = "claude-sonnet-4-6") -> AsyncGenerator[str, None]:
        system_msg, api_messages = self._prepare_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream(
                "POST",
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.anthropic_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
                json={"model": model_id, "max_tokens": 8192, "stream": True, "system": system_msg, "messages": api_messages}
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Exception(f"HTTP {response.status_code}: {error_body.decode()}")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    if data.get("type") == "content_block_delta":
                        text = data.get("delta", {}).get("text", "")
                        if text:
                            yield text
                    elif data.get("type") == "message_stop":
                        return

    # ── Groq (OpenAI-compatible, Llama 3.3 70B) ──────────────────────

    async def _groq_chat(self, messages: List[AIMessage]) -> str:
        api_messages = self._prepare_openai_messages(messages)
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": api_messages, "max_tokens": 8192}
            )
            if resp.status_code != 200:
                raise Exception(f"Groq HTTP {resp.status_code}: {resp.text}")
            return resp.json()["choices"][0]["message"]["content"]

    async def _groq_chat_stream(self, messages: List[AIMessage]) -> AsyncGenerator[str, None]:
        api_messages = self._prepare_openai_messages(messages)
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.groq_key}", "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": api_messages, "max_tokens": 8192, "stream": True}
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Exception(f"Groq HTTP {response.status_code}: {error_body.decode()}")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        yield text

    # ── Google Gemini (REST API, 2.5 Flash) ───────────────────────────

    async def _gemini_chat(self, messages: List[AIMessage], image_path: Optional[Path] = None) -> str:
        """Chat via Google Gemini 2.5 Flash (free tier)."""
        contents = []
        for msg in messages:
            role = "user" if msg.role in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        # Add image if present
        if image_path and contents:
            media_type, image_data = self._encode_image(image_path)
            contents[-1]["parts"].insert(0, {
                "inline_data": {"mime_type": media_type, "data": image_data}
            })

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_key}",
                json={"contents": contents, "generationConfig": {"maxOutputTokens": 4096}}
            )
            if resp.status_code == 429:
                raise Exception("Gemini rate limited (429)")
            if resp.status_code != 200:
                raise Exception(f"Gemini HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(p.get("text", "") for p in parts)
            return "No response from Gemini"

    async def _gemini_chat_stream(self, messages: List[AIMessage], image_path: Optional[Path] = None) -> AsyncGenerator[str, None]:
        """Stream chat via Google Gemini 2.5 Flash."""
        contents = []
        for msg in messages:
            role = "user" if msg.role in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        if image_path and contents:
            media_type, image_data = self._encode_image(image_path)
            contents[-1]["parts"].insert(0, {
                "inline_data": {"mime_type": media_type, "data": image_data}
            })

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:streamGenerateContent?alt=sse&key={self.gemini_key}",
                json={"contents": contents, "generationConfig": {"maxOutputTokens": 4096}}
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Exception(f"Gemini HTTP {response.status_code}: {error_body.decode()[:200]}")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        data = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts)
                        if text:
                            yield text

    # ── OpenAI API ────────────────────────────────────────────────────

    async def _openai_chat(self, messages: List[AIMessage], model: str = "gpt-4.1-nano", image_path: Optional[Path] = None) -> str:
        """Chat via OpenAI API."""
        api_messages = self._prepare_openai_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": api_messages, "max_tokens": 4096}
            )
            if resp.status_code != 200:
                raise Exception(f"OpenAI HTTP {resp.status_code}: {resp.text[:200]}")
            return resp.json()["choices"][0]["message"]["content"]

    async def _openai_chat_stream(self, messages: List[AIMessage], model: str = "gpt-4.1-nano", image_path: Optional[Path] = None) -> AsyncGenerator[str, None]:
        """Stream chat via OpenAI API."""
        api_messages = self._prepare_openai_messages(messages, image_path)
        async with httpx.AsyncClient(timeout=45.0) as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": api_messages, "max_tokens": 4096, "stream": True}
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise Exception(f"OpenAI HTTP {response.status_code}: {error_body.decode()[:200]}")
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        yield text

    # ── OpenClaw ──────────────────────────────────────────────────────

    async def _openclaw_chat(self, messages: List[AIMessage]) -> str:
        last_user_msg = ""
        history = []
        for msg in messages:
            if msg.role == "user":
                last_user_msg = msg.content
            history.append({"role": msg.role, "content": msg.content})

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "http://localhost:7878/chat",
                json={"message": last_user_msg, "history": history[:-1], "system_prompt": self.system_prompt},
            )
            if resp.status_code != 200:
                raise Exception(f"OpenClaw HTTP {resp.status_code}: {resp.text}")
            return resp.json().get("response", "No response from OpenClaw")

    # ── Ollama ────────────────────────────────────────────────────────

    async def _ollama_chat(self, messages: List[AIMessage]) -> str:
        prompt = "\n".join([f"<|{m.role}|>\n{m.content}" for m in messages]) + "\n<|assistant|>\n"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.1:8b", "prompt": prompt, "stream": False}
            )
            return resp.json().get("response", "No response")

    async def _ollama_chat_stream(self, messages: List[AIMessage]) -> AsyncGenerator[str, None]:
        prompt = "\n".join([f"<|{m.role}|>\n{m.content}" for m in messages]) + "\n<|assistant|>\n"
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                "http://localhost:11434/api/generate",
                json={"model": "llama3.1:8b", "prompt": prompt, "stream": True}
            ) as response:
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    text = data.get("response", "")
                    if text:
                        yield text
                    if data.get("done", False):
                        return

ai_router = AIRouter()
