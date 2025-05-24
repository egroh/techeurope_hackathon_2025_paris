import json
import logging
import uuid
from typing import List, Dict, Any, Optional, Literal # For schemas if defined in same file

from fastapi import APIRouter, WebSocket, HTTPException, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError # For schemas and error handling

# Assuming LLMAgent and schemas are structured as before
from .agent import LLMAgent # Keep if you plan to use it
from .schemas import PostUserMessage, BaseMessage, ToolCall # Ensure these are correctly defined

# If schemas are in this file, they would be here:
# class PostUserMessage(BaseModel):
#     content: str

# class ToolCall(BaseModel):
#    name: str
#    args: Dict[str, Any]

# class BaseMessage(BaseModel):
#    type: Literal["human", "ai", "tool"] = Field(..., description="Who sent the message")
#    content: str
#    conversation_id: str
#    tool_calls: Optional[List[ToolCall]] = None


router = APIRouter()
logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO) # Usually set globally, but fine here if needed


@router.websocket("/chat")
async def chat_websocket_endpoint(websocket: WebSocket): # Renamed for clarity
    await websocket.accept()
    conversation_id = str(uuid.uuid4())
    logger.info(
        f"WebSocket connection accepted. Conversation ID: {conversation_id}"
    )

    # agent = LLMAgent() # Initialize your agent here if needed per connection
    # logger.info(f"Agent initialized for conversation: {conversation_id}")

    try:
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(
                    f"Received raw data on conversation {conversation_id}: {data}"
                )

                try:
                    message_data = json.loads(data)
                    user_message = PostUserMessage(**message_data)
                except json.JSONDecodeError:
                    logger.error(
                        f"Invalid JSON received on conversation {conversation_id}: {data}"
                    )
                    error_response = BaseMessage(
                        type="ai", # Or a new "error" type
                        content="Error: Invalid JSON format.",
                        conversation_id=conversation_id,
                    )
                    await websocket.send_text(error_response.model_dump_json())
                    continue # Or break, depending on desired behavior
                except ValidationError as e:
                    logger.error(
                        f"Validation error for incoming message on conversation {conversation_id}: {e.errors()}"
                    )
                    error_response = BaseMessage(
                        type="ai", # Or a new "error" type
                        content=f"Error: Invalid message structure. {e.errors()}",
                        conversation_id=conversation_id,
                    )
                    await websocket.send_text(error_response.model_dump_json())
                    continue # Or break

                logger.info(
                    f"Received message from user on conversation {conversation_id}: {user_message.content}"
                )

                # Placeholder for your agent's response logic
                # async for response_chunk in agent.astream(user_message.content, conversation_id):
                #     ai_response = BaseMessage(
                #         type="ai",
                #         content=response_chunk, # Assuming agent streams content string
                #         conversation_id=conversation_id
                #     )
                #     await websocket.send_text(ai_response.model_dump_json())
                #     logger.info(f"WS sent chunk to {conversation_id}: {response_chunk[:50]}...")

                # Current hardcoded response (updated to use correct conversation_id)
                ai_response_content = "Testing response from AI."
                ai_response = BaseMessage(
                    type="ai",
                    content=ai_response_content,
                    conversation_id=conversation_id, # Use the generated conversation_id
                )
                await websocket.send_text(ai_response.model_dump_json())
                logger.info(
                    f"WS sent to {conversation_id}: {ai_response_content}"
                )

            except WebSocketDisconnect:
                logger.info(
                    f"WebSocket disconnected for conversation ID: {conversation_id}"
                )
                # Add any cleanup logic here if needed (e.g., if agent holds resources)
                break
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred in chat WebSocket for conversation {conversation_id}: {e}",
                    exc_info=True, # Provides traceback
                )
                # Optionally send an error message to the client before closing or breaking
                try:
                    error_response = BaseMessage(
                        type="ai", # Or "error"
                        content="An unexpected server error occurred.",
                        conversation_id=conversation_id,
                    )
                    await websocket.send_text(error_response.model_dump_json())
                except Exception as send_e: # Handle case where send itself fails
                    logger.error(f"Failed to send error message to client: {send_e}")
                break # Exit loop on unhandled errors to prevent infinite loops on bad state
    finally:
        # This block executes whether the try block completes normally or an exception occurs
        # (except for CancelledError from task cancellation, which is fine)
        logger.info(
            f"Closing WebSocket connection handler for conversation ID: {conversation_id}"
        )
        # `websocket.close()` is often handled by FastAPI when the handler exits,
        # but explicit close can be added if specific close codes are needed.
        # await websocket.close()


@router.get(
    "/_internal/message-schema",
    response_model=BaseMessage,
    tags=["internal"],
    summary="(internal) Message schema carrier",
    include_in_schema=True, # Explicitly ensure it's in schema
)
async def _expose_message_schema() -> BaseMessage:
    """
    **Internal** – never used in production.

    Exists only so that `BaseMessage` (and its components like `ToolCall`)
    are part of the OpenAPI spec, as WebSocket messages are not automatically
    included.
    """
    # This is a placeholder and will not be called by clients.
    # Its purpose is purely for schema generation.
    return BaseMessage(
        type="ai",
        content="Schema placeholder content.",
        conversation_id="00000000-0000-0000-0000-000000000000",
        tool_calls=[
            ToolCall(name="example_tool", args={"param1": "value1"})
        ],
    )

