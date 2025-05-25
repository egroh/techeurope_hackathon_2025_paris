# mathstral_solver.py
import os
import threading
import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer

# Global cache for tokenizer and model to avoid reloading if called multiple times
_mathstral_tokenizer = None
_mathstral_model = None
_mathstral_device = None


def initialize_mathstral(hf_token: str, cache_dir: str):
    """
    Initializes the Mathstral tokenizer and model.
    Sets up caching directory and HF environment variables.
    """
    global _mathstral_tokenizer, _mathstral_model, _mathstral_device

    if _mathstral_model is not None and _mathstral_tokenizer is not None:
        print("Mathstral model and tokenizer already initialized.")
        return _mathstral_tokenizer, _mathstral_model, _mathstral_device

    print("Initializing Mathstral model and tokenizer...")
    os.makedirs(cache_dir, exist_ok=True)
    os.environ["HF_HOME"] = cache_dir
    os.environ["TRANSFORMERS_CACHE"] = cache_dir
    if hf_token:
        os.environ["HF_HUB_TOKEN"] = hf_token

    try:
        _mathstral_tokenizer = AutoTokenizer.from_pretrained(
            "mistralai/Mathstral-7B-v0.1",
            use_auth_token=hf_token if hf_token else None,
            cache_dir=cache_dir
        )
        _mathstral_model = AutoModelForCausalLM.from_pretrained(
            "mistralai/Mathstral-7B-v0.1",
            use_auth_token=hf_token if hf_token else None,
            cache_dir=cache_dir,
            device_map="auto",
            torch_dtype=torch.float16
        )
        _mathstral_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _mathstral_model.to(_mathstral_device)
        print(f"Mathstral model loaded on {_mathstral_device}.")
    except Exception as e:
        print(f"Error initializing Mathstral: {e}")
        print("Please ensure you have a valid HF_TOKEN with access to mistralai/Mathstral-7B-v0.1 if it's gated.")
        print("If the model is public, you might not need a token, or try setting hf_token to None or empty string.")
        raise

    return _mathstral_tokenizer, _mathstral_model, _mathstral_device


def generate_solution(
        tokenizer: AutoTokenizer,
        model: AutoModelForCausalLM,
        device: torch.device,
        problem_prompt: str,
        stream_output: bool = True
) -> tuple[str, str]:
    """
    Generates a solution for the given problem prompt using Mathstral.
    Returns the full generated output and the extracted derived solution.
    """
    inputs = tokenizer(problem_prompt, return_tensors="pt").to(device)

    streamer = TextIteratorStreamer(
        tokenizer,
        skip_prompt=True,
        skip_special_tokens=True,
    )

    generation_kwargs = {
        **inputs,
        "max_new_tokens": 3000,
        "do_sample": False,
        "num_return_sequences": 1,
        "streamer": streamer,
        "pad_token_id": tokenizer.eos_token_id
    }

    thread = threading.Thread(target=model.generate, kwargs=generation_kwargs)
    thread.start()

    if stream_output:
        print("\n--- Mathstral Solution Streaming Below ---\n")

    full_output = ""
    for chunk in streamer:
        if stream_output:
            print(chunk, end="", flush=True)
        full_output += chunk

    thread.join()
    if stream_output:
        print("\n--- End of Mathstral Streaming ---")

    # --- Solution Extraction Logic ---
    derived_solution_text = "Could not extract the final equation and its preceding line from Mathstral output."

    # Pattern to find a line (possibly empty after stripping) followed by a math block (either $$...$$ or \[...\])
    # Group 1: The content of the line immediately preceding the math block (captured by [^\n\r]*).
    # Group 2: The entire math block itself (e.g., $$...$$ or \[...\]).
    # Group 3: Content of $$...$$ if that was the type of block. (Inner part of OR)
    # Group 4: Content of \[...\] if that was the type of block. (Inner part of OR)
    pattern_for_last_solution = r'([^\n\r]*)\n\s*((\$\$[\s\S]*?\$\$)|(\\\[[\s\S]*?\\\]))'

    all_solution_candidates = list(re.finditer(pattern_for_last_solution, full_output))

    if all_solution_candidates:
        last_candidate_match = all_solution_candidates[-1]

        preceding_line = last_candidate_match.group(1).strip()
        equation_block = last_candidate_match.group(2).strip()

        # If the captured preceding_line (group 1) is empty, it means the math block
        # was separated from previous text by at least one blank line.
        # In this case, we try to find the actual last non-blank line before the entire match.
        if not preceding_line and equation_block:  # group(1) was empty or just whitespace
            match_start_offset = last_candidate_match.start()  # Start of the matched "preceding_line_text\nmath_block"
            if match_start_offset > 0:
                # Extract text segment before the start of this whole match
                text_before_current_match = full_output[0:match_start_offset].strip()
                if text_before_current_match:
                    # The last line of this segment is our candidate for the true preceding line
                    potential_true_preceding_line = text_before_current_match.splitlines()[-1].strip()
                    if potential_true_preceding_line:
                        preceding_line = potential_true_preceding_line

        # Assemble the derived solution string
        if preceding_line:
            # Heuristic: Retain preceding line if it seems descriptive or is a clear label.
            is_conclusion_header = "conclusion" in preceding_line.lower() and preceding_line.startswith("#")
            is_likely_descriptive = (
                    len(preceding_line) > 20 or
                    preceding_line.endswith(':') or
                    is_conclusion_header or
                    "solution is" in preceding_line.lower() or
                    "answer is" in preceding_line.lower() or
                    "expression for" in preceding_line.lower() or
                    "we get" in preceding_line.lower() or  # common connecting phrases
                    preceding_line.lower().startswith("therefore")
            )

            if is_likely_descriptive:
                derived_solution_text = f"{preceding_line}\n{equation_block}"
            else:  # Preceding line is too short/generic, just use the equation
                derived_solution_text = equation_block
        elif equation_block:  # No usable preceding line found or captured
            derived_solution_text = equation_block

    # Fallback: If the primary pattern didn't yield a result or no candidates were found
    # This might happen if the output is just an equation block without clear preceding structure matching the pattern.
    if "Could not extract" in derived_solution_text or not all_solution_candidates:
        # Find the absolute last math block ( $$ or \[ )
        last_dollar_match_obj = None
        dollar_block_matches = list(re.finditer(r'(\$\$[\s\S]*?\$\$)', full_output))
        if dollar_block_matches: last_dollar_match_obj = dollar_block_matches[-1]

        last_bracket_match_obj = None
        bracket_block_matches = list(re.finditer(r'(\\\[[\s\S]*?\\\])', full_output))
        if bracket_block_matches: last_bracket_match_obj = bracket_block_matches[-1]

        final_math_block_obj = None
        if last_dollar_match_obj and last_bracket_match_obj:
            final_math_block_obj = last_dollar_match_obj if last_dollar_match_obj.start() > last_bracket_match_obj.start() else last_bracket_match_obj
        elif last_dollar_match_obj:
            final_math_block_obj = last_dollar_match_obj
        elif last_bracket_match_obj:
            final_math_block_obj = last_bracket_match_obj  # Corrected from bracket_block_matches[-1]

        if final_math_block_obj:
            equation_block = final_math_block_obj.group(
                1).strip()  # group(1) because these simple regexes have one capture group
            # Try to find a preceding line for this block
            block_start_offset = final_math_block_obj.start(1)  # Start of the equation block content
            if block_start_offset > 0:
                text_before_block = full_output[0:block_start_offset].strip()
                if text_before_block:
                    preceding_line = text_before_block.splitlines()[-1].strip()
                    # Filter for relevance (not too long, not a list item unless it's descriptive)
                    if preceding_line and len(preceding_line) < 150 and \
                            not (preceding_line.startswith(("* ", "- ", "> ")) and len(preceding_line) < 10) and \
                            not (preceding_line.startswith("# ") and len(
                                preceding_line) < 15 and "conclusion" not in preceding_line.lower()):
                        derived_solution_text = f"{preceding_line}\n{equation_block}"
                    else:
                        derived_solution_text = equation_block  # Just the block
                else:
                    derived_solution_text = equation_block  # Just the block
            else:  # Block is at the very start of the output
                derived_solution_text = equation_block

    return full_output, derived_solution_text