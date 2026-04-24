import json
import os
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

MEMORY_FILE = "memory/chat_history.json"
MAX_MESSAGES = 20  # sliding window size

def save_history(messages: list):
    """save messages to disk, keeping only last MAX_MESSAGES"""
    
    # strip SystemMessage before saving, we always add it fresh on load
    to_save = []
    for m in messages:
        if isinstance(m, HumanMessage):
            to_save.append({"role": "human", "content": m.content})
        elif isinstance(m, AIMessage):
            to_save.append({"role": "ai", "content": m.content})
        # skip ToolMessages and SystemMessages, not needed long term

    # sliding window - keep only last MAX_MESSAGES
    to_save = to_save[-MAX_MESSAGES:]

    with open(MEMORY_FILE, "w") as f:
        json.dump(to_save, f, indent=2)

def load_history() -> list:
    if not os.path.exists(MEMORY_FILE):
        return []
    
    # handle empty file
    if os.path.getsize(MEMORY_FILE) == 0:
        return []
    
    with open(MEMORY_FILE, "r") as f:
        data = json.load(f)

    messages = []
    for m in data:
        if m["role"] == "human":
            messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "ai":
            messages.append(AIMessage(content=m["content"]))

    return messages