# ./your_project/router.py
import json
import logging
import uuid
from typing import List, Dict, Any, Optional, Literal

from fastapi import APIRouter, WebSocket, HTTPException, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError

from .mathstral_model import MATHSTRAL_MODEL # Ensure correct import path
from .schemas import PostUserMessage, OpenAIChatMessage

router = APIRouter()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Basic config for logging


@router.websocket("/chat")
async def chat_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # For a stateful conversation, you'd manage conversation history here or in an agent
    # For now, each user message triggers a new generation stream
    # conversation_id = str(uuid.uuid4()) # New conversation per connection
    # logger.info(f"WebSocket connection accepted. New Conversation ID: {conversation_id}")
    # Let's make conversation_id more persistent if client sends it, or generate per connection
    # For simplicity, we'll generate one per connection for now.
    # A robust system would handle client-provided conversation_ids.
    active_conversation_id = str(uuid.uuid4())
    logger.info(f"WebSocket accepted for new conversation: {active_conversation_id}")

    try:
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Received raw data on conv {active_conversation_id}: {data}")

                try:
                    message_data = json.loads(data)
                    # Assuming client sends PostUserMessage structure for user text
                    user_message_payload = PostUserMessage(**message_data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON on conv {active_conversation_id}: {data}")
                    error_response = OpenAIChatMessage(
                        type="error",
                        content="Error: Invalid JSON format.",
                        conversation_id=active_conversation_id,
                    )
                    await websocket.send_text(error_response.model_dump_json())
                    continue
                except ValidationError as e:
                    logger.error(f"Validation error on conv {active_conversation_id}: {e.errors()}")
                    error_response = OpenAIChatMessage(
                        type="error",
                        content=f"Error: Invalid message structure. {e.errors()}",
                        conversation_id=active_conversation_id,
                    )
                    await websocket.send_text(error_response.model_dump_json())
                    continue

                logger.info(
                    f"User message on conv {active_conversation_id}: {user_message_payload.content}"
                )

                # Send user message back to client for display (optional, but good practice)
                # You might want a different schema for this if PostUserMessage doesn't fit OpenAIChatMessage
                # For now, let's assume client adds its own message to its UI.
                # If you want server to echo:
                # user_echo_message = OpenAIChatMessage(
                #     type="human",
                #     content=user_message_payload.content,
                #     conversation_id=active_conversation_id,
                #     message_id=str(uuid.uuid4()) # unique ID for this user message
                # )
                # await websocket.send_text(user_echo_message.model_dump_json())


                # Each AI response gets a unique ID for streaming purposes
                ai_message_id = str(uuid.uuid4())

                # Start streaming the response
                # The MATHSTRAL_MODEL.generate_stream will handle sending multiple messages
                await MATHSTRAL_MODEL.generate_stream(
                    prompt=user_message_payload.content,
                    websocket=websocket,
                    conversation_id=active_conversation_id,
                    ai_message_id=ai_message_id
                )
                logger.info(f"Stream completed for AI message {ai_message_id} on conv {active_conversation_id}")

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for conv ID: {active_conversation_id}")
                break
            except Exception as e:
                logger.error(
                    f"Error in WebSocket for conv {active_conversation_id}: {e}",
                    exc_info=True,
                )
                try:
                    error_response = OpenAIChatMessage(
                        type="error",
                        content="An unexpected server error occurred.",
                        conversation_id=active_conversation_id,
                    )
                    await websocket.send_text(error_response.model_dump_json())
                except Exception as send_e:
                    logger.error(f"Failed to send error to client: {send_e}")
                break # Important to break on unhandled errors
    finally:
        logger.info(f"Closing WebSocket handler for conv ID: {active_conversation_id}")
        # FastAPI handles closing the websocket when the handler exits or due to WebSocketDisconnect

# ... (rest of your router.py, including the _internal schema endpoint)
# Ensure the _internal schema endpoint uses the updated OpenAIChatMessage
@router.get(
    "/_internal/message-schema",
    response_model=OpenAIChatMessage, # Use the most comprehensive one
    tags=["internal"],
    summary="(internal) Message schema carrier",
    include_in_schema=True,
)
async def _expose_message_schema():
    raise HTTPException(status_code=404, detail="Internal schema endpoint only.")

