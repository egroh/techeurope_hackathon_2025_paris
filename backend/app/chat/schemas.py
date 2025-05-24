from pydantic import BaseModel, Field
from typing import Literal, List, Dict, Any, Optional

class PostUserMessage(BaseModel):
    content: str

class ToolCall(BaseModel):
   name: str
   args: Dict[str, Any]

class OpenAIChatMessage(BaseModel):
   type: Literal["human", "ai", "tool"] = Field(..., description="Who sent the message")
   content: str
   conversation_id: str
   tool_calls: Optional[List[ToolCall]] = None

class ChatMessageResponse(BaseModel):
   content: str
