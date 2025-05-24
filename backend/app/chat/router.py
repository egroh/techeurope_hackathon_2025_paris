import json
from fastapi import APIRouter, WebSocket
import logging
import uuid

from fastapi import APIRouter, HTTPException
from .agent import LLMAgent
from .schemas import PostUserMessage, BaseMessage
from ..example.schemas import ExampleResponse

router = APIRouter()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# create web socket connection for chat 
@router.websocket("/chat")
async def chat(websocket: WebSocket):
    logger.info("WebSocket connection accepted")
    await websocket.accept()
    conversation_id = str(uuid.uuid4())
    logger.info("WebSocket connection accepted")
    
    # agent = LLMAgent()
    logger.info("Agent initialized")
    while True:
        data = await websocket.receive_text()
        logger.info(f"Received message: {data}")
        
        message = PostUserMessage(**json.loads(data))
        
        # async for response in agent.astream(message.content, conversation_id):
        logger.info(f"WS sent: {"Testing"}")
        response = BaseMessage(type="ai", content="Testing", conversation_id="0")

        await websocket.send_text(response.model_dump_json())

@router.get(
    "/_internal/message-schema",
    response_model=BaseMessage,
    tags=["internal"],          # mark it so you can filter it out in Swagger
    summary="(internal) Message schema carrier",
)
async def _expose_message_schema() -> BaseMessage:
    """
    **Internal** – never used in production.

    Exists only so that `Message` is part of the OpenAPI spec
    (otherwise it would be stripped because WebSockets are ignored).
    """
    # We return a placeholder; the client will never call this.
    return BaseMessage(type="ai", content="example", conversation_id="00000000")

