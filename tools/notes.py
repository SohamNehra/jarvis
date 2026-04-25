from langchain_core.tools import tool
import json
import os

NOTES_FILE = "memory/user_notes.json"

DEFAULT_NOTES = {
    "profile": {
        "name": "",
        "occupation": "",
        "location": "",
        "preferences": ""
    },
    "current_focus": {
        "projects": "",
        "goals": "",
        "recent_activity": ""
    },
    "history": {
        "background": "",
        "past_projects": "",
        "interests": ""
    },
    "chat_summaries": [],
    "important_facts": {}
}

def _load() -> dict:
    if not os.path.exists(NOTES_FILE) or os.path.getsize(NOTES_FILE) == 0:
        return DEFAULT_NOTES.copy()
    with open(NOTES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(notes: dict):
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2)

@tool
def update_notes(section: str, key: str, value: str) -> str:
    """Update a specific field in the user notes.
    section: top-level key (profile, current_focus, history, important_facts).
    key: the field name within that section.
    value: the new value to store."""
    notes = _load()
    if section not in notes:
        return f"Error: unknown section '{section}'. Valid sections: {list(notes.keys())}"
    target = notes[section]
    if not isinstance(target, dict):
        return f"Error: section '{section}' is not a key-value store (use add_chat_summary for chat_summaries)."
    target[key] = value
    _save(notes)
    return f"Updated {section}.{key}"

@tool
def read_notes(section: str = "") -> str:
    """Read user notes. Pass a section name to read just that section,
    or leave empty to read all notes."""
    notes = _load()
    if section:
        if section not in notes:
            return f"Error: unknown section '{section}'. Valid sections: {list(notes.keys())}"
        return json.dumps(notes[section], indent=2)
    return json.dumps(notes, indent=2)

@tool
def add_chat_summary(summary: str) -> str:
    """Append a summary of the current conversation to the chat_summaries list."""
    notes = _load()
    notes["chat_summaries"].append(summary)
    _save(notes)
    return "Chat summary saved."

PROJECT_NOTES_FILE = None  # gets set at runtime

def set_project(project_name: str):
    """called by run_agent to set current project context"""
    global PROJECT_NOTES_FILE
    if project_name:
        path = f"memory/projects/{project_name}/project_notes.json"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        PROJECT_NOTES_FILE = path
    else:
        PROJECT_NOTES_FILE = None

@tool
def update_project_notes(key: str, value: str) -> str:
    """Update notes specific to the current project.
    Use this for project-specific context, goals, decisions, and technical details.
    Different from user notes which store personal profile information."""
    if not PROJECT_NOTES_FILE:
        return "No active project. Use update_notes for general information."
    
    if os.path.exists(PROJECT_NOTES_FILE) and os.path.getsize(PROJECT_NOTES_FILE) > 0:
        with open(PROJECT_NOTES_FILE, "r") as f:
            notes = json.load(f)
    else:
        notes = {}
    
    notes[key] = value
    with open(PROJECT_NOTES_FILE, "w") as f:
        json.dump(notes, f, indent=2)
    return f"Saved to project notes: {key}"

@tool
def read_project_notes() -> str:
    """Read all notes for the current project.
    Use this when working on project-specific tasks."""
    if not PROJECT_NOTES_FILE:
        return "No active project."
    if not os.path.exists(PROJECT_NOTES_FILE) or os.path.getsize(PROJECT_NOTES_FILE) == 0:
        return "No project notes yet."
    with open(PROJECT_NOTES_FILE, "r") as f:
        return json.dumps(json.load(f), indent=2)