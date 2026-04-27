from fastapi import APIRouter
from api.models import NotesResponse, UpdateNotesRequest
import json
import os

router = APIRouter()

@router.get("/notes")
async def get_notes():
    """get user profile notes"""
    path = "memory/user_notes.json"
    if not os.path.exists(path):
        return {"notes": {}}
    with open(path, "r") as f:
        return {"notes": json.load(f)}

@router.put("/notes")
async def update_notes_endpoint(request: UpdateNotesRequest):
    """update a specific note"""
    path = "memory/user_notes.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            notes = json.load(f)
    else:
        notes = {}
    
    if request.section not in notes:
        notes[request.section] = {}
    notes[request.section][request.key] = request.value
    
    with open(path, "w") as f:
        json.dump(notes, f, indent=2)
    
    return {"message": "notes updated"}

@router.get("/notes/project/{project_name}")
async def get_project_notes(project_name: str):
    """get project specific notes"""
    path = f"memory/projects/{project_name}/project_notes.json"
    if not os.path.exists(path):
        return {"notes": {}}
    with open(path, "r") as f:
        return {"notes": json.load(f)}