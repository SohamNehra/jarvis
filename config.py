from dotenv import load_dotenv
import os

load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
#MODEL_NAME = "gpt-5.4-nano"  # cheap and fast, good for testing
MODEL_NAME = "claude-haiku-4-5-20251001"
TEMPERATURE = 0
DEBUG = True
LOOP_CHECK_MODEL = "gpt-5.4-nano"