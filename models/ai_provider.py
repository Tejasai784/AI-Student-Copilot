"""AI Model Provider Abstraction.
Supports Gemini, OpenAI, and Offline/Local Fallback.
Configurable via environment variables (AI_PROVIDER, AI_MODEL, AI_API_KEY).
"""
from __future__ import annotations

import abc
import os
import re
import time
from typing import Optional, Tuple, Dict, Any, List

from backend.config import settings
from backend.logging_config import logger


class BaseAIProvider(abc.ABC):
    """Abstract interface for all LLM providers."""

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
    def get_model_name(self) -> str:
        """Returns the identifier of the active model."""
        pass

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Returns True if the provider is properly configured with credentials."""
        pass


class GeminiProvider(BaseAIProvider):
    """Google Gemini API Provider using current google-genai SDK."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        settings.reload()
        self._explicit_key = api_key
        self._explicit_model = model

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

    def is_available(self) -> bool:
        return bool(self.api_key)

    def get_model_name(self) -> str:
        return f"Gemini ({self.model})"

    def test_connection(self) -> Tuple[bool, str]:
        """
        Performs a safe minimal connectivity test without printing or leaking the key.
        Returns (True, 'SUCCESS') or (False, 'FAILED: <sanitized message>').
        """
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
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_args)
                )
                return response.text or ""
            except Exception as exc:
                raw_err = str(exc)
                err_lower = raw_err.lower()
                is_transient = any(
                    indicator in err_lower
                    for indicator in ["503", "unavailable", "overloaded", "temporarily unavailable"]
                )
                if is_transient and attempt < max_attempts:
                    sleep_sec = 2 if attempt == 1 else 4
                    logger.warning(
                        f"Gemini API temporarily unavailable (attempt {attempt}/{max_attempts}): {raw_err}. "
                        f"Retrying in {sleep_sec}s..."
                    )
                    time.sleep(sleep_sec)
                    continue

                sanitized = re.sub(r'AIza[0-9A-Za-z-_]{35}', '[REDACTED]', raw_err)
                sanitized = re.sub(r'key=[^&\s]+', 'key=[REDACTED]', sanitized)
                logger.error(f"Gemini text generation failed: {sanitized}")
                raise RuntimeError(f"Gemini API error: {sanitized}") from None


class OpenAIProvider(BaseAIProvider):
    """OpenAI API Provider."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("AI_API_KEY") or settings.OPENAI_API_KEY
        self.model = model or os.getenv("AI_MODEL") or settings.OPENAI_MODEL or "gpt-4o-mini"

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def get_model_name(self) -> str:
        return f"OpenAI ({self.model})"

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


class OfflineMockProvider(BaseAIProvider):
    """
    Offline/Local Rule-based Provider.
    Ensures the platform runs 100% reliably out of the box in test, offline,
    or demo environments without external network dependencies.
    """

    def __init__(self):
        self.model_name = "Offline Academic Model (Deterministic)"

    def is_available(self) -> bool:
        return True

    def get_model_name(self) -> str:
        return self.model_name

    def generate_text(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> str:
        p_lower = prompt.lower()
        sys_lower = system_instruction.lower()

        # 1. Goal Planning / Timetable Generation
        if "plan" in p_lower or "schedule" in p_lower or "timetable" in p_lower or "prepare" in p_lower:
            return (
                "### 7-Day Autonomous Study Plan & Exam Preparation\n\n"
                "**Goal**: Master high-value topics, resolve weaknesses, and complete practice mock tests.\n\n"
                "- **Day 1: Core Fundamentals & Syntax**\n"
                "  - Variables, Primitive Data Types, Operators, and Input/Output.\n"
                "  - Review Lecture Notes & run basic test snippets.\n\n"
                "- **Day 2: Control Flow & Loops**\n"
                "  - Conditionals (`if-elif-else`), `for` and `while` loops, break/continue.\n"
                "  - Solve 5 pattern printing and condition logic problems.\n\n"
                "- **Day 3: Data Structures (Lists, Tuples, Dictionaries, Sets)**\n"
                "  - Memory mutability, indexing, slicing, comprehensions, and key lookups.\n"
                "  - Practice question: frequency counter and nested data extraction.\n\n"
                "- **Day 4: Functions, Scope & Modules**\n"
                "  - Parameter passing, `*args`, `**kwargs`, lambda functions, global vs local scope.\n"
                "  - Modular code organization and error handling with `try-except`.\n\n"
                "- **Day 5: Object-Oriented Programming (OOP) & File I/O**\n"
                "  - Classes, constructors (`__init__`), inheritance, encapsulation, and file reading.\n"
                "  - Build a mini-project (e.g., Student Record System).\n\n"
                "- **Day 6: Previous Exam Papers & Mock Assessment**\n"
                "  - Take timed 45-minute practice test covering Units 1-5.\n"
                "  - Identify weak topics and review missed questions.\n\n"
                "- **Day 7: Final Formula & Weakness Revision**\n"
                "  - Re-attempt questions in previously low-scoring areas.\n"
                "  - High-yield summary review and exam readiness confirmation.\n"
            )

        # 2. Coding / Python Questions
        if "code" in p_lower or "python" in p_lower or "function" in p_lower or "debug" in p_lower:
            return (
                "### Python Concept & Implementation Guide\n\n"
                "**Explanation**:\n"
                "In Python, clean execution relies on appropriate data structures and exception handling.\n\n"
                "```python\n"
                "# Demonstrating core logic with input validation\n"
                "def process_student_data(records: list[dict]) -> dict:\n"
                "    summary = {'total': len(records), 'passed': 0, 'top_score': 0.0}\n"
                "    for item in records:\n"
                "        score = item.get('score', 0)\n"
                "        if score >= 50:\n"
                "            summary['passed'] += 1\n"
                "        if score > summary['top_score']:\n"
                "            summary['top_score'] = score\n"
                "    return summary\n\n"
                "# Example execution\n"
                "sample = [{'name': 'Alice', 'score': 92}, {'name': 'Bob', 'score': 74}]\n"
                "print(process_student_data(sample))\n"
                "```\n\n"
                "**Key Takeaways**:\n"
                "1. Always use defensive `dict.get()` lookups.\n"
                "2. Keep functions pure and testable.\n"
            )

        # 3. Mathematics / Calculation
        if "math" in p_lower or "calculate" in p_lower or "solve" in p_lower or "matrix" in p_lower:
            return (
                "### Step-by-Step Mathematical Derivation\n\n"
                "1. **Problem Statement**: Analyze the given mathematical expression.\n"
                "2. **Identified Formula**: Apply standard algebraic reduction.\n"
                "3. **Step 1**: Group like terms and factor common multipliers.\n"
                "4. **Step 2**: Evaluate intermediate terms and simplify fractions.\n"
                "5. **Final Result**: The verified exact solution is derived with full working shown.\n"
            )

        # 4. Default Academic Explanation
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


def get_ai_provider(preferred: Optional[str] = None) -> BaseAIProvider:
    """
    Returns the appropriate AI provider based on configuration.
    Priority:
    1. Explicit requested provider ('gemini', 'openai', 'offline')
    2. Environment variable AI_PROVIDER
    3. Auto-detection (Gemini if key exists, then OpenAI, then Offline fallback)
    """
    prov_env = os.getenv("AI_PROVIDER", "").strip().lower()
    choice = (preferred or prov_env or settings.PREFERRED_PROVIDER or "auto").strip().lower()

    if choice == "gemini":
        gemini = GeminiProvider()
        if gemini.is_available():
            return gemini
        logger.warning("Gemini requested but no API key configured. Checking fallback...")

    elif choice == "openai":
        openai_p = OpenAIProvider()
        if openai_p.is_available():
            return openai_p
        logger.warning("OpenAI requested but no API key configured. Checking fallback...")

    elif choice == "offline":
        return OfflineMockProvider()

    # Auto mode: try configured providers in order
    gemini = GeminiProvider()
    if gemini.is_available():
        return gemini

    openai_p = OpenAIProvider()
    if openai_p.is_available():
        return openai_p

    # Fallback to local mock
    return OfflineMockProvider()
