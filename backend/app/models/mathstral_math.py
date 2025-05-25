import os
import threading
import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer

# 0. Set up caching directory
CACHE_DIR = "/Data/tech_paris_hack"
os.makedirs(CACHE_DIR, exist_ok=True)

# Point HF Hub and transformers at that directory
os.environ["HF_HOME"] = CACHE_DIR
os.environ["TRANSFORMERS_CACHE"] = CACHE_DIR

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
    torch_dtype=torch.float16
)

# 3. Move model to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# 4. Prepare prompt
prompt = r"""
Solve this given problem:

Solve the following ODE for $y(x)$, $x>0$:

$$
\frac{dy}{dx} + \frac{1}{x}\,y \;=\; x^2\,y^2.
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
        "max_new_tokens": 3000,
        "do_sample": False,
        "num_return_sequences": 1,
        "streamer": streamer,
        "pad_token_id": tokenizer.eos_token_id
    },
)
thread.start()

# 7. Collect and print the streamed output
print(prompt + "\n\n--- Solution Streaming Below ---\n")
full_output = ""
for chunk in streamer:
    print(chunk, end="", flush=True)
    full_output += chunk

thread.join()

# 8. Extract the last $$...$$ block along with its preceding line
#    This regex captures the line immediately before the final $$...$$
pattern = r'([^\n]+)\n(\$\$[\s\S]*?\$\$)'
matches = re.findall(pattern, full_output)
if matches:
    # Take the last match
    preceding_line, equation_block = matches[-1]
    derived_solution = f"{preceding_line}\n{equation_block}"
else:
    derived_solution = "Could not extract the final equation and its preceding line."

# 9. Output the result
print("\n\nDerived solution string:\n")
print(derived_solution)
