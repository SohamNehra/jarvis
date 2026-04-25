import json
import os
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from config import ANTHROPIC_API_KEY, MODEL_NAME

MAX_MESSAGES = 20        # max messages before summarization triggers
RECENT_MESSAGES = 10     # how many recent messages to keep after summarization

# summarization llm - same model is fine here
summarization_llm = ChatAnthropic(
    model=MODEL_NAME,
    temperature=0,
    api_key=ANTHROPIC_API_KEY
)

# --- Path helpers ---

def get_chat_path(chat_name: str, project_name: str = None) -> str:
    if project_name:
        path = f"memory/projects/{project_name}/chats/{chat_name}.json"
    else:
        path = f"memory/chats/{chat_name}.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

def get_project_notes_path(project_name: str) -> str:
    path = f"memory/projects/{project_name}/project_notes.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

def get_global_notes_path() -> str:
    return "memory/user_notes.json"

# --- Serialization helpers ---

def _serialize(messages: list) -> list:
    """convert LangChain message objects to JSON serializable dicts"""
    result = []
    for m in messages:
        if isinstance(m, HumanMessage):
            result.append({"role": "human", "content": m.content})
        elif isinstance(m, AIMessage):
            if m.content and isinstance(m.content, str) and m.content.strip():
                result.append({"role": "ai", "content": m.content})
    return result

def _deserialize(data: list) -> list:
    """convert JSON dicts back to LangChain message objects"""
    messages = []
    for m in data:
        if m["role"] == "human":
            messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "ai":
            messages.append(AIMessage(content=m["content"]))
    return messages

def _load_json(path: str) -> list:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_json(path: str, data: list):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --- Summarization ---

def _summarize(messages: list) -> str:
    """compress a list of messages into a summary string"""
    conversation = "\n".join([
        f"{'User' if isinstance(m, HumanMessage) else 'Jarvis'}: {m.content}"
        for m in messages
    ])
    
    response = summarization_llm.invoke([
        HumanMessage(content=f"""Summarize this conversation segment concisely.
        Focus on: key facts learned, decisions made, tasks completed, important context.
        Keep it under 150 words. Write in third person.
        
        Conversation:
        {conversation}
        
        Summary:""")
    ])
    return response.content.strip()

# --- Core memory functions ---

def save_history(messages: list, chat_name: str = "default", project_name: str = None):
    """save messages to disk, summarizing if over limit"""
    path = get_chat_path(chat_name, project_name)
    serialized = _serialize(messages)

    if len(serialized) > MAX_MESSAGES:
        print("\nJarvis is compacting memory...")
        
        # split: old messages get summarized, recent ones kept as is
        old = _deserialize(serialized[:-RECENT_MESSAGES])
        recent = serialized[-RECENT_MESSAGES:]
        
        summary = _summarize(old)
        
        # store summary as a special message
        summary_entry = {"role": "summary", "content": summary}
        serialized = [summary_entry] + recent

    _save_json(path, serialized)

def load_history(chat_name: str = "default", project_name: str = None) -> list:
    """load chat history from disk"""
    path = get_chat_path(chat_name, project_name)
    data = _load_json(path)
    
    messages = []
    for m in data:
        if m["role"] == "human":
            messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "ai":
            messages.append(AIMessage(content=m["content"]))
        elif m["role"] == "summary":
            # inject summary as a system-like human message so LLM sees it
            messages.append(HumanMessage(
                content=f"[Previous conversation summary: {m['content']}]"
            ))
    return messages

def load_project_notes(project_name: str) -> str:
    """load project specific notes"""
    path = get_project_notes_path(project_name)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return ""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return json.dumps(data, indent=2)