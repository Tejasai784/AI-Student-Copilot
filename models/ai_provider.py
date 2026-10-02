"""AI Model Provider Abstraction with Model-Level Fallback & Resiliency.
Complies with V2.0 Specification & Amendments 1-3:
- Amendment 1: Gemini Primary -> Alternate Gemini Models (GEMINI_FALLBACK_MODELS) -> OpenAI -> Offline
- Amendment 2: Optional OpenAI provider (graceful skip if key omitted)
- Amendment 3: In-memory circuit breaker & health tracking (no over-engineering)
"""
from __future__ import annotations

import abc
import os
import re
import time
import threading
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List, Generator

from backend.config import settings
from backend.logging_config import logger


# ============================================================================
# Base Interface
# ============================================================================

class BaseAIProvider(abc.ABC):
    """Abstract interface for all AI/LLM providers."""

    @abc.abstractmethod
    def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> str:
        """Generates completion text from prompt and system instruction."""
        pass

    @abc.abstractmethod
    def stream_text(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Generator[str, None, None]:
        """Streams completion tokens from prompt."""
        pass

    @abc.abstractmethod
    def get_model_name(self) -> str:
        """Returns the identifier of the active model."""
        pass

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is properly configured with credentials."""
        pass

    def test_connection(self) -> Tuple[bool, str]:
        """Performs a safe connectivity check without exposing secrets."""
        return True, "SUCCESS"


# ============================================================================
# Gemini Provider (Primary with Model Fallback — Amendment 1)
# ============================================================================

class GeminiProvider(BaseAIProvider):
    """Google Gemini API Provider using current google-genai SDK.

    Includes automatic model-level fallback (GEMINI_FALLBACK_MODELS) on capacity/503 errors.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback_models: Optional[List[str]] = None
    ):
        settings.reload()
        self._explicit_key = api_key
        self._explicit_model = model
        self._explicit_fallback_models = fallback_models

    @property
    def api_key(self) -> str:
        return (
            self._explicit_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("AI_API_KEY")
            or settings.GEMINI_API_KEY
            or ""
        ).strip()

    @property
    def model(self) -> str:
        return (
            self._explicit_model
            or os.getenv("GEMINI_MODEL")
            or os.getenv("AI_MODEL")
            or settings.GEMINI_MODEL
            or "gemini-2.0-flash"
        ).strip()

    @property
    def fallback_models(self) -> List[str]:
        if self._explicit_fallback_models is not None:
            return self._explicit_fallback_models
        return settings.GEMINI_FALLBACK_MODELS

    @fallback_models.setter
    def fallback_models(self, value: List[str]) -> None:
        self._explicit_fallback_models = value

    def is_available(self) -> bool:
        return bool(self.api_key)

    def get_model_name(self) -> str:
        return f"Gemini ({self.model})"

    def test_connection(self) -> Tuple[bool, str]:
        """Safe minimal connectivity test without printing or leaking the key."""
        if not self.is_available():
            return False, "FAILED: GEMINI_API_KEY or GOOGLE_API_KEY is missing"
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            client.models.get(model=self.model)
            return True, "SUCCESS"
        except Exception as exc:
            raw_err = str(exc)
            sanitized = re.sub(r'AIza[0-9A-Za-z-_]{35}', '[REDACTED]', raw_err)
            sanitized = re.sub(r'key=[^&\s]+', 'key=[REDACTED]', sanitized)
            logger.warning(f"Gemini connection verification failed: {sanitized}")
            return False, f"FAILED: {sanitized}"

    def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> str:
        if not self.is_available():
            raise RuntimeError("Gemini API key is not configured.")
        from google import genai
        from google.genai import types

        # Chain: primary model followed by configured fallback models (Amendment 1)
        models_to_try = [self.model]
        for fb_model in self.fallback_models:
            if fb_model and fb_model not in models_to_try:
                models_to_try.append(fb_model)

        last_error = None
        for current_model in models_to_try:
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    client = genai.Client(api_key=self.api_key)
                    config_args: Dict[str, Any] = {
                        "temperature": temperature,
                        "max_output_tokens": max_tokens,
                    }
                    if system_instruction:
                        config_args["system_instruction"] = system_instruction

                    response = client.models.generate_content(
                        model=current_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(**config_args)
                    )
                    return response.text or ""
                except Exception as exc:
                    raw_err = str(exc)
                    err_lower = raw_err.lower()
                    is_transient = any(
                        ind in err_lower
                        for ind in ["503", "unavailable", "overloaded", "temporarily unavailable", "resourceexhausted", "429"]
                    )
                    is_auth_error = any(
                        ind in err_lower
                        for ind in ["api_key_invalid", "401", "unauthenticated", "invalid api key"]
                    )
                    if is_auth_error:
                        sanitized = re.sub(r'AIza[0-9A-Za-z-_]{35}', '[REDACTED]', raw_err)
                        sanitized = re.sub(r'key=[^&\s]+', 'key=[REDACTED]', sanitized)
                        logger.error(f"Gemini authentication error: {sanitized}")
                        raise RuntimeError(f"Gemini API error: {sanitized}") from None

                    last_error = exc
                    if is_transient and attempt < max_attempts:
                        sleep_sec = 2 if attempt == 1 else 4
                        logger.warning(
                            f"Gemini model {current_model} transient error (attempt {attempt}/{max_attempts}): {raw_err}. "
                            f"Retrying in {sleep_sec}s..."
                        )
                        time.sleep(sleep_sec)
                        continue
                    break  # Break retry loop for this model, try next fallback model

            logger.warning(f"Gemini model {current_model} exhausted retries. Attempting alternate model...")

        # If all Gemini models fail
        sanitized = re.sub(r'AIza[0-9A-Za-z-_]{35}', '[REDACTED]', str(last_error or "Generation failed"))
        sanitized = re.sub(r'key=[^&\s]+', 'key=[REDACTED]', sanitized)
        logger.error(f"All configured Gemini models failed: {sanitized}")
        raise RuntimeError(f"Gemini API error: {sanitized}") from None

    def stream_text(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Generator[str, None, None]:
        """Streams completion tokens using current Google GenAI SDK."""
        if not self.is_available():
            raise RuntimeError("Gemini API key is not configured.")
        from google import genai
        from google.genai import types

        models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
        for current_model in models_to_try:
            try:
                client = genai.Client(api_key=self.api_key)
                config_args: Dict[str, Any] = {
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
                if system_instruction:
                    config_args["system_instruction"] = system_instruction

                response_stream = client.models.generate_content_stream(
                    model=current_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_args)
                )
                for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as exc:
                logger.warning(f"Gemini streaming failed on {current_model}: {exc}. Trying fallback...")
                continue

        # If streaming failed completely, fallback to non-streaming text generator
        full_text = self.generate_text(prompt, system_instruction, temperature, max_tokens)
        words = full_text.split(" ")
        for i in range(0, len(words), 3):
            yield " ".join(words[i:i+3]) + " "


# ============================================================================
# OpenAI Provider (Optional Fallback — Amendment 2)
# ============================================================================

class OpenAIProvider(BaseAIProvider):
    """OpenAI API Provider (Optional fallback, skipped if no key configured)."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = (api_key or os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY or "").strip()
        self.model = (model or os.getenv("OPENAI_MODEL") or settings.OPENAI_MODEL or "gpt-4o-mini").strip()

    def is_available(self) -> bool:
        return bool(self.api_key)

    def get_model_name(self) -> str:
        return f"OpenAI ({self.model})"

    def test_connection(self) -> Tuple[bool, str]:
        if not self.is_available():
            return False, "NOT CONFIGURED: OPENAI_API_KEY is not set."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            client.models.retrieve(self.model)
            return True, "SUCCESS"
        except Exception as exc:
            raw_err = str(exc)
            sanitized = re.sub(r'sk-[A-Za-z0-9-_]{20,}', '[REDACTED]', raw_err)
            return False, f"FAILED: {sanitized}"

    def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> str:
        if not self.is_available():
            raise RuntimeError("OpenAI API key is not configured.")
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        resp = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    def stream_text(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Generator[str, None, None]:
        if not self.is_available():
            raise RuntimeError("OpenAI API key is not configured.")
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        stream = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else ""
            if delta:
                yield delta


# ============================================================================
# Offline Mock Provider (Deterministic Local Fallback)
# ============================================================================

class OfflineMockProvider(BaseAIProvider):
    """Offline/Local Rule-based Provider for deterministic, zero-network operation."""

    def __init__(self):
        self.model_name = "Offline Academic Model (Deterministic)"

    def is_available(self) -> bool:
        return True

    def get_model_name(self) -> str:
        return self.model_name

    def test_connection(self) -> Tuple[bool, str]:
        return True, "SUCCESS: Offline local model ready."

    def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> str:
        p_lower = prompt.lower()

        # Goal Planning
        if any(w in p_lower for w in ["plan", "schedule", "timetable", "prepare"]):
            return (
                "### 7-Day Autonomous Study Plan & Exam Preparation\n\n"
                "**Goal**: Master high-value topics, resolve weaknesses, and complete practice mock tests.\n\n"
                "- **Day 1: Core Fundamentals & Syntax**\n"
                "  - Review Lecture Notes & run basic test snippets.\n"
                "- **Day 2: Control Flow & Logic**\n"
                "  - Solve 5 pattern printing and condition logic problems.\n"
                "- **Day 3: Data Structures & Collections**\n"
                "  - Memory mutability, indexing, slicing, comprehensions.\n"
                "- **Day 4: Functions & Modularity**\n"
                "  - Parameter passing, scope, error handling with try-except.\n"
                "- **Day 5: Applied Practice & Mini-Projects**\n"
                "  - Core problem solving and implementation.\n"
                "- **Day 6: Mock Assessment**\n"
                "  - Take timed 45-minute practice test covering Units 1-5.\n"
                "- **Day 7: Final Formula & Weakness Revision**\n"
                "  - High-yield summary review and exam readiness confirmation.\n"
            )

        # Coding / Python
        if any(w in p_lower for w in ["code", "python", "function", "debug"]):
            return (
                "### Python Concept & Implementation Guide\n\n"
                "**Explanation**:\n"
                "In Python, clean execution relies on appropriate data structures and exception handling.\n\n"
                "```python\n"
                "def process_student_data(records: list[dict]) -> dict:\n"
                "    summary = {'total': len(records), 'passed': 0, 'top_score': 0.0}\n"
                "    for item in records:\n"
                "        score = item.get('score', 0)\n"
                "        if score >= 50:\n"
                "            summary['passed'] += 1\n"
                "        if score > summary['top_score']:\n"
                "            summary['top_score'] = score\n"
                "    return summary\n\n"
                "sample = [{'name': 'Alice', 'score': 92}, {'name': 'Bob', 'score': 74}]\n"
                "print(process_student_data(sample))\n"
                "```\n\n"
                "**Key Takeaways**:\n"
                "1. Always use defensive `dict.get()` lookups.\n"
                "2. Keep functions pure and testable.\n"
            )

        # Mathematics
        if any(w in p_lower for w in ["math", "calculate", "solve", "matrix", "integral"]):
            return (
                "### Step-by-Step Mathematical Derivation\n\n"
                "1. **Problem Statement**: Analyze the given mathematical expression.\n"
                "2. **Identified Formula**: Apply standard algebraic reduction.\n"
                "3. **Step 1**: Group like terms and factor common multipliers.\n"
                "4. **Step 2**: Evaluate intermediate terms and simplify fractions.\n"
                "5. **Final Result**: The verified exact solution is derived with full working shown.\n"
            )

        # Default Academic Explanation
        return (
            f"### Academic Concept Overview\n\n"
            f"Based on your query: **{prompt[:80]}**\n\n"
            "**Key Concept Definition**:\n"
            "This topic represents a foundational building block in the syllabus. It connects theoretical principles with practical application in academic examinations.\n\n"
            "**Key Points to Remember**:\n"
            "- Understand the core definitions and standard notation.\n"
            "- Practice representative exam questions and review past exam patterns.\n"
            "- Pay attention to boundary conditions and edge cases in practice exercises.\n"
        )

    def stream_text(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Generator[str, None, None]:
        full_text = self.generate_text(prompt, system_instruction, temperature, max_tokens)
        words = full_text.split(" ")
        for i in range(0, len(words), 4):
            yield " ".join(words[i:i+4]) + " "


# ============================================================================
# Circuit Breaker & Health Tracking (Amendment 1 & 3)
# ============================================================================

class CircuitBreaker:
    """Thread-safe circuit breaker preventing cascading failures to remote AI APIs."""

    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.consecutive_failures = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED | OPEN | HALF_OPEN
        self.total_requests = 0
        self.total_failures = 0
        self.latencies: List[float] = []
        self._lock = threading.Lock()

    def record_success(self, duration_ms: float) -> None:
        with self._lock:
            self.consecutive_failures = 0
            self.state = "CLOSED"
            self.total_requests += 1
            self.latencies.append(duration_ms)
            if len(self.latencies) > 50:
                self.latencies.pop(0)

    def record_failure(self) -> None:
        with self._lock:
            self.consecutive_failures += 1
            self.total_failures += 1
            self.total_requests += 1
            self.last_failure_time = time.time()
            if self.consecutive_failures >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(
                    f"Circuit breaker tripped to OPEN after {self.consecutive_failures} consecutive failures. "
                    f"Cooling down for {self.cooldown_seconds}s."
                )

    def can_attempt(self) -> bool:
        with self._lock:
            if self.state == "CLOSED":
                return True
            if self.state == "OPEN":
                if self.last_failure_time and (time.time() - self.last_failure_time) > self.cooldown_seconds:
                    self.state = "HALF_OPEN"
                    logger.info("Circuit breaker transitioning to HALF_OPEN (probing remote API).")
                    return True
                return False
            if self.state == "HALF_OPEN":
                return True
            return True

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            avg_lat = round(sum(self.latencies) / len(self.latencies), 1) if self.latencies else 0.0
            sorted_lat = sorted(self.latencies)
            p95_lat = round(sorted_lat[int(len(sorted_lat) * 0.95)], 1) if sorted_lat else 0.0
            return {
                "state": self.state,
                "consecutive_failures": self.consecutive_failures,
                "total_requests": self.total_requests,
                "total_failures": self.total_failures,
                "avg_latency_ms": avg_lat,
                "p95_latency_ms": p95_lat,
            }


# ============================================================================
# AI Provider Manager (Central Resilient Orchestration)
# ============================================================================

class AIProviderManager:
    """Manages provider resolution, circuit breaker status, model fallbacks, and telemetry."""

    _instance: Optional[AIProviderManager] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_manager()
            return cls._instance

    def _init_manager(self):
        self.gemini_circuit = CircuitBreaker(failure_threshold=3, cooldown_seconds=30.0)
        self.openai_circuit = CircuitBreaker(failure_threshold=3, cooldown_seconds=30.0)

    def get_active_provider(self, preferred: Optional[str] = None) -> BaseAIProvider:
        """Resolves the active provider respecting configuration and circuit breakers."""
        settings.reload()
        choice = (preferred or os.getenv("AI_PROVIDER") or settings.PREFERRED_PROVIDER or "auto").strip().lower()

        if choice == "gemini":
            gemini = GeminiProvider()
            if gemini.is_available() and self.gemini_circuit.can_attempt():
                return gemini

        elif choice == "openai":
            openai_p = OpenAIProvider()
            if openai_p.is_available() and self.openai_circuit.can_attempt():
                return openai_p

        elif choice == "offline":
            return OfflineMockProvider()

        # Auto resolution chain: Gemini -> OpenAI -> Offline
        gemini = GeminiProvider()
        if gemini.is_available() and self.gemini_circuit.can_attempt():
            return gemini

        openai_p = OpenAIProvider()
        if openai_p.is_available() and self.openai_circuit.can_attempt():
            return openai_p

        return OfflineMockProvider()

    def generate_text_with_resilience(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Tuple[str, str, str, bool]:
        """Executes generation with full fallback chain:

        Gemini (with model fallbacks) -> OpenAI -> OfflineMock.
        Returns: (text, provider_name, model_name, is_fallback)
        """
        settings.reload()

        # 1. Try Gemini
        gemini = GeminiProvider()
        if gemini.is_available() and self.gemini_circuit.can_attempt():
            t0 = time.time()
            try:
                text = gemini.generate_text(prompt, system_instruction, temperature, max_tokens)
                duration = (time.time() - t0) * 1000
                self.gemini_circuit.record_success(duration)
                return text, "Gemini", gemini.model, False
            except Exception as exc:
                self.gemini_circuit.record_failure()
                logger.warning(f"Gemini provider failed in manager: {exc}. Trying next in chain...")

        # 2. Try OpenAI (Optional fallback)
        openai_p = OpenAIProvider()
        if openai_p.is_available() and self.openai_circuit.can_attempt():
            t0 = time.time()
            try:
                text = openai_p.generate_text(prompt, system_instruction, temperature, max_tokens)
                duration = (time.time() - t0) * 1000
                self.openai_circuit.record_success(duration)
                return text, "OpenAI", openai_p.model, True
            except Exception as exc:
                self.openai_circuit.record_failure()
                logger.warning(f"OpenAI provider failed in manager: {exc}. Falling back to Offline...")

        # 3. Fallback to Offline Mock
        offline = OfflineMockProvider()
        text = offline.generate_text(prompt, system_instruction, temperature, max_tokens)
        return text, "Offline", offline.get_model_name(), True

    def stream_text_with_resilience(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000,
        preferred: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Executes streaming token generation with automatic circuit-breaker and mid-stream fallback:
        Attempts Gemini -> on failure mid-stream emits 'provider_switch' and restarts cleanly with fallback.
        Yields dicts with:
          - {"type": "provider_info", "provider": "Gemini", "model": "gemini-2.0-flash"}
          - {"type": "token", "text": "..."}
          - {"type": "provider_switch", "from_provider": "Gemini", "to_provider": "Offline", "reason": "...", "action": "restart"}
          - {"type": "done", "provider": "...", "model": "..."}
        """
        settings.reload()
        choice = (preferred or os.getenv("AI_PROVIDER") or settings.PREFERRED_PROVIDER or "auto").strip().lower()

        # Step 1: Decide initial provider
        can_try_gemini = False
        gemini = GeminiProvider()
        if choice in ("gemini", "auto") and gemini.is_available() and self.gemini_circuit.can_attempt():
            can_try_gemini = True

        can_try_openai = False
        openai_p = OpenAIProvider()
        if choice in ("openai", "auto") and openai_p.is_available() and self.openai_circuit.can_attempt():
            can_try_openai = True

        # Try Gemini stream
        if can_try_gemini:
            t0 = time.time()
            emitted_any = False
            gemini_model = getattr(gemini, "model", gemini.get_model_name())
            try:
                yield {"type": "provider_info", "provider": "Gemini", "model": gemini_model}
                for chunk in gemini.stream_text(prompt, system_instruction, temperature, max_tokens):
                    emitted_any = True
                    yield {"type": "token", "text": chunk}
                duration = (time.time() - t0) * 1000
                self.gemini_circuit.record_success(duration)
                yield {"type": "done", "provider": "Gemini", "model": gemini_model}
                return
            except Exception as exc:
                self.gemini_circuit.record_failure()
                logger.warning(f"Gemini streaming failed (emitted={emitted_any}): {exc}. Triggering provider fallback...")
                next_target = "OpenAI" if can_try_openai else "Offline"
                sanitized_err = re.sub(r'AIza[0-9A-Za-z-_]{35}', '[REDACTED]', str(exc))
                sanitized_err = re.sub(r'key=[^&\s]+', 'key=[REDACTED]', sanitized_err)
                yield {
                    "type": "provider_switch",
                    "from_provider": "Gemini",
                    "to_provider": next_target,
                    "reason": sanitized_err,
                    "action": "restart"
                }

        # Try OpenAI stream (fallback or primary)
        if can_try_openai:
            t0 = time.time()
            emitted_any = False
            openai_model = getattr(openai_p, "model", openai_p.get_model_name())
            try:
                yield {"type": "provider_info", "provider": "OpenAI", "model": openai_model}
                for chunk in openai_p.stream_text(prompt, system_instruction, temperature, max_tokens):
                    emitted_any = True
                    yield {"type": "token", "text": chunk}
                duration = (time.time() - t0) * 1000
                self.openai_circuit.record_success(duration)
                yield {"type": "done", "provider": "OpenAI", "model": openai_model}
                return
            except Exception as exc:
                self.openai_circuit.record_failure()
                logger.warning(f"OpenAI streaming failed: {exc}. Triggering Offline fallback...")
                sanitized_err = re.sub(r'sk-[0-9A-Za-z-_]{20,}', '[REDACTED]', str(exc))
                yield {
                    "type": "provider_switch",
                    "from_provider": "OpenAI",
                    "to_provider": "Offline",
                    "reason": sanitized_err,
                    "action": "restart"
                }

        # Fallback to OfflineMockProvider
        offline = OfflineMockProvider()
        yield {"type": "provider_info", "provider": "Offline", "model": offline.get_model_name()}
        for chunk in offline.stream_text(prompt, system_instruction, temperature, max_tokens):
            yield {"type": "token", "text": chunk}
        yield {"type": "done", "provider": "Offline", "model": offline.get_model_name()}


    def get_telemetry(self) -> Dict[str, Any]:
        """Returns health, circuit states, and diagnostics."""
        settings.reload()
        gemini = GeminiProvider()
        gemini_ok, gemini_msg = gemini.test_connection() if gemini.is_available() else (False, "Not configured")

        openai_p = OpenAIProvider()
        openai_ok, openai_msg = openai_p.test_connection() if openai_p.is_available() else (False, "Not configured")

        active = self.get_active_provider()

        return {
            "gemini": {
                "configured": gemini.is_available(),
                "model": gemini.model,
                "fallback_models": gemini.fallback_models,
                "connection": "SUCCESS" if gemini_ok else ("NOT CONFIGURED" if not gemini.is_available() else "FAILED"),
                "detail": gemini_msg,
                "circuit": self.gemini_circuit.get_stats(),
            },
            "openai": {
                "configured": openai_p.is_available(),
                "model": openai_p.model,
                "connection": "SUCCESS" if openai_ok else ("NOT CONFIGURED" if not openai_p.is_available() else "FAILED"),
                "detail": openai_msg,
                "circuit": self.openai_circuit.get_stats(),
            },
            "active_provider": active.get_model_name(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Global Provider Factory (Preserves existing interface across entire codebase)
def get_ai_provider(preferred: Optional[str] = None) -> BaseAIProvider:
    """Returns the active AI provider instance from AIProviderManager."""
    return AIProviderManager().get_active_provider(preferred=preferred)
