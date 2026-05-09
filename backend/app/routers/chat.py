"""
Chat router — public endpoint for the platform chatbot.
No authentication required so it's accessible from any page.
"""

import asyncio

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.chatbot import generate_reply

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(
        ..., description="Conversation history (user and assistant messages)"
    )


class ChatResponse(BaseModel):
    reply: str = Field(..., description="The assistant's reply")


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest):
    """
    Send a message to the platform chatbot.
    The full conversation history is sent each time (stateless).
    No authentication required.
    """
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    # Run in a thread so the synchronous model inference
    # doesn't block the event loop (which would freeze WebSockets, etc.)
    reply = await asyncio.to_thread(generate_reply, messages)
    return ChatResponse(reply=reply)

