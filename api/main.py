from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import chat, projects, memory

app = FastAPI(
    title="Jarvis API",
    description="Personal AI Agent API",
    version="2.0.0"
)

# allow React frontend to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(memory.router, prefix="/api", tags=["memory"])

@app.get("/")
async def root():
    return {"message": "Jarvis API is running", "version": "2.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}