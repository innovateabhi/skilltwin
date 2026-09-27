from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.engine.chatbot_engine import generate_reply

router = APIRouter(prefix="/api/chat", tags=["Chatbot"])

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

class ChatResponse(BaseModel):
    reply: str

@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest):
    return {"reply": generate_reply(request.message)}
