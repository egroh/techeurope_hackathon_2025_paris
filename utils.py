from latex2sympy2 import latex2sympy, latex2latex

sye = latex2sympy("\\frac{dy}{dx} + \frac{1}{x},y = x^2\,y^3, \quad y(1)=2.")

print(sye)