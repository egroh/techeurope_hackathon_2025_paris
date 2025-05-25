# ./your_project/mathstral_model.py
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
from transformers import BitsAndBytesConfig
import torch
from huggingface_hub import login

import asyncio
import os
from threading import Thread
import uuid
import logging  # Import Python's logging
import traceback  # For detailed exception trace

# Configure logger for this module
logger = logging.getLogger(__name__)
# Ensure your main FastAPI app configures logging globally, or add basicConfig here for standalone testing:
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


os.environ["HF_HOME"] = "/tmp/huggingface_cache"


class MathstralModel(object):
    def __init__(self):
        logger.info("Initializing MathstralModel...")
        model_name = "mistralai/Mathstral-7B-v0.1"
        # IMPORTANT: Use environment variables for tokens in production
        access_token = os.getenv("HF_ACCESS_TOKEN", "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")
        if not access_token:
            logger.error("Hugging Face access token not found. Set HF_ACCESS_TOKEN environment variable.")
            raise ValueError("Hugging Face access token not found. Set HF_ACCESS_TOKEN environment variable.")
        try:
            login(token=access_token)
            logger.info("Hugging Face login successful.")
        except Exception as e:
            logger.error(f"Hugging Face login failed: {e}", exc_info=True)
            raise

        bnb_config = BitsAndBytesConfig(
            load_in_8bit=True,
        )
        logger.info(f"Loading model: {model_name} with BitsAndBytes 8-bit config.")
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=bnb_config,
                device_map="auto" # Consider using this for automatic device placement
            )
            logger.info("AutoModelForCausalLM.from_pretrained call completed.")

            if torch.cuda.is_available():
                # If not using device_map="auto", explicitly move to device
                # For device_map="auto", the model is already on the correct devices
                if not hasattr(self.model, 'hf_device_map'):  # Check if device_map handled it
                    logger.info(
                        f"CUDA available. Moving model to default CUDA device: cuda:{torch.cuda.current_device()}")
                    self.model = self.model.to("cuda")
                logger.info(f"Model is on device: {self.model.device}")
            else:
                logger.warning("CUDA not available, using CPU. This will be very slow.")
                if not hasattr(self.model, 'hf_device_map'):
                    self.model = self.model.to("cpu")
                logger.info(f"Model is on device: {self.model.device}")

        except Exception as e:
            logger.error(f"Failed to load model or move to device: {e}", exc_info=True)
            raise

        logger.info(f"Loading tokenizer: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if self.tokenizer.pad_token_id is None:
            logger.info("Tokenizer pad_token_id is None, setting to eos_token_id.")
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        logger.info(f"Tokenizer loaded. EOS: {self.tokenizer.eos_token_id}, PAD: {self.tokenizer.pad_token_id}")
        logger.info("MathstralModel initialized successfully.")

    def _format_prompt(self, prompt: str) -> str:
        # This format is good.
        messages = [
            {"role": "user", "content": prompt + "\n" +
                                        "Give a detailed step-by-step solution. Start each step with '<step N>' where N is the step number."}
        ]
        formatted_prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        return formatted_prompt

    def _generate_in_thread(self, generation_kwargs: dict, streamer: TextIteratorStreamer):
        """
        Wrapper function to run model.generate in a thread and ensure streamer is closed.
        """
        try:
            logger.info("Generation Thread: Starting self.model.generate()")
            self.model.generate(**generation_kwargs)
            logger.info("Generation Thread: self.model.generate() finished successfully.")
        except Exception as e:
            logger.error(f"Generation Thread: EXCEPTION in self.model.generate(): {e}")
            logger.error(traceback.format_exc())  # Log the full traceback
            # You could potentially try to send an error message via the streamer here if needed,
            # but closing it is the primary goal to unblock the main thread.
        finally:
            logger.info("Generation Thread: Closing streamer (streamer.end()).")
            streamer.end()  # THIS IS CRUCIAL

    async def generate_stream(self, prompt: str, websocket, conversation_id: str, ai_message_id: str):
        # To avoid circular import if schemas.py imports this file for some reason
        from .schemas import OpenAIChatMessage  # Ensure this import is correct

        logger.info(f"[{conversation_id}-{ai_message_id}] Formatting prompt: '{prompt[:50]}...'")
        formatted_prompt = self._format_prompt(prompt)

        try:
            inputs = self.tokenizer(formatted_prompt, return_tensors="pt").to(self.model.device)
            logger.info(
                f"[{conversation_id}-{ai_message_id}] Inputs tokenized and moved to device: {self.model.device}")
        except Exception as e:
            logger.error(f"[{conversation_id}-{ai_message_id}] Error during input tokenization/processing: {e}",
                         exc_info=True)
            # ... (error handling) ...
            return

        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True
        )

        # Ensure 'inputs' is correctly unpacked if it's a dictionary from the tokenizer
        # The tokenizer output is typically a dict like {'input_ids': ..., 'attention_mask': ...}
        generation_kwargs = {
            **inputs,  # Unpack input_ids, attention_mask, etc.
            "streamer": streamer,
            "max_new_tokens": 1024,
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
            # "do_sample": True, # Consider for more varied output
            # "temperature": 0.7,
            # "top_p": 0.9,
        }

        thread = Thread(target=self._generate_in_thread, args=(generation_kwargs, streamer))

        logger.info(f"[{conversation_id}-{ai_message_id}] Starting generation thread.")
        thread.start()
        logger.info(f"[{conversation_id}-{ai_message_id}] Generation thread started.")

        try:
            # Send a "start" message
            start_message = OpenAIChatMessage(
                type="ai",
                content="",  # Start with empty content
                conversation_id=conversation_id,
                message_id=ai_message_id,
                stream_event="start"
            )
            await websocket.send_text(start_message.model_dump_json())
            logger.info(f"[{conversation_id}-{ai_message_id}] Sent 'start' stream event.")

            full_response_for_log = ""
            chunks_sent = 0
            for new_text in streamer:  # This loop pulls from the queue filled by the other thread
                if new_text:
                    full_response_for_log += new_text
                    chunk_message = OpenAIChatMessage(
                        type="ai",
                        content=new_text,
                        conversation_id=conversation_id,
                        message_id=ai_message_id,
                        stream_event="chunk"
                    )
                    await websocket.send_text(chunk_message.model_dump_json())
                    chunks_sent += 1
                    # VERY IMPORTANT: Yield control to the event loop
                    await asyncio.sleep(0)  # Allows other tasks (like new connections) to be processed

            logger.info(
                f"[{conversation_id}-{ai_message_id}] Streamer loop finished. Sent {chunks_sent} chunks. Full response preview: '{full_response_for_log[:100]}...'")

        except Exception as e:
            logger.error(f"[{conversation_id}-{ai_message_id}] Error during websocket send or stream iteration: {e}",
                         exc_info=True)
        finally:
            logger.info(f"[{conversation_id}-{ai_message_id}] Waiting for generation thread to join.")
            thread.join()
            logger.info(f"[{conversation_id}-{ai_message_id}] Generation thread joined.")

            # Send an "end" message
            end_message = OpenAIChatMessage(
                type="ai",
                content="",  # No new content for the end signal
                conversation_id=conversation_id,
                message_id=ai_message_id,
                stream_event="end"
            )
            try:
                await websocket.send_text(end_message.model_dump_json())
                logger.info(f"[{conversation_id}-{ai_message_id}] Sent 'end' stream event.")
            except Exception as e:
                logger.warning(f"[{conversation_id}-{ai_message_id}] Failed to send 'end' stream event: {e}",
                               exc_info=False)

MATHSTRAL_MODEL = MathstralModel()
