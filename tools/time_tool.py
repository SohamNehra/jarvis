from langchain_core.tools import tool
from datetime import datetime

@tool
def get_current_time() -> str:
    """Returns the current date and time. Use this whenever the user asks what time or date it is."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
