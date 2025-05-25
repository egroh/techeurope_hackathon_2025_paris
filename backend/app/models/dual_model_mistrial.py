import os
import re
import requests
import subprocess
import tempfile
import time
from typing import List, Dict
from mistralai import Mistral

class SimpleMathVerifier:


###################conect the mistaril client###############################
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.client= Mistral(api_key=self.api_key)


    def call_api(self, prompt: str,model="mistral-large-latest") -> str:
        """Call Mistral AI API"""
        
        message= [{"role": "user", "content": prompt}]

        
        
        chat_response = self.client.chat.complete(
                model=model,
                messages=message
            )
        return chat_response.choices[0].message.content


###################generate steps prompt###############################


    def generate_solution_steps(self, problem: str) -> List[str]:
        """Generate mathematical solution steps"""
        prompt = f"""
Solve this mathematical problem step by step:

{problem}

Please answer in the following format:
Step 1: [specific step description]
Step 2: [specific step description]
...
Final Answer: [final answer]

Make each step clear and specific.
"""
        
        response = self.call_api(prompt)
        #print(response)
        
        # Parse steps
        steps = []
        for line in response.split('\n'):
            line = line.strip()
            if re.search(r'Step \d+', line, re.IGNORECASE) or re.search(r'Final Answer', line, re.IGNORECASE):
                steps.append(line)
        
        return steps
###################generate codes prompt###############################


    def generate_verification_code(self, step: str, step_num: int) -> str:
        """Generate verification code for each step"""
        prompt = f"""
Generate Python verification code for this mathematical step:

{step}

Requirements:
1. Use sympy library for mathematical calculations
2. Code must be complete and runnable
3. Print "PASS" if verification passes, print "FAIL" if verification fails
4. Include try-except error handling

Format:
```python
import sympy as sp
import math

try:
    # verification logic
    # ...
    print("PASS")
except Exception as e:
    print("FAIL")
```

Return only the code, no other explanations.
"""
        
        #response = self.call_api(prompt,model="codestral-latest")
        response = self.call_api(prompt)
        #print(response)
        
        # Extract code
        code_match = re.search(r'```python\n(.*?)\n```', response, re.DOTALL)
        if code_match:
            return code_match.group(1)
        else:
            # If no code block found, return simple template
            return f'''import sympy as sp
import math

try:
    # Step {step_num}: {step}
    # TODO: Add verification logic
    print("FAIL")  # Default fail, needs manual implementation
except Exception as e:
    print("FAIL")
'''
###################run the code###############################

    def run_code_file(self, code: str) -> tuple:
        """Save code to file, run it, then delete"""
        temp_file = None
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_file = f.name
            
            # Run file
            result = subprocess.run(
                ['python', temp_file], 
                capture_output=True, 
                text=True, 
                timeout=15,
                encoding='utf-8'
            )
            
            # Check result
            success = result.returncode == 0
            output = result.stdout.strip() if result.stdout else ""
            error = result.stderr.strip() if result.stderr else ""
            
            # Determine if passed
            passed = "PASS" in output and result.returncode == 0
            
            return success, passed, output, error
            
        except subprocess.TimeoutExpired:
            return False, False, "", "Code execution timeout"
        except Exception as e:
            return False, False, "", f"Execution error: {str(e)}"
        finally:
            # Delete temporary file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass  # Ignore deletion failure
###################verify solution workflow###############################

    def verify_solution(self, problem: str):
        """Complete verification workflow"""
        print(f"🔍 Problem: {problem}")
        print("="*60)
        
        # 1. Generate solution steps
        print("📝 Generating solution steps...")
        steps = self.generate_solution_steps(problem)
        
        if not steps:
            print("❌ Unable to generate solution steps")
            return
        
        print(f"Found {len(steps)} steps")
        
        # 2. Generate verification code for each step and run
        results = []
        for i, step in enumerate(steps, 1):
            print(f"\n--- Step {i} ---")
            print(f"Step: {step}")
            
            # Generate verification code
            print("🔧 Generating verification code...")
            code = self.generate_verification_code(step, i)
            
            # Save, run, delete
            print("⚡ Running verification (save file→run→delete)...")
            success, passed, output, error = self.run_code_file(code)
            
            if success and passed:
                status = "✅ Passed"
                is_correct = True
            elif success and not passed:
                status = "❌ Failed"
                is_correct = False
            else:
                status = "⚠️ Execution Error"
                is_correct = False
            
            print(f"Result: {status}")
            
            # Display output information
            if output:
                print(f"Output: {output}")
            if error:
                print(f"Error: {error}")
            
            # If failed, show generated code
            if not is_correct:
                print("Generated code:")
                print("-" * 40)
                print(code)
                print("-" * 40)
            
            results.append({
                'step': step,
                'code': code,
                'correct': is_correct,
                'execution_success': success,
                'output': output,
                'error': error
            })
        
        # 3. Summary
        print("\n" + "="*60)
        print("📊 Verification Summary:")
        passed = sum(1 for r in results if r['correct'])
        total = len(results)
        
        for i, result in enumerate(results, 1):
            if result['correct']:
                status = "✅"
            elif result['execution_success']:
                status = "❌"  # Code ran but verification failed
            else:
                status = "⚠️"  # Code execution error
                
            step_short = result['step'][:50] + "..." if len(result['step']) > 50 else result['step']
            print(f"{status} Step {i}: {step_short}")
        
        accuracy = (passed / total * 100) if total > 0 else 0
        print(f"\n🎯 Overall Accuracy: {passed}/{total} ({accuracy:.1f}%)")
        
        # Show execution issue statistics
        exec_failed = sum(1 for r in results if not r['execution_success'])
        if exec_failed > 0:
            print(f"⚠️ Code execution failed: {exec_failed}/{total} steps")
        
        return results

    def test_execution(self):
        """Test file execution functionality"""
        print("Testing file execution functionality...")
        
        test_code = '''import sympy as sp
import math

try:
    # Simple test
    x = sp.Symbol('x')
    expr = x**2 + 1
    result = expr.subs(x, 2)  # Should equal 5
    if result == 5:
        print("PASS")
    else:
        print("FAIL")
except Exception as e:
    print("FAIL")
'''
        
        success, passed, output, error = self.run_code_file(test_code)
        
        print(f"Execution successful: {success}")
        print(f"Verification passed: {passed}")
        print(f"Output: {output}")
        if error:
            print(f"Error: {error}")
        
        return success and passed

def main():
    print("Starting File Execution Math Verifier")
    print("="*50)
    
    # Initialize verifier
    try:
        verifier = SimpleMathVerifier()
    except ValueError as e:
        print(f"Error: {e}")
        return
    
    # Test execution functionality first
    if verifier.test_execution():
        print("✅ File execution functionality normal\n")
    else:
        print("❌ File execution functionality abnormal, please check Python environment and SymPy installation\n")
        print("Tip: Make sure sympy is installed (pip install sympy)")
        return
    
    # Test problems
    problems = [
    "Solve this ODE for y(x), giving its general solution:\frac{d^2y}{dx^2} - y = e^x.\n"
    ]
    
    for problem in problems:
        print("\n" + "="*80)
        verifier.verify_solution(problem)
        print("\n")


if __name__ == "__main__":
    os.environ["MISTRAL_API_KEY"] = "IhmKJGkJv61EPFwWIuY9wCgnbaFV6Fm1"
    
    main()