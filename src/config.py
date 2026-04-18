"""Configuration utilities for loading settings from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def get_env(key: str, default: str = None) -> str | None:
    """Get environment variable value.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        Environment variable value or default
    """
    return os.getenv(key, default)


def get_required_env(key: str) -> str:
    """Get required environment variable.
    
    Args:
        key: Environment variable name
        
    Returns:
        Environment variable value
        
    Raises:
        ValueError: If environment variable is not set
    """
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Required environment variable '{key}' is not set. "
                        f"Please set it in your .env file or environment.")
    return value


# API Configuration
OPENAI_API_KEY = get_env("OPENAI_API_KEY")
OPENAI_BASE_URL = get_env("OPENAI_BASE_URL", "https://api.openai.com/v1")

ANTHROPIC_API_KEY = get_env("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL = get_env("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1")

# Model Configuration
EMBEDDING_MODEL = get_env("EMBEDDING_MODEL", "text-embedding-3-large")


def get_llm_config(provider: str = "openai") -> dict:
    """Get LLM configuration for the specified provider.
    
    Args:
        provider: LLM provider name ('openai' or 'anthropic')
        
    Returns:
        Configuration dictionary for create_llm_client()
    """
    provider = provider.lower()
    
    if provider == "openai":
        api_key = OPENAI_API_KEY
        base_url = OPENAI_BASE_URL
    elif provider == "anthropic":
        api_key = ANTHROPIC_API_KEY
        base_url = ANTHROPIC_BASE_URL
    else:
        raise ValueError(f"Unknown provider: {provider}")
    
    if not api_key:
        raise ValueError(
            f"API key for {provider} is not set. "
            f"Please set {provider.upper()}_API_KEY in your .env file."
        )
    
    return {
        "provider": provider,
        "api_key": api_key,
        "base_url": base_url,
    }
