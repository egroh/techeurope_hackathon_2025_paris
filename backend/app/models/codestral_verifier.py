# codestral_verifier.py
from typing import Dict
from mistralai import Mistral
import os
import traceback
import sympy as sp


def build_verification_prompt(problem: str, claimed_solution: str) -> str:
    """
    Construct a generic prompt for the Codestral model given a problem
    and claimed solution. Instructs the model to assign:
      - solver’s result to `solver_sol`
      - claimed result to `claimed_sol`
    without assertions.
    """
    template = """
Given the following problem description and claimed solution, automatically:

1. Select an appropriate Python solver library (e.g., sympy, z3).
2. Extract the core equation(s) from the problem string and convert them into the solver’s API format.
3. Extract the claimed solution from the solution string and convert it into a form that can be compared programmatically.
4. Write complete Python code that:
   - Uses the selected solver to solve the problem and assigns its result to `solver_sol`.
   - Parses the claimed solution and assigns it to `claimed_sol`.
   - Does not perform assertions or prints.

Problem:
\"\"\"{problem}\"\"\"

Claimed solution:
\"\"\"{claimed_solution}\"\"\"

Only output the Python code.
"""
    return template.format(problem=problem, claimed_solution=claimed_solution)


def generate_solver_code(
        client: Mistral, prompt: str, model: str = "codestral-latest"
) -> str:
    """
    Send the prompt to the Codestral model and return its code output.
    """
    response = client.chat.complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        stream=False,
    )
    return response.choices[0].message.content


def strip_code_fences(code: str) -> str:
    """
    Remove leading/trailing Markdown code fences if present.
    """
    lines = code.splitlines()
    if lines and lines[0].strip().startswith("```"):  # Added strip() for robustness
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):  # Added strip() for robustness
        lines = lines[:-1]
    return "\n".join(lines)


def execute_and_compare_solutions(code: str) -> None:
    """
    Executes the generated code in a clean namespace, then looks
    for `solver_sol` and `claimed_sol` in that namespace and
    prints both as LaTeX inside $$ $$ delimiters.
    Also attempts a symbolic comparison if both are Sympy expressions.
    """
    namespace: Dict = {"sp": sp}  # Make sympy available in the exec context
    solver_sol_obj = None
    claimed_sol_obj = None

    print("\n--- Codestral Generated Code ---")
    print(code)
    print("--- End of Codestral Generated Code ---\n")

    print("--- Codestral Verification Results ---")
    try:
        exec(code, namespace)
    except Exception:
        traceback.print_exc()
        print("Execution of generated code failed.")
        return

    solver_sol_obj = namespace.get("solver_sol")
    claimed_sol_obj = namespace.get("claimed_sol")

    print("\nSolution from Codestral's solver (solver_sol):")
    if solver_sol_obj is not None:
        try:
            latex_solver = sp.latex(solver_sol_obj)
            print(f"$$\n{latex_solver}\n$$")
        except Exception as e:
            print(f"Could not convert solver_sol to LaTeX: {e}")
            print(f"solver_sol raw: {solver_sol_obj}")
    else:
        print("`solver_sol` not found in generated code.")

    print("\nClaimed solution parsed by Codestral (claimed_sol):")
    if claimed_sol_obj is not None:
        try:
            latex_claimed = sp.latex(claimed_sol_obj)
            print(f"\n$$\n{latex_claimed}\n$$")
        except Exception as e:
            print(f"Could not convert claimed_sol to LaTeX: {e}")
            print(f"claimed_sol raw: {claimed_sol_obj}")
    else:
        print("`claimed_sol` not found in generated code.")

    # Attempt comparison if both are Sympy objects
    if solver_sol_obj is not None and claimed_sol_obj is not None:
        print("\n--- Symbolic Comparison (Experimental) ---")
        try:
            # This is a basic check. For ODEs, solutions can have different forms (e.g. constants)
            # and might require dsolve to verify or simplification.
            if isinstance(solver_sol_obj, sp.Equality) and isinstance(claimed_sol_obj, sp.Equality):
                # If solutions are like y(x) = ..., compare the RHS
                # This requires knowing the dependent variable, let's assume 'y(x)' or 'y'
                # For simplicity, let's try simplifying the difference of RHS if they are equations
                if hasattr(solver_sol_obj, 'rhs') and hasattr(claimed_sol_obj, 'rhs'):
                    diff = sp.simplify(solver_sol_obj.rhs - claimed_sol_obj.rhs)
                    if diff == 0:
                        print("SUCCESS: The right-hand sides of the solutions simplify to be equivalent.")
                    else:
                        print(f"INFO: Difference of RHS (solver - claimed) simplifies to: {sp.latex(diff)}")
                        print(
                            "The solutions might be different or require further checks (e.g., checking if claimed_sol satisfies the ODE).")
                else:  # If not sp.Equality or no rhs, try direct equality
                    if sp.simplify(solver_sol_obj - claimed_sol_obj) == 0:
                        print("SUCCESS: The solutions simplify to be equivalent.")
                    else:
                        print("INFO: The solutions do not simplify to be directly equivalent.")

            elif sp.simplify(solver_sol_obj - claimed_sol_obj) == 0:
                print("SUCCESS: The solutions simplify to be equivalent.")
            else:  # A fallback, more general comparison might be needed.
                print("INFO: Attempted direct simplification and solutions are not equivalent.")
                print(
                    "Further verification might be needed, e.g., substituting the claimed solution into the original ODE.")

        except Exception as e:
            print(f"Error during symbolic comparison: {e}")
    print("--- End of Codestral Verification ---")


def verify_solution_with_codestral(
        mistral_api_key: str,
        problem_description: str,
        mathstral_claimed_solution: str,
        codestral_model: str = "codestral-latest"
) -> None:
    """
    Main driver for Codestral verification:
      1. Initializes Mistral client.
      2. Builds prompt.
      3. Generates solver code via Codestral.
      4. Executes code and prints both solutions as LaTeX.
    """
    if not mistral_api_key:
        print("MISTRAL_API_KEY not provided. Codestral verification will be skipped.")
        return

    client = Mistral(api_key=mistral_api_key)

    prompt = build_verification_prompt(problem_description, mathstral_claimed_solution)
    raw_code = generate_solver_code(client, prompt, model=codestral_model)
    generated_code = strip_code_fences(raw_code)

    execute_and_compare_solutions(generated_code)