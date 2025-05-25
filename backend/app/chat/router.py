# ./your_project/router.py
import json
import logging
import uuid
from typing import List, Dict, Any, Optional, Literal

from fastapi import APIRouter, WebSocket, HTTPException, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError

from .mathstral_model import MATHSTRAL_MODEL
from .mathstral_model import _format_prompt_for_verification
from .schemas import PostUserMessage, OpenAIChatMessage
# Import the new verification service
from .math_verification_pipeline import (
    MathVerificationService,
) # Ensure this path is correct

from .lesson_explainer import explain_lesson

router = APIRouter()
logger = logging.getLogger(__name__)
# Ensure logging is configured in your main FastAPI app (e.g., main.py or app.py)
# logging.basicConfig(level=logging.INFO) # Can be here for standalone router testing

# Instantiate the verification service.
# This could also be managed via FastAPI's dependency injection system for larger apps.
try:
    MATH_VERIFICATION_SERVICE = MathVerificationService()
except ImportError as e:
    logger.error(
        f"Failed to import a module for MathVerificationService (e.g., codestral_verifier): {e}. "
        "Verification will be unavailable."
    )
    MATH_VERIFICATION_SERVICE = None
except Exception as e:
    logger.error(
        f"Failed to initialize MathVerificationService: {e}. Verification will be unavailable."
    )
    MATH_VERIFICATION_SERVICE = None


@router.websocket("/chat")
async def chat_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_conversation_id = str(uuid.uuid4())
    logger.info(
        f"WebSocket accepted for new conversation: {active_conversation_id}"
    )

    try:
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(
                    f"Received raw data on conv {active_conversation_id}: {data}"
                )

                try:
                    message_data = json.loads(data)
                    user_message_payload = PostUserMessage(**message_data)
                except json.JSONDecodeError:
                    logger.error(
                        f"Invalid JSON on conv {active_conversation_id}: {data}"
                    )
                    error_response = OpenAIChatMessage(
                        type="error",
                        content="Error: Invalid JSON format.",
                        conversation_id=active_conversation_id,
                        message_id=str(uuid.uuid4()),
                    )
                    await websocket.send_text(
                        error_response.model_dump_json()
                    )
                    continue
                except ValidationError as e:
                    logger.error(
                        f"Validation error on conv {active_conversation_id}: {e.errors()}"
                    )
                    error_response = OpenAIChatMessage(
                        type="error",
                        content=f"Error: Invalid message structure. {e.errors()}",
                        conversation_id=active_conversation_id,
                        message_id=str(uuid.uuid4()),
                    )
                    await websocket.send_text(
                        error_response.model_dump_json()
                    )
                    continue

                original_problem_statement = user_message_payload.content
                logger.info(
                    f"User message on conv {active_conversation_id} (problem statement): '{original_problem_statement[:100]}...'"
                )

                ai_message_id_mathstral = str(uuid.uuid4())

                # --- Step 1: Generate Math Solution with Mathstral (Streaming) ---
                logger.info(
                    f"[{active_conversation_id}] Calling Mathstral model for solution..."
                )
                mathstral_full_solution = (
                    await MATHSTRAL_MODEL.generate_stream(
                        prompt=original_problem_statement,
                        websocket=websocket,
                        conversation_id=active_conversation_id,
                        ai_message_id=ai_message_id_mathstral,
                    )
                )
                logger.info(
                    f"[{active_conversation_id}] Mathstral stream completed. Full solution length: {len(mathstral_full_solution)}"
                )
                if not mathstral_full_solution:
                    logger.warning(
                        f"[{active_conversation_id}] Mathstral returned an empty solution."
                    )
                    # Optionally inform client if Mathstral produced nothing
                    # (though generate_stream already sends start/end chunks)

                if mathstral_full_solution:
                    logger.warning(
                        f"[{active_conversation_id}] MathVerificationService not available. Skipping verification."
                    )
                    # Optionally inform client
                    info_msg = OpenAIChatMessage(
                        type="ai", # Define in schema
                        content="Solution generated. Verification service is not used.",
                        conversation_id=active_conversation_id,
                        message_id=str(uuid.uuid4())
                    )
                    await websocket.send_text(info_msg.model_dump_json())
                else:
                    logger.info(
                        f"[{active_conversation_id}] No solution from Mathstral to verify."
                    )
                    # Client already knows stream ended, possibly with no content.

            except WebSocketDisconnect:
                logger.info(
                    f"WebSocket disconnected for conv ID: {active_conversation_id}"
                )
                break
            except Exception as e:
                logger.error(
                    f"Error in WebSocket main loop for conv {active_conversation_id}: {e}",
                    exc_info=True,
                )
                try:
                    error_response = OpenAIChatMessage(
                        type="error",
                        content="An unexpected server error occurred processing your request.",
                        conversation_id=active_conversation_id,
                        message_id=str(uuid.uuid4()),
                    )
                    await websocket.send_text(
                        error_response.model_dump_json()
                    )
                except Exception as send_e:
                    logger.error(
                        f"[{active_conversation_id}] Failed to send error to client: {send_e}"
                    )
                break  # Break from while loop on unhandled errors
    finally:
        logger.info(
            f"Closing WebSocket handler for conv ID: {active_conversation_id}"
        )


@router.websocket("/chat_with_verification")
async def chat_with_verification_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_conversation_id = str(uuid.uuid4())
    logger.info(
        f"WebSocket accepted for new conversation: {active_conversation_id}"
    )

    try:
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(
                    f"Received raw data on conv {active_conversation_id}: {data}"
                )

                try:
                    message_data = json.loads(data)
                    user_message_payload = PostUserMessage(**message_data)
                except json.JSONDecodeError:
                    logger.error(
                        f"Invalid JSON on conv {active_conversation_id}: {data}"
                    )
                    error_response = OpenAIChatMessage(
                        type="error",
                        content="Error: Invalid JSON format.",
                        conversation_id=active_conversation_id,
                        message_id=str(uuid.uuid4()),
                    )
                    await websocket.send_text(
                        error_response.model_dump_json()
                    )
                    continue
                except ValidationError as e:
                    logger.error(
                        f"Validation error on conv {active_conversation_id}: {e.errors()}"
                    )
                    error_response = OpenAIChatMessage(
                        type="error",
                        content=f"Error: Invalid message structure. {e.errors()}",
                        conversation_id=active_conversation_id,
                        message_id=str(uuid.uuid4()),
                    )
                    await websocket.send_text(
                        error_response.model_dump_json()
                    )
                    continue

                original_problem_statement = user_message_payload.content
                logger.info(
                    f"User message on conv {active_conversation_id} (problem statement): '{original_problem_statement[:100]}...'"
                )

                ai_message_id_mathstral = str(uuid.uuid4())

                # --- Step 1: Generate Math Solution with Mathstral (Streaming) ---
                logger.info(
                    f"[{active_conversation_id}] Calling Mathstral model for solution..."
                )
                mathstral_full_solution = (
                    await MATHSTRAL_MODEL.generate_stream(
                        prompt=original_problem_statement,
                        websocket=websocket,
                        conversation_id=active_conversation_id,
                        ai_message_id=ai_message_id_mathstral,
                    )
                )
                logger.info(
                    f"[{active_conversation_id}] Mathstral stream completed. Full solution length: {len(mathstral_full_solution)}"
                )
                if not mathstral_full_solution:
                    logger.warning(
                        f"[{active_conversation_id}] Mathstral returned an empty solution."
                    )
                    # Optionally inform client if Mathstral produced nothing
                    # (though generate_stream already sends start/end chunks)

                # --- Step 2: Verify Solution with Codestral (if available and solution is valid) ---
                if MATH_VERIFICATION_SERVICE and mathstral_full_solution:
                    logger.info(
                        f"[{active_conversation_id}] Proceeding to Codestral verification."
                    )
                    verification_result_dict = (
                        MATH_VERIFICATION_SERVICE.verify_solution(
                            problem_statement=original_problem_statement,
                            math_solution_str=mathstral_full_solution,
                        )
                    )
                    logger.info(
                        f"[{active_conversation_id}] Codestral verification result: {verification_result_dict}"
                    )

                    # validate based on step-by-step solution and related theorems
                    question = original_problem_statement
                    step_by_step_answer = mathstral_full_solution
                    related_thms = verification_result_dict["details"]
                    _prompt_for_verification = _format_prompt_for_verification(question, step_by_step_answer, related_thms)

                    ai_message_id_mathstral_verification = str(uuid.uuid4())
                    mathstral_full_solution_forverification = (
                        await MATHSTRAL_MODEL.generate_stream(
                            prompt=_prompt_for_verification,
                            websocket=websocket,
                            conversation_id=active_conversation_id,
                            ai_message_id=ai_message_id_mathstral_verification,
                            is_verification_step=True
                        )
                    )

                    verification_result_dict["details"] = mathstral_full_solution_forverification
                    
                    logger.info(
                        f"[{active_conversation_id}] Mathstral verification stream completed. Full solution length: {len(mathstral_full_solution_forverification)}"
                    )


                    # Send verification result back to client
                    verification_message_id = str(uuid.uuid4())
                    # You might want a specific message type for this in OpenAIChatMessage schema
                    verification_response = OpenAIChatMessage(
                        type="ai", # Define in schema if using strict types
                        content=json.dumps(
                            verification_result_dict
                        ), # Send the whole dict as JSON string
                        conversation_id=active_conversation_id,
                        message_id=verification_message_id,
                    )
                    await websocket.send_text(
                        verification_response.model_dump_json()
                    )
                    logger.info(
                        f"[{active_conversation_id}] Sent verification result to client."
                    )
                elif not MATH_VERIFICATION_SERVICE:
                    logger.warning(
                        f"[{active_conversation_id}] MathVerificationService not available. Skipping verification."
                    )
                    # Optionally inform client
                    info_msg = OpenAIChatMessage(
                        type="ai", # Define in schema
                        content="Solution generated. Verification service is unavailable.",
                        conversation_id=active_conversation_id,
                        message_id=str(uuid.uuid4())
                    )
                    await websocket.send_text(info_msg.model_dump_json())
                elif not mathstral_full_solution:
                    logger.info(
                        f"[{active_conversation_id}] No solution from Mathstral to verify."
                    )
                    # Client already knows stream ended, possibly with no content.

            except WebSocketDisconnect:
                logger.info(
                    f"WebSocket disconnected for conv ID: {active_conversation_id}"
                )
                break
            except Exception as e:
                logger.error(
                    f"Error in WebSocket main loop for conv {active_conversation_id}: {e}",
                    exc_info=True,
                )
                try:
                    error_response = OpenAIChatMessage(
                        type="error",
                        content="An unexpected server error occurred processing your request.",
                        conversation_id=active_conversation_id,
                        message_id=str(uuid.uuid4()),
                    )
                    await websocket.send_text(
                        error_response.model_dump_json()
                    )
                except Exception as send_e:
                    logger.error(
                        f"[{active_conversation_id}] Failed to send error to client: {send_e}"
                    )
                break  # Break from while loop on unhandled errors
    finally:
        logger.info(
            f"Closing WebSocket handler for conv ID: {active_conversation_id}"
        )


@router.websocket("/explain_lesson")
async def explain_lesson_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_conversation_id = str(uuid.uuid4())
    logger.info(
        f"WebSocket accepted for new conversation: {active_conversation_id}"
    )

    try:
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(
                    f"Received raw data on conv {active_conversation_id}: {data}"
                )

                try:
                    message_data = json.loads(data)
                    user_message_payload = PostUserMessage(**message_data)
                except json.JSONDecodeError:
                    logger.error(
                        f"Invalid JSON on conv {active_conversation_id}: {data}"
                    )
                    error_response = OpenAIChatMessage(
                        type="error",
                        content="Error: Invalid JSON format.",
                        conversation_id=active_conversation_id,
                        message_id=str(uuid.uuid4()),
                    )
                    await websocket.send_text(
                        error_response.model_dump_json()
                    )
                    continue
                except ValidationError as e:
                    logger.error(
                        f"Validation error on conv {active_conversation_id}: {e.errors()}"
                    )
                    error_response = OpenAIChatMessage(
                        type="error",
                        content=f"Error: Invalid message structure. {e.errors()}",
                        conversation_id=active_conversation_id,
                        message_id=str(uuid.uuid4()),
                    )
                    await websocket.send_text(
                        error_response.model_dump_json()
                    )
                    continue

                original_problem_statement = user_message_payload.content
                logger.info(
                    f"User message on conv {active_conversation_id} (problem statement): '{original_problem_statement[:100]}...'"
                )

                ai_message_id_explain_lesson = str(uuid.uuid4())

                # --- Step 1: Generate Math Solution with lesson_explain ---
                logger.info(
                    f"[{active_conversation_id}] Calling Mathstral model for solution..."
                )
                textual_prompt = original_problem_statement
                ocr_text = None # need to get ocr data from websocket
                max_tokens = 1024
                temperature = 0.6
                top_p = 0.9
                lesson_explanation = explain_lesson(textual_prompt, ocr_text,max_tokens,temperature,top_p)

                logger.info(
                    f"[{active_conversation_id}] explain_lesson completed. Full solution length: {len(lesson_explanation)}"
                )
                if not lesson_explanation:
                    logger.warning(
                        f"[{active_conversation_id}] explain_lesson returned an empty solution."
                    )

                if lesson_explanation:
                    # Optionally inform client
                    info_msg = OpenAIChatMessage(
                        type="ai", # Define in schema
                        content="Solution generated.",
                        conversation_id=active_conversation_id,
                        message_id=str(uuid.uuid4())
                    )
                    await websocket.send_text(info_msg.model_dump_json())
                else:
                    logger.info(
                        f"[{active_conversation_id}] No solution from explain_lesson."
                    )
                    # Client already knows stream ended, possibly with no content.

            except WebSocketDisconnect:
                logger.info(
                    f"WebSocket disconnected for conv ID: {active_conversation_id}"
                )
                break
            except Exception as e:
                logger.error(
                    f"Error in WebSocket main loop for conv {active_conversation_id}: {e}",
                    exc_info=True,
                )
                try:
                    error_response = OpenAIChatMessage(
                        type="error",
                        content="An unexpected server error occurred processing your request.",
                        conversation_id=active_conversation_id,
                        message_id=str(uuid.uuid4()),
                    )
                    await websocket.send_text(
                        error_response.model_dump_json()
                    )
                except Exception as send_e:
                    logger.error(
                        f"[{active_conversation_id}] Failed to send error to client: {send_e}"
                    )
                break  # Break from while loop on unhandled errors
    finally:
        logger.info(
            f"Closing WebSocket handler for conv ID: {active_conversation_id}"
        )


@router.get(
    "/_internal/message-schema",
    response_model=OpenAIChatMessage,
    tags=["internal"],
    summary="(internal) Message schema carrier",
    include_in_schema=True, # Correctly True to show in OpenAPI docs
)
async def _expose_message_schema():
    # This endpoint is for schema exposure in OpenAPI, not direct calls.
    raise HTTPException(
        status_code=404, detail="Internal schema endpoint only for schema exposure."
    )
