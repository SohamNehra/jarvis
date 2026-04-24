import json
import os
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

MEMORY_FILE = "memory/chat_history.json"
MAX_MESSAGES = 20  # sliding window size

def save_history(messages: list):
    to_save = []
    for m in messages:
        if isinstance(m, HumanMessage):
            to_save.append({"role": "human", "content": m.content})
        elif isinstance(m, AIMessage):
            # only save if it has actual text content, skip tool_use only messages
            if m.content and isinstance(m.content, str) and m.content.strip():
                to_save.append({"role": "ai", "content": m.content})

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