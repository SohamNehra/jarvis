from fastapi import APIRouter
from api.models import CreateProjectRequest, Project, Chat
import os
import json

router = APIRouter()

@router.get("/projects")
async def list_projects():
    """list all projects"""
    projects_dir = "memory/projects"
    if not os.path.exists(projects_dir):
        return {"projects": []}
    
    projects = []
    for name in os.listdir(projects_dir):
        if os.path.isdir(f"{projects_dir}/{name}"):
            chats_dir = f"{projects_dir}/{name}/chats"
            chats = []
            if os.path.exists(chats_dir):
                chats = [f.replace(".json", "") for f in os.listdir(chats_dir) if f.endswith(".json")]
            projects.append({"name": name, "chats": chats})
    
    return {"projects": projects}

@router.post("/projects")
async def create_project(request: CreateProjectRequest):
    """create a new project"""
    path = f"memory/projects/{request.name}"
    os.makedirs(f"{path}/chats", exist_ok=True)
    
    notes_path = f"{path}/project_notes.json"
    if not os.path.exists(notes_path):
        with open(notes_path, "w") as f:
            json.dump({"overview": request.description}, f, indent=2)
    
    return {"message": f"project '{request.name}' created", "name": request.name}

@router.get("/chats")
async def list_chats(project_name: str = None):
    """list all chats, optionally filtered by project"""
    if project_name:
        chats_dir = f"memory/projects/{project_name}/chats"
    else:
        chats_dir = "memory/chats"
    
    if not os.path.exists(chats_dir):
        return {"chats": []}
    
    chats = []
    for f in os.listdir(chats_dir):
        if f.endswith(".json"):
            chat_name = f.replace(".json", "")
            path = f"{chats_dir}/{f}"
            size = os.path.getsize(path)
            chats.append({"name": chat_name, "project": project_name, "size": size})
    
    return {"chats": chats}