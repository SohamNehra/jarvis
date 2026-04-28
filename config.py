import json
import os
from dotenv import load_dotenv

load_dotenv()

# load runtime config overrides
JARVIS_CONFIG_PATH = ".jarvis_config.json"

def load_jarvis_config() -> dict:
    if os.path.exists(JARVIS_CONFIG_PATH):
        with open(JARVIS_CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

_config = load_jarvis_config()

def get_config(key: str, default: str = None) -> str:
    return _config.get(key) or os.getenv(key) or default

def get_service_config(service: str) -> dict:
    return _config.get("services", {}).get(service, {})

def write_config(updates: dict):
    current = load_jarvis_config()
    for key, value in updates.items():
        if key == "services" and isinstance(value, dict) and isinstance(current.get("services"), dict):
            for svc, cfg in value.items():
                if isinstance(cfg, dict) and isinstance(current["services"].get(svc), dict):
                    current["services"][svc].update(cfg)
                else:
                    current["services"][svc] = cfg
        else:
            current[key] = value
    with open(JARVIS_CONFIG_PATH, "w") as f:
        json.dump(current, f, indent=2)
    reload_config()

def reload_config():
    global _config, ANTHROPIC_API_KEY, OPENAI_API_KEY, TAVILY_API_KEY, MODEL_NAME, LOOP_CHECK_MODEL, SECURITY_CHECK_MODEL
    _config = load_jarvis_config()
    ANTHROPIC_API_KEY = get_config("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = get_config("OPENAI_API_KEY")
    TAVILY_API_KEY = get_config("TAVILY_API_KEY")
    MODEL_NAME = get_config("MODEL_NAME", "claude-haiku-4-5-20251001")
    LOOP_CHECK_MODEL = get_config("LOOP_CHECK_MODEL", "gpt-4.1-nano")
    SECURITY_CHECK_MODEL = get_config("SECURITY_CHECK_MODEL", "gpt-4.1-nano")

ANTHROPIC_API_KEY = get_config("ANTHROPIC_API_KEY")
OPENAI_API_KEY = get_config("OPENAI_API_KEY")
TAVILY_API_KEY = get_config("TAVILY_API_KEY")
MODEL_NAME = get_config("MODEL_NAME", "claude-haiku-4-5-20251001")
LOOP_CHECK_MODEL = get_config("LOOP_CHECK_MODEL", "gpt-4.1-nano")
SECURITY_CHECK_MODEL = get_config("SECURITY_CHECK_MODEL", "gpt-4.1-nano")
TEMPERATURE = 0
AGENT_TIMEOUT_SECONDS = 60
MAX_PARALLEL_AGENTS = 3
DEBUG = False