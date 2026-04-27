from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from api.models import ChatRequest, ChatResponse
from agent.core import run_agent
from agent.supervisor import run_supervisor
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from config import OPENAI_API_KEY, LOOP_CHECK_MODEL
import json
import asyncio

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
    """streaming chat endpoint - returns tokens as they generate"""
    
    async def generate():
        # run agent in thread pool to not block async event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            route_request,
            request.message,
            request.chat_name,
            request.project_name,
            request.use_multi_agent
        )
        
        # stream the response word by word
        # real token streaming requires LangChain .stream() - upgrade later
        words = response.split(" ")
        for word in words:
            data = json.dumps({"token": word + " ", "done": False})
            yield f"data: {data}\n\n"
            await asyncio.sleep(0.02)  # small delay for smooth streaming effect
        
        # send done signal
        yield f"data: {json.dumps({'token': '', 'done': True})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )