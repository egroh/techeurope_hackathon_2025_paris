# ./your_project/schemas.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
import uuid

class PostUserMessage(BaseModel):
    content: str
    # conversation_id: Optional[str] = None # Client might not send this initially

class ToolCall(BaseModel): # If you plan to use tools
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["function"] = "function"
    function: Dict[str, Any] # e.g. {"name": "calculator", "arguments": "{ \"query\": \"2+2\" }"}

class OpenAIChatMessage(BaseModel): # Used for sending messages TO client
    id: str = Field(default_factory=lambda: str(uuid.uuid4())) # Message instance ID
    conversation_id: str
    type: Literal["human", "ai", "system", "error", "tool_request", "tool_response"]
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None # For tool_response type

    # For streaming
    message_id: Optional[str] = None # ID of the specific AI response being streamed
    stream_event: Optional[Literal["start", "chunk", "end"]] = None

    class Config:
        use_enum_values = True