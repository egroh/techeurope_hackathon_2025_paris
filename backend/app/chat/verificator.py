import re
from weaviate_client import WeaviateClient
from mathstral_model import MATHSTRAL_MODEL

def extract_sections(llm_answer: str) -> tuple[list[str], list[str]]:
    """
    Returns (assumptions, steps), each a list of strings.
    Discards any text before the first tag.
    """
    # extract assumptions
    asm_parts = re.split(r"<assumption\s*>", llm_answer)
    raw_ass  = asm_parts[1:] if len(asm_parts) > 1 else []
    assumptions = [a.strip() for a in raw_ass if a.strip()]

    # extract steps
    step_parts = re.split(r"<step\s*>", llm_answer)
    raw_steps  = step_parts[1:] if len(step_parts) > 1 else []
    steps = [s.strip() for s in raw_steps if s.strip()]

    return assumptions, steps

def verify_step(step: str,
                retrieved: list[dict],
                assumptions: list[str],
                previous_step: str = "") -> str:
    """
    Given one proof step, the 3 retrieved references, and the list of assumptions,
    ask the model to verify the step in light of those assumptions.
    """
    # Build the nested REFERENCES block
    # --- Assumptions subsection
    if assumptions:
        asm_lines = [f"Assumption {i+1}: {text}"
                     for i, text in enumerate(assumptions)]
        asm_block = "\n".join(asm_lines)
    else:
        asm_block = "None"

    # --- Concepts subsection
    concept_blocks = []
    for i, obj in enumerate(retrieved, start=1):
        title = obj["title"]
        contents = obj["contents"]
        concept_blocks.append(
            f"Reference {i}: {title}\n{contents}"
        )
    concepts_block = "\n\n".join(concept_blocks) if concept_blocks else "None"

    prompt = (
    f"You are a proof verifier. Use the following REFERENCE information to check one proof step.\n\n"
    f"STEP TO VERIFY:\n{step}\n"
    )
    
    if previous_step:
        prompt += f"\nPREVIOUS STEP:\n{previous_step}\n"

    prompt += (
    "\nREFERENCES:\n"
    "Assumptions:\n"
    f"{asm_block}\n\n"
    "Concepts:\n"
    f"{concepts_block}\n\n"
    "Briefly show your reasoning, citing reference titles, then on a new line answer EXACTLY TRUE or FALSE (no extra words)."
    )
    return MATHSTRAL_MODEL.generate(prompt)


def refine_proof(problem: str,
                 original_proof: str,
                 bad_step: str,
                 error_reason: str) -> str:
    """
    Re-prompt Mathstral to correct its proof for the given problem,
    including the original problem statement for context.
    """
    prompt = f"""\
You were asked to solve the following mathematics problem—but your previous proof attempt contained an unjustified step.

ORIGINAL PROBLEM:
{problem}

YOUR PREVIOUS PROOF ATTEMPT:
{original_proof}

THE VERIFIER FOUND AN ISSUE:
Bad step:
{bad_step}

Explanation of the error:
{error_reason}

Please provide a fully corrected proof of the ORIGINAL PROBLEM,
using EXACTLY the same <assumption> and <step> format as before."""
    return MATHSTRAL_MODEL.generate(prompt)