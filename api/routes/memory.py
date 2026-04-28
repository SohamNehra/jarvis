from fastapi import APIRouter, HTTPException
from fastapi import Body
from api.models import NotesResponse, UpdateNotesRequest, SettingsUpdate
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


# ── Settings endpoints ────────────────────────────────────────────────────────

_KEY_FIELDS = {"ANTHROPIC_API_KEY", "OPENAI_API_KEY", "TAVILY_API_KEY"}


def _mask(value: str) -> str:
    if not value or len(value) <= 4:
        return "***"
    return "..." + value[-4:]


@router.get("/settings")
async def get_settings():
    """return .jarvis_config.json with secret keys masked to last 4 chars"""
    from config import load_jarvis_config
    config = load_jarvis_config()
    masked = {}
    for k, v in config.items():
        if k == "services" and isinstance(v, dict):
            masked["services"] = {
                svc: {
                    sk: (_mask(sv) if isinstance(sv, str) else sv)
                    for sk, sv in svc_cfg.items()
                }
                for svc, svc_cfg in v.items()
            }
        elif k in _KEY_FIELDS and isinstance(v, str):
            masked[k] = _mask(v)
        else:
            masked[k] = v
    return {"settings": masked}


@router.put("/settings")
async def update_settings(request: SettingsUpdate):
    """write updates to .jarvis_config.json and reload module-level config vars"""
    from config import write_config
    write_config(request.settings)
    return {"message": "settings updated"}


@router.get("/settings/status")
async def get_settings_status():
    """return which config keys are set (true/false), without revealing values"""
    from config import load_jarvis_config
    config = load_jarvis_config()

    status: dict = {}
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "TAVILY_API_KEY", "MODEL_NAME"):
        val = config.get(key) or os.getenv(key)
        status[key] = bool(val)

    for svc, cfg in config.get("services", {}).items():
        status[f"services.{svc}"] = any(bool(v) for v in cfg.values())

    return {"status": status}
