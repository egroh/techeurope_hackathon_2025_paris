from typing import Dict
from mistralai import Mistral
import os
import traceback
import sympy as sp


def build_prompt(problem: str, claimed_solution: str) -> str:
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
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines)


def execute_and_print_latex(code: str) -> None:
    """
    Executes the generated code in a clean namespace, then looks
    for `solver_sol` and `claimed_sol` in that namespace and
    prints both as LaTeX inside $$ $$ delimiters.
    """
    namespace: Dict = {"sp": sp}
    try:
        exec(code, namespace)
    except Exception:
        traceback.print_exc()
        print("Execution of generated code failed.")
        return

    solver_sol = namespace.get("solver_sol")
    claimed_sol = namespace.get("claimed_sol")

    if solver_sol is not None:
        latex_solver = sp.latex(solver_sol)
        print(f"$$\n{latex_solver}\n$$")
    else:
        print("`solver_sol` not found.")

    if claimed_sol is not None:
        latex_claimed = sp.latex(claimed_sol)
        print(f"\n$$\n{latex_claimed}\n$$")
    else:
        print("`claimed_sol` not found.")


def main() -> None:
    """
    Main driver:
      1. Defines problem & claimed solution.
      2. Builds prompt.
      3. Generates solver code.
      4. Executes code and prints both solutions as LaTeX.
    """
    api_key = os.getenv("MISTRAL_API_KEY", "IhmKJGkJv61EPFwWIuY9wCgnbaFV6Fm1")
    client = Mistral(api_key=api_key)

    problem = """Solve the following ODE for $y(x)$, $x>0$:

    $$
    \frac{dy}{dx} + \frac{1}{x}\,y \;=\; x^2\,y^2.
    $$
    """
    claimed_solution = """Therefore, the solution to the given ODE is:
    $$
    \boxed{y = -\frac{1}{x(x+C)}}.
    $$
    """

    prompt = build_prompt(problem, claimed_solution)
    raw_code = generate_solver_code(client, prompt)
    generated_code = strip_code_fences(raw_code)

    execute_and_print_latex(generated_code)


if __name__ == "__main__":
    main()
