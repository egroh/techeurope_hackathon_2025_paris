#!/usr/bin/env python3
import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def main():
    # ────────────────────────────────────────────────────────────────────────────
    # 0. Configure cache and HF token (if not already in env)
    # ────────────────────────────────────────────────────────────────────────────
    CACHE_DIR = "/Data/tech_paris_hack"
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.environ["HF_HOME"] = CACHE_DIR
    os.environ["TRANSFORMERS_CACHE"] = CACHE_DIR
    # Make sure HF_HUB_TOKEN is exported in your shell, or uncomment below:
    os.environ["HF_HUB_TOKEN"] = "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"

    # ────────────────────────────────────────────────────────────────────────────
    # 1. Load tokenizer & model – auto-shard across all available GPUs
    # ────────────────────────────────────────────────────────────────────────────
    model_name = "mistralai/Mathstral-7B-v0.1"
    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=CACHE_DIR)

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        cache_dir=CACHE_DIR,
        device_map="auto",            # <— auto-splits layers across all GPUs
        load_in_4bit=True,            # <— optional quantization to save VRAM
        offload_folder="./offload",   # <— optional spill to disk if needed
    )
    model.eval()

    # ────────────────────────────────────────────────────────────────────────────
    # 2. Inference
    # ────────────────────────────────────────────────────────────────────────────
    prompt = "Calculate the derivative of x^3."
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=64,
            do_sample=False,
        )

    # ────────────────────────────────────────────────────────────────────────────
    # 3. Decode & print
    # ────────────────────────────────────────────────────────────────────────────
    result = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"\nPrompt:     {prompt}\nGeneration: {result}")

if __name__ == "__main__":
    main()
