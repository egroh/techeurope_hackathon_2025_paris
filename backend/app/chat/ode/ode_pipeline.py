# main.py
import os

# Import our refactored modules
import mathstral_solver
import codestral_verifier



# 0. Set up caching directory for Hugging Face models
# CACHE_DIR = os.getenv("HF_CACHE_DIR", "/Data/tech_paris_hack")  # Default if not set
CACHE_DIR = os.getenv("HF_HOME", "/tmp/huggingface_cache")  # Default if not set

# 1. Hugging Face Token for Mathstral (if needed for gated model access)
#    Leave as "" or None if model is public or token is already in HF_HUB_TOKEN env var
HF_TOKEN = os.getenv("HF_TOKEN", "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")  # Replace with your token or ""

# 2. Mistral API Key for Codestral
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "IhmKJGkJv61EPFwWIuY9wCgnbaFV6Fm1")  # Replace with your key

# 3. Define the math problem
MATH_PROBLEM_STATEMENT = r"""
Solve the following ODE for $y(x)$, $x>0$:

$$
\frac{dy}{dx} + \frac{1}{x}\,y \;=\; x^2\,y^2.
$$

"""

def format_prompt_for_ode(prompt: str) -> str:
    # Mathstral prompt includes instructions
    MATHSTRAL_PROMPT = f"""
    Solve this given problem:

    {prompt}

    and give detailed steps for solving this. 
    Only Give all the equations in $$ $$ latex code representation 
    """
    return MATHSTRAL_PROMPT


def run_ode_pipeline(prompt: str):
    """
    Runs the full pipeline:
    1. Initialize Mathstral.
    2. Solve problem with Mathstral.
    3. Verify Mathstral's solution with Codestral.
    """
    print("--- Starting Math Problem Solving and Verification Pipeline ---")

    # --- Step 1: Solve with Mathstral ---
    print("\n--- Phase 1: Solving with Mathstral ---")
    try:
        tokenizer, model, device = mathstral_solver.initialize_mathstral(HF_TOKEN, CACHE_DIR)
        
        prompt_foematted = format_prompt_for_ode(prompt)
        # Set stream_output to False if you don't want to see Mathstral's live generation
        full_mathstral_output, derived_mathstral_solution = mathstral_solver.generate_solution(
            tokenizer, model, device, prompt_foematted, stream_output=True
        )

        print("\n\nFull Mathstral Output (for context):\n")
        print(full_mathstral_output)

        print("\n\nDerived solution string from Mathstral:\n")
        print(derived_mathstral_solution)

        if "Could not extract" in derived_mathstral_solution:
            print(
                "\nWARNING: Mathstral did not produce a clearly extractable final solution. Verification might be unreliable.")

    except Exception as e:
        print(f"An error occurred during the Mathstral phase: {e}")
        print("Skipping Codestral verification.")
        return

    # --- Step 2: Verify with Codestral ---
    print("\n\n--- Phase 2: Verifying with Codestral ---")
    if not MISTRAL_API_KEY or MISTRAL_API_KEY == "your_mistral_api_key_here":
        print("MISTRAL_API_KEY is not set or is set to placeholder. Skipping Codestral verification.")
        print("Please set MISTRAL_API_KEY environment variable or in main.py to run verification.")
    elif "Could not extract" in derived_mathstral_solution:  # Don't verify if Mathstral failed
        print("Skipping Codestral verification as Mathstral did not provide a clear solution.")
    else:
        try:
            codestral_verifier.verify_solution_with_codestral(
                MISTRAL_API_KEY,
                prompt,  # Pass the original problem statement
                derived_mathstral_solution  # Pass Mathstral's derived solution
            )
        except Exception as e:
            print(f"An error occurred during the Codestral verification phase: {e}")

    print("\n--- Pipeline Finished ---")


if __name__ == "__main__":
    # Basic check for API keys before starting
    if not HF_TOKEN and "Mathstral-7B-v0.1" not in os.getenv("HF_HOME", ""):  # Simple check, might need adjustment
        print("Warning: HF_TOKEN is not set. Mathstral might fail if the model is gated and not cached.")
        # input("Press Enter to continue or Ctrl+C to abort...") # Optional pause

    run_ode_pipeline()