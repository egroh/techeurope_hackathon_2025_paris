import os
import threading
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TextIteratorStreamer
)

# 0. Set up caching directory
CACHE_DIR = "/Data/tech_paris_hack"
os.makedirs(CACHE_DIR, exist_ok=True)

# Point HF Hub and transformers at that directory
os.environ["HF_HOME"] = CACHE_DIR  # for HF Hub (models, datasets, etc.)
os.environ["TRANSFORMERS_CACHE"] = CACHE_DIR  # for transformer-specific cache

# 1. Insert your HF token here
HF_TOKEN = "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"
os.environ["HF_HUB_TOKEN"] = HF_TOKEN

# 2. Load tokenizer and model with authentication, specifying cache_dir
tokenizer = AutoTokenizer.from_pretrained(
    "mistralai/Mathstral-7B-v0.1",
    use_auth_token=HF_TOKEN,
    cache_dir=CACHE_DIR
)
model = AutoModelForCausalLM.from_pretrained(
    "mistralai/Mathstral-7B-v0.1",
    use_auth_token=HF_TOKEN,
    cache_dir=CACHE_DIR,
    device_map="auto",
    torch_dtype="float16"
)

# 3. Move model to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# 4. Prepare prompt
prompt = r"""
    Solve this given problem: Bernoulli’s Equation

    $$
   \frac{dy}{dx} + \frac{1}{x}\,y = x^2\,y^3,
   \quad y(1)=2.
   $$


    and give detailed steps for solving this.
"""
inputs = tokenizer(prompt, return_tensors="pt").to(device)

# 5. Set up streaming
streamer = TextIteratorStreamer(
    tokenizer,
    skip_prompt=True,
    skip_special_tokens=True,
)

# 6. Launch generation in a background thread
thread = threading.Thread(
    target=model.generate,
    kwargs={
        **inputs,
        "max_new_tokens": 3000,  # generate up to 500 tokens beyond the prompt
        "do_sample": False,  # greedy decoding
        "num_return_sequences": 1,
        "streamer": streamer,
    },
)
thread.start()

# 7. Print prompt and stream tokens as they arrive
print(prompt + "\n\n--- Solution Streaming Below ---\n")
for chunk in streamer:
    print(chunk, end="", flush=True)

# 8. Wait for the generation thread to finish
thread.join()
