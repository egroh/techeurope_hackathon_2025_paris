import sympy as sp

# Generalized ODE solver using Sympy
def solve_ode(expr, y, x, ics=None, relation='='):
    """
    Solve an ODE given in Sympy form.

    Parameters:
    - expr: a Sympy Eq or expression. If expression, it's assumed expr=0.
    - y: the dependent function, e.g., y = sp.Function('y')
    - x: the independent symbol, e.g., x = sp.symbols('x')
    - ics: initial conditions as dict, e.g., {y(1): 2}
    - relation: '=' if expr is Eq, otherwise '-' treats expr as lhs - rhs = 0

    Returns:
    - solution: the Sympy Eq y(x) = ...
    """
    # Ensure equation is Eq
    if not isinstance(expr, sp.Equality):
        eq = sp.Eq(expr, 0)
    else:
        eq = expr

    # Solve via dsolve
    sol = sp.dsolve(eq, y(x), ics=ics)
    return sol


if __name__ == '__main__':
    # Symbols and function
    x = sp.symbols('x')
    y = sp.Function('y')

    # 1. Linear ODE: y' + tan(x)*y = sin(x), y(pi/4)=0
    ode1 = sp.Eq(sp.diff(y(x), x) + sp.tan(x)*y(x) - sp.sin(x), 0)
    sol1 = solve_ode(ode1, y, x, ics={y(sp.pi/4): 0})

    # 2. Exact-ish: (2xy + y^2) dx + (x^2 + 2xy) dy = 0, y(1)=1
    eq2 = sp.Eq((2*x*y(x) + y(x)**2) + (x**2 + 2*x*y(x))*sp.diff(y(x), x), 0)
    sol2 = solve_ode(eq2, y, x, ics={y(1): 1})

    # 3. Equation: y' = (x + 2y)/(2x - y)
    ode3 = sp.Eq(sp.diff(y(x), x), (x + 2*y(x))/(2*x - y(x)))
    sol3 = solve_ode(ode3, y, x)

    # 4. Repeat of 1
    sol4 = sol1

    # 5. Bernoulli: y' + y/x = x**2 * y**3, y(1)=2
    ode5 = sp.Eq(sp.diff(y(x), x) + y(x)/x - x**2*y(x)**3, 0)
    sol5 = solve_ode(ode5, y, x, ics={y(1): 2})

    # 6. Logistic equation: y' = y*(1 - y), y(0)=0.5
    ode6 = sp.Eq(sp.diff(y(x), x), y(x) * (1 - y(x)))
    sol6 = solve_ode(ode6, y, x, ics={y(0): 0.5})

    print("Solution 1:", sol1)
    print("Solution 2:", sol2)
    print("Solution 3:", sol3)
    print("Solution 4:", sol4)
    print("Solution 5:", sol5)
    print("Solution 6:", sol6)
