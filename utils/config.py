import json
from pathlib import Path

import streamlit as st


CONFIG_FILE = Path("config.json")


def load_config() -> dict:
    """Load configuration from disk."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(config: dict) -> bool:
    """Persist configuration to disk."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"설정 저장 중 오류가 발생했습니다: {e}")
        return False


def get_openai_api_key() -> str:
    """Return stored OpenAI API key if available."""
    config = load_config()
    return config.get("openai_api_key", "")


def save_openai_api_key(api_key: str) -> bool:
    """Store OpenAI API key."""
    config = load_config()
    config["openai_api_key"] = api_key
    return save_config(config)
