import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
VECTOR_STORE_PATH = DATA_DIR / "vector_store"

# Ensure data directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)

from dotenv import load_dotenv, dotenv_values

# Initial environment load from .env file
for ep in [BASE_DIR / ".env", Path.cwd() / ".env"]:
    if ep.exists() and ep.is_file():
        load_dotenv(ep)
        break


def reload_env() -> None:
    """
    Refreshes configuration and synchronizes key aliases from the current environment.
    """
    gemini_key = (os.getenv("GEMINI_API_KEY") or "").strip().strip("'\"")
    google_key = (os.getenv("GOOGLE_API_KEY") or "").strip().strip("'\"")
    ai_key = (os.getenv("AI_API_KEY") or "").strip().strip("'\"")

    active_key = gemini_key or google_key or ai_key
    if active_key:
        os.environ["GEMINI_API_KEY"] = active_key
        os.environ["GOOGLE_API_KEY"] = active_key
    else:
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("GOOGLE_API_KEY", None)


def update_env_file(key_values: dict[str, str]) -> None:
    """
    Safely updates or sets key-value pairs in the .env file without destroying other entries.
    Calls reload_env() immediately after writing to disk.
    """
    env_path = BASE_DIR / ".env"
    lines = []
    found_keys = set()

    if env_path.exists():
        with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k = stripped.split("=", 1)[0].strip()
                    if k in key_values:
                        lines.append(f"{k}={key_values[k]}\n")
                        found_keys.add(k)
                        continue
                lines.append(line)

    for k, v in key_values.items():
        if k not in found_keys:
            lines.append(f"{k}={v}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    for k, v in key_values.items():
        if v:
            os.environ[k] = v

    reload_env()


# Initial environment load
reload_env()


class Settings:
    """Application configuration settings with dynamic environment reflection."""
    APP_NAME: str = "AI Student Copilot"
    APP_VERSION: str = "2.0.0"

    DEFAULT_DB_PATH: str = (DATA_DIR / "ai_student_copilot.db").as_posix()

    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = DATA_DIR
    UPLOAD_DIR: Path = UPLOAD_DIR
    VECTOR_STORE_PATH: Path = VECTOR_STORE_PATH

    MAX_FILE_SIZE_MB: int = 25
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".docx", ".txt", ".md", ".csv", ".json"]

    @property
    def APP_ENV(self) -> str:
        return os.getenv("APP_ENV", "development")

    @property
    def LOG_LEVEL(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO")

    @property
    def DATABASE_URL(self) -> str:
        return os.getenv("DATABASE_URL", f"sqlite:///{self.DEFAULT_DB_PATH}")

    @property
    def GEMINI_API_KEY(self) -> str:
        """Reads GEMINI_API_KEY with GOOGLE_API_KEY and AI_API_KEY fallback."""
        return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("AI_API_KEY") or "").strip()

    @property
    def GOOGLE_API_KEY(self) -> str:
        return self.GEMINI_API_KEY

    @property
    def GEMINI_MODEL(self) -> str:
        """Currently supported GA Gemini model."""
        return (os.getenv("GEMINI_MODEL") or os.getenv("AI_MODEL") or "gemini-2.0-flash").strip()

    @property
    def OPENAI_API_KEY(self) -> str:
        return (os.getenv("OPENAI_API_KEY") or "").strip()

    @property
    def OPENAI_MODEL(self) -> str:
        return (os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()

    @property
    def EMBEDDING_MODEL(self) -> str:
        return (os.getenv("EMBEDDING_MODEL") or "text-embedding-3-small").strip()

    @property
    def RAG_TOP_K(self) -> int:
        try:
            return int(os.getenv("RAG_TOP_K", "5"))
        except (ValueError, TypeError):
            return 5

    @property
    def MAX_CONTEXT_CHARS(self) -> int:
        try:
            return int(os.getenv("MAX_CONTEXT_CHARS", "6000"))
        except (ValueError, TypeError):
            return 6000

    @property
    def PREFERRED_PROVIDER(self) -> str:
        return os.getenv("PREFERRED_PROVIDER", "auto").strip().lower()

    @property
    def JWT_SECRET(self) -> str:
        return os.getenv("JWT_SECRET", "ai-student-copilot-dev-secret-key-change-in-production-v2").strip()

    @property
    def JWT_ALGORITHM(self) -> str:
        return os.getenv("JWT_ALGORITHM", "HS256").strip()

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        try:
            return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        except (ValueError, TypeError):
            return 60

    @property
    def REFRESH_TOKEN_EXPIRE_DAYS(self) -> int:
        try:
            return int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
        except (ValueError, TypeError):
            return 7

    @property
    def CORS_ORIGINS(self) -> list[str]:
        origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8501",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8501",
            "https://ai-student-copilot-pi.vercel.app",
        ]
        raw = os.getenv("CORS_ORIGINS", "").strip()
        if raw:
            extra: list[str] = []
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    extra = [str(item).strip() for item in parsed if str(item).strip()]
                elif isinstance(parsed, str):
                    extra = [o.strip() for o in parsed.split(",") if o.strip()]
            except Exception:
                extra = [o.strip().strip("'\"[]") for o in raw.split(",") if o.strip().strip("'\"[]")]
            for o in extra:
                if o not in origins:
                    origins.append(o)
        return origins

    @property
    def CORS_ORIGIN_REGEX(self) -> str:
        return os.getenv("CORS_ORIGIN_REGEX", r"^https:\/\/.*\.vercel\.app$").strip()

    @property
    def GEMINI_FALLBACK_MODELS(self) -> list[str]:
        raw = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.5-flash-lite,gemini-3.8-flash,gemini-2.0-flash-lite")
        return [m.strip() for m in raw.split(",") if m.strip()]

    def reload(self) -> None:
        """Refreshes environment variables from disk."""
        reload_env()


settings = Settings()
