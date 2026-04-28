from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from api.models import ChatRequest, ChatResponse, ChatRenameRequest, ChatMoveRequest
from agent.core import run_agent, run_agent_streaming
from agent.supervisor import run_supervisor
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from config import OPENAI_API_KEY, LOOP_CHECK_MODEL
import json
import asyncio
import queue as _queue
import os

router = APIRouter()


def route_request(user_input: str, chat_name: str, project_name: str = None, force_multi: bool = False) -> str:
    if force_multi:
        return run_supervisor(user_input)

    router_llm = ChatOpenAI(model=LOOP_CHECK_MODEL, temperature=0, api_key=OPENAI_API_KEY)
    response = router_llm.invoke([
        SystemMessage(content="""Decide if this task needs multiple specialist agents or a single agent.
        ONLY use multi-agent when ALL of these are true:
        - Task has 3 or more clearly distinct phases
        - Phases require genuinely different expertise
        - Task would clearly benefit from parallel execution
        For everything else reply 'single'.
        Reply with ONLY 'multi' or 'single'."""),
        HumanMessage(content=user_input)
    ])

    if response.content.strip().lower() == "multi":
        return run_supervisor(user_input)
    return run_agent(user_input, chat_name, project_name)


@router.post("/chat")
async def chat(request: ChatRequest):
    """non-streaming chat endpoint"""
    response = route_request(
        request.message,
        request.chat_name,
        request.project_name,
        request.use_multi_agent
    )
    return ChatResponse(
        response=response,
        chat_name=request.chat_name,
        project_name=request.project_name
    )


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE streaming endpoint.
    Emits tool_start / tool_end events then streams the final response word-by-word.
    Multi-agent requests are supported but without tool events (supervisor is opaque)."""

    async def generate():
        loop = asyncio.get_event_loop()

        if request.use_multi_agent:
            response = await loop.run_in_executor(None, run_supervisor, request.message)
            for word in response.split(" "):
                yield f"data: {json.dumps({'token': word + ' ', 'done': False})}\n\n"
                await asyncio.sleep(0.02)

        else:
            event_queue: _queue.Queue = _queue.Queue()
            future = loop.run_in_executor(
                None,
                run_agent_streaming,
                request.message,
                request.chat_name,
                request.project_name,
                event_queue,
            )

            done = False
            while not done:
                try:
                    event = event_queue.get_nowait()
                except _queue.Empty:
                    await asyncio.sleep(0.05)
                    continue

                if event is None:
                    done = True

                elif event["type"] in ("tool_start", "tool_end"):
                    yield f"data: {json.dumps(event)}\n\n"

                elif event["type"] == "response":
                    words = event["content"].split(" ")
                    for i, word in enumerate(words):
                        tok = word + (" " if i < len(words) - 1 else "")
                        yield f"data: {json.dumps({'token': tok, 'done': False})}\n\n"
                        await asyncio.sleep(0.02)

                elif event["type"] == "error":
                    yield f"data: {json.dumps({'error': event['message'], 'done': True})}\n\n"
                    done = True

            await future

        yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get("/chat/history")
async def get_chat_history(chat_name: str = "default", project_name: str = None):
    """load chat history for a specific chat session"""
    from memory.memory import load_history
    from langchain_core.messages import HumanMessage, AIMessage

    messages = load_history(chat_name, project_name)

    result = []
    for m in messages:
        if isinstance(m, HumanMessage):
            result.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            result.append({"role": "assistant", "content": m.content})

    return {"messages": result, "chat_name": chat_name, "project_name": project_name}


@router.post("/chat/rename")
async def rename_chat(request: ChatRenameRequest):
    """rename a chat session; also moves the .meta.json file"""
    from memory.memory import get_chat_path
    old_path = get_chat_path(request.old_name, request.project_name)
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


@router.post("/chat/move")
async def move_chat(request: ChatMoveRequest):
    """move a chat between global chats and a project (or between projects)"""
    from memory.memory import get_chat_path
    src = get_chat_path(request.chat_name, request.from_project)
    dst = get_chat_path(request.chat_name, request.to_project)
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
    return {"message": f"moved '{request.chat_name}' to {target}"}
