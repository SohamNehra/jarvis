from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    chat_name: str = "default"
    project_name: Optional[str] = None
    use_multi_agent: bool = False

class ChatResponse(BaseModel):
    response: str
    chat_name: str
    project_name: Optional[str] = None

class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""

class Project(BaseModel):
    name: str
    description: str = ""
    chats: list[str] = []

class Chat(BaseModel):
    name: str
    project_name: Optional[str] = None
    message_count: int = 0

class NotesResponse(BaseModel):
    notes: dict

class UpdateNotesRequest(BaseModel):
    section: str
    key: str
    value: str

class SettingsUpdate(BaseModel):
    settings: dict

class ChatRenameRequest(BaseModel):
    old_name: str
    new_name: str
    project_name: Optional[str] = None

class ChatMoveRequest(BaseModel):
    chat_name: str
    from_project: Optional[str] = None
    to_project: Optional[str] = None