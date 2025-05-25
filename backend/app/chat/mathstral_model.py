# ./your_project/mathstral_model.py
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
from transformers import BitsAndBytesConfig
import torch
from huggingface_hub import login

import asyncio
import os
from threading import Thread
import uuid
import logging
import traceback

logger = logging.getLogger(__name__)
# Assuming global logging is configured elsewhere in your FastAPI app
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Use getenv for HF_HOME for flexibility, default to /tmp/huggingface_cache
os.environ["HF_HOME"] = os.getenv("HF_HOME", "/tmp/huggingface_cache")

_verification_prompt_header = """You are a helpful math tutor. I will give you:\n"
- A mathematical question\n"
- A step-by-step answer\n
- A list of related theorems or definitions\n

Please generate a clear and logical explanation that:\n
- Restates the question in simple terms\n
- Explains each step of the solution, referencing the relevant theorems where appropriate\n
- Also validate step by step solution based on related theorems\n
- Provides insight into why each step works\n
- Optionally, summarizes the overall strategy at the end
"""

def _format_prompt_for_verification(question: str, step_by_step_answer: str, related_thms: str) -> str:
    prompt_formatted = f"""
Question:
{question}

Step-by-step Answer:
{step_by_step_answer}

Related Theorems/Definitions:
{related_thms}
    """
    return prompt_formatted

class MathstralModel(object):
    def __init__(self):
        logger.info("Initializing MathstralModel...")
        model_name = "mistralai/Mathstral-7B-v0.1"
        # IMPORTANT: Use environment variables for tokens in production
        access_token = os.getenv(
            "HF_ACCESS_TOKEN", "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"
        )  # Example token
        if (
            not access_token
            or access_token == "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"
        ):  # Check if it's the placeholder
            logger.warning(
                "HF_ACCESS_TOKEN is using a placeholder or not set. "
                "Ensure it's correctly configured if the model is private or gated."
            )
            # Not raising an error, as public/cached models might still work.
        try:
            login(token=access_token)
            logger.info("Hugging Face login successful.")
        except Exception as e:
            logger.warning(
                f"Hugging Face login failed: {e}. This might be an issue for gated models not locally cached.",
                exc_info=False,
            ) # Log less verbosely if login is not strictly required

        bnb_config = BitsAndBytesConfig(
            load_in_8bit=True,
        )
        logger.info(
            f"Loading model: {model_name} with BitsAndBytes 8-bit config."
        )
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=bnb_config,
                device_map="auto",  # Recommended for automatic device placement
            )
            logger.info("AutoModelForCausalLM.from_pretrained call completed.")

            if hasattr(self.model, "hf_device_map"):
                logger.info(f"Model device map: {self.model.hf_device_map}")
                is_on_cuda = any(
                    p.device.type == "cuda" for p in self.model.parameters()
                )
                logger.info(
                    f"Model is on CUDA: {is_on_cuda} (based on parameter check)"
                )
            elif torch.cuda.is_available(): # Fallback if device_map not effective or not used
                logger.info(
                    f"CUDA available. Moving model to default CUDA device: cuda:{torch.cuda.current_device()}"
                )
                self.model = self.model.to("cuda")
                logger.info(f"Model is on device: {self.model.device}")
            else:
                logger.warning(
                    "CUDA not available, using CPU. This will be very slow."
                )
                if not hasattr(self.model, 'hf_device_map'): # Ensure it's moved if not device_mapped
                    self.model = self.model.to("cpu")
                logger.info(f"Model is on device: {self.model.device if hasattr(self.model, 'device') else 'CPU (assumed)'}")


        except Exception as e:
            logger.error(
                f"Failed to load model or move to device: {e}", exc_info=True
            )
            raise

        logger.info(f"Loading tokenizer: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if self.tokenizer.pad_token_id is None:
            logger.info(
                "Tokenizer pad_token_id is None, setting to eos_token_id."
            )
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        logger.info(
            f"Tokenizer loaded. EOS: {self.tokenizer.eos_token_id}, PAD: {self.tokenizer.pad_token_id}"
        )
        logger.info("MathstralModel initialized successfully.")

    def _format_prompt(self, prompt: str, is_verification_step: bool=False) -> str:
        if is_verification_step:
            content = _verification_prompt_header + "\n" + prompt
        else:
            content = prompt + "\n" + "Give a detailed step-by-step solution. Start each step with '<step N>' where N is the step number."

        messages = [
            {
                "role": "user",
                "content": content,
            }
        ]
        formatted_prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        return formatted_prompt

    def _generate_in_thread(
        self, generation_kwargs: dict, streamer: TextIteratorStreamer
    ):
        try:
            logger.debug("Generation Thread: Starting self.model.generate()")
            self.model.generate(**generation_kwargs)
            logger.debug(
                "Generation Thread: self.model.generate() finished successfully."
            )
        except Exception as e:
            logger.error(
                f"Generation Thread: EXCEPTION in self.model.generate(): {e}"
            )
            logger.error(traceback.format_exc())
        finally:
            logger.debug(
                "Generation Thread: Closing streamer (streamer.end())."
            )
            streamer.end()

    async def generate_stream(
        self,
        prompt: str,
        websocket,
        conversation_id: str,
        ai_message_id: str,
        is_verification_step: bool=False
    ) -> str:  # Added return type hint
        # To avoid circular import if schemas.py imports this file
        from .schemas import OpenAIChatMessage

        logger.info(
            f"[{conversation_id}-{ai_message_id}] Formatting prompt: '{prompt[:50]}...'"
        )
        formatted_prompt = self._format_prompt(prompt, is_verification_step)
        full_response_for_log = ""  # Initialize here

        try:
            # Determine target device for inputs
            target_device = next(self.model.parameters()).device if hasattr(self.model, 'hf_device_map') and self.model.hf_device_map else self.model.device
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt").to(target_device)
            logger.info(
                f"[{conversation_id}-{ai_message_id}] Inputs tokenized and moved to device: {inputs['input_ids'].device}"
            )
        except Exception as e:
            logger.error(
                f"[{conversation_id}-{ai_message_id}] Error during input tokenization/processing: {e}",
                exc_info=True,
            )
            error_response = OpenAIChatMessage(
                type="error",
                content="Error processing your request before generation.",
                conversation_id=conversation_id,
                message_id=ai_message_id,
                stream_event="error", # Custom event
            )
            try:
                await websocket.send_text(error_response.model_dump_json())
            except Exception as send_err:
                logger.error(f"[{conversation_id}-{ai_message_id}] Failed to send pre-generation error to client: {send_err}")
            return "" # Return empty string on error

        streamer = TextIteratorStreamer(
            self.tokenizer, skip_prompt=True, skip_special_tokens=True
        )

        generation_kwargs = {
            **inputs,
            "streamer": streamer,
            "max_new_tokens": 2048, # Increased from original example
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
            # "do_sample": True,
            # "temperature": 0.7,
            # "top_p": 0.9,
        }

        thread = Thread(
            target=self._generate_in_thread,
            args=(generation_kwargs, streamer),
        )

        logger.info(
            f"[{conversation_id}-{ai_message_id}] Starting generation thread."
        )
        thread.start()
        logger.debug(
            f"[{conversation_id}-{ai_message_id}] Generation thread started."
        )

        try:
            start_message = OpenAIChatMessage(
                type="ai",
                content="",
                conversation_id=conversation_id,
                message_id=ai_message_id,
                stream_event="start",
            )
            await websocket.send_text(start_message.model_dump_json())
            logger.info(
                f"[{conversation_id}-{ai_message_id}] Sent 'start' stream event."
            )

            chunks_sent = 0
            for new_text in streamer:
                if new_text:
                    full_response_for_log += new_text
                    chunk_message = OpenAIChatMessage(
                        type="ai",
                        content=new_text,
                        conversation_id=conversation_id,
                        message_id=ai_message_id,
                        stream_event="chunk",
                    )
                    await websocket.send_text(
                        chunk_message.model_dump_json()
                    )
                    chunks_sent += 1
                    await asyncio.sleep(0) # Yield control

            logger.info(
                f"[{conversation_id}-{ai_message_id}] Streamer loop finished. Sent {chunks_sent} chunks. "
                f"Full response preview: '{full_response_for_log[:100]}...'"
            )

        except Exception as e:
            logger.error(
                f"[{conversation_id}-{ai_message_id}] Error during websocket send or stream iteration: {e}",
                exc_info=True,
            )
        finally:
            logger.debug(
                f"[{conversation_id}-{ai_message_id}] Waiting for generation thread to join."
            )
            thread.join()
            logger.debug(
                f"[{conversation_id}-{ai_message_id}] Generation thread joined."
            )

            end_message = OpenAIChatMessage(
                type="ai",
                content="",
                conversation_id=conversation_id,
                message_id=ai_message_id,
                stream_event="end",
            )
            try:
                await websocket.send_text(end_message.model_dump_json())
                logger.info(
                    f"[{conversation_id}-{ai_message_id}] Sent 'end' stream event."
                )
            except Exception as e:
                logger.warning(
                    f"[{conversation_id}-{ai_message_id}] Failed to send 'end' stream event: {e}",
                    exc_info=False,
                )

        return full_response_for_log # Return the accumulated response


MATHSTRAL_MODEL = MathstralModel()
