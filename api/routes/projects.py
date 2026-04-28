from fastapi import APIRouter, HTTPException
from api.models import CreateProjectRequest, Project, Chat, ChatPatchRequest
import os
import json
from datetime import datetime, timezone

router = APIRouter()

PROJECTS_DIR = "memory/projects"
CHATS_DIR = "memory/chats"


def _read_meta(json_path: str) -> dict:
    meta_path = json_path[:-5] + ".meta.json"
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    mtime = os.path.getmtime(json_path)
    ts = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
    return {"created_at": ts, "updated_at": ts, "message_count": 0}


@router.get("/projects")
async def list_projects():
    """list all projects"""
    if not os.path.exists(PROJECTS_DIR):
        return {"projects": []}

    projects = []
    for name in os.listdir(PROJECTS_DIR):
        if os.path.isdir(f"{PROJECTS_DIR}/{name}"):
            chats_dir = f"{PROJECTS_DIR}/{name}/chats"
            chats = []
            if os.path.exists(chats_dir):
                chats = [
                    f.replace(".json", "")
                    for f in os.listdir(chats_dir)
                    if f.endswith(".json") and not f.endswith(".meta.json")
                ]
            projects.append({"name": name, "chats": chats})

    return {"projects": projects}


@router.post("/projects")
async def create_project(request: CreateProjectRequest):
    """create a new project"""
    path = f"{PROJECTS_DIR}/{request.name}"
    os.makedirs(f"{path}/chats", exist_ok=True)

    notes_path = f"{path}/project_notes.json"
    if not os.path.exists(notes_path):
        with open(notes_path, "w") as f:
            json.dump({"overview": request.description}, f, indent=2)

    return {"message": f"project '{request.name}' created", "name": request.name}


@router.get("/chats")
async def list_chats(project_name: str = None):
    """list chats with metadata; scans both standalone and project chats when no project_name given"""
    result = []

    if project_name:
        chats_dir = f"{PROJECTS_DIR}/{project_name}/chats"
        if os.path.isdir(chats_dir):
            for f in os.listdir(chats_dir):
                if f.endswith(".json") and not f.endswith(".meta.json"):
                    path = f"{chats_dir}/{f}"
                    meta = _read_meta(path)
                    result.append({"name": f[:-5], "project_name": project_name, **meta})
    else:
        # standalone chats
        if os.path.isdir(CHATS_DIR):
            for f in os.listdir(CHATS_DIR):
                if f.endswith(".json") and not f.endswith(".meta.json"):
                    path = f"{CHATS_DIR}/{f}"
                    meta = _read_meta(path)
                    result.append({"name": f[:-5], "project_name": None, **meta})

        # all project chats
        if os.path.isdir(PROJECTS_DIR):
            for proj in os.listdir(PROJECTS_DIR):
                proj_chats = f"{PROJECTS_DIR}/{proj}/chats"
                if os.path.isdir(proj_chats):
                    for f in os.listdir(proj_chats):
                        if f.endswith(".json") and not f.endswith(".meta.json"):
                            path = f"{proj_chats}/{f}"
                            meta = _read_meta(path)
                            result.append({"name": f[:-5], "project_name": proj, **meta})

    result.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return {"chats": result}


@router.patch("/chats/{chat_name}")
async def patch_chat(chat_name: str, request: ChatPatchRequest):
    """rename or move a chat session"""
    from memory.memory import get_chat_path

    if request.action == "rename":
        if not request.new_name:
            raise HTTPException(status_code=400, detail="new_name is required for rename")
        old_path = get_chat_path(chat_name, request.project_name)
        new_path = get_chat_path(request.new_name, request.project_name)
        if not os.path.exists(old_path):
            raise HTTPException(status_code=404, detail="Chat not found")
        if os.path.exists(new_path):
            raise HTTPException(status_code=409, detail="A chat with that name already exists")
        os.rename(old_path, new_path)
        old_meta = old_path[:-5] + ".meta.json"
        new_meta = new_path[:-5] + ".meta.json"
        if os.path.exists(old_meta):
            os.rename(old_meta, new_meta)
        return {"message": f"renamed to '{request.new_name}'"}

    elif request.action == "move":
        src = get_chat_path(chat_name, request.project_name)
        dst = get_chat_path(chat_name, request.to_project)
        if not os.path.exists(src):
            raise HTTPException(status_code=404, detail="Chat not found")
        if os.path.exists(dst):
            raise HTTPException(status_code=409, detail="A chat with that name already exists in the target")
        os.rename(src, dst)
        src_meta = src[:-5] + ".meta.json"
        dst_meta = dst[:-5] + ".meta.json"
        if os.path.exists(src_meta):
            os.rename(src_meta, dst_meta)
        target = f"project '{request.to_project}'" if request.to_project else "global chats"
        return {"message": f"moved '{chat_name}' to {target}"}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action '{request.action}'")
