import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory pointing to project root
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file at project root if present
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


class ConfigurationError(Exception):
    """Custom exception raised when a required configuration or API key is missing or empty."""
    pass


def get_api_key(key_name: str, provider_name: str) -> str:
    """
    Retrieve an API key from environment variables.
    
    Raises ConfigurationError if the key is missing or empty when requested.
    """
    key = os.getenv(key_name)
    if not key or not key.strip():
        raise ConfigurationError(
            f"Missing {provider_name} API Key. Please set '{key_name}' in your local .env file or system environment variables."
        )
    return key.strip()


def get_groq_api_key() -> str:
    """Retrieve the Groq API key dynamic value."""
    return get_api_key("GROQ_API_KEY", "Groq")


class Config:
    """Modular configuration manager for API keys and global settings."""
    
    @property
    def GROQ_API_KEY(self) -> str:
        return get_groq_api_key()

    @staticmethod
    def get_groq_api_key() -> str:
        return get_groq_api_key()

    @staticmethod
    def get_provider_key(key_name: str, provider_name: str) -> str:
        """Helper for fetching any future API key modularly."""
        return get_api_key(key_name, provider_name)


config = Config()


def __getattr__(name: str):
    """
    Allow dynamic module attribute access (e.g., `from backend.config import GROQ_API_KEY`)
    so keys are fetched and validated dynamically only when accessed.
    """
    if name == "GROQ_API_KEY":
        return get_groq_api_key()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
